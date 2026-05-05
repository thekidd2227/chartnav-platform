"""Scribe-session lifecycle service.

Phase 8. One row per AI scribe session: the unit of work between a
provider's source/transcript text and a finalized clinical artifact.

This module is responsible for:
  * status + input_mode constants
  * the status transition matrix
  * exception types the route layer translates to HTTP errors
  * deterministic processing v1 (heading-based section parser)
  * raw-SQL persistence via app.db (org-scoped on every read/write)
  * a normalize_response helper so structured_note_json reaches the
    frontend as a real object, not a JSON-encoded string

No LLM. No diagnosis. Processing v1 only structures provided text.

Audit safety: nothing in this module logs source_text, transcript_text,
draft_note_text, structured_note_json bodies, or review_notes. The
route layer's audit_record(...) call is metadata-only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.db import engine, fetch_one, insert_returning_id, transaction


_TABLE = "scribe_sessions"


# --- enums --------------------------------------------------------------


class ScribeStatus:
    DRAFT = "draft"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"
    DISCARDED = "discarded"


ALL_STATUSES: frozenset[str] = frozenset({
    ScribeStatus.DRAFT,
    ScribeStatus.PROCESSING,
    ScribeStatus.READY_FOR_REVIEW,
    ScribeStatus.REVIEWED,
    ScribeStatus.FINALIZED,
    ScribeStatus.DISCARDED,
})

TERMINAL_STATUSES: frozenset[str] = frozenset({
    ScribeStatus.FINALIZED,
    ScribeStatus.DISCARDED,
})


class InputMode:
    PASTED_TEXT = "pasted_text"
    TRANSCRIPT = "transcript"
    AUDIO_PLACEHOLDER = "audio_placeholder"


ALL_INPUT_MODES: frozenset[str] = frozenset({
    InputMode.PASTED_TEXT,
    InputMode.TRANSCRIPT,
    InputMode.AUDIO_PLACEHOLDER,
})


# --- transition matrix --------------------------------------------------
#
# Per spec:
#   draft, processing, ready_for_review, reviewed, finalized, discarded
#
#   process     : draft           -> processing -> ready_for_review (synchronous)
#   review      : ready_for_review -> reviewed
#   finalize    : reviewed         -> finalized        (immutable thereafter)
#   discard     : draft|processing|ready_for_review|reviewed -> discarded
#                                                              (immutable thereafter)
#   update      : allowed only when status NOT IN {finalized, discarded}

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "process": frozenset({ScribeStatus.DRAFT}),
    "review": frozenset({ScribeStatus.READY_FOR_REVIEW}),
    "finalize": frozenset({ScribeStatus.REVIEWED}),
    "discard": frozenset({
        ScribeStatus.DRAFT,
        ScribeStatus.PROCESSING,
        ScribeStatus.READY_FOR_REVIEW,
        ScribeStatus.REVIEWED,
    }),
}


# --- exceptions ---------------------------------------------------------


class ScribeSessionNotFound(Exception):
    """Session does not exist for this caller's org+patient."""


class InvalidScribeTransition(Exception):
    """Caller asked for an action the current status does not allow."""

    def __init__(self, action: str, current_status: str):
        super().__init__(
            f"cannot {action!r} from status {current_status!r}"
        )
        self.action = action
        self.current_status = current_status


class ImmutableScribeSession(Exception):
    """Mutation attempted against a finalized or discarded session."""

    def __init__(self, current_status: str):
        super().__init__(
            f"session is {current_status!r} and cannot be modified"
        )
        self.current_status = current_status


class PatientEncounterMismatch(Exception):
    """Provided encounter_id does not belong to the same patient."""


# --- record + helpers ---------------------------------------------------


@dataclass
class ScribeSession:
    id: int
    organization_id: int
    patient_id: int
    encounter_id: Optional[int]
    created_by_user_id: int
    status: str
    input_mode: str
    source_text: Optional[str]
    transcript_text: Optional[str]
    draft_note_text: Optional[str]
    structured_note: dict[str, Any]
    linked_artifact_id: Optional[int]
    review_notes: Optional[str]
    finalized_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reviewed_by_user_id: Optional[int]
    discarded_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_response(self) -> dict[str, Any]:
        """Boundary-safe shape for the route layer.

        `structured_note_json` is rendered as a real object (not a
        JSON-encoded string) so frontends never have to double-parse.
        """
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
            "created_by_user_id": self.created_by_user_id,
            "status": self.status,
            "input_mode": self.input_mode,
            "source_text": self.source_text,
            "transcript_text": self.transcript_text,
            "draft_note_text": self.draft_note_text,
            "structured_note_json": self.structured_note,
            "linked_artifact_id": self.linked_artifact_id,
            "review_notes": self.review_notes,
            "finalized_at": _iso(self.finalized_at),
            "reviewed_at": _iso(self.reviewed_at),
            "reviewed_by_user_id": self.reviewed_by_user_id,
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


