"""Phase 55 — immutable audit and external evidence hardening.

A hash-chained evidence log that sits alongside the general
`security_audit_events` table. Records only the governance
transitions that must be forensically reconstructible:

  - note_signed
  - note_final_approved
  - note_exported
  - note_amended_source             (original row at amendment time)
  - note_amended_new                (new amendment row)
  - note_final_approval_invalidated (programmatic invalidation event
                                     — separately recorded because
                                     the row-level invalidation
                                     fields can be overwritten)

Each row is hash-chained to the previous row in the same org. The
hash is SHA-256 over a canonical serialization of the row's fields
plus the previous row's hash. Tampering with any row's canonical
fields breaks the chain from that row forward; re-running
`verify_chain(organization_id)` detects the break and reports the
first broken row.

Chain semantics:

  * First event in an org → prev_event_hash = NULL, event_hash
    computed over NULL + row content.
  * Every subsequent event → prev_event_hash = last row's event_hash,
    event_hash computed over prev_event_hash + row content.
  * Verification walks the chain in id order and recomputes each
    event_hash, comparing against the stored value.

This module owns both writes (append) and reads (verify + bundle).
Routes call `record_evidence_event(...)` after each governance
transition; they do NOT construct evidence rows directly.

Tamper-evident, not tamper-proof: a sophisticated attacker with DB
write access can rewrite the entire chain. The value is that any
partial tamper (single-row edit / insert / delete without chain
re-hash) is detectable, and the chain is cheap to verify offline.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_all, fetch_one, transaction


# ---------------------------------------------------------------------
# Canonical event-type taxonomy
# ---------------------------------------------------------------------

class EvidenceEventType(str, Enum):
    note_signed = "note_signed"
    note_final_approved = "note_final_approved"
    note_exported = "note_exported"
    note_amended_source = "note_amended_source"
    note_amended_new = "note_amended_new"
    note_final_approval_invalidated = "note_final_approval_invalidated"


EVIDENCE_EVENT_TYPES: frozenset[str] = frozenset(
    t.value for t in EvidenceEventType
)


# ---------------------------------------------------------------------
# Hash construction
# ---------------------------------------------------------------------

def _canonical_row_payload(
    *,
    organization_id: int,
    note_version_id: int,
    encounter_id: int,
    event_type: str,
    actor_user_id: Optional[int],
    actor_email: Optional[str],
    occurred_at_iso: str,
    draft_status: Optional[str],
    final_approval_status: Optional[str],
    content_fingerprint: Optional[str],
    detail_json: Optional[str],
    prev_event_hash: Optional[str],
) -> str:
    """Deterministic canonical serialization used as the hash input.

    Using JSON with sorted keys so equal semantic content produces
    equal hashes regardless of field order. `None` values are
    serialized as JSON null. The final newline is intentional so
    binary-level diffs never collapse trailing whitespace.
    """
    payload = {
        "organization_id": int(organization_id),
        "note_version_id": int(note_version_id),
        "encounter_id": int(encounter_id),
        "event_type": str(event_type),
        "actor_user_id": int(actor_user_id) if actor_user_id is not None else None,
        "actor_email": actor_email,
        "occurred_at": occurred_at_iso,
        "draft_status": draft_status,
        "final_approval_status": final_approval_status,
        "content_fingerprint": content_fingerprint,
        "detail_json": detail_json,
        "prev_event_hash": prev_event_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def _compute_event_hash(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# Append path
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceWriteResult:
    id: int
    event_hash: str
    prev_event_hash: Optional[str]


def record_evidence_event(
    *,
    organization_id: int,
    note_version_id: int,
    encounter_id: int,
    event_type: str,
    actor_user_id: Optional[int],
    actor_email: Optional[str],
    draft_status: Optional[str],
    final_approval_status: Optional[str],
    content_fingerprint: Optional[str],
    detail: Optional[dict[str, Any]] = None,
    dispatch_to_sink: bool = True,
) -> EvidenceWriteResult:
    """Append a new evidence event, linked to the org's previous
    event. Returns the new row's id + its hash.

    Callers are expected to pass `event_type` from the enum above.
    Invalid event types raise — this module is the canonical gate.

    The write is transactional: previous-hash lookup + INSERT happen
    in the same transaction to keep the chain consistent under
    concurrent writes. SQLite serializes writes anyway; Postgres
    would need SERIALIZABLE isolation for strict correctness, but
    the chain is re-verifiable after the fact, so a race that
    produces two rows with the same prev_event_hash is detectable
    offline.
    """
    if event_type not in EVIDENCE_EVENT_TYPES:
        raise ValueError(
            f"invalid evidence event_type {event_type!r}; "
            f"expected one of {sorted(EVIDENCE_EVENT_TYPES)}"
        )

    occurred_at = datetime.now(timezone.utc)
    occurred_at_iso = occurred_at.isoformat()
    detail_json = (
        json.dumps(detail, sort_keys=True, ensure_ascii=False)
        if detail is not None
        else None
    )

    with transaction() as conn:
        prev_row = conn.execute(
            text(
                "SELECT event_hash FROM note_evidence_events "
                "WHERE organization_id = :org "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"org": organization_id},
        ).mappings().first()
        prev_event_hash = prev_row["event_hash"] if prev_row else None

        canonical = _canonical_row_payload(
            organization_id=organization_id,
            note_version_id=note_version_id,
            encounter_id=encounter_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            occurred_at_iso=occurred_at_iso,
            draft_status=draft_status,
            final_approval_status=final_approval_status,
            content_fingerprint=content_fingerprint,
            detail_json=detail_json,
            prev_event_hash=prev_event_hash,
        )
        event_hash = _compute_event_hash(canonical)

        new_row = conn.execute(
            text(
                "INSERT INTO note_evidence_events ("
                "  organization_id, note_version_id, encounter_id, "
                "  event_type, actor_user_id, actor_email, occurred_at, "
                "  draft_status, final_approval_status, content_fingerprint, "
                "  detail_json, prev_event_hash, event_hash"
                ") VALUES ("
                "  :org, :nvid, :enc, :et, :uid, :email, :occ, "
                "  :ds, :fas, :fp, :det, :prev, :hash"
                ") RETURNING id"
            ),
            {
                "org": organization_id,
                "nvid": note_version_id,
                "enc": encounter_id,
                "et": event_type,
                "uid": actor_user_id,
                "email": actor_email,
                "occ": occurred_at_iso,
                "ds": draft_status,
                "fas": final_approval_status,
                "fp": content_fingerprint,
                "det": detail_json,
                "prev": prev_event_hash,
                "hash": event_hash,
            },
        ).mappings().first()

    result = EvidenceWriteResult(
        id=int(new_row["id"]),
        event_hash=event_hash,
        prev_event_hash=prev_event_hash,
    )

    # Phase 56 — attempt external sink delivery AFTER the chain write
    # has committed. The chain is authoritative; the sink is
    # best-effort and the per-event sink_status column tracks the
    # outcome. Callers that want to batch deliveries (e.g. a test
    # that writes many events) can pass dispatch_to_sink=False.
    if dispatch_to_sink:
        try:
            from app.services.evidence_sink import (
                dispatch_event,
                update_sink_status,
            )
            row_for_sink = {
                "id": result.id,
                "organization_id": organization_id,
                "note_version_id": note_version_id,
                "encounter_id": encounter_id,
                "event_type": event_type,
                "actor_user_id": actor_user_id,
                "actor_email": actor_email,
                "occurred_at": occurred_at_iso,
                "draft_status": draft_status,
                "final_approval_status": final_approval_status,
                "content_fingerprint": content_fingerprint,
                "detail_json": detail_json,
                "prev_event_hash": prev_event_hash,
                "event_hash": event_hash,
            }
            dr = dispatch_event(
                organization_id=organization_id,
                event_row=row_for_sink,
            )
            update_sink_status(evidence_event_id=result.id, result=dr)
        except Exception:  # pragma: no cover
            import logging as _lg
            _lg.getLogger("chartnav.evidence_sink").warning(
                "evidence_sink_dispatch_unexpected_error", exc_info=True
            )

    return result


# ---------------------------------------------------------------------
# Read paths
# ---------------------------------------------------------------------

def list_events_for_note(
    note_version_id: int,
) -> list[dict[str, Any]]:
    """Return every evidence event touching this note, oldest first."""
    return fetch_all(
        "SELECT id, organization_id, note_version_id, encounter_id, "
        "event_type, actor_user_id, actor_email, occurred_at, "
        "draft_status, final_approval_status, content_fingerprint, "
        "detail_json, prev_event_hash, event_hash "
        "FROM note_evidence_events "
        "WHERE note_version_id = :nvid "
        "ORDER BY id ASC",
        {"nvid": int(note_version_id)},
    )


def list_events_for_org(
    organization_id: int,
    *,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Return the org's evidence chain, oldest first. Capped for
    defensive paging; callers that need the full chain should stream
    via id > cursor."""
    return fetch_all(
        "SELECT id, organization_id, note_version_id, encounter_id, "
        "event_type, actor_user_id, actor_email, occurred_at, "
        "draft_status, final_approval_status, content_fingerprint, "
        "detail_json, prev_event_hash, event_hash "
        "FROM note_evidence_events "
        "WHERE organization_id = :org "
        "ORDER BY id ASC LIMIT :lim",
        {"org": int(organization_id), "lim": int(limit)},
    )


