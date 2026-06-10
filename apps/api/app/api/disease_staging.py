"""Phase 84 — Disease Staging Protocol Engine HTTP routes.

GET  /api/v1/patients/{patient_id}/disease-staging
POST /api/v1/encounters/{encounter_id}/disease-staging

Read-only listing and provider-entered creation. POST requires admin
or clinician — technician / reviewer / front-desk are denied. Cross-org
access returns 404 (no existence leak).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.disease_staging import (
    StagingError,
    create_stage,
    list_for_patient,
)

router = APIRouter(prefix="/api/v1", tags=["disease-staging"])


def _translate(exc: StagingError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class DiseaseStageCreate(BaseModel):
    diagnosis_code: str = Field(..., min_length=1, max_length=64)
    staging_system: str = Field(..., min_length=1, max_length=48)
    stage_value: str = Field(..., min_length=1, max_length=64)
    prior_stage: Optional[str] = Field(default=None, max_length=64)


@router.get("/patients/{patient_id}/disease-staging")
def get_patient_staging(
    patient_id: int,
    diagnosis_code: Optional[str] = Query(default=None, max_length=64),
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_for_patient(
            patient_id, caller, diagnosis_code=diagnosis_code
        )
    except StagingError as exc:
        raise _translate(exc)


@router.post(
    "/encounters/{encounter_id}/disease-staging",
    status_code=201,
)
def post_encounter_staging(
    encounter_id: int,
    payload: DiseaseStageCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_stage(
            encounter_id, caller, payload.model_dump(exclude_none=True)
        )
    except StagingError as exc:
        raise _translate(exc)