def _decode_structured(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _row_to_session(row: dict[str, Any]) -> ScribeSession:
    return ScribeSession(
        id=int(row["id"]),
        organization_id=int(row["organization_id"]),
        patient_id=int(row["patient_id"]),
        encounter_id=row.get("encounter_id"),
        created_by_user_id=int(row["created_by_user_id"]),
        status=row.get("status") or ScribeStatus.DRAFT,
        input_mode=row.get("input_mode") or InputMode.PASTED_TEXT,
        source_text=row.get("source_text"),
        transcript_text=row.get("transcript_text"),
        draft_note_text=row.get("draft_note_text"),
        structured_note=_decode_structured(row.get("structured_note_json")),
        linked_artifact_id=row.get("linked_artifact_id"),
        review_notes=row.get("review_notes"),
        finalized_at=row.get("finalized_at"),
        reviewed_at=row.get("reviewed_at"),
        reviewed_by_user_id=row.get("reviewed_by_user_id"),
        discarded_at=row.get("discarded_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


# --- processing v1 ------------------------------------------------------
#
# Deterministic heading-based parser. Recognized headings:
#   chief complaint / chief_complaint / cc
#   hpi
#   exam
#   assessment
#   plan
# Anything outside a known heading lands in unassigned_text. The
# function never claims a diagnosis; the caller marks the result as
# "draft" and the provider must review.


_HEADING_TO_KEY: dict[str, str] = {
    "chief complaint": "chief_complaint",
    "chief_complaint": "chief_complaint",
    "cc": "chief_complaint",
    "hpi": "hpi",
    "exam": "exam",
    "assessment": "assessment",
    "plan": "plan",
}

_HEADING_RE = re.compile(
    r"^\s*(chief\s+complaint|chief_complaint|cc|hpi|exam|assessment|plan)"
    r"\s*[:\-]\s*",
    re.IGNORECASE,
)

DRAFT_PREFIX = "Draft — provider review required"


def parse_sections(text_in: str) -> dict[str, str]:
    """Split text by recognized headings into a structured note.

    Heading detection is line-leading and case-insensitive. The first
    paragraph before any heading is dropped into `unassigned_text`.
    Sections appear in the dict only when they contain content.
    """
    sections: dict[str, list[str]] = {}
    current_key = "unassigned_text"

    if not text_in:
        return {}

    for raw_line in text_in.splitlines():
        line = raw_line.rstrip()
        m = _HEADING_RE.match(line)
        if m:
            heading = m.group(1).lower().strip()
            current_key = _HEADING_TO_KEY.get(heading, "unassigned_text")
            remainder = line[m.end():].strip()
            if remainder:
                sections.setdefault(current_key, []).append(remainder)
            continue
        if line.strip():
            sections.setdefault(current_key, []).append(line)

    return {
        key: "\n".join(parts).strip()
        for key, parts in sections.items()
        if "".join(parts).strip()
    }


def build_draft_note(structured: dict[str, str]) -> str:
    """Render the structured sections into a human-readable draft note.

    Always begins with the explicit "Draft — provider review required"
    banner so the frontend cannot ship the text as a finalized note.
    """
    order = [
        ("chief_complaint", "Chief complaint"),
        ("hpi", "HPI"),
        ("exam", "Exam"),
        ("assessment", "Assessment"),
        ("plan", "Plan"),
        ("unassigned_text", "Unassigned"),
    ]
    lines: list[str] = [DRAFT_PREFIX]
    for key, label in order:
        if key in structured and structured[key]:
            lines.append("")
            lines.append(f"{label}:")
            lines.append(structured[key])
    return "\n".join(lines)


# --- persistence (org-scoped) -------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _verify_encounter(
    encounter_id: int, *, organization_id: int, patient_id: int
) -> None:
    """Encounter must belong to the same org. If the encounters row has
    a numeric `patient_id`, it must match the session's patient_id.

    Some encounter rows in this repo predate native patients and link
    via `patient_identifier` instead — we only enforce mismatch when
    the encounter row has a non-null numeric patient_id.
    """
    row = fetch_one(
        "SELECT id, organization_id, patient_id "
        "FROM encounters WHERE id = :id AND organization_id = :org",
        {"id": encounter_id, "org": organization_id},
    )
    if not row:
        # Surfaces as 404 in the route layer — same shape as
        # cross-org lookups.
        raise ScribeSessionNotFound(f"encounter {encounter_id} not in your org")
    enc_patient = row.get("patient_id")
    if enc_patient is not None and int(enc_patient) != patient_id:
        raise PatientEncounterMismatch(
            f"encounter {encounter_id} belongs to patient {enc_patient}, "
            f"not {patient_id}"
        )


def _verify_linked_artifact(
    linked_artifact_id: int, *, organization_id: int
) -> None:
    """Linked artifact must be in the same org, if it exists."""
    row = fetch_one(
        "SELECT id FROM chart_artifacts WHERE id = :id AND organization_id = :org",
        {"id": linked_artifact_id, "org": organization_id},
    )
    if not row:
        raise ScribeSessionNotFound(
            f"linked_artifact {linked_artifact_id} not in your org"
        )


def create_session(
    *,
    organization_id: int,
    patient_id: int,
    created_by_user_id: int,
    encounter_id: Optional[int] = None,
    input_mode: str = InputMode.PASTED_TEXT,
    source_text: Optional[str] = None,
    transcript_text: Optional[str] = None,
    linked_artifact_id: Optional[int] = None,
) -> ScribeSession:
    if input_mode not in ALL_INPUT_MODES:
        raise ValueError(f"invalid input_mode {input_mode!r}")
    if encounter_id is not None:
        _verify_encounter(
            encounter_id,
            organization_id=organization_id,
            patient_id=patient_id,
        )
    if linked_artifact_id is not None:
        _verify_linked_artifact(linked_artifact_id, organization_id=organization_id)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            _TABLE,
            {
                "organization_id": organization_id,
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "created_by_user_id": created_by_user_id,
                "status": ScribeStatus.DRAFT,
                "input_mode": input_mode,
                "source_text": source_text,
                "transcript_text": transcript_text,
                "draft_note_text": None,
                "structured_note_json": None,
                "linked_artifact_id": linked_artifact_id,
                "review_notes": None,
                "finalized_at": None,
                "reviewed_at": None,
                "reviewed_by_user_id": None,
                "discarded_at": None,
            },
        )
    fetched = get_session(new_id, organization_id=organization_id, patient_id=patient_id)
    assert fetched is not None
    return fetched


def list_sessions_for_patient(
    *,
    organization_id: int,
    patient_id: int,
) -> list[ScribeSession]:
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
    return [_row_to_session(dict(r)) for r in rows]


def get_session(
    session_id: int,
    *,
    organization_id: int,
    patient_id: int,
) -> Optional[ScribeSession]:
    row = fetch_one(
        f"SELECT * FROM {_TABLE} "
        "WHERE id = :id AND organization_id = :org AND patient_id = :pid",
        {"id": session_id, "org": organization_id, "pid": patient_id},
    )
    return _row_to_session(row) if row else None


def update_session(
    session: ScribeSession,
    *,
    source_text: Optional[str] = None,
    transcript_text: Optional[str] = None,
    review_notes: Optional[str] = None,
    encounter_id: Optional[int] = None,
    linked_artifact_id: Optional[int] = None,
    input_mode: Optional[str] = None,
) -> ScribeSession:
    """Update a non-terminal session in place.

    Only mutates fields the caller actually supplied (uses sentinel-by-
    `None` semantics — pass an empty string to clear a text field).
    """
    if session.is_terminal:
        raise ImmutableScribeSession(session.status)

    sets: list[str] = ["updated_at = :now"]
    params: dict[str, Any] = {
        "id": session.id,
        "org": session.organization_id,
        "now": _now(),
    }

    if source_text is not None:
        sets.append("source_text = :source_text")
        params["source_text"] = source_text
    if transcript_text is not None:
        sets.append("transcript_text = :transcript_text")
        params["transcript_text"] = transcript_text
    if review_notes is not None:
        sets.append("review_notes = :review_notes")
        params["review_notes"] = review_notes
    if input_mode is not None:
        if input_mode not in ALL_INPUT_MODES:
            raise ValueError(f"invalid input_mode {input_mode!r}")
        sets.append("input_mode = :input_mode")
        params["input_mode"] = input_mode
    if encounter_id is not None:
        _verify_encounter(
            encounter_id,
            organization_id=session.organization_id,
            patient_id=session.patient_id,
        )
        sets.append("encounter_id = :encounter_id")
        params["encounter_id"] = encounter_id
    if linked_artifact_id is not None:
        _verify_linked_artifact(
            linked_artifact_id, organization_id=session.organization_id
        )
        sets.append("linked_artifact_id = :linked_artifact_id")
        params["linked_artifact_id"] = linked_artifact_id

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET {', '.join(sets)} "
                "WHERE id = :id AND organization_id = :org"
            ),
            params,
        )
    refreshed = get_session(
        session.id,
        organization_id=session.organization_id,
        patient_id=session.patient_id,
    )
    assert refreshed is not None
    return refreshed


