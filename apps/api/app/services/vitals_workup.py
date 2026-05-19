"""Structured vitals/workup service.

Technician- or clinician-entered intake only. This module normalizes
values, calculates BMI, generates non-diagnostic review warnings, and
enforces review/sign lifecycle rules. It never creates diagnosis,
treatment, order, referral, patient-message, billing, or coding output.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy import text

from app.db import engine, insert_returning_id, transaction


TABLE = "visit_vitals_workups"


class VitalWorkupNotFound(Exception):
    """Workup not found in the caller's organization."""


class VitalWorkupImmutable(Exception):
    """Signed workup cannot be changed."""


class InvalidVitalWorkupTransition(Exception):
    """Requested lifecycle transition is not allowed."""


class VitalWorkupAttestationRequired(Exception):
    """Signing requires explicit attestation."""


class PatientEncounterMismatch(Exception):
    """Encounter does not belong to the expected org/patient boundary."""


STATUSES = {"draft", "entered", "reviewed", "signed", "superseded"}
SOURCE_TYPES = {"technician_entry", "clinician_entry", "imported", "demo"}
UPDATABLE_STATUSES = {"draft", "entered", "reviewed"}


INTAKE_FIELDS: tuple[str, ...] = (
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
)

READ_FIELDS: tuple[str, ...] = (
    "id",
    "organization_id",
    "encounter_id",
    "patient_id",
    *INTAKE_FIELDS,
    "bmi",
    "warnings_json",
    "reviewed_by_user_id",
    "signed_by_user_id",
    "signed_at",
    "created_by_user_id",
    "created_at",
    "updated_at",
)


@dataclass(frozen=True)
class EncounterRef:
    id: int
    patient_id: int


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _round(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def calculate_bmi(
    height_value: Any,
    height_unit: str | None,
    weight_value: Any,
    weight_unit: str | None,
) -> Decimal | None:
    height = _decimal(height_value)
    weight = _decimal(weight_value)
    if height is None or weight is None or height <= 0 or weight <= 0:
        return None

    height_in = height if (height_unit or "in") == "in" else height / Decimal("2.54")
    weight_lb = weight if (weight_unit or "lb") == "lb" else weight * Decimal("2.2046226218")
    if height_in <= 0:
        return None
    return _round((weight_lb / (height_in * height_in)) * Decimal("703"))


def generate_warnings(values: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    sys = values.get("bp_systolic")
    dia = values.get("bp_diastolic")
    if sys is not None and dia is None:
        warnings.append("Blood pressure systolic entered without diastolic; provider review required.")
    if dia is not None and sys is None:
        warnings.append("Blood pressure diastolic entered without systolic; provider review required.")
    if (sys is not None or dia is not None) and not values.get("bp_site"):
        warnings.append("Blood pressure value entered without site; review required.")
    if (sys is not None or dia is not None) and not values.get("bp_position"):
        warnings.append("Blood pressure value entered without position; review required.")

    if values.get("height_value") is not None and values.get("weight_value") is None:
        warnings.append("Height entered without weight; review required.")
    if values.get("weight_value") is not None and values.get("height_value") is None:
        warnings.append("Weight entered without height; review required.")

    if values.get("iop_od") is not None and values.get("iop_os") is None:
        warnings.append("IOP OD entered without IOP OS; provider review required.")
    if values.get("iop_os") is not None and values.get("iop_od") is None:
        warnings.append("IOP OS entered without IOP OD; provider review required.")

    if values.get("visual_acuity_od") and not values.get("visual_acuity_os"):
        warnings.append("VA OD entered without VA OS; provider review required.")
    if values.get("visual_acuity_os") and not values.get("visual_acuity_od"):
        warnings.append("VA OS entered without VA OD; provider review required.")

    spo2 = values.get("oxygen_saturation")
    if spo2 is not None and int(spo2) < 92:
        warnings.append("Oxygen saturation is outside expected review range; provider review required.")

    temp = _decimal(values.get("temperature_value"))
    unit = values.get("temperature_unit") or "F"
    if temp is not None:
        if (unit == "F" and (temp < Decimal("95") or temp > Decimal("100.4"))) or (
            unit == "C" and (temp < Decimal("35") or temp > Decimal("38"))
        ):
            warnings.append("Temperature is outside expected review range; provider review required.")

    return warnings


def normalize_values(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    normalized.setdefault("status", "entered")
    normalized.setdefault("source_type", "technician_entry")
    normalized.setdefault("temperature_unit", "F")
    normalized.setdefault("height_unit", "in")
    normalized.setdefault("weight_unit", "lb")
    normalized.setdefault("allergies_reviewed", False)
    normalized.setdefault("medications_reviewed", False)
    bmi = calculate_bmi(
        normalized.get("height_value"),
        normalized.get("height_unit"),
        normalized.get("weight_value"),
        normalized.get("weight_unit"),
    )
    normalized["bmi"] = float(bmi) if bmi is not None else None
    normalized["warnings_json"] = json.dumps(generate_warnings(normalized))
    return normalized


def _decode_warnings(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw]
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(v) for v in parsed] if isinstance(parsed, list) else []


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["warnings_json"] = _decode_warnings(data.get("warnings_json"))
    for key in ("bmi", "temperature_value", "height_value", "weight_value", "iop_od", "iop_os"):
        if data.get(key) is not None:
            data[key] = float(data[key])
    return data


def resolve_encounter(encounter_id: int, organization_id: int) -> EncounterRef:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, patient_id FROM encounters "
                "WHERE id = :id AND organization_id = :org"
            ),
            {"id": encounter_id, "org": organization_id},
        ).mappings().first()
    if not row or row["patient_id"] is None:
        raise VitalWorkupNotFound("encounter not found in organization")
    return EncounterRef(id=int(row["id"]), patient_id=int(row["patient_id"]))


