"""Phase A item 4 — PM/RCM continuity handoff export contract tests.

Spec: docs/chartnav/closure/PHASE_A_PM_RCM_Continuity_and_Integration_Path.md

Covers:
  - POST /encounters/{id}/export on an unsigned encounter returns 409
    encounter_not_signed.
  - JSON, CSV, PDF, and manifest formats all returned correctly.
  - Payload schema_version == "1.0" and carries every required field
    listed in §5.1 of the spec.
  - RBAC: clinician/admin/biller_coder may export; technician/front_desk
    may not.
  - Vendor mappings are pure functions and produce the documented
    NextGen + AdvancedMD shapes.
  - The PDF body is a real, parseable PDF (starts with %PDF, ends with
    %%EOF).
"""
from __future__ import annotations

from .conftest import ADMIN1, BILLING1, CLIN1, REV1, TECH1


def _create_and_sign(client) -> int:
    """Helper: create an encounter, drive it to signed via the
    note_versions sign route, and return its id."""
    create = client.post(
        "/encounters",
        json={
            "organization_id": 1,
            "location_id": 1,
            "patient_identifier": "PT-EXPORT",
            "patient_name": "Export Patient",
            "provider_name": "Dr. Carter",
            "template_key": "retina",
        },
        headers=ADMIN1,
    )
    assert create.status_code == 201, create.text
    enc_id = create.json()["id"]

    # Walk the encounter through the legal status transitions to
    # `completed` so the immutability gate kicks in. The handoff
    # export reads encounter_attestations, which is written when the
    # note-version sign happens. We simulate sign by calling the
    # service directly (avoids needing a full transcript-to-note flow
    # inside this test file).
    from app.services.encounter_audit import record_attestation
    from app.db import transaction
    with transaction() as conn:
        record_attestation(
            conn,
            encounter_id=enc_id,
            encounter_snapshot={
                "id": enc_id,
                "template_key": "retina",
                "patient_identifier": "PT-EXPORT",
            },
            attested_by_user_id=1,
            typed_name="Casey Clinician",
            attestation_text="I attest that this note accurately reflects the visit.",
        )
    return enc_id


# -------- 409 when not signed ----------------------------------------

