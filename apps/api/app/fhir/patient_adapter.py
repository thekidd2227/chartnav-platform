"""Phase 87 — FHIR R4 Patient adapter.

Read-only projection of `patients` rows into a minimal FHIR R4
Patient resource. The projection exposes only fields the existing
non-FHIR API already exposes (identifier, name, dob, sex_at_birth,
active) — no new PHI surface is opened by this adapter.

Hard rules:

  * Org isolation enforced by the caller (cross-org → 404).
  * No mutation. There is no PATCH / POST / DELETE Patient route.
  * No clinical free text. The Patient resource carries identifier,
    HumanName, birthDate, gender, and active only — no observations,
    conditions, medications, or allergy data leaks through this
    adapter.
  * `gender` projection is conservative: ChartNav's `sex_at_birth`
    column is free-form text. The adapter normalizes to the FHIR
    `administrative-gender` value set (male / female / other /
    unknown). Free-form values that don't match fall back to
    'unknown' so the projection stays FHIR-conformant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class FhirExportError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


_PATIENT_COLS = (
    "id",
    "organization_id",
    "external_ref",
    "patient_identifier",
    "first_name",
    "last_name",
    "date_of_birth",
    "sex_at_birth",
    "is_active",
    "created_at",
)


# FHIR administrative-gender value set:
#   http://hl7.org/fhir/R4/valueset-administrative-gender.html
_GENDER_MAP = {
    "m": "male",
    "male": "male",
    "f": "female",
    "female": "female",
    "o": "other",
    "other": "other",
    "u": "unknown",
    "unknown": "unknown",
}


def _normalize_gender(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    key = value.strip().lower()
    if not key:
        return "unknown"
    return _GENDER_MAP.get(key, "unknown")


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return None
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return bool(value)


def _fetch_patient(
    conn, patient_id: int, organization_id: int
) -> dict[str, Any] | None:
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_PATIENT_COLS)} FROM patients "
            "WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_PATIENT_COLS, row))


def build_patient_resource(patient_id: int, caller: Caller) -> dict[str, Any]:
    """Return a FHIR R4 Patient resource for the given patient.

    Raises ``FhirExportError`` with status 404 when the patient does
    not exist in the caller's organization (no existence leak across
    tenants).
    """
    with engine.connect() as conn:
        rec = _fetch_patient(conn, patient_id, caller.organization_id)
    if rec is None:
        raise FhirExportError(
            "patient_not_found", "patient not found", 404
        )

    given = (rec["first_name"] or "").strip()
    family = (rec["last_name"] or "").strip()
    name_text = " ".join(p for p in (given, family) if p) or rec[
        "patient_identifier"
    ]

    identifiers: list[dict[str, Any]] = [
        {
            "use": "usual",
            "system": "urn:chartnav:patient-identifier",
            "value": rec["patient_identifier"],
        },
    ]
    if rec.get("external_ref"):
        identifiers.append(
            {
                "use": "secondary",
                "system": "urn:chartnav:external-ref",
                "value": rec["external_ref"],
            }
        )

    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(rec["id"]),
        "meta": {
            "source": (
                f"urn:chartnav:organization:{rec['organization_id']}"
            ),
        },
        "identifier": identifiers,
        "active": _truthy(rec["is_active"]),
        "name": [
            {
                "use": "official",
                "text": name_text,
                **({"given": [given]} if given else {}),
                **({"family": family} if family else {}),
            }
        ],
        "gender": _normalize_gender(rec.get("sex_at_birth")),
    }

    dob = _iso_date(rec.get("date_of_birth"))
    if dob:
        resource["birthDate"] = dob

    return resource


__all__ = ["FhirExportError", "build_patient_resource"]
