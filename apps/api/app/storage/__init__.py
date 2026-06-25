"""Object storage abstraction for ChartNav.

A small, server-controlled storage layer so clinical artifacts (imaging,
exports, attachments) never live in PostgreSQL and are always organization-
scoped, size/type-limited, checksum-verified, and audited at the call site.

Adapters:
  - LocalObjectStorage  — filesystem, DEVELOPMENT ONLY.
  - S3ObjectStorage      — Amazon S3 with KMS encryption, presigned URLs,
                           public-access blocked (staging/production).

Object keys are ALWAYS derived server-side from (organization_id, kind, name);
callers never supply raw keys, so a tenant can never address another tenant's
prefix. See docs/security/object-storage.md.
"""
from __future__ import annotations

from .base import (
    ObjectStorage,
    StoredObject,
    StorageError,
    ContentTypeNotAllowed,
    ObjectTooLarge,
    ChecksumMismatch,
    DEFAULT_ALLOWED_CONTENT_TYPES,
)
from .local import LocalObjectStorage


def get_object_storage(settings) -> ObjectStorage:
    """Factory: pick the adapter from settings.

    settings.storage_backend in {"local", "s3"}. 's3' requires bucket + KMS
    key id; 'local' is dev-only.
    """
    backend = getattr(settings, "storage_backend", "local")
    if backend == "s3":
        from .s3 import S3ObjectStorage
        return S3ObjectStorage(
            bucket=settings.s3_bucket,
            kms_key_id=settings.s3_kms_key_id,
            region=getattr(settings, "aws_region", None),
        )
    if backend == "local":
        return LocalObjectStorage(root=getattr(settings, "storage_local_root", None))
    raise StorageError(f"unknown storage backend: {backend!r}")


__all__ = [
    "ObjectStorage", "StoredObject", "StorageError", "ContentTypeNotAllowed",
    "ObjectTooLarge", "ChecksumMismatch", "DEFAULT_ALLOWED_CONTENT_TYPES",
    "LocalObjectStorage", "get_object_storage",
]
