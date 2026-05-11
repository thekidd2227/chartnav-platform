"""Phase 21A — Retina + Glaucoma specialty tracking tests.

Coverage groups:
  * Retina tracking: list/create/patch + RBAC + isolation + audit safety
  * Retina injection events: list/create + technician create permission
  * Glaucoma tracking: list/create/patch + RBAC + isolation
  * Glaucoma IOP measurements: validation (0..80) + invalid eye + create
  * Glaucoma visual field tests: list/create
  * Cross-org no-existence-leak: foreign patient/record returns 404
  * Audit metadata-only: clinical body never serialized into audit detail
"""

from __future__ import annotations

import sqlite3

from tests.conftest import (
    ADMIN1,
    ADMIN2,
    CLIN1,
    CLIN2,
    FRONT1,
    REV1,
    TECH1,
)


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _create_patient(client, headers, **overrides) -> dict:
    body = {
        "patient_identifier": "PT-PHASE21A",
        "first_name": "Specialty",
        "last_name": "TrackingTest",
        "date_of_birth": "1955-04-12",
        "sex_at_birth": "female",
    }
    body.update(overrides)
    r = client.post("/patients", headers=headers, json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _create_retina(client, headers, patient_id, **overrides) -> dict:
    body = {
        "eye": "OD",
        "condition": "neovascular AMD",
        "severity": "moderate",
        "follow_up_interval": "4 weeks",
        "review_status": "draft",
        "provider_assessment": (
            "stable; continue current monitoring schedule (clinical text)"
        ),
    }
    body.update(overrides)
    r = client.post(
        f"/patients/{patient_id}/retina", headers=headers, json=body
    )
    return r


def _create_glaucoma(client, headers, patient_id, **overrides) -> dict:
    body = {
        "eye": "OS",
        "glaucoma_type": "POAG",
        "target_iop": 16.0,
        "latest_iop": 18.5,
        "cup_to_disc_ratio": 0.6,
        "rnfl_status": "thinning",
        "visual_field_status": "stable",
        "medication_plan": "latanoprost qhs OS (clinical text)",
        "progression_risk_label": "moderate",
        "review_status": "draft",
        "provider_assessment": "monitor; recheck in 12 weeks (clinical text)",
    }
    body.update(overrides)
    r = client.post(
        f"/patients/{patient_id}/glaucoma", headers=headers, json=body
    )
    return r


# =====================================================================
# Retina tracking
# =====================================================================


class TestRetinaTracking:
    def test_clinician_creates_lists_patches(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_retina(client, CLIN1, p["id"])
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["eye"] == "OD"
        assert body["condition"] == "neovascular AMD"
        assert body["review_status"] == "draft"
        record_id = body["id"]

        # list
        rl = client.get(
            f"/patients/{p['id']}/retina", headers=CLIN1
        )
        assert rl.status_code == 200
        listed = rl.json()
        assert listed["total"] == 1
        assert listed["items"][0]["id"] == record_id

        # patch — change status + severity
        rp = client.patch(
            f"/patients/{p['id']}/retina/{record_id}",
            headers=CLIN1,
            json={"review_status": "reviewed", "severity": "advanced"},
        )
        assert rp.status_code == 200, rp.text
        patched = rp.json()
        assert patched["review_status"] == "reviewed"
        assert patched["severity"] == "advanced"
        assert patched["updated_by_user_id"] is not None

    def test_admin_can_create(self, client):
        p = _create_patient(client, ADMIN1)
        r = _create_retina(client, ADMIN1, p["id"])
        assert r.status_code == 201

    def test_reviewer_read_only(self, client):
        p = _create_patient(client, CLIN1)
        _create_retina(client, CLIN1, p["id"])

        # Reviewer can list
        rl = client.get(f"/patients/{p['id']}/retina", headers=REV1)
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

        # Reviewer cannot create
        rc = _create_retina(client, REV1, p["id"], condition="diabetic retinopathy")
        assert rc.status_code == 403
        assert rc.json()["detail"]["error_code"] == "specialty_role_forbidden"

        # Reviewer cannot patch
        record_id = rl.json()["items"][0]["id"]
        rp = client.patch(
            f"/patients/{p['id']}/retina/{record_id}",
            headers=REV1,
            json={"review_status": "reviewed"},
        )
        assert rp.status_code == 403

    def test_technician_cannot_create_tracking_row(self, client):
        p = _create_patient(client, CLIN1)
        rc = _create_retina(client, TECH1, p["id"])
        assert rc.status_code == 403

    def test_front_desk_has_no_access(self, client):
        p = _create_patient(client, CLIN1)
        # No write
        rc = _create_retina(client, FRONT1, p["id"])
        assert rc.status_code == 403
        # No read
        rl = client.get(f"/patients/{p['id']}/retina", headers=FRONT1)
        assert rl.status_code == 403

    def test_invalid_eye_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_retina(client, CLIN1, p["id"], eye="XX")
        assert r.status_code in (400, 422)

    def test_invalid_review_status_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_retina(client, CLIN1, p["id"], review_status="approved")
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_review_status"

    def test_cross_org_patient_returns_404(self, client):
        # Create a patient in Org 1
        p = _create_patient(client, CLIN1)
        # Org 2 clinician asks about that patient → 404
        rl = client.get(f"/patients/{p['id']}/retina", headers=CLIN2)
        assert rl.status_code == 404
        assert rl.json()["detail"]["error_code"] == "patient_not_found"

    def test_cross_org_record_returns_404(self, client):
        # Org 1 clinician creates the row
        p = _create_patient(client, CLIN1)
        cr = _create_retina(client, CLIN1, p["id"])
        record_id = cr.json()["id"]

        # Org 2 clinician creates their own patient and tries to
        # patch the Org-1 record — must 404 on the patient first.
        p2 = _create_patient(
            client,
            CLIN2,
            patient_identifier="PT-O2-21A",
        )
        rp = client.patch(
            f"/patients/{p2['id']}/retina/{record_id}",
            headers=CLIN2,
            json={"review_status": "reviewed"},
        )
        assert rp.status_code == 404
        assert (
            rp.json()["detail"]["error_code"] == "retina_tracking_not_found"
        )

    def test_audit_excludes_clinical_body(self, client, test_db):
        p = _create_patient(client, CLIN1)
        r = _create_retina(client, CLIN1, p["id"])
        record_id = r.json()["id"]
        # Patch to include another clinical body
        client.patch(
            f"/patients/{p['id']}/retina/{record_id}",
            headers=CLIN1,
            json={"provider_assessment": "SECRET clinical assessment text"},
        )
        # Inspect audit_log directly
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT event_type, detail FROM security_audit_events "
                "WHERE event_type IN ('retina_tracking_created', "
                "'retina_tracking_updated')"
            ).fetchall()
        finally:
            conn.close()
        assert rows, "expected at least one retina audit row"
        for event_type, detail in rows:
            assert detail is not None
            assert "SECRET" not in detail
            assert "clinical text" not in (detail or "")
            assert "neovascular AMD" not in detail
            assert "monitor; recheck" not in (detail or "")


# =====================================================================
# Retina injection events
# =====================================================================


class TestRetinaInjections:
    def test_clinician_creates_and_lists(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/retina/injections",
            headers=CLIN1,
            json={
                "eye": "OD",
                "medication": "aflibercept",
                "procedure_date": "2026-04-01T10:30:00",
                "notes": "uneventful procedure (clinical text)",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["eye"] == "OD"
        assert body["medication"] == "aflibercept"

        rl = client.get(
            f"/patients/{p['id']}/retina/injections", headers=CLIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

    def test_technician_can_create_injection(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/retina/injections",
            headers=TECH1,
            json={"eye": "OS", "medication": "ranibizumab"},
        )
        assert r.status_code == 201

    def test_reviewer_cannot_create_injection(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/retina/injections",
            headers=REV1,
            json={"eye": "OS"},
        )
        assert r.status_code == 403

    def test_front_desk_cannot_create_injection(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/retina/injections",
            headers=FRONT1,
            json={"eye": "OS"},
        )
        assert r.status_code == 403


# =====================================================================
# Glaucoma tracking
# =====================================================================


class TestGlaucomaTracking:
    def test_clinician_creates_lists_patches(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_glaucoma(client, CLIN1, p["id"])
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["eye"] == "OS"
        assert body["glaucoma_type"] == "POAG"
        assert body["target_iop"] == 16.0
        assert body["latest_iop"] == 18.5

        record_id = body["id"]
        rl = client.get(f"/patients/{p['id']}/glaucoma", headers=CLIN1)
        assert rl.json()["total"] == 1

        rp = client.patch(
            f"/patients/{p['id']}/glaucoma/{record_id}",
            headers=CLIN1,
            json={
                "review_status": "needs_review",
                "latest_iop": 22.0,
                "progression_risk_label": "high",
            },
        )
        assert rp.status_code == 200
        patched = rp.json()
        assert patched["review_status"] == "needs_review"
        assert patched["latest_iop"] == 22.0
        assert patched["progression_risk_label"] == "high"

    def test_reviewer_read_only(self, client):
        p = _create_patient(client, CLIN1)
        _create_glaucoma(client, CLIN1, p["id"])

        rl = client.get(f"/patients/{p['id']}/glaucoma", headers=REV1)
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

        rc = _create_glaucoma(client, REV1, p["id"], glaucoma_type="NTG")
        assert rc.status_code == 403

    def test_front_desk_no_access(self, client):
        p = _create_patient(client, CLIN1)
        rl = client.get(f"/patients/{p['id']}/glaucoma", headers=FRONT1)
        assert rl.status_code == 403

    def test_invalid_eye_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_glaucoma(client, CLIN1, p["id"], eye="LEFT")
        assert r.status_code in (400, 422)

    def test_invalid_review_status_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_glaucoma(client, CLIN1, p["id"], review_status="signed")
        assert r.status_code == 400

    def test_cross_org_patient_returns_404(self, client):
        p = _create_patient(client, CLIN1)
        rl = client.get(f"/patients/{p['id']}/glaucoma", headers=CLIN2)
        assert rl.status_code == 404

    def test_cross_org_record_returns_404(self, client):
        p = _create_patient(client, CLIN1)
        cr = _create_glaucoma(client, CLIN1, p["id"])
        record_id = cr.json()["id"]
        p2 = _create_patient(
            client, CLIN2, patient_identifier="PT-O2-G21A"
        )
        rp = client.patch(
            f"/patients/{p2['id']}/glaucoma/{record_id}",
            headers=CLIN2,
            json={"review_status": "reviewed"},
        )
        assert rp.status_code == 404

    def test_audit_excludes_clinical_body(self, client, test_db):
        p = _create_patient(client, CLIN1)
        cr = _create_glaucoma(client, CLIN1, p["id"])
        record_id = cr.json()["id"]
        client.patch(
            f"/patients/{p['id']}/glaucoma/{record_id}",
            headers=CLIN1,
            json={"medication_plan": "SECRET med plan text"},
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT event_type, detail FROM security_audit_events "
                "WHERE event_type LIKE 'glaucoma_tracking_%'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for event_type, detail in rows:
            assert "SECRET" not in (detail or "")
            assert "latanoprost" not in (detail or "")
            assert "monitor; recheck" not in (detail or "")


# =====================================================================
# Glaucoma IOP measurements
# =====================================================================


class TestIopMeasurements:
    def test_clinician_creates_and_lists(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/iop",
            headers=CLIN1,
            json={
                "eye": "OD",
                "iop_value": 18.0,
                "measured_at": "2026-04-15T10:00:00",
                "method": "Goldmann",
            },
        )
        assert r.status_code == 201
        rl = client.get(
            f"/patients/{p['id']}/glaucoma/iop", headers=CLIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

    def test_technician_can_create_iop(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/iop",
            headers=TECH1,
            json={"eye": "OS", "iop_value": 22.0},
        )
        assert r.status_code == 201

    def test_invalid_eye_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/iop",
            headers=CLIN1,
            json={"eye": "OU", "iop_value": 18.0},
        )
        # IOP measurements only allow OD/OS — OU should be rejected.
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_eye"

    def test_iop_value_out_of_range_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/iop",
            headers=CLIN1,
            json={"eye": "OD", "iop_value": 999.0},
        )
        # Pydantic ge/le rejects out-of-range values at the schema layer.
        assert r.status_code in (400, 422)

    def test_reviewer_cannot_create_iop(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/iop",
            headers=REV1,
            json={"eye": "OD", "iop_value": 18.0},
        )
        assert r.status_code == 403


# =====================================================================
# Glaucoma visual field tests
# =====================================================================


class TestVisualFields:
    def test_clinician_creates_and_lists(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/visual-fields",
            headers=CLIN1,
            json={
                "eye": "OD",
                "test_type": "24-2",
                "performed_at": "2026-03-12T09:00:00",
                "result_summary": "MD -3.4 dB (clinical text)",
                "reliability": "good",
                "progression_flag": "stable",
            },
        )
        assert r.status_code == 201
        rl = client.get(
            f"/patients/{p['id']}/glaucoma/visual-fields", headers=CLIN1
        )
        assert rl.json()["total"] == 1

    def test_technician_can_create_vf(self, client):
        p = _create_patient(client, CLIN1)
        r = client.post(
            f"/patients/{p['id']}/glaucoma/visual-fields",
            headers=TECH1,
            json={"eye": "OS", "test_type": "10-2"},
        )
        assert r.status_code == 201

    def test_audit_excludes_result_summary(self, client, test_db):
        p = _create_patient(client, CLIN1)
        client.post(
            f"/patients/{p['id']}/glaucoma/visual-fields",
            headers=CLIN1,
            json={
                "eye": "OD",
                "test_type": "24-2",
                "result_summary": "VERY-SECRET result body",
                "reliability": "good",
            },
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT detail FROM security_audit_events "
                "WHERE event_type = 'glaucoma_visual_field_created'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for (detail,) in rows:
            assert "VERY-SECRET" not in (detail or "")


# =====================================================================
# Auth required everywhere
# =====================================================================


class TestAuthRequired:
    def test_list_requires_auth(self, client):
        r = client.get("/patients/1/retina")
        assert r.status_code == 401
