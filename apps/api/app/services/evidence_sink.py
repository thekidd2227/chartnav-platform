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


# Phase 59 — retry disposition + cap.
#
# MAX_SINK_ATTEMPTS: once an event has been attempted this many
# times without success, the retry sweep promotes it to
# `permanent_failure` so it stops cycling through automatic retries.
# 10 is generous: a short SIEM outage can blow through a handful of
# retries without triggering it; a long one eventually does.
MAX_SINK_ATTEMPTS: int = 10


def update_sink_status(
    *,
    evidence_event_id: int,
    result: EvidenceSinkDeliveryResult,
    increment_attempt: bool = True,
    disposition_override: Optional[str] = None,
) -> None:
    """Stamp the delivery outcome on the evidence row. The write is
    small and unconditional — the caller has already committed the
    row, and this is an independent columnar update on the same id.

    Phase 57 — also increments `sink_attempt_count`. The initial
    append after `record_evidence_event` sets the count to 1; each
    retry increments. Callers that wish to record a status WITHOUT
    consuming an attempt (e.g. a config migration) can pass
    `increment_attempt=False`.

    Never raises up to the caller: evidence chain correctness is
    more important than tracking delivery perfectly.
    """
    # Phase 59 — disposition tri-state. On a 'sent' outcome, clear
    # to no disposition (treat as completed). On a 'failed' outcome,
    # mark pending unless the attempt count has reached the cap, at
    # which point promote to permanent_failure. Disposition can also
    # be explicitly overridden (e.g. the abandon action).
    try:
        with transaction() as conn:
            # Fetch current attempt count so we can decide on the
            # disposition without a second UPDATE. If the row is
            # missing we just return — the row was deleted out from
            # under us, nothing to track.
            row = conn.execute(
                text(
                    "SELECT COALESCE(sink_attempt_count, 0) AS c "
                    "FROM note_evidence_events WHERE id = :id"
                ),
                {"id": int(evidence_event_id)},
            ).mappings().first()
            if not row:
                return
            next_count = int(row["c"]) + (1 if increment_attempt else 0)

            if disposition_override is not None:
                disposition = disposition_override
            elif result.status == "sent":
                # Delivery succeeded: no longer a retry candidate.
                disposition = None
            elif result.status == "failed":
                disposition = (
                    "permanent_failure"
                    if next_count >= MAX_SINK_ATTEMPTS
                    else "pending"
                )
            elif result.status == "skipped":
                # Transport disabled: not a failure, no disposition.
                disposition = None
            else:  # pragma: no cover — defensive
                disposition = None

            if increment_attempt:
                conn.execute(
                    text(
                        "UPDATE note_evidence_events SET "
                        "sink_status = :s, sink_attempted_at = :t, "
                        "sink_error = :e, "
                        "sink_attempt_count = :c, "
                        "sink_retry_disposition = :d "
                        "WHERE id = :id"
                    ),
                    {
                        "id": int(evidence_event_id),
                        "s": result.status,
                        "t": datetime.now(timezone.utc).isoformat(),
                        "e": result.error,
                        "c": next_count,
                        "d": disposition,
                    },
                )
            else:
                conn.execute(
                    text(
                        "UPDATE note_evidence_events SET "
                        "sink_status = :s, sink_attempted_at = :t, "
                        "sink_error = :e, "
                        "sink_retry_disposition = :d "
                        "WHERE id = :id"
                    ),
                    {
                        "id": int(evidence_event_id),
                        "s": result.status,
                        "t": datetime.now(timezone.utc).isoformat(),
                        "e": result.error,
                        "d": disposition,
                    },
                )
    except Exception:  # pragma: no cover
        log.warning("evidence_sink_status_update_failed", exc_info=True)


# ---------------------------------------------------------------------
# Phase 57 — retry path
# ---------------------------------------------------------------------

_EVIDENCE_ROW_COLS = (
    "id, organization_id, note_version_id, encounter_id, "
    "event_type, actor_user_id, actor_email, occurred_at, "
    "draft_status, final_approval_status, content_fingerprint, "
    "detail_json, prev_event_hash, event_hash"
)


@dataclass(frozen=True)
class RetrySweepResult:
    attempted: int
    sent: int
    failed: int
    skipped: int
    events: list[dict[str, Any]]


