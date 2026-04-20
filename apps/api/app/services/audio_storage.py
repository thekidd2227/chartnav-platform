"""Audio storage abstraction (phase 35).

Decouples the upload handler from "where exactly the bytes live" so
ChartNav can run on local disk in dev/test and graduate to S3-class
object storage without touching the upload contract or the
transcriber adapter.

A `StorageRef` is the only thing the rest of the system stores in
`encounter_inputs.source_metadata.storage_ref`. The transcriber, the
worker, and any future cleanup job ask the storage backend to
materialise the bytes again — they never touch raw filesystem paths
themselves.

Three principles:

1. **Opaque reference, not a path.** A `StorageRef` carries a
   `scheme` ("file" / "s3" / vendor) plus enough fields for that
   scheme to round-trip via `open(ref)`. Callers never assume
   `ref["uri"]` is a filesystem path.

2. **Honest backends only.** `LocalDiskStorage` is real and ships
   today. `S3Storage` etc. are explicitly NOT in this phase — when
   they land they implement the same `AudioStorage` Protocol and
   the upload route picks them up via `resolve_storage()`.

3. **Backwards compatibility with phase 33.** The pre-phase-35 code
   stored `stored_path` directly. We continue to write
   `stored_path` alongside `storage_ref` so any reader (audit,
   downstream tools) that still expects the legacy field keeps
   working. New readers should prefer `storage_ref`.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any, Protocol


class StorageError(RuntimeError):
    """Raised when a storage backend can't fulfil a put/open."""

    def __init__(self, error_code: str, reason: str):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason


# A `StorageRef` is a JSON-serialisable dict. Schemes shipped today:
#   {"scheme": "file", "uri": "/abs/path/to/file.wav", "size_bytes": 1234}
#
# Future schemes (NOT in this phase, listed for the seam contract):
#   {"scheme": "s3",   "bucket": "...", "key": "...", "size_bytes": 1234}
#   {"scheme": "gcs",  "bucket": "...", "key": "...", "size_bytes": 1234}
#   {"scheme": "blob", "container": "...", "path": "...", "size_bytes": 1234}
StorageRef = dict[str, Any]


class AudioStorage(Protocol):
    """Storage backend for raw audio bytes.

    Every backend exposes the same two operations. The opaque
    `StorageRef` lets the rest of the system pass references around
    without leaking backend specifics.
    """

    scheme: str

    def put(
        self,
        *,
        encounter_id: int,
        ext: str,
        body: bytes,
        content_type: str,
    ) -> StorageRef:
        """Persist `body` and return a backend-specific reference."""
        ...

    def open(self, ref: StorageRef) -> bytes:
        """Materialise the bytes referenced by `ref`."""
        ...


# ---------------------------------------------------------------------------
# Local-disk implementation (dev/test default)
# ---------------------------------------------------------------------------

class LocalDiskStorage:
    """File-system backend.

    Default in dev / test / CI. Path layout:
        <root>/<encounter_id>/<random>.<ext>

    `<random>` is a hex token so the on-disk filename is detached
    from the original upload name (no PHI leakage into the
    filesystem). The original name stays in
    `source_metadata.original_filename` for audit.
    """

    scheme = "file"

    def __init__(self, root: Path):
        self._root = Path(root)
        # Defer mkdir until first put — keeps `__init__` cheap and
        # safe to call from request hot paths.

    def put(
        self,
        *,
        encounter_id: int,
        ext: str,
        body: bytes,
        content_type: str,
    ) -> StorageRef:
        encounter_dir = self._root / str(encounter_id)
        encounter_dir.mkdir(parents=True, exist_ok=True)
        stored_ext = ext or ".bin"
        name = f"{secrets.token_hex(8)}{stored_ext}"
        target = encounter_dir / name
        try:
            target.write_bytes(bytes(body))
        except OSError as e:
            raise StorageError(
                "audio_storage_write_failed",
                f"could not write {target}: {e}",
            ) from e
        return {
            "scheme": "file",
            "uri": str(target.resolve()),
            "size_bytes": len(body),
            "content_type": content_type,
        }

    def open(self, ref: StorageRef) -> bytes:
        if ref.get("scheme") != "file":
            raise StorageError(
                "audio_storage_scheme_mismatch",
                f"LocalDiskStorage cannot open scheme={ref.get('scheme')!r}",
            )
        uri = ref.get("uri")
        if not isinstance(uri, str) or not uri:
            raise StorageError(
                "audio_storage_invalid_ref",
                "file-scheme storage_ref missing 'uri'",
            )
        path = Path(uri)
        if not path.exists():
            raise StorageError(
                "audio_storage_not_found",
                f"audio file no longer exists at {uri}",
            )
        try:
            return path.read_bytes()
        except OSError as e:
            raise StorageError(
                "audio_storage_read_failed",
                f"could not read {uri}: {e}",
            ) from e


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

_storage_singleton: AudioStorage | None = None


def resolve_storage() -> AudioStorage:
    """Pick the configured storage backend.

    Today we ship `LocalDiskStorage` only. The resolver shape is
    here so a future S3 / GCS / blob backend slots in without
    touching the upload route. Cached after the first call so
    repeated requests don't re-resolve config.
    """
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    from app.config import settings

    root = Path(settings.audio_upload_dir)
    if not root.is_absolute():
        # Resolve relative to the API package root so different CWDs
        # (tests, prod, docker) land in the same place. Matches the
        # phase-33 _audio_upload_root() behaviour for byte-for-byte
        # back-compat with files written before this phase.
        root = (
            Path(__file__).resolve().parents[2]
            / settings.audio_upload_dir
        )
    root.mkdir(parents=True, exist_ok=True)
    _storage_singleton = LocalDiskStorage(root=root)
    return _storage_singleton


def reset_storage_for_tests() -> None:
    """Drop the cached singleton so a test that reconfigures the
    `audio_upload_dir` env can pick up the new path on the next call.
    Production code never touches this."""
    global _storage_singleton
    _storage_singleton = None


def storage_ref_to_legacy_path(ref: StorageRef) -> str | None:
    """Best-effort translate a `StorageRef` back into a filesystem
    path string for back-compat with code that still expects
    `source_metadata.stored_path`. Returns None for non-file schemes.
    """
    if ref.get("scheme") == "file":
        uri = ref.get("uri")
        if isinstance(uri, str):
            return uri
    return None
