"""Phase 60 — Structured Vitals & Technician Workup HTTP routes.

GET    /api/v1/encounters/{encounter_id}/vitals-workups
POST   /api/v1/encounters/{encounter_id}/vitals-workups
GET    /api/v1/vitals-workups/{workup_id}
PATCH  /api/v1/vitals-workups/{workup_id}
POST   /api/v1/vitals-workups/{workup_id}/review
POST   /api/v1/vitals-workups/{workup_id}/sign

RBAC
----
- admin / clinician / technician can create + update + mark entered.
- admin / clinician can review and sign.
- technician CANNOT sign.
- reviewer is read-only.
- front_desk has no clinical access.
- Cross-org access returns 404 (not 403).

Audit
-----
Every write action emits an audit row with metadata-only `detail`
(`workup_id`, `encounter_id`, `patient_id`, `status`, `warning_count`,
`action`). The raw BP / temp / pulse / RR / SpO2 / VA / IOP /
technician_notes values are NEVER written to the audit detail. Phase
60's `test_audit_detail_excludes_clinical_body` proves this with a
canary.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text as sa_text

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import engine, insert_returning_id, transaction
from app.services.vitals_workup import (
    AuditMetadata,
    VALID_BP_POSITION,
    VALID_BP_SITE,
    VALID_DILATION_STATUS,
    VALID_HEIGHT_UNIT,
    VALID_IOP_METHOD,
    VALID_SOURCE_TYPES,
    VALID_TEMP_SITE,
    VALID_TEMP_UNIT,
    VALID_WEIGHT_UNIT,
    VitalsImmutable,
    VitalsStatus,
    VitalsTransitionError,
    assert_can_modify,
    assert_can_transition,
    build_audit_detail,
    calculate_bmi,
    generate_warnings,
)

router = APIRouter(prefix="/api/v1", tags=["vitals-workup"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


def _validate_enum(name: str, value: Optional[str], allowed: frozenset[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if value not in allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_enum",
                "reason": f"{name} must be one of {sorted(allowed)}; got {value!r}",
            },
        )
    return value


class VitalsWorkupCreate(BaseModel):
    source_type: str = Field(default="technician_entry")
    # BP
    bp_systolic: Optional[int] = Field(default=None, ge=1, le=400)
    bp_diastolic: Optional[int] = Field(default=None, ge=1, le=300)
    bp_position: Optional[str] = None
    bp_site: Optional[str] = None
    # Temperature
    temperature_value: Optional[float] = Field(default=None, gt=0)
    temperature_unit: Optional[str] = "F"
    temperature_site: Optional[str] = None
    # Other vitals
    pulse: Optional[int] = Field(default=None, ge=1, le=400)
    respiratory_rate: Optional[int] = Field(default=None, ge=1, le=200)
    oxygen_saturation: Optional[int] = Field(default=None, ge=0, le=100)
    # Biometrics
    height_value: Optional[float] = Field(default=None, gt=0)
    height_unit: Optional[str] = "in"
    weight_value: Optional[float] = Field(default=None, gt=0)
    weight_unit: Optional[str] = "lb"
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)
    # Ophthalmology
    visual_acuity_od: Optional[str] = Field(default=None, max_length=32)
    visual_acuity_os: Optional[str] = Field(default=None, max_length=32)
    visual_acuity_ou: Optional[str] = Field(default=None, max_length=32)
    iop_od: Optional[float] = Field(default=None, gt=0)
    iop_os: Optional[float] = Field(default=None, gt=0)
    iop_method: Optional[str] = None
    dilation_status: Optional[str] = None
    dilation_time: Optional[datetime] = None
    # Review checks
    allergies_reviewed: bool = False
    medications_reviewed: bool = False
    # Free-text
    technician_notes: Optional[str] = Field(default=None, max_length=4000)


class VitalsWorkupUpdate(BaseModel):
    bp_systolic: Optional[int] = Field(default=None, ge=1, le=400)
    bp_diastolic: Optional[int] = Field(default=None, ge=1, le=300)
    bp_position: Optional[str] = None
    bp_site: Optional[str] = None
    temperature_value: Optional[float] = Field(default=None, gt=0)
    temperature_unit: Optional[str] = None
    temperature_site: Optional[str] = None
    pulse: Optional[int] = Field(default=None, ge=1, le=400)
    respiratory_rate: Optional[int] = Field(default=None, ge=1, le=200)
    oxygen_saturation: Optional[int] = Field(default=None, ge=0, le=100)
    height_value: Optional[float] = Field(default=None, gt=0)
    height_unit: Optional[str] = None
    weight_value: Optional[float] = Field(default=None, gt=0)
    weight_unit: Optional[str] = None
    pain_score: Optional[int] = Field(default=None, ge=0, le=10)
    visual_acuity_od: Optional[str] = Field(default=None, max_length=32)
    visual_acuity_os: Optional[str] = Field(default=None, max_length=32)
    visual_acuity_ou: Optional[str] = Field(default=None, max_length=32)
    iop_od: Optional[float] = Field(default=None, gt=0)
    iop_os: Optional[float] = Field(default=None, gt=0)
    iop_method: Optional[str] = None
    dilation_status: Optional[str] = None
    dilation_time: Optional[datetime] = None
    allergies_reviewed: Optional[bool] = None
    medications_reviewed: Optional[bool] = None
    technician_notes: Optional[str] = Field(default=None, max_length=4000)
    # Allow client to advance draft -> entered explicitly.
    advance_to_entered: bool = False


class VitalsWorkupSignRequest(BaseModel):
    attested: bool


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


_WRITE_ROLES = {"admin", "clinician", "technician"}
_REVIEW_ROLES = {"admin", "clinician"}
_SIGN_ROLES = {"admin", "clinician"}


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_write_role(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot write vitals workups; "
            "requires admin, clinician, or technician",
            403,
        )


def _require_review_role(caller: Caller) -> None:
    if caller.role not in _REVIEW_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot review vitals workups; "
            "requires admin or clinician",
            403,
        )


def _require_sign_role(caller: Caller) -> None:
    if caller.role not in _SIGN_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot sign vitals workups; "
            "requires admin or clinician (technician cannot sign)",
            403,
        )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


_ROW_COLS = [
    "id",
    "organization_id",
    "encounter_id",
    "patient_id",
    "status",
    "source_type",
    "bp_systolic",
    "bp_diastolic",
    "bp_position",
    "bp_site",
    "temperature_value",
    "temperature_unit",
    "temperature_site",
    "pulse",
    "respiratory_rate",
    "oxygen_saturation",
    "height_value",
    "height_unit",
    "weight_value",
    "weight_unit",
    "bmi",
    "pain_score",
    "visual_acuity_od",
    "visual_acuity_os",
    "visual_acuity_ou",
    "iop_od",
    "iop_os",
    "iop_method",
    "dilation_status",
    "dilation_time",
    "allergies_reviewed",
    "medications_reviewed",
    "technician_notes",
    "warnings_json",
    "reviewed_by_user_id",
    "reviewed_at",
    "signed_by_user_id",
    "signed_at",
    "created_by_user_id",
    "created_at",
    "updated_at",
]


def _resolve_encounter(encounter_id: int, org_id: int, conn: Any) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_id FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise _err("encounter_not_found", "encounter not found", 404)
    return {"id": row[0], "patient_id": row[1]}


def _select_row_sql() -> str:
    return ", ".join(_ROW_COLS)


def _get_workup(workup_id: int, org_id: int, conn: Any) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            f"SELECT {_select_row_sql()} FROM visit_vitals_workups "
            "WHERE id = :wid AND organization_id = :oid"
        ),
        {"wid": workup_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise _err("workup_not_found", "vitals workup not found", 404)
    return dict(zip(_ROW_COLS, row))


def _coerce_decimal(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a DB row into the API response shape.

    Numeric Decimal columns become Python floats. Datetimes become
    isoformat strings. Booleans are preserved. warnings_json is
    deserialised from JSON text into a list.
    """
    out: dict[str, Any] = dict(row)
    for k in (
        "temperature_value",
        "height_value",
        "weight_value",
        "bmi",
        "iop_od",
        "iop_os",
    ):
        out[k] = _coerce_decimal(out.get(k))
    for k in ("reviewed_at", "signed_at", "dilation_time", "created_at", "updated_at"):
        v = out.get(k)
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    raw_warn = out.get("warnings_json")
    if isinstance(raw_warn, str):
        try:
            out["warnings"] = json.loads(raw_warn)
        except (ValueError, TypeError):
            out["warnings"] = []
    elif isinstance(raw_warn, list):
        out["warnings"] = raw_warn
    else:
        out["warnings"] = []
    # Pin the safety contract on every response.
    out["requires_provider_review"] = out.get("status") != VitalsStatus.SIGNED
    out["forbidden_actions"] = {
        "diagnosis": False,
        "treatment_recommendation": False,
        "orders": False,
        "referrals": False,
        "patient_message": False,
        "billing_or_coding": False,
        "device_integration": False,
        "remote_patient_monitoring": False,
        "auto_sign": False,
    }
    out["is_terminal"] = out.get("status") in {
        VitalsStatus.SIGNED,
        VitalsStatus.SUPERSEDED,
    }
    return out


