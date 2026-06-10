"""Phase 85 — Ophthalmic Medication Safety & Adherence Engine.

Provider-entered medication list + refill history + allergy list, plus
four deterministic informational signals computed at read time:

  * **refill_gap_days**     — today - (last_refill + expected_days_supply),
                              when both refill history and expected days
                              supply are on file. Strict subtraction; no
                              extrapolation. Negative values clamped to 0.
  * **preservative_burden** — count of active drop medications whose
                              ``preservative_flag=True``. The flag itself
                              is provider-entered — ChartNav does NOT
                              autonomously classify whether a drop carries
                              BAK or other preservatives.
  * **polypharmacy_count**  — count of currently active medication rows
                              (``discontinued_on`` is NULL or in the
                              future).
  * **allergy_matches**     — list of (medication_id, allergy_id) pairs
                              where the medication_name OR medication_class
                              substring-matches a recorded allergy
                              ``substance``. Case-insensitive; never a
                              full interaction inference.

Hard rules:

  * Every field is provider-entered. ChartNav does NOT prescribe, does
    NOT refill, does NOT auto-dose, does NOT recommend medication
    changes, does NOT contact the pharmacy, and does NOT perform
    autonomous drug interaction checking beyond the literal allergy
    substring match.
  * The refill-gap signal is informational only. It never blocks
    signing, never recommends an action, and never escalates.
  * The note validation surface (Phase 82) emits a single informational
    check; never requires acknowledgement.
  * The provider action queue (Phase 81) surfaces medication-gap items
    at "informational" priority only — never tier 1.
  * Only admin / clinician may POST or DELETE. Reviewer / front_desk /
    technician are denied.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Closed allowlists
# ---------------------------------------------------------------------------

MED_CLASS_LABELS: dict[str, str] = {
    "pgf2_analog": "Prostaglandin F2α analog",
    "beta_blocker": "Beta blocker",
    "alpha_agonist": "Alpha agonist",
    "carbonic_anhydrase_inhibitor": "Carbonic anhydrase inhibitor",
    "rho_kinase_inhibitor": "Rho-kinase inhibitor",
    "combination_drop": "Combination drop",
    "steroid_drop": "Steroid drop",
    "nsaid_drop": "NSAID drop",
    "antibiotic_drop": "Antibiotic drop",
    "anti_vegf_intravitreal": "Anti-VEGF intravitreal",
    "lubricant": "Lubricant",
    "oral_systemic_other": "Oral / systemic — other",
}
VALID_MED_CLASSES = frozenset(MED_CLASS_LABELS.keys())
VALID_ROUTES = frozenset({"drops", "oral", "intravitreal"})
VALID_LATERALITIES = frozenset({"OD", "OS", "OU", "NA"})

REACTION_TYPE_LABELS: dict[str, str] = {
    "rash": "Rash",
    "swelling": "Swelling",
    "anaphylaxis": "Anaphylaxis",
    "gi_distress": "GI distress",
    "respiratory": "Respiratory",
    "other": "Other",
}
VALID_REACTION_TYPES = frozenset(REACTION_TYPE_LABELS.keys())
VALID_SEVERITIES = frozenset({"mild", "moderate", "severe"})


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class MedicationError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _text(name: str, value: Any, *, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MedicationError(
            "invalid_text", f"{name} must be a non-empty string", 422
        )
    s = value.strip()
    if len(s) > max_len:
        raise MedicationError(
            "invalid_text",
            f"{name} must be at most {max_len} characters",
            422,
        )
    return s


def _opt_text(value: Any, *, max_len: int) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise MedicationError(
            "invalid_text", "value must be a string or null", 422
        )
    s = value.strip()
    if not s:
        return None
    if len(s) > max_len:
        raise MedicationError(
            "invalid_text",
            f"value must be at most {max_len} characters",
            422,
        )
    return s


def _enum(name: str, value: Any, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise MedicationError(
            f"invalid_{name}",
            f"{name} must be one of {sorted(allowed)}; got {value!r}",
            422,
        )
    return value


def _int_range(name: str, value: Any, *, lo: int, hi: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MedicationError(
            f"invalid_{name}", f"{name} must be an integer", 422
        )
    if value < lo or value > hi:
        raise MedicationError(
            f"invalid_{name}",
            f"{name} must be between {lo} and {hi}; got {value}",
            422,
        )
    return value


def _bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise MedicationError(
            f"invalid_{name}", f"{name} must be a boolean", 422
        )
    return value


def _opt_date(name: str, value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise MedicationError(
                f"invalid_{name}",
                f"{name} must be an ISO date (YYYY-MM-DD)",
                422,
            )
    raise MedicationError(
        f"invalid_{name}", f"{name} must be an ISO date or null", 422
    )


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise MedicationError(
            "forbidden",
            "only admin or clinician can record a medication",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_patient_or_404(
    conn, patient_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise MedicationError("patient_not_found", "patient not found", 404)
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


def _resolve_encounter_or_404(
    conn, encounter_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise MedicationError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    eid, oid, pid = row
    return {
        "id": int(eid),
        "organization_id": int(oid),
        "patient_id": int(pid) if pid is not None else None,
    }


def _resolve_medication_or_404(
    conn, medication_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_MED_COLS)} FROM medications "
            "WHERE id = :mid AND organization_id = :oid"
        ),
        {"mid": medication_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise MedicationError(
            "medication_not_found",
            "medication not found in your organization",
            404,
        )
    return dict(zip(_MED_COLS, row))


def _actor_display(conn, user_id: int) -> dict[str, str | None]:
    row = conn.execute(
        sa_text("SELECT full_name, email, role FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    if row is None:
        return {"display_name": None, "role": None}
    full_name, email, role = row
    return {"display_name": full_name or email, "role": role}


# ---------------------------------------------------------------------------
# Row schema helpers
# ---------------------------------------------------------------------------

_MED_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "medication_name",
    "medication_class",
    "route",
    "laterality",
    "dose_per_day",
    "preservative_flag",
    "started_on",
    "discontinued_on",
    "prescriber_user_id",
    "prescriber_display_name",
    "recorded_by_user_id",
    "recorded_at",
    "created_at",
    "updated_at",
)

_REFILL_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "medication_id",
    "encounter_id",
    "refill_date",
    "expected_days_supply",
    "recorded_by_user_id",
    "recorded_at",
    "created_at",
    "updated_at",
)

_ALLERGY_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "substance",
    "reaction_type",
    "severity",
    "recorded_by_user_id",
    "recorded_at",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _truthy_bool(value: Any) -> bool:
    """SQLite returns 0/1; Postgres returns bool. Normalize."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "t", "true", "y", "yes"}
    return bool(value)


