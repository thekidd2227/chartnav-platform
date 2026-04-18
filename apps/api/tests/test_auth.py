from tests.conftest import ADMIN1


def test_health_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_me_missing_header(client):
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "missing_auth_header"


def test_me_empty_header(client):
    r = client.get("/me", headers={"X-User-Email": ""})
    assert r.status_code == 401


def test_me_unknown_user(client):
    r = client.get("/me", headers={"X-User-Email": "ghost@nowhere.test"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "unknown_user"


def test_me_admin_org1(client):
    r = client.get("/me", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@chartnav.local"
    assert body["role"] == "admin"
    assert body["organization_id"] == 1
