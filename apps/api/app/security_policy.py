"""Phase 48 — enterprise control-plane wave 2: org security policy.

Single source of truth for every org-scoped enterprise-security
value that lives in `organizations.settings`. Extends (does not
replace) the phase-47 `session_policy.py` seam:

  - phase-47 `session_policy.resolve_session_policy(org)` →
    {require_mfa, idle_timeout_minutes, absolute_timeout_minutes}
    is the **timeout-enforcement** lens. Still used by the
    middleware-time gate.
  - phase-48 `security_policy.resolve_security_policy(org)` →
    the broader **policy document** the admin UI reads/writes:
    MFA + timeouts + audit sink + security-admin allowlist.

The two views read from the same JSON blob so they can never
drift. Writers only go through `update_security_policy(...)`.

Storage shape under `organizations.settings`:

    {
      "feature_flags": { ...existing flags (audit_export, bulk_import) },
      "security": {
        "require_mfa":                    bool,
        "idle_timeout_minutes":           int|null,
        "absolute_timeout_minutes":       int|null,
        "audit_sink_mode":                "disabled"|"jsonl"|"webhook",
        "audit_sink_target":              str|null,   # file path or URL
        "security_admin_emails":          [str, ...]  # lowercase, trimmed
      }
    }

Default: absence of `security` → all values off / disabled. Current
production settings that have never touched this block continue to
behave exactly as before.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from fastapi import Depends, HTTPException

from app.auth import Caller, require_caller
from app.db import fetch_one, transaction
from sqlalchemy import text


# ---------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------

AUDIT_SINK_MODES: tuple[str, ...] = ("disabled", "jsonl", "webhook")


EVIDENCE_SINK_MODES = ("disabled", "jsonl", "webhook")
EVIDENCE_SIGNING_MODES = ("disabled", "hmac_sha256")


@dataclass(frozen=True)
class SecurityPolicy:
    """Resolved per-org security posture. All fields default to the
    safe "off" values — orgs that have never configured security
    see exactly the behavior they saw before phase 48."""
    require_mfa: bool = False
    idle_timeout_minutes: Optional[int] = None
    absolute_timeout_minutes: Optional[int] = None
    audit_sink_mode: str = "disabled"
    audit_sink_target: Optional[str] = None
    security_admin_emails: tuple[str, ...] = field(default_factory=tuple)
    # Phase 56 — independent evidence-sink channel. Separate from the
    # general audit sink because these are distinct forensic streams:
    # one org may want observability events in a SIEM and evidence
    # events in a WORM store, or vice versa.
    evidence_sink_mode: str = "disabled"
    evidence_sink_target: Optional[str] = None
    # Phase 56 — evidence bundle signing. The HMAC secret itself
    # lives in process config (CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY),
    # NOT in the per-org settings JSON, because that JSON is readable
    # by org admins and the secret must not be.
    evidence_signing_mode: str = "disabled"
    evidence_signing_key_id: Optional[str] = None
    # Phase 57 — export snapshot retention (days). Null => retain
    # indefinitely. When set, a retention sweep soft-purges the
    # heavy `artifact_json` body on snapshots older than this window;
    # the row + hash + issuer stay so evidence-chain references
    # remain valid. There is a hard floor (90 days) enforced on
    # write so an org cannot accidentally configure a value that
    # would destroy current-quarter evidence.
    export_snapshot_retention_days: Optional[int] = None

    @classmethod
    def off(cls) -> "SecurityPolicy":
        return cls()

    def as_public_dict(self) -> dict[str, Any]:
        """The payload the admin UI sees. Never includes unknown keys
        or internal flags — every field here is intentional."""
        return {
            "require_mfa": self.require_mfa,
            "idle_timeout_minutes": self.idle_timeout_minutes,
            "absolute_timeout_minutes": self.absolute_timeout_minutes,
            "audit_sink_mode": self.audit_sink_mode,
            "audit_sink_target": self.audit_sink_target,
            "security_admin_emails": list(self.security_admin_emails),
            "evidence_sink_mode": self.evidence_sink_mode,
            "evidence_sink_target": self.evidence_sink_target,
            "evidence_signing_mode": self.evidence_signing_mode,
            "evidence_signing_key_id": self.evidence_signing_key_id,
            "export_snapshot_retention_days": self.export_snapshot_retention_days,
        }


# ---------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------

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


def resolve_security_policy(organization_id: int) -> SecurityPolicy:
    """Read the org's policy. Pure. Falls back to all-off defaults."""
    blob = _load_org_settings(organization_id)
    sec = blob.get("security")
    # Backwards compat: phase-47 seam wrote `require_mfa` +
    # `session_idle_timeout_minutes` + `session_absolute_timeout_minutes`
    # under `feature_flags` + `extensions`. Read those as fallbacks.
    flags = blob.get("feature_flags") or {}
    ext = blob.get("extensions") or {}
    if not isinstance(sec, dict):
        sec = {}

    def _bool(keys: Iterable[str], default: bool = False) -> bool:
        for k in keys:
            if k in sec:
                return bool(sec[k])
            if k in flags:
                return bool(flags[k])
            if k in ext:
                return bool(ext[k])
        return default

    def _int(keys: Iterable[str]) -> Optional[int]:
        for k in keys:
            v = sec.get(k, flags.get(k, ext.get(k)))
            if v is None:
                continue
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            return n if n > 0 else None
        return None

    def _str(keys: Iterable[str], default: Optional[str] = None) -> Optional[str]:
        for k in keys:
            v = sec.get(k, flags.get(k, ext.get(k)))
            if isinstance(v, str) and v.strip():
                return v.strip()
        return default

    mode = (_str(["audit_sink_mode"]) or "disabled").lower()
    if mode not in AUDIT_SINK_MODES:
        mode = "disabled"

    admins_raw = sec.get("security_admin_emails") or ext.get("security_admin_emails") or []
    if isinstance(admins_raw, str):
        admins_raw = [admins_raw]
    if not isinstance(admins_raw, list):
        admins_raw = []
    admins = tuple(
        sorted({
            str(e).strip().lower()
            for e in admins_raw
            if isinstance(e, str) and e.strip()
        })
    )

    evidence_sink_mode = (
        _str(["evidence_sink_mode"]) or "disabled"
    ).lower()
    if evidence_sink_mode not in EVIDENCE_SINK_MODES:
        evidence_sink_mode = "disabled"

    evidence_signing_mode = (
        _str(["evidence_signing_mode"]) or "disabled"
    ).lower()
    if evidence_signing_mode not in EVIDENCE_SIGNING_MODES:
        evidence_signing_mode = "disabled"

    return SecurityPolicy(
        require_mfa=_bool(["require_mfa"], False),
        idle_timeout_minutes=_int(
            ["idle_timeout_minutes", "session_idle_timeout_minutes"]
        ),
        absolute_timeout_minutes=_int(
            [
                "absolute_timeout_minutes",
                "session_absolute_timeout_minutes",
            ]
        ),
        audit_sink_mode=mode,
        audit_sink_target=_str(["audit_sink_target"]),
        security_admin_emails=admins,
        evidence_sink_mode=evidence_sink_mode,
        evidence_sink_target=_str(["evidence_sink_target"]),
        evidence_signing_mode=evidence_signing_mode,
        evidence_signing_key_id=_str(["evidence_signing_key_id"]),
        export_snapshot_retention_days=_int(
            ["export_snapshot_retention_days"]
        ),
    )


