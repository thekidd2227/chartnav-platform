"""Provider action review queue — deterministic suggestions + lifecycle.

Phase 11. Each row in `provider_action_items` is a provider-reviewable
suggestion that ChartNav has surfaced from existing chart records.

Important non-goals — this module never:
  - creates orders / prescriptions
  - submits referrals
  - posts billing / coding entries
  - sends messages to patients
  - calls an external LLM
  - claims diagnoses

It surfaces *review tasks* with `review_…`, `consider_…`, or
`check_…` action types. The provider explicitly Accepts, Dismisses,
or Completes them. Statuses dismissed/completed are immutable.

Audit-side rules (enforced by the route layer):
  - Detail rows for `provider_action_item_*` events contain only
    metadata (action_id, patient_id, encounter_id, action_type,
    priority, status, source_type, source_id, generated/created/
    reused counts).
  - `title` and `reason` are NEVER written into the audit log.

This service trusts the route layer for org-scoped patient
resolution; it re-asserts `organization_id = :org` on every read and
write for defense in depth.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import text

from app.db import engine, fetch_all, fetch_one, insert_returning_id, transaction


_TABLE = "provider_action_items"


# --- enums --------------------------------------------------------------


class ActionStatus:
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    COMPLETED = "completed"


ALL_STATUSES: frozenset[str] = frozenset({
    ActionStatus.SUGGESTED,
    ActionStatus.ACCEPTED,
    ActionStatus.DISMISSED,
    ActionStatus.COMPLETED,
})


TERMINAL_STATUSES: frozenset[str] = frozenset({
    ActionStatus.DISMISSED,
    ActionStatus.COMPLETED,
})


class ActionPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ALL_PRIORITIES: frozenset[str] = frozenset({
    ActionPriority.LOW,
    ActionPriority.MEDIUM,
    ActionPriority.HIGH,
})


# Closed action_type vocabulary. The generator and the route layer
# reject any value outside this set, so a future attempt to slip in
# an order/coding/messaging type fails fast.
class ActionType:
    # Clinical review prompts (trigger when high-signal language
    # appears in a finalized scribe note or signed retinal artifact).
    REVIEW_RETINAL_TEAR_LANGUAGE = "review_retinal_tear_language"
    REVIEW_RETINAL_DETACHMENT_LANGUAGE = "review_retinal_detachment_language"
    REVIEW_NEOVASCULARIZATION_LANGUAGE = "review_neovascularization_language"
    REVIEW_SEVERE_HEMORRHAGE_LANGUAGE = "review_severe_hemorrhage_language"
    # Workflow completion prompts.
    SIGN_UNSIGNED_RETINAL_DIAGRAM = "sign_unsigned_retinal_diagram"
    REVIEW_PENDING_AI_DIAGRAM_PROPOSALS = "review_pending_ai_diagram_proposals"
    REVIEW_SCRIBE_SESSION = "review_scribe_session"
    FINALIZE_SCRIBE_SESSION = "finalize_scribe_session"
    REVIEW_PATIENT_SUMMARY = "review_patient_summary"
    FINALIZE_PATIENT_SUMMARY = "finalize_patient_summary"
    # Pre-visit readiness prompts.
    REVIEW_PRE_VISIT_DATA_GAPS = "review_pre_visit_data_gaps"
    REVIEW_MISSING_SIGNED_RETINAL_ARTIFACT = "review_missing_signed_retinal_artifact"
    REVIEW_MISSING_FINALIZED_PATIENT_SUMMARY = (
        "review_missing_finalized_patient_summary"
    )
    REVIEW_MISSING_REVIEWED_SCRIBE_SESSION = (
        "review_missing_reviewed_scribe_session"
    )
    # Data hygiene prompts.
    RECONCILE_UNSIGNED_ARTIFACTS = "reconcile_unsigned_artifacts"
    REVIEW_UNFINALIZED_PATIENT_CONTEXT = "review_unfinalized_patient_context"


ALL_ACTION_TYPES: frozenset[str] = frozenset({
    ActionType.REVIEW_RETINAL_TEAR_LANGUAGE,
    ActionType.REVIEW_RETINAL_DETACHMENT_LANGUAGE,
    ActionType.REVIEW_NEOVASCULARIZATION_LANGUAGE,
    ActionType.REVIEW_SEVERE_HEMORRHAGE_LANGUAGE,
    ActionType.SIGN_UNSIGNED_RETINAL_DIAGRAM,
    ActionType.REVIEW_PENDING_AI_DIAGRAM_PROPOSALS,
    ActionType.REVIEW_SCRIBE_SESSION,
    ActionType.FINALIZE_SCRIBE_SESSION,
    ActionType.REVIEW_PATIENT_SUMMARY,
    ActionType.FINALIZE_PATIENT_SUMMARY,
    ActionType.REVIEW_PRE_VISIT_DATA_GAPS,
    ActionType.REVIEW_MISSING_SIGNED_RETINAL_ARTIFACT,
    ActionType.REVIEW_MISSING_FINALIZED_PATIENT_SUMMARY,
    ActionType.REVIEW_MISSING_REVIEWED_SCRIBE_SESSION,
    ActionType.RECONCILE_UNSIGNED_ARTIFACTS,
    ActionType.REVIEW_UNFINALIZED_PATIENT_CONTEXT,
})


# --- transition matrix --------------------------------------------------
#
#   accept   : suggested            -> accepted
#   dismiss  : suggested | accepted -> dismissed
#   complete : accepted             -> completed
#
# Direct suggested -> completed is rejected (must accept first).
# Anything against dismissed/completed is rejected as immutable.


_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "accept": frozenset({ActionStatus.SUGGESTED}),
    "dismiss": frozenset({ActionStatus.SUGGESTED, ActionStatus.ACCEPTED}),
    "complete": frozenset({ActionStatus.ACCEPTED}),
}


# --- exceptions ---------------------------------------------------------


class ProviderActionItemNotFound(Exception):
    """Action item not in the caller's org / patient."""


