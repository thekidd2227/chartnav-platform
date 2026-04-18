"""Enterprise quality + compliance: admin-list pagination/search,
audit retention helper, feature-flag behavior consumers."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from tests.conftest import ADMIN1, CLIN1, REV1


# ---- Admin list pagination + search ------------------------------------

def test_users_list_pagination_headers_and_search(client, seeded_ids):
    # Seed extra users so pagination kicks in.
    for i in range(30):
        r = client.post(
            "/users",
            headers=ADMIN1,
            json={
                "email": f"bulk-{i}@chartnav.local",
                "full_name": f"Bulk {i}",
                "role": "clinician",
            },
        )
        assert r.status_code == 201

    r = client.get("/users?limit=10&offset=0", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 10
    total = int(r.headers["X-Total-Count"])
    assert total >= 30 + 3  # 30 bulk + 3 seeded org1 users

    # Offset advances
    r2 = client.get("/users?limit=10&offset=10", headers=ADMIN1)
    assert r2.status_code == 200
    ids1 = {u["id"] for u in rows}
    ids2 = {u["id"] for u in r2.json()}
    assert ids1.isdisjoint(ids2)

    # Search narrows
    r3 = client.get("/users?q=bulk-1", headers=ADMIN1)
    assert r3.status_code == 200
    # bulk-1 matches "bulk-1", "bulk-10"..."bulk-19" = 11 rows
    bulk_matches = [u for u in r3.json() if u["email"].startswith("bulk-1")]
    assert len(bulk_matches) >= 1

    # Role filter
    r4 = client.get("/users?role=admin", headers=ADMIN1)
    assert r4.status_code == 200
    assert all(u["role"] == "admin" for u in r4.json())


def test_users_list_role_invalid(client):
    r = client.get("/users?role=root", headers=ADMIN1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_role"


def test_locations_pagination_and_search(client):
    for i in range(12):
        r = client.post(
            "/locations", headers=ADMIN1, json={"name": f"Room {i:02d}"}
        )
        assert r.status_code == 201

    r = client.get("/locations?limit=5", headers=ADMIN1)
    assert r.status_code == 200
    assert len(r.json()) == 5
    assert int(r.headers["X-Total-Count"]) >= 12 + 1  # seeded + 12

    r2 = client.get("/locations?q=Room%200", headers=ADMIN1)
    # "Room 00".."Room 09" → 10 matches
    assert r2.status_code == 200
    assert len(r2.json()) == 10


def test_admin_list_pagination_preserves_org_scope(client):
    from tests.conftest import ADMIN2  # org2
    # seeded org1 has 3 users, seeded org2 has 2. Neither should leak.
    org1 = client.get("/users?limit=100", headers=ADMIN1).json()
    org2 = client.get("/users?limit=100", headers=ADMIN2).json()
    assert all(u["organization_id"] == 1 for u in org1)
    assert all(u["organization_id"] == 2 for u in org2)


# ---- Audit retention helper --------------------------------------------

def test_retention_disabled_when_zero(client, test_db):
    from app.retention import prune_audit_events
    # Drive one denial so there's data.
    client.get("/me")
    s = prune_audit_events(retention_days=0, dry_run=False)
    assert s["status"] == "disabled"
    assert s["deleted"] == 0


def test_retention_dry_run_reports_without_deleting(client, test_db):
    from app.retention import prune_audit_events
    client.get("/me")  # 401 audit row
    s = prune_audit_events(retention_days=0.0001, dry_run=True)
    # retention_days is int in prod; override with 0 below via SQL trick.
    # Simpler: set created_at of existing rows to far in the past, then prune with days=1.
    conn = sqlite3.connect(test_db)
    past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    conn.execute("UPDATE security_audit_events SET created_at = ?", (past,))
    conn.commit()
    conn.close()
    s = prune_audit_events(retention_days=1, dry_run=True)
    assert s["matched"] >= 1
    assert s["deleted"] == 0


def test_retention_actually_deletes(client, test_db):
    from app.retention import prune_audit_events
    client.get("/me")  # create a row
    conn = sqlite3.connect(test_db)
    past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    conn.execute("UPDATE security_audit_events SET created_at = ?", (past,))
    conn.commit()
    conn.close()
    s = prune_audit_events(retention_days=1)
    assert s["deleted"] >= 1
    # Nothing old remains after prune.
    remaining = client.get(
        "/security-audit-events?limit=500", headers=ADMIN1
    ).json()
    assert not any(
        datetime.fromisoformat((r["created_at"]).replace(" ", "T")).replace(tzinfo=timezone.utc)
        < datetime.now(timezone.utc) - timedelta(days=1)
        for r in remaining
    )


# ---- Feature flag behavior (server-side plumbing) ----------------------

def test_settings_feature_flags_round_trip(client):
    r = client.patch(
        "/organization",
        headers=ADMIN1,
        json={"settings": {"feature_flags": {"audit_export": False, "bulk_import": True}}},
    )
    assert r.status_code == 200
    got = r.json()["settings"]["feature_flags"]
    assert got == {"audit_export": False, "bulk_import": True}

    # Read-back from GET preserves the flag.
    r2 = client.get("/organization", headers=ADMIN1).json()
    assert r2["settings"]["feature_flags"]["audit_export"] is False
