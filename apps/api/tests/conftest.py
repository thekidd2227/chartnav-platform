"""Pytest fixtures — isolated SQLite + seeded tenants per test.

Strategy:
  1. Per test, write a fresh SQLite file in a temp dir.
  2. Set `DATABASE_URL` to point at it BEFORE importing any `app.*`
     module, so `app.config.settings.database_url` picks it up.
  3. Migrate that DB with alembic, seed it, then import the FastAPI app
     for a `TestClient`.

Env-based wiring (rather than monkey-patching module attrs) works
uniformly for both SQLite and Postgres and matches how the app reads
config in production.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))


def _reload_app_modules() -> None:
    """Drop cached `app.*` modules so they re-read the current env."""
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "chartnav.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("CHARTNAV_AUTH_MODE", "header")
    # Any JWT env left over from the host should not bleed into tests.
    for k in ("CHARTNAV_JWT_ISSUER", "CHARTNAV_JWT_AUDIENCE", "CHARTNAV_JWT_JWKS_URL"):
        monkeypatch.delenv(k, raising=False)

    # Alembic migrate against the temp DB.
    subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(API_DIR / "alembic.ini"),
            "-x", f"sqlalchemy.url={url}",
            "upgrade", "head",
        ],
        check=True, cwd=API_DIR,
    )

    # Seed using the app's own seed script (it reads DATABASE_URL).
    _reload_app_modules()
    import scripts_seed  # noqa: F401  (imports app.db which reads env)
    importlib.reload(scripts_seed)
    scripts_seed.main()

    return db_path


@pytest.fixture()
def client(test_db):
    _reload_app_modules()  # ensure app.main re-reads env
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


@pytest.fixture()
def seeded_ids(test_db) -> dict:
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    try:
        orgs = {
            r["slug"]: r["id"]
            for r in conn.execute("SELECT id, slug FROM organizations").fetchall()
        }
        locs_by_org = {
            r["organization_id"]: r["id"]
            for r in conn.execute("SELECT id, organization_id FROM locations").fetchall()
        }
        encs = {
            r["patient_identifier"]: (r["id"], r["organization_id"], r["status"])
            for r in conn.execute(
                "SELECT id, organization_id, patient_identifier, status FROM encounters"
            ).fetchall()
        }
    finally:
        conn.close()
    return {"orgs": orgs, "locs_by_org": locs_by_org, "encs": encs}