class InvalidProviderActionTransition(Exception):
    def __init__(self, action: str, current_status: str) -> None:
        self.action = action
        self.current_status = current_status
        super().__init__(
            f"cannot {action} from status {current_status!r}"
        )


class ImmutableProviderActionItem(Exception):
    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(
            f"action item is {current_status} and cannot be modified"
        )


class ProviderActionSourceMismatch(Exception):
    """A `source_type`/`source_id` pair refers to a row in another
    org, another patient, or a non-existent row."""


# --- dataclass shape ---------------------------------------------------


@dataclass(frozen=True)
class ProviderActionItem:
    id: int
    organization_id: int
    patient_id: int
    encounter_id: Optional[int]
    source_type: Optional[str]
    source_id: Optional[int]
    action_type: str
    priority: str
    title: str
    reason: str
    status: str
    created_by_system: bool
    generated_batch_id: Optional[str]
    accepted_by_user_id: Optional[int]
    dismissed_by_user_id: Optional[int]
    completed_by_user_id: Optional[int]
    accepted_at: Optional[str]
    dismissed_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_response(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "action_type": self.action_type,
            "priority": self.priority,
            "title": self.title,
            "reason": self.reason,
            "status": self.status,
            "created_by_system": self.created_by_system,
            "generated_batch_id": self.generated_batch_id,
            "accepted_by_user_id": self.accepted_by_user_id,
            "dismissed_by_user_id": self.dismissed_by_user_id,
            "completed_by_user_id": self.completed_by_user_id,
            "accepted_at": self.accepted_at,
            "dismissed_at": self.dismissed_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_terminal": self.is_terminal,
        }


