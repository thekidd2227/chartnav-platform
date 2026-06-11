"""Phase 90 — Ophthalmic Medication Safety & Adherence Engine service.

Provider-reviewed medication safety + adherence support. Reads the
Phase 85 ``medications`` table (now extended with adherence + review
columns by the Phase 90 migration) and walks the deterministic
rule registry to surface ``medication_safety_events`` rows.

HARD RULES — read this before changing the file.

  * ChartNav does NOT prescribe.
  * ChartNav does NOT recommend a medication, recommend stopping
    or changing a medication, recommend escalation, recommend
    surgery cancellation, or recommend treatment.
  * ChartNav does NOT diagnose, interpret images, or place orders.
  * Every rule message is templated. The medication name is
    structured metadata, not a clinical narrative.
  * Severity ``hard_stop`` is RESERVED for a future qualified-
    operator extension. The Phase 90 seeded rules use ``advisory``
    only. ``alert`` is reserved for a future curated-operator
    extension.
  * Only admin / clinician may acknowledge an event or POST a new
    medication record.
  * Cross-org access returns 404 (no existence leak).
  * Acknowledgement persists as metadata only — no clinical free
    text on the persisted row.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Closed allowlists
# ---------------------------------------------------------------------------

VALID_PRESERVATIVE_TYPES = frozenset(
    {"BAK", "preservative_free", "other", "unknown"}
)

VALID_EVENT_SEVERITIES = frozenset({"hard_stop", "alert", "advisory"})

VALID_RULE_SEVERITIES = VALID_EVENT_SEVERITIES

VALID_EVENT_STATUSES = frozenset({"active", "acknowledged", "resolved"})

VALID_RULE_STATUSES = frozenset({"active", "inactive"})

VALID_EVENT_LATERALITIES = frozenset({"OD", "OS", "OU", "none"})


# Rule keys — the deterministic registry. Seeded as DEMO rules. A
# qualified operator can add organization-scoped rules via a future
# admin surface; Phase 90 ships the rule keys themselves only.
RULE_KEY_PRESERVATIVE_BURDEN = "ophth_preservative_burden_advisory"
RULE_KEY_REFILL_GAP = "ophth_refill_gap_advisory"
RULE_KEY_CATARACT_ALPHA_BLOCKER = "ophth_cataract_alpha_blocker_review"
RULE_KEY_DUPLICATE_CLASS = "ophth_duplicate_class_advisory"
RULE_KEY_REVIEW_MISSING = "ophth_medication_review_missing_advisory"

SEEDED_RULE_KEYS = frozenset(
    {
        RULE_KEY_PRESERVATIVE_BURDEN,
        RULE_KEY_REFILL_GAP,
        RULE_KEY_CATARACT_ALPHA_BLOCKER,
        RULE_KEY_DUPLICATE_CLASS,
        RULE_KEY_REVIEW_MISSING,
    }
)

# Thresholds (deterministic, documented).
PRESERVATIVE_BURDEN_THRESHOLD = 3
REFILL_GAP_THRESHOLD_DAYS = 7
REVIEW_STALE_THRESHOLD_DAYS = 365

# Alpha-blocker classes / substrings that trigger the cataract review.
# Phase 90 uses provider-entered medication_class only — no NLP, no
# free-text inference.
_CATARACT_ALPHA_CLASSES = frozenset(
    {"alpha_agonist"}  # closest mapping from Phase 85's enum
)
# Substring matched against medication_name for the IFIS/tamsulosin
# review reminder. Case-insensitive.
_CATARACT_ALPHA_NAME_TOKENS = (
    "tamsulosin", "flomax", "doxazosin", "terazosin", "silodosin",
)


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class MedicationSafetyError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _enum(name: str, value: Any, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise MedicationSafetyError(
            f"invalid_{name}",
            f"{name} must be one of {sorted(allowed)}; got {value!r}",
            422,
        )
    return value


def _text(name: str, value: Any, *, max_len: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MedicationSafetyError(
            "invalid_text", f"{name} must be a non-empty string", 422
        )
    s = value.strip()
    if len(s) > max_len:
        raise MedicationSafetyError(
            "invalid_text",
            f"{name} must be at most {max_len} characters",
            422,
        )
    return s


def _opt_int_range(
    name: str, value: Any, *, lo: int, hi: int
) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise MedicationSafetyError(
            f"invalid_{name}", f"{name} must be an integer", 422
        )
    if value < lo or value > hi:
        raise MedicationSafetyError(
            f"invalid_{name}",
            f"{name} must be between {lo} and {hi}; got {value}",
            422,
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
            raise MedicationSafetyError(
                f"invalid_{name}",
                f"{name} must be ISO date YYYY-MM-DD",
                422,
            )
    raise MedicationSafetyError(
        f"invalid_{name}", f"{name} must be a date or null", 422
    )


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise MedicationSafetyError(
            "forbidden",
            "only admin or clinician can write medication safety records",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_patient_or_404(
    conn, patient_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise MedicationSafetyError(
            "patient_not_found", "patient not found", 404
        )
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


def _resolve_encounter_or_404(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id "
            "FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise MedicationSafetyError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return {
        "id": int(row[0]),
        "organization_id": int(row[1]),
        "patient_id": int(row[2]) if row[2] is not None else None,
    }


def _resolve_event_or_404(
    conn, event_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_EVENT_COLS)} FROM medication_safety_events "
            "WHERE id = :id AND organization_id = :oid"
        ),
        {"id": event_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise MedicationSafetyError(
            "event_not_found",
            "medication safety event not found in your organization",
            404,
        )
    return dict(zip(_EVENT_COLS, row))


def _actor_cache(
    conn, user_ids: Iterable[int]
) -> dict[int, dict[str, str | None]]:
    ids = sorted({int(u) for u in user_ids if u is not None})
    out: dict[int, dict[str, str | None]] = {}
    if not ids:
        return out
    placeholders = ", ".join(f":u{i}" for i in range(len(ids)))
    params: dict[str, Any] = {}
    for i, uid in enumerate(ids):
        params[f"u{i}"] = uid
    rows = conn.execute(
        sa_text(
            "SELECT id, full_name, email, role FROM users "
            f"WHERE id IN ({placeholders})"
        ),
        params,
    ).fetchall()
    for uid, full_name, email, role in rows:
        out[int(uid)] = {
            "display_name": full_name or email,
            "role": role,
        }
    return out


# ---------------------------------------------------------------------------
# Row schemas
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
    "preservative_type",
    "started_on",
    "discontinued_on",
    "last_fill_date",
    "days_supply",
    "prescriber_user_id",
    "prescriber_display_name",
    "recorded_by_user_id",
    "reviewed_by_user_id",
    "reviewed_at",
    "recorded_at",
    "created_at",
    "updated_at",
)

_RULE_COLS = (
    "id",
    "organization_id",
    "rule_key",
    "rule_name",
    "medication_class",
    "trigger_context",
    "severity",
    "message",
    "requires_acknowledgement",
    "status",
    "created_at",
    "updated_at",
)

_EVENT_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "medication_id",
    "rule_key",
    "severity",
    "laterality",
    "status",
    "message",
    "acknowledged_by_user_id",
    "acknowledged_at",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "t", "true", "y", "yes"}
    return bool(value)


def _serialize_medication(
    rec: dict[str, Any], *, today: date | None = None
) -> dict[str, Any]:
    today = today or date.today()
    discontinued = _parse_date(rec.get("discontinued_on"))
    active = discontinued is None or discontinued > today
    last_fill = _parse_date(rec.get("last_fill_date"))
    days_supply = (
        int(rec["days_supply"]) if rec.get("days_supply") is not None else None
    )
    supply_through = None
    refill_gap_days = None
    if last_fill is not None and days_supply is not None:
        supply_through = last_fill.fromordinal(
            last_fill.toordinal() + days_supply
        )
        delta = (today - supply_through).days
        refill_gap_days = max(0, delta)
    return {
        "id": int(rec["id"]),
        "organization_id": int(rec["organization_id"]),
        "patient_id": int(rec["patient_id"]),
        "encounter_id": (
            int(rec["encounter_id"])
            if rec.get("encounter_id") is not None
            else None
        ),
        "medication_name": rec["medication_name"],
        "medication_class": rec["medication_class"],
        "route": rec["route"],
        "laterality": rec["laterality"],
        "dose_per_day": int(rec["dose_per_day"]),
        "preservative_flag": _truthy(rec.get("preservative_flag")),
        "preservative_type": rec.get("preservative_type") or "unknown",
        "started_on": _iso(rec.get("started_on")),
        "discontinued_on": _iso(discontinued),
        "last_fill_date": _iso(last_fill),
        "days_supply": days_supply,
        "supply_through": _iso(supply_through),
        "refill_gap_days": refill_gap_days,
        "active": active,
        "reviewed_by_user_id": (
            int(rec["reviewed_by_user_id"])
            if rec.get("reviewed_by_user_id") is not None
            else None
        ),
        "reviewed_at": _iso(rec.get("reviewed_at")),
        "recorded_by_user_id": int(rec["recorded_by_user_id"]),
        "created_at": _iso(rec.get("created_at")),
        "updated_at": _iso(rec.get("updated_at")),
    }


def _serialize_event(
    rec: dict[str, Any],
    *,
    acknowledger_display: str | None = None,
    acknowledger_role: str | None = None,
) -> dict[str, Any]:
    return {
        "id": int(rec["id"]),
        "organization_id": int(rec["organization_id"]),
        "patient_id": int(rec["patient_id"]),
        "encounter_id": (
            int(rec["encounter_id"])
            if rec.get("encounter_id") is not None
            else None
        ),
        "medication_id": (
            int(rec["medication_id"])
            if rec.get("medication_id") is not None
            else None
        ),
        "rule_key": rec["rule_key"],
        "severity": rec["severity"],
        "laterality": rec.get("laterality") or "none",
        "status": rec["status"],
        "message": rec["message"],
        "acknowledged_by_user_id": (
            int(rec["acknowledged_by_user_id"])
            if rec.get("acknowledged_by_user_id") is not None
            else None
        ),
        "acknowledged_by_display_name": acknowledger_display,
        "acknowledged_by_role": acknowledger_role,
        "acknowledged_at": _iso(rec.get("acknowledged_at")),
        "created_at": _iso(rec.get("created_at")),
        "updated_at": _iso(rec.get("updated_at")),
    }


def _serialize_rule(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(rec["id"]),
        "organization_id": (
            int(rec["organization_id"])
            if rec.get("organization_id") is not None
            else None
        ),
        "rule_key": rec["rule_key"],
        "rule_name": rec["rule_name"],
        "medication_class": rec.get("medication_class"),
        "trigger_context": rec["trigger_context"],
        "severity": rec["severity"],
        "message": rec["message"],
        "requires_acknowledgement": _truthy(rec.get("requires_acknowledgement")),
        "status": rec["status"],
        "internal_demo_only": rec["rule_key"] in SEEDED_RULE_KEYS,
        "verified_for_clinical_use": rec["rule_key"] not in SEEDED_RULE_KEYS,
        "created_at": _iso(rec.get("created_at")),
        "updated_at": _iso(rec.get("updated_at")),
    }


_DISCLOSURE = (
    "Provider-reviewed medication safety workflow support. ChartNav "
    "does NOT prescribe, does NOT recommend a medication, does NOT "
    "recommend stopping or changing a medication, does NOT diagnose, "
    "does NOT recommend treatment or surgery, does NOT place orders, "
    "does NOT submit to pharmacies, payers, or EHRs. Safety signals "
    "are generated from structured provider-entered medication data. "
    "Internal demo rules must be verified by a qualified operator "
    "before any real-program use."
)


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


def _list_active_rules(
    conn, organization_id: int
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_RULE_COLS)} FROM medication_safety_rules "
            "WHERE status = 'active' "
            "AND (organization_id IS NULL OR organization_id = :oid)"
        ),
        {"oid": organization_id},
    ).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        rec = dict(zip(_RULE_COLS, r))
        # Org-scoped wins over global with the same rule_key.
        if rec["rule_key"] in out and rec["organization_id"] is None:
            continue
        out[rec["rule_key"]] = rec
    return out


def _list_medications(
    conn, *, patient_id: int, organization_id: int
) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            f"SELECT {', '.join(_MED_COLS)} FROM medications "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "ORDER BY recorded_at DESC, id DESC"
        ),
        {"pid": patient_id, "oid": organization_id},
    ).fetchall()
    return [dict(zip(_MED_COLS, r)) for r in rows]


def _has_active_cataract_workflow(
    conn, *, patient_id: int, organization_id: int
) -> bool:
    row = conn.execute(
        sa_text(
            "SELECT id FROM cataract_workflow_records "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "LIMIT 1"
        ),
        {"pid": patient_id, "oid": organization_id},
    ).fetchone()
    return row is not None


def _is_alpha_blocker(med: dict[str, Any]) -> bool:
    if med.get("medication_class") in _CATARACT_ALPHA_CLASSES:
        return True
    name = (med.get("medication_name") or "").lower()
    return any(tok in name for tok in _CATARACT_ALPHA_NAME_TOKENS)


def _build_target_events(
    *,
    rules: dict[str, dict[str, Any]],
    medications: list[dict[str, Any]],
    has_cataract: bool,
    today: date,
) -> list[dict[str, Any]]:
    """Pure projection: given the rule set + meds + cataract flag, what
    safety events SHOULD exist right now?

    Returns a list of dicts with: rule_key, medication_id (nullable),
    severity, laterality, message. Stable order: rule_key, then
    medication_id.
    """
    actives = [m for m in medications if _truthy(m.get("preservative_flag")) or True]
    # The above is intentionally kept simple — we use the serialized
    # active flag below where it matters.
    actives = []
    for m in medications:
        disc = _parse_date(m.get("discontinued_on"))
        if disc is None or disc > today:
            actives.append(m)

    out: list[dict[str, Any]] = []

    # Preservative burden — count BAK-preserved active drops.
    rule = rules.get(RULE_KEY_PRESERVATIVE_BURDEN)
    if rule is not None:
        bak_count = sum(
            1
            for m in actives
            if m.get("route") == "drops"
            and (m.get("preservative_type") or "").upper() == "BAK"
        )
        if bak_count >= PRESERVATIVE_BURDEN_THRESHOLD:
            out.append(
                {
                    "rule_key": RULE_KEY_PRESERVATIVE_BURDEN,
                    "medication_id": None,
                    "severity": rule["severity"],
                    "laterality": "none",
                    "message": (
                        f"Provider review advisory: {bak_count} active "
                        "BAK-preserved drop(s) on the medication list. "
                        "ChartNav does not recommend a medication change."
                    ),
                }
            )

    # Refill gap — per medication.
    rule = rules.get(RULE_KEY_REFILL_GAP)
    if rule is not None:
        for m in actives:
            last = _parse_date(m.get("last_fill_date"))
            supply = m.get("days_supply")
            if last is None or supply is None:
                continue
            supply_through = date.fromordinal(
                last.toordinal() + int(supply)
            )
            gap = (today - supply_through).days
            if gap > REFILL_GAP_THRESHOLD_DAYS:
                out.append(
                    {
                        "rule_key": RULE_KEY_REFILL_GAP,
                        "medication_id": int(m["id"]),
                        "severity": rule["severity"],
                        "laterality": (m.get("laterality") or "none"),
                        "message": (
                            f"Provider review advisory: refill gap of "
                            f"{gap} day(s) on {m['medication_name']}. "
                            "Provider review required."
                        ),
                    }
                )

    # Cataract + alpha-blocker review reminder.
    rule = rules.get(RULE_KEY_CATARACT_ALPHA_BLOCKER)
    if rule is not None and has_cataract:
        for m in actives:
            if _is_alpha_blocker(m):
                out.append(
                    {
                        "rule_key": RULE_KEY_CATARACT_ALPHA_BLOCKER,
                        "medication_id": int(m["id"]),
                        "severity": rule["severity"],
                        "laterality": "none",
                        "message": (
                            "Provider review advisory: cataract workflow "
                            "record on file with active alpha-blocker class "
                            f"medication ({m['medication_name']}). "
                            "Provider review required; ChartNav does not "
                            "recommend a medication change or surgical decision."
                        ),
                    }
                )

    # Duplicate class — 2+ active drops in the same class.
    rule = rules.get(RULE_KEY_DUPLICATE_CLASS)
    if rule is not None:
        by_class: dict[str, list[dict[str, Any]]] = {}
        for m in actives:
            if m.get("route") != "drops":
                continue
            by_class.setdefault(m["medication_class"], []).append(m)
        for klass, group in by_class.items():
            if len(group) >= 2:
                # One event per duplicate class, attributed to the first
                # medication for stable identity.
                first = sorted(group, key=lambda x: int(x["id"]))[0]
                names = ", ".join(
                    sorted({m["medication_name"] for m in group})
                )
                out.append(
                    {
                        "rule_key": RULE_KEY_DUPLICATE_CLASS,
                        "medication_id": int(first["id"]),
                        "severity": rule["severity"],
                        "laterality": "none",
                        "message": (
                            f"Provider review advisory: {len(group)} active "
                            f"{klass} drop(s) on file ({names}). "
                            "Provider review required."
                        ),
                    }
                )

    # Medication review missing — at least one active med, none reviewed
    # or recorded within the threshold window. A freshly-recorded
    # medication counts as an implicit review (recording IS review).
    rule = rules.get(RULE_KEY_REVIEW_MISSING)
    if rule is not None and actives:
        cutoff_ord = today.toordinal() - REVIEW_STALE_THRESHOLD_DAYS
        recent_review = False
        for m in actives:
            candidates: list[Any] = [
                m.get("reviewed_at"),
                m.get("recorded_at"),
                m.get("updated_at"),
            ]
            for cand in candidates:
                if cand is None:
                    continue
                try:
                    if isinstance(cand, datetime):
                        cand_date = cand.date()
                    elif isinstance(cand, date):
                        cand_date = cand
                    else:
                        cand_date = date.fromisoformat(str(cand)[:10])
                    if cand_date.toordinal() >= cutoff_ord:
                        recent_review = True
                        break
                except (ValueError, TypeError):
                    continue
            if recent_review:
                break
        if not recent_review:
            out.append(
                {
                    "rule_key": RULE_KEY_REVIEW_MISSING,
                    "medication_id": None,
                    "severity": rule["severity"],
                    "laterality": "none",
                    "message": (
                        f"Provider review advisory: {len(actives)} active "
                        "medication(s) without a recorded review in the "
                        f"last {REVIEW_STALE_THRESHOLD_DAYS} day(s). "
                        "Provider review required."
                    ),
                }
            )

    out.sort(
        key=lambda e: (e["rule_key"], e.get("medication_id") or 0)
    )
    return out


def _reconcile_events(
    conn,
    *,
    patient_id: int,
    organization_id: int,
    target: list[dict[str, Any]],
) -> None:
    """Materialize the target events for a patient. Idempotent.

    * Active events whose (rule_key, medication_id) are no longer in
      the target list are marked ``resolved``.
    * Active or acknowledged events that match the target are left
      untouched.
    * Target rows with no existing match are INSERTed as ``active``.
    """
    existing_rows = conn.execute(
        sa_text(
            "SELECT id, rule_key, medication_id, status, severity, message "
            "FROM medication_safety_events "
            "WHERE patient_id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": organization_id},
    ).fetchall()
    existing_index: dict[tuple[str, int | None], dict[str, Any]] = {}
    for r in existing_rows:
        key = (r[1], int(r[2]) if r[2] is not None else None)
        existing_index[key] = {
            "id": int(r[0]),
            "status": r[3],
            "severity": r[4],
            "message": r[5],
        }

    target_keys = {
        (t["rule_key"], t.get("medication_id")) for t in target
    }

    # Resolve no-longer-target active events.
    for key, rec in existing_index.items():
        if key in target_keys:
            continue
        if rec["status"] != "active":
            continue
        conn.execute(
            sa_text(
                "UPDATE medication_safety_events SET status = 'resolved', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": rec["id"]},
        )

    # Insert / re-activate target events.
    for t in target:
        key = (t["rule_key"], t.get("medication_id"))
        existing = existing_index.get(key)
        if existing is None:
            insert_returning_id(
                conn,
                "medication_safety_events",
                {
                    "organization_id": organization_id,
                    "patient_id": patient_id,
                    "encounter_id": None,
                    "medication_id": t.get("medication_id"),
                    "rule_key": t["rule_key"],
                    "severity": t["severity"],
                    "laterality": t.get("laterality") or "none",
                    "status": "active",
                    "message": t["message"],
                },
            )
        elif existing["status"] == "resolved":
            # Re-open + refresh metadata.
            conn.execute(
                sa_text(
                    "UPDATE medication_safety_events SET status = 'active', "
                    "severity = :sev, message = :msg, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {
                    "sev": t["severity"],
                    "msg": t["message"],
                    "id": existing["id"],
                },
            )
        elif existing["message"] != t["message"]:
            # Update message in-place if it drifted (e.g. count changed).
            conn.execute(
                sa_text(
                    "UPDATE medication_safety_events SET "
                    "severity = :sev, message = :msg, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {
                    "sev": t["severity"],
                    "msg": t["message"],
                    "id": existing["id"],
                },
            )


# ---------------------------------------------------------------------------
# Public API — writes
# ---------------------------------------------------------------------------


def create_medication(
    encounter_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    """Provider-entered ophthalmic medication record. Extends Phase 85's
    medications table with Phase 90 fields (preservative_type,
    last_fill_date, days_supply, reviewed_*).
    """
    _assert_write_role(caller)

    medication_name = _text(
        "medication_name", payload.get("medication_name"), max_len=128
    )
    medication_class = _text(
        "medication_class", payload.get("medication_class"), max_len=48
    )
    route = _text("route", payload.get("route"), max_len=16)
    laterality_raw = payload.get("laterality") or "NA"
    if laterality_raw not in {"OD", "OS", "OU", "NA"}:
        raise MedicationSafetyError(
            "invalid_laterality",
            "laterality must be OD / OS / OU / NA",
            422,
        )
    dose_per_day = payload.get("dose_per_day")
    if not isinstance(dose_per_day, int) or isinstance(dose_per_day, bool):
        raise MedicationSafetyError(
            "invalid_dose_per_day", "dose_per_day must be an integer", 422
        )
    if dose_per_day < 0 or dose_per_day > 24:
        raise MedicationSafetyError(
            "invalid_dose_per_day",
            f"dose_per_day must be 0-24; got {dose_per_day}",
            422,
        )
    preservative_type = _enum(
        "preservative_type",
        payload.get("preservative_type", "unknown"),
        VALID_PRESERVATIVE_TYPES,
    )
    preservative_flag = preservative_type == "BAK"
    started_on = _opt_date("started_on", payload.get("started_on"))
    discontinued_on = _opt_date(
        "discontinued_on", payload.get("discontinued_on")
    )
    last_fill_date = _opt_date(
        "last_fill_date", payload.get("last_fill_date")
    )
    days_supply = _opt_int_range(
        "days_supply", payload.get("days_supply"), lo=1, hi=365
    )

    with engine.begin() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        if encounter["patient_id"] is None:
            raise MedicationSafetyError(
                "patient_not_found",
                "encounter has no linked patient",
                404,
            )
        patient = _resolve_patient_or_404(
            conn, encounter["patient_id"], caller.organization_id
        )
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
                "laterality": laterality_raw,
                "dose_per_day": dose_per_day,
                "preservative_flag": preservative_flag,
                "preservative_type": preservative_type,
                "started_on": started_on,
                "discontinued_on": discontinued_on,
                "last_fill_date": last_fill_date,
                "days_supply": days_supply,
                "recorded_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_MED_COLS)} FROM medications WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        record = dict(zip(_MED_COLS, row))
        # Re-run safety rules now that the medication list changed.
        _refresh_patient_events(
            conn, patient_id=patient["id"], organization_id=caller.organization_id
        )

    return _serialize_medication(record)


def acknowledge_event(
    event_id: int, caller: Caller
) -> dict[str, Any]:
    _assert_write_role(caller)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        existing = _resolve_event_or_404(
            conn, event_id, caller.organization_id
        )
        if existing["status"] == "resolved":
            raise MedicationSafetyError(
                "event_resolved",
                "event already resolved; cannot acknowledge",
                409,
            )
        conn.execute(
            sa_text(
                "UPDATE medication_safety_events SET status = 'acknowledged', "
                "acknowledged_by_user_id = :uid, acknowledged_at = :ts, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"uid": caller.user_id, "ts": now, "id": event_id},
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_EVENT_COLS)} FROM medication_safety_events "
                "WHERE id = :id"
            ),
            {"id": event_id},
        ).fetchone()
        record = dict(zip(_EVENT_COLS, row))
        actors = _actor_cache(conn, [caller.user_id])
    actor = actors.get(caller.user_id)
    return _serialize_event(
        record,
        acknowledger_display=actor["display_name"] if actor else None,
        acknowledger_role=actor["role"] if actor else None,
    )


def _refresh_patient_events(
    conn, *, patient_id: int, organization_id: int
) -> None:
    today = date.today()
    rules = _list_active_rules(conn, organization_id)
    meds = _list_medications(
        conn, patient_id=patient_id, organization_id=organization_id
    )
    has_cataract = _has_active_cataract_workflow(
        conn, patient_id=patient_id, organization_id=organization_id
    )
    target = _build_target_events(
        rules=rules,
        medications=meds,
        has_cataract=has_cataract,
        today=today,
    )
    _reconcile_events(
        conn,
        patient_id=patient_id,
        organization_id=organization_id,
        target=target,
    )


# ---------------------------------------------------------------------------
# Public API — reads
# ---------------------------------------------------------------------------


def list_for_patient(
    patient_id: int, caller: Caller
) -> dict[str, Any]:
    today = date.today()
    with engine.begin() as conn:
        patient = _resolve_patient_or_404(
            conn, patient_id, caller.organization_id
        )
        # Refresh events so reads always reflect the deterministic
        # rule projection.
        _refresh_patient_events(
            conn,
            patient_id=patient["id"],
            organization_id=caller.organization_id,
        )
        meds_raw = _list_medications(
            conn,
            patient_id=patient["id"],
            organization_id=caller.organization_id,
        )
        event_rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_EVENT_COLS)} FROM medication_safety_events "
                "WHERE patient_id = :pid AND organization_id = :oid "
                "ORDER BY status ASC, created_at DESC, id DESC"
            ),
            {"pid": patient["id"], "oid": caller.organization_id},
        ).fetchall()
        rules = _list_active_rules(conn, caller.organization_id)
        actor_ids = {
            int(r[_EVENT_COLS.index("acknowledged_by_user_id")])
            for r in event_rows
            if r[_EVENT_COLS.index("acknowledged_by_user_id")] is not None
        }
        actors = _actor_cache(conn, actor_ids)

    medications = [
        _serialize_medication(m, today=today) for m in meds_raw
    ]
    active_meds = [m for m in medications if m["active"]]

    events: list[dict[str, Any]] = []
    for r in event_rows:
        rec = dict(zip(_EVENT_COLS, r))
        actor = (
            actors.get(int(rec["acknowledged_by_user_id"]))
            if rec.get("acknowledged_by_user_id") is not None
            else None
        )
        events.append(
            _serialize_event(
                rec,
                acknowledger_display=actor["display_name"] if actor else None,
                acknowledger_role=actor["role"] if actor else None,
            )
        )

    # Aggregate signals — pure metadata.
    preservative_burden_count = sum(
        1
        for m in active_meds
        if m["route"] == "drops" and m["preservative_type"] == "BAK"
    )
    refill_gaps = [
        {
            "medication_id": m["id"],
            "medication_name": m["medication_name"],
            "refill_gap_days": m["refill_gap_days"],
            "last_fill_date": m["last_fill_date"],
            "supply_through": m["supply_through"],
        }
        for m in active_meds
        if (m.get("refill_gap_days") or 0) > REFILL_GAP_THRESHOLD_DAYS
    ]
    reviewed_recently = sum(
        1 for m in active_meds if m["reviewed_at"] is not None
    )

    active_events = [e for e in events if e["status"] == "active"]
    acknowledged_events = [
        e for e in events if e["status"] == "acknowledged"
    ]

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "medications": medications,
        "active_medication_count": len(active_meds),
        "events": events,
        "counts": {
            "active_events": len(active_events),
            "acknowledged_events": len(acknowledged_events),
            "resolved_events": sum(
                1 for e in events if e["status"] == "resolved"
            ),
            "total_events": len(events),
        },
        "signals": {
            "preservative_burden_count": preservative_burden_count,
            "refill_gap_count": len(refill_gaps),
            "refill_gaps": refill_gaps,
            "active_medication_count": len(active_meds),
            "medications_reviewed_count": reviewed_recently,
            "insufficient_data": len(active_meds) == 0,
        },
        "rules": [_serialize_rule(r) for r in rules.values()],
        "internal_demo_rules_present": any(
            r["rule_key"] in SEEDED_RULE_KEYS for r in rules.values()
        ),
        "submission_status": "not_submitted",
        "disclosure": _DISCLOSURE,
    }


def analytics_summary(caller: Caller) -> dict[str, Any]:
    """Org-wide medication safety event rollup. Deterministic counts
    only — no PHI free text, no clinical interpretation."""
    with engine.connect() as conn:
        rule_rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_RULE_COLS)} FROM medication_safety_rules "
                "WHERE status = 'active' "
                "AND (organization_id IS NULL OR organization_id = :oid)"
            ),
            {"oid": caller.organization_id},
        ).fetchall()
        rules = [_serialize_rule(dict(zip(_RULE_COLS, r))) for r in rule_rows]

        ev_rows = conn.execute(
            sa_text(
                "SELECT rule_key, status, severity, COUNT(*) "
                "FROM medication_safety_events "
                "WHERE organization_id = :oid "
                "GROUP BY rule_key, status, severity"
            ),
            {"oid": caller.organization_id},
        ).fetchall()

    by_rule: dict[str, dict[str, Any]] = {}
    for r in rules:
        by_rule[r["rule_key"]] = {
            "rule_key": r["rule_key"],
            "rule_name": r["rule_name"],
            "severity": r["severity"],
            "internal_demo_only": r["internal_demo_only"],
            "verified_for_clinical_use": r["verified_for_clinical_use"],
            "active": 0,
            "acknowledged": 0,
            "resolved": 0,
            "total": 0,
        }
    for rk, status, severity, count in ev_rows:
        bucket = by_rule.setdefault(
            rk,
            {
                "rule_key": rk,
                "rule_name": rk,
                "severity": severity,
                "internal_demo_only": rk in SEEDED_RULE_KEYS,
                "verified_for_clinical_use": rk not in SEEDED_RULE_KEYS,
                "active": 0,
                "acknowledged": 0,
                "resolved": 0,
                "total": 0,
            },
        )
        if status in {"active", "acknowledged", "resolved"}:
            bucket[status] += int(count)
            bucket["total"] += int(count)

    return {
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "rules": list(by_rule.values()),
        "internal_demo_rules_present": any(
            r["internal_demo_only"] for r in by_rule.values()
        ),
        "submission_status": "not_submitted",
        "disclosure": _DISCLOSURE,
    }


def summary_for_encounter(
    encounter_id: int, organization_id: int
) -> dict[str, Any]:
    """Metadata-only projection used by Phase 76 summary and Phase 77
    packet. Counts only; no clinical free text; no submission."""
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, patient_id FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
        if row is None or row[1] is None:
            return _empty_summary()
        patient_id = int(row[1])
        meds_raw = _list_medications(
            conn,
            patient_id=patient_id,
            organization_id=organization_id,
        )
        event_rows = conn.execute(
            sa_text(
                "SELECT status, severity FROM medication_safety_events "
                "WHERE patient_id = :pid AND organization_id = :oid"
            ),
            {"pid": patient_id, "oid": organization_id},
        ).fetchall()

    today = date.today()
    active = [
        m for m in meds_raw
        if (
            _parse_date(m.get("discontinued_on")) is None
            or (_parse_date(m.get("discontinued_on")) or today) > today
        )
    ]
    preservative_burden = sum(
        1
        for m in active
        if m.get("route") == "drops"
        and (m.get("preservative_type") or "") == "BAK"
    )
    refill_gap_count = 0
    for m in active:
        last = _parse_date(m.get("last_fill_date"))
        supply = m.get("days_supply")
        if last is None or supply is None:
            continue
        st = date.fromordinal(last.toordinal() + int(supply))
        if (today - st).days > REFILL_GAP_THRESHOLD_DAYS:
            refill_gap_count += 1
    active_events = 0
    acknowledged_events = 0
    resolved_events = 0
    for status, _sev in event_rows:
        if status == "active":
            active_events += 1
        elif status == "acknowledged":
            acknowledged_events += 1
        elif status == "resolved":
            resolved_events += 1
    return {
        "active_medication_count": len(active),
        "preservative_burden_count": preservative_burden,
        "refill_gap_count": refill_gap_count,
        "active_event_count": active_events,
        "acknowledged_event_count": acknowledged_events,
        "resolved_event_count": resolved_events,
        "total_event_count": active_events + acknowledged_events + resolved_events,
        "internal_demo_rules_present": True,
        "submission_status": "not_submitted",
        "boundary_note": (
            "Medication safety content is provider-reviewed workflow "
            "support only."
        ),
        "insufficient_data": len(active) == 0,
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "active_medication_count": 0,
        "preservative_burden_count": 0,
        "refill_gap_count": 0,
        "active_event_count": 0,
        "acknowledged_event_count": 0,
        "resolved_event_count": 0,
        "total_event_count": 0,
        "internal_demo_rules_present": False,
        "submission_status": "not_submitted",
        "boundary_note": (
            "Medication safety content is provider-reviewed workflow "
            "support only."
        ),
        "insufficient_data": True,
    }


def patients_with_active_safety_events(
    organization_id: int,
) -> list[dict[str, Any]]:
    """Phase 81 hook — patients with one or more active medication
    safety events. Informational only; never tier 1."""
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT patient_id, COUNT(*) AS n "
                "FROM medication_safety_events "
                "WHERE organization_id = :oid AND status = 'active' "
                "GROUP BY patient_id "
                "ORDER BY n DESC, patient_id ASC"
            ),
            {"oid": organization_id},
        ).fetchall()
    return [
        {"patient_id": int(r[0]), "active_event_count": int(r[1])}
        for r in rows
    ]


__all__ = [
    "MedicationSafetyError",
    "VALID_PRESERVATIVE_TYPES",
    "VALID_EVENT_SEVERITIES",
    "VALID_EVENT_STATUSES",
    "VALID_EVENT_LATERALITIES",
    "SEEDED_RULE_KEYS",
    "RULE_KEY_PRESERVATIVE_BURDEN",
    "RULE_KEY_REFILL_GAP",
    "RULE_KEY_CATARACT_ALPHA_BLOCKER",
    "RULE_KEY_DUPLICATE_CLASS",
    "RULE_KEY_REVIEW_MISSING",
    "REFILL_GAP_THRESHOLD_DAYS",
    "PRESERVATIVE_BURDEN_THRESHOLD",
    "REVIEW_STALE_THRESHOLD_DAYS",
    "create_medication",
    "acknowledge_event",
    "list_for_patient",
    "analytics_summary",
    "summary_for_encounter",
    "patients_with_active_safety_events",
]
