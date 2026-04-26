"""Phase 2 item 2 — admin dashboard + operational metrics.

Spec: docs/chartnav/closure/PHASE_B_Admin_Dashboard_and_Operational_Metrics.md §4.

Covers:
  - Role-gating: admin OK; clinician without is_lead → 403;
    clinician with is_lead → 200; reviewer / technician /
    biller_coder → 403.
  - Org scoping: org-2 admin's KPIs do not leak org-1 rows.
  - Empty-state: zero data → structured zeros, no nulls.
  - Trend: 14 daily buckets, oldest first.
  - The six KPI keys are present.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1, TECH1, BILLING1


# -------- helpers ---------------------------------------------------

def _make_signed_note_with_flags(
    encounter_id: int,
    *,
    flags: list[str],
    signed_at: datetime | None = None,
    exported_at: datetime | None = None,
) -> int:
    from app.db import transaction
    import json
    with transaction() as conn:
        next_v_row = conn.execute(
            text(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS v "
                "FROM note_versions WHERE encounter_id = :e"
            ),
            {"e": encounter_id},
        ).mappings().first()
        v = int(next_v_row["v"])
        sig = (signed_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
        exp = exported_at.isoformat(timespec="seconds") if exported_at else None
        row = conn.execute(
            text(
                "INSERT INTO note_versions ("
                "  encounter_id, version_number, draft_status, "
                "  note_format, note_text, generated_by, "
                "  provider_review_required, missing_data_flags, "
                "  signed_at, signed_by_user_id, exported_at) "
                "VALUES ("
                "  :e, :v, 'signed', 'soap', '...', 'manual', "
                "  0, :flags, :sig, 1, :exp) RETURNING id"
            ),
            {
                "e": encounter_id,
                "v": v,
                "flags": json.dumps(flags),
                "sig": sig,
                "exp": exp,
            },
        ).mappings().first()
    return int(row["id"])


def _create_encounter(client, headers=ADMIN1, patient_id="PT-DASH") -> int:
    r = client.post(
        "/encounters",
        json={
            "organization_id": 1 if headers in (ADMIN1, CLIN1, REV1, TECH1, BILLING1) else 2,
            "location_id": 1 if headers in (ADMIN1, CLIN1, REV1, TECH1, BILLING1) else 2,
            "patient_identifier": patient_id,
            "patient_name": "Dash Patient",
            "provider_name": "Dr. D",
            "template_key": "retina",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _grant_clinician_lead(email: str) -> None:
    from app.db import transaction
    with transaction() as conn:
        conn.execute(
            text("UPDATE users SET is_lead = 1 WHERE email = :e"),
            {"e": email},
        )


# -------- role gating -----------------------------------------------

def test_admin_can_view_summary(client):
    r = client.get("/admin/dashboard/summary", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in (
        "encounters_signed_today",
        "encounters_signed_7d",
        "median_sign_to_export_minutes_7d",
        "missing_flags_open",
        "missing_flag_resolution_rate_14d",
        "reminders_overdue",
    ):
        assert key in body


def test_general_clinician_forbidden(client):
    r = client.get("/admin/dashboard/summary", headers=CLIN1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_view_admin_dashboard"


def test_clinician_lead_allowed(client):
    _grant_clinician_lead("clin@chartnav.local")
    r = client.get("/admin/dashboard/summary", headers=CLIN1)
    assert r.status_code == 200, r.text


def test_reviewer_forbidden(client):
    r = client.get("/admin/dashboard/summary", headers=REV1)
    assert r.status_code == 403


def test_technician_forbidden(client):
    r = client.get("/admin/dashboard/summary", headers=TECH1)
    assert r.status_code == 403


def test_biller_coder_forbidden(client):
    r = client.get("/admin/dashboard/summary", headers=BILLING1)
    assert r.status_code == 403


# -------- empty state ------------------------------------------------

def test_empty_state_returns_zeros_not_nulls(client):
    """Org with no encounters touched yet — KPIs are zeros (or None
    for median), never missing keys."""
    r = client.get("/admin/dashboard/summary", headers=ADMIN2)
    assert r.status_code == 200
    body = r.json()
    assert body["encounters_signed_today"] == 0
    assert body["encounters_signed_7d"] == 0
    assert body["missing_flags_open"] == 0
    assert body["missing_flag_resolution_rate_14d"] == 0.0
    assert body["reminders_overdue"] == 0
    # median_sign_to_export_minutes_7d is None when no exports have
    # happened — that's an honest absence rather than a fake zero.
    assert body["median_sign_to_export_minutes_7d"] is None


# -------- happy path with data --------------------------------------

def test_summary_counts_signed_today(client):
    enc = _create_encounter(client, patient_id="PT-DASH-TODAY")
    _make_signed_note_with_flags(enc, flags=[])
    r = client.get("/admin/dashboard/summary", headers=ADMIN1)
    body = r.json()
    assert body["encounters_signed_today"] >= 1
    assert body["encounters_signed_7d"] >= 1


def test_summary_lag_minutes_when_exported(client):
    enc = _create_encounter(client, patient_id="PT-DASH-LAG")
    sig = datetime.now(timezone.utc) - timedelta(minutes=15)
    exp = sig + timedelta(minutes=10)
    _make_signed_note_with_flags(enc, flags=[], signed_at=sig, exported_at=exp)
    r = client.get("/admin/dashboard/summary", headers=ADMIN1)
    body = r.json()
    assert body["median_sign_to_export_minutes_7d"] is not None
    assert body["median_sign_to_export_minutes_7d"] >= 9.0


# -------- org scoping ------------------------------------------------

def test_summary_does_not_leak_other_org_rows(client):
    enc1 = _create_encounter(client, headers=ADMIN1, patient_id="PT-DASH-O1")
    _make_signed_note_with_flags(enc1, flags=[])
    enc2 = _create_encounter(client, headers=ADMIN2, patient_id="PT-DASH-O2")
    _make_signed_note_with_flags(enc2, flags=[])
    r1 = client.get("/admin/dashboard/summary", headers=ADMIN1)
    r2 = client.get("/admin/dashboard/summary", headers=ADMIN2)
    # Both orgs see exactly their own one signed encounter today.
    assert r1.json()["encounters_signed_today"] == 1
    assert r2.json()["encounters_signed_today"] == 1


# -------- trend shape ------------------------------------------------

def test_trend_returns_exactly_14_buckets(client):
    r = client.get("/admin/dashboard/trend", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert "series" in body
    assert len(body["series"]) == 14
    # Oldest first.
    dates = [b["date"] for b in body["series"]]
    assert dates == sorted(dates)
    for b in body["series"]:
        assert "encounters_signed" in b
        assert "missing_flag_resolution_rate" in b


def test_trend_role_gate_same_as_summary(client):
    r = client.get("/admin/dashboard/trend", headers=REV1)
    assert r.status_code == 403


def test_trend_days_param_clamps(client):
    r = client.get("/admin/dashboard/trend?days=7", headers=ADMIN1)
    assert r.status_code == 200
    assert len(r.json()["series"]) == 7


# -------- additional negative coverage (per Phase B reviewer request) --

def test_summary_unauthenticated_returns_401(client):
    """No X-User-Email header at all → 401 from the auth dependency,
    never silently accepted."""
    r = client.get("/admin/dashboard/summary")
    assert r.status_code == 401, r.text


def test_trend_unauthenticated_returns_401(client):
    r = client.get("/admin/dashboard/trend")
    assert r.status_code == 401, r.text


def test_trend_general_clinician_forbidden(client):
    """Spec §4 role-gate: general clinician (no is_lead) rejected on
    BOTH summary and trend. Mirror of the summary test for safety."""
    r = client.get("/admin/dashboard/trend", headers=CLIN1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_view_admin_dashboard"


def test_trend_does_not_leak_other_org_signed_counts(client):
    """Org-2 admin pulls trend; the per-day signed counts must reflect
    org-2 rows only, not the org-1 row inserted by this test."""
    enc1 = _create_encounter(client, headers=ADMIN1, patient_id="PT-TR-O1")
    _make_signed_note_with_flags(enc1, flags=[])
    r = client.get("/admin/dashboard/trend", headers=ADMIN2)
    assert r.status_code == 200
    today_bucket = r.json()["series"][-1]
    # Org-2 has zero signed encounters today even though org-1 has one.
    assert today_bucket["encounters_signed"] == 0


def test_clinician_lead_in_other_org_cannot_see_org1_rows(client):
    """Clinician-lead in org-2 must not see org-1 KPIs."""
    _grant_clinician_lead("clin@northside.local")
    enc1 = _create_encounter(client, headers=ADMIN1, patient_id="PT-LEAD-O1")
    _make_signed_note_with_flags(enc1, flags=["iop_missing", "follow_up_missing"])
    r = client.get("/admin/dashboard/summary", headers=CLIN2)
    assert r.status_code == 200, r.text
    body = r.json()
    # Org-2 lead sees zero — the org-1 flags must NOT bleed across.
    assert body["missing_flags_open"] == 0
    assert body["encounters_signed_today"] == 0
