"""Transcript ingestion pipeline (phase 22).

Turns `encounter_inputs` rows through a real job lifecycle:

    queued → processing → completed
                        ↘ failed        (operator may retry)
                        ↘ needs_review  (operator intervention required)

Why this exists:
- Until now, text-paste / manual-entry inputs flipped straight to
  `completed` on arrival and audio uploads got stuck at `queued`.
  The rest of the system (`generate_note`) asked for a `completed`
  input and fell over otherwise.
- This module is the seam where a real audio transcriber (Deepgram,
  Whisper, vendor-specific STT) plugs in. For text-type inputs the
  "processing" work is trivial; for audio it becomes HTTP calls and
  polling. The HTTP layer never needs to know the difference.

Design invariants:
- Every state transition is a single DB write. No half-state rows.
- `retry_count`, `last_error`, `last_error_code`, `started_at`,
  `finished_at` are always set correctly so ops can answer "why is
  this stuck / when did it run / how many times".
- The transcriber is a single pluggable function (`_transcribe_audio`).
  Swap it without touching the orchestrator.
- `run_ingestion_now(input_id)` is synchronous and safe to call from
  the HTTP request path (tests do). A real deployment would invoke
  it from a cron/worker process. The contract is identical.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

import sqlalchemy as sa

from app.db import engine

log = logging.getLogger("chartnav.ingestion")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROCESSING_STATUSES = {
    "queued", "processing", "completed", "failed", "needs_review",
}
TERMINAL_STATUSES = {"completed", "failed", "needs_review"}

# Most inputs get a single retry-on-transient-failure; operators can
# call retry_input again. Audio STT specifically may burn more retries.
DEFAULT_MAX_RETRIES = 3


class IngestionError(RuntimeError):
    """Honest ingestion failure with an explicit error code."""

    def __init__(self, error_code: str, reason: str):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason


class TranscriptTooShort(IngestionError):
    def __init__(self, length: int):
        super().__init__(
            "transcript_too_short",
            f"transcript is {length} characters; need at least 10",
        )


class NotReadyToProcess(IngestionError):
    def __init__(self, current: str):
        super().__init__(
            "input_not_queueable",
            f"input is {current!r}; only queued / failed / needs_review can be (re)processed",
        )


# ---------------------------------------------------------------------------
# Transcriber seam
# ---------------------------------------------------------------------------
#
# Text-paste / manual-entry / imported-transcript inputs arrive with
# `transcript_text` already populated; the "transcription" step is a
# no-op. Audio uploads need a real transcriber. The signature is
# intentionally minimal:
#
#     transcribe(metadata: dict) -> str
#
# A real deployment monkey-patches `transcribe_audio` at module import
# time, or a future phase injects it via a registry. Today we ship a
# NotImplemented transcriber so audio uploads fail honestly instead
# of silently appearing "completed" with fake text.

def _not_implemented_transcriber(metadata: dict[str, Any]) -> str:  # pragma: no cover
    raise IngestionError(
        "audio_transcription_not_implemented",
        "no audio transcriber is wired; install one via "
        "ingestion.set_transcriber(...) before queueing audio uploads",
    )


transcribe_audio: Callable[[dict[str, Any]], str] = _not_implemented_transcriber


def set_transcriber(fn: Callable[[dict[str, Any]], str]) -> None:
    """Install a real transcriber implementation.

    Called from deployment bootstrap, vendor adapters, or tests that
    want to simulate an STT pipeline. Keeps the seam grep-able.
    """
    global transcribe_audio
    transcribe_audio = fn


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _load_input(conn, input_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa.text(
            "SELECT id, encounter_id, input_type, processing_status, "
            "transcript_text, confidence_summary, source_metadata, "
            "retry_count, last_error, last_error_code, started_at, "
            "finished_at, worker_id, created_at, updated_at "
            "FROM encounter_inputs WHERE id = :id"
        ),
        {"id": input_id},
    ).mappings().first()
    if row is None:
        raise IngestionError("input_not_found", f"encounter_input id={input_id}")
    return dict(row)


def _set_status(
    conn,
    input_id: int,
    *,
    status: str,
    transcript_text: str | None = None,
    last_error: str | None = None,
    last_error_code: str | None = None,
    retry_increment: int = 0,
    stamp_started: bool = False,
    stamp_finished: bool = False,
    worker_id: str | None = None,
) -> None:
    parts = ["processing_status = :status", "updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": input_id, "status": status}

    if transcript_text is not None:
        parts.append("transcript_text = :text")
        params["text"] = transcript_text

    # `last_error` is cleared on success and repopulated on failure so
    # operators don't see stale errors after a successful retry.
    if status == "completed":
        parts.append("last_error = NULL")
        parts.append("last_error_code = NULL")
    else:
        if last_error is not None:
            parts.append("last_error = :err")
            params["err"] = last_error
        if last_error_code is not None:
            parts.append("last_error_code = :ecode")
            params["ecode"] = last_error_code

    if retry_increment:
        parts.append(f"retry_count = retry_count + {int(retry_increment)}")

    if stamp_started:
        parts.append("started_at = CURRENT_TIMESTAMP")
    if stamp_finished:
        parts.append("finished_at = CURRENT_TIMESTAMP")

    if worker_id is not None:
        parts.append("worker_id = :worker")
        params["worker"] = worker_id

    conn.execute(
        sa.text(
            f"UPDATE encounter_inputs SET {', '.join(parts)} WHERE id = :id"
        ),
        params,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def enqueue_input(input_id: int) -> dict[str, Any]:
    """Move an input into `queued` state from a terminal retryable state.

    Text-type inputs are created with `processing_status=completed`
    directly by the HTTP route (no transcription to do). This helper
    is the explicit retry path for rows that previously `failed` or
    `needs_review`.
    """
    with engine.begin() as conn:
        row = _load_input(conn, input_id)
        current = row["processing_status"]
        # `queued` is already queued — idempotent no-op. `processing`
        # means a worker thinks it's running; refuse to stomp on it.
        if current == "queued":
            return row
        if current == "processing":
            raise NotReadyToProcess(current)
        if current not in {"failed", "needs_review"}:
            raise NotReadyToProcess(current)
        _set_status(
            conn,
            input_id,
            status="queued",
            retry_increment=1,
            # Clear started/finished so downstream runs re-stamp them.
        )
    # Read back the fresh shape.
    with engine.connect() as conn:
        return _load_input(conn, input_id)


def run_ingestion_now(
    input_id: int,
    *,
    worker_id: str = "inline",
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    """Run the ingestion pipeline for a single input synchronously.

    Safe to call from the HTTP handler (tests rely on this). A real
    deployment would invoke the same function from a worker loop.

    Transitions:
        queued   → processing → (completed | failed | needs_review)

    If the input is already `completed`, this is a no-op. `failed` /
    `needs_review` rows are skipped — use `enqueue_input()` to flip
    them back to `queued` first. That keeps retry semantics explicit.
    """
    with engine.begin() as conn:
        row = _load_input(conn, input_id)
        current = row["processing_status"]

        if current == "completed":
            return row
        if current not in {"queued", "processing"}:
            raise NotReadyToProcess(current)

        # Refuse to burn past the retry budget.
        if row["retry_count"] >= max_retries and current != "queued":
            _set_status(
                conn,
                input_id,
                status="failed",
                last_error_code="max_retries_exceeded",
                last_error=(
                    f"retry_count={row['retry_count']} reached max_retries="
                    f"{max_retries}; operator must reset"
                ),
                stamp_finished=True,
                worker_id=worker_id,
            )
            return _load_input(conn, input_id)

        # Move into `processing` before doing the work so a crashed
        # worker leaves the row in the right state.
        _set_status(
            conn,
            input_id,
            status="processing",
            stamp_started=True,
            worker_id=worker_id,
        )

    # Do the actual work outside the transaction so long-running
    # transcription doesn't hold a DB lock.
    try:
        transcript_text = _execute_pipeline(row)
    except IngestionError as e:
        with engine.begin() as conn:
            _set_status(
                conn,
                input_id,
                status="failed",
                last_error=e.reason,
                last_error_code=e.error_code,
                stamp_finished=True,
                worker_id=worker_id,
            )
        log.warning(
            "ingestion_failed input_id=%s code=%s", input_id, e.error_code
        )
        raise
    except Exception as e:  # pragma: no cover — defensive
        with engine.begin() as conn:
            _set_status(
                conn,
                input_id,
                status="failed",
                last_error=str(e)[:500],
                last_error_code="unexpected_error",
                stamp_finished=True,
                worker_id=worker_id,
            )
        log.exception("ingestion_unexpected_error input_id=%s", input_id)
        raise IngestionError("unexpected_error", str(e)) from e

    # Success path.
    with engine.begin() as conn:
        _set_status(
            conn,
            input_id,
            status="completed",
            transcript_text=transcript_text,
            stamp_finished=True,
            worker_id=worker_id,
        )

    with engine.connect() as conn:
        return _load_input(conn, input_id)


def _execute_pipeline(row: dict[str, Any]) -> str:
    """Return the finalized `transcript_text` for a row.

    - Text paste / manual entry / imported transcript: trust the
      operator-supplied text, validate minimum length, return.
    - Audio upload: hand off to the installed transcriber. Metadata
      (filename / storage URL / duration) comes from
      `source_metadata`; callers that need more detail should parse
      the JSON there.
    """
    input_type = row["input_type"]

    if input_type in {"text_paste", "manual_entry", "imported_transcript"}:
        text = (row.get("transcript_text") or "").strip()
        if len(text) < 10:
            raise TranscriptTooShort(len(text))
        return text

    if input_type == "audio_upload":
        metadata_raw = row.get("source_metadata") or "{}"
        import json
        try:
            metadata = json.loads(metadata_raw)
        except Exception:
            metadata = {}
        text = transcribe_audio(metadata)
        if not isinstance(text, str):
            raise IngestionError(
                "transcriber_contract_violation",
                "transcriber must return str transcript_text",
            )
        if len(text.strip()) < 10:
            raise TranscriptTooShort(len(text.strip()))
        return text

    raise IngestionError(
        "invalid_input_type",
        f"ingestion does not know how to handle input_type={input_type!r}",
    )