def test_export_unsigned_encounter_returns_409(client):
    create = client.post(
        "/encounters",
        json={
            "organization_id": 1,
            "location_id": 1,
            "patient_identifier": "PT-EXPORT-UNSIGNED",
            "patient_name": "Unsigned Patient",
            "provider_name": "Dr. Carter",
        },
        headers=ADMIN1,
    )
    enc_id = create.json()["id"]
    r = client.post(f"/encounters/{enc_id}/export", headers=CLIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "encounter_not_signed"


# -------- JSON payload contract --------------------------------------

def test_export_json_carries_v1_schema(client):
    enc_id = _create_and_sign(client)
    r = client.post(f"/encounters/{enc_id}/export?fmt=json", headers=CLIN1)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["schema_version"] == "1.0"
    assert payload["encounter_id"] == str(enc_id)
    assert payload["visit"]["template_key"] == "retina"
    assert payload["patient"]["mrn"] == "PT-EXPORT"
    assert payload["note"]["attestation_hash"].startswith("sha256:")
    assert payload["_truth"]["advisory_only"] is True
    assert payload["_truth"]["no_pm_rcm_integration"] is True


# -------- CSV format -------------------------------------------------

def test_export_csv_returns_text_csv(client):
    enc_id = _create_and_sign(client)
    r = client.post(f"/encounters/{enc_id}/export?fmt=csv", headers=CLIN1)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    body = r.text
    assert "schema_version,encounter_id" in body  # header row
    assert "PT-EXPORT" in body
    assert "retina" in body


# -------- PDF format -------------------------------------------------

def test_export_pdf_is_parseable(client):
    enc_id = _create_and_sign(client)
    r = client.post(f"/encounters/{enc_id}/export?fmt=pdf", headers=CLIN1)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    blob = r.content
    assert blob.startswith(b"%PDF-1.4")
    assert blob.rstrip().endswith(b"%%EOF")
    assert b"ChartNav" in blob
    assert b"manual handoff bundle" in blob


# -------- Manifest format --------------------------------------------

def test_export_manifest_lists_all_formats(client):
    enc_id = _create_and_sign(client)
    r = client.post(f"/encounters/{enc_id}/export?fmt=manifest", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "1.0"
    assert set(body["formats"]) == {"json", "csv", "pdf"}
    assert body["advisory_only"] is True
    assert body["no_pm_rcm_integration"] is True


# -------- RBAC -------------------------------------------------------

def test_export_allowed_for_clinician_admin_biller(client):
    enc_id = _create_and_sign(client)
    for h in (ADMIN1, CLIN1, BILLING1):
        r = client.post(f"/encounters/{enc_id}/export", headers=h)
        assert r.status_code == 200, h


def test_export_forbidden_for_technician_and_reviewer(client):
    enc_id = _create_and_sign(client)
    for h in (TECH1, REV1):
        r = client.post(f"/encounters/{enc_id}/export", headers=h)
        assert r.status_code == 403, h
        assert r.json()["detail"]["error_code"] == "role_cannot_export_handoff"


# -------- Vendor mappings (pure functions) ---------------------------

def test_nextgen_mapping_shape():
    from app.services.handoff_export import map_to_nextgen
    sample = {
        "schema_version": "1.0",
        "encounter_id": "enc_1",
        "encounter_date": "2026-04-22",
        "org": {"name": "Example", "npi_group": "1234567890"},
        "provider": {"full_name": "Jane Roe, MD", "npi_individual": "9876543210"},
        "patient": {"mrn": "MRN-1", "display_name": "Pat"},
        "visit": {"place_of_service": "11"},
        "codes": {
            "cpt": [{"code": "92014", "modifiers": [], "units": 1}],
            "icd10": [{"code": "H35.31", "rank": 1}],
        },
        "note": {"signed_at": "2026-04-22T19:02:14Z", "attestation_hash": "sha256:abc"},
    }
    out = map_to_nextgen(sample)
    assert out["EncounterID"] == "enc_1"
    assert out["RenderingProvider"]["NPI"] == "9876543210"
    assert out["ServiceLines"][0]["CPT"] == "92014"
    assert out["Diagnoses"][0]["ICD10"] == "H35.31"
    assert out["_advisory_only"] is True


def test_advancedmd_mapping_shape():
    from app.services.handoff_export import map_to_advancedmd
    sample = {
        "schema_version": "1.0",
        "encounter_id": "enc_2",
        "encounter_date": "2026-04-22",
        "org": {"name": "Example", "npi_group": "1234567890"},
        "provider": {"full_name": "Jane Roe", "npi_individual": "9876543210"},
        "patient": {"mrn": "MRN-2", "display_name": "Pat"},
        "visit": {"place_of_service": "11"},
        "codes": {
            "cpt": [{"code": "92134", "modifiers": ["RT"], "units": 1}],
            "icd10": [{"code": "H40.11", "rank": 1}],
        },
        "note": {"signed_at": "2026-04-22T19:02:14Z", "attestation_hash": "sha256:def"},
    }
    out = map_to_advancedmd(sample)
    assert out["encounter_external_id"] == "enc_2"
    assert out["procedures"][0]["modifiers"] == ["RT"]
    assert out["diagnoses"] == ["H40.11"]
    assert out["_advisory_only"] is True


def test_vendor_sample_files_exist():
    """Acceptance criterion §4: example payloads for NextGen + AdvancedMD
    + X12 + FHIR Claim must be committed in
    docs/chartnav/integration/samples/."""
    import pathlib
    base = pathlib.Path(__file__).resolve().parents[3] / "docs" / "chartnav" / "integration" / "samples"
    for name in (
        "nextgen_example.json",
        "advancedmd_example.json",
        "x12_837p_sketch.md",
        "fhir_claim_sketch.md",
    ):
        assert (base / name).is_file(), f"missing {name}"
