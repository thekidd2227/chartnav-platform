"""Phase 92 — Advanced Clinical Intelligence Layer tests."""

from __future__ import annotations

from datetime import date, timedelta

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _get(client, encounter_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/encounters/{encounter_id}/advanced-clinical-intelligence",
        headers=headers,
    )


def _seed_injection(client, eye="OD", weeks=8, headers=CLIN1):
    return client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=headers,
        json={
            "eye": eye,
            "injection_date": str(date.today() - timedelta(days=10)),
            "interval_weeks": weeks,
            "authorization_status": "approved",
        },
    )


def _seed_disease_stage(client, system="amd_areds", stage="Category 3"):
    return client.post(
        "/api/v1/encounters/1/disease-staging",
        headers=CLIN1,
        json={
            "diagnosis_code": "h35.31",
            "staging_system": system,
            "stage_value": stage,
        },
    )


def _seed_glaucoma_stage(client, stage="Mild"):
    return client.post(
        "/api/v1/encounters/1/disease-staging",
        headers=CLIN1,
        json={
            "diagnosis_code": "h40.10",
            "staging_system": "glaucoma_poag",
            "stage_value": stage,
        },
    )


def _seed_cataract_record(client):
    return client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "encounter_id": 1,
            "surgery_eye": "OD",
            "planned_surgery_date": str(date.today() + timedelta(days=30)),
        },
    )


# ---------------------------------------------------------------------------
# GET — baseline + safety
# ---------------------------------------------------------------------------


def test_get_baseline_returns_all_four_sections_with_insufficient_data(client):
    body = _get(client).json()
    assert body["encounter_id"] == 1
    assert body["retina_summary"]["insufficient_data"] is True
    assert body["glaucoma_summary"]["insufficient_data"] is True
    assert body["cataract_summary"]["insufficient_data"] is True
    # fhir_export_readiness can render the packet even for empty seed
    assert "fhir_export_readiness" in body
    assert body["submission_status"] == "not_submitted"


def test_get_includes_safety_boundaries(client):
    body = _get(client).json()
    keys = {b["key"] for b in body["safety_boundaries"]}
    assert "no_autonomous_diagnosis" in keys
    assert "no_image_interpretation" in keys
    assert "no_treatment_recommendation" in keys
    assert "no_submission" in keys
    assert "metadata_only" in keys
    for b in body["safety_boundaries"]:
        assert b["asserted"] is True


def test_get_includes_disclosure_with_safe_claims_language(client):
    d = _get(client).json()["disclosure"].lower()
    assert "does not diagnose" in d
    assert "does not interpret images" in d
    assert "does not recommend treatment" in d
    assert "does not submit" in d
    assert "metadata projection" in d


def test_get_includes_data_limitations(client):
    body = _get(client).json()
    assert body["data_limitations"]
    for section in (
        body["retina_summary"],
        body["glaucoma_summary"],
        body["cataract_summary"],
    ):
        assert "data_limitations" in section
        assert isinstance(section["data_limitations"], list)
        assert section["data_limitations"]


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_unknown_encounter_returns_404(client):
    assert _get(client, encounter_id=999999).status_code == 404


# ---------------------------------------------------------------------------
# Retina section
# ---------------------------------------------------------------------------


def test_retina_section_reflects_anti_vegf_history(client):
    assert _seed_injection(client, eye="OD", weeks=8).status_code == 201
    assert _seed_injection(client, eye="OS", weeks=6).status_code == 201
    body = _get(client).json()
    retina = body["retina_summary"]
    assert retina["od"]["injection_count"] >= 1
    assert retina["os"]["injection_count"] >= 1
    assert retina["od"]["insufficient_data"] is False
    assert retina["os"]["insufficient_data"] is False
    assert retina["od"]["latest_interval_weeks"] == 8


def test_retina_section_reflects_disease_stage_history(client):
    assert _seed_disease_stage(client).status_code == 201
    body = _get(client).json()
    retina = body["retina_summary"]
    assert retina["stage_history_count"] >= 1
    assert retina["stage_history"][0]["diagnosis_code"] == "h35.31"


def test_retina_section_never_includes_forbidden_language(client):
    _seed_injection(client)
    body = _get(client).json()
    blob = str(body["retina_summary"]).lower()
    for forbidden in (
        "disease worsening detected",
        "interval should be shortened",
        "interval should be extended",
        "anti-vegf recommended",
        "image interpreted",
        "diagnosis confirmed",
    ):
        assert forbidden not in blob, forbidden