# ---------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class PolicyValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _clamp_minutes(value: Any, label: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise PolicyValidationError(
            "policy_validation_failed",
            f"{label} must be an integer number of minutes or null",
        )
    if n <= 0:
        return None
    # Hard ceiling — 30 days. Beyond that the value is meaningless
    # and a typo like `12000000` should not silently persist.
    if n > 60 * 24 * 30:
        raise PolicyValidationError(
            "policy_validation_failed",
            f"{label} must be <= 43200 (30 days)",
        )
    return n


def _coerce_update(
    patch: dict[str, Any],
    existing: SecurityPolicy,
) -> dict[str, Any]:
    """Apply a partial update over the existing policy, returning the
    canonical `security` block to persist. Missing keys preserve the
    existing value. Unknown keys are rejected."""
    allowed = {
        "require_mfa",
        "idle_timeout_minutes",
        "absolute_timeout_minutes",
        "audit_sink_mode",
        "audit_sink_target",
        "security_admin_emails",
        # Phase 56 — evidence sink + signing.
        "evidence_sink_mode",
        "evidence_sink_target",
        "evidence_signing_mode",
        "evidence_signing_key_id",
        # Phase 57 — export snapshot retention.
        "export_snapshot_retention_days",
    }
    unknown = set(patch.keys()) - allowed
    if unknown:
        raise PolicyValidationError(
            "policy_validation_failed",
            f"unknown policy keys: {sorted(unknown)}",
        )

    out: dict[str, Any] = existing.as_public_dict()

    if "require_mfa" in patch:
        out["require_mfa"] = bool(patch["require_mfa"])

    if "idle_timeout_minutes" in patch:
        out["idle_timeout_minutes"] = _clamp_minutes(
            patch["idle_timeout_minutes"], "idle_timeout_minutes"
        )

    if "absolute_timeout_minutes" in patch:
        out["absolute_timeout_minutes"] = _clamp_minutes(
            patch["absolute_timeout_minutes"], "absolute_timeout_minutes"
        )

    if "audit_sink_mode" in patch:
        mode = str(patch["audit_sink_mode"] or "").strip().lower()
        if mode not in AUDIT_SINK_MODES:
            raise PolicyValidationError(
                "policy_validation_failed",
                f"audit_sink_mode must be one of {list(AUDIT_SINK_MODES)}",
            )
        out["audit_sink_mode"] = mode

    if "audit_sink_target" in patch:
        tgt = patch["audit_sink_target"]
        if tgt is None or tgt == "":
            out["audit_sink_target"] = None
        else:
            out["audit_sink_target"] = str(tgt).strip()

    if "security_admin_emails" in patch:
        raw = patch["security_admin_emails"]
        if raw is None or raw == "":
            out["security_admin_emails"] = []
        else:
            if isinstance(raw, str):
                raw = [raw]
            if not isinstance(raw, list):
                raise PolicyValidationError(
                    "policy_validation_failed",
                    "security_admin_emails must be a list of strings",
                )
            cleaned: list[str] = []
            for e in raw:
                if not isinstance(e, str):
                    continue
                s = e.strip().lower()
                if not s:
                    continue
                if not _EMAIL_RE.match(s):
                    raise PolicyValidationError(
                        "policy_validation_failed",
                        f"security_admin_emails contains invalid email {e!r}",
                    )
                cleaned.append(s)
            out["security_admin_emails"] = sorted(set(cleaned))

    # Final cross-field sanity: if mode != disabled, target must be set.
    if out["audit_sink_mode"] != "disabled" and not out.get("audit_sink_target"):
        raise PolicyValidationError(
            "policy_validation_failed",
            f"audit_sink_target is required when audit_sink_mode is "
            f"{out['audit_sink_mode']!r}",
        )

    # Phase 56 — evidence-sink + signing patch handling.
    if "evidence_sink_mode" in patch:
        mode = str(patch["evidence_sink_mode"] or "").strip().lower()
        if mode not in EVIDENCE_SINK_MODES:
            raise PolicyValidationError(
                "policy_validation_failed",
                f"evidence_sink_mode must be one of "
                f"{list(EVIDENCE_SINK_MODES)}",
            )
        out["evidence_sink_mode"] = mode

    if "evidence_sink_target" in patch:
        tgt = patch["evidence_sink_target"]
        if tgt is None or tgt == "":
            out["evidence_sink_target"] = None
        else:
            out["evidence_sink_target"] = str(tgt).strip()

    if "evidence_signing_mode" in patch:
        mode = str(patch["evidence_signing_mode"] or "").strip().lower()
        if mode not in EVIDENCE_SIGNING_MODES:
            raise PolicyValidationError(
                "policy_validation_failed",
                f"evidence_signing_mode must be one of "
                f"{list(EVIDENCE_SIGNING_MODES)}",
            )
        out["evidence_signing_mode"] = mode

    if "evidence_signing_key_id" in patch:
        kid = patch["evidence_signing_key_id"]
        if kid is None or kid == "":
            out["evidence_signing_key_id"] = None
        else:
            out["evidence_signing_key_id"] = str(kid).strip()

    if (
        out.get("evidence_sink_mode", "disabled") != "disabled"
        and not out.get("evidence_sink_target")
    ):
        raise PolicyValidationError(
            "policy_validation_failed",
            f"evidence_sink_target is required when evidence_sink_mode "
            f"is {out['evidence_sink_mode']!r}",
        )

    # Phase 57 — retention floor. We reject values below 90 days so
    # an operator cannot accidentally configure a window that would
    # strip current-quarter evidence bodies. Null is fine (retain
    # forever). This is deliberately a hard floor; if a regulator
    # or policy requires shorter retention, that is a separate
    # conversation and should be an explicit config override.
    EXPORT_SNAPSHOT_RETENTION_FLOOR_DAYS = 90
    if "export_snapshot_retention_days" in patch:
        raw = patch["export_snapshot_retention_days"]
        if raw is None or raw == "":
            out["export_snapshot_retention_days"] = None
        else:
            try:
                n = int(raw)
            except (TypeError, ValueError):
                raise PolicyValidationError(
                    "policy_validation_failed",
                    "export_snapshot_retention_days must be an integer "
                    "number of days or null",
                )
            if n < EXPORT_SNAPSHOT_RETENTION_FLOOR_DAYS:
                raise PolicyValidationError(
                    "policy_validation_failed",
                    "export_snapshot_retention_days must be >= "
                    f"{EXPORT_SNAPSHOT_RETENTION_FLOOR_DAYS} days or null",
                )
            if n > 365 * 50:  # 50-year ceiling; beyond that, use null
                raise PolicyValidationError(
                    "policy_validation_failed",
                    "export_snapshot_retention_days too large; "
                    "use null for 'retain forever'",
                )
            out["export_snapshot_retention_days"] = n

    return out


