"""Phase 20C — Role-based dashboards tests.

Coverage groups:
  * Auth required (401 on unauthenticated)
  * RBAC: each role can read its own dashboard; admin can read all;
    cross-role reads blocked with 403 ``role_dashboard_forbidden``
  * Org isolation: dashboard counts only include caller-org rows
  * Counts: each lane counts the right Phase 20B queue_types
  * Status: completed/dismissed excluded from "open" counts
  * Overdue: due_at < now counted in admin overdue_queue_items
  * /dashboards/me dispatches by caller.role
  * Compact serializer: payload_json + clinical body NOT in
    dashboard rows
  * Migration roundtrip on extended users.role CHECK constraint
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import (
    ADMIN1,
    ADMIN2,
    CLIN1,
    FRONT1,
    REV1,
    TECH1,
)


# ---------- helpers --------------------------------------------------------


def _create_queue(client, headers, **overrides):
    """Create a work_queue_items row via the Phase 20B endpoint."""
    body = {
        "queue_type": "ready_for_doctor",
        "priority": "normal",
        "status": "open",
        "source": "manual",
    }
    body.update(overrides)
    r = client.post("/work-queues", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ============================================================
# Auth + RBAC
# ============================================================


class TestAuthAndRBAC:
    def test_unauthenticated_returns_401(self, client):
        for path in (
            "/dashboards/front-desk",
            "/dashboards/technician",
            "/dashboards/doctor",
            "/dashboards/reviewer",
            "/dashboards/admin",
            "/dashboards/me",
        ):
            r = client.get(path)
            assert r.status_code == 401, f"{path} did not require auth"

    def test_each_role_reads_own_dashboard(self, client):
        cases = [
            ("/dashboards/front-desk", FRONT1),
            ("/dashboards/technician", TECH1),
            ("/dashboards/doctor", CLIN1),
            ("/dashboards/reviewer", REV1),
            ("/dashboards/admin", ADMIN1),
        ]
        for path, headers in cases:
            r = client.get(path, headers=headers)
            assert r.status_code == 200, f"{path} failed for {headers}: {r.text}"

    def test_clinician_cannot_read_admin_dashboard(self, client):
        r = client.get("/dashboards/admin", headers=CLIN1)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_dashboard_forbidden"

    def test_front_desk_cannot_read_doctor_dashboard(self, client):
        r = client.get("/dashboards/doctor", headers=FRONT1)
        assert r.status_code == 403

    def test_technician_cannot_read_reviewer_dashboard(self, client):
        r = client.get("/dashboards/reviewer", headers=TECH1)
        assert r.status_code == 403

    def test_admin_can_view_any_role_dashboard_via_query(self, client):
        # Admin uses the front-desk endpoint to inspect that role's
        # dashboard. The endpoint defaults role=front_desk; admin
        # passing it explicitly should also work.
        r = client.get(
            "/dashboards/front-desk?role=front_desk", headers=ADMIN1
        )
        assert r.status_code == 200

    def test_admin_can_view_doctor_dashboard(self, client):
        r = client.get("/dashboards/doctor", headers=ADMIN1)
        assert r.status_code == 200

    def test_unknown_role_query_rejected(self, client):
        r = client.get(
            "/dashboards/front-desk?role=patient", headers=ADMIN1
        )
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_dashboard_unknown"

    def test_me_dispatches_by_role(self, client):
        for headers, expected_role in (
            (ADMIN1, "admin"),
            (CLIN1, "clinician"),
            (REV1, "reviewer"),
            (FRONT1, "front_desk"),
            (TECH1, "technician"),
        ):
            r = client.get("/dashboards/me", headers=headers)
            assert r.status_code == 200, headers
            assert r.json()["role"] == expected_role


# ============================================================
# Org isolation
# ============================================================


class TestOrgIsolation:
    def test_dashboard_counts_exclude_other_org(self, client):
        # Create a queue item in org-1.
        _create_queue(client, CLIN1, queue_type="ready_for_doctor")
        # Create one in org-2.
        _create_queue(client, ADMIN2, queue_type="ready_for_doctor")

        r1 = client.get("/dashboards/doctor", headers=CLIN1).json()
        r2 = client.get("/dashboards/doctor", headers=ADMIN2).json()
        # Org-1 sees its own row only.
        assert r1["counts"]["ready_for_doctor_count"] == 1
        # Org-2 sees its own row only.
        assert r2["counts"]["ready_for_doctor_count"] == 1
        assert r1["scope"]["organization_id"] != r2["scope"]["organization_id"]


# ============================================================
# Lane counts — each role sees the right queue_types
# ============================================================


class TestLaneCounts:
    def test_front_desk_lane_counts(self, client):
        _create_queue(client, CLIN1, queue_type="check_in", priority="normal")
        _create_queue(client, CLIN1, queue_type="check_in")
        _create_queue(client, CLIN1, queue_type="checkout")
        _create_queue(client, CLIN1, queue_type="follow_up")
        # Out-of-lane row should NOT show up in front-desk counts.
        _create_queue(client, CLIN1, queue_type="diagram_review")

        r = client.get("/dashboards/front-desk", headers=FRONT1).json()
        assert r["counts"]["check_in_pending_count"] == 2
        assert r["counts"]["checkout_pending_count"] == 1
        assert r["counts"]["follow_up_needed_count"] == 1
        assert r["counts"]["today_queue_count"] == 4

    def test_technician_lane_counts(self, client):
        _create_queue(client, CLIN1, queue_type="technician_workup")
        _create_queue(client, CLIN1, queue_type="va_iop_refraction")
        _create_queue(client, CLIN1, queue_type="dilation")
        _create_queue(client, CLIN1, queue_type="imaging_needed")
        _create_queue(client, CLIN1, queue_type="visual_field_needed")
        _create_queue(client, CLIN1, queue_type="ready_for_doctor")

        r = client.get("/dashboards/technician", headers=TECH1).json()
        assert r["counts"]["workup_pending_count"] == 2  # workup + va_iop
        assert r["counts"]["dilation_pending_count"] == 1
        assert r["counts"]["imaging_needed_count"] == 1
        assert r["counts"]["testing_pending_count"] == 1
        assert r["counts"]["ready_for_doctor_count"] == 1

    def test_doctor_high_priority_counts(self, client):
        _create_queue(client, CLIN1, queue_type="ready_for_doctor",
                      priority="urgent")
        _create_queue(client, CLIN1, queue_type="provider_review",
                      priority="high")
        _create_queue(client, CLIN1, queue_type="provider_review",
                      priority="normal")
        r = client.get("/dashboards/doctor", headers=CLIN1).json()
        # high + urgent = 2 across doctor lane queue_types.
        assert r["counts"]["high_priority_items_count"] == 2

    def test_reviewer_lane_counts(self, client):
        _create_queue(client, CLIN1, queue_type="note_review")
        _create_queue(client, CLIN1, queue_type="diagram_review")
        _create_queue(client, CLIN1, queue_type="ai_draft_review")
        _create_queue(client, CLIN1, queue_type="audit_exception")
        _create_queue(client, CLIN1, queue_type="blocked_review")
        r = client.get("/dashboards/reviewer", headers=REV1).json()
        assert r["counts"]["notes_awaiting_review_count"] == 1
        assert r["counts"]["diagram_proposals_review_count"] == 1
        assert r["counts"]["ai_draft_review_count"] == 1
        assert r["counts"]["audit_exceptions_count"] == 1
        assert r["counts"]["blocked_items_count"] == 1


# ============================================================
# Status: completed / dismissed excluded from open counts
# ============================================================


class TestStatusExclusion:
    def test_completed_items_excluded_from_open_counts(self, client):
        item = _create_queue(client, CLIN1, queue_type="check_in")
        # Mark completed.
        client.patch(
            f"/work-queues/{item['id']}",
            headers=CLIN1,
            json={"status": "completed"},
        )
        r = client.get("/dashboards/front-desk", headers=FRONT1).json()
        assert r["counts"]["check_in_pending_count"] == 0

    def test_dismissed_items_excluded_from_open_counts(self, client):
        item = _create_queue(client, CLIN1, queue_type="follow_up")
        client.patch(
            f"/work-queues/{item['id']}",
            headers=CLIN1,
            json={"status": "dismissed"},
        )
        r = client.get("/dashboards/front-desk", headers=FRONT1).json()
        assert r["counts"]["follow_up_needed_count"] == 0


# ============================================================
# Admin aggregates
# ============================================================


class TestAdminAggregates:
    def test_admin_dashboard_aggregates(self, client):
        _create_queue(client, CLIN1, queue_type="ready_for_doctor",
                      priority="urgent")
        _create_queue(client, CLIN1, queue_type="check_in",
                      priority="normal")
        _create_queue(client, CLIN1, queue_type="note_review",
                      priority="high")

        r = client.get("/dashboards/admin", headers=ADMIN1).json()
        assert r["counts"]["total_open_queue_items"] == 3
        # By status — all 3 are open.
        assert r["work_queue_by_status"].get("open") == 3
        # By priority — 1 urgent, 1 high, 1 normal.
        assert r["work_queue_by_priority"].get("urgent") == 1
        assert r["work_queue_by_priority"].get("high") == 1
        assert r["work_queue_by_priority"].get("normal") == 1
        # By queue type — 3 distinct.
        assert r["work_queue_by_queue_type"].get("ready_for_doctor") == 1
        assert r["work_queue_by_queue_type"].get("check_in") == 1
        assert r["work_queue_by_queue_type"].get("note_review") == 1

    def test_admin_overdue_count(self, client):
        # Past due_at => overdue.
        past = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        _create_queue(
            client, CLIN1,
            queue_type="ready_for_doctor",
            due_at=past,
        )
        # Future due_at => not overdue.
        future = (
            datetime.now(timezone.utc) + timedelta(hours=5)
        ).isoformat()
        _create_queue(
            client, CLIN1,
            queue_type="ready_for_doctor",
            due_at=future,
        )
        r = client.get("/dashboards/admin", headers=ADMIN1).json()
        assert r["counts"]["overdue_queue_items"] == 1


# ============================================================
# PHI / payload_json safety
# ============================================================


class TestPHISafety:
    def test_dashboard_rows_omit_payload_json(self, client):
        sentinel = "SENTINEL-DASHBOARD-PAYLOAD-CLINICAL"
        _create_queue(
            client, CLIN1,
            queue_type="ready_for_doctor",
            payload_json={"clinical_secret": sentinel},
        )
        r = client.get("/dashboards/doctor", headers=CLIN1).json()
        # The compact serializer must NOT include payload_json body
        # in any of the rendered rows, in either lane list.
        body = str(r)
        assert sentinel not in body
        assert "payload_json" not in body

    def test_admin_dashboard_omits_payload_json(self, client):
        sentinel = "SENTINEL-ADMIN-PAYLOAD"
        _create_queue(
            client, CLIN1,
            queue_type="note_review",
            payload_json={"x": sentinel},
        )
        r = client.get("/dashboards/admin", headers=ADMIN1).json()
        assert sentinel not in str(r)


# ============================================================
# Migration roundtrip — users.role enum extended
# ============================================================


class TestRoleEnumExtension:
    def test_seed_includes_front_desk_and_technician(self, client):
        from app.db import fetch_all
        rows = fetch_all(
            "SELECT email, role FROM users "
            "WHERE role IN ('front_desk', 'technician') "
            "ORDER BY email"
        )
        emails = sorted(r["email"] for r in rows)
        # Two orgs × two roles = 4 expected users.
        assert "front@chartnav.local" in emails
        assert "tech@chartnav.local" in emails
        assert "front@northside.local" in emails
        assert "tech@northside.local" in emails

    def test_db_check_rejects_unknown_role(self, client):
        # Direct DB insert with a role NOT in the new enum should
        # fail. We use raw SQL because /users isn't an exposed
        # write surface for this role-enforcement test.
        from sqlalchemy import text
        from app.db import transaction
        try:
            with transaction() as conn:
                conn.execute(
                    text(
                        "INSERT INTO users "
                        "(organization_id, email, full_name, role, is_active) "
                        "VALUES (1, 'x@bad.local', 'X', 'patient', 1)"
                    )
                )
        except Exception as e:
            assert "ck_users_role_allowed" in str(e) or "CHECK" in str(
                e
            ).upper()
            return
        assert False, "expected CHECK constraint to reject 'patient'"
