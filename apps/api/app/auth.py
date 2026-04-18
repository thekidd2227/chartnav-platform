"""Dev auth + org-scoping helpers for ChartNav.

This module owns *authentication* (who is the caller) only.
Authorization (what the caller may do) lives in `app.authz`.

Transport today: `X-User-Email` request header, looked up against the
`users` table. This is a dev/local transport — trivially spoofable — and
is NOT production identity. The production upgrade path is documented
in `docs/build/07-auth-and-scoping.md`; when the transport changes
(JWT/SSO), only this module needs to swap its implementation while
every route and every authorization helper keeps working unchanged.

Standardized error shape:
    { "error_code": "<stable_code>", "reason": "<human message>" }

Stable error codes emitted here:
    missing_auth_header
    unknown_user
    cross_org_access_forbidden
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

DB_PATH = Path(__file__).resolve().parents[1] / "chartnav.db"

# Auth mode is an abstraction seam for future transports. Only "header"
# is implemented today. Swapping to "jwt" or "oidc" would change only
# `require_caller`; the authz layer is transport-agnostic.
AUTH_MODE = os.environ.get("CHARTNAV_AUTH_MODE", "header")


@dataclass(frozen=True)
class Caller:
    user_id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_id: int


def _error(code: str, reason: str, status: int) -> HTTPException:
    return HTTPException(
        status_code=status, detail={"error_code": code, "reason": reason}
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _resolve_by_email(email: str) -> Optional[Caller]:
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
        return None
    return Caller(
        user_id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        organization_id=row["organization_id"],
    )


def require_caller(
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
) -> Caller:
    """Primary authentication seam.

    Swap the body of this function (or branch on AUTH_MODE) when we move
    to a real identity transport. The return contract — a `Caller` with
    `organization_id` and `role` — must stay the same so no route or
    authz helper has to change.
    """
    if AUTH_MODE != "header":
        # Safety net: if AUTH_MODE is set to something we haven't wired
        # up yet, refuse rather than silently fall back to dev auth.
        raise _error(
            "auth_mode_unsupported",
            f"AUTH_MODE={AUTH_MODE!r} is not implemented",
            status=500,
        )

    if not x_user_email or not x_user_email.strip():
        raise _error("missing_auth_header", "X-User-Email is required", 401)

    caller = _resolve_by_email(x_user_email.strip())
    if not caller:
        raise _error("unknown_user", "no user matches X-User-Email", 401)
    return caller


def ensure_same_org(caller: Caller, target_organization_id: int) -> None:
    """Raise 403 if the caller tries to act across orgs."""
    if caller.organization_id != target_organization_id:
        raise _error(
            "cross_org_access_forbidden",
            "requested organization does not match caller's organization",
            403,
        )
