"""Patient-friendly summary lifecycle service.

Phase 9. One row per provider-reviewed patient-friendly summary draft.
The unit of work between provider-reviewed clinical content (preferred:
a reviewed/finalized scribe_sessions row) and a final summary that the
provider has explicitly approved.

This module is responsible for:
  * status constants
  * the status transition matrix
  * exception types the route layer translates to HTTP errors
  * deterministic generator v1 (no LLM, no diagnosis, no orders)
  * raw-SQL persistence via app.db (org-scoped on every read/write)
  * a normalize_response helper so list/object JSON fields reach the
    frontend as real objects, not JSON-encoded strings

This service NEVER:
  - sends anything to a patient
  - calls an external LLM
  - claims a diagnosis
  - creates orders / prescriptions / referrals
  - writes back into scribe_sessions
  - logs summary body / key findings / next steps / questions /
    limitations / review notes into the audit trail (the route layer
    only audits metadata)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import text

from app.db import engine, fetch_one, insert_returning_id, transaction


_TABLE = "patient_summaries"


# --- enums --------------------------------------------------------------


class SummaryStatus:
    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"
    DISCARDED = "discarded"


ALL_STATUSES: frozenset[str] = frozenset({
    SummaryStatus.DRAFT,
    SummaryStatus.REVIEWED,
    SummaryStatus.FINALIZED,
    SummaryStatus.DISCARDED,
})

TERMINAL_STATUSES: frozenset[str] = frozenset({
    SummaryStatus.FINALIZED,
    SummaryStatus.DISCARDED,
})


# --- transition matrix --------------------------------------------------
#
#   review   : draft     -> reviewed
#   finalize : reviewed  -> finalized
#   discard  : draft|reviewed -> discarded
#   update   : allowed only when status NOT IN {finalized, discarded}
#
# Direct draft -> finalized is rejected by InvalidPatientSummaryTransition.

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "review": frozenset({SummaryStatus.DRAFT}),
    "finalize": frozenset({SummaryStatus.REVIEWED}),
    "discard": frozenset({SummaryStatus.DRAFT, SummaryStatus.REVIEWED}),
}


# --- exceptions ---------------------------------------------------------


class PatientSummaryNotFound(Exception):
    """Summary does not exist for this caller's org+patient."""


class InvalidPatientSummaryTransition(Exception):
    """Caller asked for an action the current status does not allow."""

    def __init__(self, action: str, current_status: str):
        super().__init__(
            f"cannot {action!r} from status {current_status!r}"
        )
        self.action = action
        self.current_status = current_status


class ImmutablePatientSummary(Exception):
    """Mutation attempted against a finalized or discarded summary."""

    def __init__(self, current_status: str):
        super().__init__(
            f"summary is {current_status!r} and cannot be modified"
        )
        self.current_status = current_status


class PatientSummarySourceMismatch(Exception):
    """Provided scribe_session_id does not belong to the same org/patient."""


# --- record + helpers ---------------------------------------------------


@dataclass
class PatientSummary:
    id: int
    organization_id: int
    patient_id: int
    encounter_id: Optional[int]
    scribe_session_id: Optional[int]
    created_by_user_id: int
    reviewed_by_user_id: Optional[int]
    status: str
    plain_language_summary: str
    key_findings: list[str]
    next_steps: list[str]
    questions: list[str]
    limitations_notice: str
    review_notes: Optional[str]
    finalized_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    discarded_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_response(self) -> dict[str, Any]:
        """Boundary-safe shape for the route layer.

        list/object fields are returned as real arrays so the frontend
        never has to double-parse JSON.
        """
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "scribe_session_id": self.scribe_session_id,
            "created_by_user_id": self.created_by_user_id,
            "reviewed_by_user_id": self.reviewed_by_user_id,
            "status": self.status,
            "plain_language_summary": self.plain_language_summary,
            "key_findings": list(self.key_findings),
            "next_steps": list(self.next_steps),
            "questions": list(self.questions),
            "limitations_notice": self.limitations_notice,
            "review_notes": self.review_notes,
            "finalized_at": _iso(self.finalized_at),
            "reviewed_at": _iso(self.reviewed_at),
            "discarded_at": _iso(self.discarded_at),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "is_terminal": self.is_terminal,
        }


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _decode_list(raw: Any) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw]
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(v) for v in parsed]


