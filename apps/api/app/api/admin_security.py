"""Admin security routes — AI activity, events, posture, review.

Auth: admin or reviewer roles only (closest analogs to "clinician_lead"
in this repo's RBAC model — see app/authz.py).

Org scoping: every query filters by `caller.organization_id`. There is
no path that lets one org read another's records.

No raw PHI is exposed — the responses surface hashes, event metadata,
and counts. Free-text `detail` fields on events are written by trusted
admin code; routes that accept user-typed details forward them through
the same scrubbing pipeline used by the security layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import Caller
from app.authz import ROLE_ADMIN, ROLE_REVIEWER, require_roles
from app.services.ai_governance import (
    AIGovernanceRecord,
    AIUseCase,
    HumanReviewStatus,
    SecurityEventType,
    create_governance_record,
)
from app.services.ai_governance_store import (
    append_security_event_row,
    list_records,
    save_record,
    update_review,
)


router = APIRouter(prefix="/admin/security", tags=["admin-security"])

_AdminOrLead = require_roles(ROLE_ADMIN, ROLE_REVIEWER)


# --- Helpers -------------------------------------------------------------


def _is_flagged(record: AIGovernanceRecord) -> bool:
    return any(
        e.get("severity") in ("high", "critical")
        for e in (record.security_events or [])
    )


def _record_to_item(record: AIGovernanceRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "created_at": record.created_at.isoformat() if isinstance(record.created_at, datetime) else record.created_at,
        "organization_id": record.organization_id,
        "provider": record.provider,
        "model_id": record.model_id,
        "use_case": record.use_case,
        "phi_redaction_status": record.phi_redaction_status,
        "human_review_required": record.human_review_required,
        "human_review_status": record.human_review_status,
        "human_reviewer_id": record.human_reviewer_id,
        "workflow_id": record.workflow_id,
        "user_id": record.user_id,
        "security_event_count": len(record.security_events or []),
        "flagged": _is_flagged(record),
    }


# --- Response models -----------------------------------------------------


class AIActivityResponse(BaseModel):
    total: int
    records: list[dict[str, Any]]


class EventsResponse(BaseModel):
    total: int
    events: list[dict[str, Any]]
    flagged_record_ids: list[int]


class PostureResponse(BaseModel):
    organization_id: int
    window_hours: int
    total_ai_calls: int
    pending_review: int
    flagged_records: int
    phi_incidents: int
    injection_attempts: int
    approved_calls: int
    review_completion_rate: float
    most_used_use_case: Optional[str]
    model_id_distribution: dict[str, int]
    severity_distribution: dict[str, int]


class ManualEventCreate(BaseModel):
    event_type: SecurityEventType
    detail: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")
    record_id: Optional[int] = None


class ReviewUpdate(BaseModel):
    review_status: HumanReviewStatus
    notes: Optional[str] = Field(default=None, max_length=4000)


# --- GET /admin/security/ai-activity -------------------------------------


@router.get("/ai-activity", response_model=AIActivityResponse)
def get_ai_activity(
    caller: Caller = Depends(_AdminOrLead),
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    flagged_only: bool = Query(default=False),
    review_status: Optional[HumanReviewStatus] = Query(default=None),
    use_case: Optional[AIUseCase] = Query(default=None),
) -> AIActivityResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = list_records(
        organization_id=caller.organization_id,
        since=cutoff,
        review_status=review_status.value if review_status else None,
        use_case=use_case.value if use_case else None,
    )
    if flagged_only:
        records = [r for r in records if _is_flagged(r)]

    total = len(records)
    paged = records[offset : offset + limit]
    return AIActivityResponse(
        total=total,
        records=[_record_to_item(r) for r in paged],
    )


# --- GET /admin/security/events ------------------------------------------


@router.get("/events", response_model=EventsResponse)
def get_security_events(
    caller: Caller = Depends(_AdminOrLead),
    hours: int = Query(default=72, ge=1, le=720),
    severity: Optional[str] = Query(default=None, pattern=r"^(low|medium|high|critical)$"),
    event_type: Optional[SecurityEventType] = Query(default=None),
) -> EventsResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = list_records(organization_id=caller.organization_id, since=cutoff)

    flattened: list[dict[str, Any]] = []
    flagged_ids: list[int] = []

    for record in records:
        for evt in record.security_events or []:
            if severity and evt.get("severity") != severity:
                continue
            if event_type and evt.get("type") != event_type.value:
                continue

            flattened.append(
                {
                    "record_id": record.id,
                    "organization_id": record.organization_id,
                    "workflow_id": record.workflow_id,
                    "user_id": record.user_id,
                    "provider": record.provider,
                    "model_id": record.model_id,
                    "use_case": record.use_case,
                    **evt,
                }
            )
            if (
                record.id is not None
                and record.id not in flagged_ids
                and evt.get("severity") in ("high", "critical")
            ):
                flagged_ids.append(record.id)

    flattened.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return EventsResponse(
        total=len(flattened),
        events=flattened,
        flagged_record_ids=flagged_ids,
    )


# --- POST /admin/security/events -----------------------------------------


@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_security_event(
    body: ManualEventCreate,
    caller: Caller = Depends(_AdminOrLead),
) -> dict[str, Any]:
    """Manually log a security event. Used for admin-initiated flagging."""
    event = {
        "event_id": str(uuid.uuid4()),
        "type": body.event_type.value,
        "detail": body.detail,
        "severity": body.severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if body.record_id is not None:
        updated = append_security_event_row(
            body.record_id,
            organization_id=caller.organization_id,
            event=event,
        )
        if updated is None:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "record_not_found", "reason": "Record not found in this org."},
            )
        return {"status": "event_appended", "record_id": updated.id}

    # No record_id — create a sentinel record so the event is still org-scoped
    sentinel = create_governance_record(
        organization_id=caller.organization_id,
        prompt="[manual_event]",
        output="[manual_event]",
        model_id="[admin]",
        user_id=caller.user_id,
    )
    sentinel.security_events.append(event)
    if body.severity in ("high", "critical"):
        sentinel.human_review_required = True
        sentinel.human_review_status = HumanReviewStatus.PENDING.value
    new_id = save_record(sentinel)
    return {"status": "event_created", "record_id": new_id}


# --- GET /admin/security/posture -----------------------------------------


@router.get("/posture", response_model=PostureResponse)
def get_security_posture(
    caller: Caller = Depends(_AdminOrLead),
    hours: int = Query(default=168, ge=1, le=720),  # default 7 days
) -> PostureResponse:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = list_records(organization_id=caller.organization_id, since=cutoff)

    total = len(records)
    pending = sum(1 for r in records if r.human_review_status == HumanReviewStatus.PENDING.value)
    flagged = sum(1 for r in records if _is_flagged(r))
    approved = sum(1 for r in records if r.human_review_status == HumanReviewStatus.APPROVED.value)
    rejected = sum(1 for r in records if r.human_review_status == HumanReviewStatus.REJECTED.value)
    phi_incidents = sum(
        1 for r in records
        if r.phi_redaction_status in ("phi_in_prompt", "phi_in_output")
    )

    injection_attempts = 0
    severity_dist: dict[str, int] = {}
    for r in records:
        for evt in r.security_events or []:
            if evt.get("type") == SecurityEventType.PROMPT_INJECTION.value:
                injection_attempts += 1
            sev = evt.get("severity", "unknown")
            severity_dist[sev] = severity_dist.get(sev, 0) + 1

    use_case_dist: dict[str, int] = {}
    for r in records:
        uc = r.use_case or "other"
        use_case_dist[uc] = use_case_dist.get(uc, 0) + 1
    most_used = max(use_case_dist, key=use_case_dist.get) if use_case_dist else None

    model_dist: dict[str, int] = {}
    for r in records:
        m = r.model_id or "unknown"
        model_dist[m] = model_dist.get(m, 0) + 1

    reviewed_total = approved + rejected
    completion_rate = round(reviewed_total / total, 4) if total else 0.0

    return PostureResponse(
        organization_id=caller.organization_id,
        window_hours=hours,
        total_ai_calls=total,
        pending_review=pending,
        flagged_records=flagged,
        phi_incidents=phi_incidents,
        injection_attempts=injection_attempts,
        approved_calls=approved,
        review_completion_rate=completion_rate,
        most_used_use_case=most_used,
        model_id_distribution=model_dist,
        severity_distribution=severity_dist,
    )


# --- PATCH /admin/security/ai-activity/{record_id}/review ----------------


@router.patch("/ai-activity/{record_id}/review")
def update_review_status(
    record_id: int,
    body: ReviewUpdate,
    caller: Caller = Depends(_AdminOrLead),
) -> dict[str, Any]:
    updated = update_review(
        record_id,
        organization_id=caller.organization_id,
        review_status=body.review_status.value,
        reviewer_id=caller.user_id,
        notes=body.notes,
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "record_not_found", "reason": "Record not found in this org."},
        )
    return {
        "status": "updated",
        "record_id": record_id,
        "review_status": updated.human_review_status,
    }