# --- helpers -----------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _row_to_item(row: dict[str, Any]) -> ProviderActionItem:
    # SQLite returns the boolean as 0/1; Postgres returns it as bool.
    cbs = row.get("created_by_system")
    return ProviderActionItem(
        id=int(row["id"]),
        organization_id=int(row["organization_id"]),
        patient_id=int(row["patient_id"]),
        encounter_id=(
            int(row["encounter_id"]) if row.get("encounter_id") is not None else None
        ),
        source_type=row.get("source_type"),
        source_id=(
            int(row["source_id"]) if row.get("source_id") is not None else None
        ),
        action_type=row["action_type"],
        priority=row["priority"],
        title=row.get("title") or "",
        reason=row.get("reason") or "",
        status=row["status"],
        created_by_system=bool(cbs) if cbs is not None else True,
        generated_batch_id=row.get("generated_batch_id"),
        accepted_by_user_id=(
            int(row["accepted_by_user_id"])
            if row.get("accepted_by_user_id") is not None
            else None
        ),
        dismissed_by_user_id=(
            int(row["dismissed_by_user_id"])
            if row.get("dismissed_by_user_id") is not None
            else None
        ),
        completed_by_user_id=(
            int(row["completed_by_user_id"])
            if row.get("completed_by_user_id") is not None
            else None
        ),
        accepted_at=_coerce_iso(row.get("accepted_at")),
        dismissed_at=_coerce_iso(row.get("dismissed_at")),
        completed_at=_coerce_iso(row.get("completed_at")),
        created_at=_coerce_iso(row.get("created_at")) or "",
        updated_at=_coerce_iso(row.get("updated_at")) or "",
    )


_SELECT_COLUMNS = (
    "id, organization_id, patient_id, encounter_id, source_type, "
    "source_id, action_type, priority, title, reason, status, "
    "created_by_system, generated_batch_id, accepted_by_user_id, "
    "dismissed_by_user_id, completed_by_user_id, accepted_at, "
    "dismissed_at, completed_at, created_at, updated_at"
)


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


# --- CRUD --------------------------------------------------------------


def get_action_item(
    action_id: int, *, organization_id: int, patient_id: int
) -> Optional[ProviderActionItem]:
    row = fetch_one(
        f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} "
        "WHERE id = :id AND organization_id = :org "
        "AND patient_id = :pid",
        {"id": action_id, "org": organization_id, "pid": patient_id},
    )
    return _row_to_item(row) if row else None


def list_action_items(
    *,
    organization_id: int,
    patient_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    action_type: Optional[str] = None,
    encounter_id: Optional[int] = None,
) -> list[ProviderActionItem]:
    sql = (
        f"SELECT {_SELECT_COLUMNS} FROM {_TABLE} "
        "WHERE organization_id = :org AND patient_id = :pid"
    )
    params: dict[str, Any] = {"org": organization_id, "pid": patient_id}
    if status:
        if status not in ALL_STATUSES:
            return []
        sql += " AND status = :status"
        params["status"] = status
    if priority:
        if priority not in ALL_PRIORITIES:
            return []
        sql += " AND priority = :priority"
        params["priority"] = priority
    if action_type:
        if action_type not in ALL_ACTION_TYPES:
            return []
        sql += " AND action_type = :action_type"
        params["action_type"] = action_type
    if encounter_id is not None:
        sql += " AND encounter_id = :encounter_id"
        params["encounter_id"] = encounter_id
    sql += " ORDER BY created_at DESC, id DESC"
    rows = fetch_all(sql, params)
    return [_row_to_item(r) for r in rows]


def _insert_action(
    *,
    organization_id: int,
    patient_id: int,
    encounter_id: Optional[int],
    source_type: Optional[str],
    source_id: Optional[int],
    action_type: str,
    priority: str,
    title: str,
    reason: str,
    generated_batch_id: Optional[str],
    created_by_system: bool = True,
) -> ProviderActionItem:
    if action_type not in ALL_ACTION_TYPES:
        raise ValueError(f"unknown action_type {action_type!r}")
    if priority not in ALL_PRIORITIES:
        raise ValueError(f"unknown priority {priority!r}")
    now = _now_iso()
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            _TABLE,
            {
                "organization_id": organization_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "source_type": source_type,
                "source_id": source_id,
                "action_type": action_type,
                "priority": priority,
                "title": title,
                "reason": reason,
                "status": ActionStatus.SUGGESTED,
                "created_by_system": created_by_system,
                "generated_batch_id": generated_batch_id,
                "created_at": now,
                "updated_at": now,
            },
        )
    item = get_action_item(
        new_id, organization_id=organization_id, patient_id=patient_id
    )
    assert item is not None
    return item


