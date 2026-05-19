"""Phase 60 — Structured Vitals & Technician Workup tests.

Pins:
- create / read / update / list with mixed nullable fields;
- BMI is server-calculated from height + weight when both present;
- warning generation for partial BP, partial IOP, partial VA, etc.;
- enum validation for bp_position / bp_site / iop_method /
  dilation_status / etc.;
- lifecycle: draft -> entered -> reviewed -> signed;
- signed workups are immutable (PATCH / review / sign all 409);
- review requires `entered`; sign requires `reviewed`; sign requires
  attested=True;
- RBAC: admin / clinician / technician can write; technician CANNOT
  sign; reviewer / front_desk denied; cross-org returns 404;
- audit `detail` excludes every clinical body field (BP, temp, pulse,
  VA, IOP, notes) — proven with a canary;
- the response carries `requires_provider_review` and a closed
  `forbidden_actions` map; every action is False;
- no diagnosis / treatment / order / referral / billing / coding /
  device-integration / RPM text appears in response messages.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import text

from tests.conftest import ADMIN1, CLIN1, CLIN2, FRONT1, REV1, TECH1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def enc_id(seeded_ids):
    org1_id = seeded_ids["orgs"]["demo-eye-clinic"]
    for _pid, (eid, oid, _) in seeded_ids["encs"].items():
        if oid == org1_id:
            return eid
    pytest.fail("No org-1 encounters in seeded_ids")


def _create(client, enc_id, *, headers=None, **fields) -> dict[str, Any]:
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json=fields,
        headers=headers or CLIN1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _enter(client, workup_id, *, headers=None) -> dict[str, Any]:
    r = client.patch(
        f"/api/v1/vitals-workups/{workup_id}",
        json={"advance_to_entered": True},
        headers=headers or CLIN1,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _review(client, workup_id, *, headers=None):
    return client.post(
        f"/api/v1/vitals-workups/{workup_id}/review",
        json={},
        headers=headers or CLIN1,
    )


def _sign(client, workup_id, *, headers=None, attested=True):
    return client.post(
        f"/api/v1/vitals-workups/{workup_id}/sign",
        json={"attested": attested},
        headers=headers or CLIN1,
    )


# ---------------------------------------------------------------------------
# 1. Service unit tests — BMI + warnings
# ---------------------------------------------------------------------------


def test_calculate_bmi_in_lb_round_trip():
    from app.services.vitals_workup import calculate_bmi

    # 70 in, 154 lb → BMI ~22.1
    bmi = calculate_bmi(70, "in", 154, "lb")
    assert bmi == pytest.approx(22.1, abs=0.2)


def test_calculate_bmi_cm_kg():
    from app.services.vitals_workup import calculate_bmi

    # 178 cm, 70 kg → BMI ~22.1
    bmi = calculate_bmi(178, "cm", 70, "kg")
    assert bmi == pytest.approx(22.1, abs=0.2)


def test_calculate_bmi_missing_height_returns_none():
    from app.services.vitals_workup import calculate_bmi

    assert calculate_bmi(None, "in", 154, "lb") is None
    assert calculate_bmi(70, "in", None, "lb") is None
    assert calculate_bmi(0, "in", 154, "lb") is None


def test_warnings_for_partial_bp():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"bp_systolic": 120})
    assert any("diastolic missing" in s for s in w)


def test_warnings_for_partial_iop():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"iop_od": 14})
    assert any("IOP" in s and "OS" in s for s in w)


def test_warnings_for_partial_va():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"visual_acuity_od": "20/40"})
    assert any("VA" in s or "Visual acuity" in s for s in w)


def test_warnings_for_out_of_range_systolic_does_not_diagnose():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"bp_systolic": 220, "bp_diastolic": 130, "bp_site": "left_arm", "bp_position": "sitting"})
    # The message must be a "review required" prompt, NOT a diagnosis.
    text_blob = " | ".join(w).lower()
    assert "review" in text_blob
    assert "hypertensive crisis" not in text_blob
    assert "hypertension" not in text_blob
    assert "stroke" not in text_blob


def test_warnings_for_low_spo2_does_not_diagnose():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"oxygen_saturation": 85})
    text_blob = " | ".join(w).lower()
    assert "review" in text_blob
    assert "hypoxia" not in text_blob
    assert "respiratory failure" not in text_blob


def test_warnings_for_high_temp_does_not_diagnose():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings({"temperature_value": 103.5, "temperature_unit": "F"})
    text_blob = " | ".join(w).lower()
    assert "review" in text_blob
    assert "fever" not in text_blob
    assert "sepsis" not in text_blob
    assert "infection" not in text_blob


def test_warnings_empty_for_complete_typical_values():
    from app.services.vitals_workup import generate_warnings

    w = generate_warnings(
        {
            "bp_systolic": 118,
            "bp_diastolic": 76,
            "bp_position": "sitting",
            "bp_site": "left_arm",
            "pulse": 72,
            "respiratory_rate": 16,
            "oxygen_saturation": 98,
            "temperature_value": 98.6,
            "temperature_unit": "F",
            "height_value": 70,
            "weight_value": 154,
            "iop_od": 14,
            "iop_os": 13,
            "iop_method": "applanation",
            "visual_acuity_od": "20/20",
            "visual_acuity_os": "20/20",
        }
    )
    assert w == [], f"expected no warnings, got: {w!r}"


# ---------------------------------------------------------------------------
# 2. Create + read + list
# ---------------------------------------------------------------------------


def test_create_minimum_workup(client, enc_id):
    body = _create(client, enc_id)
    assert body["status"] == "draft"
    assert body["source_type"] == "technician_entry"
    assert body["requires_provider_review"] is True
    assert body["bmi"] is None
    # forbidden_actions all False — pin each key.
    for key in (
        "diagnosis",
        "treatment_recommendation",
        "orders",
        "referrals",
        "patient_message",
        "billing_or_coding",
        "device_integration",
        "remote_patient_monitoring",
        "auto_sign",
    ):
        assert body["forbidden_actions"][key] is False, key


def test_create_workup_calculates_bmi(client, enc_id):
    body = _create(
        client,
        enc_id,
        height_value=70,
        height_unit="in",
        weight_value=154,
        weight_unit="lb",
    )
    assert body["bmi"] == pytest.approx(22.1, abs=0.2)


def test_create_workup_persists_ophthalmology_fields(client, enc_id):
    body = _create(
        client,
        enc_id,
        visual_acuity_od="20/20",
        visual_acuity_os="20/25",
        iop_od=14.0,
        iop_os=13.5,
        iop_method="applanation",
        dilation_status="dilated",
    )
    assert body["visual_acuity_od"] == "20/20"
    assert body["visual_acuity_os"] == "20/25"
    assert body["iop_od"] == pytest.approx(14.0)
    assert body["iop_os"] == pytest.approx(13.5)
    assert body["iop_method"] == "applanation"
    assert body["dilation_status"] == "dilated"


def test_partial_bp_emits_warning_on_create(client, enc_id):
    body = _create(client, enc_id, bp_systolic=120)
    assert any("diastolic missing" in w for w in body["warnings"])


def test_get_workup_returns_full_shape(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    r = client.get(
        f"/api/v1/vitals-workups/{created['id']}", headers=CLIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["pulse"] == 72
    assert body["id"] == created["id"]


def test_list_by_encounter_returns_workups(client, enc_id):
    _create(client, enc_id, pulse=70)
    _create(client, enc_id, pulse=80)
    r = client.get(
        f"/api/v1/encounters/{enc_id}/vitals-workups", headers=CLIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 2


# ---------------------------------------------------------------------------
# 3. Enum validation
# ---------------------------------------------------------------------------


def test_invalid_bp_position_rejected(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json={"bp_position": "upside_down"},
        headers=CLIN1,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_enum"


def test_invalid_iop_method_rejected(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json={"iop_method": "vibes"},
        headers=CLIN1,
    )
    assert r.status_code == 422


def test_negative_systolic_rejected_by_pydantic(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json={"bp_systolic": -10},
        headers=CLIN1,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. Update + lifecycle
# ---------------------------------------------------------------------------


def test_update_workup_recalculates_bmi(client, enc_id):
    created = _create(client, enc_id, height_value=70, weight_value=154)
    assert created["bmi"] == pytest.approx(22.1, abs=0.2)
    r = client.patch(
        f"/api/v1/vitals-workups/{created['id']}",
        json={"weight_value": 200},
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["bmi"] == pytest.approx(28.7, abs=0.3)


def test_advance_draft_to_entered(client, enc_id):
    created = _create(client, enc_id, bp_systolic=120, bp_diastolic=80, bp_site="left_arm", bp_position="sitting")
    r = client.patch(
        f"/api/v1/vitals-workups/{created['id']}",
        json={"advance_to_entered": True},
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "entered"


def test_review_requires_entered_status(client, enc_id):
    created = _create(client, enc_id)
    # status is still draft — review must refuse.
    r = _review(client, created["id"])
    assert r.status_code == 409
    assert "transition" in r.json()["detail"]["error_code"]


def test_review_from_entered_succeeds(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    r = _review(client, created["id"])
    assert r.status_code == 200
    assert r.json()["status"] == "reviewed"


def test_sign_requires_reviewed_status(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    # Skip review — sign must refuse.
    r = _sign(client, created["id"])
    assert r.status_code == 409
    assert "transition" in r.json()["detail"]["error_code"]


def test_sign_requires_attestation(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    _review(client, created["id"])
    r = _sign(client, created["id"], attested=False)
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "attestation_required"


def test_full_lifecycle_walkthrough(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    r2 = _review(client, created["id"])
    assert r2.status_code == 200
    r3 = _sign(client, created["id"])
    assert r3.status_code == 200
    body = r3.json()
    assert body["status"] == "signed"
    assert body["signed_at"] is not None
    assert body["is_terminal"] is True
    assert body["requires_provider_review"] is False


def test_signed_workup_patch_returns_409(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    _review(client, created["id"])
    _sign(client, created["id"])
    r = client.patch(
        f"/api/v1/vitals-workups/{created['id']}",
        json={"pulse": 80},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "workup_immutable"


def test_double_sign_returns_409(client, enc_id):
    created = _create(client, enc_id, pulse=72)
    _enter(client, created["id"])
    _review(client, created["id"])
    r1 = _sign(client, created["id"])
    first_signed_at = r1.json()["signed_at"]
    r2 = _sign(client, created["id"])
    assert r2.status_code == 409
    after = client.get(
        f"/api/v1/vitals-workups/{created['id']}", headers=CLIN1
    ).json()
    assert after["signed_at"] == first_signed_at


# ---------------------------------------------------------------------------
# 5. RBAC
# ---------------------------------------------------------------------------


def test_admin_can_create(client, enc_id):
    body = _create(client, enc_id, headers=ADMIN1)
    assert body["status"] == "draft"


def test_technician_can_create_and_enter(client, enc_id):
    body = _create(client, enc_id, headers=TECH1, pulse=70)
    r = client.patch(
        f"/api/v1/vitals-workups/{body['id']}",
        json={"advance_to_entered": True},
        headers=TECH1,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "entered"


def test_technician_cannot_review(client, enc_id):
    body = _create(client, enc_id, headers=TECH1, pulse=70)
    _enter(client, body["id"], headers=TECH1)
    r = _review(client, body["id"], headers=TECH1)
    assert r.status_code == 403


def test_technician_cannot_sign(client, enc_id):
    """Phase 60 — technician role can capture vitals but cannot sign."""
    body = _create(client, enc_id, headers=TECH1, pulse=70)
    _enter(client, body["id"], headers=TECH1)
    _review(client, body["id"], headers=CLIN1)
    r = _sign(client, body["id"], headers=TECH1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


def test_reviewer_cannot_create(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json={"pulse": 70},
        headers=REV1,
    )
    assert r.status_code == 403


def test_front_desk_cannot_create(client, enc_id):
    r = client.post(
        f"/api/v1/encounters/{enc_id}/vitals-workups",
        json={"pulse": 70},
        headers=FRONT1,
    )
    assert r.status_code == 403


def test_cross_org_get_returns_404(client, enc_id):
    body = _create(client, enc_id, pulse=70)
    r = client.get(
        f"/api/v1/vitals-workups/{body['id']}", headers=CLIN2
    )
    assert r.status_code == 404


def test_cross_org_list_returns_404(client, enc_id):
    r = client.get(
        f"/api/v1/encounters/{enc_id}/vitals-workups", headers=CLIN2
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6. Audit minimization — canary on every clinical field
# ---------------------------------------------------------------------------


_AUDIT_CANARY_NOTES = "PHASE60_AUDIT_CANARY clinician notes go here"


def _max_audit_id():
    from app.db import engine

    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT COALESCE(MAX(id), 0) FROM security_audit_events")
        ).fetchone()
    return int(r[0]) if r else 0


def test_audit_detail_excludes_clinical_body(client, enc_id):
    """Phase 60 — every audited vitals action must keep BP / temp /
    pulse / VA / IOP / technician_notes out of the audit detail.
    A canary value in technician_notes proves the contract."""
    from app.db import engine

    before = _max_audit_id()
    body = _create(
        client,
        enc_id,
        bp_systolic=121,
        bp_diastolic=77,
        bp_site="left_arm",
        bp_position="sitting",
        temperature_value=98.7,
        pulse=73,
        respiratory_rate=16,
        oxygen_saturation=98,
        visual_acuity_od="20/40",
        visual_acuity_os="20/25",
        iop_od=15.5,
        iop_os=14.0,
        iop_method="applanation",
        technician_notes=_AUDIT_CANARY_NOTES,
    )
    _enter(client, body["id"])
    _review(client, body["id"])
    _sign(client, body["id"])

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, event_type, detail FROM security_audit_events "
                "WHERE id > :since AND event_type LIKE 'vitals_workup_%' "
                "ORDER BY id ASC"
            ),
            {"since": before},
        ).fetchall()

    assert rows, "expected vitals_workup_* audit rows"
    forbidden = [
        _AUDIT_CANARY_NOTES,
        "121",  # bp systolic value
        "20/40",  # VA value
        "15.5",  # IOP value
        "applanation",  # iop method
        "98.7",  # temperature value
    ]
    for row in rows:
        detail = row[2] or ""
        for needle in forbidden:
            assert needle not in detail, (
                f"audit row {row[0]} ({row[1]}) leaked {needle!r}: "
                f"detail={detail!r}"
            )
    # Sanity: workup_id traceability metadata IS in the detail.
    assert any(f"workup_id={body['id']}" in (r[2] or "") for r in rows)
    # And action metadata is present.
    assert any("action=create" in (r[2] or "") for r in rows)
    assert any("action=sign" in (r[2] or "") for r in rows)


# ---------------------------------------------------------------------------
# 7. Output safety — no diagnosis / treatment / order / referral / etc.
# ---------------------------------------------------------------------------


def test_warnings_never_use_diagnosis_or_treatment_language(client, enc_id):
    """A high-BP + high-temp + low-SpO2 workup must produce review
    prompts, NOT diagnostic or treatment language."""
    body = _create(
        client,
        enc_id,
        bp_systolic=210,
        bp_diastolic=125,
        bp_site="left_arm",
        bp_position="sitting",
        temperature_value=103.8,
        temperature_unit="F",
        oxygen_saturation=82,
    )
    blob = " | ".join(body["warnings"]).lower()
    # Must NOT contain diagnostic / treatment / order language.
    for bad in [
        "hypertensive crisis",
        "hypertension",
        "stroke",
        "myocardial",
        "heart attack",
        "fever",
        "sepsis",
        "hypoxia",
        "respiratory failure",
        "diagnosis confirmed",
        "treatment recommended",
        "treatment recommendation",
        "give medication",
        "prescribe",
        "order ekg",
        "send to er",
        "refer to",
        "patient message",
        "cpt code",
        "icd-10",
        "billing code",
    ]:
        assert bad not in blob, f"unsafe phrase appeared: {bad!r}"


def test_response_forbidden_actions_includes_every_required_key(
    client, enc_id
):
    body = _create(client, enc_id)
    required = (
        "diagnosis",
        "treatment_recommendation",
        "orders",
        "referrals",
        "patient_message",
        "billing_or_coding",
        "device_integration",
        "remote_patient_monitoring",
        "auto_sign",
    )
    for key in required:
        assert key in body["forbidden_actions"], f"missing key: {key}"
        assert body["forbidden_actions"][key] is False, key