# ---------------------------------------------------------------------------
# Glaucoma section
# ---------------------------------------------------------------------------


def test_glaucoma_section_reflects_poag_stage_history(client):
    assert _seed_glaucoma_stage(client).status_code == 201
    body = _get(client).json()
    g = body["glaucoma_summary"]
    assert g["poag_stage_history_count"] >= 1
    assert g["poag_stage_history"][0]["stage_value"] == "Mild"


def test_glaucoma_section_includes_adherence_signals(client):
    body = _get(client).json()
    g = body["glaucoma_summary"]
    assert "adherence_signals" in g
    assert "active_medication_count" in g["adherence_signals"]
    assert "refill_gap_count" in g["adherence_signals"]
    assert "active_safety_event_count" in g["adherence_signals"]


def test_glaucoma_section_never_includes_forbidden_language(client):
    body = _get(client).json()
    blob = str(body["glaucoma_summary"]).lower()
    for forbidden in (
        "progression confirmed",
        "escalate to surgery",
        "medication change recommended",
        "treatment recommended",
        "auto-classified",
    ):
        assert forbidden not in blob, forbidden


# ---------------------------------------------------------------------------
# Cataract section
# ---------------------------------------------------------------------------


def test_cataract_section_reflects_workflow_record(client):
    assert _seed_cataract_record(client).status_code == 201
    body = _get(client).json()
    c = body["cataract_summary"]
    assert c["od"]["record_count"] >= 1
    assert c["od"]["insufficient_data"] is False
    assert c["conversion_funnel"]["any_record"] is True
    assert c["conversion_funnel"]["planned_date_present"] is True


def test_cataract_section_never_includes_forbidden_language(client):
    _seed_cataract_record(client)
    body = _get(client).json()
    blob = str(body["cataract_summary"]).lower()
    for forbidden in (
        "iol power recommended",
        "lens model recommended",
        "phaco recommended",
        "flacs recommended",
        "complications detected",
        "surgical plan recommended",
        "auto-scheduled",
    ):
        assert forbidden not in blob, forbidden


# ---------------------------------------------------------------------------
# FHIR / interoperability hardening
# ---------------------------------------------------------------------------


def test_fhir_section_returns_packet_renderable_and_extensions(client):
    body = _get(client).json()
    f = body["fhir_export_readiness"]
    assert f["packet_renderable"] is True
    assert f["document_reference_id"] == "retina-visit-packet-1"
    assert f["submission_status"] == "not_submitted"
    assert f["transport"] == "none"
    assert "extensions_present" in f
    assert "boundary" in f


def test_fhir_section_extensions_reflect_seeded_data(client):
    _seed_disease_stage(client)
    body = _get(client).json()
    extensions = body["fhir_export_readiness"]["extensions_present"]
    assert "disease_staging_summary" in extensions


def test_fhir_section_never_implies_submission(client):
    body = _get(client).json()
    f = body["fhir_export_readiness"]
    blob = str(f).lower()
    for forbidden in (
        "submitted to",
        "transmitted to",
        "wrote back to ehr",
        "auto-submitted",
        "bidirectional sync",
    ):
        assert forbidden not in blob, forbidden


# ---------------------------------------------------------------------------
# Encounter scoping
# ---------------------------------------------------------------------------


def test_get_reflects_phase_91_visit_mode_and_laterality(client):
    client.patch(
        "/api/v1/encounters/1/workspace-state/visit-mode",
        headers=CLIN1,
        json={"visit_mode": "follow_up"},
    )
    client.patch(
        "/api/v1/encounters/1/workspace-state/active-laterality",
        headers=CLIN1,
        json={"active_laterality": "OD"},
    )
    body = _get(client).json()
    assert body["visit_mode"] == "follow_up"
    assert body["active_laterality"] == "OD"


# ---------------------------------------------------------------------------
# Phase 77 packet integration
# ---------------------------------------------------------------------------


def test_phase_77_packet_embeds_advanced_clinical_intelligence_summary(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "advanced_clinical_intelligence_summary" in body
    block = body["advanced_clinical_intelligence_summary"]
    assert block["submission_status"] == "not_submitted"
    assert "boundary_note" in block
