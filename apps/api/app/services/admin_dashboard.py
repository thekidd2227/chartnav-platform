"""Admin dashboard analytics — pure read path.

Spec: docs/chartnav/closure/PHASE_B_Admin_Dashboard_and_Operational_Metrics.md

What this module does:
  - Aggregate the six KPI cards the spec calls for in §3.
  - Build a 14-day trend payload (signed-per-day +
    missing-flag-resolution-rate-per-day).
  - Run pure SELECTs against existing tables (encounters,
    note_versions, reminders) — no new persistent storage.

Truth limitations preserved (spec §9):
  - "Median sign-to-export lag" reflects ChartNav-mediated exports
    only; a clinician copying out manually is invisible to this
    metric.
  - In integrated_readthrough mode, encounters written directly in
    the partner EHR do not appear here.
  - Resolution-rate semantics are explicit: a flag is counted as
    "resolved" when it appeared on a note_version in the window
    and is absent from the most-recent note_version for that
    encounter at query time. This intentionally does not depend on
    a flag-events table that does not exist in Phase A; we'd add
    one in Phase C if a buyer asks for cohort-level slicing.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any

from app.db import fetch_all, fetch_one


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(s: Any) -> datetime | None:
    if s is None or s == "":
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        # SQLAlchemy returns ISO-formatted strings on SQLite.
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_flags(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        v = json.loads(raw)
        return [str(x) for x in v] if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _date_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).date().isoformat()


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

def summary(organization_id: int) -> dict[str, Any]:
    now = _now_utc()
    today = now.date()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    # All signed note_versions for the org in the last 14 days, with
    # encounter id + signed_at + exported_at + flags.
    rows = fetch_all(
        "SELECT nv.id AS nv_id, nv.encounter_id, nv.signed_at, "
        "       nv.exported_at, nv.missing_data_flags, "
        "       nv.created_at AS nv_created_at "
        "FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :oid",
        {"oid": organization_id},
    )

    encounters_signed_today = 0
    encounters_signed_7d = 0
    lags_minutes_7d: list[float] = []

    # For each encounter, find the latest signed note (max signed_at).
    latest_by_encounter: dict[int, dict] = {}
    for r in rows:
        eid = r["encounter_id"]
        signed_at = _parse_dt(r.get("signed_at"))
        nv_created = _parse_dt(r.get("nv_created_at"))
        # Use signed_at if present, else nv_created_at as the row anchor.
        anchor = signed_at or nv_created
        if not anchor:
            continue
        prev = latest_by_encounter.get(eid)
        if prev is None or anchor > prev["anchor"]:
            latest_by_encounter[eid] = {
                **dict(r),
                "anchor": anchor,
                "signed_at": signed_at,
                "exported_at": _parse_dt(r.get("exported_at")),
                "flags": _parse_flags(r.get("missing_data_flags")),
            }

    # Signed-today and signed-7d counts: distinct encounters whose
    # latest note has signed_at in the relevant window.
    for eid, latest in latest_by_encounter.items():
        sa = latest["signed_at"]
        if not sa:
            continue
        if sa.astimezone(timezone.utc).date() == today:
            encounters_signed_today += 1
        if sa >= seven_days_ago:
            encounters_signed_7d += 1
            ex = latest["exported_at"]
            if ex and ex >= sa:
                lags_minutes_7d.append((ex - sa).total_seconds() / 60.0)

    median_sign_to_export_minutes_7d: float | None = (
        round(median(lags_minutes_7d), 2) if lags_minutes_7d else None
    )

    # Missing flags open: sum of flags currently on the latest
    # note_version per encounter (status not abandoned).
    missing_flags_open = sum(
        len(latest["flags"]) for latest in latest_by_encounter.values()
    )

    # 14-day resolution rate: for each encounter touched in window,
    # surfaced = max len(flags) seen on any version in window;
    # resolved = surfaced - len(flags) on latest version.
    surfaced_per_enc: dict[int, int] = {}
    for r in rows:
        anchor = _parse_dt(r.get("signed_at")) or _parse_dt(r.get("nv_created_at"))
        if not anchor or anchor < fourteen_days_ago:
            continue
        eid = r["encounter_id"]
        n = len(_parse_flags(r.get("missing_data_flags")))
        prev = surfaced_per_enc.get(eid, 0)
        surfaced_per_enc[eid] = max(prev, n)

    surfaced_total = sum(surfaced_per_enc.values())
    resolved_total = 0
    for eid, max_flags in surfaced_per_enc.items():
        latest_flags = len(
            latest_by_encounter.get(eid, {}).get("flags", [])
        )
        resolved_total += max(max_flags - latest_flags, 0)
    if surfaced_total > 0:
        missing_flag_resolution_rate_14d = round(
            resolved_total / surfaced_total, 4,
        )
    else:
        missing_flag_resolution_rate_14d = 0.0

    # Reminders overdue: status != 'completed' and 'cancelled' AND due_at < now.
    overdue_row = fetch_one(
        "SELECT COUNT(*) AS n FROM reminders "
        "WHERE organization_id = :oid AND status NOT IN ('completed','cancelled') "
        "AND due_at IS NOT NULL AND due_at < :now",
        {"oid": organization_id, "now": now.isoformat(timespec="seconds")},
    )
    reminders_overdue = int((overdue_row or {}).get("n") or 0)

    return {
        "encounters_signed_today": encounters_signed_today,
        "encounters_signed_7d": encounters_signed_7d,
        "median_sign_to_export_minutes_7d": median_sign_to_export_minutes_7d,
        "missing_flags_open": missing_flags_open,
        "missing_flag_resolution_rate_14d": missing_flag_resolution_rate_14d,
        "reminders_overdue": reminders_overdue,
    }


# ---------------------------------------------------------------------
# Trend (14 daily buckets)
# ---------------------------------------------------------------------

def trend(organization_id: int, days: int = 14) -> dict[str, Any]:
    if days < 1:
        days = 1
    if days > 60:
        days = 60
    today = _now_utc().date()
    bucket_dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    bucket_index: dict[str, int] = {d.isoformat(): i for i, d in enumerate(bucket_dates)}
    series = [
        {"date": d.isoformat(),
         "encounters_signed": 0,
         "missing_flag_resolution_rate": 0.0}
        for d in bucket_dates
    ]
    surfaced_today: list[int] = [0] * days
    resolved_today: list[int] = [0] * days

    rows = fetch_all(
        "SELECT nv.encounter_id, nv.signed_at, nv.created_at, "
        "       nv.missing_data_flags "
        "FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :oid",
        {"oid": organization_id},
    )

    # Track per-encounter rows in window for resolution math:
    #   (anchor_date, flag_count)
    per_enc: dict[int, list[tuple[date, int]]] = {}
    signed_per_date: dict[str, set] = {d.isoformat(): set() for d in bucket_dates}
    for r in rows:
        anchor = _parse_dt(r.get("signed_at")) or _parse_dt(r.get("created_at"))
        if not anchor:
            continue
        adate = anchor.astimezone(timezone.utc).date()
        if adate.isoformat() not in bucket_index:
            continue
        eid = r["encounter_id"]
        flag_count = len(_parse_flags(r.get("missing_data_flags")))
        per_enc.setdefault(eid, []).append((adate, flag_count))
        if r.get("signed_at"):
            signed_per_date[adate.isoformat()].add(eid)

    # Per-encounter: resolved on a date d means flag_count strictly
    # decreased from the previous most-recent in-window version. We
    # attribute the "resolved count" to the day of the new version.
    for eid, pairs in per_enc.items():
        pairs.sort(key=lambda p: p[0])
        prev_n = None
        for adate, n in pairs:
            if prev_n is not None and n < prev_n:
                resolved_today[bucket_index[adate.isoformat()]] += (prev_n - n)
            # surfaced increases attributed to the day they appear
            if prev_n is None:
                if n > 0:
                    surfaced_today[bucket_index[adate.isoformat()]] += n
            elif n > prev_n:
                surfaced_today[bucket_index[adate.isoformat()]] += (n - prev_n)
            prev_n = n

    for i, d in enumerate(bucket_dates):
        series[i]["encounters_signed"] = len(signed_per_date[d.isoformat()])
        denom = surfaced_today[i] + resolved_today[i]
        if denom > 0:
            series[i]["missing_flag_resolution_rate"] = round(
                resolved_today[i] / denom, 4,
            )

    return {"series": series}
