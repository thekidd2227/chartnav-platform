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

    # Auth transport. Only "header" is fully implemented.
    # "bearer" is an honest placeholder — requests are rejected with a
    # clear 501 unless JWT settings are supplied AND validation code is
    # wired (it is NOT in this phase).
    auth_mode: str

    # JWT placeholders (production will need all three).
    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_jwks_url: str | None


def _load() -> Settings:
    env = _env("CHARTNAV_ENV", "dev") or "dev"
    database_url = _env("DATABASE_URL", _DEFAULT_SQLITE) or _DEFAULT_SQLITE
    auth_mode = (_env("CHARTNAV_AUTH_MODE", "header") or "header").lower()
    jwt_issuer = _env("CHARTNAV_JWT_ISSUER")
    jwt_audience = _env("CHARTNAV_JWT_AUDIENCE")
    jwt_jwks_url = _env("CHARTNAV_JWT_JWKS_URL")

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
        # NOTE: bearer token validation itself is not implemented in this
        # phase. `app.auth.resolve_caller_from_bearer` returns 501 so
        # deployments cannot accidentally serve unauthenticated traffic.

    return Settings(
        env=env,
        database_url=database_url,
        auth_mode=auth_mode,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        jwt_jwks_url=jwt_jwks_url,
    )


settings = _load()
