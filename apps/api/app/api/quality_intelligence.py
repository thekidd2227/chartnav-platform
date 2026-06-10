"""Phase 89 — IRIS / MIPS Quality Intelligence HTTP routes.

GET  /api/v1/encounters/{encounter_id}/quality-measures
POST /api/v1/encounters/{encounter_id}/quality-measures/{measure_id}/response
GET  /api/v1/analytics/quality?program_year=

Read-only listing + provider-driven response capture + org-wide
analytics rollup. POST requires admin / clinician. Cross-org → 404.

ChartNav does NOT submit to CMS / IRIS / payers / registries. The
endpoints here are workflow surfaces, not transport.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.quality_intelligence import (
    QualityError,
    analytics_summary,
    list_for_encounter,
    record_response,
)

router = APIRouter(prefix="/api/v1", tags=["quality-intelligence"])


def _translate(exc: QualityError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class QualityResponsePayload(BaseModel):
    response_type: str = Field(..., min_length=1, max_length=24)
    exception_code: Optional[str] = Field(default=None, max_length=64)


@router.get("/encounters/{encounter_id}/quality-measures")
def get_encounter_quality_measures(
    encounter_id: int,
    program_year: Optional[int] = Query(default=None, ge=2020, le=2030),
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_for_encounter(
            encounter_id, caller, program_year=program_year
        )
    except QualityError as exc:
        raise _translate(exc)


@router.post(
    "/encounters/{encounter_id}/quality-measures/{measure_id}/response",
    status_code=201,
)
def post_quality_response(
    encounter_id: int,
    measure_id: str,
    payload: QualityResponsePayload,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return record_response(
            encounter_id,
            caller,
            measure_id=measure_id,
            payload=payload.model_dump(exclude_none=True),
        )
    except QualityError as exc:
        raise _translate(exc)


@router.get("/analytics/quality")
def get_quality_analytics(
    program_year: Optional[int] = Query(default=None, ge=2020, le=2030),
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return analytics_summary(caller, program_year=program_year)
    except QualityError as exc:
        raise _translate(exc)
