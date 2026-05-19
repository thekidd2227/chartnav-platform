from __future__ import annotations

import json

import pytest

from tests.conftest import CLIN1, CLIN2, FRONT1, TECH1


@pytest.fixture()
def enc_id(seeded_ids):
    org1_id = seeded_ids["orgs"]["demo-eye-clinic"]
    for _pid, (eid, oid, _) in seeded_ids["encs"].items():
        if oid == org1_id:
            return eid
    pytest.fail("No org-1 encounter found")


def _create(client, enc_id, headers=CLIN1, payload=None):
    body = {
        "bp_systolic": 118,
        "bp_diastolic": 74,
        "bp_position": "sitting",
        "bp_site": "left_arm",
        "height_value": 70,
        "weight_value": 175,
        "visual_acuity_od": "20/30",
        "visual_acuity_os": "20/25",
        "iop_od": 16,
        "iop_os": 15,
        "iop_method": "tonopen",
        "allergies_reviewed": True,
        "medications_reviewed": True,
        "technician_notes": "Synthetic demo intake note.",
    }
    if payload:
        body.update(payload)
    return client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        headers=headers,
        json=body,
    )


def test_create_workup_with_basic_vitals(client, enc_id):
    r = _create(client, enc_id)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "entered"
    assert body["bp_systolic"] == 118
    assert body["bp_diastolic"] == 74
    assert body["warnings_json"] == []


def test_bmi_calculated_when_height_weight_present(client, enc_id):
    r = _create(client, enc_id, payload={"height_value": 70, "weight_value": 175})
    assert r.status_code == 201
    assert r.json()["bmi"] == pytest.approx(25.11, rel=0.01)


def test_missing_partial_bp_creates_warning(client, enc_id):
    r = _create(
        client,
        enc_id,
        payload={"bp_diastolic": None, "bp_site": None, "bp_position": None},
    )
    assert r.status_code == 201
    warnings = r.json()["warnings_json"]
    assert any("systolic entered without diastolic" in w for w in warnings)
    assert any("without site" in w for w in warnings)
    assert any("without position" in w for w in warnings)


def test_va_iop_ophthalmology_fields_persist(client, enc_id):
    r = _create(
        client,
        enc_id,
        payload={
            "visual_acuity_od": "20/40",
            "visual_acuity_os": "20/30",
            "visual_acuity_ou": "20/25",
            "iop_od": 18,
            "iop_os": 16,
            "iop_method": "applanation",
            "dilation_status": "dilated",
        },
    )
    body = r.json()
    workup_id = body["id"]
    detail = client.get(f"/api/v1/vitals-workups/{workup_id}", headers=CLIN1)
    assert detail.status_code == 200
    got = detail.json()
    assert got["visual_acuity_od"] == "20/40"
    assert got["visual_acuity_os"] == "20/30"
    assert got["visual_acuity_ou"] == "20/25"
    assert got["iop_od"] == 18
    assert got["iop_os"] == 16
    assert got["iop_method"] == "applanation"
    assert got["dilation_status"] == "dilated"


def test_list_by_encounter_works(client, enc_id):
    created = _create(client, enc_id).json()
    r = client.get(f"/api/v1/encounters/{enc_id}/vitals-workups", headers=CLIN1)
    assert r.status_code == 200
    assert any(item["id"] == created["id"] for item in r.json())


def test_update_unsigned_workup_works(client, enc_id):
    workup_id = _create(client, enc_id, payload={"pulse": 72}).json()["id"]
    r = client.patch(
        f"/api/v1/vitals-workups/{workup_id}",
        headers=CLIN1,
        json={"pulse": 76, "respiratory_rate": 14},
    )
    assert r.status_code == 200
    assert r.json()["pulse"] == 76
    assert r.json()["respiratory_rate"] == 14


def test_review_writes_audit_event(client, enc_id):
    workup_id = _create(client, enc_id).json()["id"]
    r = client.post(
        f"/api/v1/vitals-workups/{workup_id}/review",
        headers=CLIN1,
        json={"reviewed": True},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "reviewed"
    from app.audit import query_recent

    recent = query_recent(10)
    assert any(e["event_type"] == "vitals_workup_reviewed" for e in recent)


def test_sign_requires_attestation(client, enc_id):
    workup_id = _create(client, enc_id).json()["id"]
    client.post(
        f"/api/v1/vitals-workups/{workup_id}/review",
        headers=CLIN1,
        json={"reviewed": True},
    )
    r = client.post(
        f"/api/v1/vitals-workups/{workup_id}/sign",
        headers=CLIN1,
        json={"attested": False},
    )
    assert r.status_code == 422


def test_signed_workup_immutable(client, enc_id):
    workup_id = _create(client, enc_id).json()["id"]
    client.post(
        f"/api/v1/vitals-workups/{workup_id}/review",
        headers=CLIN1,
        json={"reviewed": True},
    )
    signed = client.post(
        f"/api/v1/vitals-workups/{workup_id}/sign",
        headers=CLIN1,
        json={"attested": True},
    )
    assert signed.status_code == 200
    r = client.patch(
        f"/api/v1/vitals-workups/{workup_id}",
        headers=CLIN1,
        json={"pulse": 80},
    )
    assert r.status_code == 409


def test_cross_org_returns_404(client, enc_id):
    workup_id = _create(client, enc_id).json()["id"]
    r = client.get(f"/api/v1/vitals-workups/{workup_id}", headers=CLIN2)
    assert r.status_code == 404
    r2 = client.get(f"/api/v1/encounters/{enc_id}/vitals-workups", headers=CLIN2)
    assert r2.status_code == 404


def test_wrong_role_denied(client, enc_id):
    r = _create(client, enc_id, headers=FRONT1)
    assert r.status_code == 403


def test_technician_can_enter_but_cannot_sign(client, enc_id):
    created = _create(client, enc_id, headers=TECH1)
    assert created.status_code == 201
    workup_id = created.json()["id"]
    reviewed = client.post(
        f"/api/v1/vitals-workups/{workup_id}/review",
        headers=CLIN1,
        json={"reviewed": True},
    )
    assert reviewed.status_code == 200
    signed = client.post(
        f"/api/v1/vitals-workups/{workup_id}/sign",
        headers=TECH1,
        json={"attested": True},
    )
    assert signed.status_code == 403


def test_audit_detail_excludes_vitals_values_and_notes(client, enc_id):
    _create(
        client,
        enc_id,
        payload={
            "bp_systolic": 151,
            "bp_diastolic": 93,
            "temperature_value": 99.1,
            "pulse": 88,
            "visual_acuity_od": "20/60",
            "iop_od": 21,
            "technician_notes": "Do not put this note in audit.",
        },
    )
    from app.audit import query_recent

    event = next(e for e in query_recent(10) if e["event_type"] == "vitals_workup_created")
    detail = event["detail"] or ""
    for forbidden in ["151", "93", "99.1", "88", "20/60", "21", "Do not put this note"]:
        assert forbidden not in detail
    assert "workup_id=" in detail
    assert "warning_count=" in detail


def test_no_forbidden_clinical_action_output(client, enc_id):
    r = _create(client, enc_id, payload={"oxygen_saturation": 90, "temperature_value": 101})
    blob = json.dumps(r.json()).lower()
    forbidden = [
        "diagnosis confirmed",
        "treatment recommended",
        "order placed",
        "referral",
        "patient message",
        "billing code",
        "automatic coding",
    ]
    for phrase in forbidden:
        assert phrase not in blob


def test_alembic_upgrade_head_exercised_by_fixture(seeded_ids):
    assert "demo-eye-clinic" in seeded_ids["orgs"]
