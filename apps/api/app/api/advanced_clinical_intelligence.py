"""Phase 92 — Advanced Clinical Intelligence Layer HTTP routes.

GET /api/v1/encounters/{encounter_id}/advanced-clinical-intelligence

Read-only longitudinal projection. Cross-org → 404 (no existence leak).
ChartNav does NOT diagnose, does NOT interpret images, does NOT
recommend treatment, and does NOT submit externally.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.advanced_clinical_intelligence import (
    AdvancedClinicalIntelligenceError,
    build_advanced_clinical_intelligence,
)

router = APIRouter(prefix="/api/v1", tags=["advanced-clinical-intelligence"])


def _translate(exc: AdvancedClinicalIntelligenceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


@router.get(
    "/encounters/{encounter_id}/advanced-clinical-intelligence"
)
def get_advanced_clinical_intelligence(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_advanced_clinical_intelligence(encounter_id, caller)
    except AdvancedClinicalIntelligenceError as exc:
        raise _translate(exc)
