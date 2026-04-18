from fastapi import APIRouter
import sqlite3
from pathlib import Path

router = APIRouter()

DB_PATH = Path(__file__).resolve().parents[2] / "chartnav.db"


def fetch_all(query: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "chartnav-api", "version": "0.1.0"}


@router.get("/organizations")
def list_organizations() -> list[dict]:
    return fetch_all(
        "SELECT id, name, slug, created_at FROM organizations ORDER BY id"
    )


@router.get("/locations")
def list_locations() -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, name, created_at FROM locations ORDER BY id"
    )


@router.get("/users")
def list_users() -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, email, full_name, role, created_at FROM users ORDER BY id"
    )
