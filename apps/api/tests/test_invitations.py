"""Invitation workflow, audit export, event hardening, bulk users."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# ---- /users/{id}/invite -------------------------------------------------

def _seed_fresh_user(client) -> dict:
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "newby@chartnav.local", "full_name": "N", "role": "clinician"},
    )
    assert r.status_code == 201, r.json()
    return r.json()


def test_admin_can_invite_user_and_raw_token_is_returned_once(client):
    u = _seed_fresh_user(client)
    r = client.post(f"/users/{u['id']}/invite", headers=ADMIN1)
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["user_id"] == u["id"]
    assert body["invitation_token"] and len(body["invitation_token"]) >= 32
    assert body["ttl_days"] == 7
    # The raw token isn't echoed back on subsequent user reads.
    users = client.get("/users", headers=ADMIN1).json()
    row = next(r for r in users if r["id"] == u["id"])
    assert "invitation_token" not in row
    assert "invitation_token_hash" not in row


def test_non_admin_cannot_invite(client):
    u = _seed_fresh_user(client)
    for hdr in (CLIN1, REV1):
        r = client.post(f"/users/{u['id']}/invite", headers=hdr)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_admin_required"


def test_admin_cannot_invite_cross_org_user(client):
    me2 = client.get("/me", headers=ADMIN2).json()
    r = client.post(f"/users/{me2['user_id']}/invite", headers=ADMIN1)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "user_not_found"


def test_admin_cannot_invite_inactive_user(client):
    u = _seed_fresh_user(client)
    client.delete(f"/users/{u['id']}", headers=ADMIN1)  # soft-delete
    r = client.post(f"/users/{u['id']}/invite", headers=ADMIN1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "user_inactive"


def test_accept_happy_path(client):
    u = _seed_fresh_user(client)
    tok = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    r = client.post("/invites/accept", json={"token": tok})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["accepted"] is True
    assert body["user_id"] == u["id"]
    assert body["organization_id"] == u["organization_id"]


def test_accept_invalid_token(client):
    r = client.post("/invites/accept", json={"token": "not-a-real-token-xyz-0123"})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_invite"


def test_accept_cannot_be_reused(client):
    u = _seed_fresh_user(client)
    tok = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    r1 = client.post("/invites/accept", json={"token": tok})
    assert r1.status_code == 200
    r2 = client.post("/invites/accept", json={"token": tok})
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "invalid_invite"


def test_accept_expired_token(client, test_db):
    import sqlite3
    u = _seed_fresh_user(client)
    tok = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    # Rewind expiry to the past via direct DB touch (keeps tests hermetic
    # without adding a test-only endpoint).
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conn = sqlite3.connect(test_db)
    conn.execute(
        "UPDATE users SET invitation_expires_at = ? WHERE id = ?", (past, u["id"])
    )
    conn.commit()
    conn.close()
    r = client.post("/invites/accept", json={"token": tok})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invite_expired"


def test_admin_cannot_reinvite_already_accepted(client):
    u = _seed_fresh_user(client)
    tok = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    client.post("/invites/accept", json={"token": tok})
    r = client.post(f"/users/{u['id']}/invite", headers=ADMIN1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "user_already_accepted"


def test_reissuing_invite_revokes_prior_token(client):
    u = _seed_fresh_user(client)
    old = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    new = client.post(f"/users/{u['id']}/invite", headers=ADMIN1).json()["invitation_token"]
    assert old != new
    r = client.post("/invites/accept", json={"token": old})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_invite"
    r2 = client.post("/invites/accept", json={"token": new})
    assert r2.status_code == 200


# ---- Audit CSV export ---------------------------------------------------

def test_audit_export_is_csv_and_admin_only(client):
    # generate some denials
    client.get("/me")
    client.get("/me", headers={"X-User-Email": "ghost@nowhere.test"})

    r = client.get("/security-audit-events/export", headers=ADMIN1)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.text
    # header row + at least one data row
    assert "id,created_at,event_type,error_code" in body
    assert "missing_auth_header" in body


def test_audit_export_respects_filters(client):
    client.get("/me")  # missing_auth_header
    client.get("/me", headers={"X-User-Email": "ghost@nowhere.test"})  # unknown_user

    r = client.get(
        "/security-audit-events/export?event_type=unknown_user",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    body = r.text
    assert "unknown_user" in body
    assert "missing_auth_header" not in body


def test_audit_export_forbidden_to_non_admin(client):
    for hdr in (CLIN1, REV1):
        r = client.get("/security-audit-events/export", headers=hdr)
        assert r.status_code == 403


# ---- Event payload hardening --------------------------------------------

def test_status_changed_rejects_bogus_status_values(client, seeded_ids):
    enc = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc}/events",
        headers=ADMIN1,
        json={
            "event_type": "status_changed",
            "event_data": {"old_status": "bogus", "new_status": "completed"},
        },
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_event_data"


def test_manual_note_rejects_empty_and_non_string(client, seeded_ids):
    enc = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc}/events",
        headers=ADMIN1,
        json={"event_type": "manual_note", "event_data": {"note": ""}},
    )
    assert r.status_code == 400
    r2 = client.post(
        f"/encounters/{enc}/events",
        headers=ADMIN1,
        json={"event_type": "manual_note", "event_data": {"note": 42}},
    )
    assert r2.status_code == 400


def test_note_draft_requested_fields_validated(client, seeded_ids):
    enc = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc}/events",
        headers=ADMIN1,
        json={"event_type": "note_draft_requested", "event_data": {"requested_by": ""}},
    )
    assert r.status_code == 400


# ---- Bulk user import ---------------------------------------------------

def test_bulk_user_import_creates_skips_and_errors(client):
    payload = {
        "users": [
            {"email": "ok1@chartnav.local", "full_name": "OK1", "role": "clinician"},
            {"email": "admin@chartnav.local", "full_name": "dup", "role": "admin"},  # dup
            {"email": "badrole@chartnav.local", "full_name": "x", "role": "superadmin"},  # bad role
            {"email": "ok2@chartnav.local", "full_name": "OK2", "role": "reviewer"},
        ]
    }
    r = client.post("/users/bulk", headers=ADMIN1, json=payload)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["summary"] == {"requested": 4, "created": 2, "skipped": 1, "errors": 1}
    created_emails = [u["email"] for u in body["created"]]
    assert set(created_emails) == {"ok1@chartnav.local", "ok2@chartnav.local"}
    assert body["skipped"][0]["error_code"] == "user_email_taken"
    assert body["errors"][0]["error_code"] == "invalid_role"


def test_bulk_user_non_admin_denied(client):
    for hdr in (CLIN1, REV1):
        r = client.post(
            "/users/bulk",
            headers=hdr,
            json={"users": [{"email": "x@y.test", "full_name": "X", "role": "clinician"}]},
        )
        assert r.status_code == 403


def test_bulk_user_empty_body_rejected(client):
    r = client.post("/users/bulk", headers=ADMIN1, json={"users": []})
    assert r.status_code == 422  # min_length=1 at pydantic layer


def test_bulk_user_is_org_scoped(client):
    # Admin in org1 imports; all created rows belong to org1.
    payload = {
        "users": [
            {"email": "s1@chartnav.local", "full_name": "S1", "role": "clinician"},
            {"email": "s2@chartnav.local", "full_name": "S2", "role": "reviewer"},
        ]
    }
    r = client.post("/users/bulk", headers=ADMIN1, json=payload)
    assert r.status_code == 200
    for u in r.json()["created"]:
        assert u["organization_id"] == 1
