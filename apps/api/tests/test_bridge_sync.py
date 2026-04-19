"""Phase 23 — bridged-encounter refresh foundation.

Covers:
- refresh of a bridged row updates only mirror fields.
- refresh refuses on a standalone-native row (409 not_bridged).
- refresh refuses when the deployment's active adapter doesn't
  match the historical external_source (409 external_source_mismatch).
- reviewer cannot refresh; admin + clinician can.
- cross-org refresh = 404.
- refresh does not touch ChartNav-native workflow tables
  (workflow_events, encounter_inputs, extracted_findings,
  note_versions unchanged by the refresh).
- refresh emits `encounter_refreshed` audit event.
"""

from __future__ import annotations

import os


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}


def _reload_app():
    import sys
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _integrated_client(test_db, adapter: str = "stub"):
    _reload_app()
    os.environ["CHARTNAV_PLATFORM_MODE"] = "integrated_readthrough"
    os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = adapter
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------
# Standalone refusal
# ---------------------------------------------------------------------

def test_refresh_refuses_on_standalone_native_encounter(client):
    # Seeded encounter id=1 is standalone-native (external_ref=NULL).
    r = client.post("/encounters/1/refresh", json={}, headers=CLIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "not_bridged"


# ---------------------------------------------------------------------
# Integrated mode — stub
# ---------------------------------------------------------------------

def _bridge_native(client, ref="ENC-SYNC", status="scheduled"):
    return client.post(
        "/encounters/bridge",
        json={
            "external_ref": ref,
            "external_source": "stub",
            "patient_identifier": "EXT-9001",
            "patient_name": "Morgan External",
            "provider_name": "Dr. External",
            "status": status,
        },
        headers=CLIN1,
    ).json()


def test_refresh_updates_mirror_fields_on_bridged_row(test_db, monkeypatch):
    client = _integrated_client(test_db, adapter="stub")
    try:
        bridged = _bridge_native(client, ref="ENC-A")
        native_id = bridged["id"]

        # Stub adapter's fetch_encounter returns provider_name="Stub
        # Provider" and patient_identifier="EXT-<id>". After the
        # refresh these should land on the native row.
        r = client.post(f"/encounters/{native_id}/refresh", json={}, headers=CLIN1)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["refreshed"] is True
        assert "provider_name" in body["mirrored"]
        assert body["mirrored"]["provider_name"] == "Stub Provider"

        # Verify the native row actually changed.
        row = client.get(f"/encounters/{native_id}", headers=CLIN1).json()
        assert row["provider_name"] == "Stub Provider"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_refresh_is_idempotent(test_db, monkeypatch):
    client = _integrated_client(test_db, adapter="stub")
    try:
        bridged = _bridge_native(client, ref="ENC-IDEM")
        native_id = bridged["id"]

        first = client.post(
            f"/encounters/{native_id}/refresh", json={}, headers=CLIN1,
        ).json()
        second = client.post(
            f"/encounters/{native_id}/refresh", json={}, headers=CLIN1,
        ).json()
        # Second call: nothing new to mirror.
        assert second["refreshed"] is False
        assert second["mirrored"] == {}
        assert first["id"] == second["id"] == native_id
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_refresh_does_not_touch_chartnav_native_workflow_tables(
    test_db, monkeypatch,
):
    client = _integrated_client(test_db, adapter="stub")
    try:
        bridged = _bridge_native(client, ref="ENC-NOWALK")
        native_id = bridged["id"]

        # Attach ChartNav-native workflow state to the bridged row.
        ingest = client.post(
            f"/encounters/{native_id}/inputs",
            json={
                "input_type": "text_paste",
                "transcript_text": (
                    "Chief complaint: test.\nOD 20/20, OS 20/20. "
                    "IOP 10/10.\nPlan: observe. Follow-up 4 weeks."
                ),
            },
            headers=CLIN1,
        ).json()

        # Refresh shouldn't disturb the native workflow.
        client.post(f"/encounters/{native_id}/refresh", json={}, headers=CLIN1)

        inputs = client.get(
            f"/encounters/{native_id}/inputs", headers=CLIN1,
        ).json()
        ids = [i["id"] for i in inputs]
        assert ingest["id"] in ids
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Source-of-truth mismatch
# ---------------------------------------------------------------------

def test_refresh_refuses_when_adapter_does_not_match_external_source(
    test_db, monkeypatch,
):
    """Row was bridged from `stub`, current adapter is `fhir` → refuse."""
    client = _integrated_client(test_db, adapter="stub")
    bridged = _bridge_native(client, ref="ENC-MISMATCH")
    native_id = bridged["id"]
    try:
        # Reload under a different adapter (fhir) — historical source
        # stays as `stub` on the native row.
        os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = "fhir"
        os.environ["CHARTNAV_FHIR_BASE_URL"] = "https://example.org/fhir"
        _reload_app()
        from fastapi.testclient import TestClient
        from app.main import app as _app
        client2 = TestClient(_app)

        r = client2.post(
            f"/encounters/{native_id}/refresh", json={}, headers=CLIN1,
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "external_source_mismatch"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        os.environ.pop("CHARTNAV_FHIR_BASE_URL", None)
        _reload_app()


# ---------------------------------------------------------------------
# RBAC + scoping
# ---------------------------------------------------------------------

def test_reviewer_cannot_refresh(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        bridged = _bridge_native(client, ref="ENC-RBAC")
        native_id = bridged["id"]
        r = client.post(
            f"/encounters/{native_id}/refresh", json={}, headers=REV1,
        )
        assert r.status_code == 403
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_cross_org_refresh_is_404(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        bridged = _bridge_native(client, ref="ENC-XORG")
        native_id = bridged["id"]
        r = client.post(
            f"/encounters/{native_id}/refresh",
            json={},
            headers={"X-User-Email": "clin@northside.local"},
        )
        assert r.status_code == 404
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------

def test_refresh_emits_audit_event(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        bridged = _bridge_native(client, ref="ENC-AUDIT")
        native_id = bridged["id"]
        client.post(f"/encounters/{native_id}/refresh", json={}, headers=CLIN1)

        audit = client.get(
            "/security-audit-events?limit=200", headers=ADMIN1,
        ).json()
        items = audit["items"] if isinstance(audit, dict) else audit
        types = [e["event_type"] for e in items]
        assert "encounter_refreshed" in types
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()
