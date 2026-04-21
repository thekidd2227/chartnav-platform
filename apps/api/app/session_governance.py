"""Phase 48 — real session governance.

Two responsibilities:

  1. **Session tracking.** Every authenticated request lands a row
     in `user_sessions` keyed on `(user_id, session_key)` where
     `session_key` is a deterministic, PHI-safe fingerprint of the
     auth transport (header-mode → email slug; bearer-mode → first
     32 hex chars of SHA-256 of the token payload). The raw
     bearer token is NEVER persisted.

  2. **Timeout enforcement.** On each authenticated request we
     read the org's resolved `SecurityPolicy`. If idle/absolute
     timeouts are configured, we compare them to `last_activity_at`
     / `created_at` and deny the request with a 401 when exceeded.
     The row is marked `revoked=idle_timeout` /
     `revoked=absolute_timeout` for audit legibility.

Default behavior — enforcement OFF.
    When a policy has NEITHER `idle_timeout_minutes` NOR
    `absolute_timeout_minutes` set (the current production shape
    for every seeded org and for every test that has not opted
    in), the tracking path short-circuits before hitting the DB.
    This keeps the hot path at zero cost and lets every existing
    pytest keep its current call pattern untouched.

Admin surface (routes in `app/api/routes.py`):
  GET  /admin/security/sessions
  POST /admin/security/sessions/{id}/revoke
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, Request
from sqlalchemy import text

from app.auth import Caller
from app.db import fetch_one, transaction
from app.security_policy import SecurityPolicy, resolve_security_policy

log = logging.getLogger("chartnav.session")


# ---------------------------------------------------------------------
# Session-key derivation (PHI-safe, deterministic)
# ---------------------------------------------------------------------

_EMAIL_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _email_slug(email: str) -> str:
    s = email.strip().lower()
    s = _EMAIL_SLUG_RE.sub("-", s).strip("-")
    return f"hdr:{s}"[:128]


def _bearer_fingerprint(authorization: Optional[str]) -> str:
    # authorization looks like "Bearer <token>". We hash the full
    # header so the raw token never hits disk. 32 hex chars of a
    # SHA-256 digest is more than enough entropy for session keying
    # while staying deterministic across restarts.
    if not authorization:
        return "bearer:anon"
    digest = hashlib.sha256(authorization.encode("utf-8")).hexdigest()
    return f"brr:{digest[:32]}"


def derive_session_key(
    caller: Caller,
    auth_mode: str,
    authorization: Optional[str],
) -> str:
    if auth_mode == "bearer":
        return _bearer_fingerprint(authorization)
    return _email_slug(caller.email)


# ---------------------------------------------------------------------
# Track + enforce (called from auth.require_caller)
# ---------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: Any) -> Optional[datetime]:
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        txt = str(s)
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        dt = datetime.fromisoformat(txt)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class SessionState:
    id: int
    created_at: datetime
    last_activity_at: datetime
    revoked_at: Optional[datetime]
    revoked_reason: Optional[str]


def _load_session(user_id: int, session_key: str) -> Optional[SessionState]:
    row = fetch_one(
        "SELECT id, created_at, last_activity_at, revoked_at, revoked_reason "
        "FROM user_sessions WHERE user_id = :u AND session_key = :k",
        {"u": user_id, "k": session_key},
    )
    if not row:
        return None
    r = dict(row)
    ca = _parse_iso(r["created_at"]) or _utcnow()
    la = _parse_iso(r["last_activity_at"]) or ca
    return SessionState(
        id=int(r["id"]),
        created_at=ca,
        last_activity_at=la,
        revoked_at=_parse_iso(r["revoked_at"]),
        revoked_reason=r["revoked_reason"],
    )


def _touch_session(
    caller: Caller,
    session_key: str,
    auth_mode: str,
    request: Request,
) -> None:
    remote_addr = (request.client.host if request.client else None) or None
    user_agent = request.headers.get("user-agent") if request else None
    # Upsert (portable SQL): INSERT … ON CONFLICT … DO UPDATE.
    # `user_sessions.uq_user_sessions_user_key` guarantees the conflict
    # target is deterministic.
    with transaction() as conn:
        # SQLite + Postgres both understand ON CONFLICT since a while
        # back; we keep the syntax to the intersection.
        conn.execute(
            text(
                "INSERT INTO user_sessions ("
                "  organization_id, user_id, session_key, auth_mode, "
                "  created_at, last_activity_at, remote_addr, user_agent"
                ") VALUES ("
                "  :org, :uid, :key, :mode, "
                "  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :ip, :ua"
                ") ON CONFLICT(user_id, session_key) DO UPDATE SET "
                "  last_activity_at = CURRENT_TIMESTAMP, "
                "  remote_addr = COALESCE(EXCLUDED.remote_addr, user_sessions.remote_addr), "
                "  user_agent = COALESCE(EXCLUDED.user_agent, user_sessions.user_agent)"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "key": session_key,
                "mode": auth_mode,
                "ip": remote_addr,
                "ua": (user_agent or "")[:500] or None,
            },
        )


def _revoke_session(
    session_id: int,
    reason: str,
    revoked_by_user_id: Optional[int] = None,
) -> None:
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE user_sessions SET "
                "  revoked_at = CURRENT_TIMESTAMP, "
                "  revoked_reason = :reason, "
                "  revoked_by_user_id = :byu "
                "WHERE id = :id AND revoked_at IS NULL"
            ),
            {"id": session_id, "reason": reason, "byu": revoked_by_user_id},
        )


def track_and_enforce(
    caller: Caller,
    auth_mode: str,
    authorization: Optional[str],
    request: Request,
) -> None:
    """Called from `auth.require_caller` after the caller is resolved.
    Short-circuits immediately for orgs that have NOT configured
    idle/absolute timeouts — the hot path pays zero DB cost in the
    common case."""
    try:
        policy = resolve_security_policy(caller.organization_id)
    except Exception:  # pragma: no cover — defensive
        return
    if (
        policy.idle_timeout_minutes is None
        and policy.absolute_timeout_minutes is None
    ):
        # No enforcement → no tracking. Keeps every seeded test at
        # zero overhead.
        return

    session_key = derive_session_key(caller, auth_mode, authorization)

    # Check for existing state BEFORE we update last_activity_at, so
    # idle-timeout evaluation uses the previous timestamp.
    existing = _load_session(caller.user_id, session_key)
    now = _utcnow()

    if existing and existing.revoked_at is not None:
        # Pre-revoked by admin action or a previous timeout. Refuse.
        raise _session_denied(
            "session_revoked",
            f"session revoked ({existing.revoked_reason or 'unknown'})",
        )

    if existing is not None:
        # Absolute timeout — measured from created_at.
        if (
            policy.absolute_timeout_minutes is not None
            and (now - existing.created_at)
            > timedelta(minutes=policy.absolute_timeout_minutes)
        ):
            _revoke_session(existing.id, "absolute_timeout")
            raise _session_denied(
                "session_absolute_timeout",
                "absolute session timeout exceeded; re-authenticate",
            )
        # Idle timeout — measured from last_activity_at.
        if (
            policy.idle_timeout_minutes is not None
            and (now - existing.last_activity_at)
            > timedelta(minutes=policy.idle_timeout_minutes)
        ):
            _revoke_session(existing.id, "idle_timeout")
            raise _session_denied(
                "session_idle_timeout",
                "idle session timeout exceeded; re-authenticate",
            )

    _touch_session(caller, session_key, auth_mode, request)


def _session_denied(error_code: str, reason: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error_code": error_code, "reason": reason},
    )


# ---------------------------------------------------------------------
# Admin read + write
# ---------------------------------------------------------------------

def list_sessions(
    organization_id: int,
    include_revoked: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    sql = (
        "SELECT s.id, s.user_id, u.email AS user_email, u.role AS user_role, "
        "s.session_key, s.auth_mode, s.created_at, s.last_activity_at, "
        "s.revoked_at, s.revoked_reason, s.remote_addr, s.user_agent "
        "FROM user_sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.organization_id = :org"
    )
    params: dict[str, Any] = {"org": organization_id}
    if not include_revoked:
        sql += " AND s.revoked_at IS NULL"
    sql += " ORDER BY s.last_activity_at DESC, s.id DESC LIMIT :lim"
    params["lim"] = int(limit)
    from app.db import fetch_all as _fa
    return [dict(r) for r in _fa(sql, params)]


def admin_revoke_session(
    organization_id: int,
    session_id: int,
    reason: str,
    by_user_id: int,
) -> dict[str, Any]:
    """Admin-initiated revocation. Returns the revoked row or
    raises 404 for unknown / cross-org. Audit is the caller's
    responsibility."""
    row = fetch_one(
        "SELECT id, organization_id, revoked_at FROM user_sessions WHERE id = :id",
        {"id": session_id},
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "session_not_found", "reason": "no such session"},
        )
    row = dict(row)
    if int(row["organization_id"]) != int(organization_id):
        raise HTTPException(
            status_code=404,
            detail={"error_code": "session_not_found", "reason": "no such session"},
        )
    if row["revoked_at"] is None:
        _revoke_session(int(row["id"]), reason or "admin_terminated", by_user_id)
    updated = fetch_one(
        "SELECT id, user_id, session_key, auth_mode, created_at, last_activity_at, "
        "revoked_at, revoked_reason, revoked_by_user_id "
        "FROM user_sessions WHERE id = :id",
        {"id": session_id},
    )
    return dict(updated) if updated else {}


__all__ = [
    "derive_session_key",
    "track_and_enforce",
    "list_sessions",
    "admin_revoke_session",
]
