"""Operator control plane: org settings + audit log read."""

from __future__ import annotations

from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# ---- /organization ------------------------------------------------------

def test_any_authed_role_can_read_org(client):
    for hdr in (ADMIN1, CLIN1, REV1):
        r = client.get("/organization", headers=hdr)
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "demo-eye-clinic"
        assert body["id"] == 1


def test_unauth_cannot_read_org(client):
    r = client.get("/organization")
    assert r.status_code == 401


def test_admin_can_patch_org_name(client):
    r = client.patch(
        "/organization", headers=ADMIN1, json={"name": "Demo Eye Clinic Renamed"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Demo Eye Clinic Renamed"

    # Subsequent GET reflects it.
    assert client.get("/organization", headers=ADMIN1).json()["name"] == (
        "Demo Eye Clinic Renamed"
    )


def test_admin_can_patch_settings_json(client):
    payload = {"settings": {"timezone": "America/New_York", "brand_color": "#0B6E79"}}
    r = client.patch("/organization", headers=ADMIN1, json=payload)
    assert r.status_code == 200
    assert r.json()["settings"] == payload["settings"]


def test_settings_must_be_object(client):
    r = client.patch(
        "/organization", headers=ADMIN1, json={"settings": "not an object"}
    )
    assert r.status_code == 422  # pydantic rejects non-dict


def test_settings_size_limit(client):
    big = {"k": "x" * 20_000}
    r = client.patch("/organization", headers=ADMIN1, json={"settings": big})
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "settings_too_large"


def test_non_admin_cannot_patch_org(client):
    for hdr in (CLIN1, REV1):
        r = client.patch("/organization", headers=hdr, json={"name": "x"})
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_admin_required"


def test_org_scope_isolation_for_patch(client):
    """Org1 admin's PATCH cannot affect org2 — the route always scopes
    to caller.organization_id, so a mutation by admin1 only ever touches
    org1, and admin2's GET sees its own org unchanged."""
    before = client.get("/organization", headers=ADMIN2).json()
    client.patch("/organization", headers=ADMIN1, json={"name": "Org1 Renamed"})
    after = client.get("/organization", headers=ADMIN2).json()
    assert before == after


# ---- /security-audit-events --------------------------------------------

def _generate_denials(client):
    # Create some variety in the audit log.
    client.get("/me")  # 401 missing_auth_header
    client.get("/me", headers={"X-User-Email": "ghost@nowhere.test"})  # 401 unknown_user
    client.get("/encounters?organization_id=2", headers=ADMIN1)  # 403 cross_org_access_forbidden
    # reviewer trying to create an encounter → 403 role_cannot_create_encounter
    client.post(
        "/encounters",
        headers=REV1,
        json={
            "organization_id": 1, "location_id": 1,
            "patient_identifier": "PT-DENY", "provider_name": "Dr. X",
        },
    )


def test_admin_can_read_audit_log(client):
    _generate_denials(client)
    r = client.get("/security-audit-events", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected some audit rows"
    assert rows[0]["id"] >= rows[-1]["id"], "should be newest-first"
    # X-Total-Count header present
    assert r.headers.get("X-Total-Count")


def test_non_admin_cannot_read_audit_log(client):
    for hdr in (CLIN1, REV1):
        r = client.get("/security-audit-events", headers=hdr)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_admin_required"


def test_audit_filter_by_event_type(client):
    _generate_denials(client)
    r = client.get(
        "/security-audit-events?event_type=cross_org_access_forbidden",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows
    assert all(row["event_type"] == "cross_org_access_forbidden" for row in rows)


def test_audit_filter_by_actor_email(client):
    _generate_denials(client)
    r = client.get(
        "/security-audit-events?actor_email=rev@chartnav.local",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows
    assert all(row["actor_email"] == "rev@chartnav.local" for row in rows)


def test_audit_pagination(client):
    _generate_denials(client)
    _generate_denials(client)
    page1 = client.get(
        "/security-audit-events?limit=2&offset=0", headers=ADMIN1
    )
    assert page1.status_code == 200
    assert len(page1.json()) == 2
    assert page1.headers.get("X-Limit") == "2"
    assert page1.headers.get("X-Offset") == "0"

    page2 = client.get(
        "/security-audit-events?limit=2&offset=2", headers=ADMIN1
    )
    assert page2.status_code == 200
    assert len(page2.json()) == 2
    # Different rows across pages.
    ids1 = {r["id"] for r in page1.json()}
    ids2 = {r["id"] for r in page2.json()}
    assert ids1.isdisjoint(ids2)


def test_audit_org_scoping(client):
    """Admin1 must NOT see rows tagged with org2 (cross-org denial
    against an org2 target from an org2 actor would live there).
    Rows with organization_id IS NULL (pre-auth failures) are
    intentionally visible to every admin."""
    # org1 actor generating an org1-scoped denial
    client.get("/encounters?organization_id=2", headers=ADMIN1)  # actor=org1
    # org2 actor generating a denial
    client.get("/encounters?organization_id=1", headers=ADMIN2)  # actor=org2

    r = client.get("/security-audit-events", headers=ADMIN1)
    assert r.status_code == 200
    for row in r.json():
        org = row["organization_id"]
        assert org in (None, 1), row


def test_audit_q_filter(client):
    _generate_denials(client)
    r = client.get(
        "/security-audit-events?q=/encounters", headers=ADMIN1
    )
    assert r.status_code == 200
    rows = r.json()
    # Every row must contain /encounters in path or detail.
    for row in rows:
        assert "/encounters" in (row.get("path") or "") or "/encounters" in (row.get("detail") or "")


# ---- User lifecycle: invited_at --------------------------------------

def test_create_user_sets_invited_at(client):
    r = client.post(
        "/users",
        headers=ADMIN1,
        json={"email": "invitee@chartnav.local", "full_name": "I", "role": "clinician"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["invited_at"] is not None


def test_existing_seeded_users_have_no_invited_at(client):
    users = client.get("/users", headers=ADMIN1).json()
    seeded = [u for u in users if u["email"] == "admin@chartnav.local"]
    assert seeded
    assert seeded[0].get("invited_at") is None
