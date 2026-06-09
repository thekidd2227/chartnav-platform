"""Phase 79 — Glaucoma Progression Cockpit aggregator service.

Pure aggregation across existing structured data — no new tables, no
new schema. Reads from:

  * ``visit_vitals_workups`` — for IOP per-eye history (`iop_od`,
    `iop_os`, `iop_method`)
  * ``imaging_studies``      — for visual-field and OCT review state
    (modalities `visual_field_24_2` / `visual_field_10_2` /
    `oct_rnfl` / `oct_macula`)

Returns a per-eye structure with:
  * IOP history (chronological)
  * visual-field study summary (latest captured / reviewed state +
    count + insufficient_data flag)
  * OCT RNFL study summary
  * OCT macula study summary
  * data_completeness scoring

Hard rules (matching every Phase 2 surface):

  * ChartNav does not interpret the IOP trend.
  * ChartNav does not classify progression (stable / slow / rapid /
    advanced).
  * ChartNav does not recommend medication, laser, or surgery.
  * ChartNav does not autonomously interpret VF or OCT.
  * Missing data is surfaced honestly as ``insufficient_data``; values
    are never invented to fill gaps.

The response is metadata-only — no clinical free text (notes column on
``imaging_studies`` is deliberately omitted from the per-modality
projection).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Literal

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Modality groups used by the cockpit (subset of imaging_studies modalities).
# ---------------------------------------------------------------------------

VISUAL_FIELD_MODALITIES = ("visual_field_24_2", "visual_field_10_2")
OCT_RNFL_MODALITIES = ("oct_rnfl",)
OCT_MACULA_MODALITIES = ("oct_macula",)

Eye = Literal["OD", "OS"]


@dataclass
class SummaryError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_patient_or_404(conn, patient_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE id = :pid AND organization_id = :oid"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise SummaryError("patient_not_found", "patient not found", 404)
    pid, pident, first, last = row
    name_parts = [p for p in (first, last) if p]
    return {
        "id": int(pid),
        "patient_identifier": pident,
        "patient_name": " ".join(name_parts) if name_parts else None,
    }


# ---------------------------------------------------------------------------
# IOP history aggregator.
# ---------------------------------------------------------------------------


def _fetch_iop_history(
    conn, patient_id: int, org_id: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (od_iop_history, os_iop_history), newest first."""
    rows = conn.execute(
        sa_text(
            "SELECT id, encounter_id, iop_od, iop_os, iop_method, "
            "status, signed_at, reviewed_at, created_at "
            "FROM visit_vitals_workups "
            "WHERE patient_id = :pid AND organization_id = :oid "
            "AND (iop_od IS NOT NULL OR iop_os IS NOT NULL) "
            "ORDER BY created_at DESC, id DESC"
        ),
        {"pid": patient_id, "oid": org_id},
    ).fetchall()

    od: list[dict[str, Any]] = []
    os_: list[dict[str, Any]] = []

    for r in rows:
        (wid, eid, iod, ios, method, status, signed_at, reviewed_at, created_at) = r
        signed = signed_at is not None
        common = {
            "vitals_workup_id": int(wid),
            "encounter_id": int(eid) if eid is not None else None,
            "method": method,
            "status": status,
            "signed": signed,
            "reviewed_at": _iso(reviewed_at),
            "signed_at": _iso(signed_at),
            "recorded_at": _iso(created_at),
        }
        iod_f = _to_float(iod)
        if iod_f is not None:
            od.append({**common, "eye": "OD", "value": iod_f})
        ios_f = _to_float(ios)
        if ios_f is not None:
            os_.append({**common, "eye": "OS", "value": ios_f})

    return od, os_


# ---------------------------------------------------------------------------
# Imaging-study aggregator (per modality, per eye).
# ---------------------------------------------------------------------------


def _fetch_modality_summary(
    conn,
    *,
    patient_id: int,
    org_id: int,
    eye: Eye,
    modalities: tuple[str, ...],
) -> dict[str, Any]:
    """Return summary for one modality group on one eye.

    Eye filter accepts the eye plus 'OU' (both-eye studies count for
    both per-eye lanes).
    """
    placeholders = ", ".join(f":m{i}" for i in range(len(modalities)))
    params: dict[str, Any] = {
        "pid": patient_id,
        "oid": org_id,
        "eye": eye,
    }
    for i, m in enumerate(modalities):
        params[f"m{i}"] = m

    # Order by (captured_at IS NULL, captured_at DESC, id DESC) — the
    # boolean CASE ranks non-null captured_at rows first on both SQLite
    # and Postgres without resorting to dialect-specific NULLS LAST.
    rows = conn.execute(
        sa_text(
            "SELECT id, modality, eye, status, captured_at, reviewed_at, "
            "reviewed_by_user_id, created_at "
            f"FROM imaging_studies WHERE patient_id = :pid AND organization_id = :oid "
            f"AND modality IN ({placeholders}) "
            "AND eye IN (:eye, 'OU') "
            "ORDER BY CASE WHEN captured_at IS NULL THEN 1 ELSE 0 END, "
            "captured_at DESC, id DESC"
        ),
        params,
    ).fetchall()

    count = len(rows)
    if count == 0:
        return {
            "count": 0,
            "latest_id": None,
            "latest_modality": None,
            "latest_status": None,
            "latest_captured_at": None,
            "latest_reviewed_at": None,
            "latest_reviewed_by_user_id": None,
            "insufficient_data": True,
        }
    latest = rows[0]
    sid, mod, _e, status, captured_at, reviewed_at, reviewed_by, _created_at = latest
    return {
        "count": count,
        "latest_id": int(sid),
        "latest_modality": mod,
        "latest_status": status,
        "latest_captured_at": _iso(captured_at),
        "latest_reviewed_at": _iso(reviewed_at),
        "latest_reviewed_by_user_id": (
            int(reviewed_by) if reviewed_by is not None else None
        ),
        "insufficient_data": False,
    }


