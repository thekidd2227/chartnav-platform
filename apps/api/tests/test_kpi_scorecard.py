"""Phase 47 — KPI / ROI scorecard service + /admin/kpi routes.

Validates the scorecard end-to-end against a seeded org:
  1. Unit tests on the pure aggregation helpers (_summ, _pct,
     _parse_iso, _delta_minutes, kpi_csv_rows) without DB.
  2. HTTP tests that hit `/admin/kpi/*` and assert:
       - admin-only access
       - org scoping (org1 does not see org2 data)
       - shape of the JSON payload (counts, latency, quality)
       - CSV export round-trips through kpi_csv_rows columns
       - KPI export is audited

The tests intentionally lean on the existing seed + any workflow
events it produces. They assert *shape* and *scoping*, not exact
minute counts, because the seed doesn't drive a full
transcript→draft→sign cycle. When a future seed does, the shape
stays the same — the numbers fill in.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from tests.conftest import ADMIN1, CLIN1, REV1, ADMIN2


# ---------- unit-level helpers ------------------------------------------

def test_summ_empty_returns_all_nulls():
    from app.services.kpi_scorecard import _summ
    s = _summ([])
    assert s["n"] == 0
    for k in ("median", "mean", "p90", "min", "max"):
        assert s[k] is None


def test_summ_basic_sorted_math():
    from app.services.kpi_scorecard import _summ
    s = _summ([10.0, 20.0, 30.0, 40.0, 50.0])
    assert s["n"] == 5
    assert s["min"] == 10.0
    assert s["max"] == 50.0
    assert s["median"] == 30.0
    assert s["mean"] == 30.0
    # p90 on 5 samples lands on the last sample.
    assert s["p90"] == 50.0


def test_pct_rounds_and_handles_none():
    from app.services.kpi_scorecard import _pct
    assert _pct(None) is None
    assert _pct(0.12345) == 12.35
    assert _pct(1.0) == 100.0


def test_delta_minutes_rejects_negative_and_none():
    from app.services.kpi_scorecard import _delta_minutes, _parse_iso
    a = _parse_iso("2026-04-21T10:00:00+00:00")
    b = _parse_iso("2026-04-21T10:30:00+00:00")
    assert _delta_minutes(a, b) == 30.0
    # Reversed → negative → treated as unusable.
    assert _delta_minutes(b, a) is None
    assert _delta_minutes(None, b) is None
    assert _delta_minutes(a, None) is None


def test_csv_rows_columns_are_stable():
    from app.services.kpi_scorecard import CSV_COLUMNS, kpi_csv_rows
    header, *rest = kpi_csv_rows({"providers": []})
    assert header == CSV_COLUMNS
    assert rest == []


# ---------- HTTP surface --------------------------------------------------

def test_kpi_overview_admin_only(client):
    # clinician + reviewer must be refused (require_admin).
    r = client.get("/admin/kpi/overview", headers=CLIN1)
    assert r.status_code == 403
    r = client.get("/admin/kpi/overview", headers=REV1)
    assert r.status_code == 403


def test_kpi_overview_shape_and_org_scoping(client):
    r = client.get("/admin/kpi/overview", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organization_id"] >= 1
    # Window is surfaced honestly.
    assert "since" in body["window"] and "until" in body["window"]
    assert body["window"]["hours"] == 24 * 7
    # Counts block always returns integers (never absent).
    counts = body["counts"]
    assert isinstance(counts["encounters"], int)
    assert isinstance(counts["signed_notes"], int)
    assert isinstance(counts["exported_notes"], int)
    assert isinstance(counts["open_drafts"], int)
    # Latency summaries always include the n=0 empty shape.
    lat = body["latency_minutes"]
    for k in ("transcript_to_draft", "draft_to_sign", "total_time_to_sign"):
        assert "n" in lat[k]
        for sub in ("median", "mean", "p90", "min", "max"):
            assert sub in lat[k]
    # Quality block always present.
    q = body["quality"]
    for k in (
        "missing_data_rate",
        "export_ready_rate",
        "notes_observed",
        "notes_with_missing_flags",
        "avg_revisions_per_signed_note",
    ):
        assert k in q

    # Org scoping: org1 admin and org2 admin see different org ids.
    r2 = client.get("/admin/kpi/overview", headers=ADMIN2)
    assert r2.status_code == 200
    assert r2.json()["organization_id"] != body["organization_id"]


def test_kpi_providers_admin_only_and_scoped(client):
    r = client.get("/admin/kpi/providers", headers=CLIN1)
    assert r.status_code == 403
    r = client.get("/admin/kpi/providers", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert "providers" in body and isinstance(body["providers"], list)
    # Each row matches the CSV column contract.
    for row in body["providers"]:
        for field in (
            "provider",
            "encounters",
            "signed_notes",
            "missing_data_rate_pct",
            "transcript_to_draft_min",
            "draft_to_sign_min",
            "total_time_to_sign_min",
        ):
            assert field in row


def test_kpi_export_csv_admin_only_and_audited(client):
    # non-admin refused
    r = client.get("/admin/kpi/export.csv", headers=REV1)
    assert r.status_code == 403
    # admin gets text/csv with a header row
    r = client.get("/admin/kpi/export.csv", headers=ADMIN1)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    lines = r.text.strip().splitlines()
    assert len(lines) >= 1
    # header contains the stable column list
    header = lines[0].split(",")
    assert header[0] == "provider"
    assert "total_time_to_sign_min_p90" in header

    # Audit row exists on the shipped `/security-audit-events` read.
    audit = client.get("/security-audit-events?limit=50", headers=ADMIN1)
    assert audit.status_code == 200, audit.text
    body = audit.json()
    rows = body if isinstance(body, list) else body.get("items", [])
    types = [ev.get("event_type") for ev in rows]
    assert "admin_kpi_export" in types


def test_kpi_window_accepts_custom_hours(client):
    r = client.get("/admin/kpi/overview?hours=24", headers=ADMIN1)
    assert r.status_code == 200
    assert r.json()["window"]["hours"] == 24


def test_kpi_window_rejects_out_of_range(client):
    # hours is constrained to 1..24*90 by the route's Query validator.
    r = client.get("/admin/kpi/overview?hours=0", headers=ADMIN1)
    assert r.status_code == 422
    r = client.get("/admin/kpi/overview?hours=99999", headers=ADMIN1)
    assert r.status_code == 422
