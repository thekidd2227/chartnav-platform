"""Phase 81 — Provider Action Item Queue tests.

Covers:
  * baseline (fresh seed, no artifacts) → empty buckets, zero totals
  * anti-VEGF source: due-today + auth-pending items land in the right
    buckets with laterality + due_at + source_artifact_id
  * glaucoma source: ready_for_review VF study → this_week item;
    IOP-without-VF/OCT → informational insufficient_data item
  * cataract source: missed post-op checkpoint → same_day; planned
    surgery with incomplete pre-op signals → this_week with
    insufficient_data; complications flag → this_week
  * signed_lock / visit_summary source: unsigned vitals + unfinalized
    visit draft + unsigned fundus chart → routine items
  * cross-source aggregation: sources_present lists ≥ 2 sources
  * org scoping: org-2 caller sees an empty queue (org-1 data invisible)
  * unauthenticated → 401
  * deterministic labels: no diagnosis / treatment / surgery
    recommendation language; no provider free text leaks
  * disclosure boundary language present
"""

from __future__ import annotations

import json
from datetime import date, timedelta

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}

QUEUE = "/api/v1/provider-action-queue"


def _queue(client, headers=CLIN1):
    r = client.get(QUEUE, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _items(body, bucket):
    return body["buckets"][bucket]


def test_baseline_queue_is_empty(client):
    body = _queue(client)
    assert body["organization_id"] == 1
    assert body["demo_mode"] is True
    assert set(body["buckets"].keys()) == {
        "same_day", "this_week", "routine", "informational",
    }
    assert body["total_items"] == 0
    assert body["totals"] == {
        "same_day": 0, "this_week": 0, "routine": 0, "informational": 0,
    }
    assert body["sources_present"] == []


def test_anti_vegf_items_bucketed_with_laterality_and_due_at(client):
    today = date.today()
    # OD due today
    r = client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(today - timedelta(days=28)),
            "interval_weeks": 4,
            "authorization_status": "approved",
        },
    )
    assert r.status_code == 201, r.text
    # OS auth pending
    r = client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OS",
            "injection_date": str(today - timedelta(days=14)),
            "interval_weeks": 8,
            "authorization_status": "pending",
        },
    )
    assert r.status_code == 201, r.text

    body = _queue(client)
    same_day = [
        it for it in _items(body, "same_day")
        if it["specialty_source"] == "anti_vegf"
    ]
    assert any(
        it["category"] == "injection_due_today" and it["laterality"] == "OD"
        for it in same_day
    ), same_day
    due_today = next(
        it for it in same_day if it["category"] == "injection_due_today"
    )
    assert due_today["due_at"] == today.isoformat()
    assert due_today["patient_id"] == 1
    assert due_today["patient_identifier"] == "PT-1001"
    assert due_today["source_artifact_id"] is not None
    assert due_today["requires_provider_review"] is True

    this_week = [
        it for it in _items(body, "this_week")
        if it["specialty_source"] == "anti_vegf"
    ]
    assert any(
        it["category"] == "authorization_pending" and it["laterality"] == "OS"
        for it in this_week
    ), this_week


def test_glaucoma_ready_for_review_study_lands_this_week(client):
    r = client.post(
        "/patients/1/imaging-studies",
        headers=CLIN1,
        json={
            "modality": "visual_field_24_2",
            "eye": "OD",
            "status": "ready_for_review",
        },
    )
    assert r.status_code == 201, r.text
    study_id = r.json()["id"]

    body = _queue(client)
    glaucoma = [
        it for it in _items(body, "this_week")
        if it["specialty_source"] == "glaucoma"
    ]
    assert any(
        it["category"] == "imaging_review_pending"
        and it["source_artifact_id"] == study_id
        and it["laterality"] == "OD"
        for it in glaucoma
    ), glaucoma


def test_glaucoma_iop_without_imaging_is_informational_insufficient(client):
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "iop_od": 18, "iop_method": "applanation"},
    )
    assert r.status_code in (200, 201), r.text

    body = _queue(client)
    info = [
        it for it in _items(body, "informational")
        if it["specialty_source"] == "glaucoma"
    ]
    assert any(
        it["category"] == "glaucoma_data_incomplete"
        and it["insufficient_data"] is True
        and it["laterality"] == "OU"
        for it in info
    ), info


def test_cataract_missed_postop_is_same_day(client):
    r = client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OD",
            "postop_day_1_status": "missed",
        },
    )
    assert r.status_code == 201, r.text

    body = _queue(client)
    cataract = [
        it for it in _items(body, "same_day")
        if it["specialty_source"] == "cataract"
    ]
    assert any(
        it["category"] == "postop_checkpoint_missed" and it["laterality"] == "OD"
        for it in cataract
    ), cataract


