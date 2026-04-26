"""Phase A item 1 — encounter templates contract tests.

Spec: docs/chartnav/closure/PHASE_A_Ophthalmology_Encounter_Templates.md

Covers:
  - GET /encounter-templates returns the four expected templates
  - templates carry section order, required-findings, suggested CPT,
    ICD relevance, and the advisor-review-pending flag
  - POST /encounters accepts a known template_key and persists it
  - POST /encounters rejects an unknown template_key with HTTP 400
  - POST /encounters with no template_key defaults to general_ophthalmology
"""
from __future__ import annotations

from .conftest import ADMIN1, CLIN1


EXPECTED_KEYS = {
    "retina",
    "glaucoma",
    "anterior_segment_cataract",
    "general_ophthalmology",
}


# -------- catalog endpoint --------------------------------------------

def test_list_encounter_templates_returns_four(client):
    r = client.get("/encounter-templates", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    keys = {t["key"] for t in body["items"]}
    assert keys == EXPECTED_KEYS, keys
    assert body["default_key"] == "general_ophthalmology"
    assert body["advisory_only"] is True
    assert body["advisor_review_status"] == "pending"


def test_each_template_has_required_shape(client):
    r = client.get("/encounter-templates", headers=CLIN1)
    body = r.json()
    for t in body["items"]:
        assert isinstance(t["sections"], list) and len(t["sections"]) >= 6
        assert isinstance(t["required_findings"], list)
        assert isinstance(t["suggested_cpt"], list)
        assert isinstance(t["icd10_relevance"], list)
        assert isinstance(t["display_name"], str) and t["display_name"]


def test_glaucoma_template_includes_visual_field_section(client):
    r = client.get("/encounter-templates", headers=CLIN1)
    glaucoma = next(t for t in r.json()["items"] if t["key"] == "glaucoma")
    assert "imaging.visual_field" in glaucoma["sections"]
    assert "92133" in glaucoma["suggested_cpt"]


# -------- create-encounter integration --------------------------------

def _create_payload(**overrides):
    p = {
        "organization_id": 1,
        "location_id": 1,
        "patient_identifier": "PT-PHASE-A-1",
        "patient_name": "Sample Patient",
        "provider_name": "Dr. Carter",
    }
    p.update(overrides)
    return p


def test_create_encounter_accepts_known_template(client):
    r = client.post(
        "/encounters",
        json=_create_payload(
            patient_identifier="PT-PHASE-A-RETINA",
            template_key="retina",
        ),
        headers=ADMIN1,
    )
    assert r.status_code == 201, r.text
    assert r.json()["template_key"] == "retina"


def test_create_encounter_rejects_unknown_template(client):
    r = client.post(
        "/encounters",
        json=_create_payload(
            patient_identifier="PT-PHASE-A-BAD",
            template_key="bananas",
        ),
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "unknown_template_key"


def test_create_encounter_defaults_to_general(client):
    r = client.post(
        "/encounters",
        json=_create_payload(patient_identifier="PT-PHASE-A-DEFAULT"),
        headers=ADMIN1,
    )
    assert r.status_code == 201, r.text
    assert r.json()["template_key"] == "general_ophthalmology"


def test_template_key_is_returned_on_list(client):
    # seed one with each value so the list endpoint covers both branches
    client.post(
        "/encounters",
        json=_create_payload(
            patient_identifier="PT-PHASE-A-LIST-G",
            template_key="glaucoma",
        ),
        headers=ADMIN1,
    )
    r = client.get("/encounters", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    rows = body if isinstance(body, list) else body.get("items", [])
    keys = {row["template_key"] for row in rows}
    assert "glaucoma" in keys
    assert "general_ophthalmology" in keys
