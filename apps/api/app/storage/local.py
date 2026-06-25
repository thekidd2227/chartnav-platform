"""Filesystem object-storage adapter — DEVELOPMENT ONLY.

Not encrypted at rest by the app, no presigning. Refuses to run when
CHARTNAV_ENV=prod. Production uses S3ObjectStorage.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .base import (
    ObjectStorage,
    StoredObject,
    StorageError,
    derive_key,
    key_belongs_to_org,
)


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: str | None = None):
        if (os.environ.get("CHARTNAV_ENV", "dev") or "dev").lower() == "prod":
            raise StorageError(
                "LocalObjectStorage is dev-only; set CHARTNAV_STORAGE_BACKEND=s3 "
                "in production."
            )
        self.root = Path(root or os.environ.get(
            "CHARTNAV_STORAGE_LOCAL_ROOT", "./object_store")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        # Containment guard: never escape the storage root.
        if not str(p).startswith(str(self.root) + os.sep):
            raise StorageError("resolved path escapes storage root")
        return p

    def put(self, *, organization_id, kind, name, data, content_type,
            expected_sha256=None, metadata=None) -> StoredObject:
        digest = self._validate(data, content_type, expected_sha256)
        key = derive_key(organization_id, kind, name)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        meta = {
            "organization_id": organization_id,
            "content_type": content_type,
            "sha256": digest,
            **(metadata or {}),
        }
        path.with_suffix(path.suffix + ".meta.json").write_text(json.dumps(meta))
        return StoredObject(key=key, organization_id=organization_id,
                            size=len(data), content_type=content_type,
                            sha256=digest, metadata=meta)

    def presigned_get_url(self, *, key, organization_id, expires_seconds=300) -> str:
        if not key_belongs_to_org(key, organization_id):
            raise StorageError("key does not belong to organization")
        # No real presigning locally; return a dev file URL.
        return self._path(key).as_uri()

    def presigned_put_url(self, *, organization_id, kind, name, content_type,
                          expires_seconds=300) -> dict:
        key = derive_key(organization_id, kind, name)
        return {"url": self._path(key).as_uri(), "key": key, "method": "PUT",
                "note": "local dev adapter — no real presigning"}

    def delete(self, *, key, organization_id) -> None:
        if not key_belongs_to_org(key, organization_id):
            raise StorageError("key does not belong to organization")
        path = self._path(key)
        if path.exists():
            path.unlink()
        meta = path.with_suffix(path.suffix + ".meta.json")
        if meta.exists():
            meta.unlink()
