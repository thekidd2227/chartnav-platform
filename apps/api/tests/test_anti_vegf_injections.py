"""Phase 78 — Anti-VEGF injection rail tests.

Covers:
  * create requires admin / clinician / technician; reviewer/front-desk denied
  * eye is strictly OD or OS; OU rejected
  * interval_weeks bounds enforced
  * cross-org access returns 404
  * laterality preserved in history split (OD vs OS)
  * bilateral patient surfaces in both histories
  * readiness queue buckets are deterministic for known dates
  * authorization_pending / authorization_expired surface correctly
  * bilateral_asymmetric surfaces when OD/OS land in different buckets
  * payload shape never includes diagnosis / treatment / orders text
  * disclosure language present
"""

from __future__ import annotations

from datetime import date, timedelta
import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _create(client, headers, patient_id, **fields):
    payload = {
        "eye": "OD",
        "drug_label": "anti_vegf_generic",
        "injection_date": "2026-05-01",
        "interval_weeks": 4,
        "authorization_status": "approved",
        "lot_number": "DEMO-001",
        **fields,
    }
    return client.post(
        f"/api/v1/patients/{patient_id}/anti-vegf-injections",
        headers=headers,
        json=payload,
    )


def test_create_requires_write_role(client):
    # reviewer denied
    r = _create(client, REV1, 1)
    assert r.status_code == 403, r.text
    # front desk denied
    r = _create(client, FRONT1, 1)
    assert r.status_code == 403, r.text
    # clinician allowed
    r = _create(client, CLIN1, 1)
    assert r.status_code == 201, r.text
    # admin allowed
    r = _create(client, ADMIN1, 1, eye="OS")
    assert r.status_code == 201, r.text
    # technician allowed (intake-style writes are technician-level)
    r = _create(client, TECH1, 1, eye="OD", injection_date="2026-05-15")
    assert r.status_code == 201, r.text


def test_create_validates_eye_strictly_OD_or_OS(client):
    r = _create(client, CLIN1, 1, eye="OU")
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error_code"] == "invalid_enum"

    r = _create(client, CLIN1, 1, eye="XX")
    assert r.status_code == 422, r.text


def test_create_validates_interval_range(client):
    r = _create(client, CLIN1, 1, interval_weeks=0)
    assert r.status_code == 422, r.text
    r = _create(client, CLIN1, 1, interval_weeks=53)
    assert r.status_code == 422, r.text
    r = _create(client, CLIN1, 1, interval_weeks=8)
    assert r.status_code == 201, r.text


def test_create_validates_drug_label_allowlist(client):
    r = _create(client, CLIN1, 1, drug_label="branded_avastin")
    assert r.status_code == 422, r.text
    r = _create(client, CLIN1, 1, drug_label="anti_vegf_branded")
    assert r.status_code == 201, r.text


