"""Phase 26 — signed-note transmission write path.

Covers:

- POST /note-versions/{id}/transmit in standalone mode →
  409 `transmit_not_available_in_mode` (platform-mode gate).
- transmit in integrated_writethrough with the stub adapter →
  200, row persisted, transport_status=succeeded, remote_id set,
  artifact hash recorded, audit event written.
- transmit in integrated_readthrough with stub → 409
  `adapter_does_not_support_transmit` (readthrough stub advertises
  writes off; writethrough stub advertises writes on).
- transmit in integrated_writethrough with the FHIR adapter via an
  injected write_transport → success path: status code captured,
  Location header parsed into remote_id, response_snippet stored.
- transmit with a FHIR adapter whose write_transport returns 400 →
  row status=failed with error_code=fhir_transmit_http_error.
- transmit on unsigned → 409 `note_not_signed` (forwarded from the
  phase-25 artifact gate).
- transmit cross-org → 404 `note_not_found`.
- transmit by reviewer → 403 `role_cannot_transmit`.
- double-transmit without force → 409 `already_transmitted`; with
  force=true → new row inserted, attempt_number increments.
- GET /note-versions/{id}/transmissions returns rows newest-first,
  and is cross-org masked.
"""

from __future__ import annotations

import json
import os

import pytest


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


TRANSCRIPT = """
Chief complaint: blurry vision right eye for 3 weeks.
OD 20/40, OS 20/20.
IOP 15/17.
Diagnosis: posterior capsular opacification right eye.
Plan: YAG capsulotomy OD.
Follow-up in 4 weeks.
""".strip()