def process_session(session: ScribeSession) -> ScribeSession:
    """Run processing v1 and advance to ready_for_review."""
    if session.status not in _VALID_TRANSITIONS["process"]:
        if session.is_terminal:
            raise ImmutableScribeSession(session.status)
        raise InvalidScribeTransition("process", session.status)

    text_in = session.source_text or session.transcript_text or ""
    structured = parse_sections(text_in)
    draft_text = build_draft_note(structured)
    structured_payload = json.dumps(structured)

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "status = :status, "
                "draft_note_text = :draft, "
                "structured_note_json = :structured, "
                "updated_at = :now "
                "WHERE id = :id AND organization_id = :org"
            ),
            {
                "status": ScribeStatus.READY_FOR_REVIEW,
                "draft": draft_text,
                "structured": structured_payload,
                "now": _now(),
                "id": session.id,
                "org": session.organization_id,
            },
        )
    refreshed = get_session(
        session.id,
        organization_id=session.organization_id,
        patient_id=session.patient_id,
    )
    assert refreshed is not None
    return refreshed


def review_session(
    session: ScribeSession,
    *,
    reviewer_user_id: int,
    review_notes: Optional[str] = None,
) -> ScribeSession:
    if session.status not in _VALID_TRANSITIONS["review"]:
        if session.is_terminal:
            raise ImmutableScribeSession(session.status)
        raise InvalidScribeTransition("review", session.status)

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
                "status": ScribeStatus.REVIEWED,
                "now": _now(),
                "uid": reviewer_user_id,
                "notes": review_notes,
                "id": session.id,
                "org": session.organization_id,
            },
        )
    refreshed = get_session(
        session.id,
        organization_id=session.organization_id,
        patient_id=session.patient_id,
    )
    assert refreshed is not None
    return refreshed


