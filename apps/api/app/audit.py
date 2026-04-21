"""Security audit trail.

Writes a durable row for every denied or suspicious access attempt.
Stored in the `security_audit_events` table (migration `b2c3d4e5f6a7`).

Rules:
  - No secrets, no raw JWTs, no `Authorization` header value.
  - Safe by construction: audit failures never mask the original error.
  - Called from both the auth layer (via the HTTP exception handler) and
    any place that wants to record a business-level denial.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import text

from app.db import transaction

log = logging.getLogger("chartnav.audit")

# Error codes that should always be audited, regardless of status.
AUDITED_ERROR_CODES: frozenset[str] = frozenset(
    {
        "missing_auth_header",
        "unknown_user",
        "invalid_authorization_header",
        "invalid_token",
        "token_expired",
        "invalid_issuer",
        "invalid_audience",
        "missing_user_claim",
        "cross_org_access_forbidden",
        "role_forbidden",
        "role_cannot_create_encounter",
        "role_cannot_create_event",
        "role_cannot_transition",
        "rate_limited",
    }
)


def should_audit(status_code: int, error_code: Optional[str]) -> bool:
    if error_code and error_code in AUDITED_ERROR_CODES:
        return True
    # All 401/403 get audited even if the error code is unknown.
    return status_code in (401, 403)


def record(
    *,
    event_type: str,
    request_id: Optional[str],
    actor_email: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    error_code: Optional[str] = None,
    detail: Optional[str] = None,
    remote_addr: Optional[str] = None,
) -> None:
    """Write a single audit event. Never raises."""
    try:
        # Observe the metric first so it still counts even if the DB
        # insert fails.
        from app.metrics import metrics as _metrics
        _metrics.observe_audit_event(event_type)
    except Exception:  # pragma: no cover
        pass
    try:
        with transaction() as conn:
            conn.execute(
                text(
                    "INSERT INTO security_audit_events ("
                    "event_type, request_id, actor_email, actor_user_id, "
                    "organization_id, path, method, error_code, detail, "
                    "remote_addr) VALUES ("
                    ":event_type, :request_id, :actor_email, :actor_user_id, "
                    ":organization_id, :path, :method, :error_code, :detail, "
                    ":remote_addr)"
                ),
                {
                    "event_type": event_type,
                    "request_id": request_id,
                    "actor_email": actor_email,
                    "actor_user_id": actor_user_id,
                    "organization_id": organization_id,
                    "path": path,
                    "method": method,
                    "error_code": error_code,
                    "detail": detail,
                    "remote_addr": remote_addr,
                },
            )
    except Exception as e:  # pragma: no cover — defensive
        log.error("audit.record failed: %s", e)

    # Phase 48 — enterprise audit sink. Fire AFTER the authoritative
    # DB insert so a sink outage cannot block or corrupt the
    # internal audit trail. `dispatch(...)` swallows every error it
    # encounters; see apps/api/app/services/audit_sink.py.
    try:
        from app.services.audit_sink import dispatch as _sink_dispatch
        _sink_dispatch({
            "event_type": event_type,
            "request_id": request_id,
            "actor_email": actor_email,
            "actor_user_id": actor_user_id,
            "organization_id": organization_id,
            "path": path,
            "method": method,
            "error_code": error_code,
            "detail": detail,
            "remote_addr": remote_addr,
        })
    except Exception:  # pragma: no cover — defensive
        pass


def query_recent(limit: int = 50) -> list[dict[str, Any]]:
    """Read helper used only by tests / operator debugging."""
    from app.db import fetch_all

    return fetch_all(
        "SELECT id, event_type, request_id, actor_email, actor_user_id, "
        "organization_id, path, method, error_code, detail, remote_addr, "
        "created_at FROM security_audit_events ORDER BY id DESC LIMIT :lim",
        {"lim": limit},
    )