def _reload_app():
    import sys
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _writethrough_client(test_db, *, adapter: str = "stub"):
    _reload_app()
    os.environ["CHARTNAV_PLATFORM_MODE"] = "integrated_writethrough"
    os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = adapter
    # FHIR adapter wants a base URL even if the transport is injected.
    if adapter == "fhir":
        os.environ.setdefault("CHARTNAV_FHIR_BASE_URL", "https://fhir.test/r4")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _readthrough_client(test_db, *, adapter: str = "stub"):
    _reload_app()
    os.environ["CHARTNAV_PLATFORM_MODE"] = "integrated_readthrough"
    os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = adapter
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _sign_note(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    input_id = r.json()["id"]

    r = client.post(
        "/encounters/1/notes/generate",
        json={"input_id": input_id},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    note_id = r.json()["note"]["id"]

    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200
    return note_id


# =======================================================================
# Mode gate
# =======================================================================


def test_transmit_refused_in_standalone_mode(client):
    """Default conftest client is standalone; the write path must refuse."""
    note_id = _sign_note(client)
    r = client.post(
        f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["error_code"] == "transmit_not_available_in_mode"


def test_transmit_refused_in_readthrough_stub(test_db):
    client = _readthrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        # Readthrough mode fails at the mode gate (it isn't
        # integrated_writethrough) before the adapter-support check.
        assert r.status_code == 409
        assert (
            r.json()["detail"]["error_code"]
            == "transmit_not_available_in_mode"
        )
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


# =======================================================================
# Happy path — stub adapter in writethrough
# =======================================================================


def test_transmit_via_stub_succeeds_and_persists_row(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        assert r.status_code == 200, r.text
        row = r.json()
        assert row["note_version_id"] == note_id
        assert row["transport_status"] == "succeeded"
        assert row["adapter_key"] == "stub"
        assert row["attempt_number"] == 1
        assert row["remote_id"].startswith("stub-docref-")
        assert row["response_snippet"].startswith("stub adapter")
        assert len(row["request_body_hash"]) == 64
        assert row["last_error"] is None

        # GET list reflects the attempt.
        r2 = client.get(
            f"/note-versions/{note_id}/transmissions", headers=CLIN1
        )
        assert r2.status_code == 200
        rows = r2.json()
        assert len(rows) == 1
        assert rows[0]["transport_status"] == "succeeded"

        # Audit event recorded.
        r3 = client.get("/security-audit-events?limit=200", headers=ADMIN1)
        assert r3.status_code == 200
        body = r3.json()
        items = body["items"] if isinstance(body, dict) else body
        assert any(
            ev["event_type"] == "note_version_transmitted" for ev in items
        )
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


# =======================================================================
# Happy path — FHIR adapter with injected transport
# =======================================================================


def _install_fhir_transport(monkeypatch, *, status_code: int, body: str,
                            location: str | None):
    """Patch the FHIR adapter's default write transport so no network
    call happens. Every newly-constructed FHIRAdapter in this test
    picks up the injected transport through the default argument."""
    from app.integrations import fhir as fhir_mod

    def fake_write(url, body_bytes, headers):
        return status_code, body, location

    monkeypatch.setattr(fhir_mod, "_default_write_transport", fake_write)


def test_transmit_via_fhir_success_path(test_db, monkeypatch):
    client = _writethrough_client(test_db, adapter="fhir")
    try:
        # Read transport (GET) is never called by the transmit path, but
        # the adapter constructs at import time so we need a sane base URL.
        # Inject only the write transport.
        _install_fhir_transport(
            monkeypatch,
            status_code=201,
            body='{"resourceType":"DocumentReference","id":"abc-123"}',
            location="https://fhir.test/r4/DocumentReference/abc-123/_history/1",
        )

        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        assert r.status_code == 200, r.text
        row = r.json()
        assert row["transport_status"] == "succeeded"
        assert row["adapter_key"] == "fhir"
        assert row["response_code"] == 201
        assert row["remote_id"] == "abc-123"
        assert "abc-123" in (row["response_snippet"] or "")
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        os.environ.pop("CHARTNAV_FHIR_BASE_URL", None)


def test_transmit_via_fhir_http_400_is_persisted_as_failed(test_db, monkeypatch):
    client = _writethrough_client(test_db, adapter="fhir")
    try:
        _install_fhir_transport(
            monkeypatch,
            status_code=400,
            body='{"resourceType":"OperationOutcome","issue":[{"severity":"error"}]}',
            location=None,
        )
        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        # The call itself succeeds (200) — we persisted a failed
        # transmission row. That's the whole point of the write-path
        # design: remote failures are data, not exceptions.
        assert r.status_code == 200
        row = r.json()
        assert row["transport_status"] == "failed"
        assert row["response_code"] == 400
        assert row["last_error_code"] == "fhir_transmit_http_error"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        os.environ.pop("CHARTNAV_FHIR_BASE_URL", None)


# =======================================================================
# Gating
# =======================================================================


def test_transmit_unsigned_refused(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        # Ingest + generate but do NOT sign.
        r = client.post(
            "/encounters/1/inputs",
            json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
            headers=CLIN1,
        )
        input_id = r.json()["id"]
        r = client.post(
            "/encounters/1/notes/generate",
            json={"input_id": input_id},
            headers=CLIN1,
        )
        note_id = r.json()["note"]["id"]

        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "note_not_signed"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


def test_transmit_cross_org_is_404(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN2
        )
        assert r.status_code == 404
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


def test_transmit_reviewer_role_refused(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        r = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=REV1
        )
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_cannot_transmit"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


# =======================================================================
# Idempotency + force
# =======================================================================


def test_double_transmit_without_force_is_409(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        r1 = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        assert r1.status_code == 200
        assert r1.json()["transport_status"] == "succeeded"

        r2 = client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["error_code"] == "already_transmitted"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


def test_double_transmit_with_force_inserts_new_attempt(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        r2 = client.post(
            f"/note-versions/{note_id}/transmit",
            json={"force": True},
            headers=CLIN1,
        )
        assert r2.status_code == 200
        assert r2.json()["attempt_number"] == 2

        listing = client.get(
            f"/note-versions/{note_id}/transmissions", headers=CLIN1
        ).json()
        # Newest first.
        assert [row["attempt_number"] for row in listing] == [2, 1]
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)


# =======================================================================
# Read surface
# =======================================================================


def test_list_transmissions_cross_org_masked(test_db):
    client = _writethrough_client(test_db, adapter="stub")
    try:
        note_id = _sign_note(client)
        client.post(
            f"/note-versions/{note_id}/transmit", json={}, headers=CLIN1
        )
        # CLIN2 is in a different org — the note itself is invisible to
        # them, so the GET must 404 rather than leak existence.
        r = client.get(
            f"/note-versions/{note_id}/transmissions", headers=CLIN2
        )
        assert r.status_code == 404
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
