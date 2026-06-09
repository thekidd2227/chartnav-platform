"""Phase 80 — Cataract surgical workflow tests.

Covers:
  * RBAC: admin/clinician can write; technician/reviewer/front_desk denied
  * surgery_eye strict OD/OS
  * consent_status enum allowlist
  * postop status enum allowlist
  * text-length validators
  * date validator
  * baseline (no records) → both eyes insufficient_data=True
  * per-eye placement on create
  * latest_record reflects most recent insert
  * preop_readiness 4-signal score
  * postop_cadence 3-signal score
  * cross-org returns 404 on summary AND records AND POST
  * unknown patient → 404
  * unauthenticated → 401
  * summary projection deliberately omits free-text fields
  * disclosure boundary language present
  * forbidden clinical phrasings canary
"""

from __future__ import annotations

import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _post(client, headers, patient_id, **over):
    payload = {
        "surgery_eye": "OD",
        "planned_surgery_date": "2026-07-01",
        "biometry_reviewed": True,
        "topography_reviewed": True,
        "consent_status": "signed",
        "target_refraction": "-0.50",
        "lens_plan_label": "Provider-entered: target monofocal IOL",
        "postop_day_1_status": "scheduled",
        "postop_week_1_status": "not_scheduled",
        "postop_month_1_status": "not_scheduled",
        "complications_flag": False,
        **over,
    }
    return client.post(
        f"/api/v1/patients/{patient_id}/cataract-workflow/records",
        headers=headers,
        json=payload,
    )


def test_baseline_summary_both_eyes_insufficient(client):
    r = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["patient_id"] == 1
    assert body["patient_identifier"] == "PT-1001"
    assert body["patient_name"] == "Morgan Lee"
    assert body["od"]["eye"] == "OD"
    assert body["os"]["eye"] == "OS"
    assert body["od"]["insufficient_data"] is True
    assert body["os"]["insufficient_data"] is True
    assert body["od"]["record_count"] == 0
    assert body["os"]["record_count"] == 0
    assert body["od"]["latest_record"] is None
    assert body["bilateral_planned"] is False


def test_create_requires_admin_or_clinician(client):
    # reviewer denied
    r = _post(client, REV1, 1)
    assert r.status_code == 403, r.text
    # technician denied (cataract workflow is provider-level)
    r = _post(client, TECH1, 1)
    assert r.status_code == 403, r.text
    # front_desk denied
    r = _post(client, FRONT1, 1)
    assert r.status_code == 403, r.text
    # clinician allowed
    r = _post(client, CLIN1, 1)
    assert r.status_code == 201, r.text
    # admin allowed
    r = _post(client, ADMIN1, 1, surgery_eye="OS")
    assert r.status_code == 201, r.text


def test_surgery_eye_strict_OD_or_OS(client):
    r = _post(client, CLIN1, 1, surgery_eye="OU")
    assert r.status_code == 422, r.text
    r = _post(client, CLIN1, 1, surgery_eye="XX")
    assert r.status_code == 422, r.text


def test_consent_status_allowlist(client):
    r = _post(client, CLIN1, 1, consent_status="maybe")
    assert r.status_code == 422, r.text
    r = _post(client, CLIN1, 1, consent_status="signed")
    assert r.status_code == 201, r.text


def test_postop_status_allowlist(client):
    r = _post(client, CLIN1, 1, postop_day_1_status="forgot")
    assert r.status_code == 422, r.text
    r = _post(client, CLIN1, 1, postop_week_1_status="missed")
    assert r.status_code == 201, r.text


def test_invalid_date_format(client):
    r = _post(client, CLIN1, 1, planned_surgery_date="next thursday")
    assert r.status_code == 422, r.text


def test_text_length_validators(client):
    r = _post(client, CLIN1, 1, target_refraction="x" * 65)
    assert r.status_code == 422, r.text
    r = _post(client, CLIN1, 1, lens_plan_label="y" * 161)
    assert r.status_code == 422, r.text


def test_per_eye_placement_on_summary(client):
    assert _post(client, CLIN1, 1, surgery_eye="OD").status_code == 201
    assert _post(client, CLIN1, 1, surgery_eye="OS").status_code == 201

    r = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["od"]["record_count"] == 1
    assert body["os"]["record_count"] == 1
    assert body["od"]["latest_record"]["surgery_eye"] == "OD"
    assert body["os"]["latest_record"]["surgery_eye"] == "OS"
    assert body["bilateral_planned"] is True


