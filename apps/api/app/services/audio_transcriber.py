"""Audio-transcription adapter seam (phase 33).

The ingestion pipeline (phase 22) already exposes a single pluggable
function — `app.services.ingestion.set_transcriber(fn)`. This module
is the narrow, honest default implementation that ships in-tree.

Why this exists:
- Before phase 33, `audio_upload` rows that reached `processing`
  blew up with `audio_transcription_not_implemented` because the
  default transcriber was `_not_implemented_transcriber`. That was
  correct — ChartNav must not pretend STT is wired when it isn't.
- Phase 33 adds real audio intake (multipart file upload) + a real
  job-lifecycle wedge around audio. We still do NOT have a
  production STT vendor integrated — that's an explicit follow-on.
  So this module ships a deterministic, grep-able **stub**
  transcriber that emits an honest placeholder transcript plus a
  provenance marker. It's good enough for tests, for dogfood
  workflows, and for exercising the end-to-end pipeline without
  lying about vendor capability.

Swap-out contract:
- A real deployment calls
  `app.services.audio_transcriber.install_default()` at startup to
  wire this stub OR
  `app.services.ingestion.set_transcriber(real_fn)` to install a
  vendor-specific STT callable.
- The function signature is stable: `(metadata: dict) -> str`.
- Metadata is the JSON-decoded `encounter_inputs.source_metadata`
  dict as stored at upload time. A real adapter inspects
  `stored_path` (or `storage_url` for S3-like adapters) and calls
  whatever STT service is configured.

Test adapter:
- `stub_transcript` in metadata short-circuits the placeholder and
  returns the exact string — tests seed this to drive deterministic
  queued → completed transitions without needing to read a WAV file.
- `stub_transcript_error` in metadata forces a failed-ingestion
  outcome with a clean error code, so failed/retry tests don't
  depend on corrupt-audio fixtures.

Provenance:
- The placeholder transcript always starts with the literal prefix
  `[stub-transcript]` so downstream consumers (the note artifact,
  the audit log, a human reviewer) can see immediately that this
  text did NOT come from a real STT engine. The doctor-facing
  review screen surfaces the same marker so nobody accidentally
  signs a fake transcript as attested clinical content.
"""

from __future__ import annotations

from typing import Any

from app.services.ingestion import IngestionError, set_transcriber


STUB_TRANSCRIPT_PREFIX = "[stub-transcript]"


class StubTranscriberError(IngestionError):
    """Stub-forced transcription failure for deterministic failure tests."""

    def __init__(self, reason: str):
        super().__init__("stub_transcription_failed", reason)


def stub_transcribe(metadata: dict[str, Any]) -> str:
    """Deterministic, test-friendly audio transcriber.

    Decision table (first match wins):

    1. `metadata["stub_transcript_error"]` present → raise
       `StubTranscriberError` with that reason. Drives the `failed`
       state-machine test without needing a corrupted binary fixture.
    2. `metadata["stub_transcript"]` is a non-empty string →
       return it verbatim. Drives the happy-path queued → processing
       → completed tests.
    3. Otherwise return an honest placeholder that names the
       uploaded file + size so the operator knows *something* real
       landed on disk, but the prefix makes it unambiguous that this
       is not live STT output.

    Minimum length is enforced at the ingestion layer
    (`TranscriptTooShort` ≥ 10 chars). All three branches above
    return strings well above that threshold.
    """
    err = metadata.get("stub_transcript_error")
    if isinstance(err, str) and err.strip():
        raise StubTranscriberError(err.strip())

    canned = metadata.get("stub_transcript")
    if isinstance(canned, str) and canned.strip():
        return canned.strip()

    # Prefer the clinician-facing `original_filename` (the name the
    # doctor saw when uploading) over the UUID-named `filename` (the
    # on-disk storage name). Audit legibility > storage detail.
    filename = (
        metadata.get("original_filename")
        or metadata.get("filename")
        or "<unnamed>"
    )
    size = metadata.get("size_bytes") or metadata.get("size")
    content_type = metadata.get("content_type") or "audio/unknown"
    size_note = f"{size} bytes" if isinstance(size, int) else "size unknown"
    return (
        f"{STUB_TRANSCRIPT_PREFIX} Audio ingested but no production "
        f"STT provider is wired in this deployment. File metadata: "
        f"{filename} ({content_type}, {size_note}). The clinician "
        f"must paste or dictate the actual transcript before note "
        f"generation."
    )


def install_default() -> None:
    """Install the stub transcriber at app bootstrap.

    Called from `app.main` at import time. A vendor adapter can
    re-install itself after this by calling `set_transcriber(...)`
    again — the last call wins. Keeping this explicit + grep-able
    beats a decorator-based registry because the swap-out is always
    one obvious line of code.
    """
    set_transcriber(stub_transcribe)
