"""Phase 21A — Retina + Glaucoma specialty tracking endpoints.

Read + provider-reviewed write surface for the five tables added by
``e6f7a8b9c0d1_phase_21a_specialty_tracking``:

  * ``retina_tracking``
  * ``retina_injection_events``
  * ``glaucoma_tracking``
  * ``glaucoma_iop_measurements``
  * ``glaucoma_visual_field_tests``

Permission model
----------------

  * **admin**       — full read + write
  * **clinician**   — full read + write
  * **technician**  — read everywhere; create-only on the discrete
                      measurement events (retina injection, IOP, VF)
  * **reviewer**    — read-only across all five resources
  * **front_desk**  — no access (clinical surface)

Audit
-----
Every create / patch records a metadata-only audit row. ``detail``
strings include only IDs, eye, status, and the type of change.
``provider_assessment``, ``notes``, ``result_summary``,
``medication_plan``, ``injection_history_summary``, and other
clinical body fields are NEVER included in the audit detail.

PHI / cross-org safety
----------------------
Patients and encounters are resolved via
``_resolve_patient_in_org`` / ``_resolve_encounter_in_org`` which
return 404 (not 403) on cross-org miss, preserving the
no-existence-leak invariant.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_all, fetch_one, insert_returning_id, transaction


router = APIRouter()


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

_EYE_OD_OS_OU = {"OD", "OS", "OU"}
_EYE_OD_OS = {"OD", "OS"}
_REVIEW_STATUSES = {"draft", "needs_review", "reviewed", "archived"}

_ROLE_ADMIN = "admin"
_ROLE_CLINICIAN = "clinician"
_ROLE_REVIEWER = "reviewer"
_ROLE_TECHNICIAN = "technician"
_ROLE_FRONT_DESK = "front_desk"

# Tracking rows — full lifecycle (create + patch) is admin/clinician.
_TRACKING_WRITE_ROLES = {_ROLE_ADMIN, _ROLE_CLINICIAN}

# Discrete measurement events — admin/clinician + technician
# (the technician is the operator capturing IOP / VF / injection
# events, but never writing the longitudinal review row).
_MEASUREMENT_WRITE_ROLES = {
    _ROLE_ADMIN,
    _ROLE_CLINICIAN,
    _ROLE_TECHNICIAN,
}

# Read access — everyone but front_desk. Front desk is a
# non-clinical surface; specialty tracking is a clinical surface.
_READ_ROLES = {
    _ROLE_ADMIN,
    _ROLE_CLINICIAN,
    _ROLE_REVIEWER,
    _ROLE_TECHNICIAN,
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_read_access(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err(
            "specialty_role_forbidden",
            f"role {caller.role!r} cannot read specialty tracking",
            403,
        )


def _require_tracking_write(caller: Caller) -> None:
    if caller.role not in _TRACKING_WRITE_ROLES:
        raise _err(
            "specialty_role_forbidden",
            f"role {caller.role!r} cannot write specialty tracking; "
            "requires admin or clinician",
            403,
        )


def _require_measurement_write(caller: Caller) -> None:
    if caller.role not in _MEASUREMENT_WRITE_ROLES:
        raise _err(
            "specialty_role_forbidden",
            f"role {caller.role!r} cannot create specialty measurement; "
            "requires admin, clinician, or technician",
            403,
        )


def _resolve_patient_in_org(patient_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM patients WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "patient_not_found",
            "patient not found in your organization",
            404,
        )
    return int(row["id"])


def _resolve_encounter_in_org(
    encounter_id: Optional[int], caller: Caller
) -> Optional[int]:
    if encounter_id is None:
        return None
    row = fetch_one(
        "SELECT id FROM encounters WHERE id = :id AND organization_id = :org",
        {"id": encounter_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return int(row["id"])


def _validate_eye(eye: str, *, allow_ou: bool = True) -> str:
    allowed = _EYE_OD_OS_OU if allow_ou else _EYE_OD_OS
    if eye not in allowed:
        raise _err(
            "invalid_eye",
            f"eye must be one of {sorted(allowed)}",
            400,
        )
    return eye


def _validate_review_status(value: str) -> str:
    if value not in _REVIEW_STATUSES:
        raise _err(
            "invalid_review_status",
            f"review_status must be one of {sorted(_REVIEW_STATUSES)}",
            400,
        )
    return value


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    detail: str,
) -> None:
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


# ---------------------------------------------------------------------
# Pydantic shapes
# ---------------------------------------------------------------------


class RetinaTrackingCreate(BaseModel):
    eye: str = Field(..., min_length=2, max_length=2)
    condition: str = Field(..., min_length=1, max_length=200)
    severity: Optional[str] = Field(default=None, max_length=64)
    last_oct_at: Optional[str] = None
    last_fundus_at: Optional[str] = None
    injection_history_summary: Optional[str] = Field(
        default=None, max_length=4000
    )
    follow_up_interval: Optional[str] = Field(default=None, max_length=64)
    provider_assessment: Optional[str] = Field(default=None, max_length=8000)
    review_status: str = Field(default="draft", max_length=32)
    encounter_id: Optional[int] = None


class RetinaTrackingUpdate(BaseModel):
    severity: Optional[str] = Field(default=None, max_length=64)
    last_oct_at: Optional[str] = None
    last_fundus_at: Optional[str] = None
    injection_history_summary: Optional[str] = Field(
        default=None, max_length=4000
    )
    follow_up_interval: Optional[str] = Field(default=None, max_length=64)
    provider_assessment: Optional[str] = Field(default=None, max_length=8000)
    review_status: Optional[str] = Field(default=None, max_length=32)


class RetinaInjectionCreate(BaseModel):
    eye: str = Field(..., min_length=2, max_length=2)
    medication: Optional[str] = Field(default=None, max_length=200)
    procedure_date: Optional[str] = None
    laterality: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = Field(default=None, max_length=4000)
    encounter_id: Optional[int] = None


class GlaucomaTrackingCreate(BaseModel):
    eye: str = Field(..., min_length=2, max_length=2)
    glaucoma_type: Optional[str] = Field(default=None, max_length=120)
    target_iop: Optional[float] = Field(default=None, ge=0, le=80)
    latest_iop: Optional[float] = Field(default=None, ge=0, le=80)
    cup_to_disc_ratio: Optional[float] = Field(default=None, ge=0, le=1)
    rnfl_status: Optional[str] = Field(default=None, max_length=120)
    visual_field_status: Optional[str] = Field(default=None, max_length=120)
    medication_plan: Optional[str] = Field(default=None, max_length=4000)
    progression_risk_label: Optional[str] = Field(default=None, max_length=64)
    provider_assessment: Optional[str] = Field(default=None, max_length=8000)
    review_status: str = Field(default="draft", max_length=32)
    encounter_id: Optional[int] = None


class GlaucomaTrackingUpdate(BaseModel):
    glaucoma_type: Optional[str] = Field(default=None, max_length=120)
    target_iop: Optional[float] = Field(default=None, ge=0, le=80)
    latest_iop: Optional[float] = Field(default=None, ge=0, le=80)
    cup_to_disc_ratio: Optional[float] = Field(default=None, ge=0, le=1)
    rnfl_status: Optional[str] = Field(default=None, max_length=120)
    visual_field_status: Optional[str] = Field(default=None, max_length=120)
    medication_plan: Optional[str] = Field(default=None, max_length=4000)
    progression_risk_label: Optional[str] = Field(default=None, max_length=64)
    provider_assessment: Optional[str] = Field(default=None, max_length=8000)
    review_status: Optional[str] = Field(default=None, max_length=32)


class IopMeasurementCreate(BaseModel):
    eye: str = Field(..., min_length=2, max_length=2)
    iop_value: float = Field(..., ge=0, le=80)
    measured_at: Optional[str] = None
    method: Optional[str] = Field(default=None, max_length=64)
    encounter_id: Optional[int] = None


class VisualFieldCreate(BaseModel):
    eye: str = Field(..., min_length=2, max_length=2)
    test_type: Optional[str] = Field(default=None, max_length=120)
    performed_at: Optional[str] = None
    result_summary: Optional[str] = Field(default=None, max_length=8000)
    reliability: Optional[str] = Field(default=None, max_length=64)
    progression_flag: Optional[str] = Field(default=None, max_length=64)
    encounter_id: Optional[int] = None


# ---------------------------------------------------------------------
# Row serializers — explicit whitelists; safe to return as-is.
# ---------------------------------------------------------------------


def _row_to_dict(row: dict) -> dict:
    """Coerce sqlite/postgres datetimes into JSON-friendly strings."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        out[k] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


