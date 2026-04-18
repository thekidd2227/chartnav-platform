from tests.conftest import ADMIN1, ADMIN2, CLIN1


def test_list_orgs_scoped(client):
    r = client.get("/organizations", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["slug"] == "demo-eye-clinic"

    r2 = client.get("/organizations", headers=ADMIN2)
    assert r2.json()[0]["slug"] == "northside-retina"


def test_list_orgs_requires_auth(client):
    r = client.get("/organizations")
    assert r.status_code == 401


def test_list_locations_scoped(client, seeded_ids):
    r = client.get("/locations", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert all(row["organization_id"] == seeded_ids["orgs"]["demo-eye-clinic"] for row in rows)
    assert len(rows) == 1


def test_list_users_scoped(client):
    r = client.get("/users", headers=ADMIN1)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    # Org1 has three users, none from northside should leak.
    assert emails == {"admin@chartnav.local", "clin@chartnav.local", "rev@chartnav.local"}


def test_encounters_scoped_by_caller_org(client, seeded_ids):
    r1 = client.get("/encounters", headers=ADMIN1)
    ids1 = sorted(e["id"] for e in r1.json())

    r2 = client.get("/encounters", headers=ADMIN2)
    ids2 = sorted(e["id"] for e in r2.json())

    assert set(ids1).isdisjoint(set(ids2))


def test_cross_org_read_returns_404(client, seeded_ids):
    org2_enc_id = seeded_ids["encs"]["PT-2001"][0]
    r = client.get(f"/encounters/{org2_enc_id}", headers=CLIN1)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_cross_org_query_lens_forbidden(client):
    r = client.get("/encounters?organization_id=2", headers=ADMIN1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "cross_org_access_forbidden"


def test_filter_within_org(client, seeded_ids):
    r = client.get("/encounters?status=in_progress", headers=ADMIN1)
    assert r.status_code == 200
    ids = [e["id"] for e in r.json()]
    assert ids == [seeded_ids["encs"]["PT-1001"][0]]

    # And cannot see org2 matches under same filter
    r2 = client.get("/encounters?status=scheduled", headers=ADMIN1)
    scheduled_ids = [e["id"] for e in r2.json()]
    assert seeded_ids["encs"]["PT-2001"][0] not in scheduled_ids
