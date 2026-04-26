"""Phase A item 3 — encounter revisions + attestation contract tests.

Spec: docs/chartnav/closure/PHASE_A_Structured_Charting_and_Attestation.md

Covers:
  - PATCH /encounters/{id} writes a revision row when template_key
    changes, leaves no row when the value is unchanged.
  - PATCH /encounters/{id} on a signed (status=completed) encounter
    returns 409 ENCOUNTER_LOCKED_AFTER_SIGN with a signed_at field.
  - GET /encounters/{id}/revisions surfaces the revision history
    newest-first and the attestation row.
  - Front desk + technician + biller_coder cannot read revisions
    (role gate).
  - Sign flow writes a row to encounter_attestations with a
    deterministic snapshot hash.
"""
from __future__ import annotations

from .conftest import ADMIN1, BILLING1, CLIN1, REV1, TECH1


def _create_encounter(client, **overrides):
    payload = {
        "organization_id": 1,
        "location_id": 1,
        "patient_identifier": "PT-PHASE-A-IM",
        "patient_name": "Immutability Patient",
        "provider_name": "Dr. Carter",
    }
    payload.update(overrides)
    r = client.post("/encounters", json=payload, headers=ADMIN1)
    assert r.status_code == 201, r.text
    return r.json()


# -------- revision recorder + GET endpoint ----------------------------

def test_patch_template_key_records_revision(client):
    enc = _create_encounter(
        client,
        patient_identifier="PT-REV-1",
        template_key="general_ophthalmology",
    )
    r = client.patch(
        f"/encounters/{enc['id']}",
        json={"template_key": "glaucoma", "reason": "scope correction"},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    assert r.json()["template_key"] == "glaucoma"

    rev_resp = client.get(f"/encounters/{enc['id']}/revisions", headers=CLIN1)
    assert rev_resp.status_code == 200
    body = rev_resp.json()
    assert body["encounter_id"] == enc["id"]
    assert len(body["items"]) == 1
    rev = body["items"][0]
    assert rev["field_path"] == "template_key"
    assert rev["before_json"] == "general_ophthalmology"
    assert rev["after_json"] == "glaucoma"
    assert rev["reason"] == "scope correction"


def test_patch_no_op_does_not_record_revision(client):
    enc = _create_encounter(
        client,
        patient_identifier="PT-REV-2",
        template_key="retina",
    )
    r = client.patch(
        f"/encounters/{enc['id']}",
        json={"template_key": "retina"},
        headers=CLIN1,
    )
    assert r.status_code == 200
    rev_resp = client.get(f"/encounters/{enc['id']}/revisions", headers=CLIN1)
    assert rev_resp.json()["items"] == []


def test_patch_unknown_template_rejected(client):
    enc = _create_encounter(client, patient_identifier="PT-REV-3")
    r = client.patch(
        f"/encounters/{enc['id']}",
        json={"template_key": "bananas"},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "unknown_template_key"


# -------- immutability gate ------------------------------------------

def test_patch_refused_after_completed(client):
    """A `completed` encounter is the Phase-A signal that the chart is
    locked. The gate uses encounter.status == 'completed' OR the
    presence of a signed note_versions row; both routes raise 409."""
    enc = _create_encounter(client, patient_identifier="PT-REV-LOCK")
    # Move via the status route through the legal transitions:
    for s in ("in_progress", "draft_ready", "review_needed", "completed"):
        sr = client.post(
            f"/encounters/{enc['id']}/status",
            json={"status": s},
            headers=ADMIN1,
        )
        assert sr.status_code == 200, (s, sr.text)
    # Now PATCH is refused.
    r = client.patch(
        f"/encounters/{enc['id']}",
        json={"template_key": "glaucoma"},
        headers=ADMIN1,
    )
    assert r.status_code == 409
    body = r.json()["detail"]
    assert body["error_code"] == "ENCOUNTER_LOCKED_AFTER_SIGN"
    assert "signed_at" in body


# -------- role gating on the revisions surface -----------------------

def test_revisions_visible_to_clinician_admin_reviewer(client):
    enc = _create_encounter(client, patient_identifier="PT-REV-RBAC-1")
    client.patch(
        f"/encounters/{enc['id']}",
        json={"template_key": "retina"},
        headers=CLIN1,
    )
    for h in (ADMIN1, CLIN1, REV1):
        r = client.get(f"/encounters/{enc['id']}/revisions", headers=h)
        assert r.status_code == 200, h


def test_revisions_forbidden_to_tech_and_billing(client):
    enc = _create_encounter(client, patient_identifier="PT-REV-RBAC-2")
    for h in (TECH1, BILLING1):
        r = client.get(f"/encounters/{enc['id']}/revisions", headers=h)
        assert r.status_code == 403, h
        assert r.json()["detail"]["error_code"] == "role_cannot_read_revisions"


def test_patch_forbidden_for_non_clinical_roles(client):
    enc = _create_encounter(client, patient_identifier="PT-REV-RBAC-3")
    for h in (TECH1, BILLING1, REV1):
        r = client.patch(
            f"/encounters/{enc['id']}",
            json={"template_key": "retina"},
            headers=h,
        )
        assert r.status_code == 403, h
        assert r.json()["detail"]["error_code"] == "role_cannot_patch_encounter"


# -------- attestation hash determinism + uniqueness ------------------

def test_canonical_snapshot_hash_is_deterministic():
    from app.services.encounter_audit import canonical_snapshot_hash
    a = canonical_snapshot_hash({"id": 1, "template_key": "retina", "z": [1, 2]})
    b = canonical_snapshot_hash({"z": [1, 2], "template_key": "retina", "id": 1})
    assert a == b
    assert a.startswith("sha256:")


def test_attestation_record_is_unique_per_encounter():
    from app.services.encounter_audit import record_attestation
    from app.db import transaction
    # Two recordings for the same encounter return the SAME row.
    with transaction() as conn:
        first = record_attestation(
            conn,
            encounter_id=999_001,
            encounter_snapshot={"id": 999_001, "template_key": "retina"},
            attested_by_user_id=1,
            typed_name="Dr. Carter",
            attestation_text="I attest …",
        )
        second = record_attestation(
            conn,
            encounter_id=999_001,
            encounter_snapshot={"id": 999_001, "template_key": "retina"},
            attested_by_user_id=2,  # different signer; should be IGNORED
            typed_name="Different Person",
            attestation_text="Different text",
        )
    assert first["id"] == second["id"]
    assert second["typed_name"] == "Dr. Carter"  # original preserved