def update_security_policy(
    organization_id: int,
    patch: dict[str, Any],
) -> SecurityPolicy:
    """Apply a partial update. Writes the merged `security` block
    back into `organizations.settings`. Raises `PolicyValidationError`
    on bad input — callers at the route layer map that to HTTP 400."""
    existing = resolve_security_policy(organization_id)
    merged = _coerce_update(patch, existing)
    blob = _load_org_settings(organization_id)
    blob["security"] = merged
    # Also keep the phase-47 seam's feature-flag keys in sync so the
    # middleware-time gate reads the same numbers. No removal of
    # keys that older code paths might read for.
    flags = blob.get("feature_flags") or {}
    flags["require_mfa"] = merged["require_mfa"]
    if merged["idle_timeout_minutes"] is not None:
        flags["session_idle_timeout_minutes"] = merged["idle_timeout_minutes"]
    else:
        flags.pop("session_idle_timeout_minutes", None)
    if merged["absolute_timeout_minutes"] is not None:
        flags["session_absolute_timeout_minutes"] = merged[
            "absolute_timeout_minutes"
        ]
    else:
        flags.pop("session_absolute_timeout_minutes", None)
    blob["feature_flags"] = flags

    with transaction() as conn:
        conn.execute(
            text("UPDATE organizations SET settings = :s WHERE id = :id"),
            {"s": json.dumps(blob), "id": organization_id},
        )
    return resolve_security_policy(organization_id)


