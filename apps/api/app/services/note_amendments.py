"""Phase 49 — clinical governance wave 3: amendment / supersession.

When a signed note needs correction, ChartNav does NOT allow the
signed row to revert to an editable draft. That would break
immutability and make the signed attestation meaningless. Instead,
amendment creates a NEW `note_versions` row:

  - draft_status            = "amended"
  - encounter_id            = same encounter
  - version_number          = max(version_number) + 1
  - note_text               = corrected body
  - amended_from_note_id    = original signed note_versions.id
  - amended_by_user_id      = caller.user_id
  - amended_at              = CURRENT_TIMESTAMP
  - amendment_reason        = free-text reason (required)
  - generated_by            = "manual"
  - provider_review_required = original.provider_review_required
  - missing_data_flags      = []

The original signed row is marked superseded:

  - superseded_at           = CURRENT_TIMESTAMP
  - superseded_by_note_id   = new row id

The amendment row does NOT carry `signed_at` / `signed_by_user_id`
until an authorized signer explicitly signs it through the normal
sign path (which re-runs release gates + re-freezes
content_fingerprint + attestation_text against the amendment's own
text). Until then the amendment is draft-editable only by the
amender + admins.

Export chain: once the amendment itself is signed+exported, both
the superseded original and the amendment remain inspectable. The
`superseded_by_note_id` on the original makes the chain walkable.

Cross-org safety: cross-org amendment is refused at the route layer
via the existing `_load_note_for_caller` pattern. This module
trusts callers to have already run that check.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_one, transaction


class AmendmentError(Exception):
    """Raised for amendment preconditions that violate governance."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _latest_version_for_encounter(encounter_id: int) -> int:
    row = fetch_one(
        "SELECT MAX(version_number) AS vmax FROM note_versions "
        "WHERE encounter_id = :enc",
        {"enc": encounter_id},
    )
    if not row:
        return 0
    v = dict(row).get("vmax")
    return int(v or 0)


