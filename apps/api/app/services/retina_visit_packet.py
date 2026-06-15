"""Phase 77 — Retina Visit Packet builder service.

Wraps the Phase 76 retina-visit-summary aggregator with packet
metadata (schema_version, generated_at, per-artifact metadata-only
content hashes, explicit safety-boundary statements) so a buyer can
download / share a single self-describing JSON document that captures
the visit's current state.

Hard rule (inherited from Phase 76):
    The packet body never contains clinical free text. Every section
    is metadata only — see app.services.retina_visit_summary for the
    enforced FORBIDDEN_CLINICAL_COLUMNS set.

The packet is reproducible: same encounter state → same packet (modulo
the generated_at timestamp). Artifact hashes are computed over a
canonical metadata-only projection so callers can prove that the
artifact rows referenced by ref_id haven't changed since the packet
was issued.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.auth import Caller
from app.services.retina_visit_summary import SummaryError, build_summary

PACKET_SCHEMA_VERSION = "chartnav.retina_visit_packet/1.0"


SAFETY_BOUNDARIES: list[dict[str, Any]] = [
    {
        "key": "not_certified_ehr",
        "asserted": True,
        "statement": "ChartNav is not a certified electronic health record.",
    },
    {
        "key": "not_ehr_replacement",
        "asserted": True,
        "statement": (
            "ChartNav does not replace the practice's existing EHR. "
            "Integrations are gated and operate read-only by default."
        ),
    },
    {
        "key": "no_autonomous_diagnosis",
        "asserted": True,
        "statement": (
            "ChartNav does not diagnose. Every clinical artifact in this "
            "packet was drafted from clinician-entered findings and is "
            "subject to provider review and signature."
        ),
    },
    {
        "key": "no_autonomous_image_interpretation",
        "asserted": True,
        "statement": (
            "ChartNav does not interpret fundus photographs, OCT scans, "
            "visual fields, or any imaging modality. Fundus diagrams are "
            "drafted from clinician-entered findings, not from photo "
            "interpretation."
        ),
    },
    {
        "key": "no_autonomous_billing_or_coding",
        "asserted": True,
        "statement": (
            "ChartNav does not bill, code, or transmit any billing or "
            "coding claim. No CPT, ICD-10, or HCPCS workflow is part of "
            "this product."
        ),
    },
    {
        "key": "no_autonomous_signing",
        "asserted": True,
        "statement": (
            "Signing and locking every clinical artifact requires explicit "
            "provider attestation. No automated signing exists."
        ),
    },
    {
        "key": "provider_review_required",
        "asserted": True,
        "statement": (
            "Every clinical artifact (vitals, visit draft, fundus chart) "
            "requires provider review and signature before it can be "
            "considered final."
        ),
    },
    {
        "key": "no_real_phi",
        "asserted": True,
        "statement": (
            "This packet was generated from the local fake-data demo "
            "environment. ChartNav does not process real protected health "
            "information in this build."
        ),
    },
    {
        "key": "metadata_only_audit_trail",
        "asserted": True,
        "statement": (
            "The evidence timeline in this packet contains only metadata: "
            "artifact type, event type, actor display name and role, "
            "timestamp, ref id, and optional counts. The audit trail does "
            "not store clinical free text such as transcripts, BP/IOP/VA "
            "values, chief complaint, HPI, or findings text."
        ),
    },
]


def _hash_artifact(section: dict[str, Any], section_name: str) -> dict[str, Any]:
    """Compute a short stable hash over the metadata-only projection
    of one artifact section. Identical section state → identical hash.

    This is a content-integrity hash, not a security-grade signature —
    it lets a packet reviewer verify the artifact metadata referenced
    by ``latest_id`` hasn't shifted since packet issuance.
    """
    projection = {
        "section": section_name,
        "count": section.get("count"),
        "latest_id": section.get("latest_id"),
        "latest_status": section.get("latest_status"),
        "latest_signed_at": section.get("latest_signed_at"),
        "latest_finalized_at": section.get("latest_finalized_at"),
        "latest_reviewed_at": section.get("latest_reviewed_at"),
        "latest_warning_count": section.get("latest_warning_count"),
        "latest_element_count": section.get("latest_element_count"),
        "latest_laterality": section.get("latest_laterality"),
    }
    blob = json.dumps(projection, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()
    return {
        "section": section_name,
        "algorithm": "sha256",
        "hash": digest,
        "hash_short": digest[:12],
    }


def _build_medication_safety_section(summary: dict[str, Any]) -> dict[str, Any]:
    """Phase 85 — embed the metadata-only medication safety summary in
    the packet. Pure counts; no clinical narrative; no prescription
    workflow."""
    from app.services.medications import medication_safety_summary

    pid = summary.get("patient_id")
    org = summary.get("organization_id")
    if not isinstance(pid, int) or not isinstance(org, int):
        return {
            "active_medication_count": 0,
            "preservative_burden": 0,
            "refill_gap_count": 0,
            "refill_gap_medication_ids": [],
            "allergy_count": 0,
            "medication_classes_present": [],
            "insufficient_data": True,
        }
    return medication_safety_summary(pid, org)


def _build_advanced_clinical_intelligence_section(
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Phase 92 — embed the metadata-only advanced clinical intelligence
    summary in the packet. Counts only; no clinical narrative; no
    autonomous conclusion."""
    from app.services.advanced_clinical_intelligence import summary_for_packet

    eid = summary.get("encounter_id")
    org = summary.get("organization_id")
    if not isinstance(eid, int) or not isinstance(org, int):
        return {
            "retina_present": False,
            "glaucoma_present": False,
            "cataract_present": False,
            "fhir_export_renderable": False,
            "submission_status": "not_submitted",
            "boundary_note": (
                "Advanced clinical intelligence section is metadata only — "
                "no clinical narrative, no autonomous conclusion."
            ),
            "insufficient_data": True,
        }
    return summary_for_packet(eid, org)


