"""Phase 56 — external immutable evidence sink.

A dedicated forward-channel for `note_evidence_events`, separate
from the general `audit_sink` so that one org can send
observability events to a SIEM and forensic evidence events to a
WORM store (or vice versa).

The in-app `note_evidence_events` chain remains authoritative. The
sink is best-effort: if delivery fails, the event is still written
to the DB and the chain is still verifiable offline. Per-event
delivery status is recorded on the event row (`sink_status`,
`sink_attempted_at`, `sink_error`) so operators can see which
events made it out.

Supports two transport modes today:

  - `jsonl`    → append-only JSON Lines file. The consumer tails
                 the file and ingests to their preferred store.
                 Every line is self-contained with prev/event
                 hashes so tampering can be detected offline.
  - `webhook`  → HTTPS POST to a target URL with a compact JSON
                 body. Strict 2s timeout so a broken SIEM never
                 holds the governance path open.

The chain design reuses the audit_sink transport helpers
directly — same safety properties, same timeout.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.db import transaction
from app.security_policy import EVIDENCE_SINK_MODES, resolve_security_policy
from app.services.audit_sink import _emit_jsonl, _emit_webhook

log = logging.getLogger("chartnav.evidence_sink")


@dataclass(frozen=True)
class EvidenceSinkDeliveryResult:
    status: str  # "sent" | "failed" | "skipped"
    error: Optional[str]


def _serialize_event_for_sink(row: dict[str, Any]) -> dict[str, Any]:
    """Shape of a single evidence event as it is delivered to the
    external sink. Includes everything a downstream consumer needs
    to re-verify integrity: prev_event_hash + event_hash.

    `detail_json` stays stringified — the consumer parses if they
    want; otherwise the raw string is easy to store."""
    return {
        "kind": "chartnav.evidence_event.v1",
        "id": row.get("id"),
        "organization_id": row.get("organization_id"),
        "note_version_id": row.get("note_version_id"),
        "encounter_id": row.get("encounter_id"),
        "event_type": row.get("event_type"),
        "actor_user_id": row.get("actor_user_id"),
        "actor_email": row.get("actor_email"),
        "occurred_at": (
            row["occurred_at"].isoformat()
            if isinstance(row.get("occurred_at"), datetime)
            else row.get("occurred_at")
        ),
        "draft_status": row.get("draft_status"),
        "final_approval_status": row.get("final_approval_status"),
        "content_fingerprint": row.get("content_fingerprint"),
        "detail_json": row.get("detail_json"),
        "prev_event_hash": row.get("prev_event_hash"),
        "event_hash": row.get("event_hash"),
    }


def dispatch_event(
    *,
    organization_id: int,
    event_row: dict[str, Any],
) -> EvidenceSinkDeliveryResult:
    """Deliver one evidence event to the org's configured sink.

    Returns a structured result — never raises. Callers (the
    evidence append path) update the row's sink_status based on this
    result.
    """
    policy = resolve_security_policy(organization_id)
    mode = (policy.evidence_sink_mode or "disabled").lower()
    target = policy.evidence_sink_target

    if mode == "disabled" or mode not in EVIDENCE_SINK_MODES:
        return EvidenceSinkDeliveryResult(status="skipped", error=None)

    if not target:
        return EvidenceSinkDeliveryResult(
            status="failed",
            error="evidence_sink_target_missing",
        )

    payload = _serialize_event_for_sink(event_row)
    try:
        if mode == "jsonl":
            _emit_jsonl(payload, target, raising=True)
        elif mode == "webhook":
            _emit_webhook(payload, target, raising=True)
        else:  # pragma: no cover — defensive; mode validated above
            return EvidenceSinkDeliveryResult(
                status="failed",
                error=f"unknown_mode:{mode}",
            )
    except Exception as exc:
        # Short reason only — never let a full exception traceback
        # leak into the DB column.
        reason = f"{type(exc).__name__}:{str(exc)[:200]}"
        log.warning("evidence_sink_delivery_failed", exc_info=True)
        return EvidenceSinkDeliveryResult(status="failed", error=reason)

    return EvidenceSinkDeliveryResult(status="sent", error=None)


def update_sink_status(
    *,
    evidence_event_id: int,
    result: EvidenceSinkDeliveryResult,
) -> None:
    """Stamp the delivery outcome on the evidence row. The write is
    small and unconditional — the caller has already committed the
    row, and this is an independent columnar update on the same id.

    Never raises up to the caller: evidence chain correctness is
    more important than tracking delivery perfectly.
    """
    try:
        with transaction() as conn:
            conn.execute(
                text(
                    "UPDATE note_evidence_events SET "
                    "sink_status = :s, sink_attempted_at = :t, "
                    "sink_error = :e "
                    "WHERE id = :id"
                ),
                {
                    "id": int(evidence_event_id),
                    "s": result.status,
                    "t": datetime.now(timezone.utc).isoformat(),
                    "e": result.error,
                },
            )
    except Exception:  # pragma: no cover
        log.warning("evidence_sink_status_update_failed", exc_info=True)


def probe_evidence_sink(organization_id: int) -> dict[str, Any]:
    """Admin-initiated test shot at the configured sink. Writes a
    synthetic payload to the transport (never to the DB chain) and
    reports whether the sink accepted it. Used by the admin probe
    endpoint."""
    policy = resolve_security_policy(organization_id)
    mode = (policy.evidence_sink_mode or "disabled").lower()
    target = policy.evidence_sink_target

    if mode == "disabled" or mode not in EVIDENCE_SINK_MODES:
        return {
            "ok": False,
            "mode": mode,
            "target": target,
            "error_code": "evidence_sink_disabled",
            "reason": "no evidence sink configured for this org",
        }

    probe_event = {
        "kind": "chartnav.evidence_sink.probe.v1",
        "organization_id": organization_id,
        "probed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        if mode == "jsonl":
            _emit_jsonl(probe_event, target, raising=True)
        elif mode == "webhook":
            _emit_webhook(probe_event, target, raising=True)
        return {
            "ok": True,
            "mode": mode,
            "target": target,
            "error_code": None,
            "reason": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "mode": mode,
            "target": target,
            "error_code": "evidence_sink_delivery_failed",
            "reason": f"{type(exc).__name__}: {exc}",
        }


__all__ = [
    "EvidenceSinkDeliveryResult",
    "dispatch_event",
    "update_sink_status",
    "probe_evidence_sink",
]
