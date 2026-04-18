"""Tests for the production-shaped auth seam."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]


def _fresh_client(monkeypatch, tmp_path, auth_mode: str, **env):
    """Bring up a TestClient with the given auth mode + env, migrated + seeded."""
    db_path = tmp_path / "chartnav.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", auth_mode)
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

    # Drop cached app modules so settings re-read env.
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    import scripts_seed
    importlib.reload(scripts_seed)
    scripts_seed.main()

    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_bearer_mode_requires_jwt_env(monkeypatch, tmp_path):
    # Missing JWT config → app.config refuses to load (import-time).
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", "bearer")
    for k in ("CHARTNAV_JWT_ISSUER", "CHARTNAV_JWT_AUDIENCE", "CHARTNAV_JWT_JWKS_URL"):
        monkeypatch.delenv(k, raising=False)

    with pytest.raises(RuntimeError) as e:
        import app.config  # noqa: F401

    msg = str(e.value)
    assert "CHARTNAV_JWT_ISSUER" in msg
    assert "CHARTNAV_JWT_AUDIENCE" in msg
    assert "CHARTNAV_JWT_JWKS_URL" in msg


def test_bearer_mode_refuses_to_serve_traffic(monkeypatch, tmp_path):
    client = _fresh_client(
        monkeypatch, tmp_path, "bearer",
        CHARTNAV_JWT_ISSUER="https://example.com/",
        CHARTNAV_JWT_AUDIENCE="chartnav-api",
        CHARTNAV_JWT_JWKS_URL="https://example.com/.well-known/jwks.json",
    )

    # No Authorization header → 401 missing
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "missing_auth_header"

    # With a bearer token → 501 (not implemented)
    r2 = client.get("/me", headers={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9..."})
    assert r2.status_code == 501
    assert r2.json()["detail"]["error_code"] == "auth_bearer_not_implemented"


def test_header_mode_unchanged_contract(monkeypatch, tmp_path):
    client = _fresh_client(monkeypatch, tmp_path, "header")
    r = client.get("/me", headers={"X-User-Email": "admin@chartnav.local"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
