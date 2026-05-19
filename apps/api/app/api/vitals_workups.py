"""Structured vitals/workup routes.

GET    /api/v1/encounters/{encounter_id}/vitals-workups
POST   /api/v1/encounters/{encounter_id}/vitals-workups
GET    /api/v1/vitals-workups/{workup_id}
PATCH  /api/v1/vitals-workups/{workup_id}
POST   /api/v1/vitals-workups/{workup_id}/review
POST   /api/v1/vitals-workups/{workup_id}/sign

Audit detail is metadata-only: workup id, patient id, encounter id,
status, and warning count. It never includes vitals values, VA/IOP,
or technician notes.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.services.vitals_workup import (
    InvalidVitalWorkupTransition,
    VitalWorkupAttestationRequired,
    VitalWorkupImmutable,
    VitalWorkupNotFound,
    audit_detail,
    create_workup,
    get_workup,
    list_by_encounter,
    review_workup,
    sign_workup,
    update_workup,
)


router = APIRouter(prefix="/api/v1", tags=["vitals-workups"])

_READ_ROLES = {"admin", "clinician", "reviewer", "technician"}
_WRITE_ROLES = {"admin", "clinician", "technician"}
_REVIEW_ROLES = {"admin", "clinician"}

_STATUS_VALUES = {"draft", "entered", "reviewed", "signed", "superseded"}
_SOURCE_TYPES = {"technician_entry", "clinician_entry", "imported", "demo"}
_BP_POSITIONS = {"sitting", "standing", "supine", "unknown"}
_BP_SITES = {"left_arm", "right_arm", "wrist", "other", "unknown"}
_TEMP_UNITS = {"F", "C"}
_TEMP_SITES = {"oral", "temporal", "tympanic", "axillary", "other", "unknown"}
_HEIGHT_UNITS = {"in", "cm"}
_WEIGHT_UNITS = {"lb", "kg"}
_IOP_METHODS = {"applanation", "tonopen", "icare", "other", "unknown"}
_DILATION_STATUSES = {"not_dilated", "dilated", "declined", "contraindicated", "unknown"}


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_read_role(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err("role_forbidden", "clinical workup read access denied", 403)


def _require_write_role(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err("role_forbidden", "clinical workup write requires admin, clinician, or technician", 403)


def _require_review_role(caller: Caller) -> None:
    if caller.role not in _REVIEW_ROLES:
        raise _err("role_forbidden", "clinical workup review/sign requires admin or clinician", 403)


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, VitalWorkupNotFound):
        return _err("vitals_workup_not_found", "workup not found in your organization", 404)
    if isinstance(exc, VitalWorkupImmutable):
        return _err("vitals_workup_immutable", str(exc), 409)
    if isinstance(exc, InvalidVitalWorkupTransition):
        return _err("vitals_workup_invalid_transition", str(exc), 409)
    if isinstance(exc, VitalWorkupAttestationRequired):
        return _err("attestation_required", "attestation is required to sign", 422)
    raise exc


def _audit(request: Request, caller: Caller, event_type: str, workup: dict[str, Any]) -> None:
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=audit_detail(workup),
        remote_addr=(request.client.host if request.client else None),
    )


class VitalWorkupWarnings(BaseModel):
    warnings: list[str] = Field(default_factory=list)


class VitalWorkupFields(BaseModel):
    bp_systolic: Optional[int] = Field(default=None, gt=0)
    bp_diastolic: Optional[int] = Field(default=None, gt=0)
    bp_position: Optional[str] = None
    bp_site: Optional[str] = None
    temperature_value: Optional[float] = Field(default=None, gt=0)
    temperature_unit: str = "F"
    temperature_site: Optional[str] = None
    pulse: Optional[int] = Field(default=None, gt=0)
    respiratory_rate: Optional[int] = Field(default=None, gt=0)
    oxygen_saturation: Optional[int] = Field(default=None, ge=0, le=100)
    height_value: Optional[float] = Field(default=None, gt=0)
    height_unit: str = "in"
    weight_value: Optional[float] = Field(default=None, gt=0)
    weight_unit: str = "lb"
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)
    visual_acuity_od: Optional[str] = Field(default=None, max_length=64)
    visual_acuity_os: Optional[str] = Field(default=None, max_length=64)
    visual_acuity_ou: Optional[str] = Field(default=None, max_length=64)
    iop_od: Optional[float] = Field(default=None, gt=0)
    iop_os: Optional[float] = Field(default=None, gt=0)
    iop_method: Optional[str] = None
    dilation_status: Optional[str] = None
    dilation_time: Optional[str] = None
    allergies_reviewed: bool = False
    medications_reviewed: bool = False
    technician_notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("bp_position")
    @classmethod
    def _bp_position(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _BP_POSITIONS, "bp_position")

    @field_validator("bp_site")
    @classmethod
    def _bp_site(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _BP_SITES, "bp_site")

    @field_validator("temperature_unit")
    @classmethod
    def _temperature_unit(cls, value: str) -> str:
        return _check_enum(value, _TEMP_UNITS, "temperature_unit") or "F"

    @field_validator("temperature_site")
    @classmethod
    def _temperature_site(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _TEMP_SITES, "temperature_site")

    @field_validator("height_unit")
    @classmethod
    def _height_unit(cls, value: str) -> str:
        return _check_enum(value, _HEIGHT_UNITS, "height_unit") or "in"

    @field_validator("weight_unit")
    @classmethod
    def _weight_unit(cls, value: str) -> str:
        return _check_enum(value, _WEIGHT_UNITS, "weight_unit") or "lb"

    @field_validator("iop_method")
    @classmethod
    def _iop_method(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _IOP_METHODS, "iop_method")

    @field_validator("dilation_status")
    @classmethod
    def _dilation_status(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _DILATION_STATUSES, "dilation_status")


def _check_enum(value: Optional[str], allowed: set[str], field: str) -> Optional[str]:
    if value in (None, ""):
        return None
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")
    return value


class VitalWorkupCreate(VitalWorkupFields):
    status: str = "entered"
    source_type: str = "technician_entry"

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in {"draft", "entered"}:
            raise ValueError("new workup status must be draft or entered")
        return value

    @field_validator("source_type")
    @classmethod
    def _source_type(cls, value: str) -> str:
        if value not in _SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {sorted(_SOURCE_TYPES)}")
        return value


class VitalWorkupUpdate(BaseModel):
    status: Optional[str] = None
    source_type: Optional[str] = None
    bp_systolic: Optional[int] = Field(default=None, gt=0)
    bp_diastolic: Optional[int] = Field(default=None, gt=0)
    bp_position: Optional[str] = None
    bp_site: Optional[str] = None
    temperature_value: Optional[float] = Field(default=None, gt=0)
    temperature_unit: Optional[str] = None
    temperature_site: Optional[str] = None
    pulse: Optional[int] = Field(default=None, gt=0)
    respiratory_rate: Optional[int] = Field(default=None, gt=0)
    oxygen_saturation: Optional[int] = Field(default=None, ge=0, le=100)
    height_value: Optional[float] = Field(default=None, gt=0)
    height_unit: Optional[str] = None
    weight_value: Optional[float] = Field(default=None, gt=0)
    weight_unit: Optional[str] = None
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)
    visual_acuity_od: Optional[str] = Field(default=None, max_length=64)
    visual_acuity_os: Optional[str] = Field(default=None, max_length=64)
    visual_acuity_ou: Optional[str] = Field(default=None, max_length=64)
    iop_od: Optional[float] = Field(default=None, gt=0)
    iop_os: Optional[float] = Field(default=None, gt=0)
    iop_method: Optional[str] = None
    dilation_status: Optional[str] = None
    dilation_time: Optional[str] = None
    allergies_reviewed: Optional[bool] = None
    medications_reviewed: Optional[bool] = None
    technician_notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def _status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in _STATUS_VALUES:
            raise ValueError(f"status must be one of {sorted(_STATUS_VALUES)}")
        return value

    @field_validator("source_type")
    @classmethod
    def _source_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in _SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {sorted(_SOURCE_TYPES)}")
        return value

    @field_validator("bp_position")
    @classmethod
    def _bp_position(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _BP_POSITIONS, "bp_position")

    @field_validator("bp_site")
    @classmethod
    def _bp_site(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _BP_SITES, "bp_site")

    @field_validator("temperature_unit")
    @classmethod
    def _temperature_unit(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _TEMP_UNITS, "temperature_unit")

    @field_validator("temperature_site")
    @classmethod
    def _temperature_site(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _TEMP_SITES, "temperature_site")

    @field_validator("height_unit")
    @classmethod
    def _height_unit(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _HEIGHT_UNITS, "height_unit")

    @field_validator("weight_unit")
    @classmethod
    def _weight_unit(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _WEIGHT_UNITS, "weight_unit")

    @field_validator("iop_method")
    @classmethod
    def _iop_method(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _IOP_METHODS, "iop_method")

    @field_validator("dilation_status")
    @classmethod
    def _dilation_status(cls, value: Optional[str]) -> Optional[str]:
        return _check_enum(value, _DILATION_STATUSES, "dilation_status")


class VitalWorkupReviewRequest(BaseModel):
    reviewed: bool = True


class VitalWorkupSignRequest(BaseModel):
    attested: bool


class VitalWorkupRead(BaseModel):
    id: int
    organization_id: int
    encounter_id: Optional[int]
    patient_id: int
    status: str
    source_type: str
    bp_systolic: Optional[int]
    bp_diastolic: Optional[int]
    bp_position: Optional[str]
    bp_site: Optional[str]
    temperature_value: Optional[float]
    temperature_unit: str
    temperature_site: Optional[str]
    pulse: Optional[int]
    respiratory_rate: Optional[int]
    oxygen_saturation: Optional[int]
    height_value: Optional[float]
    height_unit: str
    weight_value: Optional[float]
    weight_unit: str
    bmi: Optional[float]
    pain_score: Optional[int]
    visual_acuity_od: Optional[str]
    visual_acuity_os: Optional[str]
    visual_acuity_ou: Optional[str]
    iop_od: Optional[float]
    iop_os: Optional[float]
    iop_method: Optional[str]
    dilation_status: Optional[str]
    dilation_time: Optional[str]
    allergies_reviewed: bool
    medications_reviewed: bool
    technician_notes: Optional[str]
    warnings_json: list[str]
    reviewed_by_user_id: Optional[int]
    signed_by_user_id: Optional[int]
    signed_at: Optional[Any]
    created_by_user_id: int
    created_at: Optional[Any]
    updated_at: Optional[Any]


@router.get("/encounters/{encounter_id}/vitals-workups", response_model=list[VitalWorkupRead])
def list_vitals_workups(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_read_role(caller)
    try:
        return list_by_encounter(encounter_id, organization_id=caller.organization_id)
    except Exception as exc:
        raise _translate(exc)


@router.post(
    "/encounters/{encounter_id}/vitals-workups",
    status_code=status.HTTP_201_CREATED,
    response_model=VitalWorkupRead,
)
def create_vitals_workup(
    encounter_id: int,
    payload: VitalWorkupCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    try:
        workup = create_workup(
            encounter_id,
            organization_id=caller.organization_id,
            created_by_user_id=caller.user_id,
            values=payload.model_dump(),
        )
    except Exception as exc:
        raise _translate(exc)
    _audit(request, caller, "vitals_workup_created", workup)
    return workup


@router.get("/vitals-workups/{workup_id}", response_model=VitalWorkupRead)
def get_vitals_workup(
    workup_id: int,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_read_role(caller)
    try:
        return get_workup(workup_id, organization_id=caller.organization_id)
    except Exception as exc:
        raise _translate(exc)


@router.patch("/vitals-workups/{workup_id}", response_model=VitalWorkupRead)
def patch_vitals_workup(
    workup_id: int,
    payload: VitalWorkupUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    try:
        workup = update_workup(
            workup_id,
            organization_id=caller.organization_id,
            values=payload.model_dump(exclude_unset=True),
        )
    except Exception as exc:
        raise _translate(exc)
    _audit(request, caller, "vitals_workup_updated", workup)
    return workup


@router.post("/vitals-workups/{workup_id}/review", response_model=VitalWorkupRead)
def review_vitals_workup(
    workup_id: int,
    payload: VitalWorkupReviewRequest,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_review_role(caller)
    if payload.reviewed is not True:
        raise _err("review_confirmation_required", "reviewed must be true", 422)
    try:
        workup = review_workup(
            workup_id,
            organization_id=caller.organization_id,
            reviewed_by_user_id=caller.user_id,
        )
    except Exception as exc:
        raise _translate(exc)
    _audit(request, caller, "vitals_workup_reviewed", workup)
    return workup


@router.post("/vitals-workups/{workup_id}/sign", response_model=VitalWorkupRead)
def sign_vitals_workup(
    workup_id: int,
    payload: VitalWorkupSignRequest,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_review_role(caller)
    try:
        workup = sign_workup(
            workup_id,
            organization_id=caller.organization_id,
            signed_by_user_id=caller.user_id,
            attested=payload.attested,
        )
    except Exception as exc:
        raise _translate(exc)
    _audit(request, caller, "vitals_workup_signed", workup)
    return workup
