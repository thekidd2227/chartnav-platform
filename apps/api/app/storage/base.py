"""Object storage contract + shared guards (server-controlled keys)."""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

MAX_BYTES_DEFAULT = 50 * 1024 * 1024  # 50 MiB

DEFAULT_ALLOWED_CONTENT_TYPES = frozenset({
    "application/pdf",
    "image/png", "image/jpeg", "image/webp", "image/tiff",
    "application/dicom",
    "text/csv", "text/plain",
    "application/json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class StorageError(Exception):
    pass


class ContentTypeNotAllowed(StorageError):
    pass


class ObjectTooLarge(StorageError):
    pass


class ChecksumMismatch(StorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    key: str
    organization_id: int
    size: int
    content_type: str
    sha256: str
    metadata: dict = field(default_factory=dict)


def derive_key(organization_id: int, kind: str, name: str) -> str:
    """Server-controlled, organization-scoped object key.

    Format: ``org/<organization_id>/<kind>/<safe-name>``. Callers never pass a
    raw key; the org prefix makes cross-tenant addressing impossible.
    """
    if not isinstance(organization_id, int) or organization_id <= 0:
        raise StorageError("organization_id must be a positive int")
    kind_safe = _SAFE_NAME.sub("-", kind).strip("-") or "object"
    name_safe = _SAFE_NAME.sub("-", name).strip("-") or "object"
    # Defuse traversal explicitly even though the regex already strips slashes.
    name_safe = name_safe.replace("..", "-")
    return f"org/{organization_id}/{kind_safe}/{name_safe}"


def key_belongs_to_org(key: str, organization_id: int) -> bool:
    return key.startswith(f"org/{organization_id}/")


class ObjectStorage(ABC):
    """Base contract. Implementations enforce encryption + access control."""

    allowed_content_types: frozenset = DEFAULT_ALLOWED_CONTENT_TYPES
    max_bytes: int = MAX_BYTES_DEFAULT

    def _validate(self, data: bytes, content_type: str,
                  expected_sha256: str | None) -> str:
        if content_type not in self.allowed_content_types:
            raise ContentTypeNotAllowed(content_type)
        if len(data) > self.max_bytes:
            raise ObjectTooLarge(f"{len(data)} > {self.max_bytes}")
        digest = hashlib.sha256(data).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise ChecksumMismatch(f"{digest} != {expected_sha256}")
        return digest

    @abstractmethod
    def put(self, *, organization_id: int, kind: str, name: str, data: bytes,
            content_type: str, expected_sha256: str | None = None,
            metadata: dict | None = None) -> StoredObject:
        ...

    @abstractmethod
    def presigned_get_url(self, *, key: str, organization_id: int,
                          expires_seconds: int = 300) -> str:
        ...

    @abstractmethod
    def presigned_put_url(self, *, organization_id: int, kind: str, name: str,
                          content_type: str, expires_seconds: int = 300) -> dict:
        ...

    @abstractmethod
    def delete(self, *, key: str, organization_id: int) -> None:
        ...
