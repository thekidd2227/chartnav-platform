"""Scribe-session lifecycle routes.

Endpoints under `/patients/{patient_id}/scribe-sessions`:

  POST   /                                 — create draft
  GET    /                                 — list for patient
  GET    /{session_id}                     — detail
  PATCH  /{session_id}                     — update non-terminal
  POST   /{session_id}/process             — draft → ready_for_review
  POST   /{session_id}/review              — ready_for_review → reviewed
  POST   /{session_id}/finalize            — reviewed → finalized
  POST   /{session_id}/discard             — non-terminal → discarded

RBAC: admin + clinician can write. Reviewer is read-only on this
surface (matches the rest of the patient-chart write surfaces).

Org isolation: every request resolves the patient inside the caller's
org first; cross-org returns **404 `patient_not_found`**.

Audit: every mutation emits a `scribe_session_*` row to
`security_audit_events` whose `detail` is metadata-only — session_id,
patient_id, encounter_id, status, linked_artifact_id. The raw
source_text / transcript_text / draft_note_text / structured_note body
/ review_notes are NEVER written to the audit log.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_one
from app.services.scribe_sessions import (
    ImmutableScribeSession,
    InputMode,
    InvalidScribeTransition,
    PatientEncounterMismatch,
    ScribeSession,
    ScribeSessionNotFound,
    ScribeStatus,
    create_session,
    discard_session,
    finalize_session,
    get_session,
    list_sessions_for_patient,
    process_session,
    review_session,
    update_session,
)


router = APIRouter(tags=["scribe-sessions"])

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
            f"role {caller.role!r} cannot write scribe sessions; "
            "requires admin or clinician",
            403,
        )


def _get_or_404(session_id: int, *, caller: Caller, patient_id: int) -> ScribeSession:
    sess = get_session(
        session_id,
        organization_id=caller.organization_id,
        patient_id=patient_id,
    )
    if sess is None:
        raise _err(
            "scribe_session_not_found",
            "scribe session not found in your organization",
            404,
        )
    return sess


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    sess: ScribeSession,
) -> None:
    """Metadata-only audit. NEVER include source/transcript/draft/structured/review_notes."""
    detail = (
        f"session_id={sess.id} "
        f"patient_id={sess.patient_id} "
        f"encounter_id={sess.encounter_id} "
        f"status={sess.status} "
        f"linked_artifact_id={sess.linked_artifact_id}"
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
    if isinstance(exc, ImmutableScribeSession):
        return _err(
            "scribe_session_immutable",
            f"session is {exc.current_status} and cannot be modified",
            409,
        )
    if isinstance(exc, InvalidScribeTransition):
        return _err(
            "scribe_session_invalid_transition",
            f"cannot {exc.action} from status {exc.current_status}",
            409,
        )
    if isinstance(exc, PatientEncounterMismatch):
        return _err(
            "patient_encounter_mismatch",
            "encounter does not belong to this patient",
            400,
        )
    if isinstance(exc, ScribeSessionNotFound):
        return _err(
            "scribe_session_not_found",
            str(exc),
            404,
        )
    raise exc  # unknown — let FastAPI 500 it


# --- pydantic shapes ----------------------------------------------------


class ScribeSessionCreate(BaseModel):
    encounter_id: Optional[int] = None
    input_mode: str = Field(default=InputMode.PASTED_TEXT, max_length=32)
    source_text: Optional[str] = Field(default=None, max_length=50000)
    transcript_text: Optional[str] = Field(default=None, max_length=50000)
    linked_artifact_id: Optional[int] = None


class ScribeSessionUpdate(BaseModel):
    source_text: Optional[str] = Field(default=None, max_length=50000)
    transcript_text: Optional[str] = Field(default=None, max_length=50000)
    review_notes: Optional[str] = Field(default=None, max_length=20000)
    encounter_id: Optional[int] = None
    linked_artifact_id: Optional[int] = None
    input_mode: Optional[str] = Field(default=None, max_length=32)


class ScribeSessionReview(BaseModel):
    review_notes: Optional[str] = Field(default=None, max_length=20000)


# --- routes -------------------------------------------------------------


@router.post(
    "/patients/{patient_id}/scribe-sessions",
    status_code=status.HTTP_201_CREATED,
)
def create_scribe_session(
    patient_id: int,
    payload: ScribeSessionCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    try:
        sess = create_session(
            organization_id=caller.organization_id,
            patient_id=pid,
            created_by_user_id=caller.user_id,
            encounter_id=payload.encounter_id,
            input_mode=payload.input_mode,
            source_text=payload.source_text,
            transcript_text=payload.transcript_text,
            linked_artifact_id=payload.linked_artifact_id,
        )
    except (ScribeSessionNotFound, PatientEncounterMismatch) as e:
        raise _translate_lifecycle_error(e)
    except ValueError as e:
        raise _err("invalid_input", str(e), 400)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_created",
        sess=sess,
    )
    return sess.to_response()


@router.get("/patients/{patient_id}/scribe-sessions")
def list_scribe_sessions(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    sessions = list_sessions_for_patient(
        organization_id=caller.organization_id,
        patient_id=pid,
    )
    return {
        "items": [s.to_response() for s in sessions],
        "total": len(sessions),
    }


@router.get("/patients/{patient_id}/scribe-sessions/{session_id}")
def get_scribe_session(
    patient_id: int,
    session_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)
    return sess.to_response()


@router.patch("/patients/{patient_id}/scribe-sessions/{session_id}")
def update_scribe_session(
    patient_id: int,
    session_id: int,
    payload: ScribeSessionUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    try:
        updated = update_session(
            sess,
            source_text=payload.source_text,
            transcript_text=payload.transcript_text,
            review_notes=payload.review_notes,
            encounter_id=payload.encounter_id,
            linked_artifact_id=payload.linked_artifact_id,
            input_mode=payload.input_mode,
        )
    except (
        ImmutableScribeSession,
        ScribeSessionNotFound,
        PatientEncounterMismatch,
    ) as e:
        raise _translate_lifecycle_error(e)
    except ValueError as e:
        raise _err("invalid_input", str(e), 400)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_updated",
        sess=updated,
    )
    return updated.to_response()


@router.post(
    "/patients/{patient_id}/scribe-sessions/{session_id}/process",
)
def process_scribe_session(
    patient_id: int,
    session_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    try:
        next_sess = process_session(sess)
    except (ImmutableScribeSession, InvalidScribeTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_processed",
        sess=next_sess,
    )
    return next_sess.to_response()


class AmbientDraftRequest(BaseModel):
    fake_data_context: bool = Field(
        default=True,
        description=(
            "Phase 57 — caller declares the transcript is fake / demo data. "
            "Setting False causes the route to refuse."
        ),
    )


@router.post(
    "/patients/{patient_id}/scribe-sessions/{session_id}/draft-ambient",
)
def draft_ambient_scribe_session(
    patient_id: int,
    session_id: int,
    body: AmbientDraftRequest,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    """Phase 57 — Provider-Reviewed Ambient Documentation Assist.

    Runs the ambient drafting pipeline (deterministic by default, or
    Phase 52B OpenAI fake-data adapter under explicit operator opt-in)
    against the transcript already attached to the scribe session, then
    advances the row to `ready_for_review`. The session row stores the
    enriched structured facts (including safety_flags and
    missing_information) in `structured_note_json`; the audit detail
    remains metadata-only.

    Refuses with 422 when `fake_data_context=False` so the route can
    never be used as a real-PHI promotion path.
    """
    if not body.fake_data_context:
        raise _err(
            "fake_data_context_required",
            "ambient documentation assist is fake-data / demo only; "
            "set fake_data_context=true",
            422,
        )
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    if sess.status != ScribeStatus.DRAFT:
        if sess.is_terminal:
            raise _err(
                "scribe_session_immutable",
                f"session is {sess.status} and cannot be modified",
                409,
            )
        raise _err(
            "invalid_scribe_transition",
            f"draft-ambient requires status=draft (current: {sess.status})",
            409,
        )

    transcript_text = (sess.transcript_text or sess.source_text or "").strip()
    if not transcript_text:
        raise _err(
            "transcript_missing",
            "scribe session has no transcript_text or source_text to draft from",
            422,
        )

    from app.services.ambient_documentation import generate_draft

    result = generate_draft(transcript_text)

    # Persist the ambient result onto the existing scribe_sessions row.
    # Body fields (draft_note_text, structured_note_json) — DO NOT log
    # in audit detail.
    from datetime import datetime, timezone
    import json as _json

    from sqlalchemy import text as _text

    from app.db import transaction as _transaction

    structured_payload = {
        "structured_facts": result.structured_facts,
        "safety_flags": result.safety_flags,
        "missing_information": result.missing_information,
        "requires_provider_review": result.requires_provider_review,
        "forbidden_actions": result.forbidden_actions,
        "ai_model_name": result.ai_model_name,
        "confidence": result.confidence,
    }
    now_iso = datetime.now(timezone.utc).isoformat()
    with _transaction() as conn:
        conn.execute(
            _text(
                "UPDATE scribe_sessions SET "
                "status = :status, "
                "draft_note_text = :draft, "
                "structured_note_json = :structured, "
                "updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "status": ScribeStatus.READY_FOR_REVIEW,
                "draft": result.draft_note,
                "structured": _json.dumps(structured_payload),
                "now": now_iso,
                "id": sess.id,
                "org": sess.organization_id,
            },
        )

    refreshed = get_session(
        sess.id,
        organization_id=sess.organization_id,
        patient_id=sess.patient_id,
    )
    assert refreshed is not None

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_drafted_ambient",
        sess=refreshed,
    )

    response = refreshed.to_response()
    # Surface the ambient-specific shape alongside the session so the
    # frontend renders safety_flags / missing_information / etc. without
    # a second fetch.
    response["ambient_draft"] = result.to_dict()
    return response


@router.post(
    "/patients/{patient_id}/scribe-sessions/{session_id}/review",
)
def review_scribe_session(
    patient_id: int,
    session_id: int,
    payload: ScribeSessionReview,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    try:
        next_sess = review_session(
            sess,
            reviewer_user_id=caller.user_id,
            review_notes=payload.review_notes,
        )
    except (ImmutableScribeSession, InvalidScribeTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_reviewed",
        sess=next_sess,
    )
    return next_sess.to_response()


@router.post(
    "/patients/{patient_id}/scribe-sessions/{session_id}/finalize",
)
def finalize_scribe_session(
    patient_id: int,
    session_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    try:
        next_sess = finalize_session(sess)
    except (ImmutableScribeSession, InvalidScribeTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_finalized",
        sess=next_sess,
    )
    return next_sess.to_response()


@router.post(
    "/patients/{patient_id}/scribe-sessions/{session_id}/discard",
)
def discard_scribe_session(
    patient_id: int,
    session_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    sess = _get_or_404(session_id, caller=caller, patient_id=pid)

    try:
        next_sess = discard_session(sess)
    except (ImmutableScribeSession, InvalidScribeTransition) as e:
        raise _translate_lifecycle_error(e)

    _audit(
        request=request,
        caller=caller,
        event_type="scribe_session_discarded",
        sess=next_sess,
    )
    return next_sess.to_response()
