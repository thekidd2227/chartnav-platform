"""Admin CRUD + DB role constraint + event validation + pagination."""

from __future__ import annotations

import sqlite3

import pytest

from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# ---- DB-level role constraint --------------------------------------------

def test_db_role_check_rejects_unknown_role(test_db):
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (organization_id, email, full_name, role) "
            "VALUES (1, 'evil@x.test', 'evil', 'root')"
        )
        conn.commit()
    conn.close()


# ---- Admin: create user ---------------------------------------------------

def test_admin_can_create_user(client, seeded_ids):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "newc@chartnav.local", "full_name": "New C", "role": "clinician"},
    )
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["email"] == "newc@chartnav.local"
    assert body["role"] == "clinician"
    assert body["organization_id"] == seeded_ids["orgs"]["demo-eye-clinic"]
    assert body["is_active"] == 1 or body["is_active"] is True


def test_non_admin_cannot_create_user(client):
    for hdr in (CLIN1, REV1):
        r = client.post(
            "/users",
            headers=hdr,
            json={"email": "nope@x.test", "full_name": "x", "role": "clinician"},
        )
        assert r.status_code == 403, (hdr, r.json())
        assert r.json()["detail"]["error_code"] == "role_admin_required"


def test_admin_rejects_unknown_role_at_api(client):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "bad@x.test", "full_name": "x", "role": "root"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_role"


def test_admin_rejects_duplicate_email(client):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "admin@chartnav.local", "full_name": "x", "role": "admin"},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "user_email_taken"


def test_admin_create_user_email_format(client):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "not-an-email", "full_name": "x", "role": "clinician"},
    )
    assert r.status_code == 422  # pydantic validation


# ---- Admin: update user --------------------------------------------------

def test_admin_can_patch_user_role(client):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "tochange@chartnav.local", "full_name": "X", "role": "clinician"},
    )
    user_id = r.json()["id"]
    r2 = client.patch(
        f"/users/{user_id}",
        headers=ADMIN1,
        json={"role": "reviewer", "full_name": "Renamed"},
    )
    assert r2.status_code == 200, r2.json()
    assert r2.json()["role"] == "reviewer"
    assert r2.json()["full_name"] == "Renamed"


def test_admin_cannot_demote_self(client, seeded_ids):
    me = client.get("/me", headers=ADMIN1).json()
    r = client.patch(
        f"/users/{me['user_id']}",
        headers=ADMIN1,
        json={"role": "clinician"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "cannot_demote_self"


def test_admin_cannot_cross_org_mutate_user(client):
    # Find org2 user id by asking org2 admin.
    me2 = client.get("/me", headers=ADMIN2).json()
    other_user_id = me2["user_id"]
    r = client.patch(
        f"/users/{other_user_id}",
        headers=ADMIN1,  # org1 admin touching org2 user
        json={"role": "clinician"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "user_not_found"


# ---- Admin: deactivate user ---------------------------------------------

def test_admin_can_deactivate_user_and_list_omits_it(client):
    # Create a throwaway user, deactivate, then confirm the default list
    # doesn't include them; include_inactive=1 does.
    created = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "bye@chartnav.local", "full_name": "B", "role": "clinician"},
    ).json()
    uid = created["id"]
    r = client.delete(f"/users/{uid}", headers=ADMIN1)
    assert r.status_code == 200
    assert r.json()["is_active"] in (0, False)

    active = client.get("/users", headers=ADMIN1).json()
    assert all(u["id"] != uid for u in active)

    all_including = client.get("/users?include_inactive=1", headers=ADMIN1).json()
    assert any(u["id"] == uid for u in all_including)


def test_admin_cannot_deactivate_self(client):
    me = client.get("/me", headers=ADMIN1).json()
    r = client.delete(f"/users/{me['user_id']}", headers=ADMIN1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "cannot_deactivate_self"


# ---- Admin: locations ----------------------------------------------------

def test_admin_can_create_and_update_location(client, seeded_ids):
    r = client.post(
        "/locations", headers=ADMIN1, json={"name": "Downtown Clinic"}
    )
    assert r.status_code == 201
    loc_id = r.json()["id"]
    assert r.json()["organization_id"] == seeded_ids["orgs"]["demo-eye-clinic"]

    r2 = client.patch(
        f"/locations/{loc_id}",
        headers=ADMIN1,
        json={"name": "Downtown Clinic (renamed)"},
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "Downtown Clinic (renamed)"


def test_admin_cannot_cross_org_mutate_location(client, seeded_ids):
    other_loc_id = seeded_ids["locs_by_org"][seeded_ids["orgs"]["northside-retina"]]
    r = client.patch(
        f"/locations/{other_loc_id}",
        headers=ADMIN1,
        json={"name": "hijacked"},
    )
    assert r.status_code == 404


def test_non_admin_cannot_create_location(client):
    for hdr in (CLIN1, REV1):
        r = client.post("/locations", headers=hdr, json={"name": "x"})
        assert r.status_code == 403


def test_admin_deactivate_location_hides_from_default_list(client):
    created = client.post(
        "/locations", headers=ADMIN1, json={"name": "Temporary"}
    ).json()
    lid = created["id"]
    r = client.delete(f"/locations/{lid}", headers=ADMIN1)
    assert r.status_code == 200
    assert r.json()["is_active"] in (0, False)
    default = client.get("/locations", headers=ADMIN1).json()
    assert all(l["id"] != lid for l in default)
    with_inactive = client.get("/locations?include_inactive=1", headers=ADMIN1).json()
    assert any(l["id"] == lid for l in with_inactive)


# ---- Event validation ----------------------------------------------------

def test_event_type_must_be_in_allowlist(client, seeded_ids):
    enc_id = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc_id}/events",
        headers=ADMIN1,
        json={"event_type": "made_up_thing"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_event_type"


def test_event_data_must_be_object_and_have_required_keys(client, seeded_ids):
    enc_id = seeded_ids["encs"]["PT-1001"][0]

    # manual_note requires {note}
    r = client.post(
        f"/encounters/{enc_id}/events",
        headers=ADMIN1,
        json={"event_type": "manual_note", "event_data": "just a string"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_event_data"

    r2 = client.post(
        f"/encounters/{enc_id}/events",
        headers=ADMIN1,
        json={"event_type": "manual_note", "event_data": {"oops": "nope"}},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "invalid_event_data"

    r3 = client.post(
        f"/encounters/{enc_id}/events",
        headers=ADMIN1,
        json={"event_type": "manual_note", "event_data": {"note": "ok"}},
    )
    assert r3.status_code == 201


# ---- Pagination ----------------------------------------------------------

def test_pagination_headers(client):
    r = client.get("/encounters?limit=1&offset=0", headers=ADMIN1)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.headers.get("X-Total-Count") == "2"
    assert r.headers.get("X-Limit") == "1"
    assert r.headers.get("X-Offset") == "0"


def test_pagination_offset(client):
    r = client.get("/encounters?limit=1&offset=1", headers=ADMIN1)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.headers.get("X-Total-Count") == "2"
    assert r.headers.get("X-Offset") == "1"


def test_pagination_preserves_filters(client, seeded_ids):
    r = client.get(
        "/encounters?status=in_progress&limit=10", headers=ADMIN1
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == seeded_ids["encs"]["PT-1001"][0]
    assert r.headers.get("X-Total-Count") == "1"