def _set_status(
    item: ProviderActionItem,
    *,
    new_status: str,
    user_id: int,
    timestamp_col: str,
    user_col: str,
) -> ProviderActionItem:
    now = _now_iso()
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET status = :st, "
                f"{timestamp_col} = :ts, {user_col} = :uid, "
                f"updated_at = :ts "
                f"WHERE id = :id AND organization_id = :org"
            ),
            {
                "st": new_status,
                "ts": now,
                "uid": user_id,
                "id": item.id,
                "org": item.organization_id,
            },
        )
    refreshed = get_action_item(
        item.id,
        organization_id=item.organization_id,
        patient_id=item.patient_id,
    )
    assert refreshed is not None
    return refreshed


def accept_action_item(
    item: ProviderActionItem, *, user_id: int
) -> ProviderActionItem:
    if item.status in TERMINAL_STATUSES:
        raise ImmutableProviderActionItem(item.status)
    if item.status not in _VALID_TRANSITIONS["accept"]:
        raise InvalidProviderActionTransition("accept", item.status)
    return _set_status(
        item,
        new_status=ActionStatus.ACCEPTED,
        user_id=user_id,
        timestamp_col="accepted_at",
        user_col="accepted_by_user_id",
    )


def dismiss_action_item(
    item: ProviderActionItem, *, user_id: int
) -> ProviderActionItem:
    if item.status in TERMINAL_STATUSES:
        raise ImmutableProviderActionItem(item.status)
    if item.status not in _VALID_TRANSITIONS["dismiss"]:
        raise InvalidProviderActionTransition("dismiss", item.status)
    return _set_status(
        item,
        new_status=ActionStatus.DISMISSED,
        user_id=user_id,
        timestamp_col="dismissed_at",
        user_col="dismissed_by_user_id",
    )


def complete_action_item(
    item: ProviderActionItem, *, user_id: int
) -> ProviderActionItem:
    if item.status in TERMINAL_STATUSES:
        raise ImmutableProviderActionItem(item.status)
    if item.status not in _VALID_TRANSITIONS["complete"]:
        raise InvalidProviderActionTransition("complete", item.status)
    return _set_status(
        item,
        new_status=ActionStatus.COMPLETED,
        user_id=user_id,
        timestamp_col="completed_at",
        user_col="completed_by_user_id",
    )


# --- generator ---------------------------------------------------------


@dataclass(frozen=True)
class _Suggestion:
    """Internal candidate before dedupe + persistence."""
    action_type: str
    priority: str
    title: str
    reason: str
    source_type: Optional[str]
    source_id: Optional[int]
    encounter_id: Optional[int]


# Regex vocabulary for the clinical-review prompts. The patterns are
# narrow on purpose — false positives create noise but never harm; the
# provider always reviews the suggestion before accepting it.
_CLINICAL_PATTERNS: list[tuple[str, str]] = [
    (ActionType.REVIEW_RETINAL_DETACHMENT_LANGUAGE,
     r"\bretinal\s+detachment\b"),
    (ActionType.REVIEW_RETINAL_TEAR_LANGUAGE,
     r"\bretinal\s+tear\b"),
    (ActionType.REVIEW_NEOVASCULARIZATION_LANGUAGE,
     r"\bneovascular(?:ization|isation|s)?\b"),
    (ActionType.REVIEW_SEVERE_HEMORRHAGE_LANGUAGE,
     r"\bsevere\s+(?:vitreous\s+|sub-?retinal\s+)?h(?:a|e)morrhag(?:e|ic)\b"),
]


_CLINICAL_PRIORITY: dict[str, str] = {
    ActionType.REVIEW_RETINAL_DETACHMENT_LANGUAGE: ActionPriority.HIGH,
    ActionType.REVIEW_RETINAL_TEAR_LANGUAGE: ActionPriority.HIGH,
    ActionType.REVIEW_NEOVASCULARIZATION_LANGUAGE: ActionPriority.MEDIUM,
    ActionType.REVIEW_SEVERE_HEMORRHAGE_LANGUAGE: ActionPriority.HIGH,
}


_CLINICAL_TITLES: dict[str, str] = {
    ActionType.REVIEW_RETINAL_DETACHMENT_LANGUAGE:
        "Review chart language for retinal detachment",
    ActionType.REVIEW_RETINAL_TEAR_LANGUAGE:
        "Review chart language for retinal tear",
    ActionType.REVIEW_NEOVASCULARIZATION_LANGUAGE:
        "Review chart language for neovascularization",
    ActionType.REVIEW_SEVERE_HEMORRHAGE_LANGUAGE:
        "Review chart language for severe hemorrhage",
}


