"""Phase 87 — FHIR R4 Encounter adapter.

Read-only projection of `encounters` rows into a FHIR R4 Encounter
resource. Embeds workflow metadata (status, scheduled / started /
completed timestamps), Phase 86 subspecialty type (as a Coding on
encounter.type), provider as a `participant`, and the Phase 76
review-sign-lock state inside an `extension` array.

Hard rules:

  * Org isolation enforced; cross-org → 404 (no existence leak).
  * No mutation. Read-only adapter.
  * No clinical free text. Encounter resource carries metadata only —
    no findings, no HPI, no transcripts.
  * Sign-lock metadata embedded as a FHIR Extension so downstream
    consumers can read review state without parsing ChartNav-
    specific JSON.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine
from app.fhir.patient_adapter import FhirExportError


_ENCOUNTER_COLS = (
    "id",
    "organization_id",
    "location_id",
    "patient_identifier",
    "patient_name",
    "provider_name",
    "status",
    "patient_id",
    "provider_id",
    "external_ref",
    "external_source",
    "encounter_type",
    "scheduled_at",
    "started_at",
    "completed_at",
    "created_at",
)


# Map ChartNav workflow statuses to FHIR Encounter.status
#   http://hl7.org/fhir/R4/valueset-encounter-status.html
_STATUS_MAP = {
    "scheduled": "planned",
    "in_progress": "in-progress",
    "in-progress": "in-progress",
    "awaiting_review": "in-progress",
    "ready_to_sign": "in-progress",
    "signed": "finished",
    "completed": "finished",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown"
    return _STATUS_MAP.get(value.strip().lower(), "unknown")


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def _fetch_encounter(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any] | None:
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_ENCOUNTER_COLS)} FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_ENCOUNTER_COLS, row))


def _review_sign_lock_extension(packet_block: dict[str, Any]) -> dict[str, Any]:
    """Project the Phase 76 review/sign/lock booleans as a FHIR
    Extension. Boolean fields use the FHIR `valueBoolean` form."""
    return {
        "url": "https://chartnav.local/fhir/StructureDefinition/review-sign-lock",
        "extension": [
            {
                "url": "vitals_signed",
                "valueBoolean": bool(packet_block.get("vitals_signed")),
            },
            {
                "url": "visit_draft_signed",
                "valueBoolean": bool(packet_block.get("visit_draft_signed")),
            },
            {
                "url": "fundus_signed",
                "valueBoolean": bool(packet_block.get("fundus_signed")),
            },
            {
                "url": "all_signed",
                "valueBoolean": bool(packet_block.get("all_signed")),
            },
        ],
    }


def _workspace_profile_extension(profile_code: str) -> dict[str, Any]:
    return {
        "url": "https://chartnav.local/fhir/StructureDefinition/workspace-profile",
        "valueCode": profile_code,
    }


def build_encounter_resource(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Return a FHIR R4 Encounter resource for the given encounter.

    Raises ``FhirExportError`` with status 404 when the encounter does
    not exist in the caller's organization (no existence leak across
    tenants).
    """
    # Import locally to avoid a circular dependency at module import time.
    from app.services.retina_visit_packet import build_packet
    from app.services.retina_visit_summary import SummaryError

    with engine.connect() as conn:
        rec = _fetch_encounter(conn, encounter_id, caller.organization_id)
    if rec is None:
        raise FhirExportError(
            "encounter_not_found", "encounter not found", 404
        )

    period: dict[str, Any] = {}
    started = _iso(rec.get("started_at"))
    completed = _iso(rec.get("completed_at"))
    scheduled = _iso(rec.get("scheduled_at"))
    if started:
        period["start"] = started
    elif scheduled:
        period["start"] = scheduled
    if completed:
        period["end"] = completed

    encounter_type_code = rec.get("encounter_type") or "comprehensive"

    identifiers: list[dict[str, Any]] = [
        {
            "use": "usual",
            "system": "urn:chartnav:encounter-id",
            "value": str(rec["id"]),
        }
    ]
    if rec.get("external_ref"):
        identifiers.append(
            {
                "use": "secondary",
                "system": (
                    f"urn:chartnav:external:{rec.get('external_source') or 'unknown'}"
                ),
                "value": rec["external_ref"],
            }
        )

    # Best-effort review-sign-lock projection. If the packet fails
    # (e.g. seed data without scribe rows) we fall back to an
    # all-false extension so the Encounter resource remains
    # well-formed.
    rsl_block: dict[str, Any] = {
        "vitals_signed": False,
        "visit_draft_signed": False,
        "fundus_signed": False,
        "all_signed": False,
    }
    try:
        packet = build_packet(encounter_id, caller)
        rsl_block = packet.get("review_sign_lock", rsl_block)
    except SummaryError:
        # Encounter exists but packet cannot be built — keep defaults.
        pass

    participant: list[dict[str, Any]] = []
    provider_name = rec.get("provider_name")
    if provider_name:
        participant.append(
            {
                "type": [
                    {
                        "coding": [
                            {
                                "system": (
                                    "http://terminology.hl7.org/CodeSystem/"
                                    "v3-ParticipationType"
                                ),
                                "code": "ATND",
                                "display": "attender",
                            }
                        ]
                    }
                ],
                "individual": {"display": provider_name},
            }
        )

    resource: dict[str, Any] = {
        "resourceType": "Encounter",
        "id": str(rec["id"]),
        "meta": {
            "source": (
                f"urn:chartnav:organization:{rec['organization_id']}"
            ),
        },
        "identifier": identifiers,
        "status": _normalize_status(rec.get("status")),
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "type": [
            {
                "coding": [
                    {
                        "system": (
                            "https://chartnav.local/fhir/CodeSystem/encounter-type"
                        ),
                        "code": encounter_type_code,
                        "display": encounter_type_code,
                    }
                ]
            }
        ],
        "subject": {
            "reference": (
                f"Patient/{rec['patient_id']}" if rec.get("patient_id") else None
            ),
            "display": rec.get("patient_name") or rec["patient_identifier"],
        },
        "participant": participant,
        "extension": [
            _review_sign_lock_extension(rsl_block),
            _workspace_profile_extension(encounter_type_code),
        ],
    }

    # Strip None subject reference if patient_id is absent.
    if resource["subject"]["reference"] is None:
        del resource["subject"]["reference"]

    if period:
        resource["period"] = period

    return resource


__all__ = ["build_encounter_resource"]
