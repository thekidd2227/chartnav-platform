"""Phase 78 — Anti-VEGF retina operating rail.

Workflow intelligence — NOT diagnosis, treatment recommendation, image
interpretation, drug selection, autonomous orders, or autonomous
prior-auth submission. This service stores what the provider entered
about an administered injection and computes deterministic readiness
status from those fields.

The readiness queue answers operator-facing questions like:

  * which patients are due for an injection today / this week
  * which patients have a pending or expired prior authorization
  * which patients have asymmetric bilateral cadence (OD vs OS
    intervals diverged)

It does not answer clinical questions. The cadence the provider
recorded is the source of truth. ChartNav does not propose a new
cadence, does not choose a drug, does not choose a dose.

Hard rules (matching Phase 73 metadata-only audit pattern):

  * Public response shapes never include patient-identifiable PHI
    beyond what the encounter API already exposes (patient_id,
    patient_identifier, patient_name).
  * No clinical free text from notes is selected into the readiness
    queue projection — only metadata.
  * Every mutation is recorded with the caller's user_id so the
    audit trail is complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Constants — must match the alembic migration's CHECK constraints.
# ---------------------------------------------------------------------------

VALID_EYES = frozenset({"OD", "OS"})
VALID_DRUG_LABELS = frozenset(
    {
        "anti_vegf_generic",
        "anti_vegf_biosimilar",
        "anti_vegf_branded",
        "other",
    }
)
VALID_AUTH_STATUSES = frozenset(
    {
        "not_required",
        "pending",
        "approved",
        "denied",
        "expired",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Domain error so the route layer can translate to HTTPException.
# ---------------------------------------------------------------------------


@dataclass
class InjectionError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _validate_enum(name: str, value: str | None, allowed: frozenset[str]) -> str:
    if value is None or value not in allowed:
        raise InjectionError(
            "invalid_enum",
            f"{name} must be one of {sorted(allowed)}; got {value!r}",
            422,
        )
    return value


def _parse_date(name: str, raw: Any) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise InjectionError(
                "invalid_date",
                f"{name} must be ISO date (YYYY-MM-DD); got {raw!r}",
                422,
            ) from exc
    raise InjectionError(
        "invalid_date", f"{name} has unsupported type", 422
    )


def _resolve_patient_or_404(conn, patient_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise InjectionError("patient_not_found", "patient not found", 404)
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


def _resolve_encounter_or_none(
    conn, encounter_id: int | None, org_id: int, patient_id: int
) -> int | None:
    if encounter_id is None:
        return None
    row = conn.execute(
        sa_text(
            "SELECT id FROM encounters WHERE id = :eid AND "
            "organization_id = :oid AND (patient_id = :pid OR patient_id IS NULL)"
        ),
        {"eid": encounter_id, "oid": org_id, "pid": patient_id},
    ).fetchone()
    if row is None:
        raise InjectionError(
            "encounter_not_found",
            "encounter not found in your organization for this patient",
            404,
        )
    return int(row[0])


# ---------------------------------------------------------------------------
# Serialization.
# ---------------------------------------------------------------------------


_ROW_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "eye",
    "drug_label",
    "injection_date",
    "interval_weeks",
    "next_due_date",
    "authorization_status",
    "authorization_expires_on",
    "lot_number",
    "notes",
    "created_by_user_id",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for k in ("injection_date", "next_due_date", "authorization_expires_on"):
        if k in out:
            out[k] = _iso(out[k])
    for k in ("created_at", "updated_at"):
        if k in out:
            out[k] = _iso(out[k])
    return out


# ---------------------------------------------------------------------------
# RBAC: who can write injection records.
# ---------------------------------------------------------------------------


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician", "technician"}:
        raise InjectionError(
            "forbidden",
            "only admin, clinician, or technician can record injections",
            403,
        )


# ---------------------------------------------------------------------------
# Create one injection record.
# ---------------------------------------------------------------------------


def create_injection(
    patient_id: int,
    caller: Caller,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _assert_write_role(caller)

    eye = _validate_enum("eye", payload.get("eye"), VALID_EYES)
    drug_label = _validate_enum(
        "drug_label",
        payload.get("drug_label", "anti_vegf_generic"),
        VALID_DRUG_LABELS,
    )
    injection_date = _parse_date("injection_date", payload.get("injection_date"))
    if injection_date is None:
        raise InjectionError(
            "invalid_date",
            "injection_date is required",
            422,
        )

    interval_weeks = payload.get("interval_weeks")
    if interval_weeks is not None:
        if not isinstance(interval_weeks, int) or not (1 <= interval_weeks <= 52):
            raise InjectionError(
                "invalid_interval",
                "interval_weeks must be an integer between 1 and 52",
                422,
            )

    next_due_date = _parse_date("next_due_date", payload.get("next_due_date"))
    if next_due_date is None and interval_weeks is not None:
        next_due_date = injection_date + timedelta(weeks=interval_weeks)

    authorization_status = _validate_enum(
        "authorization_status",
        payload.get("authorization_status", "unknown"),
        VALID_AUTH_STATUSES,
    )
    authorization_expires_on = _parse_date(
        "authorization_expires_on", payload.get("authorization_expires_on")
    )

    lot_number = payload.get("lot_number")
    if lot_number is not None and (
        not isinstance(lot_number, str) or len(lot_number) > 64
    ):
        raise InjectionError(
            "invalid_lot_number",
            "lot_number must be a string up to 64 characters",
            422,
        )

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise InjectionError("invalid_notes", "notes must be a string", 422)

    with engine.begin() as conn:
        patient = _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        encounter_id = _resolve_encounter_or_none(
            conn, payload.get("encounter_id"), caller.organization_id, patient["id"]
        )
        new_id = insert_returning_id(
            conn,
            "anti_vegf_injections",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient["id"],
                "encounter_id": encounter_id,
                "eye": eye,
                "drug_label": drug_label,
                "injection_date": injection_date,
                "interval_weeks": interval_weeks,
                "next_due_date": next_due_date,
                "authorization_status": authorization_status,
                "authorization_expires_on": authorization_expires_on,
                "lot_number": lot_number,
                "notes": notes,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM anti_vegf_injections WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        return _serialize(dict(zip(_ROW_COLS, row)))


# ---------------------------------------------------------------------------
# List one patient's history (newest first per eye).
# ---------------------------------------------------------------------------


def list_history(
    patient_id: int, caller: Caller, *, eye: str | None = None
) -> dict[str, Any]:
    """Return injection history for one patient, split by eye + bilateral view."""
    if eye is not None:
        _validate_enum("eye", eye, VALID_EYES)

    with engine.connect() as conn:
        patient = _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        params: dict[str, Any] = {
            "pid": patient["id"],
            "oid": caller.organization_id,
        }
        where = "patient_id = :pid AND organization_id = :oid"
        if eye is not None:
            where += " AND eye = :eye"
            params["eye"] = eye

        rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM anti_vegf_injections "
                f"WHERE {where} ORDER BY injection_date DESC, id DESC"
            ),
            params,
        ).fetchall()

    records = [_serialize(dict(zip(_ROW_COLS, r))) for r in rows]
    od = [r for r in records if r["eye"] == "OD"]
    os_ = [r for r in records if r["eye"] == "OS"]

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "total_count": len(records),
        "od_count": len(od),
        "os_count": len(os_),
        "od_history": od,
        "os_history": os_,
        "latest_od": od[0] if od else None,
        "latest_os": os_[0] if os_ else None,
        "bilateral": bool(od) and bool(os_),
    }


# ---------------------------------------------------------------------------
# Readiness queue: deterministic buckets, no autonomous recommendations.
# ---------------------------------------------------------------------------


def _bucket_one(
    row: dict[str, Any], today: date
) -> tuple[str, dict[str, Any]] | None:
    """Classify one injection row into a readiness bucket.

    Buckets (mutually exclusive):
      * due_today           — next_due_date == today
      * due_this_week       — today < next_due_date <= today + 7 days
      * overdue             — next_due_date < today
      * authorization_pending  — auth status pending
      * authorization_expired  — auth expired OR expires_on past
      * (no bucket — row is omitted from the queue)
    """
    auth = row.get("authorization_status")
    auth_expires_raw = row.get("authorization_expires_on")
    next_due_raw = row.get("next_due_date")
    next_due = (
        date.fromisoformat(next_due_raw[:10]) if isinstance(next_due_raw, str) else None
    )
    auth_expires = (
        date.fromisoformat(auth_expires_raw[:10])
        if isinstance(auth_expires_raw, str)
        else None
    )

    base = {
        "injection_id": row["id"],
        "patient_id": row["patient_id"],
        "encounter_id": row["encounter_id"],
        "eye": row["eye"],
        "drug_label": row["drug_label"],
        "injection_date": row["injection_date"],
        "next_due_date": row["next_due_date"],
        "authorization_status": auth,
        "authorization_expires_on": row["authorization_expires_on"],
        "lot_number": row["lot_number"],
        "interval_weeks": row["interval_weeks"],
    }

    if auth == "expired" or (auth_expires is not None and auth_expires < today):
        return "authorization_expired", base
    if auth == "pending":
        return "authorization_pending", base
    if next_due is None:
        return None
    if next_due < today:
        return "overdue", base
    if next_due == today:
        return "due_today", base
    if next_due <= today + timedelta(days=7):
        return "due_this_week", base
    return None


def build_readiness_queue(
    caller: Caller, *, today: date | None = None
) -> dict[str, Any]:
    """Build the deterministic readiness queue for the caller's org.

    Iterates the latest injection per (patient, eye) so a patient with
    multiple historical records only contributes one entry per eye.
    """
    today = today or datetime.now(timezone.utc).date()

    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT a.id, a.patient_id, a.encounter_id, a.eye, a.drug_label, "
                "a.injection_date, a.interval_weeks, a.next_due_date, "
                "a.authorization_status, a.authorization_expires_on, a.lot_number, "
                "p.patient_identifier, p.first_name, p.last_name "
                "FROM anti_vegf_injections a "
                "JOIN patients p ON p.id = a.patient_id "
                "WHERE a.organization_id = :oid "
                "ORDER BY a.patient_id, a.eye, a.injection_date DESC, a.id DESC"
            ),
            {"oid": caller.organization_id},
        ).fetchall()

    cols = (
        "id", "patient_id", "encounter_id", "eye", "drug_label",
        "injection_date", "interval_weeks", "next_due_date",
        "authorization_status", "authorization_expires_on", "lot_number",
        "patient_identifier", "first_name", "last_name",
    )

    # Take only the latest row per (patient_id, eye).
    seen: set[tuple[int, str]] = set()
    latest_rows: list[dict[str, Any]] = []
    for r in rows:
        d = dict(zip(cols, r))
        d["injection_date"] = _iso(d["injection_date"])
        d["next_due_date"] = _iso(d["next_due_date"])
        d["authorization_expires_on"] = _iso(d["authorization_expires_on"])
        key = (int(d["patient_id"]), d["eye"])
        if key in seen:
            continue
        seen.add(key)
        latest_rows.append(d)

    buckets: dict[str, list[dict[str, Any]]] = {
        "due_today": [],
        "due_this_week": [],
        "overdue": [],
        "authorization_pending": [],
        "authorization_expired": [],
    }

    for r in latest_rows:
        classified = _bucket_one(r, today)
        if classified is None:
            continue
        bucket, base = classified
        name_parts = [p for p in (r.get("first_name"), r.get("last_name")) if p]
        base["patient_identifier"] = r["patient_identifier"]
        base["patient_name"] = " ".join(name_parts) if name_parts else None
        buckets[bucket].append(base)

    # Bilateral-asymmetry summary: for each patient, did OD and OS land
    # in different buckets? Useful operator signal — does not imply any
    # clinical decision.
    per_patient: dict[int, dict[str, str]] = {}
    for bucket, items in buckets.items():
        for it in items:
            pid = int(it["patient_id"])
            per_patient.setdefault(pid, {})[it["eye"]] = bucket

    bilateral_asymmetric: list[dict[str, Any]] = []
    for pid, eyes in per_patient.items():
        if "OD" in eyes and "OS" in eyes and eyes["OD"] != eyes["OS"]:
            bilateral_asymmetric.append(
                {
                    "patient_id": pid,
                    "od_bucket": eyes["OD"],
                    "os_bucket": eyes["OS"],
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today": today.isoformat(),
        "organization_id": caller.organization_id,
        "demo_mode": True,
        "buckets": buckets,
        "bilateral_asymmetric": bilateral_asymmetric,
        "totals": {bucket: len(items) for bucket, items in buckets.items()},
        "disclosure": (
            "ChartNav records the cadence the provider entered. It does not "
            "recommend an injection, a drug, or a dose. It does not interpret "
            "imaging. Authorization status is provider-entered and not a "
            "ChartNav decision."
        ),
    }


__all__ = [
    "InjectionError",
    "VALID_EYES",
    "VALID_DRUG_LABELS",
    "VALID_AUTH_STATUSES",
    "create_injection",
    "list_history",
    "build_readiness_queue",
]