def test_create_auto_computes_next_due_when_interval_given(client):
    r = _create(
        client,
        CLIN1,
        1,
        injection_date="2026-05-01",
        interval_weeks=4,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["next_due_date"] == "2026-05-29"  # 28 days later


def test_history_splits_by_eye_and_marks_bilateral(client):
    # Three injections: 2 OD, 1 OS.
    assert _create(client, CLIN1, 1, eye="OD", injection_date="2026-04-01").status_code == 201
    assert _create(client, CLIN1, 1, eye="OD", injection_date="2026-05-01").status_code == 201
    assert _create(client, CLIN1, 1, eye="OS", injection_date="2026-04-15").status_code == 201

    r = client.get("/api/v1/patients/1/anti-vegf-injections", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["od_count"] == 2
    assert body["os_count"] == 1
    assert body["total_count"] == 3
    assert body["bilateral"] is True
    # Latest OD = 2026-05-01 (sorted by date desc).
    assert body["latest_od"]["injection_date"] == "2026-05-01"
    assert body["latest_os"]["injection_date"] == "2026-04-15"


def test_history_filter_by_eye_only(client):
    assert _create(client, CLIN1, 1, eye="OD", injection_date="2026-04-01").status_code == 201
    assert _create(client, CLIN1, 1, eye="OS", injection_date="2026-04-15").status_code == 201

    r = client.get(
        "/api/v1/patients/1/anti-vegf-injections?eye=OD", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["od_count"] == 1
    assert body["os_count"] == 0
    assert body["bilateral"] is False


def test_cross_org_access_returns_404(client):
    # Org 1 patient PT-1001 is id=1; admin from org 2 must 404.
    r = client.get("/api/v1/patients/1/anti-vegf-injections", headers=ADMIN2)
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "patient_not_found"

    r = _create(client, ADMIN2, 1)
    assert r.status_code == 404, r.text


def test_unauthenticated_returns_401(client):
    r = client.get("/api/v1/patients/1/anti-vegf-injections")
    assert r.status_code in (401, 403), r.text


def test_readiness_queue_buckets_are_deterministic(client):
    today = date.today()

    # Due today (next_due_date == today)
    _create(
        client, CLIN1, 1,
        eye="OD", injection_date=str(today - timedelta(days=28)),
        interval_weeks=4,
        # next_due_date computed as today.
    )

    # Due this week (today + 3 days)
    _create(
        client, CLIN1, 1,
        eye="OS",
        injection_date=str(today - timedelta(days=25)),
        interval_weeks=4,
        # next_due_date computed as today + 3.
    )

    r = client.get("/api/v1/anti-vegf/readiness-queue", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["today"] == today.isoformat()
    assert "buckets" in body
    assert "due_today" in body["buckets"]
    assert "due_this_week" in body["buckets"]
    assert "overdue" in body["buckets"]
    assert "authorization_pending" in body["buckets"]
    assert "authorization_expired" in body["buckets"]
    assert body["totals"]["due_today"] >= 1
    assert body["totals"]["due_this_week"] >= 1
    # Disclosure text present.
    assert "does not recommend" in body["disclosure"].lower()


def test_readiness_queue_authorization_pending_surfaces(client):
    _create(
        client, CLIN1, 1,
        eye="OD",
        injection_date=str(date.today() - timedelta(days=14)),
        interval_weeks=8,
        authorization_status="pending",
    )
    r = client.get("/api/v1/anti-vegf/readiness-queue", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    pending = body["buckets"]["authorization_pending"]
    assert any(b["eye"] == "OD" for b in pending)


def test_readiness_queue_authorization_expired_surfaces(client):
    _create(
        client, CLIN1, 1,
        eye="OS",
        injection_date=str(date.today() - timedelta(days=30)),
        interval_weeks=4,
        authorization_status="expired",
    )
    r = client.get("/api/v1/anti-vegf/readiness-queue", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    expired = body["buckets"]["authorization_expired"]
    assert any(b["eye"] == "OS" for b in expired)


def test_readiness_queue_bilateral_asymmetric_flags_diverging_cadence(client):
    today = date.today()
    # OD due today
    _create(
        client, CLIN1, 1, eye="OD",
        injection_date=str(today - timedelta(days=28)),
        interval_weeks=4,
    )
    # OS expired auth → different bucket
    _create(
        client, CLIN1, 1, eye="OS",
        injection_date=str(today - timedelta(days=14)),
        interval_weeks=8,
        authorization_status="expired",
    )
    r = client.get("/api/v1/anti-vegf/readiness-queue", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    asymm = body["bilateral_asymmetric"]
    assert any(
        a["patient_id"] == 1
        and a["od_bucket"] == "due_today"
        and a["os_bucket"] == "authorization_expired"
        for a in asymm
    ), asymm


def test_response_omits_forbidden_clinical_phrasings(client):
    """Canary: even with `notes` populated, the API responses must
    never surface treatment / diagnosis / order / billing language as
    ChartNav-attributed claims. The provider's notes are preserved
    verbatim only on the single-record response and only because the
    provider authored them — they're not displayed in the readiness
    queue's projection."""
    _create(
        client, CLIN1, 1,
        notes="Patient tolerated injection well per technician; provider review pending.",
    )

    # Readiness queue projection must NOT include notes / forbidden text.
    r = client.get("/api/v1/anti-vegf/readiness-queue", headers=CLIN1)
    assert r.status_code == 200, r.text
    blob = json.dumps(r.json()).lower()

    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "order placed",
        "billing code",
        "automatic coding",
        "patient message sent",
        "patient tolerated injection well",  # canary — note text MUST NOT appear
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase appeared in readiness queue: {forbidden}"
        )


def test_invalid_date_format_returns_422(client):
    r = _create(client, CLIN1, 1, injection_date="not-a-date")
    assert r.status_code == 422, r.text


def test_invalid_authorization_status_returns_422(client):
    r = _create(client, CLIN1, 1, authorization_status="negotiating")
    assert r.status_code == 422, r.text
