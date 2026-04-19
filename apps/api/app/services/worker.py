"""Background-worker foundation for the ingestion queue (phase 23).

Until now, `run_ingestion_now()` ran in the HTTP request path and
nothing prevented two callers from racing on the same `queued` row.
This module adds the minimum honest primitives for a real background
worker:

- **Claim**: atomically flip one `queued` row to `processing` with
  a `claimed_by` + `claimed_at` stamp. Only the claiming worker can
  mutate that row.
- **Release**: hand a claim back (used by stale-claim recovery and
  by the explicit release-on-failure path).
- **Requeue stale**: any row whose claim is older than
  `CHARTNAV_WORKER_CLAIM_TTL_SECONDS` gets moved back to `queued`
  with its claim cleared. Operators can run this nightly or on
  worker startup; it's idempotent.
- **Run-one / run-until-empty**: end-to-end helpers that claim,
  process via `ingestion.run_ingestion_now`, and return a summary.

The worker is a plain Python function — no Celery, no Redis, no
external broker. A deployment can wire this into cron, a systemd
timer, `scripts/run_worker.py --once`, or a real queue later without
changing the contract. The HTTP layer never has to know the worker
exists.

Key invariants:
- Claim updates are conditional on `claimed_by IS NULL` so two
  workers calling at the same moment cannot both win.
- Every `run_one()` returns a terminal state (the row is
  `completed`, `failed`, or `needs_review` when the call returns,
  or there was nothing to claim).
- Workers identify themselves with a stable `worker_id`. Default
  is `hostname/pid` so log lines attribute back to a real process.
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa

from app.db import engine
from app.services import ingestion

log = logging.getLogger("chartnav.worker")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _claim_ttl_seconds() -> int:
    """How long a claim can sit before a worker may reclaim it.

    Env-tunable so staging can ratchet this down while operators
    investigate. Default: 15 minutes — long enough for a real STT
    call to finish, short enough that a crashed worker gets recovered
    inside a business hour.
    """
    raw = os.environ.get("CHARTNAV_WORKER_CLAIM_TTL_SECONDS")
    if not raw:
        return 900
    try:
        v = int(raw)
    except ValueError:
        return 900
    return max(30, v)


def default_worker_id() -> str:
    """Stable identifier for a worker process.

    `<hostname>/<pid>` is enough to attribute a claim to one process
    without leaking anything sensitive. Operators can override via
    `CHARTNAV_WORKER_ID` if they want semantic names.
    """
    override = os.environ.get("CHARTNAV_WORKER_ID")
    if override:
        return override.strip() or _fallback_worker_id()
    return _fallback_worker_id()


def _fallback_worker_id() -> str:
    try:
        host = socket.gethostname()
    except Exception:  # pragma: no cover
        host = "host"
    return f"{host}/{os.getpid()}"


# ---------------------------------------------------------------------------
# Claim primitives
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClaimResult:
    input_id: int | None
    claimed: bool
    # `stale_reclaim=True` indicates this worker recovered a row
    # whose previous claim had expired. Telemetry hook.
    stale_reclaim: bool = False


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _claim_one_queued(conn, worker_id: str) -> int | None:
    """Atomically claim a single queued row.

    Returns the input id on success, None if nothing is queued.
    Two concurrent callers cannot both claim the same row: the
    `WHERE claimed_by IS NULL` predicate on the UPDATE enforces
    mutual exclusion at the row level.
    """
    candidate = conn.execute(
        sa.text(
            "SELECT id FROM encounter_inputs "
            "WHERE processing_status = 'queued' AND claimed_by IS NULL "
            "ORDER BY id ASC LIMIT 1"
        )
    ).mappings().first()
    if candidate is None:
        return None

    input_id = int(candidate["id"])
    result = conn.execute(
        sa.text(
            "UPDATE encounter_inputs SET "
            "claimed_by = :w, claimed_at = CURRENT_TIMESTAMP, "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :id AND claimed_by IS NULL AND "
            "processing_status = 'queued'"
        ),
        {"w": worker_id, "id": input_id},
    )
    # rowcount on UPDATE may be -1 on some dialects when unknown; the
    # safer check is to re-read the row.
    _ = result.rowcount  # noqa: F841
    confirmed = conn.execute(
        sa.text(
            "SELECT claimed_by FROM encounter_inputs WHERE id = :id"
        ),
        {"id": input_id},
    ).mappings().first()
    if confirmed is None or confirmed["claimed_by"] != worker_id:
        return None
    return input_id


def claim_one(worker_id: str | None = None) -> ClaimResult:
    """Public claim-one entry point. Safe to call from any process."""
    wid = worker_id or default_worker_id()
    # First pass: recover any stale claims so those rows are visible
    # to the main claim query. Idempotent; always safe to run.
    requeue_stale_claims(wid)
    with engine.begin() as conn:
        input_id = _claim_one_queued(conn, wid)
    if input_id is None:
        return ClaimResult(input_id=None, claimed=False)
    return ClaimResult(input_id=input_id, claimed=True)


def release_claim(input_id: int, *, reason: str = "released") -> None:
    """Explicit claim release. Used by crash-recovery callers.

    Does NOT touch `processing_status` — callers that want the row
    back in the queue should set it back to `queued` themselves (or
    use `requeue_stale_claims`).
    """
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE encounter_inputs SET "
                "claimed_by = NULL, claimed_at = NULL, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": input_id},
        )
    log.info("claim_released input_id=%s reason=%s", input_id, reason)


def requeue_stale_claims(worker_id: str | None = None) -> int:
    """Move stale `processing` rows back to `queued`.

    "Stale" = `claimed_by IS NOT NULL` AND `claimed_at` is older
    than `CHARTNAV_WORKER_CLAIM_TTL_SECONDS`. Returns the number of
    rows recovered.

    Idempotent. Safe to call on every worker-tick — the TTL is
    long enough (15 min default) that a live worker won't be
    stomped, and the race window is a second at most because the
    subsequent claim attempt will see the reset row and re-claim
    it under its own `worker_id`.
    """
    cutoff = _now() - timedelta(seconds=_claim_ttl_seconds())
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "UPDATE encounter_inputs SET "
                "processing_status = 'queued', "
                "claimed_by = NULL, claimed_at = NULL, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE processing_status = 'processing' AND "
                "claimed_by IS NOT NULL AND "
                "claimed_at IS NOT NULL AND "
                "claimed_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
    try:
        n = int(result.rowcount) if result.rowcount not in (None, -1) else 0
    except Exception:  # pragma: no cover
        n = 0
    if n:
        log.warning(
            "worker_stale_claims_recovered count=%s worker=%s cutoff=%s",
            n, worker_id or default_worker_id(), cutoff.isoformat(),
        )
    return n


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkerTick:
    input_id: int
    status: str
    ingestion_error: str | None


def run_one(worker_id: str | None = None) -> WorkerTick | None:
    """Claim one queued row and drive it through the pipeline.

    Returns `None` when the queue is empty. On success or failure,
    returns a `WorkerTick` describing the terminal state. Any
    `IngestionError` raised by the pipeline is caught here — the
    pipeline itself already persists the terminal state on the row,
    so the worker's only job is to release the claim for the next
    tick.
    """
    wid = worker_id or default_worker_id()
    claim = claim_one(wid)
    if not claim.claimed or claim.input_id is None:
        return None

    input_id = claim.input_id
    try:
        updated = ingestion.run_ingestion_now(input_id, worker_id=wid)
        return WorkerTick(
            input_id=input_id,
            status=str(updated["processing_status"]),
            ingestion_error=None,
        )
    except ingestion.IngestionError as e:
        # Pipeline already recorded `failed` on the row. Clear the
        # claim so the operator can retry without hitting a stale
        # claim check.
        release_claim(input_id, reason=f"ingestion_failed:{e.error_code}")
        return WorkerTick(
            input_id=input_id,
            status="failed",
            ingestion_error=e.error_code,
        )
    except Exception as e:  # pragma: no cover — defensive
        log.exception("worker_unexpected_error input_id=%s", input_id)
        release_claim(input_id, reason="unexpected_error")
        return WorkerTick(
            input_id=input_id,
            status="failed",
            ingestion_error="unexpected_error",
        )


def run_until_empty(
    worker_id: str | None = None, max_ticks: int = 100
) -> dict[str, Any]:
    """Drain the queue. Returns a summary for operator visibility.

    `max_ticks` is a hard ceiling so a runaway queue (or a bug that
    keeps re-queueing the same row) cannot spin forever. A real
    deployment would call `run_one()` on a fixed cadence instead.
    """
    wid = worker_id or default_worker_id()
    processed = 0
    completed = 0
    failed = 0
    error_codes: list[str] = []

    for _ in range(max_ticks):
        tick = run_one(wid)
        if tick is None:
            break
        processed += 1
        if tick.status == "completed":
            completed += 1
        elif tick.status == "failed":
            failed += 1
            if tick.ingestion_error:
                error_codes.append(tick.ingestion_error)

    return {
        "worker_id": wid,
        "processed": processed,
        "completed": completed,
        "failed": failed,
        "error_codes": error_codes,
    }
