"""Phase 22 — Multi-clinic / multi-provider scaling tests.

Coverage groups:
  * Provider-location assignments — admin CRUD, non-admin blocked,
    duplicate behavior, cross-org provider/location blocked.
  * Location rooms — admin CRUD, invalid room_type rejected,
    non-admin blocked, cross-org location blocked.
  * Provider schedule blocks — admin CRUD, invalid block_type
    rejected, invalid time range rejected, invalid capacity
    rejected, filters by provider/location/block_type/date,
    cross-org blocked.
  * Clinic operating hours — admin CRUD (upsert), invalid
    day_of_week rejected, invalid time range rejected, cross-org
    location blocked.
  * Dashboard summaries — location dashboard, provider dashboard,
    admin multi-clinic summary; non-admin blocked from admin
    summary; cross-org excluded; no PHI in payload.
  * Audit — metadata-only.
  * Auth — 401 on unauthenticated.
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


def _provider_ids(test_db) -> dict:
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, organization_id, display_name FROM providers"
        ).fetchall()
    finally:
        conn.close()
    return {r["display_name"]: (r["id"], r["organization_id"]) for r in rows}


# =====================================================================
# Provider-location assignments
# =====================================================================


class TestAssignments:
    def test_admin_creates_lists_patches(self, client, test_db, seeded_ids):
        org1_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        providers = _provider_ids(test_db)
        pid, _ = providers["Dr. Carter"]

        r = client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={
                "provider_id": pid,
                "location_id": org1_loc,
                "is_primary": True,
            },
        )
        assert r.status_code == 201, r.text
        assignment = r.json()
        assert assignment["provider_id"] == pid
        assert assignment["location_id"] == org1_loc
        # SQLite returns booleans as 0/1 integers; Postgres returns
        # native bool. Accept either.
        assert bool(assignment["is_primary"]) is True
        assert bool(assignment["is_active"]) is True

        # Duplicate is idempotent — returns the existing row.
        r2 = client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid, "location_id": org1_loc},
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == assignment["id"]

        # List
        rl = client.get("/provider-location-assignments", headers=ADMIN1)
        assert rl.status_code == 200
        assert rl.json()["total"] >= 1

        # Patch
        rp = client.patch(
            f"/provider-location-assignments/{assignment['id']}",
            headers=ADMIN1,
            json={"is_active": False},
        )
        assert rp.status_code == 200
        assert bool(rp.json()["is_active"]) is False

    def test_filters(self, client, test_db, seeded_ids):
        org1_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        providers = _provider_ids(test_db)
        pid_c, _ = providers["Dr. Carter"]
        pid_p, _ = providers["Dr. Patel"]
        client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid_c, "location_id": org1_loc},
        )
        client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid_p, "location_id": org1_loc},
        )
        r = client.get(
            f"/provider-location-assignments?provider_id={pid_c}",
            headers=ADMIN1,
        )
        assert r.status_code == 200
        rows = r.json()["items"]
        assert all(row["provider_id"] == pid_c for row in rows)

    def test_non_admin_cannot_create(self, client, test_db, seeded_ids):
        org1_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        providers = _provider_ids(test_db)
        pid, _ = providers["Dr. Carter"]
        for h in (CLIN1, REV1, TECH1, FRONT1):
            r = client.post(
                "/provider-location-assignments",
                headers=h,
                json={"provider_id": pid, "location_id": org1_loc},
            )
            assert r.status_code == 403

    def test_clinician_can_read(self, client):
        r = client.get("/provider-location-assignments", headers=CLIN1)
        assert r.status_code == 200

    def test_cross_org_provider_returns_404(self, client, test_db, seeded_ids):
        org1_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        providers = _provider_ids(test_db)
        pid_org2, _ = providers["Dr. Ahmed"]  # Org 2's provider
        r = client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid_org2, "location_id": org1_loc},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "provider_not_found"

    def test_cross_org_location_returns_404(self, client, test_db, seeded_ids):
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        providers = _provider_ids(test_db)
        pid_org1, _ = providers["Dr. Carter"]
        r = client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid_org1, "location_id": org2_loc},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "location_not_found"


# =====================================================================
# Location rooms
# =====================================================================


class TestRooms:
    def test_admin_creates_lists_patches(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            f"/locations/{loc}/rooms",
            headers=ADMIN1,
            json={"name": "Lane 1", "room_type": "exam"},
        )
        assert r.status_code == 201
        room = r.json()
        assert room["name"] == "Lane 1"
        assert room["room_type"] == "exam"

        rl = client.get(f"/locations/{loc}/rooms", headers=ADMIN1)
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

        rp = client.patch(
            f"/location-rooms/{room['id']}",
            headers=ADMIN1,
            json={"name": "Lane 1A", "room_type": "imaging"},
        )
        assert rp.status_code == 200
        assert rp.json()["name"] == "Lane 1A"
        assert rp.json()["room_type"] == "imaging"

    def test_invalid_room_type_rejected(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            f"/locations/{loc}/rooms",
            headers=ADMIN1,
            json={"name": "Vault", "room_type": "vault"},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_room_type"

    def test_non_admin_cannot_create(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        for h in (CLIN1, REV1, TECH1, FRONT1):
            r = client.post(
                f"/locations/{loc}/rooms",
                headers=h,
                json={"name": "X", "room_type": "exam"},
            )
            assert r.status_code == 403

    def test_clinician_can_read_rooms(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.get(f"/locations/{loc}/rooms", headers=CLIN1)
        assert r.status_code == 200

    def test_cross_org_location_returns_404(self, client, seeded_ids):
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        r = client.get(f"/locations/{org2_loc}/rooms", headers=ADMIN1)
        assert r.status_code == 404


# =====================================================================
# Provider schedule blocks
# =====================================================================


class TestScheduleBlocks:
    def test_admin_creates_lists_patches(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid,
                "location_id": loc,
                "start_at": "2026-06-01T08:00:00",
                "end_at": "2026-06-01T12:00:00",
                "block_type": "clinic",
                "capacity": 16,
            },
        )
        assert r.status_code == 201, r.text
        block = r.json()
        assert block["block_type"] == "clinic"
        assert block["capacity"] == 16

        rl = client.get("/provider-schedule-blocks", headers=ADMIN1)
        assert rl.status_code == 200
        assert rl.json()["total"] >= 1

        rp = client.patch(
            f"/provider-schedule-blocks/{block['id']}",
            headers=ADMIN1,
            json={"block_type": "injection", "capacity": 24},
        )
        assert rp.status_code == 200
        assert rp.json()["block_type"] == "injection"
        assert rp.json()["capacity"] == 24

    def test_invalid_block_type_rejected(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid,
                "location_id": loc,
                "start_at": "2026-06-01T08:00:00",
                "end_at": "2026-06-01T12:00:00",
                "block_type": "bogus",
            },
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_block_type"

    def test_invalid_time_range_rejected(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid,
                "location_id": loc,
                "start_at": "2026-06-01T12:00:00",
                "end_at": "2026-06-01T08:00:00",
                "block_type": "clinic",
            },
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_time_range"

    def test_invalid_capacity_rejected(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid,
                "location_id": loc,
                "start_at": "2026-06-01T08:00:00",
                "end_at": "2026-06-01T12:00:00",
                "block_type": "clinic",
                "capacity": -5,
            },
        )
        assert r.status_code in (400, 422)

    def test_filters(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid_c, _ = _provider_ids(test_db)["Dr. Carter"]
        client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid_c,
                "location_id": loc,
                "start_at": "2026-06-01T08:00:00",
                "end_at": "2026-06-01T12:00:00",
                "block_type": "clinic",
            },
        )
        client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid_c,
                "location_id": loc,
                "start_at": "2026-06-02T08:00:00",
                "end_at": "2026-06-02T12:00:00",
                "block_type": "surgery",
            },
        )
        r = client.get(
            f"/provider-schedule-blocks?provider_id={pid_c}&block_type=clinic",
            headers=ADMIN1,
        )
        assert r.status_code == 200
        rows = r.json()["items"]
        assert all(row["block_type"] == "clinic" for row in rows)

        r2 = client.get(
            "/provider-schedule-blocks?start_after=2026-06-02T00:00:00",
            headers=ADMIN1,
        )
        assert r2.status_code == 200
        for row in r2.json()["items"]:
            assert row["start_at"] >= "2026-06-02"

    def test_non_admin_cannot_create(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        for h in (CLIN1, REV1, TECH1, FRONT1):
            r = client.post(
                "/provider-schedule-blocks",
                headers=h,
                json={
                    "provider_id": pid,
                    "location_id": loc,
                    "start_at": "2026-06-01T08:00:00",
                    "end_at": "2026-06-01T12:00:00",
                    "block_type": "clinic",
                },
            )
            assert r.status_code == 403

    def test_cross_org_blocked(self, client, test_db, seeded_ids):
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        pid_org1, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.post(
            "/provider-schedule-blocks",
            headers=ADMIN1,
            json={
                "provider_id": pid_org1,
                "location_id": org2_loc,
                "start_at": "2026-06-01T08:00:00",
                "end_at": "2026-06-01T12:00:00",
                "block_type": "clinic",
            },
        )
        assert r.status_code == 404


# =====================================================================
# Clinic operating hours
# =====================================================================


class TestOperatingHours:
    def test_admin_creates_lists_patches(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            "/clinic-operating-hours",
            headers=ADMIN1,
            json={
                "location_id": loc,
                "day_of_week": 1,
                "opens_at": "08:00",
                "closes_at": "17:00",
            },
        )
        assert r.status_code == 201, r.text
        hours = r.json()
        assert hours["day_of_week"] == 1

        # Upsert behavior — same (loc, day) returns existing row.
        r2 = client.post(
            "/clinic-operating-hours",
            headers=ADMIN1,
            json={
                "location_id": loc,
                "day_of_week": 1,
                "opens_at": "09:00",
                "closes_at": "18:00",
            },
        )
        assert r2.status_code == 201
        assert r2.json()["id"] == hours["id"]

        rl = client.get(
            f"/clinic-operating-hours?location_id={loc}", headers=ADMIN1
        )
        assert rl.status_code == 200
        assert rl.json()["total"] == 1

        rp = client.patch(
            f"/clinic-operating-hours/{hours['id']}",
            headers=ADMIN1,
            json={"closes_at": "18:00"},
        )
        assert rp.status_code == 200
        assert rp.json()["closes_at"] == "18:00"

    def test_invalid_day_of_week_rejected(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            "/clinic-operating-hours",
            headers=ADMIN1,
            json={
                "location_id": loc,
                "day_of_week": 9,
                "opens_at": "08:00",
                "closes_at": "17:00",
            },
        )
        # Pydantic's ge=0,le=6 returns 422; we accept either.
        assert r.status_code in (400, 422)

    def test_invalid_time_range_rejected(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            "/clinic-operating-hours",
            headers=ADMIN1,
            json={
                "location_id": loc,
                "day_of_week": 2,
                "opens_at": "18:00",
                "closes_at": "08:00",
            },
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_time_range"

    def test_cross_org_location_blocked(self, client, seeded_ids):
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        r = client.post(
            "/clinic-operating-hours",
            headers=ADMIN1,
            json={"location_id": org2_loc, "day_of_week": 1, "is_closed": True},
        )
        assert r.status_code == 404

    def test_non_admin_cannot_write(self, client, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        r = client.post(
            "/clinic-operating-hours",
            headers=CLIN1,
            json={"location_id": loc, "day_of_week": 1, "is_closed": True},
        )
        assert r.status_code == 403


# =====================================================================
# Dashboard summaries
# =====================================================================


class TestDashboards:
    def test_location_dashboard(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        client.post(
            f"/locations/{loc}/rooms",
            headers=ADMIN1,
            json={"name": "Lane 1", "room_type": "exam"},
        )
        client.post(
            "/provider-location-assignments",
            headers=ADMIN1,
            json={"provider_id": pid, "location_id": loc},
        )
        r = client.get(f"/locations/{loc}/dashboard", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["location_id"] == loc
        c = body["counts"]
        assert c["provider_count"] >= 1
        assert c["room_count"] >= 1
        for key in (
            "open_queue_items",
            "ready_for_workup",
            "imaging_needed",
            "ready_for_doctor",
            "review_needed",
            "active_schedule_blocks_today",
        ):
            assert key in c
        # No clinical text in body.
        assert "notes" not in body
        assert "payload_json" not in body

    def test_provider_dashboard(self, client, test_db):
        pid, _ = _provider_ids(test_db)["Dr. Carter"]
        r = client.get(f"/providers/{pid}/dashboard", headers=CLIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["provider_id"] == pid
        for key in (
            "assigned_queue_items",
            "ready_for_doctor",
            "imaging_review",
            "signoff_needed",
            "review_needed",
            "schedule_blocks_today",
            "locations_today",
        ):
            assert key in body["counts"]

    def test_admin_multi_clinic_summary(self, client, seeded_ids):
        r = client.get("/admin/multi-clinic-summary", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["organization_id"] == seeded_ids["orgs"]["demo-eye-clinic"]
        assert isinstance(body["locations"], list)
        assert isinstance(body["providers"], list)
        assert isinstance(body["queue_by_status"], dict)
        assert isinstance(body["queue_by_queue_type"], dict)
        assert isinstance(body["queue_by_source"], dict)
        assert isinstance(body["open_queue_by_assigned_role"], dict)
        assert isinstance(body["open_queue_by_assigned_user"], dict)
        assert isinstance(body["stale_queue_by_assigned_role"], dict)
        assert body["stale_queue_items"] >= 0
        assert body["due_today_queue_items"] >= 0
        # No PHI text.
        assert "payload_json" not in body

    def test_non_admin_blocked_from_admin_summary(self, client):
        for h in (CLIN1, REV1, TECH1, FRONT1):
            r = client.get("/admin/multi-clinic-summary", headers=h)
            assert r.status_code == 403

    def test_cross_org_location_dashboard_returns_404(self, client, seeded_ids):
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        r = client.get(f"/locations/{org2_loc}/dashboard", headers=ADMIN1)
        assert r.status_code == 404

    def test_cross_org_provider_dashboard_returns_404(self, client, test_db):
        pid_org2, _ = _provider_ids(test_db)["Dr. Ahmed"]
        r = client.get(f"/providers/{pid_org2}/dashboard", headers=ADMIN1)
        assert r.status_code == 404

    def test_admin_summary_org_isolated(self, client, seeded_ids):
        r2 = client.get("/admin/multi-clinic-summary", headers=ADMIN2)
        assert r2.status_code == 200
        body = r2.json()
        assert body["organization_id"] == seeded_ids["orgs"]["northside-retina"]
        # The summary lists Org-2 locations only.
        org2_loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
        location_ids = [loc["location_id"] for loc in body["locations"]]
        assert location_ids == [org2_loc]

    def test_admin_summary_phase_24c_wedge_visibility(self, test_db_with_wedge):
        """Phase 24C admin ops rollup is asserted only on the wedge-enabled fixture."""
        from fastapi.testclient import TestClient

        from tests.conftest import _reload_app_modules

        _reload_app_modules()
        from app.main import app

        client = TestClient(app)
        r = client.get("/admin/multi-clinic-summary", headers=ADMIN1)
        assert r.status_code == 200
        body = r.json()
        assert body["queue_by_source"].get("phase_24b_wedge", 0) >= 7
        assert body["queue_by_source"].get("phase_24c_glaucoma_wedge", 0) >= 2
        assert body["open_queue_by_assigned_user"].get("tech@chartnav.local", 0) >= 1
        assert body["open_queue_by_assigned_user"].get("clin@chartnav.local", 0) >= 1
        assert body["stale_queue_items"] >= 1
        assert body["due_today_queue_items"] >= 0
        assert body["stale_queue_by_assigned_role"].get("technician", 0) >= 1


# =====================================================================
# Audit + Auth
# =====================================================================


class TestAuditAndAuth:
    def test_create_emits_metadata_only_audit(self, client, test_db, seeded_ids):
        loc = seeded_ids["locs_by_org"][seeded_ids["orgs"]["demo-eye-clinic"]]
        client.post(
            f"/locations/{loc}/rooms",
            headers=ADMIN1,
            json={"name": "VERY-SECRET-ROOM-NAME", "room_type": "exam"},
        )
        conn = sqlite3.connect(test_db)
        try:
            rows = conn.execute(
                "SELECT detail FROM security_audit_events "
                "WHERE event_type = 'location_room_created'"
            ).fetchall()
        finally:
            conn.close()
        assert rows
        for (detail,) in rows:
            assert "VERY-SECRET-ROOM-NAME" not in (detail or "")

    def test_auth_required(self, client):
        for path in (
            "/provider-location-assignments",
            "/clinic-operating-hours",
            "/provider-schedule-blocks",
            "/admin/multi-clinic-summary",
        ):
            r = client.get(path)
            assert r.status_code == 401
