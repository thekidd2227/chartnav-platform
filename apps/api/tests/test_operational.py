"""Operational hardening tests: request IDs, CORS, rate limiting,
and the security audit trail."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN1, CLIN1, REV1

API_DIR = Path(__file__).resolve().parents[1]


def _fresh_client_with_env(monkeypatch, tmp_path, **env) -> TestClient:
    """Boot the app with custom env (CORS / rate limit / etc.)."""
    db_path = tmp_path / "chartnav.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", "header")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(API_DIR / "alembic.ini"),
            "-x", f"sqlalchemy.url={url}",
            "upgrade", "head",
        ],
        check=True, cwd=API_DIR,
    )
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import scripts_seed
    importlib.reload(scripts_seed)
    scripts_seed.main()
    from app.main import app
    return TestClient(app)


# ---- Request ID ---------------------------------------------------------

def test_request_id_header_roundtrips(client):
    r = client.get("/health", headers={"X-Request-ID": "rid-fixed-42"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "rid-fixed-42"


def test_request_id_generated_when_missing(client):
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid and len(rid) >= 16


def test_request_id_on_error_response(client):
    # 401 path must still carry a request id
    r = client.get("/me")
    assert r.status_code == 401
    assert "X-Request-ID" in r.headers


# ---- Audit trail --------------------------------------------------------

def _recent_audit(test_db) -> list[dict]:
    from app.audit import query_recent
    return query_recent(limit=20)


def test_audit_written_on_missing_auth_header(client, test_db):
    r = client.get("/encounters")
    assert r.status_code == 401
    rows = _recent_audit(test_db)
    events = [e for e in rows if e["event_type"] == "missing_auth_header"]
    assert events, rows
    last = events[0]
    assert last["path"] == "/encounters"
    assert last["method"] == "GET"
    assert last["error_code"] == "missing_auth_header"
    assert last["request_id"]


def test_audit_written_on_unknown_user(client, test_db):
    r = client.get("/me", headers={"X-User-Email": "ghost@nowhere.test"})
    assert r.status_code == 401
    events = [
        e for e in _recent_audit(test_db) if e["event_type"] == "unknown_user"
    ]
    assert events


def test_audit_written_on_cross_org_forbidden(client, test_db, seeded_ids):
    # org1 admin with a ?organization_id=2 lens → 403 cross_org_access_forbidden
    r = client.get("/encounters?organization_id=2", headers=ADMIN1)
    assert r.status_code == 403
    events = [
        e for e in _recent_audit(test_db)
        if e["event_type"] == "cross_org_access_forbidden"
    ]
    assert events
    last = events[0]
    assert last["actor_email"] == "admin@chartnav.local"
    assert last["organization_id"] == 1


def test_audit_written_on_role_forbidden(client, test_db, seeded_ids):
    # reviewer tries to create an encounter → 403 role_cannot_create_encounter
    body = {
        "organization_id": seeded_ids["orgs"]["demo-eye-clinic"],
        "location_id": seeded_ids["locs_by_org"][1],
        "patient_identifier": "PT-AUDIT",
        "provider_name": "Dr. Audit",
    }
    r = client.post("/encounters", headers=REV1, json=body)
    assert r.status_code == 403
    events = [
        e for e in _recent_audit(test_db)
        if e["event_type"] == "role_cannot_create_encounter"
    ]
    assert events
    assert events[0]["actor_email"] == "rev@chartnav.local"


def test_audit_not_written_on_success(client, test_db):
    r = client.get("/me", headers=ADMIN1)
    assert r.status_code == 200
    before = len(_recent_audit(test_db))
    # repeat a success — count should be stable
    r2 = client.get("/encounters", headers=ADMIN1)
    assert r2.status_code == 200
    assert len(_recent_audit(test_db)) == before


# ---- Rate limiting ------------------------------------------------------

def test_rate_limit_returns_429(monkeypatch, tmp_path):
    client = _fresh_client_with_env(
        monkeypatch, tmp_path,
        CHARTNAV_RATE_LIMIT_PER_MINUTE="3",
    )
    # 3 allowed, 4th limited. Use /me so we exercise an authed path.
    for _ in range(3):
        r = client.get("/me", headers=ADMIN1)
        assert r.status_code == 200
    r4 = client.get("/me", headers=ADMIN1)
    assert r4.status_code == 429
    body = r4.json()
    assert body["detail"]["error_code"] == "rate_limited"


def test_rate_limit_disabled_when_zero(monkeypatch, tmp_path):
    client = _fresh_client_with_env(
        monkeypatch, tmp_path,
        CHARTNAV_RATE_LIMIT_PER_MINUTE="0",
    )
    for _ in range(10):
        r = client.get("/me", headers=ADMIN1)
        assert r.status_code == 200


# ---- CORS ---------------------------------------------------------------

def test_cors_allowed_origin(monkeypatch, tmp_path):
    client = _fresh_client_with_env(
        monkeypatch, tmp_path,
        CHARTNAV_CORS_ALLOW_ORIGINS="https://app.example.com",
    )
    r = client.options(
        "/me",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-User-Email",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://app.example.com"


def test_cors_disallowed_origin(monkeypatch, tmp_path):
    client = _fresh_client_with_env(
        monkeypatch, tmp_path,
        CHARTNAV_CORS_ALLOW_ORIGINS="https://app.example.com",
    )
    r = client.options(
        "/me",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-User-Email",
        },
    )
    # Starlette rejects the preflight outright.
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers
