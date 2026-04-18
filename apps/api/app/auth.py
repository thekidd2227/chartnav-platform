"""Dev auth + org-scoping helpers for ChartNav.

This is an *intentionally small* dev auth layer. It is not production
identity — there are no passwords, tokens, signatures, or sessions. The
contract is:

  1. Clients send `X-User-Email: <email>` on every protected request.
  2. The server looks the user up in the `users` table.
  3. The caller's `organization_id` is derived from that row — never from
     the request body or query string.
  4. Endpoints that accept `organization_id` from the client must check
     it matches the caller's org; mismatches are rejected with 403.

This gives us a real enforcement point to layer real identity (JWT, SSO,
etc.) on top of later without re-plumbing the route code.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

DB_PATH = Path(__file__).resolve().parents[1] / "chartnav.db"


@dataclass(frozen=True)
class Caller:
    user_id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_id: int


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def require_caller(
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
) -> Caller:
    """FastAPI dependency — resolves the caller or raises 401."""
    if not x_user_email or not x_user_email.strip():
        raise HTTPException(status_code=401, detail="missing_auth_header")

    email = x_user_email.strip()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, email, full_name, role, organization_id "
            "FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="unknown_user")

    return Caller(
        user_id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        organization_id=row["organization_id"],
    )


def ensure_same_org(caller: Caller, target_organization_id: int) -> None:
    """Raise 403 if the caller tries to act across orgs."""
    if caller.organization_id != target_organization_id:
        raise HTTPException(status_code=403, detail="cross_org_access_forbidden")
