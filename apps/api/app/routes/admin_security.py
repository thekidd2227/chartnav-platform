"""
ChartNav Admin Security Routes — final
Routes: GET ai-activity | GET events | POST events | GET posture | PATCH review
Auth: admin or clinician_lead only
Scoping: all queries filter by org_id — no cross-org reads
No raw PHI exposed — only hashes and event metadata
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_async_session
from app.services.ai_governance import (
    AIGovernanceRecord,
    AIUseCase,
    HumanReviewStatus,
    PHIRedactionStatus,
    SecurityEventType,
    append_security_event,
    create_governance_record,
)

router = APIRouter(prefix="/admin/security", tags=["admin-security"])

AdminOrLead = Annotated[Any, Depends(require_roles(["admin", "clinician_lead"]))]


# ── Org scoping guard ─────────────────────────────────────────────────────────

def _get_org_id(user: Any) -> str:
    org_id = getattr(user, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org context required for security access.",
        )
    return org_id


def _is_flagged(record: AIGovernanceRecord) -> bool:
    return any(
        e.get("severity") in ("high", "critical")
        for e in (record.security_events or [])
    )


# ── Response models ───────────────────────────────────────────────────────────

class AIActivityItem(BaseModel):
    id:                    str
    created_at:            datetime
    org_id:                str
    provider:              str
    model_id:              str
    use_case:              str
    phi_redaction_status:  str
    human_review_required: bool
    human_review_status:   str
    human_reviewer_id:     Optional[str]
    workflow_id:           Optional[str]
    user_id:               Optional[str]
    security_event_count:  int
    flagged:               bool


class AIActivityResponse(BaseModel):
    total:   int
    records: list[AIActivityItem]


class EventsResponse(BaseModel):
    total:       int
    events:      list[dict[str, Any]]
    flagged_ids: list[str]


class PostureResponse(BaseModel):
    org_id:                   str
    window_hours:             int
    total_ai_calls:           int
    pending_review:           int
    flagged_records:          int
    phi_incidents:            int
    injection_attempts:       int
    approved_calls:           int
    review_completion_rate:   float
    most_used_use_case:       Optional[str]
    model_id_distribution:    dict[str, int]
    severity_distribution:    dict[str, int]


class ManualEventCreate(BaseModel):
    event_type: SecurityEventType
    detail:     str
    severity:   str = "medium"
    record_id:  Optional[str] = None


class ReviewUpdate(BaseModel):
    review_status: HumanReviewStatus
    notes:         Optional[str] = None


# ── GET /admin/security/ai-activity ──────────────────────────────────────────

@router.get("/ai-activity", response_model=AIActivityResponse)
async def get_ai_activity(
    user: AdminOrLead,
    session: AsyncSession = Depends(get_async_session),
    hours:        int  = Query(default=24,  ge=1, le=720),
    limit:        int  = Query(default=50,  ge=1, le=500),
    offset:       int  = Query(default=0,   ge=0),
    flagged_only: bool = Query(default=False),
    review_status: Optional[HumanReviewStatus] = Query(default=None),
    use_case:      Optional[AIUseCase]          = Query(default=None),
) -> AIActivityResponse:
    org_id = _get_org_id(user)
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    stmt = (
        select(AIGovernanceRecord)
        .where(
            AIGovernanceRecord.org_id     == org_id,   # ← org scope enforced
            AIGovernanceRecord.created_at >= cutoff,
        )
        .order_by(desc(AIGovernanceRecord.created_at))
    )

    if review_status:
        stmt = stmt.where(AIGovernanceRecord.human_review_status == review_status)
    if use_case:
        stmt = stmt.where(AIGovernanceRecord.use_case == use_case)

    result  = await session.execute(stmt)
    records = list(result.scalars().all())

    if flagged_only:
        records = [r for r in records if _is_flagged(r)]

    total = len(records)
    paged = records[offset : offset + limit]

    items = [
        AIActivityItem(
            id=r.id,
            created_at=r.created_at,
            org_id=r.org_id,
            provider=r.provider,
            model_id=r.model_id,
            use_case=r.use_case,
            phi_redaction_status=r.phi_redaction_status,
            human_review_required=r.human_review_required,
            human_review_status=r.human_review_status,
            human_reviewer_id=r.human_reviewer_id,
            workflow_id=r.workflow_id,
            user_id=r.user_id,
            security_event_count=len(r.security_events or []),
            flagged=_is_flagged(r),
        )
        for r in paged
    ]
    return AIActivityResponse(total=total, records=items)


# ── GET /admin/security/events ────────────────────────────────────────────────

@router.get("/events", response_model=EventsResponse)
async def get_security_events(
    user: AdminOrLead,
    session: AsyncSession = Depends(get_async_session),
    hours:      int  = Query(default=72, ge=1,  le=720),
    severity:   Optional[str]               = Query(default=None),
    event_type: Optional[SecurityEventType] = Query(default=None),
) -> EventsResponse:
    org_id = _get_org_id(user)
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    stmt = (
        select(AIGovernanceRecord)
        .where(
            AIGovernanceRecord.org_id     == org_id,
            AIGovernanceRecord.created_at >= cutoff,
        )
        .order_by(desc(AIGovernanceRecord.created_at))
    )
    result  = await session.execute(stmt)
    records = list(result.scalars().all())

    flattened: list[dict[str, Any]] = []
    flagged_ids: list[str]          = []

    for record in records:
        for evt in record.security_events or []:
            if severity   and evt.get("severity") != severity:   continue
            if event_type and evt.get("type") != event_type.value: continue

            entry = {
                "record_id":   record.id,
                "org_id":      record.org_id,
                "workflow_id": record.workflow_id,
                "user_id":     record.user_id,
                "provider":    record.provider,
                "model_id":    record.model_id,
                "use_case":    record.use_case,
                **evt,
            }
            flattened.append(entry)

            if record.id not in flagged_ids and evt.get("severity") in ("high", "critical"):
                flagged_ids.append(record.id)

    flattened.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return EventsResponse(total=len(flattened), events=flattened, flagged_ids=flagged_ids)


# ── POST /admin/security/events ───────────────────────────────────────────────

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_security_event(
    body: ManualEventCreate,
    user: AdminOrLead,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Manually log a security event. Used for admin-initiated flagging."""
    org_id = _get_org_id(user)

    if body.record_id:
        stmt = (
            select(AIGovernanceRecord)
            .where(
                AIGovernanceRecord.id     == body.record_id,
                AIGovernanceRecord.org_id == org_id,   # ← cross-org block
            )
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found in this org.")

        append_security_event(record, body.event_type, body.detail, body.severity)
        await session.commit()
        return {"status": "event_appended", "record_id": record.id}

    # No record_id — log as a standalone platform event
    # (stored as a sentinel record with no prompt/output context)
    sentinel = create_governance_record(
        org_id=org_id,
        prompt="[manual_event]",
        output="[manual_event]",
        model_id="[admin]",
        user_id=str(getattr(user, "id", "")),
    )
    append_security_event(sentinel, body.event_type, body.detail, body.severity)
    session.add(sentinel)
    await session.commit()
    return {"status": "event_created", "record_id": sentinel.id}


# ── GET /admin/security/posture ───────────────────────────────────────────────

@router.get("/posture", response_model=PostureResponse)
async def get_security_posture(
    user: AdminOrLead,
    session: AsyncSession = Depends(get_async_session),
    hours: int = Query(default=168, ge=1, le=720),   # default 7 days
) -> PostureResponse:
    org_id = _get_org_id(user)
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    stmt = (
        select(AIGovernanceRecord)
        .where(
            AIGovernanceRecord.org_id     == org_id,
            AIGovernanceRecord.created_at >= cutoff,
        )
    )
    result  = await session.execute(stmt)
    records = list(result.scalars().all())

    total           = len(records)
    pending         = sum(1 for r in records if r.human_review_status == HumanReviewStatus.PENDING)
    flagged         = sum(1 for r in records if _is_flagged(r))
    approved        = sum(1 for r in records if r.human_review_status == HumanReviewStatus.APPROVED)
    phi_incidents   = sum(
        1 for r in records
        if r.phi_redaction_status in (PHIRedactionStatus.PHI_IN_PROMPT, PHIRedactionStatus.PHI_IN_OUTPUT)
    )

    injection_attempts = 0
    severity_dist: dict[str, int] = {}
    for r in records:
        for evt in r.security_events or []:
            if evt.get("type") == SecurityEventType.PROMPT_INJECTION.value:
                injection_attempts += 1
            sev = evt.get("severity", "unknown")
            severity_dist[sev] = severity_dist.get(sev, 0) + 1

    # Use-case distribution
    use_case_dist: dict[str, int] = {}
    for r in records:
        uc = r.use_case or "other"
        use_case_dist[uc] = use_case_dist.get(uc, 0) + 1
    most_used = max(use_case_dist, key=use_case_dist.get) if use_case_dist else None

    # Model distribution
    model_dist: dict[str, int] = {}
    for r in records:
        m = r.model_id or "unknown"
        model_dist[m] = model_dist.get(m, 0) + 1

    reviewed_total = approved + sum(
        1 for r in records if r.human_review_status == HumanReviewStatus.REJECTED
    )
    completion_rate = round(reviewed_total / total, 4) if total else 0.0

    return PostureResponse(
        org_id=org_id,
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


# ── PATCH /admin/security/ai-activity/{record_id}/review ─────────────────────

@router.patch("/ai-activity/{record_id}/review")
async def update_review_status(
    record_id: str,
    body: ReviewUpdate,
    user: AdminOrLead,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    org_id = _get_org_id(user)

    stmt = (
        select(AIGovernanceRecord)
        .where(
            AIGovernanceRecord.id     == record_id,
            AIGovernanceRecord.org_id == org_id,   # ← cross-org block
        )
    )
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    record.human_review_status    = body.review_status
    record.human_reviewer_id      = str(getattr(user, "id", ""))
    record.human_review_timestamp = datetime.utcnow()
    record.human_review_notes     = body.notes

    await session.commit()
    return {"status": "updated", "record_id": record_id, "review_status": body.review_status}