def _row_to_summary(row: dict[str, Any]) -> PatientSummary:
    return PatientSummary(
        id=int(row["id"]),
        organization_id=int(row["organization_id"]),
        patient_id=int(row["patient_id"]),
        encounter_id=row.get("encounter_id"),
        scribe_session_id=row.get("scribe_session_id"),
        created_by_user_id=int(row["created_by_user_id"]),
        reviewed_by_user_id=row.get("reviewed_by_user_id"),
        status=row.get("status") or SummaryStatus.DRAFT,
        plain_language_summary=row.get("plain_language_summary") or "",
        key_findings=_decode_list(row.get("key_findings_json")),
        next_steps=_decode_list(row.get("next_steps_json")),
        questions=_decode_list(row.get("questions_json")),
        limitations_notice=row.get("limitations_notice") or "",
        review_notes=row.get("review_notes"),
        finalized_at=row.get("finalized_at"),
        reviewed_at=row.get("reviewed_at"),
        discarded_at=row.get("discarded_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


# --- generator v1 -------------------------------------------------------
#
# Deterministic, no LLM, no diagnosis. Pulls from a scribe session's
# structured note when present, else from its draft note, else surfaces
# explicit limitations. Provider review is mandatory before any further
# transition. The output never claims a diagnosis or recommends a
# treatment.


DEFAULT_LIMITATIONS_NOTICE = (
    "This summary is a draft for provider review and may be incomplete."
)


@dataclass
class _GeneratedSummary:
    plain_language_summary: str
    key_findings: list[str]
    next_steps: list[str]
    questions: list[str]
    limitations_notice: str


def _split_lines(text_in: str) -> list[str]:
    out: list[str] = []
    for raw in (text_in or "").splitlines():
        s = raw.strip(" \t.;:-")
        if s:
            out.append(s)
    return out


def _split_bullets(text_in: str) -> list[str]:
    """Split a section into reasonable line-or-clause bullets.

    Splits on newline first, then on `;` separators if a line has more
    than one clause. Keeps short single-line items intact.
    """
    lines = _split_lines(text_in)
    bullets: list[str] = []
    for line in lines:
        # Split on `;` for clause-level bullets, but only when there's
        # more than one clause and each is non-trivial.
        parts = [p.strip(" .;:-") for p in line.split(";")]
        parts = [p for p in parts if len(p) > 2]
        if len(parts) > 1:
            bullets.extend(parts)
        else:
            bullets.append(line)
    return bullets


def _normalize_provider_instructions(text_in: Optional[str]) -> str:
    if not text_in:
        return ""
    # Single line, trimmed, no newlines so it stays inside one summary
    # paragraph.
    return re.sub(r"\s+", " ", text_in).strip()


def generate_summary(
    *,
    structured_note: Optional[dict[str, Any]],
    draft_note_text: Optional[str],
    provider_instructions: Optional[str] = None,
) -> _GeneratedSummary:
    """Produce a deterministic patient-friendly summary draft.

    Source preference:
      1. structured_note["chief_complaint"|"hpi"|"exam"|"assessment"|
         "plan"] — preferred when present.
      2. draft_note_text fallback.
      3. neither — emit limitations only.

    Output rules:
      * Plain language. Never invents diagnoses. Never invents
        treatments / medications / orders.
      * The limitations notice is ALWAYS present, regardless of input.
        When source is sparse, it explicitly says the summary is
        limited by available chart text.
    """
    structured = structured_note or {}
    sections: dict[str, str] = {}
    for key in ("chief_complaint", "hpi", "exam", "assessment", "plan"):
        value = structured.get(key)
        if isinstance(value, str) and value.strip():
            sections[key] = value.strip()

    has_structured = bool(sections)
    has_draft = bool((draft_note_text or "").strip())

    summary_lines: list[str] = []
    key_findings: list[str] = []
    next_steps: list[str] = []
    questions: list[str] = []
    limitations = DEFAULT_LIMITATIONS_NOTICE

    if has_structured:
        if "chief_complaint" in sections:
            summary_lines.append(
                f"You came in about: {sections['chief_complaint']}."
            )
        if "hpi" in sections:
            summary_lines.append(
                f"Background your provider noted: {sections['hpi']}."
            )
        if "exam" in sections:
            key_findings.extend(_split_bullets(sections["exam"]))
        if "assessment" in sections:
            # Assessment goes verbatim into key findings — we do NOT
            # rephrase it into a diagnosis claim of our own.
            key_findings.extend(_split_bullets(sections["assessment"]))
        if "plan" in sections:
            next_steps.extend(_split_bullets(sections["plan"]))
            questions.append(
                "Is there anything in the plan I should call about if it changes?"
            )
        questions.extend(
            [
                "What should I watch for that means I should call back?",
                "When is my next visit, and what should I bring?",
            ]
        )
    elif has_draft:
        summary_lines.append(
            "Your provider drafted a note from this visit. The provider will "
            "share specifics with you in plain language during review."
        )
        # We do NOT parse the draft note itself into "findings" — it has
        # not been reviewed yet. We only acknowledge that a draft exists.
        limitations = (
            DEFAULT_LIMITATIONS_NOTICE
            + " Source content was an unprocessed draft note; details "
            "will be added after the provider reviews."
        )
        questions.append(
            "Could you walk me through what is in the draft note?"
        )
    else:
        summary_lines.append(
            "Your provider has started a patient-friendly summary for "
            "this visit. Specifics will be added after the provider "
            "reviews the chart."
        )
        limitations = (
            DEFAULT_LIMITATIONS_NOTICE
            + " No structured chart text was available at draft time."
        )

    instructions = _normalize_provider_instructions(provider_instructions)
    if instructions:
        # Provider-supplied tone/context note is included verbatim as a
        # line in the summary. We never act on instructions like
        # "diagnose this" or "prescribe X" — the generator has no such
        # capability, only sectioning and labeling.
        summary_lines.append(f"Note from your provider: {instructions}")

    plain_language_summary = "\n".join(summary_lines).strip()
    return _GeneratedSummary(
        plain_language_summary=plain_language_summary,
        key_findings=key_findings,
        next_steps=next_steps,
        questions=questions,
        limitations_notice=limitations,
    )


# --- persistence helpers ------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _verify_scribe_session(
    scribe_session_id: int, *, organization_id: int, patient_id: int
) -> dict[str, Any]:
    """Scribe session must belong to the same org and patient.

    Returns the row dict so the caller can use its content for
    generation. Raises PatientSummarySourceMismatch if either check
    fails. (We surface BOTH org and patient mismatches as the same
    sentinel so cross-org leakage isn't possible.)
    """
    row = fetch_one(
        "SELECT id, organization_id, patient_id, status, "
        "draft_note_text, structured_note_json "
        "FROM scribe_sessions WHERE id = :id",
        {"id": scribe_session_id},
    )
    if not row:
        raise PatientSummarySourceMismatch(
            f"scribe session {scribe_session_id} not found"
        )
    if int(row["organization_id"]) != int(organization_id):
        raise PatientSummarySourceMismatch(
            f"scribe session {scribe_session_id} not in your organization"
        )
    if int(row["patient_id"]) != int(patient_id):
        raise PatientSummarySourceMismatch(
            f"scribe session {scribe_session_id} belongs to a different patient"
        )
    return dict(row)


def _decode_structured_note_json(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def create_summary(
    *,
    organization_id: int,
    patient_id: int,
    created_by_user_id: int,
    encounter_id: Optional[int] = None,
    scribe_session_id: Optional[int] = None,
    provider_instructions: Optional[str] = None,
) -> PatientSummary:
    """Create a new draft summary, generating content from the source."""
    structured: Optional[dict[str, Any]] = None
    draft_text: Optional[str] = None

    if scribe_session_id is not None:
        sess = _verify_scribe_session(
            scribe_session_id,
            organization_id=organization_id,
            patient_id=patient_id,
        )
        # Prefer reviewed/finalized scribe sessions; we still allow
        # earlier statuses but tag the limitation.
        structured = _decode_structured_note_json(sess.get("structured_note_json"))
        draft_text = sess.get("draft_note_text")

    generated = generate_summary(
        structured_note=structured,
        draft_note_text=draft_text,
        provider_instructions=provider_instructions,
    )

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            _TABLE,
            {
                "organization_id": organization_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "scribe_session_id": scribe_session_id,
                "created_by_user_id": created_by_user_id,
                "reviewed_by_user_id": None,
                "status": SummaryStatus.DRAFT,
                "plain_language_summary": generated.plain_language_summary,
                "key_findings_json": json.dumps(generated.key_findings),
                "next_steps_json": json.dumps(generated.next_steps),
                "questions_json": json.dumps(generated.questions),
                "limitations_notice": generated.limitations_notice,
                "review_notes": None,
                "finalized_at": None,
                "reviewed_at": None,
                "discarded_at": None,
            },
        )
    fetched = get_summary(
        new_id, organization_id=organization_id, patient_id=patient_id
    )
    assert fetched is not None
    return fetched


def list_summaries_for_patient(
    *, organization_id: int, patient_id: int
) -> list[PatientSummary]:
    sql = (
        f"SELECT * FROM {_TABLE} "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY created_at DESC, id DESC"
    )
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"org": organization_id, "pid": patient_id},
        ).mappings().all()
    return [_row_to_summary(dict(r)) for r in rows]