def retry_failed_deliveries(
    organization_id: int,
    *,
    max_events: int = 100,
) -> RetrySweepResult:
    """Retry every event with sink_status='failed' AND
    sink_retry_disposition in (NULL, 'pending') for this org, up to
    `max_events`. Oldest-first so backlog drains in order.

    Phase 59 — events that have crossed MAX_SINK_ATTEMPTS are NOT
    retried automatically; they now carry
    `sink_retry_disposition='permanent_failure'` and require an
    operator-initiated action. Events that an operator has flagged
    `'abandoned'` are also skipped. The retry sweep is therefore
    bounded — it cannot re-attempt a row that has been explicitly
    taken out of the retry pool.

    Guarantees:
      * does NOT touch any canonical evidence column (event_hash,
        prev_event_hash, content_fingerprint, etc.) — ONLY the
        sink_* tracking columns
      * skipped (sink disabled) events stay skipped rather than
        being marked sent; retry on a disabled sink is a no-op
      * each retry increments sink_attempt_count so operators can
        see stuck rows
      * post-attempt, if count >= MAX_SINK_ATTEMPTS the row is
        auto-promoted to disposition='permanent_failure'
    """
    from app.db import fetch_all as _fa

    rows = _fa(
        f"SELECT {_EVIDENCE_ROW_COLS}, sink_status, sink_attempt_count, "
        "sink_retry_disposition "
        "FROM note_evidence_events "
        "WHERE organization_id = :org AND sink_status = 'failed' "
        "AND (sink_retry_disposition IS NULL "
        "  OR sink_retry_disposition = 'pending') "
        "ORDER BY id ASC LIMIT :lim",
        {"org": int(organization_id), "lim": int(max_events)},
    )

    attempted = 0
    sent = 0
    failed = 0
    skipped = 0
    per_event: list[dict[str, Any]] = []
    for row in rows:
        attempted += 1
        result = dispatch_event(
            organization_id=int(row["organization_id"]),
            event_row=dict(row),
        )
        if result.status == "sent":
            sent += 1
        elif result.status == "failed":
            failed += 1
        elif result.status == "skipped":
            skipped += 1
        update_sink_status(
            evidence_event_id=int(row["id"]),
            result=result,
            increment_attempt=True,
        )
        per_event.append(
            {
                "evidence_event_id": int(row["id"]),
                "event_type": row.get("event_type"),
                "status": result.status,
                "error": result.error,
            }
        )
    return RetrySweepResult(
        attempted=attempted,
        sent=sent,
        failed=failed,
        skipped=skipped,
        events=per_event,
    )


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


# ---------------------------------------------------------------------
# Phase 59 — operator abandon path + retention of retry noise
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class AbandonResult:
    ok: bool
    evidence_event_id: int
    previous_disposition: Optional[str]
    new_disposition: str
    error_code: Optional[str] = None
    reason: Optional[str] = None


def abandon_event(
    *,
    evidence_event_id: int,
    organization_id: int,
    operator_reason: Optional[str],
) -> AbandonResult:
    """Mark a single failed evidence event as 'abandoned'.

    Preconditions:
      - the event exists and belongs to the caller's org
      - the event's sink_status is 'failed' (otherwise there's
        nothing to abandon — a 'sent' row needs no remediation and
        a 'skipped' row has no delivery to abandon)
      - the disposition is not already 'abandoned' (idempotent)

    Effect:
      - sink_retry_disposition flips to 'abandoned'
      - sink_error remains intact (evidence of why the operator
        abandoned) until the retention sweep clears it
      - sink_attempt_count is NOT incremented (abandoning is not an
        attempt)

    Returns an AbandonResult; the route layer audits.
    """
    from app.db import fetch_one as _fo

    row = _fo(
        "SELECT id, organization_id, sink_status, sink_retry_disposition, "
        "sink_attempt_count "
        "FROM note_evidence_events WHERE id = :id",
        {"id": int(evidence_event_id)},
    )
    if not row or int(row["organization_id"]) != int(organization_id):
        return AbandonResult(
            ok=False, evidence_event_id=int(evidence_event_id),
            previous_disposition=None, new_disposition="",
            error_code="evidence_event_not_found",
            reason="no such evidence event in this organization",
        )
    prev = row.get("sink_retry_disposition")
    if row.get("sink_status") != "failed":
        return AbandonResult(
            ok=False, evidence_event_id=int(evidence_event_id),
            previous_disposition=prev, new_disposition=prev or "",
            error_code="abandon_not_applicable",
            reason=(
                f"event sink_status is {row.get('sink_status')!r}; "
                "only 'failed' rows can be abandoned"
            ),
        )
    if prev == "abandoned":
        # Idempotent no-op.
        return AbandonResult(
            ok=True, evidence_event_id=int(evidence_event_id),
            previous_disposition="abandoned",
            new_disposition="abandoned",
        )

    reason_str = (operator_reason or "").strip()[:500] or None
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_evidence_events SET "
                "sink_retry_disposition = 'abandoned', "
                "sink_error = COALESCE(:r, sink_error) "
                "WHERE id = :id"
            ),
            {"id": int(evidence_event_id), "r": reason_str},
        )
    return AbandonResult(
        ok=True, evidence_event_id=int(evidence_event_id),
        previous_disposition=prev, new_disposition="abandoned",
    )


