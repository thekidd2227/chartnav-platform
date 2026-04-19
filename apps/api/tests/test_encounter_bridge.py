"""Phase 21 — external encounter → native workflow bridge.

Covers:
- `POST /encounters/bridge` creates a native row with external_ref +
  external_source, idempotent on repeat calls.
- bridge row gets `_bridged=True` on first creation, `False` on
  subsequent resolves (same external_ref).
- bridge is refused in standalone mode (409).
- bridge is allowed in both integrated modes.
- reviewer role cannot bridge; admin + clinician can.
- transcript ingest + note generate + sign works on the bridged
  native row in integrated mode — proving the full wedge runs over
  bridged encounters.
- standalone mode unaffected (native encounters keep
  external_ref=NULL, existing tests pass).
- integrated encounter state writes (status / create) still gated
  (phase 20 contract preserved).
- workflow events still writable on bridged encounters.
- RBAC + org scoping hold.
- listing native encounters returns rows with external_ref +
  external_source when present.
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


def _integrated_client(test_db, mode: str = "integrated_readthrough", adapter: str = "stub"):
    _reload_app()
    os.environ["CHARTNAV_PLATFORM_MODE"] = mode
    os.environ["CHARTNAV_INTEGRATION_ADAPTER"] = adapter
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------
# bridge semantics
# ---------------------------------------------------------------------

def test_bridge_creates_native_row_with_external_ref(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        r = client.post(
            "/encounters/bridge",
            json={
                "external_ref": "ENC-XYZ",
                "external_source": "stub",
                "patient_identifier": "EXT-1001",
                "patient_name": "Morgan External",
                "provider_name": "Dr. External",
                "status": "in_progress",
            },
            headers=CLIN1,
        )
        assert r.status_code == 200, r.text
        row = r.json()
        assert row["_bridged"] is True
        assert row["external_ref"] == "ENC-XYZ"
        assert row["external_source"] == "stub"
        assert row["patient_identifier"] == "EXT-1001"
        assert row["status"] == "in_progress"
        assert row["organization_id"] == 1
        assert row["_source"] == "chartnav"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_bridge_is_idempotent(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        first = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-1", "external_source": "stub"},
            headers=CLIN1,
        ).json()
        second = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-1", "external_source": "stub"},
            headers=CLIN1,
        ).json()
        assert first["id"] == second["id"]
        assert first["_bridged"] is True
        assert second["_bridged"] is False
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_bridge_refused_in_standalone_mode(client):
    r = client.post(
        "/encounters/bridge",
        json={"external_ref": "X", "external_source": "stub"},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert (
        r.json()["detail"]["error_code"]
        == "bridge_not_available_in_standalone_mode"
    )


def test_reviewer_cannot_bridge(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        r = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-R", "external_source": "stub"},
            headers=REV1,
        )
        assert r.status_code == 403
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_admin_can_bridge(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        r = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-ADMIN", "external_source": "stub"},
            headers=ADMIN1,
        )
        assert r.status_code == 200
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_bridge_allowed_in_writethrough_mode(test_db, monkeypatch):
    client = _integrated_client(
        test_db, mode="integrated_writethrough", adapter="stub"
    )
    try:
        r = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-W", "external_source": "stub"},
            headers=CLIN1,
        )
        assert r.status_code == 200
        assert r.json()["_bridged"] is True
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_invalid_bridge_status(test_db, monkeypatch):
    client = _integrated_client(test_db)
    try:
        r = client.post(
            "/encounters/bridge",
            json={
                "external_ref": "ENC-BAD",
                "external_source": "stub",
                "status": "bogus",
            },
            headers=CLIN1,
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_status"
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Full wedge over a bridged encounter
# ---------------------------------------------------------------------

TRANSCRIPT = (
    "Chief complaint: blurry vision right eye.\n"
    "OD 20/40, OS 20/20.\nIOP 15/17.\n"
    "Diagnosis: cataract.\nPlan: refer for surgery.\n"
    "Follow-up in 4 weeks.\n"
)


def test_full_wedge_runs_on_bridged_encounter(test_db, monkeypatch):
    """Bridged encounter supports the full ChartNav wedge end-to-end."""
    client = _integrated_client(test_db)
    try:
        # 1. Bridge.
        bridge_row = client.post(
            "/encounters/bridge",
            json={
                "external_ref": "ENC-BRIDGE-1",
                "external_source": "stub",
                "patient_identifier": "EXT-9001",
                "patient_name": "Morgan External",
                "provider_name": "Dr. External",
            },
            headers=CLIN1,
        ).json()
        native_id = bridge_row["id"]

        # 2. Transcript ingest against the NATIVE id.
        r = client.post(
            f"/encounters/{native_id}/inputs",
            json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
            headers=CLIN1,
        )
        assert r.status_code == 201, r.text

        # 3. Generate a draft.
        r = client.post(
            f"/encounters/{native_id}/notes/generate",
            json={},
            headers=CLIN1,
        )
        assert r.status_code == 201, r.text
        note_id = r.json()["note"]["id"]

        # 4. Sign.
        r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
        assert r.status_code == 200, r.text
        assert r.json()["draft_status"] == "signed"

        # 5. Export.
        r = client.post(f"/note-versions/{note_id}/export", headers=CLIN1)
        assert r.status_code == 200, r.text
        assert r.json()["draft_status"] == "exported"

        # 6. Workflow events still writable.
        r = client.post(
            f"/encounters/{native_id}/events",
            json={"event_type": "manual_note", "event_data": {"note": "ok"}},
            headers=CLIN1,
        )
        assert r.status_code == 201, r.text
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


def test_integrated_mode_still_refuses_encounter_state_mutation_on_bridge(
    test_db, monkeypatch,
):
    """Bridging does NOT reopen encounter-state writes in read-through.

    The external EHR still owns the encounter status; bridging only
    unlocks ChartNav-native workflow (inputs, notes, events). The
    phase-20 contract stays intact.
    """
    client = _integrated_client(test_db)
    try:
        bridge_row = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-NOWRITE", "external_source": "stub"},
            headers=CLIN1,
        ).json()
        native_id = bridge_row["id"]

        # Attempting to mutate the external-owned status still fails.
        r = client.post(
            f"/encounters/{native_id}/status",
            json={"status": "draft_ready"},
            headers=CLIN1,
        )
        assert r.status_code == 409
        assert (
            r.json()["detail"]["error_code"]
            == "encounter_write_unsupported"
        )
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Org scoping
# ---------------------------------------------------------------------

def test_bridge_is_org_scoped(test_db, monkeypatch):
    """Same external_ref in two orgs → two distinct native rows."""
    client = _integrated_client(test_db)
    try:
        r1 = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-SHARED", "external_source": "stub"},
            headers=ADMIN1,
        )
        r2 = client.post(
            "/encounters/bridge",
            json={"external_ref": "ENC-SHARED", "external_source": "stub"},
            headers={"X-User-Email": "admin@northside.local"},
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["id"] != r2.json()["id"]
        assert r1.json()["organization_id"] == 1
        assert r2.json()["organization_id"] == 2
    finally:
        os.environ.pop("CHARTNAV_PLATFORM_MODE", None)
        os.environ.pop("CHARTNAV_INTEGRATION_ADAPTER", None)
        _reload_app()


# ---------------------------------------------------------------------
# Standalone regression
# ---------------------------------------------------------------------

def test_standalone_encounters_still_have_no_external_ref(client):
    r = client.get("/encounters", headers=ADMIN1)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    for row in rows:
        assert row.get("external_ref") is None
        assert row.get("external_source") is None
        assert row["_source"] == "chartnav"
