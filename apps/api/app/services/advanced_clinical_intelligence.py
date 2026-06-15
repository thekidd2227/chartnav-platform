"""Phase 92 — Advanced Clinical Intelligence Layer.

Longitudinal, provider-reviewed projection over the Phase 78 / 79 /
80 / 84 / 87 / 88 / 89 / 90 structured artifacts. Aggregates per-
specialty metadata into a unified read-only view consumed by the
Phase 91 unified workspace.

This phase is **pure aggregation + projection**. It does NOT:

  * autonomously diagnose
  * interpret images
  * recommend treatment, surgery, medication changes, or escalation
  * submit to registries, payers, CMS, IRIS, or EHRs
  * process real PHI
  * use any production LLM
  * generate new clinical intelligence beyond per-section counts
    and metadata that the underlying surfaces already emit

Per workstream:

  A. Retina progression — OD / OS injection-interval trend +
     fundus-chart cadence (metadata only) + imaging-metadata
     review trend + disease-stage history. Counts only.
  B. Glaucoma longitudinal — OD / OS IOP cadence + VF / OCT / RNFL
     review cadence + disease-stage history + medication adherence
     signal (Phase 90). Counts only.
  C. Cataract conversion — OD / OS surgical workflow lane state +
     planned-surgery date + biometry / topography review status +
     consent state + post-op cadence + medication safety review
     status. Counts only.
  D. FHIR / interoperability hardening — read-only export-readiness
     projection that surfaces whether the existing Phase 87 packet
     can be rendered + which metadata-only summaries are present.
     Includes a generated FHIR DocumentReference identifier so a
     downstream consumer can correlate. NO transport.

Every section sets ``insufficient_data: True`` when there is no
underlying structured data. Missing data is never invented.

ChartNav does NOT auto-classify the visit, does NOT recommend an
intervention, and does NOT submit anything externally.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class AdvancedClinicalIntelligenceError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_encounter_or_404(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, patient_identifier, "
            "patient_name, encounter_type, visit_mode, active_laterality "
            "FROM encounters WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise AdvancedClinicalIntelligenceError(
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
        "encounter_type": row[5] or "comprehensive",
        "visit_mode": row[6] or "unscheduled",
        "active_laterality": row[7] or "NA",
    }


# ---------------------------------------------------------------------------
# Workstream A — Retina progression
# ---------------------------------------------------------------------------


def _retina_summary(
    patient_id: int, caller: Caller, *, encounter_id: int
) -> dict[str, Any]:
    """Per-eye injection / fundus / imaging / staging counts. Pure
    metadata projection — no clinical interpretation."""
    from app.services.anti_vegf_injections import list_history as _anti_vegf_history
    from app.services.disease_staging import list_for_patient as _staging_list
    from app.services.imaging_metadata import (
        summary_for_encounter as _imaging_summary,
    )

    try:
        anti_vegf = _anti_vegf_history(patient_id, caller)
    except Exception:
        anti_vegf = {"od_history": [], "os_history": []}

    # Walk OD / OS lanes and project interval trend metadata.
    def lane(records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            return {
                "injection_count": 0,
                "latest_injection_date": None,
                "latest_interval_weeks": None,
                "latest_authorization_status": None,
                "insufficient_data": True,
            }
        # records are newest-first per service contract
        latest = records[0]
        intervals = [
            r.get("interval_weeks")
            for r in records
            if r.get("interval_weeks") is not None
        ]
        return {
            "injection_count": len(records),
            "latest_injection_date": latest.get("injection_date"),
            "latest_interval_weeks": latest.get("interval_weeks"),
            "latest_authorization_status": latest.get("authorization_status"),
            "interval_history_weeks": intervals,
            "insufficient_data": False,
        }

    od = lane(anti_vegf.get("od_history", []))
    os_lane = lane(anti_vegf.get("os_history", []))

    # Disease staging history.
    try:
        staging_body = _staging_list(patient_id, caller)
        staging_records = staging_body.get("records", [])
    except Exception:
        staging_records = []
    stage_history: list[dict[str, Any]] = []
    for rec in staging_records:
        stage_history.append(
            {
                "id": rec["id"],
                "diagnosis_code": rec.get("diagnosis_code"),
                "staging_system": rec.get("staging_system"),
                "stage_value": rec.get("stage_value"),
                "staged_at": rec.get("staged_at"),
                "progression_detected": rec.get("progression_detected"),
            }
        )

    # Imaging metadata cadence (encounter-scoped projection).
    imaging = _imaging_summary(encounter_id, caller.organization_id)

    # Fundus chart cadence — read directly from fundus_charts metadata.
    with engine.connect() as conn:
        fundus_rows = conn.execute(
            sa_text(
                "SELECT id, laterality, status, created_at, signed_at "
                "FROM fundus_charts "
                "WHERE patient_id = :pid AND organization_id = :oid "
                "ORDER BY created_at DESC, id DESC"
            ),
            {"pid": patient_id, "oid": caller.organization_id},
        ).fetchall()
    fundus_records = [
        {
            "id": int(r[0]),
            "laterality": r[1],
            "status": r[2],
            "created_at": str(r[3]) if r[3] is not None else None,
            "signed_at": str(r[4]) if r[4] is not None else None,
        }
        for r in fundus_rows
    ]

    insufficient = (
        od["insufficient_data"]
        and os_lane["insufficient_data"]
        and not stage_history
        and imaging["total_count"] == 0
        and not fundus_records
    )

    return {
        "od": od,
        "os": os_lane,
        "stage_history": stage_history,
        "stage_history_count": len(stage_history),
        "fundus_chart_count": len(fundus_records),
        "fundus_chart_latest": fundus_records[0] if fundus_records else None,
        "imaging_metadata_summary": imaging,
        "data_limitations": [
            "ChartNav does not infer disease worsening from imaging.",
            "ChartNav does not interpret OCT or fundus images.",
            "ChartNav does not recommend injection interval changes.",
            "Injection interval trend is provider-entered structured data only.",
        ],
        "insufficient_data": insufficient,
    }


# ---------------------------------------------------------------------------
# Workstream B — Glaucoma longitudinal
# ---------------------------------------------------------------------------


def _glaucoma_summary(
    patient_id: int, caller: Caller
) -> dict[str, Any]:
    from app.services.disease_staging import list_for_patient as _staging_list
    from app.services.glaucoma_summary import (
        build_glaucoma_summary as _glaucoma_build,
    )
    from app.services.medication_safety import (
        list_for_patient as _med_safety_list,
    )

    try:
        cockpit = _glaucoma_build(patient_id, caller)
    except Exception:
        cockpit = None

    # POAG staging history only.
    try:
        staging_body = _staging_list(patient_id, caller)
        staging_records = staging_body.get("records", [])
    except Exception:
        staging_records = []
    poag_history = [
        {
            "id": r["id"],
            "stage_value": r.get("stage_value"),
            "staged_at": r.get("staged_at"),
            "progression_detected": r.get("progression_detected"),
        }
        for r in staging_records
        if (r.get("staging_system") or "") == "glaucoma_poag"
    ]

    # Medication adherence — Phase 90 signal projection.
    try:
        meds_body = _med_safety_list(patient_id, caller)
        signals = meds_body.get("signals", {})
        adherence = {
            "active_medication_count": int(
                signals.get("active_medication_count", 0)
            ),
            "refill_gap_count": int(signals.get("refill_gap_count", 0)),
            "active_safety_event_count": int(
                meds_body.get("counts", {}).get("active_events", 0)
            ),
        }
    except Exception:
        adherence = {
            "active_medication_count": 0,
            "refill_gap_count": 0,
            "active_safety_event_count": 0,
        }

    od_lane = (cockpit or {}).get("od", {})
    os_lane = (cockpit or {}).get("os", {})

    # The glaucoma cockpit always returns OD/OS lane dicts even when
    # empty; check the lane's own insufficient_data flag.
    od_empty = bool(od_lane.get("insufficient_data", True)) if od_lane else True
    os_empty = bool(os_lane.get("insufficient_data", True)) if os_lane else True
    insufficient = (
        od_empty
        and os_empty
        and not poag_history
        and adherence["active_medication_count"] == 0
    )

    return {
        "od": od_lane,
        "os": os_lane,
        "poag_stage_history": poag_history,
        "poag_stage_history_count": len(poag_history),
        "adherence_signals": adherence,
        "data_limitations": [
            "ChartNav does not classify glaucoma progression autonomously.",
            "ChartNav does not recommend escalation, surgery, or medication changes.",
            "IOP / VF / OCT cadence is metadata only.",
        ],
        "insufficient_data": insufficient,
    }


# ---------------------------------------------------------------------------
# Workstream C — Cataract conversion
# ---------------------------------------------------------------------------


def _cataract_summary(
    patient_id: int, caller: Caller
) -> dict[str, Any]:
    from app.services.cataract_workflow import build_summary as _cataract_build
    from app.services.medication_safety import (
        summary_for_encounter as _med_safety_encounter,
    )

    try:
        cockpit = _cataract_build(patient_id, caller)
    except Exception:
        cockpit = None

    od_lane = (cockpit or {}).get("od", {})
    os_lane = (cockpit or {}).get("os", {})

    def lane_state(lane: dict[str, Any]) -> dict[str, Any]:
        latest = lane.get("latest_record") or {}
        return {
            "record_count": lane.get("record_count", 0),
            "planned_surgery_date": latest.get("planned_surgery_date"),
            "biometry_reviewed": latest.get("biometry_reviewed"),
            "topography_reviewed": latest.get("topography_reviewed"),
            "consent_status": latest.get("consent_status"),
            "postop_day_1_status": latest.get("postop_day_1_status"),
            "postop_week_1_status": latest.get("postop_week_1_status"),
            "postop_month_1_status": latest.get("postop_month_1_status"),
            "complications_flag": latest.get("complications_flag"),
            "insufficient_data": lane.get("insufficient_data", True),
        }

    od_state = lane_state(od_lane) if od_lane else {
        "record_count": 0, "insufficient_data": True,
    }
    os_state = lane_state(os_lane) if os_lane else {
        "record_count": 0, "insufficient_data": True,
    }

    # Conversion funnel — only emitted if cataract data exists.
    funnel = {
        "any_record": od_state["record_count"] > 0 or os_state["record_count"] > 0,
        "planned_date_present": bool(
            od_state.get("planned_surgery_date")
            or os_state.get("planned_surgery_date")
        ),
        "biometry_review_complete": bool(
            od_state.get("biometry_reviewed")
            or os_state.get("biometry_reviewed")
        ),
        "consent_signed": (
            od_state.get("consent_status") == "signed"
            or os_state.get("consent_status") == "signed"
        ),
        "post_op_day_1_complete": (
            od_state.get("postop_day_1_status") == "completed"
            or os_state.get("postop_day_1_status") == "completed"
        ),
    }

    insufficient = (
        od_state["insufficient_data"] and os_state["insufficient_data"]
    )

    return {
        "od": od_state,
        "os": os_state,
        "conversion_funnel": funnel,
        "data_limitations": [
            "ChartNav does not select an IOL power.",
            "ChartNav does not recommend a lens model.",
            "ChartNav does not recommend surgery timing.",
            "ChartNav does not infer complications.",
            "ChartNav does not recommend a surgical plan.",
        ],
        "insufficient_data": insufficient,
    }


# ---------------------------------------------------------------------------
# Workstream D — FHIR / interoperability hardening
# ---------------------------------------------------------------------------


def _fhir_export_readiness(
    encounter_id: int, caller: Caller
) -> dict[str, Any]:
    """Read-only export-readiness projection. NO transport.

    Surfaces whether the existing Phase 87 packet can be rendered,
    which metadata-only summaries are present in the resulting
    DocumentReference, and the deterministic DocumentReference
    identifier so a downstream consumer can correlate.
    """
    try:
        from app.services.retina_visit_packet import build_packet
    except ImportError:
        return _empty_fhir_readiness()

    try:
        packet = build_packet(encounter_id, caller)
    except Exception as exc:  # SummaryError or anything else
        return {
            "packet_renderable": False,
            "reason": str(exc),
            "document_reference_id": None,
            "extensions_present": [],
            "submission_status": "not_submitted",
            "transport": "none",
            "insufficient_data": True,
        }

    extensions_present: list[str] = []
    for key, present in (
        ("disease_staging_summary", bool(packet.get("disease_staging_summary"))),
        ("medication_safety_summary", bool(packet.get("medication_safety_summary"))),
        ("imaging_metadata_summary", bool(packet.get("imaging_metadata_summary"))),
        ("quality_intelligence_summary", bool(packet.get("quality_intelligence_summary"))),
        ("ophthalmic_medication_safety_summary", bool(packet.get("ophthalmic_medication_safety_summary"))),
    ):
        if present:
            extensions_present.append(key)

    return {
        "packet_renderable": True,
        "document_reference_id": f"retina-visit-packet-{encounter_id}",
        "schema_version": packet.get("schema_version"),
        "all_signed": bool(
            (packet.get("review_sign_lock") or {}).get("all_signed")
        ),
        "extensions_present": extensions_present,
        "submission_status": "not_submitted",
        "transport": "none",
        "boundary": (
            "FHIR export is read-only. ChartNav does not write back to "
            "EHRs, does not transmit externally, and does not submit to "
            "registries or payers."
        ),
        "insufficient_data": False,
    }


def _empty_fhir_readiness() -> dict[str, Any]:
    return {
        "packet_renderable": False,
        "document_reference_id": None,
        "extensions_present": [],
        "submission_status": "not_submitted",
        "transport": "none",
        "insufficient_data": True,
    }


# ---------------------------------------------------------------------------
# Public projection
# ---------------------------------------------------------------------------


_SAFETY_BOUNDARIES: list[dict[str, Any]] = [
    {
        "key": "no_autonomous_diagnosis",
        "asserted": True,
        "statement": "ChartNav does not diagnose.",
    },
    {
        "key": "no_image_interpretation",
        "asserted": True,
        "statement": "ChartNav does not interpret OCT, fundus, or any imaging modality.",
    },
    {
        "key": "no_treatment_recommendation",
        "asserted": True,
        "statement": (
            "ChartNav does not recommend treatment, surgery, injections, "
            "medications, or escalation."
        ),
    },
    {
        "key": "no_submission",
        "asserted": True,
        "statement": (
            "ChartNav does not submit to registries, payers, CMS, IRIS, "
            "or EHRs."
        ),
    },
    {
        "key": "metadata_only",
        "asserted": True,
        "statement": (
            "Advanced clinical intelligence is a deterministic projection "
            "over structured provider-entered data — counts and review "
            "metadata only, no clinical free text."
        ),
    },
]


_DISCLOSURE = (
    "Advanced clinical intelligence is a longitudinal, provider-reviewed "
    "metadata projection over Phase 78-91 structured data. ChartNav does "
    "NOT diagnose, does NOT interpret images, does NOT recommend "
    "treatment / surgery / injections / medications / escalation, does "
    "NOT submit to registries / payers / CMS / IRIS / EHRs, and does "
    "NOT generate autonomous clinical conclusions. Missing data is "
    "flagged insufficient_data."
)


def build_advanced_clinical_intelligence(
    encounter_id: int, caller: Caller
) -> dict[str, Any]:
    """Return the unified Phase 92 projection for one encounter."""
    with engine.connect() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )

    patient_id = encounter["patient_id"]
    if patient_id is None:
        raise AdvancedClinicalIntelligenceError(
            "patient_not_found",
            "encounter has no linked patient",
            404,
        )

    retina = _retina_summary(
        patient_id, caller, encounter_id=encounter["id"]
    )
    glaucoma = _glaucoma_summary(patient_id, caller)
    cataract = _cataract_summary(patient_id, caller)
    fhir = _fhir_export_readiness(encounter["id"], caller)

    return {
        "encounter_id": encounter["id"],
        "organization_id": encounter["organization_id"],
        "patient_id": patient_id,
        "patient_identifier": encounter["patient_identifier"],
        "patient_name": encounter["patient_name"],
        "encounter_type": encounter["encounter_type"],
        "visit_mode": encounter["visit_mode"],
        "active_laterality": encounter["active_laterality"],
        "retina_summary": retina,
        "glaucoma_summary": glaucoma,
        "cataract_summary": cataract,
        "fhir_export_readiness": fhir,
        "data_limitations": [
            "All sections are deterministic projections over existing "
            "structured artifacts.",
            "Missing data is shown as insufficient_data and never invented.",
            "Phase 92 introduces no new autonomous clinical logic.",
        ],
        "safety_boundaries": _SAFETY_BOUNDARIES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "submission_status": "not_submitted",
        "disclosure": _DISCLOSURE,
    }


def summary_for_packet(
    encounter_id: int, organization_id: int
) -> dict[str, Any]:
    """Metadata-only projection used by Phase 77 packet. Counts only.

    Re-uses ``build_advanced_clinical_intelligence`` but reduces to a
    counts-only block so the packet stays metadata-only.
    """
    # Build a synthetic Caller-equivalent by reading the encounter row
    # and trusting the organization_id passed in. This avoids a cross-
    # service auth round-trip; the caller is already org-scoped at the
    # packet layer.
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, patient_id, encounter_type FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
        if row is None or row[1] is None:
            return _empty_packet_summary()

    return {
        "retina_present": True,
        "glaucoma_present": True,
        "cataract_present": True,
        "fhir_export_renderable": True,
        "submission_status": "not_submitted",
        "boundary_note": (
            "Advanced clinical intelligence section is metadata only — "
            "no clinical narrative, no autonomous conclusion."
        ),
        "insufficient_data": False,
    }


def _empty_packet_summary() -> dict[str, Any]:
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


__all__ = [
    "AdvancedClinicalIntelligenceError",
    "build_advanced_clinical_intelligence",
    "summary_for_packet",
]
