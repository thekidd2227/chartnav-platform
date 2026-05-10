"""Phase 20B — Structured-data-layer tests.

Coverage groups:
  * patient_segments + memberships (CRUD, RBAC, org isolation, idempotency)
  * patient_tags (CRUD, RBAC, org isolation, idempotency, color)
  * patient_problem_list (CRUD, validation, filters, RBAC, org isolation)
  * clinic_workflow_templates + stages (admin-only CRUD, ordering, conflicts)
  * work_queue_items (CRUD, filters, status auto-stamp, FK org-isolation)
  * role_view_presets (admin-only CRUD, default behavior, role validation)
  * audit metadata-only (no clinical body / no JSON payloads)
  * cross-org no-existence-leak (returns 404 not 403)

The conftest seeds two organizations:
  - chartnav.local         (admin@chartnav.local / clin@chartnav.local /
                            rev@chartnav.local)
  - northside.local        (admin@northside.local / clin@northside.local)

Patient PT-1001 / PT-1002 belong to chartnav.local.
"""

from __future__ import annotations

from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# ---------- helpers --------------------------------------------------------
#
# `app.db` MUST be imported lazily inside the helper bodies. The
# conftest `_reload_app_modules()` fixture drops cached `app.*`
# modules per test, so any module-level `from app.db import …` would
# capture a stale connection from a previous test's database.


def _patient_id(identifier: str, *, org: str = "demo-eye-clinic") -> int:
    """Return the patient.id for ``identifier`` scoped to the given org
    (the seed loads the same identifiers in two orgs, so we must
    disambiguate)."""
    from app.db import fetch_one

    row = fetch_one(
        "SELECT p.id FROM patients p "
        "JOIN organizations o ON o.id = p.organization_id "
        "WHERE o.slug = :org AND p.patient_identifier = :pid",
        {"org": org, "pid": identifier},
    )
    assert row, f"seed missing patient {identifier!r} in org {org!r}"
    return int(row["id"])


def _audit_details_matching(prefix: str) -> str:
    """Return all `security_audit_events.detail` strings concatenated
    for events whose ``event_type`` starts with ``prefix``."""
    from app.db import fetch_all

    rows = fetch_all(
        "SELECT detail FROM security_audit_events "
        "WHERE event_type LIKE :p",
        {"p": f"{prefix}%"},
    )
    return "||".join(r["detail"] or "" for r in rows)


def _create_segment(client, **overrides):
    body = {
        "name": "Diabetic retina followup",
        "description": "Patients with DR/DME monitoring schedule",
        "segment_type": "dynamic",
        "criteria_json": {
            "problem.specialty": "retina",
            "problem.status": "active",
        },
        "is_active": True,
    }
    body.update(overrides)
    return client.post("/segments", json=body, headers=ADMIN1)


# ============================================================
# patient_segments + memberships
# ============================================================


