"""Central runtime configuration.

All environment-derived settings live here. Other modules MUST import
from `app.config`, not read `os.environ` directly, so the contract is
discoverable in one place.

Required for local dev: nothing (defaults are safe).
Required for production: `CHARTNAV_AUTH_MODE=bearer` → plus
`CHARTNAV_JWT_ISSUER`, `CHARTNAV_JWT_AUDIENCE`, `CHARTNAV_JWT_JWKS_URL`.
See docs/build/12-runtime-config.md for the full contract.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE = f"sqlite:///{_API_DIR / 'chartnav.db'}"


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v.strip()


@dataclass(frozen=True)
class Settings:
    # Runtime env name — purely informational (dev / test / ci / prod).
    env: str

    # Database URL. SQLAlchemy-style:
    #   sqlite:///absolute/path/to/file.db
    #   postgresql+psycopg://user:pw@host:5432/db
    database_url: str

    # Auth transport.
    #   "header"  → dev. Reads `X-User-Email` and resolves against `users`.
    #   "bearer"  → production. Reads `Authorization: Bearer <jwt>` and
    #              validates signature/iss/aud/exp against a JWKS endpoint.
    auth_mode: str

    # JWT (production). Required when auth_mode == "bearer".
    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_jwks_url: str | None
    # Claim used to map the token to a row in `users`. Default "email".
    jwt_user_claim: str

    # CORS — comma-separated list of origins. Empty string → deny all
    # cross-origin traffic (same-origin only).
    cors_allow_origins: tuple[str, ...]

    # Rate limiting (per-process, in-memory). Requests per minute per
    # client (remote addr + path). 0 disables.
    rate_limit_per_minute: int


_DEFAULT_CORS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)


def _load() -> Settings:
    env = _env("CHARTNAV_ENV", "dev") or "dev"
    database_url = _env("DATABASE_URL", _DEFAULT_SQLITE) or _DEFAULT_SQLITE
    auth_mode = (_env("CHARTNAV_AUTH_MODE", "header") or "header").lower()
    jwt_issuer = _env("CHARTNAV_JWT_ISSUER")
    jwt_audience = _env("CHARTNAV_JWT_AUDIENCE")
    jwt_jwks_url = _env("CHARTNAV_JWT_JWKS_URL")
    jwt_user_claim = _env("CHARTNAV_JWT_USER_CLAIM", "email") or "email"

    cors_raw = _env("CHARTNAV_CORS_ALLOW_ORIGINS", _DEFAULT_CORS) or ""
    cors_allow_origins = tuple(
        o.strip() for o in cors_raw.split(",") if o.strip()
    )

    try:
        rate_limit_per_minute = int(
            _env("CHARTNAV_RATE_LIMIT_PER_MINUTE", "120") or "120"
        )
    except ValueError:
        raise RuntimeError("CHARTNAV_RATE_LIMIT_PER_MINUTE must be an integer")

    # Validate combinations. Fail loudly at import time rather than
    # silently accepting half-configured production auth.
    if auth_mode not in {"header", "bearer"}:
        raise RuntimeError(
            f"CHARTNAV_AUTH_MODE must be 'header' or 'bearer' "
            f"(got {auth_mode!r})"
        )
    if auth_mode == "bearer":
        missing = [
            name for name, value in (
                ("CHARTNAV_JWT_ISSUER", jwt_issuer),
                ("CHARTNAV_JWT_AUDIENCE", jwt_audience),
                ("CHARTNAV_JWT_JWKS_URL", jwt_jwks_url),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "CHARTNAV_AUTH_MODE=bearer requires: " + ", ".join(missing)
            )

    return Settings(
        env=env,
        database_url=database_url,
        auth_mode=auth_mode,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        jwt_jwks_url=jwt_jwks_url,
        jwt_user_claim=jwt_user_claim,
        cors_allow_origins=cors_allow_origins,
        rate_limit_per_minute=rate_limit_per_minute,
    )


settings = _load()
