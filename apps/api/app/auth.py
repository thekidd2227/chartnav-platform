"""Authentication for ChartNav.

Two transports, gated by `CHARTNAV_AUTH_MODE` (see `app.config`):

    header  — dev only. Reads `X-User-Email` and resolves from the
              `users` table. Trivially spoofable.
    bearer  — production-shaped stub. Requires `Authorization: Bearer <jwt>`.
              JWT signature / issuer / audience validation is NOT
              implemented in this phase — the resolver returns 501
              `auth_bearer_not_implemented` so deployments cannot
              accidentally serve unauthenticated traffic.

Every transport must produce the same `Caller` contract so routes and
authorization helpers do not need to change when the transport is
swapped. Downstream code depends on `require_caller`, never on a header.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException

from app.config import settings
from app.db import fetch_one


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


def _caller_from_row(row: dict) -> Caller:
    return Caller(
        user_id=row["id"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        organization_id=row["organization_id"],
    )


def resolve_caller_from_header(x_user_email: Optional[str]) -> Caller:
    if not x_user_email or not x_user_email.strip():
        raise _error("missing_auth_header", "X-User-Email is required", 401)
    row = fetch_one(
        "SELECT id, email, full_name, role, organization_id "
        "FROM users WHERE email = :email",
        {"email": x_user_email.strip()},
    )
    if not row:
        raise _error("unknown_user", "no user matches X-User-Email", 401)
    return _caller_from_row(row)


def resolve_caller_from_bearer(authorization: Optional[str]) -> Caller:
    """Production-shaped placeholder.

    In this phase we refuse to serve bearer-authenticated traffic
    because signature validation is not wired yet. The config module
    has already verified that issuer / audience / JWKS URL are set if
    `CHARTNAV_AUTH_MODE=bearer`, so operators know what they need; this
    function is the enforcement point that prevents a half-built
    deployment from looking "authenticated".
    """
    if not authorization or not authorization.strip():
        raise _error(
            "missing_auth_header",
            "Authorization: Bearer <token> is required",
            401,
        )
    raise _error(
        "auth_bearer_not_implemented",
        "bearer-token validation is not implemented in this phase; "
        "set CHARTNAV_AUTH_MODE=header for local dev",
        status=501,
    )


def require_caller(
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Caller:
    """Primary authentication seam.

    Dispatches based on `settings.auth_mode`. The return contract — a
    `Caller` with `organization_id` and `role` — is invariant across
    transports.
    """
    mode = settings.auth_mode
    if mode == "header":
        return resolve_caller_from_header(x_user_email)
    if mode == "bearer":
        return resolve_caller_from_bearer(authorization)
    # `app.config` already validates the mode; this is a belt-and-braces
    # guard in case someone imports Settings manually.
    raise _error(
        "auth_mode_unsupported", f"unknown auth mode: {mode!r}", 500
    )


def ensure_same_org(caller: Caller, target_organization_id: int) -> None:
    """Raise 403 if the caller tries to act across orgs."""
    if caller.organization_id != target_organization_id:
        raise _error(
            "cross_org_access_forbidden",
            "requested organization does not match caller's organization",
            403,
        )
