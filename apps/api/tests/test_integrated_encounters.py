"""Phase 20 — adapter-driven encounter reads + integrated write gating.

Covers:
- standalone mode: /encounters + /encounters/{id} keep native semantics;
  rows carry `_source: "chartnav"`.
- integrated_readthrough + stub: /encounters returns the stub's canned
  rows with `_source: "stub"`; /encounters/{id} fetches via adapter.
- integrated_readthrough: every encounter mutation path refuses
  with a specific error code (encounter_write_unsupported /
  adapter_write_not_supported / native_write_disabled_in_integrated_mode).
- integrated_writethrough + stub: status write dispatches through
  the adapter (stub records it in-process).
- integrated_writethrough + fhir: status write raises
  AdapterNotSupported → 501 adapter_write_not_supported.
- Encounter list honors status filter in integrated mode.
- workflow events still writable in integrated modes (ChartNav-native).
- RBAC + org scoping still enforced.
"""
from __future__ import annotations

import importlib
import os
from contextlib import contextmanager


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}


@contextmanager
def _env(**kv):
    prev = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _reload_app():
    """Drop cached app.* modules so the next import re-reads env."""
    import sys
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


# ---------------------------------------------------------------------
# Standalone (unchanged contract, now tagged with _source)
# ---------------------------------------------------------------------

def test_standalone_list_has_chartnav_source_tag(client):
    r = client.get("/encounters", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    for row in rows:
        assert row["_source"] == "chartnav"
        assert row["organization_id"] == 1


def test_standalone_detail_has_chartnav_source_tag(client):
    r = client.get("/encounters/1", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["_source"] == "chartnav"
    assert body["id"] == 1


# ---------------------------------------------------------------------
# Integrated readthrough + stub
# ---------------------------------------------------------------------

def _integrated_client(test_db, mode: str, adapter: str = "stub"):
    """Build a fresh TestClient under an integrated mode.

    test_db sets DATABASE_URL; we set the platform mode BEFORE
    importing app.main so app.config.settings picks it up.
    """
    _reload_app()
    os.environ["CHARTNAV_PLATFORM_MODE"] = mode
    os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = adapter
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_integrated_readthrough_list_dispatches_to_stub_adapter(
    test_db, monkeypatch
):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.get("/encounters", headers=ADMIN1)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert len(rows) == 2
        assert {row["_source"] for row in rows} == {"stub"}
        assert {row["patient_identifier"] for row in rows} == {
            "EXT-1001", "EXT-1002",
        }
        assert r.headers.get("X-Total-Count") == "2"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_readthrough_detail_dispatches_to_stub_adapter(
    test_db, monkeypatch
):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.get("/encounters/ENC-X", headers=ADMIN1)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["_source"] == "stub"
        assert body["_external_ref"] == "ENC-X"
        # HTTP layer stamps caller's org for UI scoping.
        assert body["organization_id"] == 1
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_readthrough_refuses_encounter_creation(
    test_db, monkeypatch
):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.post(
            "/encounters",
            json={
                "organization_id": 1,
                "location_id": 1,
                "patient_identifier": "PT-NEW",
                "patient_name": "Nope",
                "provider_name": "Dr. Nope",
                "status": "scheduled",
            },
            headers=ADMIN1,
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "encounter_write_unsupported"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_readthrough_refuses_status_update(test_db, monkeypatch):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.post(
            "/encounters/1/status",
            json={"status": "draft_ready"},
            headers=CLIN1,
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "encounter_write_unsupported"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_mode_allows_workflow_event_write(test_db, monkeypatch):
    """workflow_events are ChartNav-native tracking; allowed in every mode."""
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.post(
            "/encounters/1/events",
            json={"event_type": "manual_note", "event_data": {"note": "hi"}},
            headers=CLIN1,
        )
        assert r.status_code == 201, r.text
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Integrated writethrough
# ---------------------------------------------------------------------

def test_integrated_writethrough_stub_allows_status_write(
    test_db, monkeypatch
):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_writethrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_writethrough")
    try:
        r = client.post(
            "/encounters/1/status",
            json={"status": "draft_ready"},
            headers=CLIN1,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "draft_ready"
        assert body["source"] == "stub"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_writethrough_fhir_refuses_status_write(
    test_db, monkeypatch
):
    """Generic FHIR adapter raises AdapterNotSupported → 501 adapter_write_not_supported."""
    monkeypatch.setenv("CHARTNAV_FHIR_BASE_URL", "https://example.org/fhir")
    client = _integrated_client(test_db, "integrated_writethrough", adapter="fhir")
    try:
        r = client.post(
            "/encounters/1/status",
            json={"status": "draft_ready"},
            headers=CLIN1,
        )
        assert r.status_code == 501
        assert (
            r.json()["detail"]["error_code"]
            == "adapter_write_not_supported"
        )
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        os.environ.pop("CHARTNAV_FHIR_BASE_URL", None)
        _reload_app()


# ---------------------------------------------------------------------
# FHIR adapter — list_encounters normalization via fixture transport
# ---------------------------------------------------------------------

def test_fhir_list_encounters_normalizes_bundle():
    with _env(
        CHARTNAV_FHIR_BASE_URL="https://example.org/fhir",
    ):
        _reload_app()
        from app.integrations.fhir import FHIRAdapter

        calls: list[str] = []

        def transport(url: str, headers: dict[str, str]):
            calls.append(url)
            return {
                "resourceType": "Bundle",
                "total": 1,
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Encounter",
                            "id": "enc-42",
                            "status": "in-progress",
                            "subject": {"reference": "Patient/pt-7"},
                            "participant": [
                                {"individual": {"display": "Dr. Carter"}}
                            ],
                            "period": {"start": "2026-04-18T10:00:00Z"},
                        }
                    }
                ],
            }

        adapter = FHIRAdapter(
            base_url="https://example.org/fhir",
            transport=transport,
        )
        res = adapter.list_encounters(
            organization_id=42, status="in_progress", limit=10, offset=0,
        )
        assert res.total == 1
        assert len(res.items) == 1
        row = res.items[0]
        assert row["_source"] == "fhir"
        assert row["_fhir_status"] == "in-progress"
        assert row["status"] == "in_progress"
        assert row["provider_name"] == "Dr. Carter"
        assert row["patient_identifier"] == "pt-7"
        assert row["organization_id"] == 42
        assert row["scheduled_at"] == "2026-04-18T10:00:00Z"
        # ChartNav status → FHIR status mapping threaded through the URL.
        assert any("status=in-progress" in u for u in calls), calls


# ---------------------------------------------------------------------
# RBAC still holds in integrated mode
# ---------------------------------------------------------------------

def test_integrated_list_requires_auth(test_db, monkeypatch):
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")
    client = _integrated_client(test_db, "integrated_readthrough")
    try:
        r = client.get("/encounters")
        assert r.status_code == 401
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()
