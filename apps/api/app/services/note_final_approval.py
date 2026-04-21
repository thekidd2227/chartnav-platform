"""Phase 52 — clinical approval and record finalization wave 7.

Authoritative final physician approval service. Sits orthogonal to
the lifecycle state machine in `note_lifecycle.py`: a note's
`draft_status` is untouched by final approval — instead a separate
`final_approval_status` column tracks whether an authorized doctor
has typed their exact stored name to approve the already-signed
record.

This module is pure (no DB I/O). Routes own the DB lifecycle and
call into this module to:

  1. confirm a caller is authorized to final-approve
  2. compare a typed signature to the stored name
  3. decide whether final approval is required / missing / present
  4. decide whether downstream actions (export) are blocked
  5. decide how to govern prior approval after an amendment

Keeping the signature comparison here (rather than in-line in the
route) makes the case-sensitive policy unit-testable in isolation,
and keeps every call site honest about the exact comparison rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------
# Canonical final-approval statuses
# ---------------------------------------------------------------------

class FinalApprovalStatus(str, Enum):
    pending = "pending"           # note signed, awaiting authorized doctor
    approved = "approved"         # authorized doctor has typed + matched
    invalidated = "invalidated"   # amendment or governed path invalidated


FINAL_APPROVAL_STATUSES: frozenset[str] = frozenset(
    s.value for s in FinalApprovalStatus
)


# ---------------------------------------------------------------------
# Authorization — who may final-approve
# ---------------------------------------------------------------------

def is_authorized_final_signer(user_row: dict[str, Any]) -> bool:
    """Server-side authorization gate for final approval.

    A coarse role like `clinician` is NOT sufficient. An org must
    explicitly flag a user with `is_authorized_final_signer = true`.
    Admins are NOT automatically authorized — an admin without the
    flag cannot final-approve (admins manage accounts; doctors
    approve records). This avoids accidentally conflating
    account-admin privilege with clinical-approval privilege.

    The only way to get the privilege is via the users row.
    """
    if user_row is None:
        return False
    # User must be active and explicitly flagged.
    if not bool(user_row.get("is_active", True)):
        return False
    return bool(user_row.get("is_authorized_final_signer"))


# ---------------------------------------------------------------------
# Case-sensitive signature comparison
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class SignatureCompareResult:
    matched: bool
    reason: Optional[str]   # short structured reason on mismatch
    expected_empty: bool    # true if the stored name is missing


def compare_typed_signature(
    *,
    typed: Optional[str],
    stored_full_name: Optional[str],
) -> SignatureCompareResult:
    """Compare what the doctor typed against their stored `full_name`.

    Policy:
      - Exact string equality. Case-sensitive. "john smith" does
        not match "John Smith". This is a deliberate choice — the
        act of typing the name correctly is the attestation.
      - Leading/trailing whitespace is trimmed from BOTH sides
        before comparison, because typing via the web form routinely
        introduces a trailing newline on Enter and no one can see
        it. Whitespace *inside* the name is not collapsed: "John  Smith"
        (two spaces) does not match "John Smith" (one space).
      - An empty typed value is always a mismatch.
      - A missing / empty stored name is a hard system error —
        the user row must have a `full_name` before they can
        final-approve. We surface this as `expected_empty=True`.
    """
    stored_clean = (stored_full_name or "").strip()
    typed_clean = (typed or "").strip()

    if not stored_clean:
        return SignatureCompareResult(
            matched=False,
            reason="signer_has_no_stored_name",
            expected_empty=True,
        )

    if not typed_clean:
        return SignatureCompareResult(
            matched=False,
            reason="signature_required",
            expected_empty=False,
        )

    if typed_clean != stored_clean:
        return SignatureCompareResult(
            matched=False,
            reason="signature_mismatch",
            expected_empty=False,
        )

    return SignatureCompareResult(
        matched=True,
        reason=None,
        expected_empty=False,
    )


# ---------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------

def approval_state_on_sign() -> str:
    """The value to stamp into `final_approval_status` when a note
    transitions into `signed`. Always `pending` — we require an
    explicit authorized-doctor approval even if the signer was
    already an authorized doctor. Sign and final-approval are two
    distinct acts."""
    return FinalApprovalStatus.pending.value


def is_approved(note_row: dict[str, Any]) -> bool:
    """True iff the row currently carries an active final approval."""
    return note_row.get("final_approval_status") == FinalApprovalStatus.approved.value


def is_pending(note_row: dict[str, Any]) -> bool:
    return note_row.get("final_approval_status") == FinalApprovalStatus.pending.value


def is_invalidated(note_row: dict[str, Any]) -> bool:
    return (
        note_row.get("final_approval_status")
        == FinalApprovalStatus.invalidated.value
    )


# ---------------------------------------------------------------------
# Final-approval precondition check
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class FinalApprovalPrecondition:
    ok: bool
    reason: Optional[str]   # short structured reason when not ok
    detail: Optional[str]   # human-facing detail for error payload


def can_attempt_final_approval(note_row: dict[str, Any]) -> FinalApprovalPrecondition:
    """Return whether the given note row is in a state where final
    approval can even be attempted. Does NOT check caller authz —
    that is a separate call to `is_authorized_final_signer`.

    Rules:
      - Note must exist.
      - Note must be in `signed` or `amended` lifecycle state
        (export is also acceptable; an exported-but-unapproved row
        from legacy should still be approvable).
      - Note must not be superseded (its amendment is the new
        row of record).
      - Note's current `final_approval_status` must be NULL,
        'pending', or 'invalidated'. 'approved' is a no-op idempotency
        guard — the route returns 200 with the existing row.
    """
    if not note_row:
        return FinalApprovalPrecondition(
            ok=False,
            reason="note_missing",
            detail="no note version to approve",
        )

    status = str(note_row.get("draft_status") or "")
    if status not in {"signed", "exported", "amended"}:
        return FinalApprovalPrecondition(
            ok=False,
            reason="not_signable_state",
            detail=(
                "final approval requires a signed, exported, or amended note; "
                f"current state is {status!r}"
            ),
        )

    if note_row.get("superseded_at"):
        return FinalApprovalPrecondition(
            ok=False,
            reason="note_superseded",
            detail=(
                "this note has been superseded by an amendment; approve "
                "the amendment row instead"
            ),
        )

    current_approval = note_row.get("final_approval_status")
    if current_approval == FinalApprovalStatus.approved.value:
        return FinalApprovalPrecondition(
            ok=False,
            reason="already_approved",
            detail="note is already final-approved; re-approval is a no-op",
        )

    return FinalApprovalPrecondition(ok=True, reason=None, detail=None)


# ---------------------------------------------------------------------
# Export gating
# ---------------------------------------------------------------------

def export_requires_final_approval(note_row: dict[str, Any]) -> bool:
    """Decide whether this note's export must wait for final approval.

    Policy for Wave 7:
      - If `final_approval_status` is NULL → row predates Wave 7
        or the org is not using final approval. Do NOT block export.
        Existing pilot flow is preserved.
      - If status is 'pending' → block export. The whole point of
        Wave 7 is that release leaves a doctor fingerprint.
      - If status is 'approved' → allow export.
      - If status is 'invalidated' → block export. An amendment
        has invalidated the prior approval; either approve the
        amendment or re-approve this row through the governed path.
    """
    status = note_row.get("final_approval_status")
    if status is None:
        return False
    return status != FinalApprovalStatus.approved.value


# ---------------------------------------------------------------------
# Invalidation on amendment
# ---------------------------------------------------------------------

INVALIDATION_REASON_AMENDED = (
    "Superseded by amendment; prior final approval no longer applies to "
    "the record of care."
)


def invalidation_reason_for_amendment() -> str:
    """Canonical reason string stamped on an invalidated approval
    when the cause is an amendment. Kept centralized so every
    invalidation path writes the identical string."""
    return INVALIDATION_REASON_AMENDED


__all__ = [
    "FinalApprovalStatus",
    "FINAL_APPROVAL_STATUSES",
    "is_authorized_final_signer",
    "SignatureCompareResult",
    "compare_typed_signature",
    "approval_state_on_sign",
    "is_approved",
    "is_pending",
    "is_invalidated",
    "FinalApprovalPrecondition",
    "can_attempt_final_approval",
    "export_requires_final_approval",
    "INVALIDATION_REASON_AMENDED",
    "invalidation_reason_for_amendment",
]