# ---------------------------------------------------------------------
# Chain verification
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ChainVerification:
    organization_id: int
    total_events: int
    verified_events: int
    broken_at_event_id: Optional[int]
    broken_reason: Optional[str]
    first_event_hash: Optional[str]
    last_event_hash: Optional[str]

    @property
    def ok(self) -> bool:
        """True when no break was detected. Mirrors the `ok` key in
        `as_dict()` so callers that hold the dataclass directly don't
        have to serialize first."""
        return self.broken_at_event_id is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "total_events": self.total_events,
            "verified_events": self.verified_events,
            "broken_at_event_id": self.broken_at_event_id,
            "broken_reason": self.broken_reason,
            "first_event_hash": self.first_event_hash,
            "last_event_hash": self.last_event_hash,
            "ok": self.ok,
        }


def _row_to_canonical(row: dict[str, Any]) -> str:
    # occurred_at may come back as a datetime from sqlite or str from
    # Postgres. Normalize to ISO.
    occ = row.get("occurred_at")
    if isinstance(occ, datetime):
        occ_iso = occ.isoformat()
    else:
        occ_iso = str(occ) if occ is not None else ""
    return _canonical_row_payload(
        organization_id=int(row["organization_id"]),
        note_version_id=int(row["note_version_id"]),
        encounter_id=int(row["encounter_id"]),
        event_type=str(row["event_type"]),
        actor_user_id=row.get("actor_user_id"),
        actor_email=row.get("actor_email"),
        occurred_at_iso=occ_iso,
        draft_status=row.get("draft_status"),
        final_approval_status=row.get("final_approval_status"),
        content_fingerprint=row.get("content_fingerprint"),
        detail_json=row.get("detail_json"),
        prev_event_hash=row.get("prev_event_hash"),
    )