def get_summary(
    summary_id: int,
    *,
    organization_id: int,
    patient_id: int,
) -> Optional[PatientSummary]:
    row = fetch_one(
        f"SELECT * FROM {_TABLE} "
        "WHERE id = :id AND organization_id = :org AND patient_id = :pid",
        {"id": summary_id, "org": organization_id, "pid": patient_id},
    )
    return _row_to_summary(row) if row else None


def update_summary(
    summary: PatientSummary,
    *,
    plain_language_summary: Optional[str] = None,
    key_findings: Optional[list[str]] = None,
    next_steps: Optional[list[str]] = None,
    questions: Optional[list[str]] = None,
    limitations_notice: Optional[str] = None,
    review_notes: Optional[str] = None,
) -> PatientSummary:
    """In-place update of a non-terminal summary.

    Sentinel-by-`None` semantics: omit a field to leave it unchanged;
    pass `""` or `[]` to clear it.
    """
    if summary.is_terminal:
        raise ImmutablePatientSummary(summary.status)

    sets: list[str] = ["updated_at = :now"]
    params: dict[str, Any] = {
        "id": summary.id,
        "org": summary.organization_id,
        "now": _now(),
    }

    if plain_language_summary is not None:
        sets.append("plain_language_summary = :pls")
        params["pls"] = plain_language_summary
    if key_findings is not None:
        sets.append("key_findings_json = :kf")
        params["kf"] = json.dumps(list(key_findings))
    if next_steps is not None:
        sets.append("next_steps_json = :ns")
        params["ns"] = json.dumps(list(next_steps))
    if questions is not None:
        sets.append("questions_json = :q")
        params["q"] = json.dumps(list(questions))
    if limitations_notice is not None:
        sets.append("limitations_notice = :ln")
        params["ln"] = limitations_notice
    if review_notes is not None:
        sets.append("review_notes = :rn")
        params["rn"] = review_notes

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET {', '.join(sets)} "
                "WHERE id = :id AND organization_id = :org"
            ),
            params,
        )
    refreshed = get_summary(
        summary.id,
        organization_id=summary.organization_id,
        patient_id=summary.patient_id,
    )
    assert refreshed is not None
    return refreshed