# ---------------------------------------------------------------------------
# Data-completeness scoring.
# ---------------------------------------------------------------------------


def _completeness(
    iop_history: list[dict[str, Any]],
    visual_field: dict[str, Any],
    oct_rnfl: dict[str, Any],
) -> dict[str, Any]:
    """Three boolean signals + a fraction. Not a clinical score."""
    has_iop = len(iop_history) > 0
    has_visual_field = visual_field["count"] > 0
    has_oct_rnfl = oct_rnfl["count"] > 0
    score_num = int(has_iop) + int(has_visual_field) + int(has_oct_rnfl)
    return {
        "has_iop": has_iop,
        "has_visual_field": has_visual_field,
        "has_oct_rnfl": has_oct_rnfl,
        "score_numerator": score_num,
        "score_denominator": 3,
    }


def _build_lane(
    conn,
    *,
    patient_id: int,
    org_id: int,
    eye: Eye,
    iop_history: list[dict[str, Any]],
) -> dict[str, Any]:
    visual_field = _fetch_modality_summary(
        conn,
        patient_id=patient_id,
        org_id=org_id,
        eye=eye,
        modalities=VISUAL_FIELD_MODALITIES,
    )
    oct_rnfl = _fetch_modality_summary(
        conn,
        patient_id=patient_id,
        org_id=org_id,
        eye=eye,
        modalities=OCT_RNFL_MODALITIES,
    )
    oct_macula = _fetch_modality_summary(
        conn,
        patient_id=patient_id,
        org_id=org_id,
        eye=eye,
        modalities=OCT_MACULA_MODALITIES,
    )
    latest_iop = iop_history[0] if iop_history else None
    completeness = _completeness(iop_history, visual_field, oct_rnfl)
    insufficient = (
        not completeness["has_iop"]
        and not completeness["has_visual_field"]
        and not completeness["has_oct_rnfl"]
    )
    return {
        "eye": eye,
        "iop_history": iop_history,
        "latest_iop": latest_iop,
        "iop_count": len(iop_history),
        "visual_field": visual_field,
        "oct_rnfl": oct_rnfl,
        "oct_macula": oct_macula,
        "data_completeness": completeness,
        "insufficient_data": insufficient,
    }


# ---------------------------------------------------------------------------
# Public entrypoint.
# ---------------------------------------------------------------------------


def build_glaucoma_summary(patient_id: int, caller: Caller) -> dict[str, Any]:
    """Aggregate the per-eye glaucoma cockpit view for one patient."""
    with engine.connect() as conn:
        patient = _resolve_patient_or_404(conn, patient_id, caller.organization_id)
        od_iop, os_iop = _fetch_iop_history(
            conn, patient_id=patient["id"], org_id=caller.organization_id
        )
        od_lane = _build_lane(
            conn,
            patient_id=patient["id"],
            org_id=caller.organization_id,
            eye="OD",
            iop_history=od_iop,
        )
        os_lane = _build_lane(
            conn,
            patient_id=patient["id"],
            org_id=caller.organization_id,
            eye="OS",
            iop_history=os_iop,
        )

    bilateral = bool(od_iop or od_lane["visual_field"]["count"] or od_lane["oct_rnfl"]["count"]) and bool(
        os_iop or os_lane["visual_field"]["count"] or os_lane["oct_rnfl"]["count"]
    )

    return {
        "patient_id": patient["id"],
        "patient_identifier": patient["patient_identifier"],
        "patient_name": patient["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "bilateral_data": bilateral,
        "od": od_lane,
        "os": os_lane,
        "disclosure": (
            "ChartNav surfaces what the provider's measurements show. "
            "ChartNav does not interpret IOP trends, visual fields, "
            "or OCT scans. It does not classify glaucoma progression. "
            "It does not recommend medication, laser, or surgery. "
            "Missing data is shown as insufficient_data; values are "
            "never invented to fill gaps."
        ),
    }


__all__ = [
    "SummaryError",
    "build_glaucoma_summary",
    "VISUAL_FIELD_MODALITIES",
    "OCT_RNFL_MODALITIES",
    "OCT_MACULA_MODALITIES",
]