def verify_chain(organization_id: int) -> ChainVerification:
    """Walk this org's evidence chain in id order and recompute every
    event_hash. Returns a structured verification result; does NOT
    raise. Callers (admin UI, ops plane) render the result.

    Verification details:
      - row[0].prev_event_hash must be NULL
      - row[i].prev_event_hash == row[i-1].event_hash  for i >= 1
      - recomputed_hash(row[i]) == row[i].event_hash   for every i
    """
    rows = list_events_for_org(organization_id, limit=1_000_000)
    if not rows:
        return ChainVerification(
            organization_id=organization_id,
            total_events=0,
            verified_events=0,
            broken_at_event_id=None,
            broken_reason=None,
            first_event_hash=None,
            last_event_hash=None,
        )

    verified = 0
    first_hash = rows[0]["event_hash"]
    last_hash = rows[-1]["event_hash"]
    for i, row in enumerate(rows):
        # (a) prev-link check.
        expected_prev = None if i == 0 else rows[i - 1]["event_hash"]
        if row.get("prev_event_hash") != expected_prev:
            return ChainVerification(
                organization_id=organization_id,
                total_events=len(rows),
                verified_events=verified,
                broken_at_event_id=int(row["id"]),
                broken_reason="prev_event_hash_mismatch",
                first_event_hash=first_hash,
                last_event_hash=last_hash,
            )
        # (b) content-hash recomputation.
        canonical = _row_to_canonical(row)
        expected_hash = _compute_event_hash(canonical)
        if expected_hash != row["event_hash"]:
            return ChainVerification(
                organization_id=organization_id,
                total_events=len(rows),
                verified_events=verified,
                broken_at_event_id=int(row["id"]),
                broken_reason="event_hash_mismatch",
                first_event_hash=first_hash,
                last_event_hash=last_hash,
            )
        verified += 1

    return ChainVerification(
        organization_id=organization_id,
        total_events=len(rows),
        verified_events=verified,
        broken_at_event_id=None,
        broken_reason=None,
        first_event_hash=first_hash,
        last_event_hash=last_hash,
    )


# ---------------------------------------------------------------------
# Per-note evidence health
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class NoteEvidenceHealth:
    note_version_id: int
    has_signed_event: bool
    has_final_approval_event: bool
    has_export_event: bool
    has_invalidated_approval_event: bool
    content_fingerprint_present: bool
    fingerprint_matches_current: Optional[bool]
    event_count: int
    last_event_hash: Optional[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "note_version_id": self.note_version_id,
            "has_signed_event": self.has_signed_event,
            "has_final_approval_event": self.has_final_approval_event,
            "has_export_event": self.has_export_event,
            "has_invalidated_approval_event": self.has_invalidated_approval_event,
            "content_fingerprint_present": self.content_fingerprint_present,
            "fingerprint_matches_current": self.fingerprint_matches_current,
            "event_count": self.event_count,
            "last_event_hash": self.last_event_hash,
        }


def note_evidence_health(
    note_row: dict[str, Any],
) -> NoteEvidenceHealth:
    """Cheap per-note evidence health card. Consumed by the
    /admin/operations/notes/{id}/evidence-health endpoint and by the
    lifecycle panel."""
    from app.services.note_lifecycle import fingerprint_matches

    events = list_events_for_note(int(note_row["id"]))
    types_seen = {ev["event_type"] for ev in events}
    fp = note_row.get("content_fingerprint")
    return NoteEvidenceHealth(
        note_version_id=int(note_row["id"]),
        has_signed_event=EvidenceEventType.note_signed.value in types_seen,
        has_final_approval_event=(
            EvidenceEventType.note_final_approved.value in types_seen
        ),
        has_export_event=EvidenceEventType.note_exported.value in types_seen,
        has_invalidated_approval_event=(
            EvidenceEventType.note_final_approval_invalidated.value in types_seen
        ),
        content_fingerprint_present=bool(fp),
        fingerprint_matches_current=fingerprint_matches(note_row),
        event_count=len(events),
        last_event_hash=events[-1]["event_hash"] if events else None,
    )


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


