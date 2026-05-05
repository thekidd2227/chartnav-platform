"""Retinal diagram artifact routes (persistence shell).

Endpoints under `/patients/{patient_id}/eye-diagrams`:

  GET    list      — list artifacts for a patient
  GET    detail    — fetch one artifact
  POST   create    — create a new (unsigned) artifact
  PATCH  update    — update an unsigned artifact in place; if the target
                     is signed, the response is HTTP 409 telling the
                     caller to fork via the dedicated `fork=true` flag
  POST   sign      — stamp signed_at; re-sign returns HTTP 409

This is the persistence shell only — no drawing canvas, no AI proposals,
no apply/reject pipeline. The frontend may submit any JSON object as
`drawing_json`; the backend stores it verbatim.

Org isolation: every request resolves the patient by id within the
caller's organization. A patient that does not belong to the caller's
org returns 404 — never leaks existence across orgs.

Audit: create / update / sign / fork events are recorded via
`app.audit.record`. **Audit detail strings carry only metadata
(artifact id, version, action). They never contain `findings_text` or
`drawing_json`.**
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_one
from app.services.chart_artifacts import (
    ARTIFACT_TYPE_RETINAL_DIAGRAM,
    ArtifactAlreadySigned,
    ChartArtifact,
    create_artifact,
    fork_signed_artifact,
    get_for_patient,
    list_for_patient,
    sign_artifact,
    update_unsigned_artifact,
)
from app.services.retinal_proposals import (
    propose_from_findings,
    result_to_response,
)


router = APIRouter(tags=["eye-diagrams"])

_WRITE_ROLES: set[str] = {"admin", "clinician"}


# --- Helpers -------------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _resolve_patient_in_org(patient_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM patients WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("patient_not_found", "patient not found in your organization", 404)
    return int(row["id"])


def _require_write_role(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot write retinal diagrams; "
            "requires admin or clinician",
            403,
        )


def _get_or_404(
    artifact_id: int, *, caller: Caller, patient_id: int
) -> ChartArtifact:
    artifact = get_for_patient(
        artifact_id,
        organization_id=caller.organization_id,
        patient_id=patient_id,
    )
    if artifact is None:
        raise _err("artifact_not_found", "artifact not found in your organization", 404)
    if artifact.artifact_type != ARTIFACT_TYPE_RETINAL_DIAGRAM:
        # The shape only ships retinal_diagram in this PR.
        raise _err("artifact_not_found", "artifact not found in your organization", 404)
    return artifact


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    artifact: ChartArtifact,
) -> None:
    """Record an audit row. Detail is metadata-only — never PHI/clinical."""
    detail = (
        f"artifact_id={artifact.id} "
        f"version={artifact.version_number} "
        f"parent={artifact.parent_artifact_id} "
        f"signed={artifact.is_signed}"
    )
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


# --- Pydantic shapes -----------------------------------------------------


class EyeDiagramCreate(BaseModel):
    title: str = Field(default="", max_length=255)
    findings_text: str = Field(default="", max_length=20000)
    drawing_json: dict[str, Any] = Field(default_factory=dict)
    encounter_id: Optional[int] = None


class EyeDiagramUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    findings_text: Optional[str] = Field(default=None, max_length=20000)
    drawing_json: Optional[dict[str, Any]] = None


class ProposeFromFindings(BaseModel):
    findings_text: str = Field(default="", max_length=20000)
    drawing_json: Optional[dict[str, Any]] = None


# --- Routes --------------------------------------------------------------


@router.get("/patients/{patient_id}/eye-diagrams")
def list_eye_diagrams(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    artifacts = list_for_patient(
        organization_id=caller.organization_id,
        patient_id=pid,
    )
    return {"items": [a.to_response() for a in artifacts], "total": len(artifacts)}


@router.get("/patients/{patient_id}/eye-diagrams/{artifact_id}")
def get_eye_diagram(
    patient_id: int,
    artifact_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    artifact = _get_or_404(artifact_id, caller=caller, patient_id=pid)
    return artifact.to_response()


@router.post(
    "/patients/{patient_id}/eye-diagrams",
    status_code=status.HTTP_201_CREATED,
)
def create_eye_diagram(
    patient_id: int,
    payload: EyeDiagramCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    if payload.encounter_id is not None:
        # Verify encounter is in the caller's org. We don't require
        # patient<->encounter linkage here because encounters in this
        # repo predate the patients table and may be linked via
        # patient_identifier instead of patient_id.
        row = fetch_one(
            "SELECT id FROM encounters WHERE id = :id AND organization_id = :org",
            {"id": payload.encounter_id, "org": caller.organization_id},
        )
        if not row:
            raise _err(
                "encounter_not_found",
                "encounter not found in your organization",
                404,
            )

    artifact = create_artifact(
        organization_id=caller.organization_id,
        patient_id=pid,
        encounter_id=payload.encounter_id,
        created_by_user_id=caller.user_id,
        title=payload.title,
        findings_text=payload.findings_text,
        drawing_json=payload.drawing_json,
    )
    _audit(
        request=request,
        caller=caller,
        event_type="eye_diagram_created",
        artifact=artifact,
    )
    return artifact.to_response()


@router.patch("/patients/{patient_id}/eye-diagrams/{artifact_id}")
def update_eye_diagram(
    patient_id: int,
    artifact_id: int,
    payload: EyeDiagramUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
    fork: bool = Query(
        default=False,
        description=(
            "When true and the target is signed, create a new unsigned "
            "version (fork) instead of returning 409."
        ),
    ),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    artifact = _get_or_404(artifact_id, caller=caller, patient_id=pid)

    if artifact.is_signed:
        if not fork:
            raise _err(
                "artifact_signed_immutable",
                "this artifact is signed and cannot be edited in place; "
                "pass ?fork=true to create a new unsigned version",
                409,
            )
        forked = fork_signed_artifact(
            artifact,
            created_by_user_id=caller.user_id,
            title=payload.title,
            findings_text=payload.findings_text,
            drawing_json=payload.drawing_json,
        )
        _audit(
            request=request,
            caller=caller,
            event_type="eye_diagram_forked",
            artifact=forked,
        )
        return forked.to_response()

    try:
        updated = update_unsigned_artifact(
            artifact,
            title=payload.title,
            findings_text=payload.findings_text,
            drawing_json=payload.drawing_json,
        )
    except ArtifactAlreadySigned:
        # Race: artifact got signed between our SELECT and UPDATE.
        raise _err(
            "artifact_signed_immutable",
            "this artifact is signed and cannot be edited in place",
            409,
        )

    _audit(
        request=request,
        caller=caller,
        event_type="eye_diagram_updated",
        artifact=updated,
    )
    return updated.to_response()


@router.post(
    "/patients/{patient_id}/eye-diagrams/{artifact_id}/sign",
    status_code=status.HTTP_200_OK,
)
def sign_eye_diagram(
    patient_id: int,
    artifact_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    artifact = _get_or_404(artifact_id, caller=caller, patient_id=pid)

    if artifact.is_signed:
        raise _err(
            "artifact_already_signed",
            f"artifact {artifact.id} is already signed",
            409,
        )

    signed = sign_artifact(artifact, signing_user_id=caller.user_id)
    _audit(
        request=request,
        caller=caller,
        event_type="eye_diagram_signed",
        artifact=signed,
    )
    return signed.to_response()


# --- Phase 6: findings -> diagram proposal review -----------------------


@router.post("/patients/{patient_id}/eye-diagrams/propose-from-findings")
def propose_eye_diagram_from_findings(
    patient_id: int,
    payload: ProposeFromFindings,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    """Generate diagram proposals from a findings_text string.

    Pure read on the data side — this endpoint never writes to
    `chart_artifacts`. Proposals only enter `drawing_json` after the
    provider explicitly applies them on the frontend.

    RBAC: admin + clinician only. The endpoint produces clinical
    suggestions, so it follows write-like access even though the data
    layer is read-only.

    Audit detail is metadata-only — counts and patient_id. The raw
    `findings_text` and proposal bodies are NEVER written to the audit
    log.
    """
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    result = propose_from_findings(payload.findings_text or "")
    response = result_to_response(result)

    detail = (
        f"patient_id={pid} "
        f"proposal_count={len(result.proposed_annotations)} "
        f"uncertain_count={len(result.uncertain_phrases)} "
        f"missing_flag_count={len(result.missing_flags)}"
    )
    audit_record(
        event_type="eye_diagram_proposed",
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )

    return response
