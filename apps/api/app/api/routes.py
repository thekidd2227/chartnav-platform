from fastapi import APIRouter
import sqlite3
from pathlib import Path

router = APIRouter()

DB_PATH = Path(__file__).resolve().parents[2] / "chartnav.db"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "chartnav-api", "version": "0.1.0"}


@router.get("/organizations")
def list_organizations() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, slug, created_at FROM organizations ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
