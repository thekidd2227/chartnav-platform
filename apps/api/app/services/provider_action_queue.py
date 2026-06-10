"""Phase 81 — Provider Action Item Queue (cross-specialty aggregator).

Aggregates deterministic workflow signals from the three Phase 2
surfaces plus the Phase 1 signed-lock workflow into a single
provider-facing triage queue:

  * anti_vegf      — Phase 78 readiness queue buckets
  * glaucoma       — Phase 79 imaging metadata review state +
                     data-completeness signals
  * cataract       — Phase 80 pre-op signal gaps + post-op cadence
  * visit_summary  — unsigned visit drafts (scribe sessions)
  * signed_lock    — unsigned vitals workups + fundus charts

This is NOT autonomous clinical prioritization. Every bucket
assignment is a documented deterministic rule over provider-entered
structured data. ChartNav does not diagnose, does not recommend
treatment or surgery, does not interpret images, and does not decide
clinical urgency — the buckets mirror the operational rules the
practice already uses (due dates, missing attestations, unsigned
artifacts).

Priority buckets (deterministic, documented):

  same_day:
    * anti-VEGF injection due today (provider-entered cadence)
    * anti-VEGF injection overdue
    * anti-VEGF authorization expired
    * cataract post-op checkpoint marked 'missed' (provider-entered)
  this_week:
    * anti-VEGF injection due within 7 days
    * anti-VEGF authorization pending
    * glaucoma VF / OCT study in 'ready_for_review'
    * cataract planned surgery with incomplete pre-op signals
    * cataract provider-entered complications flag set
  routine:
    * unsigned vitals workup (signed_lock)
    * unfinalized visit draft (visit_summary)
    * unsigned fundus chart (signed_lock)
  informational:
    * glaucoma lane with IOP recorded but no VF and no OCT RNFL
      metadata on file (insufficient_data)

Hard rules (matching every Phase 2 surface):
  * No provider free text is ever aggregated into the queue — labels
    and details are templated metadata strings only.
  * Missing data is labeled ``insufficient_data``; values are never
    invented.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine
from app.services.anti_vegf_injections import build_readiness_queue
from app.services.glaucoma_summary import (
    OCT_RNFL_MODALITIES,
    VISUAL_FIELD_MODALITIES,
)

PRIORITY_BUCKETS = ("same_day", "this_week", "routine", "informational")

_GLAUCOMA_REVIEW_MODALITIES = VISUAL_FIELD_MODALITIES + OCT_RNFL_MODALITIES + (
    "oct_macula",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _patient_names(conn, org_id: int) -> dict[int, dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, patient_identifier, first_name, last_name "
            "FROM patients WHERE organization_id = :oid"
        ),
        {"oid": org_id},
    ).fetchall()
    out: dict[int, dict[str, Any]] = {}
    for pid, pident, first, last in rows:
        name_parts = [p for p in (first, last) if p]
        out[int(pid)] = {
            "patient_identifier": pident,
            "patient_name": " ".join(name_parts) if name_parts else None,
        }
    return out


def _item(
    *,
    item_id: str,
    patient_id: int,
    patients: dict[int, dict[str, Any]],
    specialty_source: str,
    category: str,
    label: str,
    detail: str,
    priority_bucket: str,
    status: str,
    encounter_id: int | None = None,
    laterality: str | None = None,
    source_artifact_id: int | None = None,
    created_at: str | None = None,
    due_at: str | None = None,
    insufficient_data: bool = False,
    requires_provider_review: bool = True,
) -> dict[str, Any]:
    meta = patients.get(patient_id, {})
    return {
        "item_id": item_id,
        "patient_id": patient_id,
        "patient_identifier": meta.get("patient_identifier"),
        "patient_name": meta.get("patient_name"),
        "encounter_id": encounter_id,
        "laterality": laterality,
        "specialty_source": specialty_source,
        "category": category,
        "label": label,
        "detail": detail,
        "status": status,
        "priority_bucket": priority_bucket,
        "source_artifact_id": source_artifact_id,
        "created_at": created_at,
        "due_at": due_at,
        "insufficient_data": insufficient_data,
        "requires_provider_review": requires_provider_review,
    }


# ---------------------------------------------------------------------------
# Source 1 — anti-VEGF (reuses the Phase 78 readiness queue).
# ---------------------------------------------------------------------------

_ANTI_VEGF_BUCKET_MAP = {
    # phase-78 bucket -> (queue bucket, category, label template)
    "due_today": ("same_day", "injection_due_today", "Injection due today"),
    "overdue": ("same_day", "injection_overdue", "Injection overdue"),
    "authorization_expired": (
        "same_day",
        "authorization_expired",
        "Authorization expired",
    ),
    "due_this_week": (
        "this_week",
        "injection_due_this_week",
        "Injection due this week",
    ),
    "authorization_pending": (
        "this_week",
        "authorization_pending",
        "Authorization pending",
    ),
}


def _anti_vegf_items(
    caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    queue = build_readiness_queue(caller)
    items: list[dict[str, Any]] = []
    for src_bucket, entries in queue["buckets"].items():
        mapping = _ANTI_VEGF_BUCKET_MAP.get(src_bucket)
        if mapping is None:
            continue
        bucket, category, label = mapping
        for e in entries:
            items.append(
                _item(
                    item_id=f"anti_vegf:{category}:{e['injection_id']}",
                    patient_id=int(e["patient_id"]),
                    patients=patients,
                    encounter_id=e.get("encounter_id"),
                    laterality=e.get("eye"),
                    specialty_source="anti_vegf",
                    category=category,
                    label=label,
                    detail=(
                        f"Provider-entered cadence for {e.get('eye')}: "
                        f"last injection {e.get('injection_date')}, "
                        f"next due {e.get('next_due_date') or 'not set'}, "
                        f"authorization {e.get('authorization_status')}."
                    ),
                    status=src_bucket,
                    priority_bucket=bucket,
                    source_artifact_id=e.get("injection_id"),
                    due_at=e.get("next_due_date"),
                )
            )
    return items


# ---------------------------------------------------------------------------
# Source 2 — glaucoma (imaging review state + completeness signals).
# ---------------------------------------------------------------------------


def _glaucoma_items(
    conn, caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    placeholders = ", ".join(f":m{i}" for i in range(len(_GLAUCOMA_REVIEW_MODALITIES)))
    params: dict[str, Any] = {"oid": caller.organization_id}
    for i, m in enumerate(_GLAUCOMA_REVIEW_MODALITIES):
        params[f"m{i}"] = m

    # this_week — VF / OCT studies sitting in ready_for_review.
    rows = conn.execute(
        sa_text(
            "SELECT id, patient_id, encounter_id, modality, eye, "
            "captured_at, created_at "
            f"FROM imaging_studies WHERE organization_id = :oid "
            f"AND modality IN ({placeholders}) "
            "AND status = 'ready_for_review' ORDER BY id"
        ),
        params,
    ).fetchall()
    for sid, pid, eid, modality, eye, captured_at, created_at in rows:
        items.append(
            _item(
                item_id=f"glaucoma:imaging_review_pending:{sid}",
                patient_id=int(pid),
                patients=patients,
                encounter_id=int(eid) if eid is not None else None,
                laterality=eye,
                specialty_source="glaucoma",
                category="imaging_review_pending",
                label="Imaging study ready for review",
                detail=(
                    f"{modality} study captured "
                    f"{_iso(captured_at) or 'date not recorded'} is in "
                    "ready_for_review and awaits provider review."
                ),
                status="ready_for_review",
                priority_bucket="this_week",
                source_artifact_id=int(sid),
                created_at=_iso(created_at),
            )
        )

    # informational — IOP recorded but no VF and no OCT RNFL metadata.
    vf_csv = ", ".join(f"'{m}'" for m in VISUAL_FIELD_MODALITIES)
    rnfl_csv = ", ".join(f"'{m}'" for m in OCT_RNFL_MODALITIES)
    rows = conn.execute(
        sa_text(
            "SELECT DISTINCT v.patient_id "
            "FROM visit_vitals_workups v "
            "WHERE v.organization_id = :oid "
            "AND (v.iop_od IS NOT NULL OR v.iop_os IS NOT NULL) "
            "AND v.patient_id IS NOT NULL "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM imaging_studies s WHERE s.patient_id = v.patient_id "
            f" AND s.organization_id = :oid AND s.modality IN ({vf_csv})"
            ") "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM imaging_studies s WHERE s.patient_id = v.patient_id "
            f" AND s.organization_id = :oid AND s.modality IN ({rnfl_csv})"
            ")"
        ),
        {"oid": caller.organization_id},
    ).fetchall()
    for (pid,) in rows:
        items.append(
            _item(
                item_id=f"glaucoma:data_incomplete:{int(pid)}",
                patient_id=int(pid),
                patients=patients,
                laterality="OU",
                specialty_source="glaucoma",
                category="glaucoma_data_incomplete",
                label="IOP on file without VF / OCT RNFL metadata",
                detail=(
                    "IOP measurements exist but no visual-field or OCT RNFL "
                    "study metadata is on file. Insufficient data for the "
                    "glaucoma cockpit lanes."
                ),
                status="insufficient_data",
                priority_bucket="informational",
                insufficient_data=True,
            )
        )

    return items


# ---------------------------------------------------------------------------
# Source 3 — cataract (pre-op gaps + post-op cadence + complications flag).
# ---------------------------------------------------------------------------


def _cataract_items(
    conn, caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, patient_id, encounter_id, surgery_eye, "
            "planned_surgery_date, biometry_reviewed, topography_reviewed, "
            "consent_status, postop_day_1_status, postop_week_1_status, "
            "postop_month_1_status, complications_flag, created_at "
            "FROM cataract_workflow_records WHERE organization_id = :oid "
            "ORDER BY patient_id, surgery_eye, id DESC"
        ),
        {"oid": caller.organization_id},
    ).fetchall()

    # Latest row per (patient, eye) only.
    seen: set[tuple[int, str]] = set()
    items: list[dict[str, Any]] = []
    for (
        rid, pid, eid, eye, planned, biometry, topo, consent,
        pd1, pw1, pm1, comp_flag, created_at,
    ) in rows:
        key = (int(pid), eye)
        if key in seen:
            continue
        seen.add(key)

        common = {
            "patient_id": int(pid),
            "patients": patients,
            "encounter_id": int(eid) if eid is not None else None,
            "laterality": eye,
            "specialty_source": "cataract",
            "source_artifact_id": int(rid),
            "created_at": _iso(created_at),
        }

        # same_day — provider-entered 'missed' post-op checkpoint.
        missed = [
            name
            for name, val in (
                ("day 1", pd1), ("week 1", pw1), ("month 1", pm1)
            )
            if val == "missed"
        ]
        if missed:
            items.append(
                _item(
                    item_id=f"cataract:postop_checkpoint_missed:{rid}",
                    category="postop_checkpoint_missed",
                    label="Post-op checkpoint marked missed",
                    detail=(
                        f"Provider-entered post-op status for {eye}: "
                        f"{', '.join(missed)} checkpoint(s) marked missed."
                    ),
                    status="missed",
                    priority_bucket="same_day",
                    **common,
                )
            )

        # this_week — planned surgery with incomplete pre-op signals.
        if planned is not None:
            gaps = []
            if not biometry:
                gaps.append("biometry not reviewed")
            if not topo:
                gaps.append("topography not reviewed")
            if consent != "signed":
                gaps.append(f"consent {consent}")
            if gaps:
                items.append(
                    _item(
                        item_id=f"cataract:preop_signals_incomplete:{rid}",
                        category="preop_signals_incomplete",
                        label="Pre-op signals incomplete for planned surgery",
                        detail=(
                            f"Surgery planned {_iso(planned)} for {eye}; "
                            f"open signals: {', '.join(gaps)}."
                        ),
                        status="incomplete",
                        priority_bucket="this_week",
                        due_at=_iso(planned),
                        insufficient_data=True,
                        **common,
                    )
                )

        # this_week — provider-entered complications flag.
        if comp_flag:
            items.append(
                _item(
                    item_id=f"cataract:complications_flag:{rid}",
                    category="provider_entered_complications_flag",
                    label="Provider-entered complications flag set",
                    detail=(
                        f"Complications flag set by the provider for {eye}. "
                        "Details live on the per-record view; ChartNav does "
                        "not interpret the note."
                    ),
                    status="flagged",
                    priority_bucket="this_week",
                    **common,
                )
            )

    return items


# ---------------------------------------------------------------------------
# Source 4 — unsigned artifacts (visit_summary + signed_lock).
# ---------------------------------------------------------------------------


def _unsigned_artifact_items(
    conn, caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    rows = conn.execute(
        sa_text(
            "SELECT id, patient_id, encounter_id, status, created_at "
            "FROM visit_vitals_workups WHERE organization_id = :oid "
            "AND signed_at IS NULL AND status != 'superseded' ORDER BY id"
        ),
        {"oid": caller.organization_id},
    ).fetchall()
    for wid, pid, eid, status, created_at in rows:
        if pid is None:
            continue
        items.append(
            _item(
                item_id=f"signed_lock:vitals_unsigned:{wid}",
                patient_id=int(pid),
                patients=patients,
                encounter_id=int(eid) if eid is not None else None,
                specialty_source="signed_lock",
                category="vitals_unsigned",
                label="Vitals workup awaiting provider signature",
                detail=(
                    f"Vitals workup #{wid} is {status} and has not been "
                    "signed. Provider review and signature required."
                ),
                status=status,
                priority_bucket="routine",
                source_artifact_id=int(wid),
                created_at=_iso(created_at),
            )
        )

    rows = conn.execute(
        sa_text(
            "SELECT id, patient_id, encounter_id, status, created_at "
            "FROM scribe_sessions WHERE organization_id = :oid "
            "AND status NOT IN ('finalized', 'discarded') ORDER BY id"
        ),
        {"oid": caller.organization_id},
    ).fetchall()
    for sid, pid, eid, status, created_at in rows:
        items.append(
            _item(
                item_id=f"visit_summary:visit_draft_unsigned:{sid}",
                patient_id=int(pid),
                patients=patients,
                encounter_id=int(eid) if eid is not None else None,
                specialty_source="visit_summary",
                category="visit_draft_unsigned",
                label="Visit draft awaiting provider sign-off",
                detail=(
                    f"Visit draft #{sid} is {status} and has not been "
                    "finalized. Provider review and signature required."
                ),
                status=status,
                priority_bucket="routine",
                source_artifact_id=int(sid),
                created_at=_iso(created_at),
            )
        )

    rows = conn.execute(
        sa_text(
            "SELECT id, patient_id, encounter_id, laterality, status, created_at "
            "FROM fundus_charts WHERE organization_id = :oid "
            "AND signed_at IS NULL ORDER BY id"
        ),
        {"oid": caller.organization_id},
    ).fetchall()
    for fid, pid, eid, laterality, status, created_at in rows:
        items.append(
            _item(
                item_id=f"signed_lock:fundus_unsigned:{fid}",
                patient_id=int(pid),
                patients=patients,
                encounter_id=int(eid) if eid is not None else None,
                laterality=laterality,
                specialty_source="signed_lock",
                category="fundus_unsigned",
                label="Fundus chart awaiting provider signature",
                detail=(
                    f"Fundus chart #{fid} ({laterality}) is {status} and has "
                    "not been signed. Provider review and signature required."
                ),
                status=status,
                priority_bucket="routine",
                source_artifact_id=int(fid),
                created_at=_iso(created_at),
            )
        )

    return items


# ---------------------------------------------------------------------------
# Public entrypoint.
# ---------------------------------------------------------------------------


def _staging_items(
    caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Phase 84 — informational items for patients with retina/glaucoma
    activity but no provider-entered disease-staging record. Always
    'informational' / never tier 1."""
    from app.services.disease_staging import patients_missing_recent_stage

    items: list[dict[str, Any]] = []
    for entry in patients_missing_recent_stage(caller.organization_id):
        pid = int(entry["patient_id"])
        items.append(
            _item(
                item_id=f"staging:missing:{pid}",
                patient_id=pid,
                patients=patients,
                specialty_source="staging",
                category="staging_missing",
                label="Disease staging not documented",
                detail=(
                    "Patient has retina or glaucoma activity but no "
                    "provider-entered disease-staging record on file. "
                    "Informational only — never blocks signing."
                ),
                status="missing",
                priority_bucket="informational",
                insufficient_data=True,
                requires_provider_review=True,
            )
        )
    return items


