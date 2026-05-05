"""Patient-friendly summary routes.

Endpoints under `/patients/{patient_id}/patient-summaries`:

  POST   /                                  — create draft (generates v1)
  GET    /                                  — list for patient
  GET    /{summary_id}                      — detail
  PATCH  /{summary_id}                      — edit non-terminal
  POST   /{summary_id}/review               — draft → reviewed
  POST   /{summary_id}/finalize             — reviewed → finalized
  POST   /{summary_id}/discard              — non-terminal → discarded

RBAC: admin + clinician can write. Reviewer is read-only on this
surface.

Org isolation: patient resolved inside caller's org first; cross-org
returns 404 patient_not_found (no existence leak). Cross-org
scribe_session_id is rejected as a source mismatch (also 404 to avoid
existence leakage).

Audit: every mutation emits a `patient_summary_*` row to
`security_audit_events` whose `detail` is metadata-only — summary_id,
patient_id, encounter_id, scribe_session_id, status. Summary body /
key findings / next steps / questions / limitations / review_notes
are NEVER written to the audit log.

This endpoint never sends anything to a patient. Patient delivery is
explicitly deferred.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_one
from app.services.patient_summaries import (
    ImmutablePatientSummary,
    InvalidPatientSummaryTransition,
    PatientSummary,
    PatientSummaryNotFound,
    PatientSummarySourceMismatch,
    create_summary,
    discard_summary,
    finalize_summary,
    get_summary,
    list_summaries_for_patient,
    review_summary,
    update_summary,
)


router = APIRouter(tags=["patient-summaries"])

_WRITE_ROLES: set[str] = {"admin", "clinician"}


# --- helpers -----------------------------------------------------------


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
            f"role {caller.role!r} cannot write patient summaries; "
            "requires admin or clinician",
            403,
        )


def _get_or_404(
    summary_id: int, *, caller: Caller, patient_id: int
) -> PatientSummary:
    summary = get_summary(
        summary_id,
        organization_id=caller.organization_id,
        patient_id=patient_id,
    )
    if summary is None:
        raise _err(
            "patient_summary_not_found",
            "patient summary not found in your organization",
            404,
        )
    return summary


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    summary: PatientSummary,
) -> None:
    """Metadata-only audit. NEVER include summary body or list contents."""
    detail = (
        f"summary_id={summary.id} "
        f"patient_id={summary.patient_id} "
        f"encounter_id={summary.encounter_id} "
        f"scribe_session_id={summary.scribe_session_id} "
        f"status={summary.status}"
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


def _translate_lifecycle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ImmutablePatientSummary):
        return _err(
            "patient_summary_immutable",
            f"summary is {exc.current_status} and cannot be modified",
            409,
        )
    if isinstance(exc, InvalidPatientSummaryTransition):
        return _err(
            "patient_summary_invalid_transition",
            f"cannot {exc.action} from status {exc.current_status}",
            409,
        )
    if isinstance(exc, PatientSummarySourceMismatch):
        # 404 on cross-org/cross-patient mismatch to avoid existence
        # leakage of scribe sessions in other orgs/patients.
        return _err(
            "scribe_session_not_found",
            "scribe session not found in your organization for this patient",
            404,
        )
    if isinstance(exc, PatientSummaryNotFound):
        return _err("patient_summary_not_found", str(exc), 404)
    raise exc  # unknown — let FastAPI 500 it


def _verify_encounter_in_org(
    encounter_id: int, *, caller: Caller, patient_id: int
) -> None:
    row = fetch_one(
        "SELECT id, patient_id FROM encounters "
        "WHERE id = :id AND organization_id = :org",
        {"id": encounter_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    enc_patient = row.get("patient_id")
    if enc_patient is not None and int(enc_patient) != patient_id:
        raise _err(
            "patient_encounter_mismatch",
            "encounter does not belong to this patient",
            400,
        )


# --- pydantic shapes ---------------------------------------------------


class PatientSummaryCreate(BaseModel):
    encounter_id: Optional[int] = None
    scribe_session_id: Optional[int] = None
    provider_instructions: Optional[str] = Field(default=None, max_length=4000)


class PatientSummaryUpdate(BaseModel):
    plain_language_summary: Optional[str] = Field(default=None, max_length=20000)
    key_findings: Optional[list[str]] = None
    next_steps: Optional[list[str]] = None
    questions: Optional[list[str]] = None
    limitations_notice: Optional[str] = Field(default=None, max_length=4000)
    review_notes: Optional[str] = Field(default=None, max_length=20000)


class PatientSummaryReview(BaseModel):
    review_notes: Optional[str] = Field(default=None, max_length=20000)


# --- routes ------------------------------------------------------------


@router.post(
    "/patients/{patient_id}/patient-summaries",
    status_code=status.HTTP_201_CREATED,
)
def create_patient_summary(
    patient_id: int,
    payload: PatientSummaryCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    if payload.encounter_id is not None:
        _verify_encounter_in_org(
            payload.encounter_id, caller=caller, patient_id=pid
        )

    try:
        summary = create_summary(
            organization_id=caller.organization_id,
            patient_id=pid,
            created_by_user_id=caller.user_id,
            encounter_id=payload.encounter_id,
            scribe_session_id=payload.scribe_session_id,
            provider_instructions=payload.provider_instructions,
        )
    except PatientSummarySourceMismatch as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="patient_summary_created",
        summary=summary,
    )
    return summary.to_response()


@router.get("/patients/{patient_id}/patient-summaries")
def list_patient_summaries(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    summaries = list_summaries_for_patient(
        organization_id=caller.organization_id,
        patient_id=pid,
    )
    return {
        "items": [s.to_response() for s in summaries],
        "total": len(summaries),
    }


@router.get("/patients/{patient_id}/patient-summaries/{summary_id}")
def get_patient_summary(
    patient_id: int,
    summary_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    summary = _get_or_404(summary_id, caller=caller, patient_id=pid)
    return summary.to_response()


@router.patch("/patients/{patient_id}/patient-summaries/{summary_id}")
def update_patient_summary(
    patient_id: int,
    summary_id: int,
    payload: PatientSummaryUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    summary = _get_or_404(summary_id, caller=caller, patient_id=pid)

    try:
        updated = update_summary(
            summary,
            plain_language_summary=payload.plain_language_summary,
            key_findings=payload.key_findings,
            next_steps=payload.next_steps,
            questions=payload.questions,
            limitations_notice=payload.limitations_notice,
            review_notes=payload.review_notes,
        )
    except ImmutablePatientSummary as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="patient_summary_updated",
        summary=updated,
    )
    return updated.to_response()


@router.post(
    "/patients/{patient_id}/patient-summaries/{summary_id}/review",
)
def review_patient_summary(
    patient_id: int,
    summary_id: int,
    payload: PatientSummaryReview,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    summary = _get_or_404(summary_id, caller=caller, patient_id=pid)

    try:
        next_summary = review_summary(
            summary,
            reviewer_user_id=caller.user_id,
            review_notes=payload.review_notes,
        )
    except (ImmutablePatientSummary, InvalidPatientSummaryTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="patient_summary_reviewed",
        summary=next_summary,
    )
    return next_summary.to_response()


@router.post(
    "/patients/{patient_id}/patient-summaries/{summary_id}/finalize",
)
def finalize_patient_summary(
    patient_id: int,
    summary_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    summary = _get_or_404(summary_id, caller=caller, patient_id=pid)

    try:
        next_summary = finalize_summary(summary)
    except (ImmutablePatientSummary, InvalidPatientSummaryTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="patient_summary_finalized",
        summary=next_summary,
    )
    return next_summary.to_response()


@router.post(
    "/patients/{patient_id}/patient-summaries/{summary_id}/discard",
)
def discard_patient_summary(
    patient_id: int,
    summary_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    summary = _get_or_404(summary_id, caller=caller, patient_id=pid)

    try:
        next_summary = discard_summary(summary)
    except (ImmutablePatientSummary, InvalidPatientSummaryTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="patient_summary_discarded",
        summary=next_summary,
    )
    return next_summary.to_response()