def test_latest_record_reflects_most_recent_insert(client):
    assert (
        _post(
            client, CLIN1, 1,
            surgery_eye="OD",
            planned_surgery_date="2026-07-01",
        ).status_code
        == 201
    )
    r = _post(
        client, CLIN1, 1,
        surgery_eye="OD",
        planned_surgery_date="2026-08-15",
        consent_status="signed",
    )
    assert r.status_code == 201, r.text

    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    assert s["od"]["record_count"] == 2
    assert s["od"]["latest_record"]["planned_surgery_date"] == "2026-08-15"


def test_preop_readiness_score_aggregates_signals(client):
    _post(
        client, CLIN1, 1,
        surgery_eye="OD",
        planned_surgery_date="2026-07-01",
        biometry_reviewed=True,
        topography_reviewed=True,
        consent_status="signed",
    )
    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    pre = s["od"]["preop_readiness"]
    assert pre["has_planned_date"] is True
    assert pre["biometry_reviewed"] is True
    assert pre["topography_reviewed"] is True
    assert pre["consent_signed"] is True
    assert pre["score_numerator"] == 4
    assert pre["score_denominator"] == 4


def test_postop_cadence_score_counts_known_statuses(client):
    _post(
        client, CLIN1, 1,
        surgery_eye="OD",
        postop_day_1_status="completed",
        postop_week_1_status="scheduled",
        postop_month_1_status="unknown",
    )
    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    cad = s["od"]["postop_cadence"]
    assert cad["postop_day_1_status"] == "completed"
    assert cad["postop_week_1_status"] == "scheduled"
    assert cad["postop_month_1_status"] == "unknown"
    assert cad["score_numerator"] == 2
    assert cad["score_denominator"] == 3


def test_cross_org_returns_404_on_all_paths(client):
    # Summary
    r = client.get("/api/v1/patients/1/cataract-workflow", headers=ADMIN2)
    assert r.status_code == 404, r.text
    # Records list
    r = client.get(
        "/api/v1/patients/1/cataract-workflow/records", headers=ADMIN2
    )
    assert r.status_code == 404, r.text
    # POST
    r = _post(client, ADMIN2, 1)
    assert r.status_code == 404, r.text


def test_unknown_patient_returns_404(client):
    r = client.get(
        "/api/v1/patients/99999/cataract-workflow", headers=ADMIN1
    )
    assert r.status_code == 404, r.text


def test_unauthenticated_returns_401(client):
    r = client.get("/api/v1/patients/1/cataract-workflow")
    assert r.status_code in (401, 403), r.text


def test_summary_projection_omits_provider_entered_free_text(client):
    """Hard rule: target_refraction / lens_plan_label / complication_note /
    notes appear on the RECORD response but NOT on the summary projection."""
    _post(
        client, CLIN1, 1,
        target_refraction="-0.50 OD plano-target",
        lens_plan_label="Provider-entered: monofocal IOL plan",
        complications_flag=True,
        complication_note="Provider canary note about a complication.",
        notes="Provider canary internal note.",
    )

    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    blob = json.dumps(s).lower()

    # Provider-entered free text MUST NOT appear in the summary projection.
    for forbidden in [
        "plano-target",
        "monofocal iol plan",
        "provider canary note",
        "provider canary internal",
        "target_refraction",
        "lens_plan_label",
        "complication_note",
    ]:
        assert forbidden not in blob, (
            f"forbidden free-text fragment leaked into summary: {forbidden!r}"
        )

    # Records GET preserves verbatim (provider authored).
    records = client.get(
        "/api/v1/patients/1/cataract-workflow/records", headers=CLIN1
    ).json()
    assert any(
        "plano-target" in (r.get("target_refraction") or "").lower()
        for r in records
    )


def test_disclosure_explicit_boundary_language(client):
    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    d = s["disclosure"].lower()
    assert "does not select an iol power" in d
    assert "does not recommend a surgical technique" in d
    assert "does not recommend a surgery date" in d
    assert "does not order tests" in d


def test_summary_has_no_forbidden_clinical_phrases(client):
    _post(client, CLIN1, 1, complications_flag=True)
    s = client.get("/api/v1/patients/1/cataract-workflow", headers=CLIN1).json()
    blob = json.dumps(s).lower()
    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "order placed",
        "iol power 22",
        "phaco recommended",
        "flacs recommended",
        "surgery scheduled by chartnav",
        "automatic billing",
        "billing code",
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase appeared in summary: {forbidden!r}"
        )