# ---------------------------------------------------------------------
# Security-admin separation
# ---------------------------------------------------------------------

def caller_is_security_admin(caller: Caller) -> bool:
    """Return True iff the caller may perform privileged security
    actions. Rule: the built-in `admin` role is always a security
    admin (so a fresh org with no configured `security_admin_emails`
    still has a way in). If the org adds at least one email, only
    admins whose email is in that allowlist qualify.

    This gives us a real extension seam without breaking any of the
    seeded org1/org2 dev identities.
    """
    if caller.role != "admin":
        return False
    policy = resolve_security_policy(caller.organization_id)
    allowlist = policy.security_admin_emails
    if not allowlist:
        return True
    return caller.email.lower() in allowlist


def require_security_admin(
    caller: Caller = Depends(require_caller),
) -> Caller:
    """FastAPI dependency — only a security admin may proceed."""
    if not caller_is_security_admin(caller):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "security_admin_required",
                "reason": (
                    "this action requires the security-admin role for "
                    "this organization"
                ),
            },
        )
    return caller


__all__ = [
    "AUDIT_SINK_MODES",
    "EVIDENCE_SINK_MODES",
    "EVIDENCE_SIGNING_MODES",
    "SecurityPolicy",
    "PolicyValidationError",
    "resolve_security_policy",
    "update_security_policy",
    "caller_is_security_admin",
    "require_security_admin",
]
