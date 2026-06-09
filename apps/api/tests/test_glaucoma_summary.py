"""Phase 79 — Glaucoma Progression Cockpit aggregator tests.

Covers:
  * baseline (no IOP, no imaging) → both eyes insufficient_data=True
  * IOP captured per eye → appears in correct lane history
  * cross-org returns 404
  * unknown patient returns 404
  * data_completeness scoring reflects what data exists
  * disclosure language present + no diagnosis / progression language
  * forbidden clinical text canary (no notes / interpretation leak)
"""

from __future__ import annotations

import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _create_vitals_with_iop(client, headers, iop_od=None, iop_os=None):
    body = {"source_type": "technician_entry"}
    if iop_od is not None:
        body["iop_od"] = iop_od
    if iop_os is not None:
        body["iop_os"] = iop_os
    body["iop_method"] = "applanation"
    return client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=headers,
        json=body,
    )


def test_baseline_insufficient_data_for_both_eyes(client):
    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["patient_id"] == 1
    assert body["patient_identifier"] == "PT-1001"
    assert body["patient_name"] == "Morgan Lee"
    assert body["organization_id"] == 1
    assert body["demo_mode"] is True
    assert body["od"]["eye"] == "OD"
    assert body["os"]["eye"] == "OS"
    assert body["od"]["insufficient_data"] is True
    assert body["os"]["insufficient_data"] is True
    assert body["od"]["iop_count"] == 0
    assert body["os"]["iop_count"] == 0
    assert body["od"]["visual_field"]["insufficient_data"] is True
    assert body["od"]["oct_rnfl"]["insufficient_data"] is True
    assert body["od"]["oct_macula"]["insufficient_data"] is True
    assert body["bilateral_data"] is False


def test_iop_history_appears_in_correct_eye_lane(client):
    # Record an IOP measurement per eye.
    r = _create_vitals_with_iop(client, CLIN1, iop_od=18, iop_os=16)
    assert r.status_code in (200, 201), r.text

    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["od"]["iop_count"] == 1
    assert body["os"]["iop_count"] == 1
    assert body["od"]["iop_history"][0]["value"] == 18
    assert body["od"]["iop_history"][0]["eye"] == "OD"
    assert body["os"]["iop_history"][0]["value"] == 16
    assert body["os"]["iop_history"][0]["eye"] == "OS"
    assert body["od"]["latest_iop"]["value"] == 18
    assert body["os"]["latest_iop"]["value"] == 16


def test_iop_only_one_eye_does_not_pollute_other_eye(client):
    r = _create_vitals_with_iop(client, CLIN1, iop_od=22, iop_os=None)
    assert r.status_code in (200, 201), r.text

    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["od"]["iop_count"] == 1
    assert body["os"]["iop_count"] == 0
    assert body["od"]["data_completeness"]["has_iop"] is True
    assert body["os"]["data_completeness"]["has_iop"] is False
    assert body["od"]["insufficient_data"] is False
    assert body["os"]["insufficient_data"] is True


def test_iop_history_returns_newest_first(client):
    assert _create_vitals_with_iop(client, CLIN1, iop_od=14).status_code in (200, 201)
    assert _create_vitals_with_iop(client, CLIN1, iop_od=18).status_code in (200, 201)
    assert _create_vitals_with_iop(client, CLIN1, iop_od=22).status_code in (200, 201)

    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    history = r.json()["od"]["iop_history"]
    assert len(history) == 3
    # Newest first
    assert history[0]["value"] == 22
    assert history[-1]["value"] == 14


def test_completeness_score_aggregates_present_signals(client):
    _create_vitals_with_iop(client, CLIN1, iop_od=18)
    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    od = r.json()["od"]
    assert od["data_completeness"]["has_iop"] is True
    assert od["data_completeness"]["has_visual_field"] is False
    assert od["data_completeness"]["has_oct_rnfl"] is False
    assert od["data_completeness"]["score_numerator"] == 1
    assert od["data_completeness"]["score_denominator"] == 3


def test_cross_org_returns_404(client):
    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=ADMIN2)
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "patient_not_found"


def test_unknown_patient_returns_404(client):
    r = client.get("/api/v1/patients/99999/glaucoma-summary", headers=ADMIN1)
    assert r.status_code == 404, r.text


def test_unauthenticated_returns_401(client):
    r = client.get("/api/v1/patients/1/glaucoma-summary")
    assert r.status_code in (401, 403), r.text


def test_disclosure_contains_explicit_boundary_language(client):
    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    disclosure = r.json()["disclosure"].lower()
    assert "does not interpret" in disclosure
    assert "does not classify glaucoma progression" in disclosure
    assert "does not recommend medication" in disclosure


def test_response_contains_no_forbidden_clinical_phrases(client):
    """Canary: even after writing notes-bearing vitals, the aggregator
    must never surface clinical interpretation / diagnosis text."""
    # Create vitals with technician notes containing a canary string.
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={
            "source_type": "technician_entry",
            "iop_od": 28,
            "iop_os": 30,
            "iop_method": "applanation",
            "technician_notes": "Provider concerned about progression per technician canary text.",
        },
    )
    assert r.status_code in (200, 201), r.text

    r = client.get("/api/v1/patients/1/glaucoma-summary", headers=CLIN1)
    assert r.status_code == 200, r.text
    blob = json.dumps(r.json()).lower()

    # The canary note must NOT leak into the summary.
    for forbidden in [
        "concerned about progression",
        "canary text",
        "technician_notes",
        "diagnosis confirmed",
        "treatment recommended",
        "stage iii",
        "stage iv",
        "rapid progression",
        "advanced glaucoma",
        "surgery recommended",
        "laser recommended",
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase leaked into glaucoma summary: {forbidden!r}"
        )
