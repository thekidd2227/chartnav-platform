"""Pre-visit clinical brief — deterministic on-demand generator.

Phase 10. The brief is a provider-facing summary of the existing
ChartNav records for one patient. It is not a clinical decision, not
patient-facing content, not orders, not coding, and not autonomous
diagnosis. The generator is deterministic regex/aggregation over
already-persisted source tables.

Source priority (highest to lowest) — implemented in
`generate_pre_visit_brief`:

  1. finalized patient summaries  (status='finalized', latest)
  2. reviewed/finalized scribe sessions (latest in those statuses)
  3. signed retinal artifacts     (signed_at IS NOT NULL, latest)
  4. recent encounters            (most recent, capped)
  5. workflow events              (recent across the patient's encounters)

The service does NOT persist the brief. There is no
`pre_visit_briefs` table — the brief is a derived view re-computed on
each call. This keeps it fresh by construction and avoids stale-cache
correctness bugs across five source tables.

Audit-side rules (enforced by the route layer, not here): the audit
`detail` row for `pre_visit_brief_generated` must contain ONLY
metadata — patient_id, source_counts, and generated_at. None of the
section-body strings produced by this module belong in the audit log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from app.db import fetch_all, fetch_one


# --- public constants --------------------------------------------------


DEFAULT_RECENT_ENCOUNTER_LIMIT = 10
DEFAULT_WORKFLOW_EVENT_LIMIT = 25
DEFAULT_SCRIBE_PREVIEW_LIMIT = 280
DEFAULT_SUMMARY_PREVIEW_LIMIT = 480
DEFAULT_RETINAL_TITLE_LIMIT = 160

PROVIDER_REVIEW_NOTICE = (
    "Pre-visit brief — provider review required. This brief summarizes "
    "available ChartNav records and may be incomplete."
)

# Encounter statuses we consider "still pending" for the purposes of
# the pending_items section. Everything else is treated as wrapped up
# enough to not be a pre-visit todo. We keep this conservative — we'd
# rather leave a finished encounter off pending_items than nag the
# provider.
_PENDING_ENCOUNTER_STATUSES: frozenset[str] = frozenset({
    "scheduled",
    "in_progress",
    "draft_ready",
    "review_needed",
})

# Scribe statuses that mean "still needs the provider to finish it".
_PENDING_SCRIBE_STATUSES: frozenset[str] = frozenset({
    "draft",
    "processing",
    "ready_for_review",
    "reviewed",  # reviewed but not finalized — still pending
})

# Patient summary statuses that mean "still needs provider action".
_PENDING_SUMMARY_STATUSES: frozenset[str] = frozenset({
    "draft",
    "reviewed",  # reviewed but not finalized
})

# Statuses that count as "done" / context-only sources for the
# higher-priority sections.
_FINALIZED_SCRIBE_STATUSES: frozenset[str] = frozenset({
    "reviewed",  # reviewed-or-finalized counts as a finished source
    "finalized",
})


# --- result shape ------------------------------------------------------


@dataclass(frozen=True)
class PreVisitBrief:
    """Provider-facing pre-visit brief.

    `brief_status` is `"generated"` when the call succeeded. There is
    no `"failed"` or `"error"` value emitted from the service —
    callers receive an exception, not a stub. When the patient has no
    ChartNav records at all, the brief is still `"generated"` but
    `data_gaps` lists what was missing.
    """

    patient_id: int
    brief_status: str
    last_visit_summary: Optional[str]
    active_issues: list[str]
    retinal_artifact_summary: dict[str, Any]
    recent_scribe_session_summary: dict[str, Any]
    patient_summary_context: dict[str, Any]
    pending_items: list[dict[str, Any]]
    suggested_review_items: list[dict[str, Any]]
    data_gaps: list[str]
    source_counts: dict[str, int]
    generated_at: str
    notice: str = PROVIDER_REVIEW_NOTICE

    def to_response(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "brief_status": self.brief_status,
            "last_visit_summary": self.last_visit_summary,
            "active_issues": list(self.active_issues),
            "retinal_artifact_summary": dict(self.retinal_artifact_summary),
            "recent_scribe_session_summary": dict(self.recent_scribe_session_summary),
            "patient_summary_context": dict(self.patient_summary_context),
            "pending_items": [dict(p) for p in self.pending_items],
            "suggested_review_items": [dict(s) for s in self.suggested_review_items],
            "data_gaps": list(self.data_gaps),
            "source_counts": dict(self.source_counts),
            "generated_at": self.generated_at,
            "notice": self.notice,
        }


# --- exceptions --------------------------------------------------------


class PatientNotFoundError(Exception):
    """The patient does not exist in the caller's organization."""