# ---------------------------------------------------------------------
# Retina tracking
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/retina")
def list_retina_tracking(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM retina_tracking "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/retina",
    status_code=status.HTTP_201_CREATED,
)
def create_retina_tracking(
    patient_id: int,
    payload: RetinaTrackingCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_tracking_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    eye = _validate_eye(payload.eye, allow_ou=True)
    review_status = _validate_review_status(payload.review_status)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "retina_tracking",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "eye": eye,
                "condition": payload.condition,
                "severity": payload.severity,
                "last_oct_at": payload.last_oct_at,
                "last_fundus_at": payload.last_fundus_at,
                "injection_history_summary": payload.injection_history_summary,
                "follow_up_interval": payload.follow_up_interval,
                "provider_assessment": payload.provider_assessment,
                "review_status": review_status,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM retina_tracking WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="retina_tracking_created",
        detail=(
            f"retina_tracking_id={new_id} patient_id={pid} "
            f"eye={eye} review_status={review_status}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/patients/{patient_id}/retina/{record_id}")
def patch_retina_tracking(
    patient_id: int,
    record_id: int,
    payload: RetinaTrackingUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_tracking_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    existing = fetch_one(
        "SELECT * FROM retina_tracking "
        "WHERE id = :id AND organization_id = :org AND patient_id = :pid",
        {"id": record_id, "org": caller.organization_id, "pid": pid},
    )
    if not existing:
        raise _err(
            "retina_tracking_not_found",
            "retina tracking row not found in your organization",
            404,
        )

    sets: dict[str, Any] = {}
    for field in (
        "severity",
        "last_oct_at",
        "last_fundus_at",
        "injection_history_summary",
        "follow_up_interval",
        "provider_assessment",
    ):
        value = getattr(payload, field)
        if value is not None:
            sets[field] = value
    if payload.review_status is not None:
        sets["review_status"] = _validate_review_status(payload.review_status)

    if not sets:
        return _row_to_dict(existing)

    sets["updated_by_user_id"] = caller.user_id
    sets["updated_at"] = "CURRENT_TIMESTAMP"

    set_clauses = []
    params: dict[str, Any] = {"id": record_id}
    for k, v in sets.items():
        if k == "updated_at":
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            continue
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE retina_tracking SET {', '.join(set_clauses)} "
                "WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM retina_tracking WHERE id = :id"),
            {"id": record_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="retina_tracking_updated",
        detail=(
            f"retina_tracking_id={record_id} patient_id={pid} "
            f"fields_changed={sorted(sets.keys())} "
            f"review_status={row['review_status']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Retina injection events
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/retina/injections")
def list_retina_injections(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM retina_injection_events "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/retina/injections",
    status_code=status.HTTP_201_CREATED,
)
def create_retina_injection(
    patient_id: int,
    payload: RetinaInjectionCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_measurement_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    eye = _validate_eye(payload.eye, allow_ou=True)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "retina_injection_events",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "eye": eye,
                "medication": payload.medication,
                "procedure_date": payload.procedure_date,
                "laterality": payload.laterality,
                "notes": payload.notes,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM retina_injection_events WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="retina_injection_created",
        detail=(
            f"retina_injection_id={new_id} patient_id={pid} eye={eye}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Glaucoma tracking
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/glaucoma")
def list_glaucoma_tracking(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM glaucoma_tracking "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/glaucoma",
    status_code=status.HTTP_201_CREATED,
)
def create_glaucoma_tracking(
    patient_id: int,
    payload: GlaucomaTrackingCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_tracking_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    eye = _validate_eye(payload.eye, allow_ou=True)
    review_status = _validate_review_status(payload.review_status)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "glaucoma_tracking",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "eye": eye,
                "glaucoma_type": payload.glaucoma_type,
                "target_iop": payload.target_iop,
                "latest_iop": payload.latest_iop,
                "cup_to_disc_ratio": payload.cup_to_disc_ratio,
                "rnfl_status": payload.rnfl_status,
                "visual_field_status": payload.visual_field_status,
                "medication_plan": payload.medication_plan,
                "progression_risk_label": payload.progression_risk_label,
                "provider_assessment": payload.provider_assessment,
                "review_status": review_status,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM glaucoma_tracking WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="glaucoma_tracking_created",
        detail=(
            f"glaucoma_tracking_id={new_id} patient_id={pid} "
            f"eye={eye} review_status={review_status}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/patients/{patient_id}/glaucoma/{record_id}")
def patch_glaucoma_tracking(
    patient_id: int,
    record_id: int,
    payload: GlaucomaTrackingUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_tracking_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    existing = fetch_one(
        "SELECT * FROM glaucoma_tracking "
        "WHERE id = :id AND organization_id = :org AND patient_id = :pid",
        {"id": record_id, "org": caller.organization_id, "pid": pid},
    )
    if not existing:
        raise _err(
            "glaucoma_tracking_not_found",
            "glaucoma tracking row not found in your organization",
            404,
        )

    sets: dict[str, Any] = {}
    for field in (
        "glaucoma_type",
        "target_iop",
        "latest_iop",
        "cup_to_disc_ratio",
        "rnfl_status",
        "visual_field_status",
        "medication_plan",
        "progression_risk_label",
        "provider_assessment",
    ):
        value = getattr(payload, field)
        if value is not None:
            sets[field] = value
    if payload.review_status is not None:
        sets["review_status"] = _validate_review_status(payload.review_status)

    if not sets:
        return _row_to_dict(existing)

    sets["updated_by_user_id"] = caller.user_id

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": record_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE glaucoma_tracking SET {', '.join(set_clauses)} "
                "WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM glaucoma_tracking WHERE id = :id"),
            {"id": record_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="glaucoma_tracking_updated",
        detail=(
            f"glaucoma_tracking_id={record_id} patient_id={pid} "
            f"fields_changed={sorted(sets.keys())} "
            f"review_status={row['review_status']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Glaucoma IOP measurements
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/glaucoma/iop")
def list_iop_measurements(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    # SQLite lacks `NULLS LAST` on every dialect; use COALESCE
    # against created_at for a portable trend-friendly ordering.
    rows = fetch_all(
        "SELECT * FROM glaucoma_iop_measurements "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY COALESCE(measured_at, created_at) DESC, id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/glaucoma/iop",
    status_code=status.HTTP_201_CREATED,
)
def create_iop_measurement(
    patient_id: int,
    payload: IopMeasurementCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_measurement_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    eye = _validate_eye(payload.eye, allow_ou=False)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "glaucoma_iop_measurements",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "eye": eye,
                "iop_value": payload.iop_value,
                "measured_at": payload.measured_at,
                "method": payload.method,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM glaucoma_iop_measurements WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="glaucoma_iop_created",
        detail=(
            f"iop_id={new_id} patient_id={pid} eye={eye} "
            f"value={payload.iop_value}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Glaucoma visual field tests
# ---------------------------------------------------------------------


@router.get("/patients/{patient_id}/glaucoma/visual-fields")
def list_visual_fields(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_access(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM glaucoma_visual_field_tests "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY COALESCE(performed_at, created_at) DESC, id DESC",
        {"org": caller.organization_id, "pid": pid},
    )
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/patients/{patient_id}/glaucoma/visual-fields",
    status_code=status.HTTP_201_CREATED,
)
def create_visual_field(
    patient_id: int,
    payload: VisualFieldCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_measurement_write(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    eye = _validate_eye(payload.eye, allow_ou=True)
    eid = _resolve_encounter_in_org(payload.encounter_id, caller)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "glaucoma_visual_field_tests",
            {
                "organization_id": caller.organization_id,
                "patient_id": pid,
                "encounter_id": eid,
                "eye": eye,
                "test_type": payload.test_type,
                "performed_at": payload.performed_at,
                "result_summary": payload.result_summary,
                "reliability": payload.reliability,
                "progression_flag": payload.progression_flag,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM glaucoma_visual_field_tests WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="glaucoma_visual_field_created",
        detail=(
            f"vf_id={new_id} patient_id={pid} eye={eye} "
            f"reliability={payload.reliability or ''}"
        ),
    )
    return _row_to_dict(dict(row))
