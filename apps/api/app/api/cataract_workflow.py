"""Phase 80 — Cataract Surgical Workflow HTTP routes.

GET  /api/v1/patients/{patient_id}/cataract-workflow             — per-eye summary
GET  /api/v1/patients/{patient_id}/cataract-workflow/records     — raw records
POST /api/v1/patients/{patient_id}/cataract-workflow/records     — provider-entered create

All routes require an authenticated caller. POST requires admin or
clinician — technician / reviewer / front-desk are denied. Cross-org
access returns 404 (no existence leak).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.cataract_workflow import (
    WorkflowError,
    build_summary,
    create_record,
    list_records,
)

router = APIRouter(prefix="/api/v1", tags=["cataract-workflow"])


def _translate(exc: WorkflowError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class CataractRecordCreate(BaseModel):
    surgery_eye: str
    encounter_id: Optional[int] = None
    planned_surgery_date: Optional[str] = None
    biometry_study_id: Optional[int] = None
    biometry_reviewed: Optional[bool] = False
    topography_reviewed: Optional[bool] = False
    consent_status: Optional[str] = "unknown"
    target_refraction: Optional[str] = Field(default=None, max_length=64)
    lens_plan_label: Optional[str] = Field(default=None, max_length=160)
    postop_day_1_status: Optional[str] = "unknown"
    postop_week_1_status: Optional[str] = "unknown"
    postop_month_1_status: Optional[str] = "unknown"
    complications_flag: Optional[bool] = False
    complication_note: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.get("/patients/{patient_id}/cataract-workflow")
def get_summary(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_summary(patient_id, caller)
    except WorkflowError as exc:
        raise _translate(exc)


@router.get("/patients/{patient_id}/cataract-workflow/records")
def get_records(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    try:
        return list_records(patient_id, caller)
    except WorkflowError as exc:
        raise _translate(exc)


@router.post(
    "/patients/{patient_id}/cataract-workflow/records",
    status_code=201,
)
def post_record(
    patient_id: int,
    payload: CataractRecordCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_record(patient_id, caller, payload.model_dump())
    except WorkflowError as exc:
        raise _translate(exc)
