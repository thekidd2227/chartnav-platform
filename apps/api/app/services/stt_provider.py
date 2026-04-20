"""Speech-to-text provider seam (phase 35).

Two real, honest providers ship in-tree. They both implement the
same `STTProvider` Protocol and plug into the existing
`app.services.ingestion.set_transcriber(...)` registry — a vendor
adapter is never more than one `set_transcriber` call away.

Providers shipped today
-----------------------
- `StubSTTProvider` — wraps the phase-33 deterministic stub
  (`stub_transcribe`). Used by tests + dev.
- `OpenAIWhisperProvider` — calls OpenAI's
  `POST /v1/audio/transcriptions` endpoint with the configured
  model (default `whisper-1`). Reads bytes from the storage
  backend (NEVER from a hard-coded local path), uploads them as
  multipart form-data, returns the transcript text. Failure modes
  (401/403/429/5xx, timeouts, connection drops) come back as a
  clean `IngestionError` with a stable `error_code` so the
  pipeline can persist + retry honestly.

Selection
---------
`select_default_provider(settings)` reads
`CHARTNAV_STT_PROVIDER`:
- unset / `stub` → `StubSTTProvider`
- `openai_whisper` → `OpenAIWhisperProvider` (requires
  `CHARTNAV_OPENAI_API_KEY`; failure to find it is a
  configuration error and we **fail loud** — we do not silently
  downgrade to the stub, because that would let a misconfigured
  prod deployment ship fake transcripts under the
  `[stub-transcript]` marker without anyone noticing).
- `none` → installs the phase-22 `_not_implemented_transcriber`
  so audio uploads fail with `audio_transcription_not_implemented`
  (useful for staging environments that explicitly forbid STT).
- anything else → `RuntimeError` at boot time.

A real vendor adapter (Deepgram, Speechmatics, Azure Speech, Google
Speech-to-Text, AWS Transcribe, …) implements `STTProvider`,
registers itself by name in `_PROVIDER_FACTORIES`, and the same
`CHARTNAV_STT_PROVIDER=<name>` selector picks it up.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Protocol

from app.services.audio_storage import (
    AudioStorage,
    StorageError,
    StorageRef,
    resolve_storage,
)
from app.services.ingestion import (
    IngestionError,
    _not_implemented_transcriber,
    set_transcriber,
)

log = logging.getLogger("chartnav.stt")


class STTProvider(Protocol):
    """Implementations turn an audio `StorageRef` into transcript text."""

    name: str

    def transcribe(self, *, storage_ref: StorageRef, metadata: dict[str, Any]) -> str:
        ...


# ---------------------------------------------------------------------------
# Stub provider (test + dev)
# ---------------------------------------------------------------------------

class StubSTTProvider:
    """Wraps the phase-33 deterministic stub.

    Honours `metadata["stub_transcript"]` for canned text, raises
    `StubTranscriberError` on `metadata["stub_transcript_error"]`,
    otherwise returns an honestly-labelled `[stub-transcript]`
    placeholder. See `app/services/audio_transcriber.py` for the
    full contract — this provider just delegates so test code can
    keep the same headers + metadata shape it already uses.
    """

    name = "stub"

    def transcribe(self, *, storage_ref: StorageRef, metadata: dict[str, Any]) -> str:
        # Phase 35 thread-through: future stub-aware test harnesses
        # may want to know the storage scheme; pass it through in
        # the transcriber metadata dict but don't require the stub
        # to read it.
        from app.services.audio_transcriber import stub_transcribe
        merged = dict(metadata)
        if "scheme" not in merged and storage_ref.get("scheme"):
            merged["scheme"] = storage_ref["scheme"]
        return stub_transcribe(merged)


# ---------------------------------------------------------------------------
# OpenAI Whisper provider
# ---------------------------------------------------------------------------

OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "whisper-1"
OPENAI_DEFAULT_TIMEOUT_S = 120
OPENAI_TRANSCRIPT_BYTES_LIMIT = 25 * 1024 * 1024  # vendor-side cap


# A pluggable HTTP transport so tests can drive the provider without
# real network I/O. Signature: (url, body_bytes, headers, timeout)
# returning (status_code: int, response_body: bytes). Mirrors the
# pattern phase-26 introduced for the FHIR adapter.
WhisperTransport = Callable[[str, bytes, dict[str, str], int], "tuple[int, bytes]"]


def _default_whisper_transport(
    url: str, body: bytes, headers: dict[str, str], timeout: int
) -> "tuple[int, bytes]":
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            body_bytes = e.read()
        except Exception:
            body_bytes = (e.reason or "").encode("utf-8", errors="replace")
        return int(e.code), body_bytes
    except urllib.error.URLError as e:
        # DNS / connection-level failures are *not* a vendor "no" —
        # they're transport failures. Surface as a distinct error
        # code so the pipeline can decide between retry and surface-
        # to-UI.
        raise IngestionError(
            "openai_whisper_transport_error",
            f"could not reach {url}: {e.reason}",
        ) from e


class OpenAIWhisperProvider:
    """Real OpenAI Whisper adapter.

    Reads bytes from the storage backend (`storage_ref` → `bytes`),
    builds a multipart/form-data request, POSTs it to the OpenAI
    audio transcription endpoint, returns the `text` field of the
    JSON response.

    Honestly fails on:
    - missing API key (caught at construction time, not at request)
    - storage read failure (surfaces the storage error code)
    - HTTP 4xx/5xx from OpenAI (returns a clean `error_code`
      naming the upstream status)
    - vendor body that doesn't carry a `text` field
    """

    name = "openai_whisper"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: int | None = None,
        api_base: str | None = None,
        storage: AudioStorage | None = None,
        transport: WhisperTransport | None = None,
    ):
        self._api_key = api_key or os.environ.get("CHARTNAV_OPENAI_API_KEY")
        self._model = model or os.environ.get("CHARTNAV_STT_MODEL") or OPENAI_DEFAULT_MODEL
        try:
            self._timeout_s = int(
                timeout_s
                if timeout_s is not None
                else (os.environ.get("CHARTNAV_STT_TIMEOUT_S")
                      or OPENAI_DEFAULT_TIMEOUT_S)
            )
        except (TypeError, ValueError):
            raise RuntimeError(
                "CHARTNAV_STT_TIMEOUT_S must be an integer (seconds)"
            )
        self._api_base = (
            api_base
            or os.environ.get("CHARTNAV_OPENAI_API_BASE")
            or OPENAI_API_BASE
        ).rstrip("/")
        self._storage = storage
        self._transport: WhisperTransport = transport or _default_whisper_transport

        if not self._api_key:
            # Fail loud at construction — `select_default_provider`
            # routes around this only if the operator explicitly
            # configured `CHARTNAV_STT_PROVIDER=stub`. Silently
            # downgrading would mean a prod deployment ships
            # `[stub-transcript]` placeholders signed by clinicians.
            raise RuntimeError(
                "CHARTNAV_STT_PROVIDER=openai_whisper requires "
                "CHARTNAV_OPENAI_API_KEY. Set the env var or switch "
                "to CHARTNAV_STT_PROVIDER=stub explicitly."
            )

    # ------- storage helper -------
    def _read_bytes(self, storage_ref: StorageRef) -> bytes:
        storage = self._storage or resolve_storage()
        try:
            return storage.open(storage_ref)
        except StorageError as e:
            raise IngestionError(e.error_code, e.reason) from e

    # ------- multipart body -------
    def _build_multipart(
        self, *, audio: bytes, filename: str, content_type: str
    ) -> "tuple[bytes, str]":
        boundary = f"----chartnav-{uuid.uuid4().hex}"
        sep = f"--{boundary}".encode("ascii")
        end = f"--{boundary}--".encode("ascii")
        crlf = b"\r\n"
        parts = [
            sep,
            b'Content-Disposition: form-data; name="model"',
            b"",
            self._model.encode("utf-8"),
            sep,
            b'Content-Disposition: form-data; name="response_format"',
            b"",
            b"json",
            sep,
            (
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{filename}"'
            ).encode("utf-8"),
            f"Content-Type: {content_type}".encode("utf-8"),
            b"",
            audio,
            end,
            b"",  # trailing CRLF
        ]
        body = crlf.join(parts)
        return body, f"multipart/form-data; boundary={boundary}"

    # ------- public surface -------
    def transcribe(self, *, storage_ref: StorageRef, metadata: dict[str, Any]) -> str:
        audio = self._read_bytes(storage_ref)
        if len(audio) == 0:
            raise IngestionError(
                "openai_whisper_empty_audio",
                "stored audio is empty; nothing to transcribe",
            )
        if len(audio) > OPENAI_TRANSCRIPT_BYTES_LIMIT:
            # Vendor-side cap — fail clearly rather than letting
            # OpenAI 413 us mid-flight after a long upload.
            raise IngestionError(
                "openai_whisper_audio_too_large",
                (
                    f"audio is {len(audio)} bytes; OpenAI Whisper caps "
                    f"transcription input at {OPENAI_TRANSCRIPT_BYTES_LIMIT} bytes"
                ),
            )

        filename = (
            metadata.get("original_filename")
            or metadata.get("filename")
            or "audio.bin"
        )
        content_type = (
            metadata.get("content_type")
            or "application/octet-stream"
        )

        body, ct_header = self._build_multipart(
            audio=audio, filename=filename, content_type=content_type,
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": ct_header,
        }
        url = f"{self._api_base}/audio/transcriptions"

        status_code, resp_body = self._transport(
            url, body, headers, self._timeout_s
        )

        if not (200 <= status_code < 300):
            snippet = resp_body[:512].decode("utf-8", errors="replace")
            log.warning(
                "openai_whisper non-2xx status=%s snippet=%r",
                status_code, snippet,
            )
            raise IngestionError(
                "openai_whisper_http_error",
                (
                    f"OpenAI Whisper returned HTTP {status_code}; "
                    f"body excerpt: {snippet}"
                ),
            )

        try:
            payload = json.loads(resp_body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            raise IngestionError(
                "openai_whisper_invalid_response",
                f"OpenAI Whisper returned non-JSON body: {e}",
            )
        text = payload.get("text") if isinstance(payload, dict) else None
        if not isinstance(text, str):
            raise IngestionError(
                "openai_whisper_missing_text",
                "OpenAI Whisper response did not include a `text` field",
            )
        return text


# ---------------------------------------------------------------------------
# Selector + bootstrap
# ---------------------------------------------------------------------------

# Vendor adapters register themselves here at import time. The
# `select_default_provider()` function reads `CHARTNAV_STT_PROVIDER`
# and instantiates by name. Adding a new provider is a one-line
# `_PROVIDER_FACTORIES["my_vendor"] = lambda: MyVendorProvider()`
# from the vendor's adapter module.
_PROVIDER_FACTORIES: dict[str, Callable[[], STTProvider]] = {
    "stub": lambda: StubSTTProvider(),
    "openai_whisper": lambda: OpenAIWhisperProvider(),
}


def select_default_provider(provider_key: str | None = None) -> STTProvider | None:
    """Resolve the configured STT provider.

    Returns:
        - an `STTProvider` instance, OR
        - `None` when the operator explicitly configured `none`
          (caller should install `_not_implemented_transcriber`).

    Raises:
        - `RuntimeError` for an unknown provider key. Better to
          fail boot than to silently fall back to the stub.
    """
    key = (provider_key or os.environ.get("CHARTNAV_STT_PROVIDER") or "stub").lower()
    if key == "none":
        return None
    factory = _PROVIDER_FACTORIES.get(key)
    if factory is None:
        raise RuntimeError(
            f"CHARTNAV_STT_PROVIDER={key!r} is not a registered provider. "
            f"Known: {sorted(_PROVIDER_FACTORIES)} or 'none'."
        )
    return factory()


def install_provider(provider: STTProvider | None) -> None:
    """Wire `provider.transcribe(...)` into the ingestion seam.

    The ingestion service expects a single callable
    `transcribe(metadata: dict) -> str`. We adapt the new
    storage-aware Provider Protocol to the legacy signature here so
    the rest of the pipeline doesn't need to change. The adapter
    extracts `storage_ref` from metadata and hands both pieces to
    the provider.
    """
    if provider is None:
        set_transcriber(_not_implemented_transcriber)
        log.info("stt provider: NONE (audio uploads will fail honestly)")
        return

    def _transcribe(metadata: dict[str, Any]) -> str:
        storage_ref = metadata.get("storage_ref")
        if not isinstance(storage_ref, dict):
            # Backwards-compat: phase-33 stored only `stored_path`.
            # Synthesize a file-scheme StorageRef so the new
            # provider seam works against legacy rows.
            stored_path = metadata.get("stored_path")
            if isinstance(stored_path, str) and stored_path:
                storage_ref = {
                    "scheme": "file",
                    "uri": stored_path,
                    "size_bytes": metadata.get("size_bytes"),
                    "content_type": metadata.get("content_type"),
                }
            else:
                # Stub provider doesn't care; non-stub providers will
                # fail clearly below when they try to read.
                storage_ref = {"scheme": "none"}
        return provider.transcribe(
            storage_ref=storage_ref, metadata=metadata,
        )

    set_transcriber(_transcribe)
    log.info("stt provider: %s", provider.name)


def install_default() -> None:
    """Phase 35 bootstrap entry-point.

    Resolves the configured provider and wires it into the ingestion
    seam. Safe to call from `app.main` at import time. A vendor
    adapter that wants to override can call `install_provider(...)`
    later.
    """
    provider = select_default_provider()
    install_provider(provider)
