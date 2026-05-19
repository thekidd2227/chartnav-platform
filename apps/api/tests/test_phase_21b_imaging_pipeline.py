"""Phase 21B — Imaging pipeline foundation tests.

Coverage groups:
  * Imaging studies: list/create/get/patch + RBAC + isolation + audit safety.
  * Review: only admin/clinician can mark reviewed.
  * Imaging files (metadata only): list/create + binary-payload rejection.
  * Imaging measurements: list/create + RBAC.
  * Validation: invalid modality / eye / status / file_kind / source rejected.
  * Cross-org no-existence-leak: foreign patient or study returns 404.
  * Audit metadata-only: notes / storage_uri / file_name / value never
    serialized into audit detail.
  * Auth required everywhere.
"""

from __future__ import annotations

import sqlite3

from tests.conftest import (
    ADMIN1,
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
        "patient_identifier": "PT-PHASE21B",
        "first_name": "Imaging",
        "last_name": "PipelineTest",
        "date_of_birth": "1957-08-21",
        "sex_at_birth": "female",
    }
    body.update(overrides)
    r = client.post("/patients", headers=headers, json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _create_study(client, headers, patient_id, **overrides) -> dict:
    body = {
        "modality": "oct_macula",
        "eye": "OD",
        "status": "uploaded",
        "captured_at": "2026-04-10T09:00:00",
        "notes": "uneventful capture (clinical text)",
    }
    body.update(overrides)
    return client.post(
        f"/patients/{patient_id}/imaging-studies",
        headers=headers,
        json=body,
    )


# =====================================================================
# Imaging studies
# =====================================================================


class TestImagingStudies:
    def test_clinician_creates_lists_gets_patches(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_study(client, CLIN1, p["id"])
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["modality"] == "oct_macula"
        assert body["eye"] == "OD"
        assert body["status"] == "uploaded"
        study_id = body["id"]

        rl = client.get(
            f"/patients/{p['id']}/imaging-studies", headers=CLIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1
        assert rl.json()["items"][0]["id"] == study_id

        rg = client.get(f"/imaging-studies/{study_id}", headers=CLIN1)
        assert rg.status_code == 200
        assert rg.json()["id"] == study_id

        rp = client.patch(
            f"/imaging-studies/{study_id}",
            headers=CLIN1,
            json={"status": "ready_for_review"},
        )
        assert rp.status_code == 200
        assert rp.json()["status"] == "ready_for_review"

    def test_technician_can_create_study(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_study(
            client, TECH1, p["id"],
            modality="fundus_photo", status="pending_upload"
        )
        assert r.status_code == 201

    def test_admin_can_create_and_review_study(self, client):
        p = _create_patient(client, ADMIN1)
        cr = _create_study(client, ADMIN1, p["id"])
        sid = cr.json()["id"]
        rr = client.patch(
            f"/imaging-studies/{sid}/review", headers=ADMIN1, json={}
        )
        assert rr.status_code == 200
        assert rr.json()["status"] == "reviewed"
        assert rr.json()["reviewed_by_user_id"] is not None
        assert rr.json()["reviewed_at"] is not None

    def test_reviewer_read_only_cannot_create_or_review(self, client):
        p = _create_patient(client, CLIN1)
        cr = _create_study(client, CLIN1, p["id"])
        sid = cr.json()["id"]

        rl = client.get(
            f"/patients/{p['id']}/imaging-studies", headers=REV1
        )
        assert rl.status_code == 200

        ccr = _create_study(client, REV1, p["id"])
        assert ccr.status_code == 403

        rev = client.patch(
            f"/imaging-studies/{sid}/review", headers=REV1, json={}
        )
        assert rev.status_code == 403

    def test_technician_cannot_mark_reviewed(self, client):
        p = _create_patient(client, CLIN1)
        cr = _create_study(client, CLIN1, p["id"])
        sid = cr.json()["id"]

        rev = client.patch(
            f"/imaging-studies/{sid}/review", headers=TECH1, json={}
        )
        assert rev.status_code == 403
        assert rev.json()["detail"]["error_code"] == "imaging_role_forbidden"

    def test_front_desk_has_no_access(self, client):
        p = _create_patient(client, CLIN1)
        rl = client.get(
            f"/patients/{p['id']}/imaging-studies", headers=FRONT1
        )
        assert rl.status_code == 403
        cr = _create_study(client, FRONT1, p["id"])
        assert cr.status_code == 403

    def test_invalid_modality_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_study(
            client, CLIN1, p["id"], modality="fancy_new_scan"
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_modality"

    def test_invalid_eye_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_study(client, CLIN1, p["id"], eye="XX")
        assert r.status_code in (400, 422)

    def test_invalid_status_rejected(self, client):
        p = _create_patient(client, CLIN1)
        r = _create_study(client, CLIN1, p["id"], status="signed_off")
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_status"

    def test_cross_org_patient_returns_404(self, client):
        p = _create_patient(client, CLIN1)
        rl = client.get(
            f"/patients/{p['id']}/imaging-studies", headers=CLIN2
        )
        assert rl.status_code == 404

    def test_cross_org_study_returns_404(self, client):
        p = _create_patient(client, CLIN1)
        cr = _create_study(client, CLIN1, p["id"])
        sid = cr.json()["id"]

        rg = client.get(f"/imaging-studies/{sid}", headers=CLIN2)
        assert rg.status_code == 404
        assert (
            rg.json()["detail"]["error_code"] == "imaging_study_not_found"
        )

        rp = client.patch(
            f"/imaging-studies/{sid}",
            headers=CLIN2,
            json={"status": "archived"},
        )
        assert rp.status_code == 404

    def test_audit_excludes_clinical_body(self, client, test_db):
        p = _create_patient(client, CLIN1)
        cr = _create_study(client, CLIN1, p["id"])
        sid = cr.json()["id"]
        client.patch(
            f"/imaging-studies/{sid}",
            headers=CLIN1,
            json={"notes": "SECRET clinical notes about MRI findings"},
        )
        client.patch(
            f"/imaging-studies/{sid}/review",
            headers=CLIN1,
            json={"notes": "SECRET review notes"},
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT event_type, detail FROM security_audit_events "
                "WHERE event_type LIKE 'imaging_study_%'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for event_type, detail in rows:
            assert "SECRET" not in (detail or "")
            assert "MRI findings" not in (detail or "")
            assert "uneventful capture" not in (detail or "")


# =====================================================================
# Imaging files — METADATA ONLY
# =====================================================================


class TestImagingFiles:
    def test_clinician_creates_and_lists(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=CLIN1,
            json={
                "file_kind": "image",
                "file_name": "od_macula_20260410.dcm",
                "storage_uri": "s3://practice-bucket/imaging/sid-100/od_macula.dcm",
                "content_type": "application/dicom",
                "size_bytes": 8421376,
                "checksum_sha256": "deadbeef" * 8,
            },
        )
        assert r.status_code == 201
        rl = client.get(
            f"/imaging-studies/{sid}/files", headers=CLIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

    def test_technician_can_create_file_metadata(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, TECH1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=TECH1,
            json={"file_kind": "image", "file_name": "scan.jpg"},
        )
        assert r.status_code == 201

    def test_reviewer_cannot_create_file(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=REV1,
            json={"file_kind": "image", "file_name": "scan.jpg"},
        )
        assert r.status_code == 403

    def test_invalid_file_kind_rejected(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=CLIN1,
            json={"file_kind": "binary_blob", "file_name": "scan.bin"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_file_kind"

    def test_binary_data_url_rejected(self, client):
        # Belt-and-suspenders: a request that tries to smuggle a
        # base64 binary into the metadata storage_uri must be
        # rejected by Pydantic validation.
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=CLIN1,
            json={
                "file_kind": "image",
                "file_name": "scan.png",
                "storage_uri": "data:image/png;base64,iVBORw0KGgo=",
            },
        )
        assert r.status_code in (400, 422)

    def test_audit_excludes_storage_uri_and_file_name(self, client, test_db):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        client.post(
            f"/imaging-studies/{sid}/files",
            headers=CLIN1,
            json={
                "file_kind": "image",
                "file_name": "VERY-SECRET-FILENAME.dcm",
                "storage_uri": "s3://VERY-SECRET-BUCKET/path.dcm",
            },
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT detail FROM security_audit_events "
                "WHERE event_type = 'imaging_file_metadata_created'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for (detail,) in rows:
            assert "VERY-SECRET-FILENAME" not in (detail or "")
            assert "VERY-SECRET-BUCKET" not in (detail or "")

    def test_cross_org_study_returns_404_on_file_create(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/files",
            headers=CLIN2,
            json={"file_kind": "image", "file_name": "scan.jpg"},
        )
        assert r.status_code == 404


# =====================================================================
# Imaging measurements
# =====================================================================


class TestImagingMeasurements:
    def test_clinician_creates_and_lists(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=CLIN1,
            json={
                "measurement_type": "central_macular_thickness",
                "eye": "OD",
                "value": "240",
                "unit": "microns",
                "source": "manual",
            },
        )
        assert r.status_code == 201
        rl = client.get(
            f"/imaging-studies/{sid}/measurements", headers=CLIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

    def test_technician_can_create_measurement(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, TECH1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=TECH1,
            json={
                "measurement_type": "cup_to_disc_ratio",
                "eye": "OS",
                "value": "0.6",
                "unit": "ratio",
                "source": "manual",
            },
        )
        assert r.status_code == 201

    def test_reviewer_cannot_create_measurement(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=REV1,
            json={
                "measurement_type": "rnfl_thickness_avg",
                "eye": "OD",
                "value": "92",
                "unit": "microns",
                "source": "manual",
            },
        )
        assert r.status_code == 403

    def test_invalid_source_rejected(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=CLIN1,
            json={
                "measurement_type": "central_macular_thickness",
                "eye": "OD",
                "value": "240",
                "unit": "microns",
                "source": "auto_inferred",
            },
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_source"

    def test_invalid_eye_rejected(self, client):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        r = client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=CLIN1,
            json={
                "measurement_type": "central_macular_thickness",
                "eye": "ZZ",
                "value": "240",
                "unit": "microns",
                "source": "manual",
            },
        )
        assert r.status_code in (400, 422)

    def test_audit_excludes_measurement_value(self, client, test_db):
        p = _create_patient(client, CLIN1)
        sid = _create_study(client, CLIN1, p["id"]).json()["id"]
        client.post(
            f"/imaging-studies/{sid}/measurements",
            headers=CLIN1,
            json={
                "measurement_type": "rnfl_thickness_avg",
                "eye": "OD",
                "value": "VERY-SECRET-VALUE-12345",
                "unit": "microns",
                "source": "manual",
            },
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT detail FROM security_audit_events "
                "WHERE event_type = 'imaging_measurement_created'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for (detail,) in rows:
            assert "VERY-SECRET-VALUE" not in (detail or "")
            assert "12345" not in (detail or "")


# =====================================================================
# Auth required
# =====================================================================


class TestAuthRequired:
    def test_list_studies_requires_auth(self, client):
        r = client.get("/patients/1/imaging-studies")
        assert r.status_code == 401

    def test_get_study_requires_auth(self, client):
        r = client.get("/imaging-studies/1")
        assert r.status_code == 401

    def test_review_requires_auth(self, client):
        r = client.patch("/imaging-studies/1/review", json={})
        assert r.status_code == 401
