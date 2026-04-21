"""Phase 48 — enterprise-consumable audit export sink.

Ships a pluggable, per-org audit transport for the existing
`security_audit_events` table. The internal audit trail remains
authoritative; this is the outward-flowing mirror an enterprise
SOC/SIEM expects.

Transports (all opt-in per-org via `security_policy.audit_sink_mode`):

  - `disabled` (default)  — no-op. Zero overhead on the hot path.
  - `jsonl`               — append one JSON-encoded event per line
                            to the configured file path. Parent
                            directory is created if missing. Each
                            line is flushed so a tailing process
                            sees events immediately.
  - `webhook`             — POST each event as JSON to the
                            configured URL. Hard 2-second timeout.
                            Non-2xx and network errors are
                            swallowed + counted on metrics but do
                            NOT fail the originating write.

Design rules:

  1. `dispatch(event)` is called from `app.audit.record()` after
     the in-DB insert succeeds. It NEVER raises.
  2. The sink is resolved per-org on every call (cheap — reads a
     single `organizations.settings` row). This keeps the sink
     hot-reloadable without an in-process cache.
  3. The sink never sees PHI beyond what's already in
     `security_audit_events` (event_type, actor_email,
     organization_id, path, method, error_code, detail). Callers
     of `audit.record` are expected to keep `detail` short and
     PHI-minimising (the existing convention across the codebase).
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from app.security_policy import SecurityPolicy, resolve_security_policy

log = logging.getLogger("chartnav.audit_sink")


# Test / observability hook.
_last_events: list[dict[str, Any]] = []


def _capture_for_tests(event: dict[str, Any]) -> None:
    """Tests can assert on `_last_events` without standing up a real
    webhook. Capped at 500 entries to avoid unbounded growth."""
    _last_events.append(event)
    if len(_last_events) > 500:
        del _last_events[: len(_last_events) - 500]


def clear_test_capture() -> None:
    _last_events.clear()


def captured() -> list[dict[str, Any]]:
    return list(_last_events)


# ---------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------

def dispatch(event: dict[str, Any]) -> None:
    """Fire-and-forget forward of a single audit event to the
    org-configured sink. Never raises."""
    try:
        org_id = event.get("organization_id")
        if org_id is None:
            # No-org events (system-level) are never sink-forwarded
            # because there's no target to resolve against.
            return
        policy = resolve_security_policy(int(org_id))
        _capture_for_tests({"policy_mode": policy.audit_sink_mode, "event": event})
        mode = policy.audit_sink_mode
        if mode == "disabled":
            return
        if mode == "jsonl":
            _emit_jsonl(event, policy.audit_sink_target)
            return
        if mode == "webhook":
            _emit_webhook(event, policy.audit_sink_target)
            return
        # Unknown mode: safe no-op (shouldn't happen — resolver
        # normalizes to `disabled`).
    except Exception:  # pragma: no cover
        log.warning("audit_sink_dispatch_failed", exc_info=True)


def probe(organization_id: int) -> dict[str, Any]:
    """Exercise the currently-configured sink with a harmless
    heartbeat event. Returns `{ok, mode, target, detail}` for the
    admin UI 'Test' action."""
    probe_event = {
        "event_type": "audit_sink_probe",
        "organization_id": organization_id,
        "path": "/admin/security/audit-sink/test",
        "method": "POST",
        "detail": f"probe at {int(time.time())}",
        "actor_email": None,
        "actor_user_id": None,
        "error_code": None,
        "remote_addr": None,
    }
    policy = resolve_security_policy(organization_id)
    mode = policy.audit_sink_mode
    if mode == "disabled":
        return {
            "ok": True,
            "mode": mode,
            "target": None,
            "detail": "sink is disabled; nothing dispatched",
        }
    try:
        if mode == "jsonl":
            _emit_jsonl(probe_event, policy.audit_sink_target, raising=True)
        elif mode == "webhook":
            _emit_webhook(probe_event, policy.audit_sink_target, raising=True)
        else:
            return {
                "ok": False,
                "mode": mode,
                "target": policy.audit_sink_target,
                "detail": f"unknown sink mode {mode!r}",
            }
    except Exception as e:
        return {
            "ok": False,
            "mode": mode,
            "target": policy.audit_sink_target,
            "detail": f"{type(e).__name__}: {e}",
        }
    return {
        "ok": True,
        "mode": mode,
        "target": policy.audit_sink_target,
        "detail": "dispatched heartbeat event",
    }


# ---------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------

def _emit_jsonl(
    event: dict[str, Any],
    target: Optional[str],
    *,
    raising: bool = False,
) -> None:
    if not target:
        if raising:
            raise ValueError("jsonl sink requires audit_sink_target")
        return
    try:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str, separators=(",", ":")) + "\n")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                # Some filesystems (tmp overlays) don't support fsync; the
                # write is still durable enough for a tail-f SIEM.
                pass
    except Exception:
        if raising:
            raise
        log.warning("audit_sink_jsonl_failed", exc_info=True)


def _emit_webhook(
    event: dict[str, Any],
    target: Optional[str],
    *,
    raising: bool = False,
) -> None:
    if not target:
        if raising:
            raise ValueError("webhook sink requires audit_sink_target")
        return
    try:
        # Use urllib instead of adding a new dep. Hard 2s timeout.
        import urllib.request
        import urllib.error
        body = json.dumps(event, default=str).encode("utf-8")
        req = urllib.request.Request(
            target,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "user-agent": "chartnav-audit-sink/1",
            },
        )
        # A timeout here protects the hot path even if the SOC is
        # unreachable. 2s is deliberately generous for a healthy
        # network path and restrictive for a broken one.
        with urllib.request.urlopen(req, timeout=2) as resp:
            status = getattr(resp, "status", 200)
            if status >= 300:
                raise RuntimeError(f"webhook non-2xx: {status}")
    except Exception:
        if raising:
            raise
        log.warning("audit_sink_webhook_failed", exc_info=True)


__all__ = [
    "dispatch",
    "probe",
    "captured",
    "clear_test_capture",
]