def test_cataract_incomplete_preop_is_this_week_insufficient(client):
    r = client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OS",
            "planned_surgery_date": "2026-08-01",
            "biometry_reviewed": False,
            "topography_reviewed": True,
            "consent_status": "in_progress",
        },
    )
    assert r.status_code == 201, r.text

    body = _queue(client)
    cataract = [
        it for it in _items(body, "this_week")
        if it["specialty_source"] == "cataract"
    ]
    item = next(
        (it for it in cataract if it["category"] == "preop_signals_incomplete"),
        None,
    )
    assert item is not None, cataract
    assert item["laterality"] == "OS"
    assert item["insufficient_data"] is True
    assert item["due_at"] == "2026-08-01"
    assert "biometry not reviewed" in item["detail"]
    assert "consent in_progress" in item["detail"]


def test_cataract_complications_flag_surfaces_this_week(client):
    r = client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OD",
            "complications_flag": True,
            "complication_note": "Provider canary complication text.",
        },
    )
    assert r.status_code == 201, r.text

    body = _queue(client)
    cataract = [
        it for it in _items(body, "this_week")
        if it["specialty_source"] == "cataract"
    ]
    assert any(
        it["category"] == "provider_entered_complications_flag"
        for it in cataract
    ), cataract
    # The provider's free-text note must NOT leak into the queue.
    blob = json.dumps(body).lower()
    assert "canary complication text" not in blob


def test_unsigned_artifacts_land_routine(client):
    # Unsigned vitals workup
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "bp_systolic": 120, "bp_diastolic": 78},
    )
    assert r.status_code in (200, 201), r.text
    # Unfinalized visit draft
    r = client.post(
        "/patients/1/scribe-sessions",
        headers=CLIN1,
        json={
            "input_mode": "transcript",
            "transcript_text": "Demo transcript only. Blurry vision OD.",
            "encounter_id": 1,
        },
    )
    assert r.status_code in (200, 201), r.text
    # Unsigned fundus chart
    r = client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "horseshoe tear at 10:30 OD", "laterality": "OD"},
    )
    assert r.status_code in (200, 201), r.text

    body = _queue(client)
    routine = _items(body, "routine")
    cats = {it["category"] for it in routine}
    assert "vitals_unsigned" in cats, routine
    assert "visit_draft_unsigned" in cats, routine
    assert "fundus_unsigned" in cats, routine
    fundus = next(it for it in routine if it["category"] == "fundus_unsigned")
    assert fundus["laterality"] == "OD"
    assert fundus["specialty_source"] == "signed_lock"
    draft = next(it for it in routine if it["category"] == "visit_draft_unsigned")
    assert draft["specialty_source"] == "visit_summary"


def test_sources_present_aggregates_multiple_sources(client):
    today = date.today()
    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(today - timedelta(days=28)),
            "interval_weeks": 4,
        },
    )
    client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={"surgery_eye": "OS", "postop_week_1_status": "missed"},
    )

    body = _queue(client)
    assert "anti_vegf" in body["sources_present"]
    assert "cataract" in body["sources_present"]
    assert len(body["sources_present"]) >= 2
    assert body["total_items"] >= 2


def test_org_scoping_other_org_sees_empty_queue(client):
    today = date.today()
    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(today - timedelta(days=28)),
            "interval_weeks": 4,
        },
    )
    body = _queue(client, headers=ADMIN2)
    assert body["organization_id"] == 2
    assert body["total_items"] == 0


def test_unauthenticated_returns_401(client):
    r = client.get(QUEUE)
    assert r.status_code in (401, 403), r.text


def test_no_forbidden_clinical_language_in_queue(client):
    today = date.today()
    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(today - timedelta(days=35)),
            "interval_weeks": 4,
            "authorization_status": "expired",
        },
    )
    client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OS",
            "planned_surgery_date": "2026-08-01",
            "consent_status": "not_obtained",
        },
    )
    body = _queue(client)
    blob = json.dumps(body).lower()
    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "surgery recommended",
        "urgent escalation",
        "order placed",
        "billing code",
        "iol power",
        "phaco recommended",
        "rapid progression",
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase appeared in action queue: {forbidden!r}"
        )


def test_disclosure_boundary_language(client):
    body = _queue(client)
    d = body["disclosure"].lower()
    assert "provider-entered data" in d
    assert "does not diagnose" in d
    assert "does not recommend" in d
    assert "provider review required" in d
    assert "deterministic" in d