# --- helpers -----------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: Optional[str], limit: int) -> Optional[str]:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _coerce_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _safe_json_list(blob: Any) -> list[str]:
    """Normalize a JSON-encoded TEXT column into a list[str].

    The patient_summaries.* JSON columns are stored as TEXT containing
    a JSON-encoded array. Be liberal in what we accept — silently coerce
    None / empty / non-list to an empty list and drop non-string items
    rather than raising. The brief is best-effort; partial source data
    must not break it.
    """
    if blob is None:
        return []
    if isinstance(blob, list):
        return [str(x).strip() for x in blob if str(x).strip()]
    if not isinstance(blob, str) or not blob.strip():
        return []
    try:
        decoded = json.loads(blob)
    except (TypeError, ValueError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(x).strip() for x in decoded if str(x).strip()]


def _safe_json_dict(blob: Any) -> dict[str, Any]:
    if blob is None:
        return {}
    if isinstance(blob, dict):
        return blob
    if not isinstance(blob, str) or not blob.strip():
        return {}
    try:
        decoded = json.loads(blob)
    except (TypeError, ValueError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


# --- patient resolution ------------------------------------------------


def resolve_patient(patient_id: int, *, organization_id: int) -> dict[str, Any]:
    """Resolve a patient row inside the caller's org.

    Cross-org / unknown raises PatientNotFoundError so the route layer
    can return a 404 without leaking existence.
    """
    row = fetch_one(
        "SELECT id, organization_id, patient_identifier, first_name, "
        "last_name, date_of_birth, sex_at_birth "
        "FROM patients "
        "WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": organization_id},
    )
    if not row:
        raise PatientNotFoundError(
            f"patient {patient_id} not found in org {organization_id}"
        )
    return dict(row)


# --- per-source readers ------------------------------------------------


def _read_encounters(
    *, organization_id: int, patient_id: int, limit: int
) -> list[dict[str, Any]]:
    """Most-recent encounters for the patient, capped.

    We try patient_id (the native FK from f6a7b8c9d0e1) first. If the
    column is unset (older bridge rows), fall back to the
    `patient_identifier` join — the patient's identifier is unique per
    org. Both filters are org-scoped.
    """
    rows = fetch_all(
        "SELECT id, status, scheduled_at, started_at, completed_at, "
        "       provider_name, patient_name, patient_identifier, "
        "       created_at "
        "FROM encounters "
        "WHERE organization_id = :org "
        "  AND (patient_id = :pid "
        "       OR patient_identifier = :pidf) "
        "ORDER BY COALESCE(completed_at, started_at, scheduled_at, "
        "                  created_at) DESC, id DESC "
        "LIMIT :limit",
        {
            "org": organization_id,
            "pid": patient_id,
            "pidf": _patient_identifier(patient_id, organization_id) or "",
            "limit": limit,
        },
    )
    return [dict(r) for r in rows]


def _patient_identifier(patient_id: int, organization_id: int) -> Optional[str]:
    row = fetch_one(
        "SELECT patient_identifier FROM patients "
        "WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": organization_id},
    )
    return row["patient_identifier"] if row else None


def _read_workflow_events(
    *, encounter_ids: Iterable[int], limit: int
) -> list[dict[str, Any]]:
    ids = list(encounter_ids)
    if not ids:
        return []
    placeholders = ", ".join(f":e{i}" for i in range(len(ids)))
    params: dict[str, Any] = {f"e{i}": v for i, v in enumerate(ids)}
    params["limit"] = limit
    rows = fetch_all(
        f"SELECT id, encounter_id, event_type, event_data, created_at "
        f"FROM workflow_events "
        f"WHERE encounter_id IN ({placeholders}) "
        f"ORDER BY created_at DESC, id DESC "
        f"LIMIT :limit",
        params,
    )
    return [dict(r) for r in rows]


def _read_scribe_sessions(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id, status, encounter_id, source_text, draft_note_text, "
        "       structured_note_json, finalized_at, reviewed_at, "
        "       discarded_at, created_at, updated_at "
        "FROM scribe_sessions "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY updated_at DESC, id DESC",
        {"org": organization_id, "pid": patient_id},
    )
    return [dict(r) for r in rows]


def _read_chart_artifacts(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id, artifact_type, title, encounter_id, "
        "       version_number, signed_at, created_at, updated_at "
        "FROM chart_artifacts "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY COALESCE(signed_at, updated_at, created_at) DESC, id DESC",
        {"org": organization_id, "pid": patient_id},
    )
    return [dict(r) for r in rows]