def _scan_text_for_clinical_prompts(
    *,
    text_blob: str,
    source_type: str,
    source_id: int,
    encounter_id: Optional[int],
) -> list[_Suggestion]:
    out: list[_Suggestion] = []
    if not text_blob:
        return out
    haystack = text_blob.lower()
    for action_type, pattern in _CLINICAL_PATTERNS:
        if re.search(pattern, haystack):
            out.append(_Suggestion(
                action_type=action_type,
                priority=_CLINICAL_PRIORITY[action_type],
                title=_CLINICAL_TITLES[action_type],
                reason=(
                    "Chart text contains language that may need provider "
                    "review. Consider verifying the finding and confirming "
                    "appropriate documentation."
                ),
                source_type=source_type,
                source_id=source_id,
                encounter_id=encounter_id,
            ))
    return out


def _extract_clinical_text_for_artifact(row: dict[str, Any]) -> str:
    title = row.get("title") or ""
    findings = row.get("findings_text") or ""
    return f"{title}\n{findings}"


def _extract_clinical_text_for_scribe(row: dict[str, Any]) -> str:
    pieces: list[str] = []
    for k in ("source_text", "draft_note_text"):
        v = row.get(k)
        if v:
            pieces.append(str(v))
    sj = _safe_json_dict(row.get("structured_note_json"))
    for v in sj.values():
        if isinstance(v, str):
            pieces.append(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    pieces.append(item)
    return "\n".join(pieces)


def _extract_clinical_text_for_summary(row: dict[str, Any]) -> str:
    pieces: list[str] = []
    pls = row.get("plain_language_summary")
    if pls:
        pieces.append(str(pls))
    for k in ("key_findings_json", "next_steps_json", "questions_json"):
        blob = row.get(k)
        if not blob:
            continue
        try:
            decoded = json.loads(blob) if isinstance(blob, str) else blob
        except (TypeError, ValueError):
            continue
        if isinstance(decoded, list):
            for item in decoded:
                if isinstance(item, str):
                    pieces.append(item)
    return "\n".join(pieces)


def _read_recent_encounter_ids(
    *, organization_id: int, patient_id: int
) -> list[int]:
    rows = fetch_all(
        "SELECT id FROM encounters WHERE organization_id = :org AND "
        "(patient_id = :pid OR patient_identifier = :pidf) "
        "ORDER BY COALESCE(completed_at, started_at, scheduled_at, "
        "created_at) DESC, id DESC LIMIT 10",
        {
            "org": organization_id,
            "pid": patient_id,
            "pidf": _patient_identifier(patient_id, organization_id) or "",
        },
    )
    return [int(r["id"]) for r in rows]


def _patient_identifier(patient_id: int, organization_id: int) -> Optional[str]:
    row = fetch_one(
        "SELECT patient_identifier FROM patients "
        "WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": organization_id},
    )
    return row["patient_identifier"] if row else None