def finalize_session(session: ScribeSession) -> ScribeSession:
    if session.status not in _VALID_TRANSITIONS["finalize"]:
        if session.is_terminal:
            raise ImmutableScribeSession(session.status)
        raise InvalidScribeTransition("finalize", session.status)

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
                "status": ScribeStatus.FINALIZED,
                "now": now,
                "id": session.id,
                "org": session.organization_id,
            },
        )
    refreshed = get_session(
        session.id,
        organization_id=session.organization_id,
        patient_id=session.patient_id,
    )
    assert refreshed is not None
    return refreshed


def discard_session(session: ScribeSession) -> ScribeSession:
    if session.status not in _VALID_TRANSITIONS["discard"]:
        if session.is_terminal:
            raise ImmutableScribeSession(session.status)
        raise InvalidScribeTransition("discard", session.status)

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
                "status": ScribeStatus.DISCARDED,
                "now": now,
                "id": session.id,
                "org": session.organization_id,
            },
        )
    refreshed = get_session(
        session.id,
        organization_id=session.organization_id,
        patient_id=session.patient_id,
    )
    assert refreshed is not None
    return refreshed


__all__ = (
    "ScribeStatus",
    "InputMode",
    "ALL_STATUSES",
    "ALL_INPUT_MODES",
    "TERMINAL_STATUSES",
    "ScribeSession",
    "ScribeSessionNotFound",
    "InvalidScribeTransition",
    "ImmutableScribeSession",
    "PatientEncounterMismatch",
    "DRAFT_PREFIX",
    "parse_sections",
    "build_draft_note",
    "create_session",
    "list_sessions_for_patient",
    "get_session",
    "update_session",
    "process_session",
    "review_session",
    "finalize_session",
    "discard_session",
)