# ---------------------------------------------------------------------
# Forensic evidence bundle
# ---------------------------------------------------------------------

BUNDLE_VERSION = "chartnav.evidence.v1"


# ---------------------------------------------------------------------
# Phase 56 — HMAC signing
# ---------------------------------------------------------------------

class EvidenceSigningError(Exception):
    """Raised when signing is required but the environment can not
    produce a signature (e.g. signing key missing)."""
    def __init__(self, error_code: str, reason: str):
        super().__init__(reason)
        self.error_code = error_code
        self.reason = reason


def _compute_hmac_signature(
    body_hash: str,
    hmac_key: str,
) -> str:
    """HMAC-SHA256 over the bundle body hash. We sign the body hash
    rather than the raw body so signature verification is cheap and
    independent of JSON serialization quirks — the body hash itself
    is the canonical anchor."""
    import hmac as _hmac
    return _hmac.new(
        hmac_key.encode("utf-8"),
        body_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _resolve_keyring() -> dict[str, str]:
    """Return the merged keyring from process config: the Phase-57
    JSON ring plus the legacy single-key env under `default`.
    Pure lookup; returns {} when no signing material is configured.
    """
    from app.config import settings
    ring = dict(getattr(settings, "evidence_signing_hmac_keyring", {}) or {})
    legacy = getattr(settings, "evidence_signing_hmac_key", None)
    if legacy and "default" not in ring:
        ring["default"] = legacy
    return ring


def _resolve_signing(organization_id: int) -> dict[str, Any]:
    """Return signing parameters for the org, or a disabled marker.

    Phase 57 — keyring-aware. The org's `evidence_signing_key_id`
    names the ACTIVE key within the process-wide keyring. If the
    named key is absent the bundle route returns 503 with a precise
    reason so the operator sees "the signing configuration is
    inconsistent" rather than a silent downgrade.

    Rules:
      - mode=disabled → {mode: "disabled"}.
      - mode=hmac_sha256 but keyring empty → 503
        `evidence_signing_unconfigured`.
      - mode=hmac_sha256 + key_id missing in ring → 503
        `evidence_signing_key_unknown`.
      - mode=hmac_sha256 + key_id="" → fall back to "default" (the
        legacy alias) so pre-rotation deploys keep working.
    """
    from app.security_policy import resolve_security_policy

    policy = resolve_security_policy(organization_id)
    mode = (policy.evidence_signing_mode or "disabled").lower()

    if mode == "disabled":
        return {"mode": "disabled", "key_id": None}

    if mode != "hmac_sha256":
        # Unknown mode → treat as disabled. Policy writer already
        # rejects unknown modes so this branch only fires on legacy
        # rows.
        return {"mode": "disabled", "key_id": None}

    ring = _resolve_keyring()
    if not ring:
        raise EvidenceSigningError(
            "evidence_signing_unconfigured",
            "evidence_signing_mode is hmac_sha256 but no HMAC keys "
            "are configured (set CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS "
            "or the legacy CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY)",
        )

    active_kid = (policy.evidence_signing_key_id or "default").strip() or "default"
    if active_kid not in ring:
        raise EvidenceSigningError(
            "evidence_signing_key_unknown",
            f"evidence_signing_key_id {active_kid!r} is not present "
            f"in the keyring; available: {sorted(ring.keys())}",
        )

    return {
        "mode": "hmac_sha256",
        "key_id": active_kid,
        "hmac_key": ring[active_kid],
    }


def verify_signature(bundle: dict[str, Any]) -> dict[str, Any]:
    """Re-compute the HMAC over the bundle's body_hash using the
    keyring entry the bundle *names* (not whatever the active key
    is right now). Returns a structured verdict.

    Phase 57 — this function is now key-id-aware. The bundle's
    `signature.key_id` picks the correct entry from the process
    keyring; old bundles remain verifiable after a rotation as
    long as the old key is still present in the ring.

    Stateless with respect to the DB; pure config lookup.
    """
    signature_block = bundle.get("signature") or {}
    mode = signature_block.get("mode")
    if not mode or mode == "disabled":
        return {
            "mode": mode or "disabled",
            "ok": False,
            "error_code": "unsigned_bundle",
            "reason": "bundle carries no signature",
        }
    if mode != "hmac_sha256":
        return {
            "mode": mode,
            "ok": False,
            "error_code": "unknown_signing_mode",
            "reason": f"unrecognised signing mode {mode!r}",
        }

    claimed_hash = (bundle.get("envelope") or {}).get("body_hash_sha256")
    claimed_sig = signature_block.get("signature_hex")
    claimed_key_id = (signature_block.get("key_id") or "default").strip() or "default"
    if not claimed_hash or not claimed_sig:
        return {
            "mode": mode,
            "key_id": claimed_key_id,
            "ok": False,
            "error_code": "malformed_signature",
            "reason": "bundle missing body_hash or signature_hex",
        }

    ring = _resolve_keyring()
    if not ring:
        return {
            "mode": mode,
            "key_id": claimed_key_id,
            "ok": False,
            "error_code": "evidence_signing_unconfigured",
            "reason": (
                "no HMAC keys configured on this host; cannot verify"
            ),
        }

    secret = ring.get(claimed_key_id)
    if secret is None:
        # Phase 57 — precise "key rotated out" signal. The bundle
        # was signed by a key that is no longer in the ring; either
        # the operator purged it prematurely or the bundle was
        # issued by a different deploy. Either way the operator
        # needs to know which key_id was expected.
        return {
            "mode": mode,
            "key_id": claimed_key_id,
            "ok": False,
            "error_code": "signing_key_not_in_keyring",
            "reason": (
                f"signing key_id {claimed_key_id!r} is not in this host's "
                f"keyring; available: {sorted(ring.keys())}"
            ),
        }

    expected = _compute_hmac_signature(claimed_hash, secret)
    import hmac as _hmac
    ok = _hmac.compare_digest(expected, claimed_sig)
    return {
        "mode": mode,
        "key_id": claimed_key_id,
        "ok": bool(ok),
        "error_code": None if ok else "signature_mismatch",
        "reason": None if ok else (
            "HMAC did not match — bundle has been tampered with or "
            "the keyring entry for this key_id has changed"
        ),
    }


def build_evidence_bundle(
    *,
    note_row: dict[str, Any],
    encounter_row: dict[str, Any],
    signer_row: Optional[dict[str, Any]],
    final_approver_row: Optional[dict[str, Any]],
    caller_email: Optional[str],
    caller_user_id: Optional[int],
) -> dict[str, Any]:
    """Assemble the forensic evidence bundle for a single note.

    Unlike the per-format artifact (JSON / text / FHIR), the evidence
    bundle is ONE structured JSON document designed for support,
    enterprise review, and dispute reconstruction. It includes:

      - note identity + canonical lifecycle state
      - final-approval metadata (verbatim signature, approver id)
      - content fingerprint (frozen + live comparison)
      - the full supersession / amendment chain
      - the org's evidence-chain events that touch this note
      - a chain-integrity verdict for the org's chain up through
        the newest event for this note
      - envelope metadata: issuance time, issuer, hash over the
        canonical payload

    The bundle is deterministic given the same row state: a re-issue
    produces the same content-hash (modulo issued_at/issued_by). The
    envelope_hash at the bottom is the SHA-256 over the canonical
    body section EXCLUDING envelope.* fields, so consumers can
    re-verify the body independently of when it was issued.
    """
    from app.services.note_amendments import amendment_chain
    from app.services.note_lifecycle import fingerprint_matches

    note_id = int(note_row["id"])
    organization_id = int(encounter_row["organization_id"])

    chain = amendment_chain(note_id)
    current_tail = next(
        (link["id"] for link in chain if link.get("superseded_at") is None),
        None,
    )
    has_invalidated = any(
        link.get("final_approval_status") == "invalidated" for link in chain
    )

    events = list_events_for_note(note_id)
    # Verify the whole org chain; include a per-bundle verdict.
    chain_verdict = verify_chain(organization_id)
    health = note_evidence_health(note_row)

    body: dict[str, Any] = {
        "bundle_version": BUNDLE_VERSION,
        "note": {
            "id": note_id,
            "encounter_id": int(note_row["encounter_id"]),
            "version_number": int(note_row["version_number"]),
            "note_format": note_row.get("note_format"),
            "draft_status": note_row.get("draft_status"),
            "content_fingerprint": note_row.get("content_fingerprint"),
            "fingerprint_matches_current": fingerprint_matches(note_row),
            "attestation_text": note_row.get("attestation_text"),
            "signed_at": _iso(note_row.get("signed_at")),
            "signed_by_user_id": note_row.get("signed_by_user_id"),
            "signed_by_email": (
                signer_row.get("email") if signer_row else None
            ),
            "exported_at": _iso(note_row.get("exported_at")),
            "reviewed_at": _iso(note_row.get("reviewed_at")),
            "reviewed_by_user_id": note_row.get("reviewed_by_user_id"),
        },
        "encounter": {
            "id": int(encounter_row["id"]),
            "organization_id": organization_id,
            "patient_display": (
                encounter_row.get("patient_name")
                or encounter_row.get("patient_identifier")
            ),
            "provider_display": encounter_row.get("provider_name"),
            "external_ref": encounter_row.get("external_ref"),
            "external_source": encounter_row.get("external_source"),
        },
        "final_approval": {
            "status": note_row.get("final_approval_status"),
            "approved_at": _iso(note_row.get("final_approved_at")),
            "approved_by_user_id": note_row.get("final_approved_by_user_id"),
            "approved_by_email": (
                final_approver_row.get("email") if final_approver_row else None
            ),
            "signature_text": note_row.get("final_approval_signature_text"),
            "invalidated_at": _iso(note_row.get("final_approval_invalidated_at")),
            "invalidated_reason": note_row.get("final_approval_invalidated_reason"),
        },
        "supersession": {
            "amended_from_note_id": note_row.get("amended_from_note_id"),
            "amended_at": _iso(note_row.get("amended_at")),
            "amended_by_user_id": note_row.get("amended_by_user_id"),
            "amendment_reason": note_row.get("amendment_reason"),
            "superseded_at": _iso(note_row.get("superseded_at")),
            "superseded_by_note_id": note_row.get("superseded_by_note_id"),
            "is_current_record_of_care": note_row.get("superseded_at") is None,
            "chain_length": len(chain),
            "current_record_of_care_note_id": current_tail,
            "has_invalidated_approval": has_invalidated,
            "chain": [
                {
                    "id": int(link["id"]),
                    "version_number": int(link["version_number"]),
                    "draft_status": link.get("draft_status"),
                    "signed_at": _iso(link.get("signed_at")),
                    "signed_by_user_id": link.get("signed_by_user_id"),
                    "amended_from_note_id": link.get("amended_from_note_id"),
                    "amendment_reason": link.get("amendment_reason"),
                    "superseded_at": _iso(link.get("superseded_at")),
                    "superseded_by_note_id": link.get("superseded_by_note_id"),
                    "content_fingerprint": link.get("content_fingerprint"),
                    "final_approval_status": link.get("final_approval_status"),
                    "final_approved_at": _iso(link.get("final_approved_at")),
                    "final_approved_by_user_id": link.get("final_approved_by_user_id"),
                    "final_approval_signature_text": link.get(
                        "final_approval_signature_text"
                    ),
                    "final_approval_invalidated_at": _iso(
                        link.get("final_approval_invalidated_at")
                    ),
                    "final_approval_invalidated_reason": link.get(
                        "final_approval_invalidated_reason"
                    ),
                }
                for link in chain
            ],
        },
        "evidence_events": [
            {
                "id": int(ev["id"]),
                "event_type": ev["event_type"],
                "actor_user_id": ev.get("actor_user_id"),
                "actor_email": ev.get("actor_email"),
                "occurred_at": _iso(ev.get("occurred_at")),
                "draft_status": ev.get("draft_status"),
                "final_approval_status": ev.get("final_approval_status"),
                "content_fingerprint": ev.get("content_fingerprint"),
                "detail_json": ev.get("detail_json"),
                "prev_event_hash": ev.get("prev_event_hash"),
                "event_hash": ev.get("event_hash"),
            }
            for ev in events
        ],
        "evidence_health": health.as_dict(),
        "chain_integrity": chain_verdict.as_dict(),
    }

    # Envelope hash: SHA-256 over the canonical body (sorted keys,
    # compact JSON). Independent of issued_at / issued_by so a
    # re-issued bundle for the same row produces the same body_hash.
    canonical_body = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    body_hash = hashlib.sha256(canonical_body.encode("utf-8")).hexdigest()

    body["envelope"] = {
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "issued_by_email": caller_email,
        "issued_by_user_id": caller_user_id,
        "body_hash_sha256": body_hash,
        "hash_inputs": "json(body,sort_keys,compact,utf8)",
    }

    # Phase 56 — optional HMAC signing. When the org has enabled
    # evidence signing and the process HMAC key is set, attach a
    # signature block. When enabled-but-key-missing, raise
    # EvidenceSigningError — the route layer maps this to 503 so the
    # operator sees a clear misconfiguration signal instead of a
    # silently-unsigned bundle.
    signing = _resolve_signing(int(encounter_row["organization_id"]))
    if signing["mode"] == "hmac_sha256":
        sig_hex = _compute_hmac_signature(body_hash, signing["hmac_key"])
        body["signature"] = {
            "mode": "hmac_sha256",
            "key_id": signing["key_id"],
            "signature_inputs": "envelope.body_hash_sha256",
            "signature_hex": sig_hex,
        }
    else:
        body["signature"] = {
            "mode": "disabled",
            "key_id": None,
            "signature_inputs": None,
            "signature_hex": None,
        }

    return body


def keyring_posture(organization_id: int) -> dict[str, Any]:
    """Safe admin view of the signing posture.

    NEVER exposes secret material — only key_ids. Consumers:
    operations overview + a dedicated /admin/operations/signing-posture
    endpoint. The admin can see which keys are loaded, which is the
    active signer for the org, and whether rotation is in a
    consistent state (active key present in ring).
    """
    from app.security_policy import resolve_security_policy

    policy = resolve_security_policy(organization_id)
    mode = (policy.evidence_signing_mode or "disabled").lower()
    active_kid = (policy.evidence_signing_key_id or "").strip() or "default"
    ring = _resolve_keyring()
    ring_ids = sorted(ring.keys())
    active_present = active_kid in ring

    # Inconsistent := org wants signing but the keyring is empty, OR
    # the active key is named but not in the ring.
    inconsistent = (mode == "hmac_sha256") and (
        not ring or not active_present
    )
    return {
        "mode": mode,
        "active_key_id": active_kid if mode == "hmac_sha256" else None,
        "active_key_present": active_present if mode == "hmac_sha256" else None,
        "keyring_key_ids": ring_ids,
        "keyring_size": len(ring_ids),
        "inconsistent": inconsistent,
    }


# ---------------------------------------------------------------------
# Phase 57 — signed chain seals
# ---------------------------------------------------------------------

def _canonical_seal_payload(
    *,
    organization_id: int,
    tip_event_id: int,
    tip_event_hash: str,
    event_count: int,
    sealed_at_iso: str,
    sealed_by_user_id: Optional[int],
    sealed_by_email: Optional[str],
    note: Optional[str],
) -> str:
    payload = {
        "organization_id": int(organization_id),
        "tip_event_id": int(tip_event_id),
        "tip_event_hash": tip_event_hash,
        "event_count": int(event_count),
        "sealed_at": sealed_at_iso,
        "sealed_by_user_id": (
            int(sealed_by_user_id) if sealed_by_user_id is not None else None
        ),
        "sealed_by_email": sealed_by_email,
        "note": note,
    }
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ) + "\n"


