"""Object-storage abstraction tests (local adapter + server-controlled keys)."""
from __future__ import annotations

import hashlib

import pytest

from app.storage import LocalObjectStorage
from app.storage.base import (
    ContentTypeNotAllowed,
    ObjectTooLarge,
    ChecksumMismatch,
    StorageError,
    derive_key,
    key_belongs_to_org,
)


def _store(tmp_path):
    return LocalObjectStorage(root=str(tmp_path / "store"))


def test_keys_are_org_scoped_and_server_controlled():
    k = derive_key(7, "imaging", "fundus OD.png")
    assert k == "org/7/imaging/fundus-OD.png"
    assert key_belongs_to_org(k, 7)
    assert not key_belongs_to_org(k, 8)


def test_key_traversal_is_defused():
    k = derive_key(3, "exports", "../../etc/passwd")
    assert k.startswith("org/3/exports/")
    assert ".." not in k


def test_put_get_roundtrip(tmp_path):
    s = _store(tmp_path)
    data = b"%PDF-1.4 fake"
    obj = s.put(organization_id=1, kind="exports", name="report.pdf",
                data=data, content_type="application/pdf")
    assert obj.key == "org/1/exports/report.pdf"
    assert obj.sha256 == hashlib.sha256(data).hexdigest()
    assert obj.organization_id == 1
    url = s.presigned_get_url(key=obj.key, organization_id=1)
    assert url.startswith("file://")


def test_cross_org_access_is_refused(tmp_path):
    s = _store(tmp_path)
    obj = s.put(organization_id=1, kind="exports", name="r.pdf",
                data=b"%PDF", content_type="application/pdf")
    with pytest.raises(StorageError):
        s.presigned_get_url(key=obj.key, organization_id=2)
    with pytest.raises(StorageError):
        s.delete(key=obj.key, organization_id=2)


def test_content_type_allowlist(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ContentTypeNotAllowed):
        s.put(organization_id=1, kind="x", name="a.exe", data=b"MZ",
              content_type="application/x-dosexec")


def test_size_limit(tmp_path):
    s = _store(tmp_path)
    s.max_bytes = 8
    with pytest.raises(ObjectTooLarge):
        s.put(organization_id=1, kind="x", name="big.txt",
              data=b"0123456789", content_type="text/plain")


def test_checksum_verification(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ChecksumMismatch):
        s.put(organization_id=1, kind="x", name="a.txt", data=b"hello",
              content_type="text/plain", expected_sha256="deadbeef")


def test_local_refuses_prod(monkeypatch, tmp_path):
    monkeypatch.setenv("CHARTNAV_ENV", "prod")
    with pytest.raises(StorageError):
        LocalObjectStorage(root=str(tmp_path / "store"))