class TestSegments:
    def test_admin_creates_segment(self, client):
        r = _create_segment(client)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Diabetic retina followup"
        assert body["segment_type"] == "dynamic"
        assert body["is_active"] is True
        assert body["criteria_json"]["problem.specialty"] == "retina"

    def test_clinician_cannot_create_segment(self, client):
        r = client.post(
            "/segments",
            headers=CLIN1,
            json={
                "name": "Glaucoma followup",
                "segment_type": "dynamic",
            },
        )
        assert r.status_code == 403
        # require_admin emits "role_admin_required"; the inline
        # _require_write_role emits "role_forbidden". Either is a valid
        # admin-only refusal.
        assert r.json()["detail"]["error_code"] in {
            "role_admin_required",
            "role_forbidden",
        }

    def test_reviewer_cannot_create_segment(self, client):
        r = client.post(
            "/segments",
            headers=REV1,
            json={"name": "Foo", "segment_type": "static"},
        )
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] in {
            "role_admin_required",
            "role_forbidden",
        }

    def test_list_segments_org_scoped(self, client):
        _create_segment(client, name="Seg-A")
        client.post(
            "/segments",
            headers=ADMIN2,
            json={"name": "Seg-B", "segment_type": "static"},
        )
        rows1 = client.get("/segments", headers=ADMIN1).json()
        rows2 = client.get("/segments", headers=ADMIN2).json()
        names1 = {r["name"] for r in rows1}
        names2 = {r["name"] for r in rows2}
        assert "Seg-A" in names1
        assert "Seg-A" not in names2
        assert "Seg-B" in names2
        assert "Seg-B" not in names1

    def test_duplicate_name_in_org_returns_409(self, client):
        _create_segment(client, name="Dup")
        r = _create_segment(client, name="Dup")
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "segment_name_conflict"

    def test_update_segment(self, client):
        seg = _create_segment(client).json()
        r = client.patch(
            f"/segments/{seg['id']}",
            headers=ADMIN1,
            json={"is_active": False, "description": "archived"},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_cross_org_segment_returns_404(self, client):
        seg = _create_segment(client).json()
        r = client.patch(
            f"/segments/{seg['id']}",
            headers=ADMIN2,
            json={"is_active": False},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "segment_not_found"

    def test_membership_lifecycle(self, client):
        seg = _create_segment(client).json()
        pid = _patient_id("PT-1001")
        # add
        r = client.post(
            f"/patients/{pid}/segments",
            headers=CLIN1,
            json={
                "segment_id": seg["id"],
                "source": "manual",
                "reason": "DR/DME",
            },
        )
        assert r.status_code == 201, r.text
        # list
        r2 = client.get(f"/patients/{pid}/segments", headers=CLIN1)
        assert r2.status_code == 200
        memberships = r2.json()
        assert len(memberships) == 1
        # idempotent re-add
        r3 = client.post(
            f"/patients/{pid}/segments",
            headers=CLIN1,
            json={"segment_id": seg["id"], "source": "manual"},
        )
        assert r3.status_code == 201
        assert (
            len(client.get(f"/patients/{pid}/segments", headers=CLIN1).json())
            == 1
        )
        # remove
        r4 = client.delete(
            f"/patients/{pid}/segments/{seg['id']}", headers=CLIN1
        )
        assert r4.status_code == 200
        assert r4.json()["removed"] is True
        # list empty
        assert (
            client.get(f"/patients/{pid}/segments", headers=CLIN1).json() == []
        )

    def test_cross_org_patient_segment_returns_404(self, client):
        seg = _create_segment(client).json()  # in chartnav.local org
        pid = _patient_id("PT-1001")  # also chartnav.local
        # ADMIN2 (northside) attempting to attach a chartnav segment to a
        # chartnav patient — patient_id resolves first → 404 patient_not_found
        r = client.post(
            f"/patients/{pid}/segments",
            headers=ADMIN2,
            json={"segment_id": seg["id"], "source": "manual"},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"


# ============================================================
# patient_tags
# ============================================================


class TestPatientTags:
    def test_add_list_delete(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/tags",
            headers=CLIN1,
            json={"tag": "high-priority", "color": "#dc2626"},
        )
        assert r.status_code == 201, r.text
        tag_id = r.json()["id"]
        assert r.json()["color"] == "#dc2626"
        # list
        r2 = client.get(f"/patients/{pid}/tags", headers=CLIN1)
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        # idempotent re-add
        r3 = client.post(
            f"/patients/{pid}/tags",
            headers=CLIN1,
            json={"tag": "high-priority"},
        )
        assert r3.status_code == 201
        assert r3.json()["id"] == tag_id  # same row
        # delete
        r4 = client.delete(
            f"/patients/{pid}/tags/{tag_id}", headers=CLIN1
        )
        assert r4.status_code == 200

    def test_reviewer_cannot_write_tags(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/tags",
            headers=REV1,
            json={"tag": "rev-attempt"},
        )
        assert r.status_code == 403

    def test_cross_org_patient_tag_404(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/tags",
            headers=ADMIN2,
            json={"tag": "x"},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"


# ============================================================
# patient_problem_list
# ============================================================


class TestProblemList:
    def test_create_list_update(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/problem-list",
            headers=CLIN1,
            json={
                "condition_label": "Dry AMD",
                "condition_code": "H35.31",
                "specialty": "retina",
                "eye": "OD",
                "status": "monitoring",
                "onset_date": "2025-02-01",
            },
        )
        assert r.status_code == 201, r.text
        item_id = r.json()["id"]
        assert r.json()["eye"] == "OD"
        assert r.json()["status"] == "monitoring"

        # list with filter
        r2 = client.get(
            f"/patients/{pid}/problem-list?specialty=retina&status=monitoring",
            headers=CLIN1,
        )
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        # update
        r3 = client.patch(
            f"/patients/{pid}/problem-list/{item_id}",
            headers=CLIN1,
            json={"status": "active", "eye": "OU"},
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "active"
        assert r3.json()["eye"] == "OU"

    def test_invalid_eye_rejected(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/problem-list",
            headers=CLIN1,
            json={
                "condition_label": "X",
                "eye": "BOTH",
                "status": "active",
            },
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_payload"

    def test_invalid_status_rejected(self, client):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/problem-list",
            headers=CLIN1,
            json={"condition_label": "X", "status": "tentative"},
        )
        assert r.status_code == 400

    def test_reviewer_can_read_problem_list(self, client):
        pid = _patient_id("PT-1001")
        client.post(
            f"/patients/{pid}/problem-list",
            headers=CLIN1,
            json={"condition_label": "Dry AMD"},
        )
        r = client.get(f"/patients/{pid}/problem-list", headers=REV1)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_cross_org_problem_list_404(self, client):
        pid = _patient_id("PT-1001")
        r = client.get(
            f"/patients/{pid}/problem-list", headers=ADMIN2
        )
        assert r.status_code == 404


# ============================================================
# clinic_workflow_templates + stages
# ============================================================


class TestWorkflowTemplates:
    def test_admin_create_template_and_stages(self, client):
        r = client.post(
            "/workflow-templates",
            headers=ADMIN1,
            json={
                "name": "Standard ophthalmology workup",
                "specialty": "retina",
                "role_owner": "technician",
                "description": "VA / IOP / refraction / dilation",
            },
        )
        assert r.status_code == 201, r.text
        tmpl_id = r.json()["id"]

        # stages — out of order, list comes back ordered
        client.post(
            f"/workflow-templates/{tmpl_id}/stages",
            headers=ADMIN1,
            json={"name": "Dilation", "stage_order": 4, "role_owner": "technician"},
        )
        client.post(
            f"/workflow-templates/{tmpl_id}/stages",
            headers=ADMIN1,
            json={"name": "VA", "stage_order": 1, "role_owner": "technician"},
        )
        client.post(
            f"/workflow-templates/{tmpl_id}/stages",
            headers=ADMIN1,
            json={"name": "IOP", "stage_order": 2, "role_owner": "technician"},
        )
        r3 = client.get(
            f"/workflow-templates/{tmpl_id}/stages", headers=CLIN1
        )
        assert r3.status_code == 200
        order = [s["stage_order"] for s in r3.json()]
        assert order == [1, 2, 4]

    def test_clinician_cannot_create_template(self, client):
        r = client.post(
            "/workflow-templates",
            headers=CLIN1,
            json={
                "name": "Sneak template",
                "role_owner": "technician",
            },
        )
        assert r.status_code == 403

    def test_invalid_role_owner_rejected(self, client):
        r = client.post(
            "/workflow-templates",
            headers=ADMIN1,
            json={"name": "X", "role_owner": "patient"},
        )
        assert r.status_code == 400

    def test_duplicate_stage_order_returns_409(self, client):
        r = client.post(
            "/workflow-templates",
            headers=ADMIN1,
            json={"name": "Tmpl", "role_owner": "technician"},
        )
        tmpl_id = r.json()["id"]
        client.post(
            f"/workflow-templates/{tmpl_id}/stages",
            headers=ADMIN1,
            json={"name": "S1", "stage_order": 1, "role_owner": "technician"},
        )
        dup = client.post(
            f"/workflow-templates/{tmpl_id}/stages",
            headers=ADMIN1,
            json={"name": "S2", "stage_order": 1, "role_owner": "technician"},
        )
        assert dup.status_code == 409

    def test_cross_org_template_404(self, client):
        r = client.post(
            "/workflow-templates",
            headers=ADMIN1,
            json={"name": "T", "role_owner": "clinician"},
        )
        tmpl_id = r.json()["id"]
        r2 = client.get(
            f"/workflow-templates/{tmpl_id}/stages", headers=ADMIN2
        )
        assert r2.status_code == 404


# ============================================================
# work_queue_items
# ============================================================


class TestWorkQueue:
    def test_create_list_filter(self, client):
        r = client.post(
            "/work-queues",
            headers=CLIN1,
            json={
                "queue_type": "md_ready",
                "priority": "high",
                "status": "open",
                "assigned_role": "clinician",
                "source": "encounter_status_change",
            },
        )
        assert r.status_code == 201, r.text
        item = r.json()
        assert item["priority"] == "high"
        assert item["status"] == "open"

        # filters
        r2 = client.get(
            "/work-queues?status=open&priority=high&queue_type=md_ready",
            headers=CLIN1,
        )
        assert r2.status_code == 200
        assert any(it["id"] == item["id"] for it in r2.json())

    def test_invalid_priority_rejected(self, client):
        r = client.post(
            "/work-queues",
            headers=CLIN1,
            json={
                "queue_type": "md_ready",
                "priority": "critical",  # not in QUEUE_PRIORITIES
            },
        )
        assert r.status_code == 400

    def test_invalid_status_rejected(self, client):
        r = client.post(
            "/work-queues",
            headers=CLIN1,
            json={"queue_type": "x", "status": "weird"},
        )
        assert r.status_code == 400

    def test_completion_auto_stamps_completed_at(self, client):
        r = client.post(
            "/work-queues",
            headers=CLIN1,
            json={"queue_type": "tech_workup"},
        )
        item_id = r.json()["id"]
        assert r.json()["completed_at"] is None
        r2 = client.patch(
            f"/work-queues/{item_id}",
            headers=CLIN1,
            json={"status": "completed"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "completed"
        assert r2.json()["completed_at"] is not None

    def test_cross_org_referenced_resource_404(self, client):
        # A patient that exists in chartnav.local — admin@northside attempts
        # to create a queue item referencing it. patient_not_found 404.
        chartnav_pid = _patient_id("PT-1001")
        r = client.post(
            "/work-queues",
            headers=ADMIN2,
            json={
                "queue_type": "md_ready",
                "patient_id": chartnav_pid,
            },
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_reviewer_cannot_write_queue(self, client):
        r = client.post(
            "/work-queues",
            headers=REV1,
            json={"queue_type": "review_needed"},
        )
        assert r.status_code == 403

    def test_reviewer_can_read_queue(self, client):
        client.post(
            "/work-queues",
            headers=CLIN1,
            json={"queue_type": "note_review"},
        )
        r = client.get("/work-queues", headers=REV1)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ============================================================
# role_view_presets
# ============================================================


class TestRoleViews:
    def test_admin_create_list(self, client):
        r = client.post(
            "/role-views",
            headers=ADMIN1,
            json={
                "role": "clinician",
                "name": "Today's MD-ready",
                "filters_json": {"queue_type": "md_ready"},
                "columns_json": ["patient", "due_at", "priority"],
                "is_default": True,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["is_default"] is True
        assert body["filters_json"] == {"queue_type": "md_ready"}
        assert body["columns_json"] == ["patient", "due_at", "priority"]

    def test_clinician_cannot_create_preset(self, client):
        r = client.post(
            "/role-views",
            headers=CLIN1,
            json={"role": "clinician", "name": "X"},
        )
        assert r.status_code == 403

    def test_invalid_role_rejected(self, client):
        r = client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "patient", "name": "X"},
        )
        assert r.status_code == 400

    def test_default_unsets_siblings(self, client):
        # First default
        a = client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "admin", "name": "A", "is_default": True},
        ).json()
        # Second created with is_default=true should unset A's default
        b = client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "admin", "name": "B", "is_default": True},
        ).json()
        rows = client.get("/role-views?role=admin", headers=ADMIN1).json()
        defaults = {r["id"]: r["is_default"] for r in rows}
        assert defaults[a["id"]] is False
        assert defaults[b["id"]] is True

    def test_cross_org_preset_404(self, client):
        r = client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "clinician", "name": "X"},
        )
        pid = r.json()["id"]
        r2 = client.patch(
            f"/role-views/{pid}",
            headers=ADMIN2,
            json={"name": "Y"},
        )
        assert r2.status_code == 404

    def test_filter_by_role(self, client):
        client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "clinician", "name": "Doc-A"},
        )
        client.post(
            "/role-views",
            headers=ADMIN1,
            json={"role": "reviewer", "name": "Rev-A"},
        )
        rows = client.get(
            "/role-views?role=clinician", headers=ADMIN1
        ).json()
        assert len(rows) == 1
        assert rows[0]["role"] == "clinician"


