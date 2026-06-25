"""Production configuration startup-refusal tests.

`app.config._load()` reads the environment fresh on each call, so we can drive
it directly under monkeypatched env without reloading the whole app.
"""
from __future__ import annotations

import pytest

from app import config

BEARER_ENV = {
    "CHARTNAV_AUTH_MODE": "bearer",
    "CHARTNAV_JWT_ISSUER": "https://idp.example.com/",
    "CHARTNAV_JWT_AUDIENCE": "chartnav-api",
    "CHARTNAV_JWT_JWKS_URL": "https://idp.example.com/.well-known/jwks.json",
}
PG_URL = "postgresql+psycopg://chartnav:secret@db.internal:5432/chartnav"


def _set(monkeypatch, **env):
    # Clear the knobs we care about, then apply the test's values.
    for k in (
        "CHARTNAV_ENV", "CHARTNAV_AUTH_MODE", "DATABASE_URL",
        "CHARTNAV_CORS_ALLOW_ORIGINS", "CHARTNAV_JWT_ISSUER",
        "CHARTNAV_JWT_AUDIENCE", "CHARTNAV_JWT_JWKS_URL",
        "CHARTNAV_PLATFORM_MODE", "CHARTNAV_INTEGRATION_ADAPTER",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


def test_prod_refuses_header_auth(monkeypatch):
    _set(monkeypatch, CHARTNAV_ENV="prod", CHARTNAV_AUTH_MODE="header",
         DATABASE_URL=PG_URL)
    with pytest.raises(RuntimeError, match="bearer.*production|production"):
        config._load()


def test_prod_refuses_sqlite(monkeypatch):
    _set(monkeypatch, CHARTNAV_ENV="prod", DATABASE_URL="sqlite:///./chartnav.db",
         **BEARER_ENV)
    with pytest.raises(RuntimeError, match="SQLite|PostgreSQL"):
        config._load()


def test_prod_refuses_wildcard_cors(monkeypatch):
    _set(monkeypatch, CHARTNAV_ENV="prod", DATABASE_URL=PG_URL,
         CHARTNAV_CORS_ALLOW_ORIGINS="*", **BEARER_ENV)
    with pytest.raises(RuntimeError, match="CORS|\\*"):
        config._load()


def test_prod_accepts_hardened_config(monkeypatch):
    _set(monkeypatch, CHARTNAV_ENV="prod", DATABASE_URL=PG_URL,
         CHARTNAV_CORS_ALLOW_ORIGINS="https://app.chartnavmd.com", **BEARER_ENV)
    s = config._load()
    assert s.env == "prod"
    assert s.auth_mode == "bearer"
    assert s.database_url.startswith("postgresql")


def test_dev_still_allows_header_and_sqlite(monkeypatch):
    _set(monkeypatch, CHARTNAV_ENV="dev")  # defaults: header + sqlite
    s = config._load()
    assert s.env == "dev"
    assert s.auth_mode == "header"
