"""Phase 85 — Ophthalmic Medication Safety & Adherence Engine HTTP routes.

GET    /api/v1/patients/{patient_id}/medications
POST   /api/v1/encounters/{encounter_id}/medications
PATCH  /api/v1/medications/{medication_id}/discontinue
POST   /api/v1/medications/{medication_id}/refills
POST   /api/v1/patients/{patient_id}/medication-allergies

Provider-entered surface; only admin or clinician can record / discontinue.
Reviewer / technician / front_desk get 403. Cross-org access returns 404
(no existence leak).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.medications import (
    MedicationError,
    create_allergy,
    create_medication,
    create_refill,
    discontinue_medication,
    list_for_patient,
)

router = APIRouter(prefix="/api/v1", tags=["medications"])


def _translate(exc: MedicationError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class MedicationCreate(BaseModel):
    medication_name: str = Field(..., min_length=1, max_length=128)
    medication_class: str = Field(..., min_length=1, max_length=48)
    route: str = Field(..., min_length=1, max_length=16)
    laterality: str = Field(..., min_length=1, max_length=4)
    dose_per_day: int = Field(..., ge=0, le=24)
    preservative_flag: bool = Field(default=False)
    started_on: Optional[str] = Field(default=None)
    discontinued_on: Optional[str] = Field(default=None)
    prescriber_display_name: Optional[str] = Field(
        default=None, max_length=128
    )


class MedicationDiscontinue(BaseModel):
    discontinued_on: Optional[str] = Field(default=None)


class RefillCreate(BaseModel):
    refill_date: Optional[str] = Field(default=None)
    expected_days_supply: int = Field(..., ge=1, le=365)
    encounter_id: Optional[int] = Field(default=None, ge=1)


class AllergyCreate(BaseModel):
    substance: str = Field(..., min_length=1, max_length=128)
    reaction_type: str = Field(..., min_length=1, max_length=24)
    severity: str = Field(..., min_length=1, max_length=16)


@router.get("/patients/{patient_id}/medications")
def get_patient_medications(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_for_patient(patient_id, caller)
    except MedicationError as exc:
        raise _translate(exc)


@router.post(
    "/encounters/{encounter_id}/medications",
    status_code=201,
)
def post_encounter_medication(
    encounter_id: int,
    payload: MedicationCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_medication(
            encounter_id, caller, payload.model_dump(exclude_none=True)
        )
    except MedicationError as exc:
        raise _translate(exc)


@router.patch("/medications/{medication_id}/discontinue")
def patch_medication_discontinue(
    medication_id: int,
    payload: MedicationDiscontinue,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return discontinue_medication(
            medication_id, caller, payload.model_dump(exclude_none=True)
        )
    except MedicationError as exc:
        raise _translate(exc)


@router.post(
    "/medications/{medication_id}/refills",
    status_code=201,
)
def post_medication_refill(
    medication_id: int,
    payload: RefillCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_refill(
            medication_id, caller, payload.model_dump(exclude_none=True)
        )
    except MedicationError as exc:
        raise _translate(exc)


@router.post(
    "/patients/{patient_id}/medication-allergies",
    status_code=201,
)
def post_patient_allergy(
    patient_id: int,
    payload: AllergyCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_allergy(
            patient_id, caller, payload.model_dump(exclude_none=True)
        )
    except MedicationError as exc:
        raise _translate(exc)