# ============================================================
# Audit metadata-only contract
# ============================================================


class TestAuditMetadataOnly:
    """The Phase 20B audit detail contract is metadata-only.

    Specifically, the following must NEVER appear in
    security_audit_events.detail rows produced by Phase 20B
    operations:
      - raw criteria_json / payload_json / filters_json /
        columns_json
      - condition_label text from problem_list (clinician-authored
        free-text may shadow PHI)
      - tag text body
      - segment.description / template.description
    """

    def test_segment_audit_omits_criteria_json(self, client):
        _create_segment(
            client,
            criteria_json={
                "secret_clinical_field": "do not log this",
                "another": "should not appear",
            },
        )
        joined = _audit_details_matching("segment_")
        assert "secret_clinical_field" not in joined
        assert "do not log this" not in joined
        # But the metadata IS recorded.
        assert "segment_id=" in joined

    def test_problem_item_audit_omits_condition_label(self, client):
        pid = _patient_id("PT-1001")
        sentinel_label = "PT-SENTINEL-CONDITION-PHI-RISK"
        client.post(
            f"/patients/{pid}/problem-list",
            headers=CLIN1,
            json={
                "condition_label": sentinel_label,
                "specialty": "retina",
                "eye": "OD",
                "status": "active",
            },
        )
        joined = _audit_details_matching("problem_item_")
        assert sentinel_label not in joined
        assert "item_id=" in joined  # metadata IS recorded

    def test_queue_item_audit_omits_payload_json(self, client):
        sentinel = "SENTINEL-QUEUE-PAYLOAD-CLINICAL"
        client.post(
            "/work-queues",
            headers=CLIN1,
            json={
                "queue_type": "imaging_review",
                "payload_json": {"clinical_notes": sentinel},
            },
        )
        joined = _audit_details_matching("queue_item_")
        assert sentinel not in joined
        assert "queue_type=imaging_review" in joined  # metadata IS recorded

    def test_role_view_audit_omits_filters_and_columns(self, client):
        sentinel_filter = "SENTINEL-ROLE-VIEW-FILTER"
        sentinel_column = "SENTINEL-ROLE-VIEW-COLUMN"
        client.post(
            "/role-views",
            headers=ADMIN1,
            json={
                "role": "clinician",
                "name": "audit-test-preset",
                "filters_json": {"x": sentinel_filter},
                "columns_json": [sentinel_column],
            },
        )
        joined = _audit_details_matching("role_view_")
        assert sentinel_filter not in joined
        assert sentinel_column not in joined
        assert "preset_id=" in joined  # metadata IS recorded


# ============================================================
# Auth / unauthenticated requests
# ============================================================


class TestAuthRequired:
    def test_unauthenticated_segments_get(self, client):
        r = client.get("/segments")
        assert r.status_code == 401

    def test_unauthenticated_segments_post(self, client):
        r = client.post(
            "/segments",
            json={"name": "X", "segment_type": "static"},
        )
        assert r.status_code == 401

    def test_unauthenticated_work_queues(self, client):
        r = client.get("/work-queues")
        assert r.status_code == 401
