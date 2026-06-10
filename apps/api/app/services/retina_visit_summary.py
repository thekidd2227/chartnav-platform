"""Phase 76 — Retina Visit Summary Aggregator service.

Pure aggregation across the three buyer-demo clinical artifact families
for a single encounter:

  - vitals workups (visit_vitals_workups)
  - visit drafts / scribe sessions (scribe_sessions)
  - fundus charts (fundus_charts)

Plus a metadata-only evidence timeline that joins the three families'
lifecycle events into one chronological list. The timeline is strictly
metadata: artifact_type, event_type, actor display name + role,
timestamp, ref id, optional warning_count / element_count. NO clinical
free text (transcripts, BP values, IOP values, chief complaint, HPI,
findings text, etc.) is ever emitted in this surface — that is the
Phase 73 "metadata-only audit trail" rule applied at the aggregator
level.

This is the Phase 76 closeout for Phase 1 Clinical Spine gates 2 and 5
(retina-visit-summary aggregator endpoint + cross-artifact metadata-only
timeline).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Forbidden columns: hard rule — these never appear in the aggregator output.
# Used by tests as a canary; also documents intent.
# ---------------------------------------------------------------------------

FORBIDDEN_CLINICAL_COLUMNS = frozenset(
    {
        # Vitals body
        "bp_systolic", "bp_diastolic", "temperature_value", "pulse",
        "respiratory_rate", "oxygen_saturation", "height_value",
        "weight_value", "pain_score", "visual_acuity_od", "visual_acuity_os",
        "visual_acuity_ou", "iop_od", "iop_os", "technician_notes",
        # Scribe body
        "source_text", "transcript_text", "draft_note_text",
        "structured_note_json", "review_notes", "ambient_draft",
        # Fundus body
        "findings_json", "drawing_json", "rendered_svg",
        "ai_confidence_json", "warnings_json",
    }
)


# ---------------------------------------------------------------------------
# Role capabilities — closed shape, every value is a literal True/False.
# ---------------------------------------------------------------------------

ROLE_EXPLAINERS = {
    "admin": "Admin can review and sign clinical artifacts.",
    "clinician": "Clinician can review and sign clinical artifacts.",
    "technician": (
        "Technician can complete intake and enter findings, but cannot "
        "sign clinical artifacts."
    ),
    "reviewer": "Reviewer has read-only access. Cannot sign.",
    "front_desk": "Front-desk role has encounter and scheduling visibility only.",
}


def _role_capabilities(role: str) -> dict[str, Any]:
    can_review = role in {"admin", "clinician", "reviewer"}
    can_sign = role in {"admin", "clinician"}
    can_create_intake = role in {"admin", "clinician", "technician"}
    return {
        "role": role,
        "can_review": can_review,
        "can_sign": can_sign,
        "can_create_intake": can_create_intake,
        "explainer": ROLE_EXPLAINERS.get(
            role, "Role has limited clinical access; consult your administrator."
        ),
    }


# ---------------------------------------------------------------------------
# Service-level error so the router can translate to HTTPException.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SummaryError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _users_by_id(conn, org_id: int) -> dict[int, dict[str, str]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, full_name, email, role FROM users "
            "WHERE organization_id = :oid"
        ),
        {"oid": org_id},
    ).fetchall()
    out: dict[int, dict[str, str]] = {}
    for r in rows:
        uid, full_name, email, role = r
        out[int(uid)] = {
            "display_name": full_name or email,
            "role": role,
        }
    return out


def _actor(users: dict[int, dict[str, str]], user_id: Any) -> dict[str, Any]:
    if user_id is None:
        return {"actor_display_name": None, "actor_role": None}
    info = users.get(int(user_id))
    if not info:
        return {"actor_display_name": f"user #{int(user_id)}", "actor_role": None}
    return {"actor_display_name": info["display_name"], "actor_role": info["role"]}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _encounter_or_404(conn, encounter_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, patient_identifier, "
            "patient_name, status, started_at "
            "FROM encounters WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise SummaryError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    eid, oid, pid, pident, pname, st, started = row
    return {
        "id": int(eid),
        "organization_id": int(oid),
        "patient_id": int(pid) if pid is not None else None,
        "patient_identifier": pident,
        "patient_name": pname,
        "status": st,
        "started_at": _iso(started),
    }


def _vitals_for_encounter(conn, encounter_id: int, org_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, status, created_by_user_id, created_at, "
            "reviewed_by_user_id, reviewed_at, signed_by_user_id, signed_at, "
            "warnings_json "
            "FROM visit_vitals_workups "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "ORDER BY id"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchall()
    out = []
    for r in rows:
        wid, st, cby, cat, rby, rat, sby, sat, warnings_json = r
        # warning_count is an integer count, not the text — safe metadata.
        import json
        try:
            warnings_list = json.loads(warnings_json) if warnings_json else []
            wc = len(warnings_list) if isinstance(warnings_list, list) else 0
        except (ValueError, TypeError):
            wc = 0
        out.append(
            {
                "id": int(wid),
                "status": st,
                "created_by_user_id": cby,
                "created_at": _iso(cat),
                "reviewed_by_user_id": rby,
                "reviewed_at": _iso(rat),
                "signed_by_user_id": sby,
                "signed_at": _iso(sat),
                "warning_count": wc,
            }
        )
    return out


def _scribes_for_encounter(conn, encounter_id: int, org_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, status, created_by_user_id, created_at, "
            "reviewed_by_user_id, reviewed_at, finalized_at "
            "FROM scribe_sessions "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "ORDER BY id"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchall()
    out = []
    for r in rows:
        sid, st, cby, cat, rby, rat, fat = r
        out.append(
            {
                "id": int(sid),
                "status": st,
                "created_by_user_id": cby,
                "created_at": _iso(cat),
                "reviewed_by_user_id": rby,
                "reviewed_at": _iso(rat),
                "finalized_at": _iso(fat),
            }
        )
    return out


def _fundus_for_encounter(conn, encounter_id: int, org_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        sa_text(
            "SELECT id, status, laterality, source_type, "
            "created_by_user_id, created_at, "
            "reviewed_by_user_id, reviewed_at, signed_by_user_id, signed_at, "
            "drawing_json, warnings_json "
            "FROM fundus_charts "
            "WHERE encounter_id = :eid AND organization_id = :oid "
            "ORDER BY id"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchall()
    import json
    out = []
    for r in rows:
        (
            fid, st, lat, src, cby, cat, rby, rat, sby, sat,
            drawing_json, warnings_json,
        ) = r
        try:
            drawing = json.loads(drawing_json) if drawing_json else None
            elements = drawing.get("elements") if isinstance(drawing, dict) else None
            ec = len(elements) if isinstance(elements, list) else 0
        except (ValueError, TypeError):
            ec = 0
        try:
            warnings_list = json.loads(warnings_json) if warnings_json else []
            wc = len(warnings_list) if isinstance(warnings_list, list) else 0
        except (ValueError, TypeError):
            wc = 0
        out.append(
            {
                "id": int(fid),
                "status": st,
                "laterality": lat,
                "source_type": src,
                "created_by_user_id": cby,
                "created_at": _iso(cat),
                "reviewed_by_user_id": rby,
                "reviewed_at": _iso(rat),
                "signed_by_user_id": sby,
                "signed_at": _iso(sat),
                "element_count": ec,
                "warning_count": wc,
            }
        )
    return out


def _summarize(rows: list[dict[str, Any]], signed_field: str) -> dict[str, Any]:
    """Roll a list of artifact rows into a {count, latest_*} summary."""
    if not rows:
        return {"count": 0, "latest_id": None, "latest_status": None}
    latest = rows[-1]
    summary = {
        "count": len(rows),
        "latest_id": latest["id"],
        "latest_status": latest["status"],
    }
    for key in ("created_at", "reviewed_at", signed_field):
        if key in latest:
            summary[f"latest_{key}"] = latest[key]
    if "warning_count" in latest:
        summary["latest_warning_count"] = latest["warning_count"]
    if "element_count" in latest:
        summary["latest_element_count"] = latest["element_count"]
    if "laterality" in latest:
        summary["latest_laterality"] = latest["laterality"]
    return summary


def _blockers(
    vitals_summary: dict[str, Any],
    scribe_summary: dict[str, Any],
    fundus_summary: dict[str, Any],
) -> list[dict[str, str]]:
    """Compute the blocker list — what still needs provider action."""
    out: list[dict[str, str]] = []

    if vitals_summary["count"] == 0:
        out.append(
            {
                "kind": "missing_vitals",
                "message": "No vitals workup recorded for this encounter yet.",
            }
        )
    elif vitals_summary.get("latest_status") != "signed":
        out.append(
            {
                "kind": "vitals_unsigned",
                "message": (
                    f"Latest vitals workup is "
                    f"{vitals_summary.get('latest_status', 'pending')} — "
                    "provider review and signature still required."
                ),
            }
        )

    if scribe_summary["count"] == 0:
        out.append(
            {
                "kind": "missing_visit_draft",
                "message": "No visit draft (ambient documentation) recorded yet.",
            }
        )
    elif scribe_summary.get("latest_status") != "finalized":
        out.append(
            {
                "kind": "visit_draft_unsigned",
                "message": (
                    f"Latest visit draft is "
                    f"{scribe_summary.get('latest_status', 'pending')} — "
                    "provider review and signature still required."
                ),
            }
        )

    if fundus_summary["count"] == 0:
        out.append(
            {
                "kind": "missing_fundus",
                "message": "No fundus chart drafted for this encounter yet.",
            }
        )
    elif fundus_summary.get("latest_status") != "signed":
        out.append(
            {
                "kind": "fundus_unsigned",
                "message": (
                    f"Latest fundus chart is "
                    f"{fundus_summary.get('latest_status', 'pending')} — "
                    "provider review and signature still required."
                ),
            }
        )

    return out


def _emit_event(
    timeline: list[dict[str, Any]],
    *,
    artifact_type: str,
    event_type: str,
    timestamp: str | None,
    actor_user_id: Any,
    ref_id: int,
    users: dict[int, dict[str, str]],
    extras: dict[str, Any] | None = None,
) -> None:
    if timestamp is None:
        return
    entry = {
        "artifact_type": artifact_type,
        "event_type": event_type,
        "timestamp": timestamp,
        "ref_id": ref_id,
        **_actor(users, actor_user_id),
    }
    if extras:
        entry.update(extras)
    timeline.append(entry)


def _build_timeline(
    vitals: list[dict[str, Any]],
    scribes: list[dict[str, Any]],
    fundus: list[dict[str, Any]],
    users: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []

    for w in vitals:
        _emit_event(
            timeline,
            artifact_type="vitals_workup",
            event_type="created",
            timestamp=w["created_at"],
            actor_user_id=w["created_by_user_id"],
            ref_id=w["id"],
            users=users,
            extras={"warning_count": w["warning_count"]},
        )
        _emit_event(
            timeline,
            artifact_type="vitals_workup",
            event_type="reviewed",
            timestamp=w["reviewed_at"],
            actor_user_id=w["reviewed_by_user_id"],
            ref_id=w["id"],
            users=users,
        )
        _emit_event(
            timeline,
            artifact_type="vitals_workup",
            event_type="signed",
            timestamp=w["signed_at"],
            actor_user_id=w["signed_by_user_id"],
            ref_id=w["id"],
            users=users,
            extras={"warning_count": w["warning_count"]},
        )

    for s in scribes:
        _emit_event(
            timeline,
            artifact_type="visit_draft",
            event_type="created",
            timestamp=s["created_at"],
            actor_user_id=s["created_by_user_id"],
            ref_id=s["id"],
            users=users,
        )
        _emit_event(
            timeline,
            artifact_type="visit_draft",
            event_type="reviewed",
            timestamp=s["reviewed_at"],
            actor_user_id=s["reviewed_by_user_id"],
            ref_id=s["id"],
            users=users,
        )
        _emit_event(
            timeline,
            artifact_type="visit_draft",
            event_type="signed",
            timestamp=s["finalized_at"],
            actor_user_id=None,
            ref_id=s["id"],
            users=users,
        )

    for f in fundus:
        _emit_event(
            timeline,
            artifact_type="fundus_chart",
            event_type="created",
            timestamp=f["created_at"],
            actor_user_id=f["created_by_user_id"],
            ref_id=f["id"],
            users=users,
            extras={
                "laterality": f["laterality"],
                "source_type": f["source_type"],
                "element_count": f["element_count"],
                "warning_count": f["warning_count"],
            },
        )
        _emit_event(
            timeline,
            artifact_type="fundus_chart",
            event_type="reviewed",
            timestamp=f["reviewed_at"],
            actor_user_id=f["reviewed_by_user_id"],
            ref_id=f["id"],
            users=users,
        )
        _emit_event(
            timeline,
            artifact_type="fundus_chart",
            event_type="signed",
            timestamp=f["signed_at"],
            actor_user_id=f["signed_by_user_id"],
            ref_id=f["id"],
            users=users,
            extras={
                "laterality": f["laterality"],
                "element_count": f["element_count"],
                "warning_count": f["warning_count"],
            },
        )

    timeline.sort(key=lambda e: e["timestamp"])
    return timeline


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def build_summary(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Aggregate the retina visit summary for one encounter.

    Returns a dict with this shape (all metadata-only — see module
    docstring):

        {
          "encounter_id": int,
          "patient_id": int | None,
          "organization_id": int,
          "patient_identifier": str | None,
          "patient_name": str | None,
          "encounter_status": str,
          "demo_mode": True,
          "vitals":      {count, latest_id, latest_status, ...},
          "visit_draft": {count, latest_id, latest_status, ...},
          "fundus":      {count, latest_id, latest_status, ...},
          "blockers":    [{kind, message}, ...],
          "role_capabilities": {role, can_review, can_sign, ...},
          "evidence_timeline": [
            {artifact_type, event_type, timestamp,
             actor_display_name, actor_role, ref_id, ...metadata},
            ...
          ],
          "audit_disclosure": str,
        }

    Raises ``SummaryError`` on cross-org access or unknown encounter.
    """
    with engine.connect() as conn:
        encounter = _encounter_or_404(conn, encounter_id, caller.organization_id)
        users = _users_by_id(conn, caller.organization_id)
        vitals = _vitals_for_encounter(conn, encounter_id, caller.organization_id)
        scribes = _scribes_for_encounter(conn, encounter_id, caller.organization_id)
        fundus = _fundus_for_encounter(conn, encounter_id, caller.organization_id)

    vitals_summary = _summarize(vitals, "signed_at")
    scribe_summary = _summarize(scribes, "finalized_at")
    fundus_summary = _summarize(fundus, "signed_at")
    blockers = _blockers(vitals_summary, scribe_summary, fundus_summary)
    timeline = _build_timeline(vitals, scribes, fundus, users)

    # Phase 83 — fold provider acknowledgement audit events into the
    # cross-artifact evidence timeline. Imported lazily to keep the
    # Phase 76 module self-contained.
    from app.services.note_validation_acknowledgements import (
        list_for_summary_timeline,
    )

    ack_events = list_for_summary_timeline(encounter_id, caller.organization_id)
    timeline.extend(ack_events)
    timeline.sort(key=lambda e: e["timestamp"])

    # Phase 84 — surface the latest provider-entered disease-stage per
    # diagnosis for this patient. Metadata only; no derived clinical
    # interpretation beyond the deterministic equality check.
    from app.services.disease_staging import latest_for_patient as _staging_latest

    if encounter["patient_id"] is not None:
        staging_records = _staging_latest(
            encounter["patient_id"], caller.organization_id
        )
    else:
        staging_records = []
    disease_staging_summary = {
        "record_count": len(staging_records),
        "latest_by_diagnosis": staging_records,
        "insufficient_data": len(staging_records) == 0,
    }

    return {
        "encounter_id": encounter["id"],
        "patient_id": encounter["patient_id"],
        "organization_id": encounter["organization_id"],
        "patient_identifier": encounter["patient_identifier"],
        "patient_name": encounter["patient_name"],
        "encounter_status": encounter["status"],
        "encounter_started_at": encounter["started_at"],
        "demo_mode": True,
        "vitals": vitals_summary,
        "visit_draft": scribe_summary,
        "fundus": fundus_summary,
        "blockers": blockers,
        "role_capabilities": _role_capabilities(caller.role),
        "evidence_timeline": timeline,
        "disease_staging_summary": disease_staging_summary,
        "audit_disclosure": (
            "ChartNav records metadata-only audit events: who created, "
            "reviewed, and signed each artifact, and when. The audit "
            "trail does not store clinical free text (no transcripts, "
            "BP/IOP/VA values, chief complaint, HPI, or findings text). "
            "Disease staging is provider-entered; ChartNav does not "
            "stage disease or interpret imaging."
        ),
    }