def _payload_for_warnings_and_bmi(
    base: dict[str, Any], updates: dict[str, Any]
) -> dict[str, Any]:
    """Merge base row + incoming updates into a flat dict suitable for
    `generate_warnings` / `calculate_bmi`."""
    merged = dict(base)
    for k, v in updates.items():
        if v is not None:
            merged[k] = v
        elif k in updates:
            merged[k] = v
    return merged


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    workup: dict[str, Any],
    action: str,
) -> None:
    detail = build_audit_detail(
        AuditMetadata(
            workup_id=int(workup["id"]),
            encounter_id=int(workup["encounter_id"]),
            patient_id=workup.get("patient_id"),
            status=str(workup.get("status", "")),
            warning_count=len(workup.get("warnings") or []),
            action=action,
        )
    )
    audit_record(
        event_type=event_type,
        request_id=_request_id(request),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/encounters/{encounter_id}/vitals-workups")
def list_vitals_workups(
    encounter_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    with engine.connect() as conn:
        _resolve_encounter(encounter_id, caller.organization_id, conn)
        rows = conn.execute(
            sa_text(
                f"SELECT {_select_row_sql()} FROM visit_vitals_workups "
                "WHERE encounter_id = :eid AND organization_id = :oid "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"eid": encounter_id, "oid": caller.organization_id},
        ).fetchall()
    return [_serialize(dict(zip(_ROW_COLS, r))) for r in rows]


@router.post(
    "/encounters/{encounter_id}/vitals-workups", status_code=201
)
def create_vitals_workup(
    encounter_id: int,
    body: VitalsWorkupCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    _validate_enum("source_type", body.source_type, VALID_SOURCE_TYPES)
    _validate_enum("bp_position", body.bp_position, VALID_BP_POSITION)
    _validate_enum("bp_site", body.bp_site, VALID_BP_SITE)
    _validate_enum(
        "temperature_unit", body.temperature_unit, VALID_TEMP_UNIT
    )
    _validate_enum(
        "temperature_site", body.temperature_site, VALID_TEMP_SITE
    )
    _validate_enum("height_unit", body.height_unit, VALID_HEIGHT_UNIT)
    _validate_enum("weight_unit", body.weight_unit, VALID_WEIGHT_UNIT)
    _validate_enum("iop_method", body.iop_method, VALID_IOP_METHOD)
    _validate_enum(
        "dilation_status", body.dilation_status, VALID_DILATION_STATUS
    )

    now = _now_utc()
    payload_dict = body.model_dump()
    bmi = calculate_bmi(
        payload_dict.get("height_value"),
        payload_dict.get("height_unit"),
        payload_dict.get("weight_value"),
        payload_dict.get("weight_unit"),
    )
    warnings = generate_warnings(payload_dict)
    warnings_str = json.dumps(warnings)

    with transaction() as conn:
        enc = _resolve_encounter(encounter_id, caller.organization_id, conn)
        insert_cols: dict[str, Any] = {
            "created_at": now,
            "updated_at": now,
            "organization_id": caller.organization_id,
            "encounter_id": encounter_id,
            "patient_id": enc["patient_id"],
            "status": VitalsStatus.DRAFT,
            "source_type": body.source_type,
            "bp_systolic": body.bp_systolic,
            "bp_diastolic": body.bp_diastolic,
            "bp_position": body.bp_position,
            "bp_site": body.bp_site,
            "temperature_value": body.temperature_value,
            "temperature_unit": (body.temperature_unit or "F"),
            "temperature_site": body.temperature_site,
            "pulse": body.pulse,
            "respiratory_rate": body.respiratory_rate,
            "oxygen_saturation": body.oxygen_saturation,
            "height_value": body.height_value,
            "height_unit": (body.height_unit or "in"),
            "weight_value": body.weight_value,
            "weight_unit": (body.weight_unit or "lb"),
            "bmi": bmi,
            "pain_score": body.pain_score,
            "visual_acuity_od": body.visual_acuity_od,
            "visual_acuity_os": body.visual_acuity_os,
            "visual_acuity_ou": body.visual_acuity_ou,
            "iop_od": body.iop_od,
            "iop_os": body.iop_os,
            "iop_method": body.iop_method,
            "dilation_status": body.dilation_status,
            "dilation_time": body.dilation_time,
            "allergies_reviewed": body.allergies_reviewed,
            "medications_reviewed": body.medications_reviewed,
            "technician_notes": body.technician_notes,
            "warnings_json": warnings_str,
            "created_by_user_id": caller.user_id,
        }
        workup_id = insert_returning_id(conn, "visit_vitals_workups", insert_cols)
        row = _get_workup(workup_id, caller.organization_id, conn)
    response = _serialize(row)
    _audit(
        request=request,
        caller=caller,
        event_type="vitals_workup_created",
        workup=response,
        action="create",
    )
    return response


@router.get("/vitals-workups/{workup_id}")
def get_vitals_workup(
    workup_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    with engine.connect() as conn:
        row = _get_workup(workup_id, caller.organization_id, conn)
    return _serialize(row)


@router.patch("/vitals-workups/{workup_id}")
def update_vitals_workup(
    workup_id: int,
    body: VitalsWorkupUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_write_role(caller)
    update_dict = body.model_dump(exclude_unset=True)
    advance = update_dict.pop("advance_to_entered", False)

    # Validate enums.
    _validate_enum(
        "bp_position", update_dict.get("bp_position"), VALID_BP_POSITION
    )
    _validate_enum("bp_site", update_dict.get("bp_site"), VALID_BP_SITE)
    _validate_enum(
        "temperature_unit",
        update_dict.get("temperature_unit"),
        VALID_TEMP_UNIT,
    )
    _validate_enum(
        "temperature_site",
        update_dict.get("temperature_site"),
        VALID_TEMP_SITE,
    )
    _validate_enum(
        "height_unit", update_dict.get("height_unit"), VALID_HEIGHT_UNIT
    )
    _validate_enum(
        "weight_unit", update_dict.get("weight_unit"), VALID_WEIGHT_UNIT
    )
    _validate_enum(
        "iop_method", update_dict.get("iop_method"), VALID_IOP_METHOD
    )
    _validate_enum(
        "dilation_status",
        update_dict.get("dilation_status"),
        VALID_DILATION_STATUS,
    )

    with transaction() as conn:
        existing = _get_workup(workup_id, caller.organization_id, conn)
        try:
            assert_can_modify(existing["status"])
        except VitalsImmutable as e:
            raise _err(
                "workup_immutable",
                f"workup is {e.current!r} and cannot be modified",
                409,
            )

        merged = _payload_for_warnings_and_bmi(existing, update_dict)
        # Recompute BMI from the merged height/weight.
        new_bmi = calculate_bmi(
            merged.get("height_value"),
            merged.get("height_unit"),
            merged.get("weight_value"),
            merged.get("weight_unit"),
        )
        new_warnings = generate_warnings(merged)

        sets: list[str] = ["updated_at = :updated_at"]
        params: dict[str, Any] = {
            "updated_at": _now_utc(),
            "id": workup_id,
            "org_id": caller.organization_id,
        }
        for col in (
            "bp_systolic",
            "bp_diastolic",
            "bp_position",
            "bp_site",
            "temperature_value",
            "temperature_unit",
            "temperature_site",
            "pulse",
            "respiratory_rate",
            "oxygen_saturation",
            "height_value",
            "height_unit",
            "weight_value",
            "weight_unit",
            "pain_score",
            "visual_acuity_od",
            "visual_acuity_os",
            "visual_acuity_ou",
            "iop_od",
            "iop_os",
            "iop_method",
            "dilation_status",
            "dilation_time",
            "allergies_reviewed",
            "medications_reviewed",
            "technician_notes",
        ):
            if col in update_dict:
                sets.append(f"{col} = :{col}")
                params[col] = update_dict[col]
        sets.append("bmi = :bmi")
        params["bmi"] = new_bmi
        sets.append("warnings_json = :warnings_json")
        params["warnings_json"] = json.dumps(new_warnings)
        if advance:
            try:
                assert_can_transition("enter", existing["status"])
            except (VitalsTransitionError, VitalsImmutable) as e:
                raise _err(
                    "invalid_transition",
                    f"cannot mark entered from status {existing['status']!r}",
                    409,
                )
            sets.append("status = :status")
            params["status"] = VitalsStatus.ENTERED

        conn.execute(
            sa_text(
                f"UPDATE visit_vitals_workups SET {', '.join(sets)} "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            params,
        )
        refreshed = _get_workup(workup_id, caller.organization_id, conn)

    response = _serialize(refreshed)
    _audit(
        request=request,
        caller=caller,
        event_type="vitals_workup_updated",
        workup=response,
        action="enter" if advance else "update",
    )
    return response


@router.post("/vitals-workups/{workup_id}/review")
def review_vitals_workup(
    workup_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_review_role(caller)
    now = _now_utc()
    with transaction() as conn:
        existing = _get_workup(workup_id, caller.organization_id, conn)
        try:
            assert_can_transition("review", existing["status"])
        except VitalsImmutable as e:
            raise _err(
                "workup_immutable",
                f"workup is {e.current!r} and cannot be reviewed",
                409,
            )
        except VitalsTransitionError as e:
            raise _err(
                "invalid_transition",
                f"review requires status=entered (current: {e.current!r})",
                409,
            )
        conn.execute(
            sa_text(
                "UPDATE visit_vitals_workups SET "
                "status = :status, reviewed_by_user_id = :uid, "
                "reviewed_at = :now, updated_at = :now "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {
                "status": VitalsStatus.REVIEWED,
                "uid": caller.user_id,
                "now": now,
                "id": workup_id,
                "org_id": caller.organization_id,
            },
        )
        refreshed = _get_workup(workup_id, caller.organization_id, conn)
    response = _serialize(refreshed)
    _audit(
        request=request,
        caller=caller,
        event_type="vitals_workup_reviewed",
        workup=response,
        action="review",
    )
    return response


@router.post("/vitals-workups/{workup_id}/sign")
def sign_vitals_workup(
    workup_id: int,
    body: VitalsWorkupSignRequest,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Any:
    _require_sign_role(caller)
    if not body.attested:
        raise _err(
            "attestation_required",
            "attested must be true to sign",
            422,
        )
    now = _now_utc()
    with transaction() as conn:
        existing = _get_workup(workup_id, caller.organization_id, conn)
        try:
            assert_can_transition("sign", existing["status"])
        except VitalsImmutable as e:
            raise _err(
                "workup_immutable",
                f"workup is {e.current!r} and cannot be signed",
                409,
            )
        except VitalsTransitionError as e:
            raise _err(
                "invalid_transition",
                f"sign requires status=reviewed (current: {e.current!r})",
                409,
            )
        conn.execute(
            sa_text(
                "UPDATE visit_vitals_workups SET "
                "status = :status, signed_by_user_id = :uid, "
                "signed_at = :now, updated_at = :now "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {
                "status": VitalsStatus.SIGNED,
                "uid": caller.user_id,
                "now": now,
                "id": workup_id,
                "org_id": caller.organization_id,
            },
        )
        refreshed = _get_workup(workup_id, caller.organization_id, conn)
    response = _serialize(refreshed)
    _audit(
        request=request,
        caller=caller,
        event_type="vitals_workup_signed",
        workup=response,
        action="sign",
    )
    return response
