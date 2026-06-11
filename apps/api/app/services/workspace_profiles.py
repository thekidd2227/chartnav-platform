"""Phase 86 — Subspecialty Adaptive Workspace service.

The Workspace Profile Resolver maps an encounter's provider-entered
``encounter_type`` to a deterministic panel ordering for the Overview
tab. The resolver does NOT infer subspecialty from clinical data, does
NOT autonomously classify the encounter, and does NOT change what
data is available — every panel that exists today still exists, the
profile only reorders and optionally collapses lower-priority panels.

Hard rules:

  * Only admin / clinician may PATCH the encounter_type.
  * Profiles are a fixed closed-allowlist mapping. New profiles
    require a migration + service change.
  * Each profile lists every panel exactly once across
    ``prioritized``, ``visible``, and ``collapsed`` — no panel is
    silently dropped. The UI may collapse-by-default, but the
    operator can always expand.
  * ``encounter_type`` defaults to ``comprehensive`` (balanced
    layout) — never inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Closed allowlists
# ---------------------------------------------------------------------------

VALID_ENCOUNTER_TYPES = frozenset({"retina", "glaucoma", "cataract", "comprehensive"})

ENCOUNTER_TYPE_LABELS: dict[str, str] = {
    "retina": "Retina",
    "glaucoma": "Glaucoma",
    "cataract": "Cataract",
    "comprehensive": "Comprehensive",
}

# Every Overview-tab panel known to the resolver. The UI references
# panels by these stable string codes.
PANEL_CODES: tuple[str, ...] = (
    "provider_action_queue",
    "note_validation",
    "retina_visit_summary",
    "retina_visit_packet",
    "anti_vegf_injection",
    "glaucoma_cockpit",
    "cataract_workflow",
    "disease_staging",
    "medication_safety",
    "quality_intelligence",
    "imaging_metadata",
)

PANEL_LABELS: dict[str, str] = {
    "provider_action_queue": "Provider Action Queue",
    "note_validation": "Note Validation Rail",
    "retina_visit_summary": "Retina Visit Summary",
    "retina_visit_packet": "Retina Visit Packet",
    "anti_vegf_injection": "Anti-VEGF Injection Rail",
    "glaucoma_cockpit": "Glaucoma Progression Cockpit",
    "cataract_workflow": "Cataract Surgical Workflow",
    "disease_staging": "Disease Staging",
    "medication_safety": "Medication Safety & Adherence",
    "quality_intelligence": "Quality Documentation Support",
    "imaging_metadata": "Imaging Metadata",
}


# ---------------------------------------------------------------------------
# Profile definitions — deterministic, never inferred.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceProfile:
    code: str
    label: str
    prioritized: tuple[str, ...]
    visible: tuple[str, ...]
    collapsed: tuple[str, ...]


_UNIVERSAL = ("provider_action_queue", "note_validation")


PROFILES: dict[str, WorkspaceProfile] = {
    "retina": WorkspaceProfile(
        code="retina",
        label="Retina",
        prioritized=(
            *_UNIVERSAL,
            "anti_vegf_injection",
            "retina_visit_summary",
            "retina_visit_packet",
            "imaging_metadata",
        ),
        visible=(
            "disease_staging",
            "medication_safety",
            "quality_intelligence",
        ),
        collapsed=(
            "glaucoma_cockpit",
            "cataract_workflow",
        ),
    ),
    "glaucoma": WorkspaceProfile(
        code="glaucoma",
        label="Glaucoma",
        prioritized=(
            *_UNIVERSAL,
            "glaucoma_cockpit",
            "imaging_metadata",
            "medication_safety",
        ),
        visible=(
            "disease_staging",
            "retina_visit_summary",
            "quality_intelligence",
        ),
        collapsed=(
            "anti_vegf_injection",
            "cataract_workflow",
            "retina_visit_packet",
        ),
    ),
    "cataract": WorkspaceProfile(
        code="cataract",
        label="Cataract",
        prioritized=(
            *_UNIVERSAL,
            "cataract_workflow",
            "imaging_metadata",
            "medication_safety",
        ),
        visible=(
            "disease_staging",
            "retina_visit_summary",
            "quality_intelligence",
        ),
        collapsed=(
            "anti_vegf_injection",
            "glaucoma_cockpit",
            "retina_visit_packet",
        ),
    ),
    "comprehensive": WorkspaceProfile(
        code="comprehensive",
        label="Comprehensive",
        prioritized=(
            *_UNIVERSAL,
            "retina_visit_summary",
            "retina_visit_packet",
            "anti_vegf_injection",
            "glaucoma_cockpit",
            "cataract_workflow",
            "disease_staging",
            "medication_safety",
            "quality_intelligence",
        ),
        visible=(),
        collapsed=("imaging_metadata",),
    ),
}


def _validate_profile_coverage() -> None:
    """Defensive check at import time: every PANEL_CODES entry must
    appear exactly once across each profile's three buckets so the UI
    can never silently drop a panel."""
    panels = set(PANEL_CODES)
    for code, profile in PROFILES.items():
        bucketed = (
            list(profile.prioritized) + list(profile.visible) + list(profile.collapsed)
        )
        if set(bucketed) != panels:
            missing = panels - set(bucketed)
            extra = set(bucketed) - panels
            raise RuntimeError(
                f"profile {code!r} coverage mismatch: missing={missing!r} "
                f"extra={extra!r}"
            )
        if len(bucketed) != len(set(bucketed)):
            raise RuntimeError(
                f"profile {code!r} has duplicate panel codes: {bucketed!r}"
            )


_validate_profile_coverage()


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class WorkspaceProfileError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_encounter_type(value: Any) -> str:
    if value not in VALID_ENCOUNTER_TYPES:
        raise WorkspaceProfileError(
            "invalid_encounter_type",
            (
                "encounter_type must be one of "
                f"{sorted(VALID_ENCOUNTER_TYPES)}; got {value!r}"
            ),
            422,
        )
    return value


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise WorkspaceProfileError(
            "forbidden",
            "only admin or clinician can change the encounter type",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_encounter_or_404(
    conn, encounter_id: int, org_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, encounter_type, "
            "status, patient_name, patient_identifier, provider_name "
            "FROM encounters WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise WorkspaceProfileError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return {
        "id": int(row[0]),
        "organization_id": int(row[1]),
        "patient_id": int(row[2]) if row[2] is not None else None,
        "encounter_type": row[3],
        "status": row[4],
        "patient_name": row[5],
        "patient_identifier": row[6],
        "provider_name": row[7],
    }


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _serialize_profile(profile: WorkspaceProfile) -> dict[str, Any]:
    return {
        "code": profile.code,
        "label": profile.label,
        "prioritized_panels": [
            {"code": c, "label": PANEL_LABELS[c]} for c in profile.prioritized
        ],
        "visible_panels": [
            {"code": c, "label": PANEL_LABELS[c]} for c in profile.visible
        ],
        "collapsed_panels": [
            {"code": c, "label": PANEL_LABELS[c]} for c in profile.collapsed
        ],
        "panel_order": [
            *profile.prioritized,
            *profile.visible,
            *profile.collapsed,
        ],
    }


_DISCLOSURE = (
    "Workspace profile is a deterministic mapping from the provider-entered "
    "encounter type to a panel-ordering preference. ChartNav does NOT "
    "autonomously classify the encounter, does NOT infer subspecialty from "
    "clinical data, and does NOT hide data — lower-priority panels may be "
    "collapsed but remain available."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_for_encounter(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Return the resolved workspace profile + encounter metadata."""
    with engine.connect() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
    profile_code = encounter["encounter_type"] or "comprehensive"
    profile = PROFILES.get(profile_code, PROFILES["comprehensive"])
    return {
        "encounter_id": encounter["id"],
        "organization_id": encounter["organization_id"],
        "patient_id": encounter["patient_id"],
        "patient_name": encounter["patient_name"],
        "patient_identifier": encounter["patient_identifier"],
        "provider_name": encounter["provider_name"],
        "status": encounter["status"],
        "encounter_type": profile_code,
        "encounter_type_label": ENCOUNTER_TYPE_LABELS.get(
            profile_code, profile_code
        ),
        "profile": _serialize_profile(profile),
        "supported_encounter_types": [
            {"code": code, "label": label}
            for code, label in ENCOUNTER_TYPE_LABELS.items()
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclosure": _DISCLOSURE,
    }


def set_encounter_type(
    encounter_id: int, caller: Caller, encounter_type: Any
) -> dict[str, Any]:
    """Provider-driven update of the encounter's subspecialty type."""
    _assert_write_role(caller)
    typ = _validate_encounter_type(encounter_type)

    with engine.begin() as conn:
        existing = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        conn.execute(
            sa_text(
                "UPDATE encounters SET encounter_type = :t WHERE id = :id"
            ),
            {"t": typ, "id": existing["id"]},
        )

    return resolve_for_encounter(encounter_id, caller)


def profile_summary_for_encounter(
    encounter_id: int, organization_id: int
) -> dict[str, Any]:
    """Lightweight projection used by Phase 76 / 82 to embed the
    encounter's workspace profile metadata into other endpoints. No
    panel ordering — just the code + label."""
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT encounter_type FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
    typ = "comprehensive"
    if row is not None and row[0]:
        typ = row[0]
    return {
        "encounter_type": typ,
        "encounter_type_label": ENCOUNTER_TYPE_LABELS.get(typ, typ),
        "profile_code": typ,
    }


__all__ = [
    "WorkspaceProfile",
    "WorkspaceProfileError",
    "VALID_ENCOUNTER_TYPES",
    "ENCOUNTER_TYPE_LABELS",
    "PANEL_CODES",
    "PANEL_LABELS",
    "PROFILES",
    "resolve_for_encounter",
    "set_encounter_type",
    "profile_summary_for_encounter",
]
