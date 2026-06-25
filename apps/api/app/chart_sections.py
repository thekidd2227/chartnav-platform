"""Chart-section registry.

Patient charts are composed of named, cohesive *sections* (Overview,
Encounters, Allergies, Medications, etc.). Most sections are still
placeholders today; a few (Overview, Encounters, Eye Diagrams) are
backed by real data. The registry is the single declaration site so
the frontend can render the chart shell from data, and so future
clinical modules can plug in without code rewrites scattered across
routers.

A section's `status` is honest:
  - active       — real backend support; UI should render data
  - placeholder  — surface is stubbed; UI should say "Not implemented yet"
  - unavailable  — feature gated off in this deployment

Each section can declare a `required_role` (any of the role names in
`app.authz`); if set, the frontend can choose to hide the tab from
roles that wouldn't be allowed to see/use it. Authorization itself is
still enforced server-side at the relevant endpoint — this is purely
a hint to keep the UI from offering surfaces the caller can't use.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChartSection:
    key: str
    label: str
    status: str  # 'active' | 'placeholder' | 'unavailable'
    description: str
    api_path: Optional[str] = None
    required_role: Optional[str] = None
    future_module: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "description": self.description,
            "api_path": self.api_path,
            "required_role": self.required_role,
            "future_module": self.future_module,
        }


# The registry order is the default tab order in the UI.
SECTIONS: tuple[ChartSection, ...] = (
    ChartSection(
        key="overview",
        label="Overview",
        status="active",
        description="Demographics, identifiers, and key patient info.",
        api_path="/patients/{id}",
    ),
    ChartSection(
        key="encounters",
        label="Encounters",
        status="active",
        description="All encounters for this patient.",
        api_path="/patients/{id}/encounters",
    ),
    ChartSection(
        key="allergies",
        label="Allergies",
        status="placeholder",
        description="Substance allergies and reactions.",
        future_module="phase-2c-allergies",
    ),
    ChartSection(
        key="medications",
        label="Medications",
        status="placeholder",
        description="Active and historical medications.",
        future_module="phase-2c-medications",
    ),
    ChartSection(
        key="labs",
        label="Labs",
        status="placeholder",
        description="Laboratory results and trends.",
        future_module="phase-2c-labs",
    ),
    ChartSection(
        key="radiology",
        label="Radiology",
        status="placeholder",
        description="Imaging studies and reports.",
        future_module="phase-2c-radiology",
    ),
    ChartSection(
        key="orders",
        label="Orders",
        status="placeholder",
        description="Pending and resulted clinical orders.",
        future_module="phase-2c-orders",
    ),
    ChartSection(
        key="documents",
        label="Documents",
        status="placeholder",
        description="Scanned forms, external documents, attachments.",
        future_module="phase-2c-documents",
    ),
    ChartSection(
        key="consults",
        label="Consults / H&P",
        status="placeholder",
        description="History & Physical, consult notes.",
        future_module="phase-2c-consults",
    ),
    ChartSection(
        key="isolation",
        label="Isolation",
        status="placeholder",
        description="Isolation precautions and infectious disease flags.",
        future_module="phase-2c-isolation",
    ),
    ChartSection(
        key="eye_diagrams",
        label="Eye Diagrams",
        status="active",
        description="Retinal and anterior-segment diagrams.",
        api_path="/patients/{id}/artifacts?type=retinal_diagram",
    ),
)


def list_sections() -> list[dict]:
    """Returns the sections as plain dicts for JSON serialization."""
    return [s.to_dict() for s in SECTIONS]


def section_keys() -> set[str]:
    return {s.key for s in SECTIONS}
