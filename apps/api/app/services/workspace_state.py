"""Phase 91 — Unified Ophthalmology Workspace State service.

The unified workspace state engine merges three orthogonal signals
into one deterministic projection consumed by the Overview tab:

  1. ``encounter_type`` (Phase 86) → workspace profile (panel order /
     visible / collapsed).
  2. ``visit_mode`` (Phase 91) → routing recommendation (which panels
     are emphasised for the current visit step).
  3. ``active_laterality`` (Phase 91) → eye-linked filter the laterality-
     aware panels subscribe to.

Hard rules:

  * ChartNav does NOT auto-classify the visit mode, does NOT
    autonomously select an eye, does NOT diagnose, does NOT
    recommend treatment, and does NOT add new clinical intelligence.
  * Visit mode and active laterality are PROVIDER-DRIVEN values set
    via PATCH endpoints.
  * The panel emphasis lists are a closed deterministic mapping per
    visit mode; new modes require a service change.
  * Every panel known to the Phase 86 workspace profile remains
    available — visit mode only *emphasises* a subset, it never
    hides one.
  * Only admin / clinician may PATCH visit mode or active laterality.
  * Cross-org access returns 404 (no existence leak).
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

VALID_VISIT_MODES = frozenset(
    {
        "intake",
        "surgical_pre_op",
        "post_op",
        "follow_up",
        "lab_review",
        "unscheduled",
    }
)

VISIT_MODE_LABELS: dict[str, str] = {
    "intake": "Intake",
    "surgical_pre_op": "Surgical pre-op",
    "post_op": "Post-op",
    "follow_up": "Follow-up",
    "lab_review": "Lab / imaging review",
    "unscheduled": "Unscheduled",
}

VALID_ACTIVE_LATERALITIES = frozenset({"OD", "OS", "OU", "NA"})

ACTIVE_LATERALITY_LABELS: dict[str, str] = {
    "OD": "OD · Right eye",
    "OS": "OS · Left eye",
    "OU": "OU · Both eyes",
    "NA": "Not applicable",
}


# Visit mode → emphasised panels. Every panel here MUST also be in
# the Phase 86 profile (we validate at import time). The emphasis is
# purely a UI hint; no panel is ever hidden by this projection.
_INTAKE_EMPHASIS = (
    "provider_action_queue",
    "note_validation",
)

_SURGICAL_EMPHASIS = (
    "cataract_workflow",
    "imaging_metadata",
    "ophthalmic_medication_safety",
    "medication_safety",
    "note_validation",
    "provider_action_queue",
)

_POST_OP_EMPHASIS = (
    "cataract_workflow",
    "note_validation",
    "provider_action_queue",
    "ophthalmic_medication_safety",
    "medication_safety",
)

_FOLLOW_UP_EMPHASIS = (
    "retina_visit_summary",
    "anti_vegf_injection",
    "glaucoma_cockpit",
    "disease_staging",
    "note_validation",
    "provider_action_queue",
)

_LAB_REVIEW_EMPHASIS = (
    "imaging_metadata",
    "retina_visit_summary",
    "quality_intelligence",
    "note_validation",
    "provider_action_queue",
)

_UNSCHEDULED_EMPHASIS = (
    "provider_action_queue",
    "note_validation",
)

VISIT_MODE_EMPHASIS: dict[str, tuple[str, ...]] = {
    "intake": _INTAKE_EMPHASIS,
    "surgical_pre_op": _SURGICAL_EMPHASIS,
    "post_op": _POST_OP_EMPHASIS,
    "follow_up": _FOLLOW_UP_EMPHASIS,
    "lab_review": _LAB_REVIEW_EMPHASIS,
    "unscheduled": _UNSCHEDULED_EMPHASIS,
}


# Panels that change behaviour when active_laterality changes. The UI
# uses this list to know which panels should re-filter on a
# laterality switch. The list is descriptive only — panels are
# already laterality-aware on the server.
LATERALITY_LINKED_PANELS = (
    "anti_vegf_injection",
    "glaucoma_cockpit",
    "cataract_workflow",
    "fundus_chart",
    "imaging_metadata",
    "ophthalmic_medication_safety",
)


def _validate_emphasis_coverage() -> None:
    """Defensive: every emphasis entry must reference a real Phase 86
    PANEL_CODES entry. Run at import time."""
    from app.services.workspace_profiles import PANEL_CODES

    known = set(PANEL_CODES)
    for mode, panels in VISIT_MODE_EMPHASIS.items():
        unknown = [p for p in panels if p not in known]
        if unknown:
            raise RuntimeError(
                f"visit_mode {mode!r} references unknown panel codes: {unknown!r}"
            )


_validate_emphasis_coverage()


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class WorkspaceStateError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _enum(name: str, value: Any, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise WorkspaceStateError(
            f"invalid_{name}",
            f"{name} must be one of {sorted(allowed)}; got {value!r}",
            422,
        )
    return value


def _assert_write_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise WorkspaceStateError(
            "forbidden",
            "only admin or clinician can change workspace state",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_encounter_or_404(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, patient_identifier, "
            "patient_name, provider_name, status, encounter_type, "
            "visit_mode, active_laterality "
            "FROM encounters WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise WorkspaceStateError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return {
        "id": int(row[0]),
        "organization_id": int(row[1]),
        "patient_id": int(row[2]) if row[2] is not None else None,
        "patient_identifier": row[3],
        "patient_name": row[4],
        "provider_name": row[5],
        "status": row[6],
        "encounter_type": row[7] or "comprehensive",
        "visit_mode": row[8] or "unscheduled",
        "active_laterality": row[9] or "NA",
    }


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


_DISCLOSURE = (
    "Unified workspace state is a deterministic projection over "
    "provider-entered encounter type, provider-entered visit mode, "
    "and provider-entered active laterality. ChartNav does NOT "
    "auto-classify the visit mode, does NOT autonomously select an "
    "eye, does NOT diagnose, does NOT recommend treatment, and does "
    "NOT add new clinical intelligence. Visit mode emphasis is a UI "
    "hint only — no panel is ever hidden by the state engine."
)


def _project_emphasis(
    visit_mode: str, profile_order: list[str]
) -> dict[str, Any]:
    raw = VISIT_MODE_EMPHASIS.get(visit_mode, _UNSCHEDULED_EMPHASIS)
    # Keep stable: emphasis order = panel_order intersection with raw.
    # This guarantees the emphasis follows the resolved profile order.
    emphasised: list[str] = []
    raw_set = set(raw)
    for code in profile_order:
        if code in raw_set:
            emphasised.append(code)
    other = [code for code in profile_order if code not in raw_set]
    return {
        "emphasised_panels": emphasised,
        "secondary_panels": other,
        "total_panels": len(profile_order),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_state_for_encounter(
    encounter_id: int, caller: Caller
) -> dict[str, Any]:
    """Return the unified workspace state for an encounter — the
    resolved Phase 86 profile, the Phase 91 visit-mode emphasis, the
    Phase 91 active laterality, and patient/encounter metadata.
    """
    from app.services.workspace_profiles import (
        PANEL_LABELS,
        PROFILES,
    )

    with engine.connect() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )

    profile_code = encounter["encounter_type"]
    profile = PROFILES.get(profile_code, PROFILES["comprehensive"])
    profile_order = [
        *profile.prioritized,
        *profile.visible,
        *profile.collapsed,
    ]
    emphasis = _project_emphasis(encounter["visit_mode"], profile_order)
    return {
        "encounter_id": encounter["id"],
        "organization_id": encounter["organization_id"],
        "patient_id": encounter["patient_id"],
        "patient_identifier": encounter["patient_identifier"],
        "patient_name": encounter["patient_name"],
        "provider_name": encounter["provider_name"],
        "status": encounter["status"],
        "encounter_type": profile_code,
        "encounter_type_label": (
            "Retina" if profile_code == "retina"
            else "Glaucoma" if profile_code == "glaucoma"
            else "Cataract" if profile_code == "cataract"
            else "Comprehensive"
        ),
        "visit_mode": encounter["visit_mode"],
        "visit_mode_label": VISIT_MODE_LABELS.get(
            encounter["visit_mode"], encounter["visit_mode"]
        ),
        "active_laterality": encounter["active_laterality"],
        "active_laterality_label": ACTIVE_LATERALITY_LABELS.get(
            encounter["active_laterality"], encounter["active_laterality"]
        ),
        "profile": {
            "code": profile.code,
            "label": profile.label,
            "panel_order": profile_order,
            "panel_labels": {c: PANEL_LABELS[c] for c in profile_order},
        },
        "emphasis": emphasis,
        "laterality_linked_panels": list(LATERALITY_LINKED_PANELS),
        "supported_visit_modes": [
            {"code": code, "label": label}
            for code, label in VISIT_MODE_LABELS.items()
        ],
        "supported_active_lateralities": [
            {"code": code, "label": label}
            for code, label in ACTIVE_LATERALITY_LABELS.items()
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclosure": _DISCLOSURE,
    }


def set_visit_mode(
    encounter_id: int, caller: Caller, visit_mode: Any
) -> dict[str, Any]:
    _assert_write_role(caller)
    mode = _enum("visit_mode", visit_mode, VALID_VISIT_MODES)
    with engine.begin() as conn:
        existing = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        conn.execute(
            sa_text(
                "UPDATE encounters SET visit_mode = :m WHERE id = :id"
            ),
            {"m": mode, "id": existing["id"]},
        )
    return resolve_state_for_encounter(encounter_id, caller)


def set_active_laterality(
    encounter_id: int, caller: Caller, active_laterality: Any
) -> dict[str, Any]:
    _assert_write_role(caller)
    lat = _enum(
        "active_laterality", active_laterality, VALID_ACTIVE_LATERALITIES
    )
    with engine.begin() as conn:
        existing = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        conn.execute(
            sa_text(
                "UPDATE encounters SET active_laterality = :l "
                "WHERE id = :id"
            ),
            {"l": lat, "id": existing["id"]},
        )
    return resolve_state_for_encounter(encounter_id, caller)


__all__ = [
    "WorkspaceStateError",
    "VALID_VISIT_MODES",
    "VISIT_MODE_LABELS",
    "VALID_ACTIVE_LATERALITIES",
    "ACTIVE_LATERALITY_LABELS",
    "VISIT_MODE_EMPHASIS",
    "LATERALITY_LINKED_PANELS",
    "resolve_state_for_encounter",
    "set_visit_mode",
    "set_active_laterality",
]
