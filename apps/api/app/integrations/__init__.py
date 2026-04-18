"""External-system integration boundary.

ChartNav talks to external EHR/EMR systems through a single adapter
contract (`ClinicalSystemAdapter`). Two honest implementations ship:

- `NativeChartNavAdapter` — persists to ChartNav's own database.
  Used in `standalone` mode. ChartNav is the system of record.
- `StubClinicalSystemAdapter` — in-memory placeholder for integrated
  modes when no real vendor connector is wired. Boots honestly,
  refuses writes in read-through, records writes without a real
  back-end in write-through, so the service layer can be exercised
  end-to-end without a live EHR.

A real vendor adapter (FHIR, Epic, Cerner, ...) is expected to plug
in by registering itself here. Each vendor adapter is responsible for
its own transport, auth, and schema translation. ChartNav's core
services never see the vendor wire protocol — only the adapter
contract defined in `base.py`.

Selection rules:
- `platform_mode=standalone` → `native` always.
- `platform_mode=integrated_readthrough` + `integration_adapter=stub`
  → StubClinicalSystemAdapter(writes_allowed=False).
- `platform_mode=integrated_writethrough` + `integration_adapter=stub`
  → StubClinicalSystemAdapter(writes_allowed=True).
- `platform_mode=integrated_*` + `integration_adapter=<vendor>` →
  resolved from `_VENDOR_ADAPTERS` (currently empty; vendor work
  plugs in here without touching the core).

See docs/build/26-platform-mode-and-interoperability.md.
"""

from __future__ import annotations

from typing import Callable

from app.config import settings
from app.integrations.base import ClinicalSystemAdapter, SourceOfTruth
from app.integrations.native import NativeChartNavAdapter
from app.integrations.stub import StubClinicalSystemAdapter

# Registry of vendor adapter factories. Real integrations register
# themselves here. Keys are the values operators pass via
# `CHARTNAV_INTEGRATION_ADAPTER=<key>`. Intentionally empty today —
# "stub" and "native" are special-cased below; adding e.g. "fhir"
# means: (1) write a FHIRAdapter in this package, (2) register its
# factory here. No other core files need to change.
_VENDOR_ADAPTERS: dict[str, Callable[[], ClinicalSystemAdapter]] = {}


def resolve_adapter() -> ClinicalSystemAdapter:
    """Return the adapter matching the current runtime configuration.

    Pure function of `settings` — call once per request path that
    needs the adapter, or memoize at startup. Raises on misconfig.
    """
    mode = settings.platform_mode
    key = settings.integration_adapter

    if mode == "standalone":
        return NativeChartNavAdapter()

    writes_allowed = mode == "integrated_writethrough"

    if key == "stub":
        return StubClinicalSystemAdapter(writes_allowed=writes_allowed)

    if key == "native":
        # Allowed as an explicit override in integrated modes — useful
        # for mixed deployments where ChartNav owns operational data
        # locally but the clinical record lives externally. The native
        # adapter is honest about what it supports.
        return NativeChartNavAdapter()

    factory = _VENDOR_ADAPTERS.get(key)
    if factory is None:
        raise RuntimeError(
            f"CHARTNAV_INTEGRATION_ADAPTER={key!r} has no registered "
            "adapter factory. Register one in app/integrations/__init__.py "
            "or set CHARTNAV_INTEGRATION_ADAPTER=stub."
        )
    return factory()


def register_vendor_adapter(
    key: str, factory: Callable[[], ClinicalSystemAdapter]
) -> None:
    """Register a vendor adapter factory under `key`.

    Called by vendor-specific modules at import time. Deliberately a
    mutating side effect rather than decorator magic — we want a
    grep-able audit trail when integrations are added.
    """
    if key in {"native", "stub"}:
        raise ValueError(f"cannot override reserved adapter key: {key}")
    _VENDOR_ADAPTERS[key] = factory


__all__ = [
    "ClinicalSystemAdapter",
    "NativeChartNavAdapter",
    "SourceOfTruth",
    "StubClinicalSystemAdapter",
    "register_vendor_adapter",
    "resolve_adapter",
]
