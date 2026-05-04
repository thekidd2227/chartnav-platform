"""Tests for the retinal diagram persistence shell.

This is the persistence-and-identity foundation only — no drawing
canvas, no AI proposal pipeline, no apply/reject workflow. Those tests
belong to a later PR.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# --- helpers -----------------------------------------------------------


def _patient_id_for(seeded_ids: dict, identifier: str) -> int:
    """Resolve numeric patient_id by patient_identifier in the seed."""
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id FROM patients WHERE patient_identifier = :pid",
        {"pid": identifier},
    )
    assert row, f"seed missing patient {identifier!r}"
    return int(row["id"])


def _create(client, headers, patient_id: int, **payload):
    body = {
        "title": "Right eye exam",
        "findings_text": "IOP 18 mmHg OU. Disc margins sharp.",
        "drawing_json": {"strokes": [{"path": "M0 0 L10 10"}]},
    }
    body.update(payload)
    return client.post(
        f"/patients/{patient_id}/eye-diagrams",
        headers=headers,
        json=body,
    )


# --- happy path --------------------------------------------------------


class TestCreateAndList:
    def test_create_returns_unsigned_artifact(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _create(client, CLIN1, pid)
        assert r.status_code == 201, r.json()
        body = r.json()
        assert body["artifact_type"] == "retinal_diagram"
        assert body["version_number"] == 1
        assert body["parent_artifact_id"] is None
        assert body["is_signed"] is False
        assert body["signed_at"] is None
        assert body["title"] == "Right eye exam"
        # drawing_json must come back as a dict, not a string
        assert isinstance(body["drawing_json"], dict)
        assert body["drawing_json"]["strokes"][0]["path"] == "M0 0 L10 10"

    def test_list_returns_artifacts_for_patient(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        _create(client, CLIN1, pid, title="A")
        _create(client, CLIN1, pid, title="B")
        r = client.get(f"/patients/{pid}/eye-diagrams", headers=CLIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        # most recent first
        titles = [item["title"] for item in body["items"]]
        assert "A" in titles and "B" in titles

    def test_get_detail(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.get(
            f"/patients/{pid}/eye-diagrams/{new['id']}", headers=CLIN1
        )
        assert r.status_code == 200
        assert r.json()["id"] == new["id"]


# --- update / sign / fork ---------------------------------------------


class TestUpdateSignFork:
    def test_unsigned_update_in_place(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}",
            headers=CLIN1,
            json={"findings_text": "IOP rechecked at 17 mmHg OU."},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == new["id"]
        assert body["version_number"] == 1
        assert body["parent_artifact_id"] is None
        assert body["findings_text"] == "IOP rechecked at 17 mmHg OU."

    def test_sign_marks_signed(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign",
            headers=CLIN1,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["is_signed"] is True
        assert body["signed_at"] is not None
        assert body["signed_by_user_id"] is not None

    def test_repeat_sign_returns_409(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )
        r = client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "artifact_already_signed"

    def test_signed_edit_without_fork_returns_409(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )
        r = client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}",
            headers=CLIN1,
            json={"findings_text": "post-sign edit"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "artifact_signed_immutable"

    def test_signed_edit_with_fork_creates_new_version(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )
        r = client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}?fork=true",
            headers=CLIN1,
            json={"findings_text": "amended after sign"},
        )
        assert r.status_code == 200
        forked = r.json()
        assert forked["id"] != new["id"]
        assert forked["parent_artifact_id"] == new["id"]
        assert forked["version_number"] == 2
        assert forked["is_signed"] is False
        assert forked["findings_text"] == "amended after sign"

    def test_fork_inherits_unspecified_fields_from_parent(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(
            client,
            CLIN1,
            pid,
            title="Parent title",
            findings_text="Parent findings",
            drawing_json={"strokes": [{"path": "parent"}]},
        ).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )
        # fork with only findings_text patched
        r = client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}?fork=true",
            headers=CLIN1,
            json={"findings_text": "Amendment only"},
        )
        forked = r.json()
        assert forked["title"] == "Parent title"
        assert forked["drawing_json"]["strokes"][0]["path"] == "parent"
        assert forked["findings_text"] == "Amendment only"


# --- response shape: drawing_json must be an object -------------------


class TestResponseShape:
    def test_drawing_json_returned_as_object_not_string(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        payload = {"strokes": [{"path": "M1 1"}], "od_os": "OD", "n": 5}
        r = _create(client, CLIN1, pid, drawing_json=payload)
        body = r.json()
        assert isinstance(body["drawing_json"], dict)
        assert body["drawing_json"] == payload

    def test_list_drawing_json_returned_as_object(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        _create(client, CLIN1, pid)
        r = client.get(f"/patients/{pid}/eye-diagrams", headers=CLIN1)
        body = r.json()
        assert isinstance(body["items"][0]["drawing_json"], dict)


# --- org isolation ----------------------------------------------------


class TestOrgIsolation:
    def test_patient_in_other_org_returns_404(self, client, seeded_ids):
        # PT-1001 lives in demo-eye-clinic. ADMIN2 is in northside-retina.
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = client.get(f"/patients/{pid}/eye-diagrams", headers=ADMIN2)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_artifact_visible_only_to_own_org(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        # Org B admin tries to fetch — must 404 (patient lookup blocks first)
        r = client.get(
            f"/patients/{pid}/eye-diagrams/{new['id']}", headers=ADMIN2
        )
        assert r.status_code == 404

    def test_cannot_sign_other_org_artifact(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=ADMIN2
        )
        assert r.status_code == 404


# --- RBAC -------------------------------------------------------------


class TestRBAC:
    def test_reviewer_can_read(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        _create(client, CLIN1, pid)
        r = client.get(f"/patients/{pid}/eye-diagrams", headers=REV1)
        assert r.status_code == 200

    def test_reviewer_cannot_create(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _create(client, REV1, pid)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_reviewer_cannot_update(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}",
            headers=REV1,
            json={"findings_text": "x"},
        )
        assert r.status_code == 403

    def test_reviewer_cannot_sign(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=REV1
        )
        assert r.status_code == 403

    def test_admin_can_create(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _create(client, ADMIN1, pid)
        assert r.status_code == 201

    def test_unauthenticated_blocked(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = client.get(f"/patients/{pid}/eye-diagrams")
        assert r.status_code == 401


# --- 404s -------------------------------------------------------------


class TestNotFound:
    def test_unknown_artifact_404(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = client.get(f"/patients/{pid}/eye-diagrams/999999", headers=CLIN1)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "artifact_not_found"

    def test_unknown_encounter_on_create_404(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _create(client, CLIN1, pid, encounter_id=999999)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "encounter_not_found"


# --- audit redaction --------------------------------------------------


class TestAuditDoesNotLogClinicalContent:
    """Audit metadata only — no findings_text, no drawing_json."""

    def test_audit_excludes_findings_and_drawing(self, client, seeded_ids):
        from app.db import fetch_all
        pid = _patient_id_for(seeded_ids, "PT-1001")

        secret_findings = "PRIVATE_FINDINGS_TOKEN_QQQ"
        secret_drawing = {"strokes": [{"path": "PRIVATE_DRAWING_TOKEN_RRR"}]}

        new = _create(
            client,
            CLIN1,
            pid,
            findings_text=secret_findings,
            drawing_json=secret_drawing,
        ).json()
        client.patch(
            f"/patients/{pid}/eye-diagrams/{new['id']}",
            headers=CLIN1,
            json={"findings_text": secret_findings + "_v2"},
        )
        client.post(
            f"/patients/{pid}/eye-diagrams/{new['id']}/sign", headers=CLIN1
        )

        rows = fetch_all(
            "SELECT event_type, detail FROM security_audit_events "
            "WHERE event_type LIKE 'eye_diagram_%' ORDER BY id"
        )
        assert any(r["event_type"] == "eye_diagram_created" for r in rows)
        assert any(r["event_type"] == "eye_diagram_updated" for r in rows)
        assert any(r["event_type"] == "eye_diagram_signed" for r in rows)
        for r in rows:
            d = r["detail"] or ""
            assert "PRIVATE_FINDINGS_TOKEN_QQQ" not in d
            assert "PRIVATE_DRAWING_TOKEN_RRR" not in d