def build_packet(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Build the retina visit packet for one encounter.

    Returns a dict with this top-level shape:

        {
          "schema_version": "chartnav.retina_visit_packet/1.0",
          "generated_at": "...",
          "demo_mode": True,
          "encounter": {...metadata...},
          "intake": {...vitals summary...},
          "fundus": {...fundus summary...},
          "visit_draft": {...visit-draft summary...},
          "review_sign_lock": {
              "vitals_signed": bool,
              "visit_draft_signed": bool,
              "fundus_signed": bool,
              "all_signed": bool,
              "blockers": [...],
          },
          "evidence_timeline": [...metadata-only events...],
          "artifact_hashes": [
              {section, algorithm, hash, hash_short},
              ...
          ],
          "role_capabilities": {...},
          "safety_boundaries": [{key, asserted, statement}, ...],
          "audit_disclosure": "...verbatim from summary...",
        }

    Raises ``SummaryError`` on cross-org or unknown encounter (same
    error semantics as ``build_summary``).
    """
    summary = build_summary(encounter_id, caller)

    vitals_sec = summary["vitals"]
    visit_sec = summary["visit_draft"]
    fundus_sec = summary["fundus"]

    vitals_signed = vitals_sec.get("latest_status") == "signed"
    visit_signed = visit_sec.get("latest_status") == "finalized"
    fundus_signed = fundus_sec.get("latest_status") == "signed"
    all_signed = (
        vitals_sec.get("count", 0) > 0
        and visit_sec.get("count", 0) > 0
        and fundus_sec.get("count", 0) > 0
        and vitals_signed
        and visit_signed
        and fundus_signed
    )

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "encounter": {
            "id": summary["encounter_id"],
            "patient_id": summary["patient_id"],
            "patient_identifier": summary["patient_identifier"],
            "patient_name": summary["patient_name"],
            "organization_id": summary["organization_id"],
            "status": summary["encounter_status"],
            "started_at": summary["encounter_started_at"],
        },
        "intake": vitals_sec,
        "visit_draft": visit_sec,
        "fundus": fundus_sec,
        "review_sign_lock": {
            "vitals_signed": vitals_signed,
            "visit_draft_signed": visit_signed,
            "fundus_signed": fundus_signed,
            "all_signed": all_signed,
            "blockers": summary["blockers"],
        },
        "evidence_timeline": summary["evidence_timeline"],
        "disease_staging_summary": summary.get(
            "disease_staging_summary",
            {
                "record_count": 0,
                "latest_by_diagnosis": [],
                "insufficient_data": True,
            },
        ),
        "medication_safety_summary": _build_medication_safety_section(summary),
        "quality_intelligence_summary": summary.get(
            "quality_intelligence_summary",
            {
                "total_count": 0,
                "applicable_count": 0,
                "incomplete_count": 0,
                "completed_count": 0,
                "internal_demo_specs_present": False,
                "submission_status": "not_submitted",
                "insufficient_data": True,
            },
        ),
        "imaging_metadata_summary": summary.get(
            "imaging_metadata_summary",
            {
                "total_count": 0,
                "reviewed_count": 0,
                "unreviewed_count": 0,
                "by_modality_group": {},
                "modality_groups_present": [],
                "summary_hash": "",
                "insufficient_data": True,
            },
        ),
        "ophthalmic_medication_safety_summary": summary.get(
            "ophthalmic_medication_safety_summary",
            {
                "active_medication_count": 0,
                "preservative_burden_count": 0,
                "refill_gap_count": 0,
                "active_event_count": 0,
                "acknowledged_event_count": 0,
                "resolved_event_count": 0,
                "total_event_count": 0,
                "internal_demo_rules_present": False,
                "submission_status": "not_submitted",
                "boundary_note": (
                    "Medication safety content is provider-reviewed "
                    "workflow support only."
                ),
                "insufficient_data": True,
            },
        ),
        "advanced_clinical_intelligence_summary": _build_advanced_clinical_intelligence_section(
            summary
        ),
        "artifact_hashes": [
            _hash_artifact(vitals_sec, "intake"),
            _hash_artifact(visit_sec, "visit_draft"),
            _hash_artifact(fundus_sec, "fundus"),
        ],
        "role_capabilities": summary["role_capabilities"],
        "safety_boundaries": SAFETY_BOUNDARIES,
        "audit_disclosure": summary["audit_disclosure"],
    }


__all__ = ["build_packet", "PACKET_SCHEMA_VERSION", "SAFETY_BOUNDARIES", "SummaryError"]