def _medication_items(
    caller: Caller, patients: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Phase 85 — informational items for patients whose active
    medications carry at least one refill gap. Always 'informational' /
    never tier 1. ChartNav does NOT refill, does NOT contact the
    pharmacy, and does NOT recommend medication changes."""
    from app.services.medications import patients_with_refill_gaps

    items: list[dict[str, Any]] = []
    for entry in patients_with_refill_gaps(caller.organization_id):
        pid = int(entry["patient_id"])
        gap_count = int(entry["gap_count"])
        max_gap = int(entry["max_gap_days"])
        items.append(
            _item(
                item_id=f"medication:refill_gap:{pid}",
                patient_id=pid,
                patients=patients,
                specialty_source="medication",
                category="medication_refill_gap",
                label="Medication refill gap on file",
                detail=(
                    f"{gap_count} active medication(s) with refill gap; "
                    f"longest gap is {max_gap} day(s). Informational only — "
                    "ChartNav does not refill or contact the pharmacy."
                ),
                status="warning",
                priority_bucket="informational",
                insufficient_data=False,
                requires_provider_review=True,
            )
        )
    return items


def build_action_queue(caller: Caller) -> dict[str, Any]:
    """Build the deterministic cross-specialty action queue for the
    caller's organization."""
    with engine.connect() as conn:
        patients = _patient_names(conn, caller.organization_id)
        glaucoma = _glaucoma_items(conn, caller, patients)
        cataract = _cataract_items(conn, caller, patients)
        unsigned = _unsigned_artifact_items(conn, caller, patients)

    anti_vegf = _anti_vegf_items(caller, patients)
    staging = _staging_items(caller, patients)
    medication = _medication_items(caller, patients)

    all_items = anti_vegf + glaucoma + cataract + unsigned + staging + medication
    buckets: dict[str, list[dict[str, Any]]] = {b: [] for b in PRIORITY_BUCKETS}
    for it in all_items:
        buckets[it["priority_bucket"]].append(it)
    for b in PRIORITY_BUCKETS:
        buckets[b].sort(key=lambda it: (it.get("due_at") or "9999", it["item_id"]))

    sources = sorted({it["specialty_source"] for it in all_items})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organization_id": caller.organization_id,
        "demo_mode": True,
        "buckets": buckets,
        "totals": {b: len(buckets[b]) for b in PRIORITY_BUCKETS},
        "total_items": len(all_items),
        "sources_present": sources,
        "disclosure": (
            "Workflow queue from provider-entered data. Bucket assignment "
            "is a documented deterministic rule (due dates, missing "
            "attestations, unsigned artifacts) — not an autonomous urgency "
            "decision. ChartNav does not diagnose, does not recommend "
            "treatment or surgery, and does not interpret images. Provider "
            "review required for every item."
        ),
    }


__all__ = ["PRIORITY_BUCKETS", "build_action_queue"]
