"""Phase 76 — Retina Visit Summary HTTP route.

GET /api/v1/encounters/{encounter_id}/retina-visit-summary

Returns the cross-artifact metadata-only aggregator built by
``app.services.retina_visit_summary``. Read-only. Cross-org access
returns 404 (matches the rest of the encounter surface).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.retina_visit_summary import SummaryError, build_summary

router = APIRouter(prefix="/api/v1", tags=["retina-visit-summary"])


@router.get("/encounters/{encounter_id}/retina-visit-summary")
def get_retina_visit_summary(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_summary(encounter_id, caller)
    except SummaryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )
