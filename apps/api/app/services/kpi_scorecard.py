"""Phase 47 — pilot KPI / ROI scorecard.

Aggregates already-existing timestamps across the charting workflow
into a handful of honest pilot metrics. **No new schema.** Every
number is derived from columns the product already writes at the
right points in the encounter lifecycle:

  - encounter_inputs.{created_at, started_at, finished_at, processing_status, retry_count}
  - note_versions.{created_at, signed_at, exported_at, draft_status, version_number, generated_by, missing_data_flags}
  - encounters.{provider_id, provider_name, organization_id, created_at}
  - workflow_events (for volume counters)

Consumer surfaces:

  GET /admin/kpi/overview       — org-level rollup
  GET /admin/kpi/providers      — per-provider breakdown
  GET /admin/kpi/export.csv     — flat CSV for before/after pilot reporting

Design rules:

  1. Never invent a metric. If the data does not support a number,
     surface `null` and let the UI render "—".
  2. Per-org scoping always. Callers hand in `organization_id`;
     every SQL statement pins it.
  3. Time-window aware. Every aggregation accepts a `since_iso`
     bound so pilots can define "this week", "this month", and
     "pre-pilot vs post-pilot" without schema changes.
  4. PHI-safe. Aggregations return counts, milliseconds, and
     rates — never transcript text, never note body, never
     patient identifiers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Optional

from app.db import fetch_all, fetch_one, is_sqlite


# ---------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Accept both "…Z" and raw "…±HH:MM" forms.
        txt = s.replace("Z", "+00:00") if s.endswith("Z") else s
        return datetime.fromisoformat(txt)
    except (ValueError, TypeError):
        return None


def _delta_minutes(a: Optional[datetime], b: Optional[datetime]) -> Optional[float]:
    if not a or not b:
        return None
    d = (b - a).total_seconds() / 60.0
    return d if d >= 0 else None


# ---------------------------------------------------------------------
# Org-level overview
# ---------------------------------------------------------------------

def kpi_overview(
    organization_id: int,
    hours: int = 24 * 7,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Rollup of the charting KPIs for the org across the last N hours.

    The default window is 7 days so pilot reviews see a week's
    cadence. Callers override with `hours` for tighter or wider
    windows.

    Thin wrapper around `_kpi_overview_range(since, until)` —
    compare / range modes call the range helper directly.
    """
    cur = now or _now()
    since = cur - timedelta(hours=hours)
    return _kpi_overview_range(organization_id, since=since, until=cur)


def _kpi_overview_range(
    organization_id: int,
    since: datetime,
    until: datetime,
) -> dict[str, Any]:
    """Range-based org KPI rollup. Both bounds are inclusive of the
    start and exclusive of the end — matches the pilot semantics
    ("what happened from April 1 through April 30" means the 1st at
    00:00:00 to the 30th at 23:59:59, i.e. the `until` is one tick
    past the observation period's close).

    Used by both `kpi_overview` (now-relative) and `kpi_compare`
    (explicit A vs B ranges). Keeps the SQL + aggregation in one
    place so the two surfaces can never drift.
    """
    since_iso = since.isoformat()
    until_iso = until.isoformat()

    # --- 1. Counts inside the window --------------------------------------
    counts_row = fetch_one(
        """
        SELECT
          COUNT(DISTINCT e.id)                     AS encounters,
          COALESCE(SUM(CASE WHEN nv.draft_status = 'signed'   THEN 1 ELSE 0 END), 0) AS signed_notes,
          COALESCE(SUM(CASE WHEN nv.draft_status = 'exported' THEN 1 ELSE 0 END), 0) AS exported_notes,
          COALESCE(SUM(CASE WHEN nv.draft_status IN ('draft','provider_review','revised') THEN 1 ELSE 0 END), 0) AS open_drafts
        FROM encounters e
        LEFT JOIN note_versions nv
          ON nv.encounter_id = e.id
         AND nv.created_at >= :since
         AND nv.created_at <  :until
        WHERE e.organization_id = :org
          AND e.created_at >= :since
          AND e.created_at <  :until
        """,
        {"org": organization_id, "since": since_iso, "until": until_iso},
    )
    counts = dict(counts_row) if counts_row else {}

    # --- 2. Latency metrics (transcript-to-draft / draft-to-sign / total) ---
    # We walk the rows in Python because dialect-portable window-function
    # math (first input, first signed note per encounter) is easier to
    # reason about this way than as a single SQL expression.
    inputs = fetch_all(
        """
        SELECT ei.encounter_id, ei.created_at, ei.finished_at, ei.processing_status
        FROM encounter_inputs ei
        JOIN encounters e ON e.id = ei.encounter_id
        WHERE e.organization_id = :org
          AND ei.created_at >= :since
          AND ei.created_at <  :until
        ORDER BY ei.encounter_id ASC, ei.created_at ASC
        """,
        {"org": organization_id, "since": since_iso, "until": until_iso},
    )
    notes = fetch_all(
        """
        SELECT
          nv.encounter_id,
          nv.version_number,
          nv.draft_status,
          nv.created_at,
          nv.signed_at,
          nv.exported_at,
          nv.generated_by,
          nv.missing_data_flags,
          nv.reviewed_at,
          nv.amended_at,
          nv.amended_from_note_id
        FROM note_versions nv
        JOIN encounters e ON e.id = nv.encounter_id
        WHERE e.organization_id = :org
          AND nv.created_at >= :since
          AND nv.created_at <  :until
        ORDER BY nv.encounter_id ASC, nv.version_number ASC
        """,
        {"org": organization_id, "since": since_iso, "until": until_iso},
    )

    transcript_to_draft: list[float] = []
    draft_to_sign: list[float] = []
    total_time_to_sign: list[float] = []
    draft_to_review: list[float] = []
    review_to_sign: list[float] = []
    sign_to_export: list[float] = []
    notes_with_missing = 0
    notes_total = 0
    amendment_rows = 0
    revisions_per_sign: list[int] = []

    # Group by encounter.
    first_completed_input: dict[int, datetime] = {}
    for row in inputs:
        row = dict(row)
        enc_id = row["encounter_id"]
        if enc_id in first_completed_input:
            continue
        if row["processing_status"] == "completed":
            fin = _parse_iso(row.get("finished_at") or row.get("created_at"))
            if fin is not None:
                first_completed_input[enc_id] = fin

    per_encounter_versions: dict[int, list[dict[str, Any]]] = {}
    for row in notes:
        row = dict(row)
        per_encounter_versions.setdefault(row["encounter_id"], []).append(row)

    for enc_id, versions in per_encounter_versions.items():
        first_draft = None
        first_signed = None
        first_reviewed = None
        first_exported = None
        for v in versions:
            notes_total += 1
            if v.get("amended_from_note_id"):
                amendment_rows += 1
            # Missing-data flags are stored as JSON text or CSV depending on
            # dialect writes; accept both and count "non-empty" conservatively.
            mdf = v.get("missing_data_flags")
            if mdf and str(mdf).strip() not in ("", "[]", "null"):
                notes_with_missing += 1
            if first_draft is None and v.get("created_at"):
                first_draft = _parse_iso(v["created_at"])
            if first_reviewed is None and v.get("reviewed_at"):
                first_reviewed = _parse_iso(v["reviewed_at"])
            if first_signed is None and v.get("signed_at"):
                first_signed = _parse_iso(v["signed_at"])
            if first_exported is None and v.get("exported_at"):
                first_exported = _parse_iso(v["exported_at"])

        input_at = first_completed_input.get(enc_id)
        if input_at and first_draft:
            d1 = _delta_minutes(input_at, first_draft)
            if d1 is not None:
                transcript_to_draft.append(d1)
        if first_draft and first_signed:
            d2 = _delta_minutes(first_draft, first_signed)
            if d2 is not None:
                draft_to_sign.append(d2)
        if input_at and first_signed:
            d3 = _delta_minutes(input_at, first_signed)
            if d3 is not None:
                total_time_to_sign.append(d3)
        # Phase 49 lifecycle latencies.
        if first_draft and first_reviewed:
            dr = _delta_minutes(first_draft, first_reviewed)
            if dr is not None:
                draft_to_review.append(dr)
        if first_reviewed and first_signed:
            drs = _delta_minutes(first_reviewed, first_signed)
            if drs is not None:
                review_to_sign.append(drs)
        if first_signed and first_exported:
            dex = _delta_minutes(first_signed, first_exported)
            if dex is not None:
                sign_to_export.append(dex)
        if first_signed:
            revisions_per_sign.append(max(0, len(versions) - 1))

    # --- 3. Derived rates --------------------------------------------------
    missing_rate = (
        (notes_with_missing / notes_total) if notes_total > 0 else None
    )
    export_ready_rate = (
        (counts.get("exported_notes", 0) /
         max(1, counts.get("signed_notes", 0) + counts.get("exported_notes", 0)))
        if counts.get("signed_notes") or counts.get("exported_notes")
        else None
    )

    total_seconds = max(0, (until - since).total_seconds())
    hours_window = round(total_seconds / 3600.0, 2)

    # Phase 49 — blocked-sign attempts + amendment rate (pilot lifecycle
    # governance). Reads the same `security_audit_events` table every
    # other audit surface reads; no schema change.
    blocked_row = fetch_one(
        "SELECT COUNT(*) AS n FROM security_audit_events "
        "WHERE organization_id = :org "
        "  AND event_type = 'note_sign_blocked' "
        "  AND created_at >= :since AND created_at < :until",
        {"org": organization_id, "since": since_iso, "until": until_iso},
    )
    blocked_sign_attempts = int(dict(blocked_row or {}).get("n") or 0)
    amendment_rate = (
        (amendment_rows / notes_total) if notes_total else None
    )

    return {
        "organization_id": organization_id,
        "window": {
            "since": since_iso,
            "until": until_iso,
            "hours": hours_window,
        },
        "counts": {
            "encounters": int(counts.get("encounters") or 0),
            "signed_notes": int(counts.get("signed_notes") or 0),
            "exported_notes": int(counts.get("exported_notes") or 0),
            "open_drafts": int(counts.get("open_drafts") or 0),
        },
        "latency_minutes": {
            "transcript_to_draft": _summ(transcript_to_draft),
            "draft_to_sign": _summ(draft_to_sign),
            "total_time_to_sign": _summ(total_time_to_sign),
            # Phase 49 lifecycle latencies.
            "draft_to_review": _summ(draft_to_review),
            "review_to_sign": _summ(review_to_sign),
            "sign_to_export": _summ(sign_to_export),
        },
        "quality": {
            "missing_data_rate": _pct(missing_rate),
            "export_ready_rate": _pct(export_ready_rate),
            "notes_observed": notes_total,
            "notes_with_missing_flags": notes_with_missing,
            "avg_revisions_per_signed_note": (
                round(sum(revisions_per_sign) / len(revisions_per_sign), 2)
                if revisions_per_sign
                else None
            ),
            # Phase 49 governance counters.
            "blocked_sign_attempts": blocked_sign_attempts,
            "amendment_rate": _pct(amendment_rate),
            "amendment_count": amendment_rows,
        },
    }