def amend_signed_note(
    *,
    original_note: dict[str, Any],
    new_text: str,
    reason: str,
    caller_user_id: int,
) -> dict[str, Any]:
    """Create an amendment row for a signed (or previously amended)
    note. Returns the new amendment row as a dict — the route layer
    serializes + audits.

    Raises AmendmentError when:
      - the original is not in a state that permits amendment
      - the original is already superseded (another amendment exists)
      - the reason is empty / too short
      - the new text is empty
    """
    reason_clean = (reason or "").strip()
    if len(reason_clean) < 4:
        raise AmendmentError(
            "amendment_reason_required",
            "amendment_reason must be a non-empty description (>= 4 chars)",
        )
    if len(reason_clean) > 500:
        raise AmendmentError(
            "amendment_reason_too_long",
            "amendment_reason must be <= 500 characters",
        )
    # Phase 54 — evidentiary hardening. A bare 4-char filler like
    # "asdf", "....", or "1111" passes the length check but is
    # meaningless as a corrective record. Require the reason to
    # contain at least two distinct alphanumeric characters; this
    # catches placeholder strings without blocking legitimate short
    # reasons like "typo" or "fix IOP".
    alnum = [c for c in reason_clean if c.isalnum()]
    if len(alnum) < 4 or len(set(alnum)) < 2:
        raise AmendmentError(
            "amendment_reason_insufficient",
            "amendment_reason must contain a real corrective reason, not "
            "placeholder characters",
        )
    new_text_clean = (new_text or "").strip()
    if len(new_text_clean) < 10:
        raise AmendmentError(
            "amendment_text_empty",
            "amendment note_text must be non-empty (>= 10 chars)",
        )

    status = str(original_note.get("draft_status") or "")
    if status not in {"signed", "exported", "amended"}:
        raise AmendmentError(
            "amendment_source_unsigned",
            f"cannot amend a note in state {status!r}; only signed, "
            f"exported, or previously amended notes may be amended",
        )

    if original_note.get("superseded_at"):
        raise AmendmentError(
            "amendment_source_superseded",
            "this note has already been superseded by a later "
            "amendment; amend the most recent version instead",
        )

    encounter_id = int(original_note["encounter_id"])
    original_id = int(original_note["id"])
    next_version = _latest_version_for_encounter(encounter_id) + 1

    with transaction() as conn:
        new_id_row = conn.execute(
            text(
                "INSERT INTO note_versions ("
                "  encounter_id, version_number, draft_status, note_format, "
                "  note_text, generated_note_text, source_input_id, "
                "  extracted_findings_id, generated_by, "
                "  provider_review_required, missing_data_flags, "
                "  amended_at, amended_by_user_id, amended_from_note_id, "
                "  amendment_reason"
                ") VALUES ("
                "  :enc, :ver, 'amended', :fmt, "
                "  :text, :gen_text, :src_input, "
                "  :src_findings, 'manual', "
                "  :review_req, '[]', "
                "  CURRENT_TIMESTAMP, :by_uid, :from_id, "
                "  :reason"
                ") RETURNING id"
            ),
            {
                "enc": encounter_id,
                "ver": next_version,
                "fmt": original_note.get("note_format") or "freeform",
                "text": new_text_clean,
                "gen_text": original_note.get("generated_note_text"),
                "src_input": original_note.get("source_input_id"),
                "src_findings": original_note.get("extracted_findings_id"),
                "review_req": bool(original_note.get("provider_review_required")),
                "by_uid": caller_user_id,
                "from_id": original_id,
                "reason": reason_clean,
            },
        ).mappings().first()
        new_id = int(new_id_row["id"])

        # Mark the original superseded so the chain is walkable.
        conn.execute(
            text(
                "UPDATE note_versions SET "
                "  superseded_at = CURRENT_TIMESTAMP, "
                "  superseded_by_note_id = :new_id, "
                "  updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id AND superseded_at IS NULL"
            ),
            {"id": original_id, "new_id": new_id},
        )

    return fetch_one(
        "SELECT id, encounter_id, version_number, draft_status, note_format, "
        "note_text, generated_note_text, source_input_id, "
        "extracted_findings_id, generated_by, provider_review_required, "
        "missing_data_flags, signed_at, signed_by_user_id, exported_at, "
        "created_at, updated_at, "
        "reviewed_at, reviewed_by_user_id, content_fingerprint, "
        "attestation_text, amended_at, amended_by_user_id, "
        "amended_from_note_id, amendment_reason, "
        "superseded_at, superseded_by_note_id "
        "FROM note_versions WHERE id = :id",
        {"id": new_id},
    ) or {}


def amendment_chain(note_id: int) -> list[dict[str, Any]]:
    """Walk the amendment chain starting at `note_id`. Returns the
    ordered list oldest → newest. Safe to call on any note (returns
    a single-row list if no amendments exist)."""
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    # Walk backwards to the root.
    root_id = note_id
    while True:
        row = fetch_one(
            "SELECT id, amended_from_note_id FROM note_versions WHERE id = :id",
            {"id": root_id},
        )
        if not row:
            break
        d = dict(row)
        prev = d.get("amended_from_note_id")
        if prev is None:
            break
        if int(prev) in seen:
            break
        seen.add(int(prev))
        root_id = int(prev)
    # Now walk forward via superseded_by_note_id.
    # Phase 54 — include final-approval columns so the chain carries
    # complete evidentiary state for every link, not just the
    # signing metadata. Consumers can tell which link was approved,
    # which was invalidated, and what reason was recorded — without
    # re-querying row-by-row.
    cursor = root_id
    while True:
        row = fetch_one(
            "SELECT id, encounter_id, version_number, draft_status, "
            "signed_at, signed_by_user_id, amended_at, amended_by_user_id, "
            "amended_from_note_id, amendment_reason, "
            "superseded_at, superseded_by_note_id, "
            "content_fingerprint, attestation_text, "
            "final_approval_status, final_approved_at, "
            "final_approved_by_user_id, final_approval_signature_text, "
            "final_approval_invalidated_at, final_approval_invalidated_reason "
            "FROM note_versions WHERE id = :id",
            {"id": cursor},
        )
        if not row:
            break
        d = dict(row)
        out.append(d)
        nxt = d.get("superseded_by_note_id")
        if not nxt or int(nxt) in {c["id"] for c in out}:
            break
        cursor = int(nxt)
    return out


__all__ = [
    "AmendmentError",
    "amend_signed_note",
    "amendment_chain",
]
