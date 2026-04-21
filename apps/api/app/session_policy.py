"""Phase 47 — enterprise session policy seam (default-off).

This is the single entry point wave-2 will extend for:

  - MFA-required-claim enforcement
  - Session idle / absolute timeout
  - Per-org policy overrides via `organizations.settings.feature_flags`

Shipping now as an explicit seam so wave-2 code lands against a
stable surface instead of a fresh design discussion. The default
behavior is **no policy enforced** — existing callers see no
change unless their org opts in.

Opt-in keys on `organizations.settings.feature_flags`:

  require_mfa                      bool   default false
  session_idle_timeout_minutes     int    default null (off)
  session_absolute_timeout_minutes int    default null (off)

When `require_mfa` is true:
  - In `bearer` auth mode, the JWT must carry at least one of:
      `mfa`     : true
      `amr`     : list containing one of { "mfa", "otp", "hwk",
                  "swk", "pwd+otp", "fido" }
      `acr`     : value ∈ { "AAL2", "AAL3", "urn:mace:incommon:iap:silver",
                  "urn:mace:incommon:iap:bronze" } (informational only;
                  real policy is AAL2+)
  - In `header` auth mode (dev), MFA is assumed present so local
    development doesn't require flipping the flag every boot.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request

from app.auth import Caller, require_caller
from app.config import settings
from app.db import fetch_one


# ---------------------------------------------------------------------
# IdP claims — typed view over the bearer JWT payload
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class IdPClaims:
    """Typed projection of the claims wave-2 cares about. All fields
    are optional because today's bearer path does not surface the
    raw claim dict to downstream dependencies; this dataclass is a
    forward-compatible placeholder populated by the MFA gate when
    it reads the request payload cache."""
    subject: Optional[str] = None
    email: Optional[str] = None
    mfa_authenticated: bool = False
    acr: Optional[str] = None
    amr: Optional[list[str]] = None
    groups: Optional[list[str]] = None

    @classmethod
    def empty(cls) -> "IdPClaims":
        return cls()

    @classmethod
    def from_jwt_payload(cls, payload: dict[str, Any]) -> "IdPClaims":
        # `mfa` is a common Auth0 / Azure claim; `amr` is OIDC core;
        # `acr` is OIDC assurance-level. We accept any of them.
        amr = payload.get("amr")
        if isinstance(amr, str):
            amr = [amr]
        if not isinstance(amr, list):
            amr = None
        groups = payload.get("groups")
        if isinstance(groups, str):
            groups = [groups]
        if not isinstance(groups, list):
            groups = None
        mfa_flag = bool(payload.get("mfa")) or _amr_looks_mfa(amr or [])
        return cls(
            subject=payload.get("sub") if isinstance(payload.get("sub"), str) else None,
            email=payload.get("email") if isinstance(payload.get("email"), str) else None,
            mfa_authenticated=mfa_flag,
            acr=payload.get("acr") if isinstance(payload.get("acr"), str) else None,
            amr=amr,
            groups=groups,
        )


_MFA_AMR_TOKENS = {
    "mfa",
    "otp",
    "hwk",      # hardware key
    "swk",      # software key
    "fido",
    "fido2",
    "webauthn",
    "pwd+otp",
}


def _amr_looks_mfa(amr: list[str]) -> bool:
    return any(
        (tok or "").lower() in _MFA_AMR_TOKENS for tok in amr
    )


# ---------------------------------------------------------------------
# Per-org policy read
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class SessionPolicy:
    """Resolved session policy for a caller's org. Built from the
    `organizations.settings` JSON blob. Everything defaults to OFF.
    """
    require_mfa: bool = False
    idle_timeout_minutes: Optional[int] = None
    absolute_timeout_minutes: Optional[int] = None

    @classmethod
    def off(cls) -> "SessionPolicy":
        return cls()


def _load_org_settings(organization_id: int) -> dict[str, Any]:
    row = fetch_one(
        "SELECT settings FROM organizations WHERE id = :id",
        {"id": organization_id},
    )
    if not row:
        return {}
    raw = dict(row).get("settings")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw) or {}
        except (ValueError, TypeError):
            return {}
    return {}


def resolve_session_policy(organization_id: int) -> SessionPolicy:
    """Read the org's session policy. Pure function. Returns a
    default-off policy when the org has no settings or the setting
    keys are absent."""
    settings_blob = _load_org_settings(organization_id)
    flags = settings_blob.get("feature_flags") or {}
    ext = settings_blob.get("extensions") or {}

    def _read_bool(k: str) -> bool:
        v = flags.get(k)
        if v is None:
            v = ext.get(k)
        return bool(v) if v is not None else False

    def _read_int(k: str) -> Optional[int]:
        v = flags.get(k)
        if v is None:
            v = ext.get(k)
        if v is None:
            return None
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return n if n > 0 else None

    return SessionPolicy(
        require_mfa=_read_bool("require_mfa"),
        idle_timeout_minutes=_read_int("session_idle_timeout_minutes"),
        absolute_timeout_minutes=_read_int("session_absolute_timeout_minutes"),
    )


# ---------------------------------------------------------------------
# require_mfa — FastAPI dependency
# ---------------------------------------------------------------------

def _forbidden(error_code: str, reason: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error_code": error_code, "reason": reason},
    )


def require_mfa(
    request: Request,
    caller: Caller = Depends(require_caller),
) -> Caller:
    """Dependency that enforces `require_mfa` when the caller's org
    has opted in. Call-site: attach alongside `require_admin` or
    `require_caller` on sensitive admin routes.

        @router.get("/admin/kpi/overview", dependencies=[Depends(require_mfa)])
        def ...

    Default behavior: off. If the org has not opted in, this
    dependency is a no-op.

    Header-auth mode is assumed MFA-present so developer loops do
    not require flipping the flag every run. Enterprise
    deployments run in bearer mode; the flag is meaningful there.
    """
    policy = resolve_session_policy(caller.organization_id)
    if not policy.require_mfa:
        return caller

    mode = settings.auth_mode
    if mode == "header":
        return caller

    # Bearer mode: read the cached JWT claims off request.state if
    # the bearer resolver stored them. Wave-2 will wire the
    # resolver to populate this; until then, a conservative
    # fallback denies when we cannot verify MFA.
    claims = getattr(request.state, "idp_claims", None)
    if isinstance(claims, IdPClaims) and claims.mfa_authenticated:
        return caller

    raise _forbidden(
        "mfa_required",
        "this organization requires an MFA-authenticated session",
    )


__all__ = [
    "IdPClaims",
    "SessionPolicy",
    "resolve_session_policy",
    "require_mfa",
]