def _summ(vals: list[float]) -> dict[str, Any]:
    """Return a standard min/median/p90/max/mean summary or all-nulls."""
    if not vals:
        return {
            "n": 0,
            "median": None,
            "mean": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    s = sorted(vals)
    n = len(s)
    p90_idx = max(0, min(n - 1, int(round(0.9 * (n - 1)))))
    return {
        "n": n,
        "median": round(median(s), 2),
        "mean": round(sum(s) / n, 2),
        "p90": round(s[p90_idx], 2),
        "min": round(s[0], 2),
        "max": round(s[-1], 2),
    }


def _pct(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v * 100.0, 2)


# ---------------------------------------------------------------------
# Per-provider breakdown
# ---------------------------------------------------------------------

def kpi_providers(
    organization_id: int,
    hours: int = 24 * 7,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Per-provider KPI rollup. Provider key is `provider_name`
    (free-text) for backward compatibility with native encounters
    that predate the providers table. When `provider_id` is set,
    we prefer that + the providers.display_name join.
    """
    cur = now or _now()
    since = cur - timedelta(hours=hours)
    since_iso = since.isoformat()

    # Pull every encounter + its earliest completed input + first note + first signed note.
    encounters = fetch_all(
        """
        SELECT
          e.id            AS encounter_id,
          e.provider_id,
          e.provider_name
        FROM encounters e
        WHERE e.organization_id = :org
          AND e.created_at >= :since
        """,
        {"org": organization_id, "since": since_iso},
    )

    inputs = fetch_all(
        """
        SELECT ei.encounter_id, ei.created_at, ei.finished_at, ei.processing_status
        FROM encounter_inputs ei
        JOIN encounters e ON e.id = ei.encounter_id
        WHERE e.organization_id = :org
          AND ei.created_at >= :since
        """,
        {"org": organization_id, "since": since_iso},
    )
    notes = fetch_all(
        """
        SELECT nv.encounter_id, nv.version_number, nv.draft_status,
               nv.created_at, nv.signed_at, nv.missing_data_flags
        FROM note_versions nv
        JOIN encounters e ON e.id = nv.encounter_id
        WHERE e.organization_id = :org
          AND nv.created_at >= :since
        ORDER BY nv.encounter_id, nv.version_number
        """,
        {"org": organization_id, "since": since_iso},
    )
    providers = fetch_all(
        """
        SELECT id, display_name FROM providers
        WHERE organization_id = :org AND is_active
        """,
        {"org": organization_id},
    )
    provider_name_by_id = {p["id"]: p["display_name"] for p in [dict(r) for r in providers]}

    # Index
    first_input: dict[int, datetime] = {}
    for r in inputs:
        row = dict(r)
        if row["encounter_id"] in first_input:
            continue
        if row["processing_status"] == "completed":
            fin = _parse_iso(row.get("finished_at") or row.get("created_at"))
            if fin:
                first_input[row["encounter_id"]] = fin
    per_enc_notes: dict[int, list[dict[str, Any]]] = {}
    for r in notes:
        per_enc_notes.setdefault(dict(r)["encounter_id"], []).append(dict(r))

    # Aggregate per provider
    by_provider: dict[str, dict[str, Any]] = {}
    for r in encounters:
        row = dict(r)
        key = (
            provider_name_by_id.get(row.get("provider_id"))
            or row.get("provider_name")
            or "—"
        )
        bucket = by_provider.setdefault(
            key,
            {
                "provider": key,
                "encounters": 0,
                "signed_notes": 0,
                "transcript_to_draft_min": [],
                "draft_to_sign_min": [],
                "total_time_to_sign_min": [],
                "missing_flag_count": 0,
                "notes_observed": 0,
                "revisions": [],
            },
        )
        bucket["encounters"] += 1
        versions = per_enc_notes.get(row["encounter_id"], [])
        first_draft = None
        first_signed = None
        for v in versions:
            bucket["notes_observed"] += 1
            mdf = v.get("missing_data_flags")
            if mdf and str(mdf).strip() not in ("", "[]", "null"):
                bucket["missing_flag_count"] += 1
            if first_draft is None and v.get("created_at"):
                first_draft = _parse_iso(v["created_at"])
            if first_signed is None and v.get("signed_at"):
                first_signed = _parse_iso(v["signed_at"])
                bucket["signed_notes"] += 1

        input_at = first_input.get(row["encounter_id"])
        if input_at and first_draft:
            d = _delta_minutes(input_at, first_draft)
            if d is not None:
                bucket["transcript_to_draft_min"].append(d)
        if first_draft and first_signed:
            d = _delta_minutes(first_draft, first_signed)
            if d is not None:
                bucket["draft_to_sign_min"].append(d)
        if input_at and first_signed:
            d = _delta_minutes(input_at, first_signed)
            if d is not None:
                bucket["total_time_to_sign_min"].append(d)
        if first_signed:
            bucket["revisions"].append(max(0, len(versions) - 1))

    rows = []
    for name, b in sorted(by_provider.items(), key=lambda kv: kv[0]):
        rows.append({
            "provider": b["provider"],
            "encounters": b["encounters"],
            "signed_notes": b["signed_notes"],
            "notes_observed": b["notes_observed"],
            "missing_flag_count": b["missing_flag_count"],
            "missing_data_rate_pct": _pct(
                (b["missing_flag_count"] / b["notes_observed"])
                if b["notes_observed"] else None
            ),
            "transcript_to_draft_min":  _summ(b["transcript_to_draft_min"]),
            "draft_to_sign_min":        _summ(b["draft_to_sign_min"]),
            "total_time_to_sign_min":   _summ(b["total_time_to_sign_min"]),
            "avg_revisions_per_signed_note": (
                round(sum(b["revisions"]) / len(b["revisions"]), 2)
                if b["revisions"] else None
            ),
        })

    return {
        "organization_id": organization_id,
        "window": {"since": since_iso, "until": cur.isoformat(), "hours": hours},
        "providers": rows,
    }


# ---------------------------------------------------------------------
# CSV export (pilot / before-after ready)
# ---------------------------------------------------------------------

CSV_COLUMNS = [
    "provider",
    "encounters",
    "signed_notes",
    "notes_observed",
    "missing_flag_count",
    "missing_data_rate_pct",
    "transcript_to_draft_min_median",
    "draft_to_sign_min_median",
    "total_time_to_sign_min_median",
    "total_time_to_sign_min_p90",
    "avg_revisions_per_signed_note",
]


def kpi_csv_rows(providers_payload: dict[str, Any]) -> list[list[Any]]:
    """Flatten the per-provider payload into CSV rows. Pure function —
    the route handler is the only place that touches `csv.writer`."""
    rows: list[list[Any]] = [list(CSV_COLUMNS)]
    for r in providers_payload.get("providers", []):
        t_draft = r.get("transcript_to_draft_min") or {}
        d_sign = r.get("draft_to_sign_min") or {}
        t_sign = r.get("total_time_to_sign_min") or {}
        rows.append([
            r.get("provider"),
            r.get("encounters"),
            r.get("signed_notes"),
            r.get("notes_observed"),
            r.get("missing_flag_count"),
            r.get("missing_data_rate_pct"),
            t_draft.get("median"),
            d_sign.get("median"),
            t_sign.get("median"),
            t_sign.get("p90"),
            r.get("avg_revisions_per_signed_note"),
        ])
    return rows


# ---------------------------------------------------------------------
# Before / after comparison
# ---------------------------------------------------------------------

def kpi_compare(
    organization_id: int,
    hours: int = 24 * 7,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Compare two consecutive windows of the same width:
        current  = [ now - hours, now )
        previous = [ now - 2*hours, now - hours )

    Rendered into a single payload so the scorecard can show
    deltas without two round-trips. Each period carries its own
    `_kpi_overview_range` payload so the UI can point at exact
    numbers on each side.

    Also surfaces a compact `deltas` block:
      - pct_change on latency medians (lower is better → negative
        delta means improvement)
      - pct_change on quality rates (higher export_ready_rate is
        better, lower missing_data_rate is better — UI labels the
        direction; service returns raw math)
    """
    cur = now or _now()
    window = timedelta(hours=hours)
    cur_payload = _kpi_overview_range(
        organization_id, since=cur - window, until=cur
    )
    prev_payload = _kpi_overview_range(
        organization_id, since=cur - 2 * window, until=cur - window
    )
    return {
        "organization_id": organization_id,
        "window_hours": hours,
        "current": cur_payload,
        "previous": prev_payload,
        "deltas": _compute_deltas(cur_payload, prev_payload),
    }


def _compute_deltas(cur: dict[str, Any], prev: dict[str, Any]) -> dict[str, Any]:
    """Compute honest current - previous deltas on the fields a pilot
    reviewer actually reads. `pct_change` is returned when previous
    is non-zero; otherwise `None` (we never divide by zero)."""
    def _pctdelta(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        if b == 0:
            return None
        return round(((a - b) / b) * 100.0, 2)

    cur_lat = cur.get("latency_minutes", {})
    prev_lat = prev.get("latency_minutes", {})
    cur_q = cur.get("quality", {})
    prev_q = prev.get("quality", {})
    cur_c = cur.get("counts", {})
    prev_c = prev.get("counts", {})

    return {
        "latency_minutes_median_pct_change": {
            "transcript_to_draft": _pctdelta(
                cur_lat.get("transcript_to_draft", {}).get("median"),
                prev_lat.get("transcript_to_draft", {}).get("median"),
            ),
            "draft_to_sign": _pctdelta(
                cur_lat.get("draft_to_sign", {}).get("median"),
                prev_lat.get("draft_to_sign", {}).get("median"),
            ),
            "total_time_to_sign": _pctdelta(
                cur_lat.get("total_time_to_sign", {}).get("median"),
                prev_lat.get("total_time_to_sign", {}).get("median"),
            ),
        },
        "quality_pct_change": {
            "missing_data_rate": _pctdelta(
                cur_q.get("missing_data_rate"),
                prev_q.get("missing_data_rate"),
            ),
            "export_ready_rate": _pctdelta(
                cur_q.get("export_ready_rate"),
                prev_q.get("export_ready_rate"),
            ),
        },
        "counts_delta": {
            "encounters": int(cur_c.get("encounters", 0)) - int(prev_c.get("encounters", 0)),
            "signed_notes": int(cur_c.get("signed_notes", 0)) - int(prev_c.get("signed_notes", 0)),
            "exported_notes": int(cur_c.get("exported_notes", 0)) - int(prev_c.get("exported_notes", 0)),
        },
    }


__all__ = [
    "kpi_overview",
    "kpi_providers",
    "kpi_compare",
    "kpi_csv_rows",
    "CSV_COLUMNS",
]
