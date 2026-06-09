"""Phase 80 — Cataract Surgical Workflow service.

Provider-reviewed surgical workflow support. NOT clinical intelligence.

ChartNav does NOT:

  * select an IOL power, model, or material
  * recommend a surgical technique (phaco vs ECCE vs FLACS)
  * recommend a surgery date or sequencing across eyes
  * infer complications from biometry / topography / imaging
  * autonomously order tests, refer, message patients, bill, or code
  * autonomously sign anything

Every value is provider-entered. Free-text fields (``target_refraction``,
``lens_plan_label``, ``complication_note``, ``notes``) are preserved
verbatim only on the single-record response. The per-eye summary
deliberately omits them so the deterministic workflow projection
never aggregates clinical free text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine, insert_returning_id


# ---------------------------------------------------------------------------
# Enums — must mirror the migration's CHECK constraints exactly.
# ---------------------------------------------------------------------------

VALID_SURGERY_EYES = frozenset({"OD", "OS"})
VALID_CONSENT_STATUSES = frozenset(
    {"not_obtained", "in_progress", "signed", "declined", "unknown"}
)
VALID_POSTOP_STATUSES = frozenset(
    {"not_scheduled", "scheduled", "completed", "missed", "unknown"}
)
_POSTOP_FIELDS = (
    "postop_day_1_status",
    "postop_week_1_status",
    "postop_month_1_status",
)


@dataclass
class WorkflowError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_enum(name: str, value: Any, allowed: frozenset[str]) -> str:
    if value is None or value not in allowed:
        raise WorkflowError(
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
            raise WorkflowError(
                "invalid_date",
                f"{name} must be ISO date (YYYY-MM-DD); got {raw!r}",
                422,
            ) from exc
    raise WorkflowError("invalid_date", f"{name} has unsupported type", 422)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "y", "t"}
    return default


def _coerce_text(name: str, raw: Any, *, max_len: int) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise WorkflowError("invalid_text", f"{name} must be a string", 422)
    if len(raw) > max_len:
        raise WorkflowError(
            "invalid_text",
            f"{name} must be at most {max_len} characters",
            422,
        )
    return raw


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise WorkflowError(
            "forbidden",
            "only admin or clinician can record cataract workflow rows",
            403,
        )


# ---------------------------------------------------------------------------
# Patient + biometry resolution
# ---------------------------------------------------------------------------


def _resolve_patient_or_404(conn, patient_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise WorkflowError("patient_not_found", "patient not found", 404)
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


def _resolve_biometry_or_none(
    conn, study_id: int | None, org_id: int, patient_id: int
) -> int | None:
    if study_id is None:
        return None
    row = conn.execute(
        sa_text(
            "SELECT id FROM imaging_studies WHERE id = :sid AND "
            "organization_id = :oid AND patient_id = :pid AND "
            "modality = 'biometry_packet'"
        ),
        {"sid": study_id, "oid": org_id, "pid": patient_id},
    ).fetchone()
    if row is None:
        raise WorkflowError(
            "biometry_study_not_found",
            "biometry_study_id must reference a biometry_packet study "
            "for this patient in your organization",
            404,
        )
    return int(row[0])


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
        raise WorkflowError(
            "encounter_not_found",
            "encounter not found in your organization for this patient",
            404,
        )
    return int(row[0])


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


_ROW_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "surgery_eye",
    "planned_surgery_date",
    "biometry_study_id",
    "biometry_reviewed",
    "topography_reviewed",
    "consent_status",
    "target_refraction",
    "lens_plan_label",
    "postop_day_1_status",
    "postop_week_1_status",
    "postop_month_1_status",
    "complications_flag",
    "complication_note",
    "notes",
    "created_by_user_id",
    "created_at",
    "updated_at",
)


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for k in ("planned_surgery_date", "created_at", "updated_at"):
        if k in out:
            out[k] = _iso(out[k])
    for k in ("biometry_reviewed", "topography_reviewed", "complications_flag"):
        if k in out:
            out[k] = bool(out[k])
    return out


# ---------------------------------------------------------------------------
# Create one record.
# ---------------------------------------------------------------------------


def create_record(
    patient_id: int, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    _assert_write_role(caller)

    surgery_eye = _validate_enum(
        "surgery_eye", payload.get("surgery_eye"), VALID_SURGERY_EYES
    )
    consent_status = _validate_enum(
        "consent_status",
        payload.get("consent_status", "unknown"),
        VALID_CONSENT_STATUSES,
    )
    postop_day = _validate_enum(
        "postop_day_1_status",
        payload.get("postop_day_1_status", "unknown"),
        VALID_POSTOP_STATUSES,
    )
    postop_week = _validate_enum(
        "postop_week_1_status",
        payload.get("postop_week_1_status", "unknown"),
        VALID_POSTOP_STATUSES,
    )
    postop_month = _validate_enum(
        "postop_month_1_status",
        payload.get("postop_month_1_status", "unknown"),
        VALID_POSTOP_STATUSES,
    )

    planned_surgery_date = _parse_date(
        "planned_surgery_date", payload.get("planned_surgery_date")
    )
    biometry_reviewed = _coerce_bool(payload.get("biometry_reviewed"))
    topography_reviewed = _coerce_bool(payload.get("topography_reviewed"))
    complications_flag = _coerce_bool(payload.get("complications_flag"))
    target_refraction = _coerce_text(
        "target_refraction", payload.get("target_refraction"), max_len=64
    )
    lens_plan_label = _coerce_text(
        "lens_plan_label", payload.get("lens_plan_label"), max_len=160
    )
    complication_note = _coerce_text(
        "complication_note", payload.get("complication_note"), max_len=2000
    )
    notes = _coerce_text("notes", payload.get("notes"), max_len=2000)

    with engine.begin() as conn:
        patient = _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        biometry_study_id = _resolve_biometry_or_none(
            conn,
            payload.get("biometry_study_id"),
            caller.organization_id,
            patient["id"],
        )
        encounter_id = _resolve_encounter_or_none(
            conn, payload.get("encounter_id"), caller.organization_id, patient["id"]
        )
        new_id = insert_returning_id(
            conn,
            "cataract_workflow_records",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient["id"],
                "encounter_id": encounter_id,
                "surgery_eye": surgery_eye,
                "planned_surgery_date": planned_surgery_date,
                "biometry_study_id": biometry_study_id,
                "biometry_reviewed": biometry_reviewed,
                "topography_reviewed": topography_reviewed,
                "consent_status": consent_status,
                "target_refraction": target_refraction,
                "lens_plan_label": lens_plan_label,
                "postop_day_1_status": postop_day,
                "postop_week_1_status": postop_week,
                "postop_month_1_status": postop_month,
                "complications_flag": complications_flag,
                "complication_note": complication_note,
                "notes": notes,
                "created_by_user_id": caller.user_id,
            },
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM cataract_workflow_records "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).fetchone()
        return _serialize(dict(zip(_ROW_COLS, row)))


# ---------------------------------------------------------------------------
# Per-eye lane builder
# ---------------------------------------------------------------------------


def _readiness_for_lane(latest: dict[str, Any] | None) -> dict[str, Any]:
    """Compute deterministic pre-op readiness signals from the latest row.

    Never recommends; never decides surgery is "ready". Just summarizes
    which provider-attested signals are present.
    """
    if latest is None:
        return {
            "has_planned_date": False,
            "biometry_reviewed": False,
            "topography_reviewed": False,
            "consent_signed": False,
            "score_numerator": 0,
            "score_denominator": 4,
        }
    has_planned = latest.get("planned_surgery_date") is not None
    biometry = bool(latest.get("biometry_reviewed"))
    topo = bool(latest.get("topography_reviewed"))
    consent_signed = latest.get("consent_status") == "signed"
    num = sum(int(b) for b in (has_planned, biometry, topo, consent_signed))
    return {
        "has_planned_date": has_planned,
        "biometry_reviewed": biometry,
        "topography_reviewed": topo,
        "consent_signed": consent_signed,
        "score_numerator": num,
        "score_denominator": 4,
    }


def _postop_completeness(latest: dict[str, Any] | None) -> dict[str, Any]:
    """Count how many post-op checkpoints have a non-unknown status."""
    out: dict[str, Any] = {}
    if latest is None:
        for field in _POSTOP_FIELDS:
            out[field] = "unknown"
        out["score_numerator"] = 0
        out["score_denominator"] = 3
        return out
    known = 0
    for field in _POSTOP_FIELDS:
        val = latest.get(field, "unknown")
        out[field] = val
        if val != "unknown":
            known += 1
    out["score_numerator"] = known
    out["score_denominator"] = 3
    return out


def _project_for_summary(row: dict[str, Any]) -> dict[str, Any]:
    """Summary projection — deliberately omits free-text fields.

    target_refraction, lens_plan_label, complication_note, and notes
    are NEVER included in this projection. The per-record GET surfaces
    them under explicit ``provider_entered`` labels.
    """
    return {
        "id": row["id"],
        "encounter_id": row["encounter_id"],
        "surgery_eye": row["surgery_eye"],
        "planned_surgery_date": row["planned_surgery_date"],
        "biometry_study_id": row["biometry_study_id"],
        "biometry_reviewed": row["biometry_reviewed"],
        "topography_reviewed": row["topography_reviewed"],
        "consent_status": row["consent_status"],
        "postop_day_1_status": row["postop_day_1_status"],
        "postop_week_1_status": row["postop_week_1_status"],
        "postop_month_1_status": row["postop_month_1_status"],
        "complications_flag": row["complications_flag"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------


def list_records(patient_id: int, caller: Caller) -> list[dict[str, Any]]:
    """Return raw records (provider-entered free text included)."""
    with engine.connect() as conn:
        _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM cataract_workflow_records "
                "WHERE patient_id = :pid AND organization_id = :oid "
                "ORDER BY id DESC"
            ),
            {"pid": patient_id, "oid": caller.organization_id},
        ).fetchall()
    return [_serialize(dict(zip(_ROW_COLS, r))) for r in rows]


def build_summary(patient_id: int, caller: Caller) -> dict[str, Any]:
    """Per-eye cataract workflow summary for one patient.

    Output shape:

        {
          "patient_id", "patient_identifier", "patient_name",
          "organization_id", "generated_at", "demo_mode",
          "od": {
            "eye": "OD",
            "record_count": int,
            "latest_record": <summary projection> | None,
            "preop_readiness": {has_planned_date, biometry_reviewed,
                                topography_reviewed, consent_signed,
                                score_numerator, score_denominator},
            "postop_cadence":  {postop_day_1_status, postop_week_1_status,
                                postop_month_1_status, score_*},
            "complications_flag": bool,
            "insufficient_data": bool,
          },
          "os": { ... same shape ... },
          "bilateral_planned": bool,
          "disclosure": "..."
        }
    """
    with engine.connect() as conn:
        patient = _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        rows = conn.execute(
            sa_text(
                f"SELECT {', '.join(_ROW_COLS)} FROM cataract_workflow_records "
                "WHERE patient_id = :pid AND organization_id = :oid "
                "ORDER BY id DESC"
            ),
            {"pid": patient["id"], "oid": caller.organization_id},
        ).fetchall()

    serialized = [_serialize(dict(zip(_ROW_COLS, r))) for r in rows]
    od_rows = [r for r in serialized if r["surgery_eye"] == "OD"]
    os_rows = [r for r in serialized if r["surgery_eye"] == "OS"]

    def build_lane(eye: str, lane_rows: list[dict[str, Any]]) -> dict[str, Any]:
        latest = lane_rows[0] if lane_rows else None
        latest_projection = _project_for_summary(latest) if latest else None
        readiness = _readiness_for_lane(latest)
        cadence = _postop_completeness(latest)
        insufficient = latest is None
        complications_flag = bool(latest["complications_flag"]) if latest else False
        return {
            "eye": eye,
            "record_count": len(lane_rows),
            "latest_record": latest_projection,
            "preop_readiness": readiness,
            "postop_cadence": cadence,
            "complications_flag": complications_flag,
            "insufficient_data": insufficient,
        }

    od_lane = build_lane("OD", od_rows)
    os_lane = build_lane("OS", os_rows)
    bilateral_planned = bool(
        od_lane["latest_record"]
        and od_lane["latest_record"]["planned_surgery_date"]
        and os_lane["latest_record"]
        and os_lane["latest_record"]["planned_surgery_date"]
    )

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "od": od_lane,
        "os": os_lane,
        "bilateral_planned": bilateral_planned,
        "disclosure": (
            "Provider-entered cataract surgical workflow support. ChartNav "
            "does not select an IOL power, does not recommend a surgical "
            "technique, does not recommend a surgery date, does not infer "
            "complications, and does not order tests. Free-text fields "
            "(target refraction, lens plan, complication note, notes) are "
            "provider-entered and stored verbatim."
        ),
    }


__all__ = [
    "VALID_SURGERY_EYES",
    "VALID_CONSENT_STATUSES",
    "VALID_POSTOP_STATUSES",
    "WorkflowError",
    "create_record",
    "list_records",
    "build_summary",
]
