"""Phase 24B — Morgan Lee retina follow-up wedge tests.

Coverage:
  * Seed presence: demo-eye-clinic + Morgan Lee + Dr. Carter + 5
    role identities + retina encounter + 7 queue items in lane
    sequence + retina tracking row + OCT macula + fundus photo
    imaging studies + imaging file metadata + internal follow-up
    action item.
  * Role dashboards reflect the wedge across front desk,
    technician, doctor, reviewer, and admin.
  * Org isolation: Org 2 (northside-retina) never sees Morgan
    Lee's wedge.
  * Claim safety: no forbidden text in any wedge row.
"""

from __future__ import annotations

import sqlite3

import pytest

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, FRONT1, REV1, TECH1


@pytest.fixture()
def test_db(test_db_with_wedge):
    """Phase 24B tests require the wedge; override the conftest default."""
    return test_db_with_wedge


# Forbidden positive-claim phrases that must never appear in seeded
# wedge text (queue payloads, retina assessment, imaging notes,
# action-item titles).
_FORBIDDEN_PHRASES = [
    "autonomous diagnosis",
    "autonomous interpretation",
    "auto-interpret oct",
    "auto-grade dr",
    "auto-determine cup-to-disc",
    "auto-select iol",
    "auto-recommend anti-vegf",
    "automatic charting",
    "automatic orders",
    "automatic referrals",
    "automatic coding",
    "automatic billing",
    "patient messaging",
    "send to patient",
    "submit claim",
    "claims submission",
    "insurance handling",
    "ehr replacement",
    "replace your ehr",
    "hipaa compliant",
    "hipaa-compliant",
    "hipaa certified",
    "hipaa-certified",
    "certified ehr",
    "powered by ibm",
    "powered by watsonx",
    "real phi",
    "real patient",
]


def _scan_for_forbidden(text: str, source: str) -> list[str]:
    """Return a list of forbidden phrases found in the lowered text."""
    if not text:
        return []
    lower = text.lower()
    return [p for p in _FORBIDDEN_PHRASES if p in lower]


def _morgan_lee_ids(test_db) -> dict:
    """Return Morgan Lee + encounter + provider + location ids."""
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    try:
        org = conn.execute(
            "SELECT id FROM organizations WHERE slug = 'demo-eye-clinic'"
        ).fetchone()
        patient = conn.execute(
            "SELECT id FROM patients WHERE patient_identifier = 'PT-1001' "
            "AND organization_id = :org",
            {"org": org["id"]},
        ).fetchone()
        encounter = conn.execute(
            "SELECT id FROM encounters WHERE patient_id = :pid",
            {"pid": patient["id"]},
        ).fetchone()
        provider = conn.execute(
            "SELECT id FROM providers WHERE display_name = 'Dr. Carter' "
            "AND organization_id = :org",
            {"org": org["id"]},
        ).fetchone()
    finally:
        conn.close()
    return {
        "org_id": org["id"],
        "patient_id": patient["id"],
        "encounter_id": encounter["id"],
        "provider_id": provider["id"],
    }


# =====================================================================
# Seed presence
# =====================================================================