def _read_patient_summaries(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id, status, encounter_id, scribe_session_id, "
        "       plain_language_summary, key_findings_json, "
        "       next_steps_json, questions_json, limitations_notice, "
        "       finalized_at, reviewed_at, discarded_at, "
        "       created_at, updated_at "
        "FROM patient_summaries "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY updated_at DESC, id DESC",
        {"org": organization_id, "pid": patient_id},
    )
    return [dict(r) for r in rows]


# --- section builders --------------------------------------------------


def _build_last_visit_summary(
    encounters: list[dict[str, Any]]
) -> Optional[str]:
    """One-line recap of the most recent encounter, no diagnosis."""
    if not encounters:
        return None
    e = encounters[0]
    when = (
        _coerce_iso(e.get("completed_at"))
        or _coerce_iso(e.get("started_at"))
        or _coerce_iso(e.get("scheduled_at"))
        or _coerce_iso(e.get("created_at"))
    )
    provider = (e.get("provider_name") or "").strip() or "Unknown provider"
    status = (e.get("status") or "").strip() or "unknown"
    if when:
        return (
            f"Most recent encounter on {when} with {provider} "
            f"(status: {status})."
        )
    return f"Most recent encounter with {provider} (status: {status})."


def _build_active_issues(
    *,
    finalized_summary: Optional[dict[str, Any]],
    finalized_scribe: Optional[dict[str, Any]],
) -> list[str]:
    """Provider-readable issue list. Source content only — no invention.

    Pulls in this order:
      1. key_findings from the latest finalized patient summary
      2. assessment items from the latest finalized scribe session's
         structured_note_json (a list under the key "assessment", if
         present), otherwise an empty list
    Items are deduped (case-insensitive) preserving order.
    """
    items: list[str] = []
    if finalized_summary is not None:
        for kf in _safe_json_list(finalized_summary.get("key_findings_json")):
            items.append(kf)
    if finalized_scribe is not None:
        sj = _safe_json_dict(finalized_scribe.get("structured_note_json"))
        raw = sj.get("assessment")
        if isinstance(raw, list):
            for entry in raw:
                s = str(entry).strip()
                if s:
                    items.append(s)
        elif isinstance(raw, str) and raw.strip():
            items.append(raw.strip())
    seen: set[str] = set()
    deduped: list[str] = []
    for it in items:
        key = it.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped


def _build_retinal_artifact_summary(
    artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    signed = [a for a in artifacts if a.get("signed_at")]
    unsigned = [a for a in artifacts if not a.get("signed_at")]
    latest_signed = signed[0] if signed else None
    return {
        "total": len(artifacts),
        "signed_count": len(signed),
        "unsigned_count": len(unsigned),
        "latest_signed": (
            {
                "id": latest_signed["id"],
                "title": _truncate(
                    latest_signed.get("title") or "",
                    DEFAULT_RETINAL_TITLE_LIMIT,
                ),
                "signed_at": _coerce_iso(latest_signed.get("signed_at")),
                "version_number": latest_signed.get("version_number"),
                "encounter_id": latest_signed.get("encounter_id"),
            }
            if latest_signed
            else None
        ),
        "has_unsigned_drafts": bool(unsigned),
    }


def _build_recent_scribe_session_summary(
    sessions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Pick the latest reviewed/finalized scribe session for context.

    If none exist in those statuses, fall back to the latest non-
    discarded session and flag the status — it's still useful context
    even if the provider hasn't finished it yet.
    """
    finalized_like = [
        s for s in sessions if s.get("status") in _FINALIZED_SCRIBE_STATUSES
    ]
    pick: Optional[dict[str, Any]] = None
    if finalized_like:
        pick = finalized_like[0]
    else:
        non_discarded = [s for s in sessions if s.get("status") != "discarded"]
        if non_discarded:
            pick = non_discarded[0]
    if pick is None:
        return {"status": "none", "session_id": None}
    structured = _safe_json_dict(pick.get("structured_note_json"))
    cc_raw = structured.get("chief_complaint")
    cc = (cc_raw or "").strip() if isinstance(cc_raw, str) else ""
    plan_raw = structured.get("plan")
    plan = (plan_raw or "").strip() if isinstance(plan_raw, str) else ""
    return {
        "session_id": pick["id"],
        "status": pick["status"],
        "updated_at": _coerce_iso(pick.get("updated_at")),
        "finalized_at": _coerce_iso(pick.get("finalized_at")),
        "reviewed_at": _coerce_iso(pick.get("reviewed_at")),
        "encounter_id": pick.get("encounter_id"),
        "chief_complaint_excerpt": _truncate(cc, DEFAULT_SCRIBE_PREVIEW_LIMIT),
        "plan_excerpt": _truncate(plan, DEFAULT_SCRIBE_PREVIEW_LIMIT),
    }


def _build_patient_summary_context(
    summaries: list[dict[str, Any]]
) -> dict[str, Any]:
    finalized = [s for s in summaries if s.get("status") == "finalized"]
    reviewed = [s for s in summaries if s.get("status") == "reviewed"]
    pick: Optional[dict[str, Any]] = None
    pick_kind: str = "none"
    if finalized:
        pick = finalized[0]
        pick_kind = "finalized"
    elif reviewed:
        pick = reviewed[0]
        pick_kind = "reviewed"
    if pick is None:
        return {"status": "none", "summary_id": None}
    return {
        "summary_id": pick["id"],
        "status": pick.get("status"),
        "source_kind": pick_kind,
        "finalized_at": _coerce_iso(pick.get("finalized_at")),
        "reviewed_at": _coerce_iso(pick.get("reviewed_at")),
        "encounter_id": pick.get("encounter_id"),
        "scribe_session_id": pick.get("scribe_session_id"),
        "plain_language_excerpt": _truncate(
            pick.get("plain_language_summary") or "",
            DEFAULT_SUMMARY_PREVIEW_LIMIT,
        ),
        "key_findings_count": len(
            _safe_json_list(pick.get("key_findings_json"))
        ),
        "next_steps_count": len(_safe_json_list(pick.get("next_steps_json"))),
    }


def _build_pending_items(
    *,
    encounters: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate non-finalized work the provider should know about."""
    pending: list[dict[str, Any]] = []
    for e in encounters:
        if e.get("status") in _PENDING_ENCOUNTER_STATUSES:
            pending.append({
                "kind": "encounter",
                "id": e["id"],
                "status": e["status"],
                "provider_name": e.get("provider_name"),
                "scheduled_at": _coerce_iso(e.get("scheduled_at")),
            })
    for s in sessions:
        if s.get("status") in _PENDING_SCRIBE_STATUSES:
            pending.append({
                "kind": "scribe_session",
                "id": s["id"],
                "status": s["status"],
                "encounter_id": s.get("encounter_id"),
                "updated_at": _coerce_iso(s.get("updated_at")),
            })
    for sm in summaries:
        if sm.get("status") in _PENDING_SUMMARY_STATUSES:
            pending.append({
                "kind": "patient_summary",
                "id": sm["id"],
                "status": sm["status"],
                "encounter_id": sm.get("encounter_id"),
                "updated_at": _coerce_iso(sm.get("updated_at")),
            })
    return pending


def _build_suggested_review_items(
    *,
    sessions: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Items in an explicit 'awaiting review' state.

    This is intentionally narrower than `pending_items` — it's only
    things that have an explicit review state that the provider still
    needs to act on. Never any diagnostic suggestion or recommendation.
    """
    out: list[dict[str, Any]] = []
    for s in sessions:
        if s.get("status") == "ready_for_review":
            out.append({
                "kind": "scribe_session",
                "id": s["id"],
                "reason": "scribe session ready for provider review",
                "updated_at": _coerce_iso(s.get("updated_at")),
            })
        elif s.get("status") == "reviewed":
            out.append({
                "kind": "scribe_session",
                "id": s["id"],
                "reason": "scribe session reviewed; awaiting finalize",
                "updated_at": _coerce_iso(s.get("updated_at")),
            })
    for sm in summaries:
        if sm.get("status") == "draft":
            out.append({
                "kind": "patient_summary",
                "id": sm["id"],
                "reason": "patient summary draft awaiting review",
                "updated_at": _coerce_iso(sm.get("updated_at")),
            })
        elif sm.get("status") == "reviewed":
            out.append({
                "kind": "patient_summary",
                "id": sm["id"],
                "reason": "patient summary reviewed; awaiting finalize",
                "updated_at": _coerce_iso(sm.get("updated_at")),
            })
    return out


def _build_data_gaps(
    *,
    encounters: list[dict[str, Any]],
    workflow_events: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    finalized_summary: Optional[dict[str, Any]],
    finalized_scribe: Optional[dict[str, Any]],
    signed_artifact: Optional[dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    if not encounters:
        gaps.append("No recent encounters on file for this patient.")
    if not workflow_events:
        gaps.append(
            "No workflow events recorded against this patient's encounters."
        )
    if not sessions:
        gaps.append("No scribe sessions on file for this patient.")
    elif finalized_scribe is None:
        gaps.append(
            "No reviewed or finalized scribe session on file; "
            "context above falls back to the most recent draft."
        )
    if not artifacts:
        gaps.append("No retinal artifacts on file for this patient.")
    elif signed_artifact is None:
        gaps.append(
            "No signed retinal artifacts on file; only unsigned drafts exist."
        )
    if not summaries:
        gaps.append("No patient-friendly summaries on file for this patient.")
    elif finalized_summary is None:
        gaps.append(
            "No finalized patient-friendly summary; using the latest "
            "reviewed/draft summary for context."
        )
    return gaps


# --- public entrypoint -------------------------------------------------


def generate_pre_visit_brief(
    *,
    organization_id: int,
    patient_id: int,
    recent_encounter_limit: int = DEFAULT_RECENT_ENCOUNTER_LIMIT,
    workflow_event_limit: int = DEFAULT_WORKFLOW_EVENT_LIMIT,
) -> PreVisitBrief:
    """Compute a fresh pre-visit brief for the given patient.

    Caller is responsible for the org-scoped patient resolution
    (see `resolve_patient`). This function trusts that
    `(organization_id, patient_id)` has already been validated as
    belonging to the caller's org. It re-asserts the org filter on
    every per-source query for defense in depth — a stale or wrong
    `patient_id` will simply produce an empty brief, never leak data
    from another org.
    """
    encounters = _read_encounters(
        organization_id=organization_id,
        patient_id=patient_id,
        limit=recent_encounter_limit,
    )
    encounter_ids = [e["id"] for e in encounters]
    workflow_events = _read_workflow_events(
        encounter_ids=encounter_ids, limit=workflow_event_limit
    )
    sessions = _read_scribe_sessions(
        organization_id=organization_id, patient_id=patient_id
    )
    artifacts = _read_chart_artifacts(
        organization_id=organization_id, patient_id=patient_id
    )
    summaries = _read_patient_summaries(
        organization_id=organization_id, patient_id=patient_id
    )

    finalized_summary: Optional[dict[str, Any]] = next(
        (s for s in summaries if s.get("status") == "finalized"), None
    )
    finalized_scribe: Optional[dict[str, Any]] = next(
        (s for s in sessions if s.get("status") in _FINALIZED_SCRIBE_STATUSES),
        None,
    )
    signed_artifact: Optional[dict[str, Any]] = next(
        (a for a in artifacts if a.get("signed_at")), None
    )

    # ---- counts ------------------------------------------------------
    source_counts: dict[str, int] = {
        "encounters": len(encounters),
        "workflow_events": len(workflow_events),
        "scribe_sessions": len(sessions),
        "scribe_sessions_finalized": sum(
            1 for s in sessions if s.get("status") in _FINALIZED_SCRIBE_STATUSES
        ),
        "retinal_artifacts": len(artifacts),
        "retinal_artifacts_signed": sum(
            1 for a in artifacts if a.get("signed_at")
        ),
        "patient_summaries": len(summaries),
        "patient_summaries_finalized": sum(
            1 for s in summaries if s.get("status") == "finalized"
        ),
    }

    # ---- sections ----------------------------------------------------
    last_visit = _build_last_visit_summary(encounters)
    active_issues = _build_active_issues(
        finalized_summary=finalized_summary,
        finalized_scribe=finalized_scribe,
    )
    retinal = _build_retinal_artifact_summary(artifacts)
    scribe_summary = _build_recent_scribe_session_summary(sessions)
    summary_context = _build_patient_summary_context(summaries)
    pending = _build_pending_items(
        encounters=encounters, sessions=sessions, summaries=summaries
    )
    suggested = _build_suggested_review_items(
        sessions=sessions, summaries=summaries
    )
    gaps = _build_data_gaps(
        encounters=encounters,
        workflow_events=workflow_events,
        sessions=sessions,
        artifacts=artifacts,
        summaries=summaries,
        finalized_summary=finalized_summary,
        finalized_scribe=finalized_scribe,
        signed_artifact=signed_artifact,
    )

    return PreVisitBrief(
        patient_id=patient_id,
        brief_status="generated",
        last_visit_summary=last_visit,
        active_issues=active_issues,
        retinal_artifact_summary=retinal,
        recent_scribe_session_summary=scribe_summary,
        patient_summary_context=summary_context,
        pending_items=pending,
        suggested_review_items=suggested,
        data_gaps=gaps,
        source_counts=source_counts,
        generated_at=_now_iso(),
    )


__all__ = [
    "DEFAULT_RECENT_ENCOUNTER_LIMIT",
    "DEFAULT_WORKFLOW_EVENT_LIMIT",
    "PROVIDER_REVIEW_NOTICE",
    "PatientNotFoundError",
    "PreVisitBrief",
    "generate_pre_visit_brief",
    "resolve_patient",
]