def _serialize_medication(
    row: dict[str, Any],
    *,
    prescriber_display_name: str | None = None,
    recorder_display_name: str | None = None,
    recorder_role: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "encounter_id": int(row["encounter_id"])
        if row.get("encounter_id") is not None
        else None,
        "medication_name": row["medication_name"],
        "medication_class": row["medication_class"],
        "medication_class_label": MED_CLASS_LABELS.get(
            row["medication_class"], row["medication_class"]
        ),
        "route": row["route"],
        "laterality": row["laterality"],
        "dose_per_day": int(row["dose_per_day"]),
        "preservative_flag": _truthy_bool(row.get("preservative_flag")),
        "started_on": _iso(row.get("started_on")),
        "discontinued_on": _iso(row.get("discontinued_on")),
        "prescriber_user_id": int(row["prescriber_user_id"])
        if row.get("prescriber_user_id") is not None
        else None,
        "prescriber_display_name": row.get("prescriber_display_name")
        or prescriber_display_name,
        "recorded_by_user_id": int(row["recorded_by_user_id"]),
        "recorded_by_display_name": recorder_display_name,
        "recorded_by_role": recorder_role,
        "recorded_at": _iso(row.get("recorded_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "is_active": active if active is not None else _is_active(row),
    }


def _serialize_refill(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "medication_id": int(row["medication_id"]),
        "encounter_id": int(row["encounter_id"])
        if row.get("encounter_id") is not None
        else None,
        "refill_date": _iso(row.get("refill_date")),
        "expected_days_supply": int(row["expected_days_supply"]),
        "recorded_by_user_id": int(row["recorded_by_user_id"]),
        "recorded_at": _iso(row.get("recorded_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _serialize_allergy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "substance": row["substance"],
        "reaction_type": row["reaction_type"],
        "reaction_type_label": REACTION_TYPE_LABELS.get(
            row["reaction_type"], row["reaction_type"]
        ),
        "severity": row["severity"],
        "recorded_by_user_id": int(row["recorded_by_user_id"]),
        "recorded_at": _iso(row.get("recorded_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }


def _is_active(row: dict[str, Any], *, today: date | None = None) -> bool:
    today = today or date.today()
    disc = _parse_date(row.get("discontinued_on"))
    if disc is None:
        return True
    return disc > today


# ---------------------------------------------------------------------------
# Deterministic signals
# ---------------------------------------------------------------------------


def _compute_refill_gap(
    medication: dict[str, Any],
    refills: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Return a deterministic refill-gap projection.

    Never recommends; never blocks. Pure arithmetic on provider-entered
    refill events.
    """
    today = today or date.today()
    if not _is_active(medication, today=today):
        return {
            "has_history": False,
            "last_refill_date": None,
            "expected_days_supply": None,
            "supply_through": None,
            "gap_days": None,
            "status": "discontinued",
        }
    if not refills:
        return {
            "has_history": False,
            "last_refill_date": None,
            "expected_days_supply": None,
            "supply_through": None,
            "gap_days": None,
            "status": "no_history",
        }
    latest = max(
        refills,
        key=lambda r: (_parse_date(r["refill_date"]) or date.min, r["id"]),
    )
    last_date = _parse_date(latest["refill_date"])
    days_supply = int(latest["expected_days_supply"])
    supply_through = None
    gap_days = None
    if last_date is not None:
        supply_through = last_date.fromordinal(
            last_date.toordinal() + days_supply
        )
        delta = (today - supply_through).days
        gap_days = max(0, delta)
    status = "on_track"
    if gap_days is not None and gap_days > 0:
        status = "gap"
    return {
        "has_history": True,
        "last_refill_date": _iso(last_date),
        "expected_days_supply": days_supply,
        "supply_through": _iso(supply_through),
        "gap_days": gap_days,
        "status": status,
    }


def _compute_allergy_matches(
    medications: list[dict[str, Any]],
    allergies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Literal substring match across (medication_name, class label) vs
    (allergy substance). Case-insensitive. Never a full interaction
    inference."""
    out: list[dict[str, Any]] = []
    for med in medications:
        name = (med.get("medication_name") or "").lower()
        klass_label = (
            MED_CLASS_LABELS.get(med.get("medication_class"), "") or ""
        ).lower()
        klass_code = (med.get("medication_class") or "").lower()
        for allergy in allergies:
            sub = (allergy.get("substance") or "").strip().lower()
            if not sub:
                continue
            if sub in name or sub in klass_label or sub in klass_code:
                out.append(
                    {
                        "medication_id": int(med["id"]),
                        "medication_name": med["medication_name"],
                        "allergy_id": int(allergy["id"]),
                        "allergy_substance": allergy["substance"],
                        "allergy_severity": allergy["severity"],
                    }
                )
    return out


# ---------------------------------------------------------------------------
# Read paths
# ---------------------------------------------------------------------------


def _list_meds(conn, *, patient_id: int, org_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_MED_COLS)} FROM medications "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "ORDER BY recorded_at DESC, id DESC"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()
    return [dict(zip(_MED_COLS, r)) for r in rows]


def _list_refills(
    conn, *, patient_id: int, org_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_REFILL_COLS)} FROM medication_refills "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "ORDER BY refill_date DESC, id DESC"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()
    return [dict(zip(_REFILL_COLS, r)) for r in rows]


def _list_allergies(
    conn, *, patient_id: int, org_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_ALLERGY_COLS)} FROM medication_allergies "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "ORDER BY recorded_at DESC, id DESC"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()
    return [dict(zip(_ALLERGY_COLS, r)) for r in rows]


def _actor_cache(conn, user_ids: set[int]) -> dict[int, dict[str, str | None]]:
    out: dict[int, dict[str, str | None]] = {}
    if not user_ids:
        return out
    placeholders = ", ".join(f":u{i}" for i in range(len(user_ids)))
    params: dict[str, Any] = {}
    for i, uid in enumerate(sorted(user_ids)):
        params[f"u{i}"] = uid
    rows = conn.execute(
        sa_text(
            "SELECT id, full_name, email, role FROM users "
            f"WHERE id IN ({placeholders})"
        ),
        params,
    ).fetchall()
    for uid, full_name, email, role in rows:
        out[int(uid)] = {"display_name": full_name or email, "role": role}
    return out


_DISCLOSURE = (
    "Provider-entered medication safety surface. ChartNav does not "
    "prescribe, does not refill, does not dose, does not contact the "
    "pharmacy, does not recommend medication changes, and does not "
    "perform autonomous drug-interaction checking. Allergy matches are "
    "literal substring matches against the provider-entered allergy "
    "list. Refill-gap signals are deterministic arithmetic and never "
    "block signing."
)


# ---------------------------------------------------------------------------
# Public API — writes
# ---------------------------------------------------------------------------


def create_medication(
    encounter_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)

    medication_name = _text(
        "medication_name", payload.get("medication_name"), max_len=128
    )
    medication_class = _enum(
        "medication_class",
        payload.get("medication_class"),
        VALID_MED_CLASSES,
    )
    route = _enum("route", payload.get("route"), VALID_ROUTES)
    laterality = _enum(
        "laterality", payload.get("laterality"), VALID_LATERALITIES
    )
    dose_per_day = _int_range(
        "dose_per_day", payload.get("dose_per_day"), lo=0, hi=24
    )
    preservative_flag = _bool(
        "preservative_flag", payload.get("preservative_flag", False)
    )
    started_on = _opt_date("started_on", payload.get("started_on"))
    discontinued_on = _opt_date(
        "discontinued_on", payload.get("discontinued_on")
    )
    prescriber_display_name = _opt_text(
        payload.get("prescriber_display_name"), max_len=128
    )

    with engine.begin() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        if encounter["patient_id"] is None:
            raise MedicationError(
                "patient_not_found",
                "encounter has no linked patient",
                404,
            )
        patient = _resolve_patient_or_404(
            conn, encounter["patient_id"], caller.organization_id
        )
        recorder = _actor_display(conn, caller.user_id)

        new_id = insert_returning_id(
            conn,
            "medications",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient["id"],
                "encounter_id": encounter["id"],
                "medication_name": medication_name,
                "medication_class": medication_class,
                "route": route,
                "laterality": laterality,
                "dose_per_day": dose_per_day,
                "preservative_flag": preservative_flag,
                "started_on": started_on,
                "discontinued_on": discontinued_on,
                "prescriber_display_name": prescriber_display_name,
                "recorded_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_MED_COLS)} FROM medications "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_MED_COLS, row))

    return _serialize_medication(
        record,
        recorder_display_name=recorder["display_name"],
        recorder_role=recorder["role"],
    )


def discontinue_medication(
    medication_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)
    discontinued_on = _opt_date(
        "discontinued_on", payload.get("discontinued_on")
    ) or date.today()

    with engine.begin() as conn:
        existing = _resolve_medication_or_404(
            conn, medication_id, caller.organization_id
        )
        conn.execute(
            sa_text(
                "UPDATE medications SET discontinued_on = :d, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"d": discontinued_on, "id": medication_id},
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_MED_COLS)} FROM medications "
                "WHERE id = :id"
            ),
            {"id": medication_id},
        ).fetchone()
        record = dict(zip(_MED_COLS, row))
        recorder = _actor_display(conn, int(existing["recorded_by_user_id"]))

    return _serialize_medication(
        record,
        recorder_display_name=recorder["display_name"],
        recorder_role=recorder["role"],
    )


def create_refill(
    medication_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)
    refill_date_raw = payload.get("refill_date")
    if refill_date_raw is None:
        refill_date = date.today()
    else:
        refill_date = _opt_date("refill_date", refill_date_raw)
        if refill_date is None:
            refill_date = date.today()
    expected_days_supply = _int_range(
        "expected_days_supply",
        payload.get("expected_days_supply"),
        lo=1,
        hi=365,
    )
    encounter_id_raw = payload.get("encounter_id")
    encounter_id: int | None = None

    with engine.begin() as conn:
        medication = _resolve_medication_or_404(
            conn, medication_id, caller.organization_id
        )
        if encounter_id_raw is not None:
            encounter = _resolve_encounter_or_404(
                conn, int(encounter_id_raw), caller.organization_id
            )
            encounter_id = encounter["id"]
        new_id = insert_returning_id(
            conn,
            "medication_refills",
            {
                "organization_id": caller.organization_id,
                "patient_id": int(medication["patient_id"]),
                "medication_id": medication_id,
                "encounter_id": encounter_id,
                "refill_date": refill_date,
                "expected_days_supply": expected_days_supply,
                "recorded_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_REFILL_COLS)} FROM medication_refills "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_REFILL_COLS, row))

    return _serialize_refill(record)


def create_allergy(
    patient_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)
    substance = _text("substance", payload.get("substance"), max_len=128)
    reaction_type = _enum(
        "reaction_type", payload.get("reaction_type"), VALID_REACTION_TYPES
    )
    severity = _enum("severity", payload.get("severity"), VALID_SEVERITIES)

    with engine.begin() as conn:
        patient = _resolve_patient_or_404(
            conn, patient_id, caller.organization_id
        )
        new_id = insert_returning_id(
            conn,
            "medication_allergies",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient["id"],
                "substance": substance,
                "reaction_type": reaction_type,
                "severity": severity,
                "recorded_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ALLERGY_COLS)} FROM medication_allergies "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_ALLERGY_COLS, row))

    return _serialize_allergy(record)


# ---------------------------------------------------------------------------
# Public API — reads
# ---------------------------------------------------------------------------


def list_for_patient(patient_id: int, caller: Caller) -> dict[str, Any]:
    today = date.today()
    with engine.connect() as conn:
        patient = _resolve_patient_or_404(
            conn, patient_id, caller.organization_id
        )
        meds_raw = _list_meds(
            conn, patient_id=patient["id"], org_id=caller.organization_id
        )
        refills_raw = _list_refills(
            conn, patient_id=patient["id"], org_id=caller.organization_id
        )
        allergies_raw = _list_allergies(
            conn, patient_id=patient["id"], org_id=caller.organization_id
        )

        user_ids: set[int] = set()
        for r in meds_raw + refills_raw + allergies_raw:
            uid = r.get("recorded_by_user_id")
            if uid is not None:
                user_ids.add(int(uid))
            puid = r.get("prescriber_user_id") if r in meds_raw else None
            if puid is not None:
                user_ids.add(int(puid))
        actors = _actor_cache(conn, user_ids)

    refills_by_med: dict[int, list[dict[str, Any]]] = {}
    for r in refills_raw:
        refills_by_med.setdefault(int(r["medication_id"]), []).append(r)

    medications: list[dict[str, Any]] = []
    refill_gaps: list[dict[str, Any]] = []
    preservative_burden = 0
    polypharmacy_count = 0
    for m in meds_raw:
        recorder = actors.get(
            int(m["recorded_by_user_id"]),
            {"display_name": None, "role": None},
        )
        prescriber = (
            actors.get(int(m["prescriber_user_id"]))
            if m.get("prescriber_user_id") is not None
            else None
        )
        active = _is_active(m, today=today)
        med = _serialize_medication(
            m,
            prescriber_display_name=(
                prescriber["display_name"] if prescriber else None
            ),
            recorder_display_name=recorder["display_name"],
            recorder_role=recorder["role"],
            active=active,
        )
        med_refills = refills_by_med.get(int(m["id"]), [])
        gap = _compute_refill_gap(m, med_refills, today=today)
        med["refill_gap"] = gap
        med["refill_count"] = len(med_refills)
        medications.append(med)
        if active:
            polypharmacy_count += 1
            if med["preservative_flag"] and m["route"] == "drops":
                preservative_burden += int(med["dose_per_day"])
            if gap["status"] == "gap":
                refill_gaps.append(
                    {
                        "medication_id": med["id"],
                        "medication_name": med["medication_name"],
                        "gap_days": gap["gap_days"],
                        "last_refill_date": gap["last_refill_date"],
                        "supply_through": gap["supply_through"],
                    }
                )

    allergies = [_serialize_allergy(a) for a in allergies_raw]
    refills = [_serialize_refill(r) for r in refills_raw]
    allergy_matches = _compute_allergy_matches(meds_raw, allergies_raw)

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "medications": medications,
        "refills": refills,
        "allergies": allergies,
        "supported_medication_classes": [
            {"code": code, "label": label}
            for code, label in MED_CLASS_LABELS.items()
        ],
        "supported_routes": sorted(VALID_ROUTES),
        "supported_lateralities": sorted(VALID_LATERALITIES),
        "supported_reaction_types": [
            {"code": code, "label": label}
            for code, label in REACTION_TYPE_LABELS.items()
        ],
        "supported_severities": sorted(VALID_SEVERITIES),
        "signals": {
            "polypharmacy_count": polypharmacy_count,
            "preservative_burden": preservative_burden,
            "refill_gaps": refill_gaps,
            "allergy_matches": allergy_matches,
            "insufficient_data": polypharmacy_count == 0,
        },
        "disclosure": _DISCLOSURE,
    }


