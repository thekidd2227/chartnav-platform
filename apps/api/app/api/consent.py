"""Phase 25A — audio consent route.

GET /encounters/{encounter_id}/audio-consent
    → returns current consent state (synthesized "not_recorded" if
      no record exists yet). Open to admin / clinician / reviewer /
      front_desk / technician within the same org.

PUT /encounters/{encounter_id}/audio-consent
    → upsert. Writable by admin / clinician / front_desk / technician.
      Reviewer is read-only on this surface (matches the rest of the
      patient-chart write surfaces).

Cross-org always returns 404 (no existence leak). Every write emits
a `audio_consent_updated` row to security_audit_events whose detail
is metadata-only.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.consent import (
    ConsentError,
    ConsentRecord,
    KNOWN_METHODS,
    KNOWN_STATUSES,
    get_consent,
    set_consent,
)

router = APIRouter(tags=["audio-consent"])

# Reviewer is read-only — consent capture is an admin/clinician/front-
# desk/technician activity in clinic. Reviewer cannot set or revoke.
_WRITE_ROLES: set[str] = {"admin", "clinician", "front_desk", "technician"}
_READ_ROLES: set[str] = {"admin", "clinician", "reviewer", "front_desk", "technician"}


class ConsentSetBody(BaseModel):
    status: str = Field(..., description="granted / declined / revoked / not_recorded")
    method: str = Field(..., description="verbal / written / demo_fake / unknown")
    note: Optional[str] = Field(None, max_length=500, description="operator-facing label, NOT PHI")


class ConsentResponse(BaseModel):
    encounter_id: int
    organization_id: int
    status: str
    method: str
    actor_user_id: Optional[int]
    note: Optional[str]
    recording_permitted: bool
    created_at: str
    updated_at: str


def _to_response(rec: ConsentRecord) -> ConsentResponse:
    return ConsentResponse(
        encounter_id=rec.encounter_id,
        organization_id=rec.organization_id,
        status=rec.status,
        method=rec.method,
        actor_user_id=rec.actor_user_id,
        note=rec.note,
        recording_permitted=rec.is_recording_permitted(),
        created_at=rec.created_at.isoformat(),
        updated_at=rec.updated_at.isoformat(),
    )


@router.get("/encounters/{encounter_id}/audio-consent", response_model=ConsentResponse)
def get_audio_consent(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> ConsentResponse:
    if caller.role not in _READ_ROLES:
        raise HTTPException(status_code=403, detail={"error_code": "forbidden", "reason": "role cannot read consent"})
    # Verify the encounter is in the caller's org before returning state.
    # set_consent does this check on write; get_consent synthesizes a
    # "not_recorded" record if no row exists, so we need to gate access
    # here ourselves.
    from sqlalchemy import text
    from app.db import transaction
    with transaction() as conn:
        row = conn.execute(
            text("SELECT organization_id FROM encounters WHERE id = :eid"),
            {"eid": encounter_id},
        ).mappings().first()
    if row is None or row["organization_id"] != caller.organization_id:
        # No existence leak — return 404 in both "not found" cases.
        raise HTTPException(status_code=404, detail={"error_code": "encounter_not_found", "reason": "encounter not found"})
    rec = get_consent(encounter_id=encounter_id, organization_id=caller.organization_id)
    return _to_response(rec)


@router.put("/encounters/{encounter_id}/audio-consent", response_model=ConsentResponse)
def set_audio_consent(
    encounter_id: int,
    body: ConsentSetBody,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> ConsentResponse:
    if caller.role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail={"error_code": "forbidden", "reason": "role cannot set consent"})
    if body.status not in KNOWN_STATUSES:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_status", "reason": "unknown status"})
    if body.method not in KNOWN_METHODS:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_method", "reason": "unknown method"})
    try:
        rec = set_consent(
            encounter_id=encounter_id,
            organization_id=caller.organization_id,
            status=body.status,
            method=body.method,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            note=body.note,
            request_id=getattr(request.state, "request_id", None),
        )
    except ConsentError as e:
        if e.error_code == "not_found":
            raise HTTPException(status_code=404, detail={"error_code": "encounter_not_found", "reason": "encounter not found"})
        raise HTTPException(status_code=400, detail={"error_code": e.error_code, "reason": e.reason})
    return _to_response(rec)
