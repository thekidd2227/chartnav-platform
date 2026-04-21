"""Authentication for ChartNav.

Two transports, gated by `CHARTNAV_AUTH_MODE` (see `app.config`):

    header  — dev only. Reads `X-User-Email` and resolves from the
              `users` table. Trivially spoofable.
    bearer  — production. Reads `Authorization: Bearer <jwt>` and
              validates signature + issuer + audience + expiry against
              `CHARTNAV_JWT_JWKS_URL`. The token is mapped to a row in
              `users` via `CHARTNAV_JWT_USER_CLAIM` (default `email`).

Every resolver returns the same `Caller` contract so routes and RBAC
helpers stay transport-agnostic.

Standardized error envelope everywhere:
    { "error_code": "<stable_code>", "reason": "<human message>" }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import jwt
from fastapi import Header, HTTPException, Request
from jwt import PyJWKClient, PyJWKClientError
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
)

from app.config import settings
from app.db import fetch_one

log = logging.getLogger("chartnav.auth")


@dataclass(frozen=True)
class Caller:
    user_id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_id: int


# --- Error shape ---------------------------------------------------------

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


def _user_by_email(email: str) -> Optional[Caller]:
    row = fetch_one(
        "SELECT id, email, full_name, role, organization_id "
        "FROM users WHERE email = :email",
        {"email": email},
    )
    return _caller_from_row(row) if row else None


# --- header mode ---------------------------------------------------------

def resolve_caller_from_header(x_user_email: Optional[str]) -> Caller:
    if not x_user_email or not x_user_email.strip():
        raise _error("missing_auth_header", "X-User-Email is required", 401)
    c = _user_by_email(x_user_email.strip())
    if not c:
        raise _error("unknown_user", "no user matches X-User-Email", 401)
    return c


# --- bearer mode (real JWT validation) -----------------------------------

# Pluggable JWKS client. Production uses PyJWKClient fetching from
# `settings.jwt_jwks_url`. Tests swap this for an in-memory stub.
_jwk_client: Optional[PyJWKClient] = None


def _jwks_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        if not settings.jwt_jwks_url:
            raise _error(
                "jwt_jwks_url_missing",
                "CHARTNAV_JWT_JWKS_URL not configured",
                500,
            )
        _jwk_client = PyJWKClient(settings.jwt_jwks_url, cache_keys=True)
    return _jwk_client


def set_jwk_client(client: Optional[PyJWKClient]) -> None:
    """Test hook: replace the module-level JWKS client."""
    global _jwk_client
    _jwk_client = client


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.strip():
        raise _error(
            "missing_auth_header",
            "Authorization: Bearer <token> is required",
            401,
        )
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _error(
            "invalid_authorization_header",
            "expected `Authorization: Bearer <token>`",
            401,
        )
    return parts[1].strip()


def resolve_caller_from_bearer(authorization: Optional[str]) -> Caller:
    token = _extract_bearer(authorization)

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    except PyJWKClientError as e:
        raise _error("invalid_token", f"JWKS lookup failed: {e}", 401)
    except InvalidTokenError as e:
        raise _error("invalid_token", str(e), 401)

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iss", "aud"]},
        )
    except ExpiredSignatureError:
        raise _error("token_expired", "token has expired", 401)
    except InvalidIssuerError:
        raise _error("invalid_issuer", "token issuer does not match", 401)
    except InvalidAudienceError:
        raise _error("invalid_audience", "token audience does not match", 401)
    except InvalidTokenError as e:
        raise _error("invalid_token", str(e), 401)

    claim = settings.jwt_user_claim
    identifier = claims.get(claim)
    if not identifier or not isinstance(identifier, str):
        raise _error(
            "missing_user_claim",
            f"token is missing required claim {claim!r}",
            401,
        )
    c = _user_by_email(identifier)
    if not c:
        raise _error(
            "unknown_user",
            f"no user matches claim {claim}={identifier!r}",
            401,
        )
    return c


# --- Single dispatch seam ------------------------------------------------

def require_caller(
    request: Request,
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> Caller:
    mode = settings.auth_mode
    if mode == "header":
        caller = resolve_caller_from_header(x_user_email)
    elif mode == "bearer":
        caller = resolve_caller_from_bearer(authorization)
    else:
        raise _error("auth_mode_unsupported", f"unknown auth mode: {mode!r}", 500)
    # Stash on request.state so middleware / error handlers / audit can
    # reference the resolved caller without re-running auth.
    request.state.caller = caller

    # Phase 48 — session governance. Short-circuits for orgs that
    # have not configured idle/absolute timeouts so the hot path is
    # zero-cost by default. Raises 401 when a session is revoked or
    # has exceeded an active timeout.
    try:
        from app.session_governance import track_and_enforce
        track_and_enforce(caller, mode, authorization, request)
    except HTTPException:
        raise
    except Exception:  # pragma: no cover — defensive
        # Never let governance bookkeeping break auth. If the tracking
        # path explodes, log and let the request through; timeout
        # enforcement remains on via the explicit denial branch above.
        import logging as _lg
        _lg.getLogger("chartnav.session").warning(
            "track_and_enforce soft-failed", exc_info=True
        )

    return caller


def ensure_same_org(caller: Caller, target_organization_id: int) -> None:
    if caller.organization_id != target_organization_id:
        raise _error(
            "cross_org_access_forbidden",
            "requested organization does not match caller's organization",
            403,
        )