@dataclass(frozen=True)
class SinkRetentionSweepResult:
    dry_run: bool
    organization_id: int
    retention_days: Optional[int]
    candidates_found: int
    cleared: int
    candidate_ids: list[int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "organization_id": self.organization_id,
            "retention_days": self.retention_days,
            "candidates_found": self.candidates_found,
            "cleared": self.cleared,
            "candidate_ids": self.candidate_ids,
        }


def sweep_sink_retention(
    organization_id: int,
    *,
    dry_run: bool = False,
) -> SinkRetentionSweepResult:
    """Clear noisy `sink_error` text on abandoned / permanently-
    failed rows once they have aged past the retention window.

    SAFETY — what this function never does:
      * never deletes an evidence row (chain references matter)
      * never touches canonical columns (event_hash etc.)
      * never clears the disposition itself (operators still see
        what the final state was)
      * never runs when retention is unconfigured

    What it DOES do:
      * clears `sink_error` (the last failure reason string) on
        rows where `sink_retry_disposition in ('abandoned',
        'permanent_failure')` AND the attempt age exceeds the
        retention window. This is the "operational retry noise" —
        once the row is finalized, the text reason is no longer
        forensically interesting.

    Policy source: `security_policy.evidence_sink_retention_days`.
    Null → retain forever (no-op). Integer → clear after N days,
    with a hard floor of 7 days enforced at policy write time.
    """
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    from app.db import fetch_all as _fa
    from app.security_policy import resolve_security_policy

    policy = resolve_security_policy(organization_id)
    days = getattr(policy, "evidence_sink_retention_days", None)
    if not days:
        return SinkRetentionSweepResult(
            dry_run=dry_run, organization_id=int(organization_id),
            retention_days=None, candidates_found=0, cleared=0,
            candidate_ids=[],
        )

    cutoff = _dt.now(_tz.utc) - _td(days=int(days))
    candidates = _fa(
        "SELECT id FROM note_evidence_events "
        "WHERE organization_id = :org "
        "AND sink_retry_disposition IN ('abandoned', 'permanent_failure') "
        "AND sink_error IS NOT NULL "
        "AND sink_attempted_at < :cutoff "
        "ORDER BY id ASC LIMIT 1000",
        {"org": int(organization_id), "cutoff": cutoff.isoformat()},
    )
    ids = [int(r["id"]) for r in candidates]
    if dry_run or not ids:
        return SinkRetentionSweepResult(
            dry_run=dry_run, organization_id=int(organization_id),
            retention_days=int(days),
            candidates_found=len(ids),
            cleared=0, candidate_ids=ids,
        )
    cleared = 0
    with transaction() as conn:
        for sid in ids:
            conn.execute(
                text(
                    "UPDATE note_evidence_events SET sink_error = NULL "
                    "WHERE id = :id AND organization_id = :org "
                    "AND sink_error IS NOT NULL"
                ),
                {"id": sid, "org": int(organization_id)},
            )
            cleared += 1
    return SinkRetentionSweepResult(
        dry_run=False, organization_id=int(organization_id),
        retention_days=int(days),
        candidates_found=len(ids), cleared=cleared,
        candidate_ids=ids,
    )


__all__ = [
    "EvidenceSinkDeliveryResult",
    "dispatch_event",
    "update_sink_status",
    "probe_evidence_sink",
    "RetrySweepResult",
    "retry_failed_deliveries",
    "MAX_SINK_ATTEMPTS",
    "AbandonResult",
    "abandon_event",
    "SinkRetentionSweepResult",
    "sweep_sink_retention",
]