def get_workup(workup_id: int, *, organization_id: int) -> dict[str, Any]:
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(READ_FIELDS)} FROM {TABLE} WHERE id = :id AND organization_id = :org"),
            {"id": workup_id, "org": organization_id},
        ).mappings().first()
    if not row:
        raise VitalWorkupNotFound("workup not found in organization")
    return _row_to_dict(row)


def list_by_encounter(encounter_id: int, *, organization_id: int) -> list[dict[str, Any]]:
    # Caller gets 404 semantics if the encounter is not in org.
    resolve_encounter(encounter_id, organization_id)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT {', '.join(READ_FIELDS)} FROM {TABLE} "
                "WHERE encounter_id = :encounter_id AND organization_id = :org "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"encounter_id": encounter_id, "org": organization_id},
        ).mappings().all()
    return [_row_to_dict(row) for row in rows]


def create_workup(
    encounter_id: int,
    *,
    organization_id: int,
    created_by_user_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    enc = resolve_encounter(encounter_id, organization_id)
    normalized = normalize_values(values)
    if normalized["status"] not in {"draft", "entered"}:
        raise InvalidVitalWorkupTransition("new workup must start as draft or entered")
    now = now_utc()
    insert_values = {
        **{k: normalized.get(k) for k in INTAKE_FIELDS},
        "bmi": normalized["bmi"],
        "warnings_json": normalized["warnings_json"],
        "organization_id": organization_id,
        "encounter_id": enc.id,
        "patient_id": enc.patient_id,
        "created_by_user_id": created_by_user_id,
        "created_at": now,
        "updated_at": now,
    }
    with transaction() as conn:
        workup_id = insert_returning_id(conn, TABLE, insert_values)
    return get_workup(workup_id, organization_id=organization_id)


def update_workup(
    workup_id: int,
    *,
    organization_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    existing = get_workup(workup_id, organization_id=organization_id)
    if existing.get("status") == "signed" or existing.get("signed_at") is not None:
        raise VitalWorkupImmutable("signed workup cannot be modified")

    merged = {k: existing.get(k) for k in INTAKE_FIELDS}
    merged.update(values)
    normalized = normalize_values(merged)
    if normalized["status"] not in UPDATABLE_STATUSES:
        raise InvalidVitalWorkupTransition("unsigned workup status must be draft, entered, or reviewed")

    update_fields = [*INTAKE_FIELDS, "bmi", "warnings_json"]
    assignments = ", ".join(f"{key} = :{key}" for key in update_fields)
    params = {key: normalized.get(key) for key in update_fields}
    params.update({"id": workup_id, "org": organization_id, "updated_at": now_utc()})
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {TABLE} SET {assignments}, updated_at = :updated_at "
                "WHERE id = :id AND organization_id = :org"
            ),
            params,
        )
    return get_workup(workup_id, organization_id=organization_id)


def review_workup(
    workup_id: int,
    *,
    organization_id: int,
    reviewed_by_user_id: int,
) -> dict[str, Any]:
    existing = get_workup(workup_id, organization_id=organization_id)
    if existing.get("status") == "signed" or existing.get("signed_at") is not None:
        raise VitalWorkupImmutable("signed workup cannot be reviewed again")
    now = now_utc()
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {TABLE} SET status = 'reviewed', reviewed_by_user_id = :uid, "
                "updated_at = :now WHERE id = :id AND organization_id = :org"
            ),
            {"uid": reviewed_by_user_id, "now": now, "id": workup_id, "org": organization_id},
        )
    return get_workup(workup_id, organization_id=organization_id)


def sign_workup(
    workup_id: int,
    *,
    organization_id: int,
    signed_by_user_id: int,
    attested: bool,
) -> dict[str, Any]:
    if not attested:
        raise VitalWorkupAttestationRequired("attestation is required")
    existing = get_workup(workup_id, organization_id=organization_id)
    if existing.get("status") == "signed" or existing.get("signed_at") is not None:
        raise VitalWorkupImmutable("signed workup cannot be signed again")
    if existing.get("status") != "reviewed":
        raise InvalidVitalWorkupTransition("workup must be reviewed before signing")
    now = now_utc()
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {TABLE} SET status = 'signed', signed_by_user_id = :uid, "
                "signed_at = :now, updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {"uid": signed_by_user_id, "now": now, "id": workup_id, "org": organization_id},
        )
    return get_workup(workup_id, organization_id=organization_id)


def audit_detail(workup: dict[str, Any]) -> str:
    warning_count = len(workup.get("warnings_json") or [])
    return (
        f"workup_id={workup['id']} "
        f"patient_id={workup['patient_id']} "
        f"encounter_id={workup['encounter_id']} "
        f"status={workup['status']} "
        f"warning_count={warning_count}"
    )
