"""Pytest fixtures — isolated SQLite + seeded tenants per test run.

We build a fresh SQLite file in a temp dir, run the same Alembic
migrations against it, and point `app.auth.DB_PATH` and
`app.api.routes.DB_PATH` at it. Then we run the normal seed so tests
get the two-tenant / three-role world the dev runs.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


API_DIR = Path(__file__).resolve().parents[1]
# Make `import app...` resolve against apps/api regardless of cwd.
sys.path.insert(0, str(API_DIR))


@pytest.fixture()
def test_db(tmp_path) -> Path:
    """Fresh migrated + seeded SQLite file per test, so tests do not
    leak writes into each other."""
    db_path = tmp_path / "chartnav.db"

    # Run alembic against the temp DB by overriding the URL via env + -x
    env = os.environ.copy()
    env["SQLALCHEMY_URL"] = f"sqlite:///{db_path}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(API_DIR / "alembic.ini"),
            "-x",
            f"sqlalchemy.url=sqlite:///{db_path}",
            "upgrade",
            "head",
        ],
        check=True,
        cwd=API_DIR,
        env=env,
    )

    # Point the app modules at the temp DB BEFORE importing seeding/app
    from app import auth as auth_mod
    from app.api import routes as routes_mod

    auth_mod.DB_PATH = db_path
    routes_mod.DB_PATH = db_path

    # Seed by running the project's seed script but with its DB_PATH rebound.
    import scripts_seed

    scripts_seed.DB_PATH = db_path
    scripts_seed.main()

    return db_path


@pytest.fixture()
def client(test_db) -> TestClient:
    from app.main import app

    return TestClient(app)


# --- Convenience header builders -----------------------------------------

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


@pytest.fixture()
def seeded_ids(test_db) -> dict:
    """IDs of seeded rows so tests don't hardcode integers."""
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    try:
        orgs = {
            r["slug"]: r["id"]
            for r in conn.execute("SELECT id, slug FROM organizations").fetchall()
        }
        locs_by_org = {}
        for r in conn.execute("SELECT id, organization_id FROM locations").fetchall():
            locs_by_org[r["organization_id"]] = r["id"]
        encs_by_patient = {
            r["patient_identifier"]: (r["id"], r["organization_id"], r["status"])
            for r in conn.execute(
                "SELECT id, organization_id, patient_identifier, status FROM encounters"
            ).fetchall()
        }
    finally:
        conn.close()
    return {"orgs": orgs, "locs_by_org": locs_by_org, "encs": encs_by_patient}
