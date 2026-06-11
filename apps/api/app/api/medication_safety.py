"""Phase 90 — Ophthalmic Medication Safety & Adherence HTTP routes.

GET   /api/v1/patients/{patient_id}/medication-safety
POST  /api/v1/encounters/{encounter_id}/ophthalmic-medications
POST  /api/v1/medication-safety-events/{event_id}/acknowledge
GET   /api/v1/analytics/medication-safety

Read-only listing + provider-driven medication entry + provider-
driven event acknowledgement + org-wide analytics. POST/acknowledge
require admin / clinician. Cross-org access returns 404 (no
existence leak).

ChartNav does NOT prescribe, does NOT recommend a medication change,
does NOT recommend treatment, surgery, or escalation, and does NOT
submit to pharmacies / payers / EHRs.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.medication_safety import (
    MedicationSafetyError,
    acknowledge_event,
    analytics_summary,
    create_medication,
    list_for_patient,
)

router = APIRouter(prefix="/api/v1", tags=["medication-safety"])


def _translate(exc: MedicationSafetyError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class OphthalmicMedicationCreate(BaseModel):
    medication_name: str = Field(..., min_length=1, max_length=128)
    medication_class: str = Field(..., min_length=1, max_length=48)
    route: str = Field(..., min_length=1, max_length=16)
    laterality: str = Field(..., min_length=1, max_length=4)
    dose_per_day: int = Field(..., ge=0, le=24)
    preservative_type: Optional[str] = Field(default="unknown", max_length=24)
    started_on: Optional[str] = Field(default=None)
    discontinued_on: Optional[str] = Field(default=None)
    last_fill_date: Optional[str] = Field(default=None)
    days_supply: Optional[int] = Field(default=None, ge=1, le=365)


@router.get("/patients/{patient_id}/medication-safety")
def get_patient_medication_safety(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_for_patient(patient_id, caller)
    except MedicationSafetyError as exc:
        raise _translate(exc)


@router.post(
    "/encounters/{encounter_id}/ophthalmic-medications",
    status_code=201,
)
def post_ophthalmic_medication(
    encounter_id: int,
    payload: OphthalmicMedicationCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_medication(
            encounter_id,
            caller,
            payload.model_dump(exclude_none=True),
        )
    except MedicationSafetyError as exc:
        raise _translate(exc)


@router.post("/medication-safety-events/{event_id}/acknowledge")
def post_acknowledge_event(
    event_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return acknowledge_event(event_id, caller)
    except MedicationSafetyError as exc:
        raise _translate(exc)


@router.get("/analytics/medication-safety")
def get_medication_safety_analytics(
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return analytics_summary(caller)
    except MedicationSafetyError as exc:
        raise _translate(exc)