def compute_seal_hash(
    *,
    organization_id: int,
    tip_event_id: int,
    tip_event_hash: str,
    event_count: int,
    sealed_at_iso: str,
    sealed_by_user_id: Optional[int],
    sealed_by_email: Optional[str],
    note: Optional[str],
) -> str:
    """Public: the canonical SHA-256 over a seal's content. Used at
    write time to stamp `seal_hash_sha256` and at verify time to
    recompute and compare."""
    canonical = _canonical_seal_payload(
        organization_id=organization_id,
        tip_event_id=tip_event_id,
        tip_event_hash=tip_event_hash,
        event_count=event_count,
        sealed_at_iso=sealed_at_iso,
        sealed_by_user_id=sealed_by_user_id,
        sealed_by_email=sealed_by_email,
        note=note,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign_seal_hash(seal_hash: str, organization_id: int) -> Optional[dict[str, Any]]:
    """Optionally produce an HMAC signature over a seal_hash using
    the org's active signing key. Returns None when the org has
    signing disabled. Raises EvidenceSigningError when signing is
    required but inconsistent — the route maps to 503 so the
    operator sees a precise reason instead of a silently-unsigned
    seal."""
    signing = _resolve_signing(organization_id)
    if signing["mode"] != "hmac_sha256":
        return None
    sig_hex = _compute_hmac_signature(seal_hash, signing["hmac_key"])
    return {
        "signature_hex": sig_hex,
        "signing_key_id": signing["key_id"],
    }


def verify_seal_row(row: dict[str, Any]) -> dict[str, Any]:
    """Verify a stored chain-seal row.

    Two checks:
      (a) recompute seal_hash_sha256 over the row's canonical
          content and compare to the stored value. Any mismatch
          means someone mutated the seal after it was written.
      (b) if the row carries a signature, re-verify it against the
          keyring entry named in `seal_signing_key_id`.

    Returns a structured verdict; pre-Phase-57 seals (with
    seal_hash_sha256 NULL) are reported as `legacy` — operator-
    visible, not silently "ok".
    """
    stored_hash = row.get("seal_hash_sha256")
    if stored_hash is None:
        return {
            "mode": "legacy",
            "ok": False,
            "hash_ok": None,
            "signature_ok": None,
            "error_code": "legacy_seal_without_hash",
            "reason": (
                "seal predates Phase 57 and carries no integrity hash"
            ),
        }

    sealed_at = row.get("sealed_at")
    if isinstance(sealed_at, datetime):
        sealed_at_iso = sealed_at.isoformat()
    else:
        sealed_at_iso = str(sealed_at) if sealed_at is not None else ""

    recomputed = compute_seal_hash(
        organization_id=int(row["organization_id"]),
        tip_event_id=int(row["tip_event_id"]),
        tip_event_hash=row["tip_event_hash"],
        event_count=int(row["event_count"]),
        sealed_at_iso=sealed_at_iso,
        sealed_by_user_id=row.get("sealed_by_user_id"),
        sealed_by_email=row.get("sealed_by_email"),
        note=row.get("note"),
    )
    hash_ok = (recomputed == stored_hash)

    # Signature verification, if present.
    signature_ok: Optional[bool] = None
    sig_error_code: Optional[str] = None
    sig_hex = row.get("seal_signature_hex")
    kid = row.get("seal_signing_key_id")
    if sig_hex and kid:
        ring = _resolve_keyring()
        secret = ring.get(kid)
        if secret is None:
            signature_ok = False
            sig_error_code = "signing_key_not_in_keyring"
        else:
            expected = _compute_hmac_signature(stored_hash, secret)
            import hmac as _hmac
            signature_ok = _hmac.compare_digest(expected, sig_hex)
            if not signature_ok:
                sig_error_code = "signature_mismatch"

    ok = hash_ok and (signature_ok is not False)
    error_code: Optional[str] = None
    if not hash_ok:
        error_code = "seal_hash_mismatch"
    elif sig_error_code:
        error_code = sig_error_code

    return {
        "mode": "signed" if sig_hex else "hashed",
        "ok": bool(ok),
        "hash_ok": hash_ok,
        "signature_ok": signature_ok,
        "recomputed_hash": recomputed,
        "stored_hash": stored_hash,
        "key_id": kid,
        "error_code": error_code,
        "reason": None if ok else (
            "seal content was mutated after write"
            if not hash_ok else
            "signature failed verification"
        ),
    }


# ---------------------------------------------------------------------
# Phase 59 — unified trust verdict
# ---------------------------------------------------------------------

class BundleTrustCategory(str, Enum):
    """Operator-facing unified verdict for a bundle's trust state.

    The evidence verify endpoint (/note-versions/{id}/evidence-bundle/verify)
    already returns `body_hash_ok` and a `signature` verdict
    separately. Category folds both into one answer an operator can
    act on without mentally combining two fields.
    """
    # Signed, body hash matches, signature verifies.
    verified = "verified"
    # Bundle was issued unsigned; body hash matches. Cryptographic
    # trust is limited to what the body hash proves. Operator-
    # visible: this is a deliberate mode, not a failure.
    unsigned_ok = "unsigned_ok"
    # Body hash mismatch: someone edited the bundle content without
    # updating envelope.body_hash_sha256.
    failed_tamper = "failed_tamper"
    # Body hash matches but the HMAC does not. Envelope-only
    # tampering OR signature corruption.
    failed_signature = "failed_signature"
    # Signature references a key id no longer in the host's keyring.
    # Not a tamper indication by itself — the operator rotated the
    # key out. Action: restore the key OR re-verify on another host.
    stale_key = "stale_key"
    # Host has signing mode enabled but no keys configured — cannot
    # verify. Operator must restore signing config.
    stale_config = "stale_config"
    # Catch-all for shape/version problems (malformed signature,
    # unknown signing mode, etc).
    unverifiable = "unverifiable"


def classify_bundle_trust(
    body_hash_ok: bool,
    signature_verdict: dict[str, Any],
) -> dict[str, Any]:
    """Fold body-hash + signature verdicts into a single
    operator-facing category.

    Rules:
      - body_hash_ok=False always wins as `failed_tamper` (someone
        mutated the body without touching the envelope).
      - otherwise category depends on the signature branch.
    """
    sig_mode = (signature_verdict or {}).get("mode") or "disabled"
    sig_ok = (signature_verdict or {}).get("ok")
    sig_error = (signature_verdict or {}).get("error_code")

    if not body_hash_ok:
        cat = BundleTrustCategory.failed_tamper
        reason = (
            "the bundle body was mutated after issuance (recomputed "
            "body hash does not match the envelope hash)"
        )
    elif sig_mode == "disabled":
        cat = BundleTrustCategory.unsigned_ok
        reason = (
            "bundle was issued unsigned; body hash matches — trust "
            "limited to body integrity only"
        )
    elif sig_error == "signing_key_not_in_keyring":
        cat = BundleTrustCategory.stale_key
        reason = (
            "signing key_id referenced by the bundle is not in this "
            "host's keyring; restore the key or verify on another "
            "host"
        )
    elif sig_error == "evidence_signing_unconfigured":
        cat = BundleTrustCategory.stale_config
        reason = (
            "this host has signing mode enabled but no keys "
            "configured; cannot verify"
        )
    elif sig_error in {
        "malformed_signature",
        "unknown_signing_mode",
        "unsigned_bundle",
    }:
        cat = BundleTrustCategory.unverifiable
        reason = (
            signature_verdict.get("reason")
            or "bundle signature block is not verifiable"
        )
    elif sig_ok is True:
        cat = BundleTrustCategory.verified
        reason = "body hash and signature verify"
    else:
        cat = BundleTrustCategory.failed_signature
        reason = (
            signature_verdict.get("reason")
            or "signature did not verify"
        )

    return {
        "category": cat.value,
        "ok": cat == BundleTrustCategory.verified
        or cat == BundleTrustCategory.unsigned_ok,
        "reason": reason,
        "signature_mode": sig_mode,
        "key_id": (signature_verdict or {}).get("key_id"),
    }


__all__ = [
    "EvidenceEventType",
    "EVIDENCE_EVENT_TYPES",
    "record_evidence_event",
    "EvidenceWriteResult",
    "list_events_for_note",
    "list_events_for_org",
    "verify_chain",
    "ChainVerification",
    "note_evidence_health",
    "NoteEvidenceHealth",
    "build_evidence_bundle",
    "BUNDLE_VERSION",
    "EvidenceSigningError",
    "verify_signature",
    # Phase 57 additions
    "keyring_posture",
    "compute_seal_hash",
    "sign_seal_hash",
    "verify_seal_row",
    # Phase 59 additions
    "BundleTrustCategory",
    "classify_bundle_trust",
]