def medication_safety_summary(
    patient_id: int, organization_id: int
) -> dict[str, Any]:
    """Lightweight metadata-only projection used by Phase 77 packet export
    and Phase 82 note validation. Pure counts; no clinical narrative."""
    today = date.today()
    with engine.connect() as conn:
        meds_raw = _list_meds(
            conn, patient_id=patient_id, org_id=organization_id
        )
        refills_raw = _list_refills(
            conn, patient_id=patient_id, org_id=organization_id
        )
        allergies_raw = _list_allergies(
            conn, patient_id=patient_id, org_id=organization_id
        )

    refills_by_med: dict[int, list[dict[str, Any]]] = {}
    for r in refills_raw:
        refills_by_med.setdefault(int(r["medication_id"]), []).append(r)

    active_count = 0
    preservative_burden = 0
    refill_gap_count = 0
    refill_gap_medication_ids: list[int] = []
    classes_present: set[str] = set()
    for m in meds_raw:
        if not _is_active(m, today=today):
            continue
        active_count += 1
        classes_present.add(m["medication_class"])
        if _truthy_bool(m.get("preservative_flag")) and m["route"] == "drops":
            preservative_burden += int(m["dose_per_day"])
        gap = _compute_refill_gap(
            m, refills_by_med.get(int(m["id"]), []), today=today
        )
        if gap["status"] == "gap":
            refill_gap_count += 1
            refill_gap_medication_ids.append(int(m["id"]))

    return {
        "active_medication_count": active_count,
        "preservative_burden": preservative_burden,
        "refill_gap_count": refill_gap_count,
        "refill_gap_medication_ids": refill_gap_medication_ids,
        "allergy_count": len(allergies_raw),
        "medication_classes_present": sorted(classes_present),
        "insufficient_data": active_count == 0,
    }


