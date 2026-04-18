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

    # Audit retention (days). 0 disables the retention helper entirely
    # (rows live forever). When non-zero, `scripts/audit_retention.py`
    # deletes rows older than this threshold. The app itself never
    # silently prunes — retention runs on an operator cadence.
    audit_retention_days: int

    # Platform operating mode (phase 16). Governs whether ChartNav is
    # the system of record or a layer on top of an external EHR/EMR.
    #   "standalone"              → ChartNav owns all clinical data.
    #                               Native adapter persists to ChartNav's
    #                               own DB.
    #   "integrated_readthrough"  → ChartNav reads from an external
    #                               EHR/EMR via a vendor adapter and
    #                               mirrors what it needs; external
    #                               system remains SoR for clinical data.
    #   "integrated_writethrough" → Same as read-through plus ChartNav
    #                               is allowed to push updates
    #                               (notes, status, coding) back to the
    #                               external EHR/EMR through the adapter.
    # See docs/build/26-platform-mode-and-interoperability.md.
    platform_mode: str

    # Which external EHR/EMR adapter to select in integrated modes.
    # In `standalone`, this is ignored and the native adapter is used.
    # Ships "stub" (honest placeholder) and "fhir" (generic FHIR R4
    # read-through) out of the box. Vendor-specific adapters ("epic",
    # "cerner", ...) plug in via the adapter registry in
    # app/integrations/__init__.py.
    integration_adapter: str

    # FHIR adapter config — consumed when
    # CHARTNAV_INTEGRATION_ADAPTER=fhir. The adapter reads these via
    # os.environ directly too (so the test suite can drive it without
    # touching the Settings singleton), but they're surfaced here so
    # the contract is discoverable in one place.
    fhir_base_url: str | None
    fhir_auth_type: str            # "none" | "bearer"
    fhir_bearer_token: str | None


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

    try:
        audit_retention_days = int(
            _env("CHARTNAV_AUDIT_RETENTION_DAYS", "0") or "0"
        )
    except ValueError:
        raise RuntimeError("CHARTNAV_AUDIT_RETENTION_DAYS must be an integer")
    if audit_retention_days < 0:
        raise RuntimeError("CHARTNAV_AUDIT_RETENTION_DAYS must be >= 0")

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

    platform_mode = (
        _env("CHARTNAV_PLATFORM_MODE", "standalone") or "standalone"
    ).lower()
    allowed_modes = {
        "standalone",
        "integrated_readthrough",
        "integrated_writethrough",
    }
    if platform_mode not in allowed_modes:
        raise RuntimeError(
            "CHARTNAV_PLATFORM_MODE must be one of "
            + ", ".join(sorted(allowed_modes))
            + f" (got {platform_mode!r})"
        )

    # Default adapter: "native" in standalone, "stub" in integrated modes
    # (so the app boots honestly without a configured vendor connector).
    default_adapter = "native" if platform_mode == "standalone" else "stub"
    integration_adapter = (
        _env("CHARTNAV_INTEGRATION_ADAPTER", default_adapter) or default_adapter
    ).lower()

    # In standalone mode we silently force the native adapter — any other
    # value is operator confusion, fail loudly.
    if platform_mode == "standalone" and integration_adapter != "native":
        raise RuntimeError(
            "CHARTNAV_PLATFORM_MODE=standalone requires "
            "CHARTNAV_INTEGRATION_ADAPTER=native (or unset). "
            f"Got {integration_adapter!r}."
        )

    fhir_base_url = _env("CHARTNAV_FHIR_BASE_URL")
    fhir_auth_type = (_env("CHARTNAV_FHIR_AUTH_TYPE", "none") or "none").lower()
    fhir_bearer_token = _env("CHARTNAV_FHIR_BEARER_TOKEN")
    if fhir_auth_type not in {"none", "bearer"}:
        raise RuntimeError(
            f"CHARTNAV_FHIR_AUTH_TYPE must be 'none' or 'bearer' "
            f"(got {fhir_auth_type!r})"
        )
    # FHIR adapter itself re-validates at construction time — the
    # Settings object records the config without instantiating the
    # adapter so bootstrapping doesn't require a live FHIR server.

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
        audit_retention_days=audit_retention_days,
        platform_mode=platform_mode,
        integration_adapter=integration_adapter,
        fhir_base_url=fhir_base_url,
        fhir_auth_type=fhir_auth_type,
        fhir_bearer_token=fhir_bearer_token,
    )


settings = _load()
