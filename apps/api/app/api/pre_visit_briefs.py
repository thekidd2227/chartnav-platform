"""Pre-visit brief routes — provider-facing summary of existing chart.

Phase 10. Endpoints under `/patients/{patient_id}/pre-visit-brief...`:

  POST   /patients/{patient_id}/pre-visit-briefs/generate
         Explicit, audited generation. Returns a freshly-computed
         brief and emits a `pre_visit_brief_generated` audit event
         whose `detail` is metadata-only — patient_id, source_counts,
         and generated_at. Body content is NEVER audited.

  GET    /patients/{patient_id}/pre-visit-brief
         Convenience read-on-demand. Computes the same brief from
         current data without emitting an audit event (consistent with
         the read-side of patient_summaries / scribe_sessions, which
         only audit mutations).

RBAC: admin/clinician can both POST and GET. Reviewer is read-only —
GET allowed, POST returns 403 role_forbidden. This matches the
review-only convention on patient_summaries / scribe_sessions.

Org isolation: patient is resolved inside the caller's org first.
Cross-org or unknown returns 404 patient_not_found (no existence
leakage).

This endpoint never sends to a patient, never creates orders, never
writes to any source table. The brief is a derived view, not a
durable artifact.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.services.pre_visit_briefs import (
    PatientNotFoundError,
    PreVisitBrief,
    generate_pre_visit_brief,
    resolve_patient,
)


router = APIRouter(tags=["pre-visit-briefs"])


_WRITE_ROLES: set[str] = {"admin", "clinician"}
_READ_ROLES: set[str] = {"admin", "clinician", "reviewer"}


# --- helpers -----------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _resolve_patient_in_org(patient_id: int, caller: Caller) -> int:
    try:
        resolve_patient(patient_id, organization_id=caller.organization_id)
    except PatientNotFoundError:
        raise _err("patient_not_found", "patient not found in your organization", 404)
    return patient_id


def _require_write_role(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot generate pre-visit briefs; "
            "requires admin or clinician",
            403,
        )


def _require_read_role(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot read pre-visit briefs",
            403,
        )


def _audit_generated(
    *,
    request: Request,
    caller: Caller,
    brief: PreVisitBrief,
) -> None:
    """Audit a generation event with metadata-only detail.

    Detail intentionally encodes only the patient id, the per-source
    counts, and the generated-at timestamp. None of the section bodies
    (last_visit_summary, active_issues, retinal/scribe/summary
    excerpts, pending_items, suggested_review_items, data_gaps) reach
    the audit log.
    """
    counts = brief.source_counts
    counts_str = " ".join(f"{k}={counts[k]}" for k in sorted(counts.keys()))
    detail = (
        f"patient_id={brief.patient_id} "
        f"generated_at={brief.generated_at} "
        f"counts[{counts_str}]"
    )
    audit_record(
        event_type="pre_visit_brief_generated",
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


# --- routes ------------------------------------------------------------


@router.post("/patients/{patient_id}/pre-visit-briefs/generate")
def generate_patient_pre_visit_brief(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    brief = generate_pre_visit_brief(
        organization_id=caller.organization_id,
        patient_id=pid,
    )
    _audit_generated(request=request, caller=caller, brief=brief)
    return brief.to_response()


@router.get("/patients/{patient_id}/pre-visit-brief")
def get_patient_pre_visit_brief(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    brief = generate_pre_visit_brief(
        organization_id=caller.organization_id,
        patient_id=pid,
    )
    return brief.to_response()