class TestSeedPresence:
    def test_morgan_lee_exists(self, test_db):
        ids = _morgan_lee_ids(test_db)
        assert ids["patient_id"]
        assert ids["encounter_id"]
        assert ids["provider_id"]

    def test_seven_queue_items_in_lane_sequence(self, test_db):
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT queue_type, status, assigned_role "
                "FROM work_queue_items WHERE source = 'phase_24b_wedge' "
                "ORDER BY id"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 7
        expected = [
            ("check_in", "front_desk"),
            ("technician_workup", "technician"),
            ("imaging_needed", "technician"),
            ("ready_for_doctor", "clinician"),
            ("documentation", "clinician"),
            ("signoff_needed", "clinician"),
            ("follow_up", "front_desk"),
        ]
        actual = [(r["queue_type"], r["assigned_role"]) for r in rows]
        assert actual == expected
        # All start in "open" status — the demo strips through them
        # one role at a time.
        assert all(r["status"] == "open" for r in rows)

    def test_queue_items_are_assigned_to_dashboard_users(self, test_db):
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            org = conn.execute(
                "SELECT id FROM organizations WHERE slug = 'demo-eye-clinic'"
            ).fetchone()
            users = {
                row["role"]: row["id"]
                for row in conn.execute(
                    "SELECT id, role FROM users WHERE organization_id = :org "
                    "AND role IN ('front_desk', 'technician', 'clinician')",
                    {"org": org["id"]},
                ).fetchall()
            }
            rows = conn.execute(
                "SELECT queue_type, assigned_role, assigned_user_id "
                "FROM work_queue_items WHERE source = 'phase_24b_wedge' "
                "ORDER BY id"
            ).fetchall()
        finally:
            conn.close()

        assert users["front_desk"]
        assert users["technician"]
        assert users["clinician"]
        assert len(rows) == 7
        for row in rows:
            assert row["assigned_user_id"] == users[row["assigned_role"]]

    def test_retina_tracking_row_exists(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM retina_tracking WHERE patient_id = :pid "
                "AND encounter_id = :eid",
                {"pid": ids["patient_id"], "eid": ids["encounter_id"]},
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        r = rows[0]
        assert r["eye"] == "OU"
        assert "Diabetic retinopathy" in r["condition"]
        assert r["review_status"] == "needs_review"
        assert r["follow_up_interval"] == "4 weeks"

    def test_oct_macula_and_fundus_studies_exist(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT modality, eye, status FROM imaging_studies "
                "WHERE patient_id = :pid AND encounter_id = :eid "
                "ORDER BY modality",
                {"pid": ids["patient_id"], "eid": ids["encounter_id"]},
            ).fetchall()
        finally:
            conn.close()
        modalities = {r["modality"] for r in rows}
        assert "oct_macula" in modalities
        assert "fundus_photo" in modalities
        for r in rows:
            assert r["eye"] in {"OD", "OS", "OU", "NA"}
            assert r["status"] == "ready_for_review"

    def test_imaging_files_are_metadata_only(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT f.* FROM imaging_files f "
                "JOIN imaging_studies s ON f.study_id = s.id "
                "WHERE s.patient_id = :pid AND s.encounter_id = :eid",
                {"pid": ids["patient_id"], "eid": ids["encounter_id"]},
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 2
        for r in rows:
            # storage_uri is a placeholder reference — never a
            # data: URL (which Phase 21B rejects).
            assert r["storage_uri"].startswith("placeholder://"), r["storage_uri"]
            assert "demo" in r["file_name"]
            assert r["file_kind"] == "image"

    def test_internal_followup_action_item_exists(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM provider_action_items "
                "WHERE patient_id = :pid AND encounter_id = :eid "
                "AND source_type = 'phase_24b_wedge'",
                {"pid": ids["patient_id"], "eid": ids["encounter_id"]},
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        r = rows[0]
        assert r["action_type"] == "review_retina_followup_window"
        assert r["status"] == "suggested"
        assert "follow-up" in (r["title"] or "").lower()


class TestPhase24CGlaucomaSeed:
    def test_glaucoma_second_specialty_rows_exist(self, test_db):
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            org = conn.execute(
                "SELECT id FROM organizations WHERE slug = 'demo-eye-clinic'"
            ).fetchone()
            patient = conn.execute(
                "SELECT id FROM patients WHERE patient_identifier = 'PT-1002' "
                "AND organization_id = :org",
                {"org": org["id"]},
            ).fetchone()
            encounter = conn.execute(
                "SELECT id FROM encounters WHERE patient_id = :pid",
                {"pid": patient["id"]},
            ).fetchone()
            tracking = conn.execute(
                "SELECT * FROM glaucoma_tracking "
                "WHERE organization_id = :org AND patient_id = :pid "
                "AND encounter_id = :eid",
                {"org": org["id"], "pid": patient["id"], "eid": encounter["id"]},
            ).fetchall()
            iop_rows = conn.execute(
                "SELECT eye, iop_value FROM glaucoma_iop_measurements "
                "WHERE organization_id = :org AND patient_id = :pid "
                "AND encounter_id = :eid ORDER BY eye",
                {"org": org["id"], "pid": patient["id"], "eid": encounter["id"]},
            ).fetchall()
            vf_rows = conn.execute(
                "SELECT eye, test_type FROM glaucoma_visual_field_tests "
                "WHERE organization_id = :org AND patient_id = :pid "
                "AND encounter_id = :eid ORDER BY eye",
                {"org": org["id"], "pid": patient["id"], "eid": encounter["id"]},
            ).fetchall()
        finally:
            conn.close()

        assert len(tracking) == 1
        assert tracking[0]["review_status"] == "needs_review"
        assert len(iop_rows) == 2
        assert [(r["eye"], float(r["iop_value"])) for r in iop_rows] == [("OD", 19.0), ("OS", 18.0)]
        assert len(vf_rows) == 2
        assert {r["eye"] for r in vf_rows} == {"OD", "OS"}

    def test_phase24c_queue_items_are_assigned_and_aged_for_ops_dashboard(self, test_db):
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT w.queue_type, w.priority, w.assigned_role, u.email, "
                "w.due_at, w.source "
                "FROM work_queue_items w "
                "LEFT JOIN users u ON u.id = w.assigned_user_id "
                "WHERE w.source = 'phase_24c_glaucoma_wedge' "
                "ORDER BY w.queue_type"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) == 2
        by_type = {r["queue_type"]: r for r in rows}
        assert by_type["glaucoma_testing_review"]["assigned_role"] == "technician"
        assert by_type["glaucoma_testing_review"]["email"] == "tech@chartnav.local"
        assert by_type["glaucoma_testing_review"]["due_at"] is not None
        assert by_type["glaucoma_provider_review"]["assigned_role"] == "clinician"
        assert by_type["glaucoma_provider_review"]["email"] == "clin@chartnav.local"
        assert by_type["glaucoma_provider_review"]["priority"] == "high"


# =====================================================================
# Role dashboard reflection
# =====================================================================


class TestDashboardReflection:
    def test_front_desk_dashboard_includes_check_in_and_followup(self, client):
        r = client.get("/dashboards/front-desk", headers=FRONT1)
        assert r.status_code == 200
        body = r.json()
        # Morgan Lee's check_in + follow_up queue items both fall
        # under the front-desk lane taxonomy.
        c = body["counts"]
        assert c["today_queue_count"] >= 2  # check_in + follow_up
        assert c["check_in_pending_count"] >= 1
        assert c["follow_up_needed_count"] >= 1
        # No clinical body text in the response.
        body_text = r.text.lower()
        assert "diabetic retinopathy" not in body_text
        assert "anti-vegf" not in body_text

    def test_technician_dashboard_includes_workup_and_imaging(self, client):
        r = client.get("/dashboards/technician", headers=TECH1)
        assert r.status_code == 200
        c = r.json()["counts"]
        # technician_workup + imaging_needed both seeded for Morgan.
        assert c["workup_pending_count"] >= 1
        assert c["imaging_needed_count"] >= 1
        # ready_for_doctor also visible since technician lane shows
        # the handoff target.
        assert c["ready_for_doctor_count"] >= 1

    def test_doctor_dashboard_includes_ready_for_md_and_signoff(self, client):
        r = client.get("/dashboards/doctor", headers=CLIN1)
        assert r.status_code == 200
        c = r.json()["counts"]
        assert c["ready_for_doctor_count"] >= 1
        assert c["notes_ready_for_signoff_count"] >= 1
        # Documentation queue contributes to "documentation in
        # progress" lane.
        assert c["documentation_in_progress_count"] >= 1

    def test_reviewer_dashboard_has_zero_for_wedge_by_default(self, client):
        # The Phase 24B wedge does not seed a note_review item
        # because the provider review flow remains optional. The
        # reviewer dashboard should be queryable and return a
        # well-formed payload.
        r = client.get("/dashboards/reviewer", headers=REV1)
        assert r.status_code == 200
        assert "counts" in r.json()

    def test_admin_summary_includes_morgan_queue_contribution(self, client):
        r = client.get("/dashboards/admin", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        # 7 wedge items are seeded. Open status is "open" for all
        # seven; admin queue-by-status should reflect this.
        assert body["counts"]["total_open_queue_items"] >= 7
        # work_queue_by_role / by_queue_type should be non-empty.
        assert body["work_queue_by_role"]
        assert body["work_queue_by_queue_type"]


# =====================================================================
# Org isolation
# =====================================================================


class TestOrgIsolation:
    def test_org2_dashboards_do_not_see_morgan(self, client):
        r = client.get("/dashboards/admin", headers=ADMIN2)
        assert r.status_code == 200
        body = r.json()
        # Org 2 (northside-retina) has its own seeded data but no
        # Phase 24B wedge.
        assert body["scope"]["organization_id"] != 1
        # The wedge contributes 7 queue items to Org 1 only; Org 2's
        # queue total must be less.
        assert body["counts"]["total_open_queue_items"] < 7

    def test_org2_cannot_read_morgan_retina_tracking(self, client, test_db):
        ids = _morgan_lee_ids(test_db)
        r = client.get(
            f"/patients/{ids['patient_id']}/retina", headers=CLIN2
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_org2_cannot_read_morgan_imaging(self, client, test_db):
        ids = _morgan_lee_ids(test_db)
        r = client.get(
            f"/patients/{ids['patient_id']}/imaging-studies", headers=CLIN2
        )
        assert r.status_code == 404


# =====================================================================
# Claim safety — seed text never contains forbidden positive claims.
# =====================================================================


class TestClaimSafety:
    def test_queue_payload_text_is_safe(self, test_db):
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, payload_json FROM work_queue_items "
                "WHERE source = 'phase_24b_wedge'"
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            hits = _scan_for_forbidden(r["payload_json"] or "", "queue")
            assert not hits, f"queue_item {r['id']} contains forbidden text: {hits}"

    def test_retina_tracking_text_is_safe(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, condition, severity, follow_up_interval, "
                "injection_history_summary, provider_assessment "
                "FROM retina_tracking WHERE patient_id = :pid",
                {"pid": ids["patient_id"]},
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            joined = " ".join(
                (r[col] or "") for col in (
                    "condition",
                    "severity",
                    "follow_up_interval",
                    "injection_history_summary",
                    "provider_assessment",
                )
            )
            hits = _scan_for_forbidden(joined, "retina_tracking")
            assert not hits, f"retina_tracking {r['id']} contains forbidden text: {hits}"

    def test_imaging_notes_text_is_safe(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, notes FROM imaging_studies WHERE patient_id = :pid",
                {"pid": ids["patient_id"]},
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            hits = _scan_for_forbidden(r["notes"] or "", "imaging")
            assert not hits, f"imaging_study {r['id']} contains forbidden text: {hits}"

    def test_action_item_title_is_safe(self, test_db):
        ids = _morgan_lee_ids(test_db)
        conn = sqlite3.connect(test_db)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, title FROM provider_action_items "
                "WHERE patient_id = :pid AND source_type = 'phase_24b_wedge'",
                {"pid": ids["patient_id"]},
            ).fetchall()
        finally:
            conn.close()
        for r in rows:
            hits = _scan_for_forbidden(r["title"] or "", "action_item")
            assert not hits