def patients_with_refill_gaps(organization_id: int) -> list[dict[str, Any]]:
    """Phase 81 hook — patients whose active drop/oral medications carry
    at least one refill gap (last_refill + expected_days_supply < today).
    Informational only; never tier 1."""
    today = date.today()
    with engine.connect() as conn:
        meds_raw = conn.execute(
            sa_text(
                f"SELECT {', '.join(_MED_COLS)} FROM medications "
                "WHERE organization_id = :oid"
            ),
            {"oid": organization_id},
        ).fetchall()
        refills_raw = conn.execute(
            sa_text(
                f"SELECT {', '.join(_REFILL_COLS)} FROM medication_refills "
                "WHERE organization_id = :oid"
            ),
            {"oid": organization_id},
        ).fetchall()

    refills_by_med: dict[int, list[dict[str, Any]]] = {}
    for r in refills_raw:
        rec = dict(zip(_REFILL_COLS, r))
        refills_by_med.setdefault(int(rec["medication_id"]), []).append(rec)

    by_patient: dict[int, list[dict[str, Any]]] = {}
    for m in meds_raw:
        med = dict(zip(_MED_COLS, m))
        if not _is_active(med, today=today):
            continue
        gap = _compute_refill_gap(
            med, refills_by_med.get(int(med["id"]), []), today=today
        )
        if gap["status"] != "gap":
            continue
        by_patient.setdefault(int(med["patient_id"]), []).append(
            {
                "medication_id": int(med["id"]),
                "medication_name": med["medication_name"],
                "medication_class": med["medication_class"],
                "gap_days": gap["gap_days"],
            }
        )

    out: list[dict[str, Any]] = []
    for pid, gaps in by_patient.items():
        out.append(
            {
                "patient_id": pid,
                "gap_count": len(gaps),
                "max_gap_days": max(g["gap_days"] for g in gaps),
                "medications": gaps,
            }
        )
    out.sort(key=lambda d: (-d["max_gap_days"], d["patient_id"]))
    return out


__all__ = [
    "MedicationError",
    "MED_CLASS_LABELS",
    "VALID_MED_CLASSES",
    "VALID_ROUTES",
    "VALID_LATERALITIES",
    "REACTION_TYPE_LABELS",
    "VALID_REACTION_TYPES",
    "VALID_SEVERITIES",
    "create_medication",
    "discontinue_medication",
    "create_refill",
    "create_allergy",
    "list_for_patient",
    "medication_safety_summary",
    "patients_with_refill_gaps",
]
