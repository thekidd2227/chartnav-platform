"""Phase 78 — Anti-VEGF injection HTTP routes.

GET    /api/v1/patients/{patient_id}/anti-vegf-injections     — history
POST   /api/v1/patients/{patient_id}/anti-vegf-injections     — record one
GET    /api/v1/anti-vegf/readiness-queue                       — org-scoped queue

All routes require an authenticated caller via require_caller. Cross-org
access returns 404 (no existence leak). Mutations require admin /
clinician / technician — reviewer and front-desk are read-only.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.anti_vegf_injections import (
    InjectionError,
    build_readiness_queue,
    create_injection,
    list_history,
)

router = APIRouter(prefix="/api/v1", tags=["anti-vegf-injections"])


def _translate(exc: InjectionError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class InjectionCreate(BaseModel):
    eye: str
    drug_label: Optional[str] = "anti_vegf_generic"
    injection_date: str
    interval_weeks: Optional[int] = Field(default=None, ge=1, le=52)
    next_due_date: Optional[str] = None
    authorization_status: Optional[str] = "unknown"
    authorization_expires_on: Optional[str] = None
    lot_number: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = None
    encounter_id: Optional[int] = None


@router.get(
    "/patients/{patient_id}/anti-vegf-injections",
    response_model_exclude_none=False,
)
def get_history(
    patient_id: int,
    eye: Optional[str] = Query(default=None, pattern="^(OD|OS)$"),
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_history(patient_id, caller, eye=eye)
    except InjectionError as exc:
        raise _translate(exc)


@router.post(
    "/patients/{patient_id}/anti-vegf-injections",
    status_code=201,
)
def post_injection(
    patient_id: int,
    payload: InjectionCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return create_injection(patient_id, caller, payload.model_dump())
    except InjectionError as exc:
        raise _translate(exc)


@router.get("/anti-vegf/readiness-queue")
def get_readiness_queue(
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_readiness_queue(caller)
    except InjectionError as exc:
        raise _translate(exc)