def _read_scribe_sessions_for_patient(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    return [
        dict(r) for r in fetch_all(
            "SELECT id, status, encounter_id, source_text, draft_note_text, "
            "structured_note_json, finalized_at "
            "FROM scribe_sessions WHERE organization_id = :org "
            "AND patient_id = :pid",
            {"org": organization_id, "pid": patient_id},
        )
    ]


def _read_artifacts_for_patient(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    return [
        dict(r) for r in fetch_all(
            "SELECT id, encounter_id, title, findings_text, signed_at "
            "FROM chart_artifacts WHERE organization_id = :org "
            "AND patient_id = :pid",
            {"org": organization_id, "pid": patient_id},
        )
    ]


def _read_summaries_for_patient(
    *, organization_id: int, patient_id: int
) -> list[dict[str, Any]]:
    return [
        dict(r) for r in fetch_all(
            "SELECT id, status, encounter_id, plain_language_summary, "
            "key_findings_json, next_steps_json, questions_json, "
            "finalized_at "
            "FROM patient_summaries WHERE organization_id = :org "
            "AND patient_id = :pid",
            {"org": organization_id, "pid": patient_id},
        )
    ]


def _build_suggestions(
    *,
    organization_id: int,
    patient_id: int,
) -> list[_Suggestion]:
    suggestions: list[_Suggestion] = []

    artifacts = _read_artifacts_for_patient(
        organization_id=organization_id, patient_id=patient_id
    )
    sessions = _read_scribe_sessions_for_patient(
        organization_id=organization_id, patient_id=patient_id
    )
    summaries = _read_summaries_for_patient(
        organization_id=organization_id, patient_id=patient_id
    )
    encounter_ids = _read_recent_encounter_ids(
        organization_id=organization_id, patient_id=patient_id
    )

    # ---- 1) Workflow completion ------------------------------------
    for a in artifacts:
        if not a.get("signed_at"):
            suggestions.append(_Suggestion(
                action_type=ActionType.SIGN_UNSIGNED_RETINAL_DIAGRAM,
                priority=ActionPriority.MEDIUM,
                title=f"Review and sign retinal diagram #{a['id']}",
                reason=(
                    "An unsigned retinal artifact exists for this "
                    "patient. Review the drawing and findings, then sign "
                    "if accurate."
                ),
                source_type="chart_artifact",
                source_id=int(a["id"]),
                encounter_id=(
                    int(a["encounter_id"]) if a.get("encounter_id") is not None
                    else None
                ),
            ))

    for s in sessions:
        st = s.get("status")
        if st == "ready_for_review":
            suggestions.append(_Suggestion(
                action_type=ActionType.REVIEW_SCRIBE_SESSION,
                priority=ActionPriority.MEDIUM,
                title=f"Review scribe session #{s['id']}",
                reason=(
                    "A scribe session is ready for provider review. "
                    "Open it to verify the structured note before "
                    "finalizing."
                ),
                source_type="scribe_session",
                source_id=int(s["id"]),
                encounter_id=(
                    int(s["encounter_id"]) if s.get("encounter_id") is not None
                    else None
                ),
            ))
        elif st == "reviewed":
            suggestions.append(_Suggestion(
                action_type=ActionType.FINALIZE_SCRIBE_SESSION,
                priority=ActionPriority.MEDIUM,
                title=f"Finalize scribe session #{s['id']}",
                reason=(
                    "A scribe session has been reviewed but not yet "
                    "finalized. Consider finalizing if the note is "
                    "ready."
                ),
                source_type="scribe_session",
                source_id=int(s["id"]),
                encounter_id=(
                    int(s["encounter_id"]) if s.get("encounter_id") is not None
                    else None
                ),
            ))
        elif st == "draft":
            # Draft session — provider can still review it, but the
            # suggestion is lower priority because it's earlier in
            # the lifecycle.
            suggestions.append(_Suggestion(
                action_type=ActionType.REVIEW_SCRIBE_SESSION,
                priority=ActionPriority.LOW,
                title=f"Review scribe session #{s['id']}",
                reason=(
                    "A draft scribe session exists. Consider reviewing "
                    "the source/transcript text before processing."
                ),
                source_type="scribe_session",
                source_id=int(s["id"]),
                encounter_id=(
                    int(s["encounter_id"]) if s.get("encounter_id") is not None
                    else None
                ),
            ))

    for sm in summaries:
        st = sm.get("status")
        if st == "draft":
            suggestions.append(_Suggestion(
                action_type=ActionType.REVIEW_PATIENT_SUMMARY,
                priority=ActionPriority.LOW,
                title=f"Review patient summary #{sm['id']}",
                reason=(
                    "A draft patient summary is awaiting provider "
                    "review. Consider editing and marking it reviewed."
                ),
                source_type="patient_summary",
                source_id=int(sm["id"]),
                encounter_id=(
                    int(sm["encounter_id"]) if sm.get("encounter_id") is not None
                    else None
                ),
            ))
        elif st == "reviewed":
            suggestions.append(_Suggestion(
                action_type=ActionType.FINALIZE_PATIENT_SUMMARY,
                priority=ActionPriority.MEDIUM,
                title=f"Finalize patient summary #{sm['id']}",
                reason=(
                    "A reviewed patient summary is awaiting "
                    "finalization. Consider finalizing if it's ready."
                ),
                source_type="patient_summary",
                source_id=int(sm["id"]),
                encounter_id=(
                    int(sm["encounter_id"]) if sm.get("encounter_id") is not None
                    else None
                ),
            ))

    # ---- 2) Pre-visit readiness / data hygiene ---------------------
    has_signed_artifact = any(a.get("signed_at") for a in artifacts)
    has_finalized_summary = any(
        sm.get("status") == "finalized" for sm in summaries
    )
    has_reviewed_or_finalized_scribe = any(
        s.get("status") in {"reviewed", "finalized"} for s in sessions
    )
    has_unsigned_artifact = any(not a.get("signed_at") for a in artifacts)

    if not has_signed_artifact and encounter_ids:
        suggestions.append(_Suggestion(
            action_type=ActionType.REVIEW_MISSING_SIGNED_RETINAL_ARTIFACT,
            priority=ActionPriority.LOW,
            title="No signed retinal artifact on file",
            reason=(
                "There is no signed retinal artifact for this patient. "
                "Consider whether the chart should include one."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))
    if not has_finalized_summary and encounter_ids:
        suggestions.append(_Suggestion(
            action_type=ActionType.REVIEW_MISSING_FINALIZED_PATIENT_SUMMARY,
            priority=ActionPriority.LOW,
            title="No finalized patient summary on file",
            reason=(
                "There is no finalized patient summary for this "
                "patient. Consider whether one should be drafted."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))
    if not has_reviewed_or_finalized_scribe and encounter_ids:
        suggestions.append(_Suggestion(
            action_type=ActionType.REVIEW_MISSING_REVIEWED_SCRIBE_SESSION,
            priority=ActionPriority.LOW,
            title="No reviewed or finalized scribe session on file",
            reason=(
                "There is no reviewed/finalized scribe session for "
                "this patient. Consider whether one should be drafted."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))

    if has_unsigned_artifact:
        suggestions.append(_Suggestion(
            action_type=ActionType.RECONCILE_UNSIGNED_ARTIFACTS,
            priority=ActionPriority.LOW,
            title="Reconcile unsigned retinal artifacts",
            reason=(
                "One or more retinal artifacts are unsigned. Consider "
                "reviewing them and either signing or discarding."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))

    if any(sm.get("status") in {"draft", "reviewed"} for sm in summaries):
        suggestions.append(_Suggestion(
            action_type=ActionType.REVIEW_UNFINALIZED_PATIENT_CONTEXT,
            priority=ActionPriority.LOW,
            title="Review unfinalized patient context",
            reason=(
                "One or more patient summaries are still in draft or "
                "reviewed state. Consider whether they should be "
                "finalized."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))

    # Generic data-gap prompt only when the patient has zero ChartNav
    # records of any kind (or only encounters). Avoids being noisy
    # when richer prompts above already cover the gaps.
    if (
        not artifacts
        and not sessions
        and not summaries
    ):
        suggestions.append(_Suggestion(
            action_type=ActionType.REVIEW_PRE_VISIT_DATA_GAPS,
            priority=ActionPriority.LOW,
            title="Review pre-visit data gaps",
            reason=(
                "ChartNav has no scribe sessions, retinal artifacts, "
                "or patient summaries on file for this patient. "
                "Consider whether the chart is ready for the visit."
            ),
            source_type=None,
            source_id=None,
            encounter_id=None,
        ))

    # ---- 3) Clinical-review language scans -------------------------
    for s in sessions:
        if s.get("status") in {"reviewed", "finalized"}:
            text_blob = _extract_clinical_text_for_scribe(s)
            suggestions.extend(_scan_text_for_clinical_prompts(
                text_blob=text_blob,
                source_type="scribe_session",
                source_id=int(s["id"]),
                encounter_id=(
                    int(s["encounter_id"]) if s.get("encounter_id") is not None
                    else None
                ),
            ))
    for a in artifacts:
        if a.get("signed_at"):
            text_blob = _extract_clinical_text_for_artifact(a)
            suggestions.extend(_scan_text_for_clinical_prompts(
                text_blob=text_blob,
                source_type="chart_artifact",
                source_id=int(a["id"]),
                encounter_id=(
                    int(a["encounter_id"]) if a.get("encounter_id") is not None
                    else None
                ),
            ))
    for sm in summaries:
        if sm.get("status") == "finalized":
            text_blob = _extract_clinical_text_for_summary(sm)
            suggestions.extend(_scan_text_for_clinical_prompts(
                text_blob=text_blob,
                source_type="patient_summary",
                source_id=int(sm["id"]),
                encounter_id=(
                    int(sm["encounter_id"]) if sm.get("encounter_id") is not None
                    else None
                ),
            ))

    return suggestions


def _existing_active_keys(
    *, organization_id: int, patient_id: int
) -> set[tuple[str, Optional[str], Optional[int], str]]:
    """Set of (action_type, source_type, source_id, title) tuples for
    items that are still in suggested or accepted state. Used to
    dedupe a fresh generate against current open items.

    Including `title` keeps the dedupe stable when the source row's
    text changes — different titles mean a different suggestion to
    show the provider.
    """
    rows = fetch_all(
        "SELECT action_type, source_type, source_id, title "
        f"FROM {_TABLE} "
        "WHERE organization_id = :org AND patient_id = :pid "
        "AND status IN ('suggested', 'accepted')",
        {"org": organization_id, "pid": patient_id},
    )
    return {
        (
            r["action_type"],
            r.get("source_type"),
            int(r["source_id"]) if r.get("source_id") is not None else None,
            r.get("title") or "",
        )
        for r in rows
    }


@dataclass(frozen=True)
class GenerateResult:
    items: list[ProviderActionItem]
    created_count: int
    reused_count: int
    generated_count: int  # candidate suggestions before dedupe
    batch_id: str

    def to_response(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "generated_count": self.generated_count,
            "created_count": self.created_count,
            "reused_count": self.reused_count,
            "items": [it.to_response() for it in self.items],
        }


def generate_action_items(
    *, organization_id: int, patient_id: int
) -> GenerateResult:
    """Generate provider-review suggestions for one patient.

    Dedupe rule: a candidate is dropped if a row with the same
    (action_type, source_type, source_id, title) is already in
    `suggested` or `accepted`. This way repeated generate calls
    don't create churn while a prior suggestion is still open.
    """
    candidates = _build_suggestions(
        organization_id=organization_id, patient_id=patient_id
    )
    existing = _existing_active_keys(
        organization_id=organization_id, patient_id=patient_id
    )
    batch_id = uuid.uuid4().hex
    created: list[ProviderActionItem] = []
    seen_in_batch: set[tuple[str, Optional[str], Optional[int], str]] = set()
    reused = 0
    for c in candidates:
        key = (c.action_type, c.source_type, c.source_id, c.title)
        # Dedupe across both existing open items and items we already
        # created earlier in *this* batch (e.g. two sessions with the
        # same title would otherwise duplicate).
        if key in existing or key in seen_in_batch:
            reused += 1
            continue
        seen_in_batch.add(key)
        item = _insert_action(
            organization_id=organization_id,
            patient_id=patient_id,
            encounter_id=c.encounter_id,
            source_type=c.source_type,
            source_id=c.source_id,
            action_type=c.action_type,
            priority=c.priority,
            title=c.title,
            reason=c.reason,
            generated_batch_id=batch_id,
        )
        created.append(item)
    return GenerateResult(
        items=created,
        created_count=len(created),
        reused_count=reused,
        generated_count=len(candidates),
        batch_id=batch_id,
    )


__all__ = [
    "ActionPriority",
    "ActionStatus",
    "ActionType",
    "ALL_ACTION_TYPES",
    "ALL_PRIORITIES",
    "ALL_STATUSES",
    "GenerateResult",
    "ImmutableProviderActionItem",
    "InvalidProviderActionTransition",
    "ProviderActionItem",
    "ProviderActionItemNotFound",
    "ProviderActionSourceMismatch",
    "TERMINAL_STATUSES",
    "accept_action_item",
    "complete_action_item",
    "dismiss_action_item",
    "generate_action_items",
    "get_action_item",
    "list_action_items",
]
