"""FHIR R4 adapter (phase 18).

Drives the adapter with a fixture transport — no network, no vendor
SDK. Proves:
- config resolution (base URL, auth, bearer token)
- Patient fetch + search normalization
- Encounter normalization (status mapping + participant display)
- read-only honesty (write/update paths raise AdapterNotSupported)
- boot fails loudly on missing base URL
- bearer header threads through the transport
- integrated_readthrough + adapter=fhir resolves the FHIR adapter
"""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager

import pytest


@contextmanager
def _env(**kv: str | None):
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


def _reload():
    import app.config
    import app.integrations
    import app.integrations.base
    import app.integrations.fhir
    import app.integrations.native
    import app.integrations.stub
    importlib.reload(app.config)
    importlib.reload(app.integrations.base)
    importlib.reload(app.integrations.fhir)
    importlib.reload(app.integrations.native)
    importlib.reload(app.integrations.stub)
    importlib.reload(app.integrations)
    return app.config, app.integrations


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

FHIR_PATIENT = {
    "resourceType": "Patient",
    "id": "pt-7",
    "identifier": [
        {
            "type": {"coding": [{"code": "MR", "display": "MRN"}]},
            "value": "MRN-7",
        }
    ],
    "name": [
        {"use": "official", "given": ["Morgan"], "family": "Lee"}
    ],
    "birthDate": "1962-03-14",
    "gender": "female",
}

FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [
        {"resource": FHIR_PATIENT},
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pt-8",
                "name": [{"given": ["Alex"], "family": "Nguyen"}],
                "identifier": [{"value": "MRN-8"}],
            }
        },
    ],
}

FHIR_ENCOUNTER = {
    "resourceType": "Encounter",
    "id": "enc-99",
    "status": "in-progress",
    "subject": {"reference": "Patient/pt-7"},
    "participant": [{"individual": {"display": "Dr. Carter"}}],
}


def _make_fixture_transport(mapping):
    captured = []

    def transport(url: str, headers: dict[str, str]):
        captured.append((url, dict(headers)))
        # Strict match → give back the fixture resource.
        for key, body in mapping.items():
            if url.endswith(key):
                return body
        raise AssertionError(f"no fixture registered for {url}")

    transport.captured = captured
    return transport


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

def test_fhir_adapter_boots_with_minimum_config():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="fhir",
        CHARTNAV_FHIR_BASE_URL="https://example.org/fhir",
        CHARTNAV_FHIR_AUTH_TYPE=None,
        CHARTNAV_FHIR_BEARER_TOKEN=None,
    ):
        _, integrations = _reload()
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "fhir"
        assert adapter.info.supports_patient_read is True
        assert adapter.info.supports_patient_write is False
        assert adapter.info.supports_encounter_write is False


def test_fhir_adapter_requires_base_url():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="fhir",
        CHARTNAV_FHIR_BASE_URL=None,
    ):
        _, integrations = _reload()
        from app.integrations.base import AdapterError
        with pytest.raises(AdapterError) as exc:
            integrations.resolve_adapter()
        assert exc.value.error_code == "fhir_not_configured"


def test_fhir_adapter_bearer_requires_token():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="fhir",
        CHARTNAV_FHIR_BASE_URL="https://example.org/fhir",
        CHARTNAV_FHIR_AUTH_TYPE="bearer",
        CHARTNAV_FHIR_BEARER_TOKEN=None,
    ):
        _, integrations = _reload()
        from app.integrations.base import AdapterError
        with pytest.raises(AdapterError) as exc:
            integrations.resolve_adapter()
        assert exc.value.error_code == "fhir_missing_bearer"


# ---------------------------------------------------------------------
# Normalization via fixture transport
# ---------------------------------------------------------------------

def test_fhir_fetch_patient_normalizes():
    from app.integrations.fhir import FHIRAdapter
    transport = _make_fixture_transport({"/Patient/pt-7": FHIR_PATIENT})
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        transport=transport,
    )
    p = adapter.fetch_patient("pt-7")
    assert p["source"] == "fhir"
    assert p["external_ref"] == "pt-7"
    assert p["first_name"] == "Morgan"
    assert p["last_name"] == "Lee"
    assert p["date_of_birth"] == "1962-03-14"
    assert p["sex_at_birth"] == "female"
    assert p["patient_identifier"] == "MRN-7"
    # URL should be base + path.
    assert transport.captured[0][0] == "https://example.org/fhir/Patient/pt-7"


def test_fhir_search_patients_normalizes_bundle():
    from app.integrations.fhir import FHIRAdapter
    transport = _make_fixture_transport({
        "/Patient?name=morgan&_count=25": FHIR_BUNDLE,
    })
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        transport=transport,
    )
    results = adapter.search_patients(query="morgan", limit=25)
    assert len(results) == 2
    assert results[0]["first_name"] == "Morgan"
    assert results[1]["patient_identifier"] == "MRN-8"


def test_fhir_fetch_encounter_maps_status():
    from app.integrations.fhir import FHIRAdapter
    transport = _make_fixture_transport({"/Encounter/enc-99": FHIR_ENCOUNTER})
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        transport=transport,
    )
    enc = adapter.fetch_encounter("enc-99")
    assert enc["status"] == "in_progress"      # ChartNav status
    assert enc["fhir_status"] == "in-progress"  # original
    assert enc["patient_id"] == "pt-7"
    assert enc["provider_name"] == "Dr. Carter"


def test_fhir_bearer_auth_adds_header():
    from app.integrations.fhir import FHIRAdapter
    transport = _make_fixture_transport({"/Patient/pt-7": FHIR_PATIENT})
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        auth_type="bearer",
        bearer_token="secret-token",
        transport=transport,
    )
    adapter.fetch_patient("pt-7")
    _, headers = transport.captured[0]
    assert headers.get("Authorization") == "Bearer secret-token"
    assert headers.get("Accept") == "application/fhir+json"


# ---------------------------------------------------------------------
# Honesty: write-through is refused
# ---------------------------------------------------------------------

def test_fhir_adapter_refuses_status_writes():
    from app.integrations.base import AdapterNotSupported
    from app.integrations.fhir import FHIRAdapter
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        transport=lambda u, h: {},
    )
    with pytest.raises(AdapterNotSupported):
        adapter.update_encounter_status("1", "completed", changed_by="x@y.z")


def test_fhir_adapter_refuses_note_writes():
    from app.integrations.base import AdapterNotSupported
    from app.integrations.fhir import FHIRAdapter
    adapter = FHIRAdapter(
        base_url="https://example.org/fhir",
        transport=lambda u, h: {},
    )
    with pytest.raises(AdapterNotSupported):
        adapter.write_note(
            encounter_id="1", author_email="x@y.z", body="hello"
        )


# ---------------------------------------------------------------------
# Integration with resolve_adapter
# ---------------------------------------------------------------------

def test_readthrough_plus_fhir_resolves_fhir_adapter():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="fhir",
        CHARTNAV_FHIR_BASE_URL="https://example.org/fhir",
    ):
        _, integrations = _reload()
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "fhir"
