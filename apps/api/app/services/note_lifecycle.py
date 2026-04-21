"""Phase 49 — clinical governance wave 3: authoritative note lifecycle.

Single source of truth for:

  - the canonical set of lifecycle states
  - every valid state-to-state transition
  - release blockers (structured, not a single boolean)
  - attestation text frozen at sign time
  - content fingerprinting so silent post-sign mutation is detectable

Routes and the amendment service call into this module; nothing else
should inline a transition check or a blocker check. If a new gate
is required, add it here once.

Storage note: this module NEVER reads or writes DB state directly.
It operates on already-loaded note rows + findings rows. Routes
own the DB lifecycle; this keeps the service trivially unit-testable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------
# Canonical state + transitions
# ---------------------------------------------------------------------

class LifecycleState(str, Enum):
    draft = "draft"
    provider_review = "provider_review"
    reviewed = "reviewed"
    revised = "revised"
    signed = "signed"
    exported = "exported"
    amended = "amended"


LIFECYCLE_STATES: frozenset[str] = frozenset(s.value for s in LifecycleState)


# Forward edges. Every allowed transition lives here. Anything else
# is rejected with a structured error at the service layer.
#
# Shape preserves the pilot flow:
#     draft → provider_review → reviewed → signed → exported
#             │             ↘         ↑
#             revised ←──────┘        │
#             │                       │
#             └──────── signed ───────┘  (provider signs without reviewer)
#
# Amendment is a separate, explicit path that creates a NEW
# note_version row; it is not a state *transition* on an existing
# row and therefore does not appear here.
LIFECYCLE_TRANSITIONS: dict[str, frozenset[str]] = {
    LifecycleState.draft.value: frozenset({
        LifecycleState.provider_review.value,
        LifecycleState.revised.value,
        LifecycleState.signed.value,
    }),
    LifecycleState.provider_review.value: frozenset({
        LifecycleState.draft.value,  # kick back to draft
        LifecycleState.revised.value,
        LifecycleState.reviewed.value,
        LifecycleState.signed.value,
    }),
    LifecycleState.revised.value: frozenset({
        LifecycleState.provider_review.value,
        LifecycleState.reviewed.value,
        LifecycleState.signed.value,
    }),
    LifecycleState.reviewed.value: frozenset({
        LifecycleState.revised.value,  # late correction after review
        LifecycleState.signed.value,
    }),
    LifecycleState.signed.value: frozenset({
        LifecycleState.exported.value,
    }),
    LifecycleState.exported.value: frozenset(),
    LifecycleState.amended.value: frozenset({
        LifecycleState.exported.value,  # an amendment can be exported
    }),
}


# Roles permitted to drive each edge. Edges not present here are
# refused unless the caller is `admin`. Matches the existing sign /
# review guards shipped in previous phases.
EDGE_ROLES: dict[tuple[str, str], frozenset[str]] = {
    ("draft", "provider_review"):        frozenset({"admin", "clinician"}),
    ("draft", "revised"):                frozenset({"admin", "clinician"}),
    ("draft", "signed"):                 frozenset({"admin", "clinician"}),
    ("provider_review", "draft"):        frozenset({"admin", "clinician", "reviewer"}),
    ("provider_review", "revised"):      frozenset({"admin", "clinician"}),
    ("provider_review", "reviewed"):     frozenset({"admin", "reviewer"}),
    ("provider_review", "signed"):       frozenset({"admin", "clinician"}),
    ("revised", "provider_review"):      frozenset({"admin", "clinician"}),
    ("revised", "reviewed"):             frozenset({"admin", "reviewer"}),
    ("revised", "signed"):               frozenset({"admin", "clinician"}),
    ("reviewed", "revised"):             frozenset({"admin", "clinician"}),
    ("reviewed", "signed"):              frozenset({"admin", "clinician"}),
    ("signed", "exported"):              frozenset({"admin", "clinician", "reviewer"}),
    ("amended", "exported"):             frozenset({"admin", "clinician", "reviewer"}),
}


def can_transition(current: str, target: str) -> Optional[str]:
    """Returns None if the transition is allowed; otherwise returns
    a short human reason string the route layer converts to a
    structured 400."""
    if current == target:
        return "target state is identical to current state"
    if current not in LIFECYCLE_STATES:
        return f"current state {current!r} is not a recognised lifecycle state"
    if target not in LIFECYCLE_STATES:
        return f"target state {target!r} is not a recognised lifecycle state"
    allowed = LIFECYCLE_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        if not allowed:
            return f"no transitions are permitted from {current!r}"
        return (
            f"cannot move from {current!r} to {target!r}; "
            f"allowed: {sorted(allowed)}"
        )
    return None


def role_permits_edge(current: str, target: str, role: str) -> bool:
    roles = EDGE_ROLES.get((current, target))
    if roles is None:
        # Edges not explicitly mapped → admin-only.
        return role == "admin"
    return role in roles


# ---------------------------------------------------------------------
# Release blockers
# ---------------------------------------------------------------------

BlockerSeverity = str  # "error" | "warn"


@dataclass(frozen=True)
class ReleaseBlocker:
    code: str
    message: str
    severity: BlockerSeverity = "error"
    field: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.field:
            d["field"] = self.field
        return d


def _missing_flags(note_row: dict[str, Any]) -> list[str]:
    raw = note_row.get("missing_data_flags")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x]
    return []


def _has_text(note_row: dict[str, Any]) -> bool:
    t = note_row.get("note_text")
    if not isinstance(t, str):
        return False
    return len(t.strip()) >= 10  # 10 chars is the minimum that isn't a typo


def compute_release_blockers(
    note_row: dict[str, Any],
    findings_row: Optional[dict[str, Any]] = None,
    *,
    target: str = "signed",
) -> list[ReleaseBlocker]:
    """Return every reason the note cannot reach `target` right now.
    Empty list → the note is clear to release to `target`.

    The resolver is intentionally conservative: when we cannot make
    a confident call we return nothing (so the UI does not invent
    drama). A real clinical-safety review happens at sign via the
    pre-sign checkpoint — this layer is about structural invariants.
    """
    blockers: list[ReleaseBlocker] = []

    if not note_row:
        blockers.append(ReleaseBlocker(
            code="note_missing",
            message="no note version to evaluate",
        ))
        return blockers

    current = str(note_row.get("draft_status") or "")

    # 1. Transition invariants (lifecycle order).
    edge_err = can_transition(current, target)
    if edge_err is not None:
        blockers.append(ReleaseBlocker(
            code="invalid_lifecycle_transition",
            message=edge_err,
        ))

    # 2. Signed notes cannot be re-signed.
    if target == "signed" and current in {"signed", "exported"}:
        blockers.append(ReleaseBlocker(
            code="already_signed",
            message=(
                "note is already signed; issue an amendment instead "
                "of re-signing"
            ),
        ))

    # 3. Export requires sign.
    if target == "exported" and current not in {"signed", "amended"}:
        blockers.append(ReleaseBlocker(
            code="export_requires_sign",
            message="only a signed or amended note can be exported",
        ))

    # 4. Note text must exist.
    if target in {"reviewed", "signed"} and not _has_text(note_row):
        blockers.append(ReleaseBlocker(
            code="note_text_empty",
            message="note_text is empty; write or generate a draft first",
            field="note_text",
        ))

    # 5. Missing-data flags become hard blockers at sign time.
    flags = _missing_flags(note_row)
    if target == "signed" and flags:
        blockers.append(ReleaseBlocker(
            code="missing_data_flags_set",
            message=(
                f"{len(flags)} missing-data flag(s) set; resolve or "
                "acknowledge each before sign"
            ),
            field=",".join(sorted(set(flags))[:8]),
        ))

    # 6. Provider-review-required — a HINT from the generator, not a
    # hard gate. Surfaces as a warn-severity blocker so the UI can
    # nudge without blocking the direct-sign pilot flow.
    if (
        target == "signed"
        and bool(note_row.get("provider_review_required"))
        and current == "draft"
    ):
        blockers.append(ReleaseBlocker(
            code="provider_review_suggested",
            message=(
                "note is flagged as suggesting provider review; consider "
                "routing through provider_review or reviewed before sign"
            ),
            severity="warn",
        ))

    # 7. Low-confidence warn (not a hard blocker; UI renders as 'warn').
    conf = None
    if findings_row is not None:
        conf = (findings_row.get("extraction_confidence") or "").lower()
    if target == "signed" and conf == "low":
        blockers.append(ReleaseBlocker(
            code="extraction_confidence_low",
            message=(
                "extracted findings are low-confidence; review before "
                "signing"
            ),
            severity="warn",
        ))

    # 8. Wave 7 — export gating on final physician approval.
    #
    # A signed row that entered the Wave 7 approval flow carries a
    # `final_approval_status`. Export is blocked until an authorized
    # doctor has performed final approval. Rows with status NULL
    # predate Wave 7 and are not gated here (existing pilot flow is
    # preserved).
    if target == "exported":
        fa_status = note_row.get("final_approval_status")
        if fa_status == "pending":
            blockers.append(ReleaseBlocker(
                code="final_approval_pending",
                message=(
                    "record awaits final physician approval; export is "
                    "blocked until an authorized doctor types their "
                    "name to approve the signed note"
                ),
                field="final_approval_status",
            ))
        elif fa_status == "invalidated":
            blockers.append(ReleaseBlocker(
                code="final_approval_invalidated",
                message=(
                    "prior final approval was invalidated (e.g. by an "
                    "amendment); re-approve the current row of record "
                    "before exporting"
                ),
                field="final_approval_status",
            ))

    return blockers


def hard_blockers(blockers: Iterable[ReleaseBlocker]) -> list[ReleaseBlocker]:
    """Subset that must stop a transition — excludes warnings."""
    return [b for b in blockers if (b.severity or "error") == "error"]


# ---------------------------------------------------------------------
# Attestation + content fingerprint
# ---------------------------------------------------------------------

ATTESTATION_TEMPLATE = (
    "I, {signer_display}, have reviewed this note and attest that it "
    "accurately reflects the services I personally performed for this "
    "patient on {encounter_date}. Signed electronically at {signed_at_iso} "
    "in ChartNav."
)


def default_attestation_text(
    *,
    signer_display: str,
    encounter_date: Optional[str] = None,
    signed_at_iso: Optional[str] = None,
) -> str:
    """Build the attestation sentence that is *frozen* on the
    note_versions row at sign time. The text the signer actually
    attested to is what the record shows forever — we do not re-derive
    it on read because the signer's name / encounter date / timestamp
    could drift.

    Callers fill in `signed_at_iso` at the moment of the DB UPDATE.
    """
    enc = encounter_date or "—"
    ts = signed_at_iso or "—"
    return ATTESTATION_TEMPLATE.format(
        signer_display=signer_display,
        encounter_date=enc,
        signed_at_iso=ts,
    )


def content_fingerprint(note_text: Optional[str]) -> str:
    """Deterministic SHA-256 hex of the normalized note body.

    Trailing / leading whitespace and Windows line endings are
    normalized so a round-trip through a text editor does not
    falsely report drift. Anything else — a single character
    change inside the body — changes the fingerprint.
    """
    src = (note_text or "").replace("\r\n", "\n").strip()
    return hashlib.sha256(src.encode("utf-8")).hexdigest()


def fingerprint_matches(
    note_row: dict[str, Any],
) -> Optional[bool]:
    """Compare the stored `content_fingerprint` to the live
    `note_text`. Returns None when no fingerprint exists (unsigned
    note), True when the row matches its frozen fingerprint, False
    when silent drift has been detected."""
    frozen = note_row.get("content_fingerprint")
    if not frozen:
        return None
    current = content_fingerprint(note_row.get("note_text"))
    return str(frozen) == current


__all__ = [
    "LifecycleState",
    "LIFECYCLE_STATES",
    "LIFECYCLE_TRANSITIONS",
    "EDGE_ROLES",
    "can_transition",
    "role_permits_edge",
    "ReleaseBlocker",
    "compute_release_blockers",
    "hard_blockers",
    "ATTESTATION_TEMPLATE",
    "default_attestation_text",
    "content_fingerprint",
    "fingerprint_matches",
]