def review_summary(
    summary: PatientSummary,
    *,
    reviewer_user_id: int,
    review_notes: Optional[str] = None,
) -> PatientSummary:
    if summary.status not in _VALID_TRANSITIONS["review"]:
        if summary.is_terminal:
            raise ImmutablePatientSummary(summary.status)
        raise InvalidPatientSummaryTransition("review", summary.status)

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "status = :status, "
                "reviewed_at = :now, "
                "reviewed_by_user_id = :uid, "
                "review_notes = COALESCE(:notes, review_notes), "
                "updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "status": SummaryStatus.REVIEWED,
                "now": _now(),
                "uid": reviewer_user_id,
                "notes": review_notes,
                "id": summary.id,
                "org": summary.organization_id,
            },
        )
    refreshed = get_summary(
        summary.id,
        organization_id=summary.organization_id,
        patient_id=summary.patient_id,
    )
    assert refreshed is not None
    return refreshed


def finalize_summary(summary: PatientSummary) -> PatientSummary:
    if summary.status not in _VALID_TRANSITIONS["finalize"]:
        if summary.is_terminal:
            raise ImmutablePatientSummary(summary.status)
        raise InvalidPatientSummaryTransition("finalize", summary.status)

    now = _now()
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "status = :status, "
                "finalized_at = :now, "
                "updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "status": SummaryStatus.FINALIZED,
                "now": now,
                "id": summary.id,
                "org": summary.organization_id,
            },
        )
    refreshed = get_summary(
        summary.id,
        organization_id=summary.organization_id,
        patient_id=summary.patient_id,
    )
    assert refreshed is not None
    return refreshed


def discard_summary(summary: PatientSummary) -> PatientSummary:
    if summary.status not in _VALID_TRANSITIONS["discard"]:
        if summary.is_terminal:
            raise ImmutablePatientSummary(summary.status)
        raise InvalidPatientSummaryTransition("discard", summary.status)

    now = _now()
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "status = :status, "
                "discarded_at = :now, "
                "updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "status": SummaryStatus.DISCARDED,
                "now": now,
                "id": summary.id,
                "org": summary.organization_id,
            },
        )
    refreshed = get_summary(
        summary.id,
        organization_id=summary.organization_id,
        patient_id=summary.patient_id,
    )
    assert refreshed is not None
    return refreshed


__all__: Iterable[str] = (
    "SummaryStatus",
    "ALL_STATUSES",
    "TERMINAL_STATUSES",
    "PatientSummary",
    "PatientSummaryNotFound",
    "InvalidPatientSummaryTransition",
    "ImmutablePatientSummary",
    "PatientSummarySourceMismatch",
    "DEFAULT_LIMITATIONS_NOTICE",
    "generate_summary",
    "create_summary",
    "list_summaries_for_patient",
    "get_summary",
    "update_summary",
    "review_summary",
    "finalize_summary",
    "discard_summary",
)
