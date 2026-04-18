"""Platform-mode + adapter resolution tests (phase 16).

Covers: config parsing of CHARTNAV_PLATFORM_MODE + CHARTNAV_INTEGRATION_ADAPTER,
invalid combinations, adapter resolution per mode, stub adapter
read-through vs write-through behavior, native adapter honesty,
and the /platform endpoint surface.
"""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager


@contextmanager
def _env(**kv: str | None):
    """Temporarily set/clear env vars."""
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


def _reload_config_and_integrations():
    import app.config
    import app.integrations
    import app.integrations.base
    import app.integrations.native
    import app.integrations.stub
    importlib.reload(app.config)
    importlib.reload(app.integrations.base)
    importlib.reload(app.integrations.native)
    importlib.reload(app.integrations.stub)
    importlib.reload(app.integrations)
    return app.config, app.integrations


# ---------------------------------------------------------------------
# Config layer
# ---------------------------------------------------------------------

def test_default_mode_is_standalone():
    with _env(
        CHARTNAV_PLATFORM_MODE=None,
        CHARTNAV_INTEGRATION_ADAPTER=None,
    ):
        config, _ = _reload_config_and_integrations()
        assert config.settings.platform_mode == "standalone"
        assert config.settings.integration_adapter == "native"


def test_integrated_readthrough_defaults_to_stub():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER=None,
    ):
        config, _ = _reload_config_and_integrations()
        assert config.settings.platform_mode == "integrated_readthrough"
        assert config.settings.integration_adapter == "stub"


def test_integrated_writethrough_defaults_to_stub():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_writethrough",
        CHARTNAV_INTEGRATION_ADAPTER=None,
    ):
        config, _ = _reload_config_and_integrations()
        assert config.settings.platform_mode == "integrated_writethrough"
        assert config.settings.integration_adapter == "stub"


def test_invalid_mode_raises():
    import pytest
    with _env(CHARTNAV_PLATFORM_MODE="bogus"):
        with pytest.raises(RuntimeError) as exc:
            _reload_config_and_integrations()
        assert "CHARTNAV_PLATFORM_MODE" in str(exc.value)


def test_standalone_forbids_non_native_adapter():
    import pytest
    with _env(
        CHARTNAV_PLATFORM_MODE="standalone",
        CHARTNAV_INTEGRATION_ADAPTER="stub",
    ):
        with pytest.raises(RuntimeError) as exc:
            _reload_config_and_integrations()
        assert "standalone" in str(exc.value)


# ---------------------------------------------------------------------
# Adapter resolution
# ---------------------------------------------------------------------

def test_standalone_mode_resolves_native_adapter():
    with _env(
        CHARTNAV_PLATFORM_MODE="standalone",
        CHARTNAV_INTEGRATION_ADAPTER=None,
    ):
        _, integrations = _reload_config_and_integrations()
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "native"
        assert adapter.info.supports_encounter_read is True


def test_integrated_readthrough_resolves_stub_without_writes():
    import pytest
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="stub",
    ):
        _, integrations = _reload_config_and_integrations()
        # Import AFTER reload so we match the reloaded class identity.
        from app.integrations.base import AdapterNotSupported
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "stub"
        assert adapter.info.supports_encounter_write is False

        # Reads succeed with canned shape.
        patient = adapter.fetch_patient("pt-42")
        assert patient["source"] == "stub"
        assert "42" in patient["id"]

        # Writes refused honestly.
        with pytest.raises(AdapterNotSupported):
            adapter.update_encounter_status(
                "1", "completed", changed_by="a@b.test"
            )


def test_integrated_writethrough_resolves_stub_with_writes_recorded():
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_writethrough",
        CHARTNAV_INTEGRATION_ADAPTER="stub",
    ):
        _, integrations = _reload_config_and_integrations()
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "stub"
        assert adapter.info.supports_encounter_write is True

        result = adapter.update_encounter_status(
            "1", "completed", changed_by="a@b.test"
        )
        assert result["status"] == "completed"
        assert adapter.recorded_writes[-1]["op"] == "update_encounter_status"

        note = adapter.write_note(
            encounter_id="1",
            author_email="a@b.test",
            body="hello",
        )
        assert note["encounter_id"] == "1"
        assert adapter.recorded_writes[-1]["op"] == "write_note"


def test_unknown_vendor_adapter_raises():
    import pytest
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="epic",  # not registered
    ):
        _, integrations = _reload_config_and_integrations()
        with pytest.raises(RuntimeError) as exc:
            integrations.resolve_adapter()
        assert "no registered adapter" in str(exc.value)


def test_vendor_registration_path():
    """Prove the registry hook actually works without a real vendor."""
    with _env(
        CHARTNAV_PLATFORM_MODE="integrated_readthrough",
        CHARTNAV_INTEGRATION_ADAPTER="custom",
    ):
        _, integrations = _reload_config_and_integrations()
        from app.integrations.stub import StubClinicalSystemAdapter
        integrations.register_vendor_adapter(
            "custom", lambda: StubClinicalSystemAdapter(writes_allowed=False)
        )
        adapter = integrations.resolve_adapter()
        assert adapter.info.key == "stub"  # stub wearing custom hat


# ---------------------------------------------------------------------
# Native adapter honesty
# ---------------------------------------------------------------------

def test_native_adapter_refuses_unsupported_operations():
    import pytest
    _reload_config_and_integrations()
    from app.integrations.base import AdapterNotSupported
    from app.integrations.native import NativeChartNavAdapter

    adapter = NativeChartNavAdapter()
    with pytest.raises(AdapterNotSupported):
        adapter.fetch_patient("anything")
    with pytest.raises(AdapterNotSupported):
        adapter.search_patients(query="anything")


# ---------------------------------------------------------------------
# /platform endpoint
# ---------------------------------------------------------------------

def test_platform_endpoint_surfaces_mode_and_adapter(client):
    """Any authenticated caller can read /platform.

    The endpoint must report mode, adapter key, and source-of-truth
    map. No secrets leak (e.g. JWT config must not appear).
    """
    resp = client.get("/platform", headers={"X-User-Email": "admin@chartnav.local"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["platform_mode"] == "standalone"
    assert body["integration_adapter"] == "native"
    assert body["adapter"]["key"] == "native"
    sot = body["adapter"]["source_of_truth"]
    assert sot["encounter"] == "chartnav"
    assert sot["patient"] == "not_supported"
    # No secret leakage.
    assert "jwt" not in resp.text.lower()
    assert "database_url" not in resp.text.lower()


def test_platform_endpoint_requires_auth(client):
    resp = client.get("/platform")
    assert resp.status_code == 401
