"""Phase 79 — Glaucoma Progression Cockpit HTTP route.

GET /api/v1/patients/{patient_id}/glaucoma-summary

Pure aggregator over existing structured data. Same auth + cross-org
semantics as the rest of the per-patient surface (404 on unknown /
cross-org).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.glaucoma_summary import SummaryError, build_glaucoma_summary

router = APIRouter(prefix="/api/v1", tags=["glaucoma-summary"])


@router.get("/patients/{patient_id}/glaucoma-summary")
def get_glaucoma_summary(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_glaucoma_summary(patient_id, caller)
    except SummaryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )
