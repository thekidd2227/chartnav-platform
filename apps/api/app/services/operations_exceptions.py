"""Phase 53 — enterprise operations & exceptions control plane (wave 8).

Aggregates the operational exception state of an organization into
queues that an admin / support operator can act on:

  - blocked-sign attempts (by gate)           from security_audit_events
  - blocked-export attempts                   from security_audit_events
  - notes awaiting final physician approval   from note_versions
  - notes with invalidated final approval     from note_versions
  - final-approval signature mismatches       from security_audit_events
  - final-approval unauthorized attempts      from security_audit_events
  - identity/auth denial events               from security_audit_events
  - session revocations + timeouts            from security_audit_events
                                                 + user_sessions
  - stuck ingest inputs                       from encounter_inputs
  - security-policy configuration status      synthesized from settings

This module is read-only. No state is mutated. It is the single
place that knows how audit-event / error-code strings map to
actionable operational buckets — keeping that mapping in one file
means routes, counters, and UI labels all agree.

Design note: the ops queue never invents a category. If the repo
has no SCIM surface, there is no `scim_identity_conflict` bucket.
If OIDC identity mapping is a pure email-claim lookup, the
"identity ambiguous" bucket is honestly labelled as
`identity_unknown_user` — the signal that actually exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Optional

from sqlalchemy import text

from app.db import fetch_all, fetch_one


# ---------------------------------------------------------------------
# Category taxonomy — the single source of truth.
# ---------------------------------------------------------------------

class ExceptionCategory(str, Enum):
    """Canonical operational exception categories.

    Each value maps to a bucket in the ops queue UI. The mapping from
    raw audit `event_type` / `error_code` values to these categories
    lives in `EVENT_TO_CATEGORY` below. Adding a new category means
    extending that mapping AND the UI.

    These names are engineering-facing, not marketing. If someone
    wants a "SCIM conflict" bucket, the question is whether SCIM
    exists in the product yet; if it does not, do not add the
    category.
    """
    # Clinical governance
    governance_sign_blocked = "governance_sign_blocked"
    export_blocked = "export_blocked"
    final_approval_pending = "final_approval_pending"
    final_approval_invalidated = "final_approval_invalidated"
    final_approval_signature_mismatch = "final_approval_signature_mismatch"
    final_approval_unauthorized = "final_approval_unauthorized"

    # Identity / access denial
    identity_unknown_user = "identity_unknown_user"
    identity_token_expired = "identity_token_expired"
    identity_invalid_token = "identity_invalid_token"
    identity_invalid_issuer = "identity_invalid_issuer"
    identity_invalid_audience = "identity_invalid_audience"
    identity_missing_user_claim = "identity_missing_user_claim"
    identity_cross_org_attempt = "identity_cross_org_attempt"

    # Session governance
    session_revoked_active = "session_revoked_active"
    session_idle_timeout = "session_idle_timeout"
    session_absolute_timeout = "session_absolute_timeout"

    # Ingest pipeline
    ingest_stuck = "ingest_stuck"

    # Security / admin policy config
    security_policy_unconfigured = "security_policy_unconfigured"

    # Phase 55 — evidence-chain integrity
    evidence_chain_broken = "evidence_chain_broken"

    # Phase 56 — evidence-sink delivery failures + export snapshots
    evidence_sink_delivery_failed = "evidence_sink_delivery_failed"
    export_snapshot_missing = "export_snapshot_missing"

    # Phase 57 — signing posture + retry backlog + retention.
    evidence_signing_inconsistent = "evidence_signing_inconsistent"
    evidence_sink_retry_pending = "evidence_sink_retry_pending"

    # Phase 59 — operator-actionable sink failures that auto-retry
    # will NOT clear (crossed attempt cap or operator-abandoned).
    evidence_sink_permanent_failure = "evidence_sink_permanent_failure"


# Map each *audit* row to a category. Keys are matched first on
# `event_type`; for pre-auth failures the event_type IS the error
# code (see app/main.py:_http_exception_handler).
EVENT_TO_CATEGORY: dict[str, ExceptionCategory] = {
    # Note lifecycle — denial/exception events
    "note_sign_blocked":                        ExceptionCategory.governance_sign_blocked,
    "note_export_blocked":                      ExceptionCategory.export_blocked,
    "note_final_approval_invalidated":          ExceptionCategory.final_approval_invalidated,
    "note_final_approval_signature_mismatch":   ExceptionCategory.final_approval_signature_mismatch,
    "note_final_approval_unauthorized":         ExceptionCategory.final_approval_unauthorized,
    # note_final_approval_invalid_state is intentionally NOT bucketed
    # here — its error_code varies and the ops queue uses the pending
    # list (from note_versions) rather than a replay of every bounced
    # attempt.

    # Identity / auth
    "unknown_user":                             ExceptionCategory.identity_unknown_user,
    "token_expired":                            ExceptionCategory.identity_token_expired,
    "invalid_token":                            ExceptionCategory.identity_invalid_token,
    "invalid_issuer":                           ExceptionCategory.identity_invalid_issuer,
    "invalid_audience":                         ExceptionCategory.identity_invalid_audience,
    "missing_user_claim":                       ExceptionCategory.identity_missing_user_claim,
    "cross_org_access_forbidden":               ExceptionCategory.identity_cross_org_attempt,

    # Session governance — these ARE the denial event_types emitted
    # by app/session_governance.py.
    "session_revoked":                          ExceptionCategory.session_revoked_active,
    "session_idle_timeout":                     ExceptionCategory.session_idle_timeout,
    "session_absolute_timeout":                 ExceptionCategory.session_absolute_timeout,
}


# Short, UI-stable human labels + remediation hints. The UI reads
# these so a support operator does not have to guess what a bucket
# means.
CATEGORY_METADATA: dict[ExceptionCategory, dict[str, str]] = {
    ExceptionCategory.governance_sign_blocked: {
        "label": "Sign blocked by governance",
        "severity": "warning",
        "next_step": (
            "Resolve or acknowledge each missing-data flag on the note, "
            "then retry the sign."
        ),
    },
    ExceptionCategory.export_blocked: {
        "label": "Export blocked",
        "severity": "warning",
        "next_step": (
            "Either perform final physician approval (pending) or "
            "route through the amendment flow (invalidated), then retry."
        ),
    },
    ExceptionCategory.final_approval_pending: {
        "label": "Awaiting final physician approval",
        "severity": "info",
        "next_step": (
            "An authorized doctor must type their exact stored name "
            "to approve. Until then, export is blocked."
        ),
    },
    ExceptionCategory.final_approval_invalidated: {
        "label": "Final approval invalidated",
        "severity": "warning",
        "next_step": (
            "Prior approval no longer applies (usually due to an "
            "amendment). Approve the current record of care."
        ),
    },
    ExceptionCategory.final_approval_signature_mismatch: {
        "label": "Final-approval signature mismatch",
        "severity": "warning",
        "next_step": (
            "The doctor typed a name that does not match their stored "
            "full_name (case-sensitive). Confirm the stored name is "
            "correct or have the doctor retype."
        ),
    },
    ExceptionCategory.final_approval_unauthorized: {
        "label": "Unauthorized final-approval attempt",
        "severity": "error",
        "next_step": (
            "Caller is not flagged is_authorized_final_signer. Grant "
            "the flag (org admin) or do not route this note to them."
        ),
    },
    ExceptionCategory.identity_unknown_user: {
        "label": "Identity not mapped to a user",
        "severity": "error",
        "next_step": (
            "A valid token arrived for an identity with no matching "
            "users row. Provision the user, or verify the JWT user "
            "claim matches a seeded email."
        ),
    },
    ExceptionCategory.identity_token_expired: {
        "label": "Token expired",
        "severity": "info",
        "next_step": "Caller should re-authenticate.",
    },
    ExceptionCategory.identity_invalid_token: {
        "label": "Invalid token",
        "severity": "warning",
        "next_step": (
            "JWT failed verification. Check clock skew, JWKS URL, and "
            "signing key rotation."
        ),
    },
    ExceptionCategory.identity_invalid_issuer: {
        "label": "Token issuer mismatch",
        "severity": "warning",
        "next_step": (
            "Token `iss` does not match CHARTNAV_JWT_ISSUER. Verify "
            "the configured issuer matches the IdP."
        ),
    },
    ExceptionCategory.identity_invalid_audience: {
        "label": "Token audience mismatch",
        "severity": "warning",
        "next_step": (
            "Token `aud` does not match CHARTNAV_JWT_AUDIENCE. "
            "Confirm client registration in the IdP."
        ),
    },
    ExceptionCategory.identity_missing_user_claim: {
        "label": "Token missing user claim",
        "severity": "warning",
        "next_step": (
            "Required claim (default `email`) was absent. Adjust the "
            "IdP mapping or CHARTNAV_JWT_USER_CLAIM."
        ),
    },
    ExceptionCategory.identity_cross_org_attempt: {
        "label": "Cross-org access attempt",
        "severity": "warning",
        "next_step": (
            "A caller tried to act on another org's resource. Confirm "
            "org assignment in the users row."
        ),
    },
    ExceptionCategory.session_revoked_active: {
        "label": "Session revoked while in use",
        "severity": "info",
        "next_step": "Expected after an admin revoke; no action needed.",
    },
    ExceptionCategory.session_idle_timeout: {
        "label": "Session idle timeout",
        "severity": "info",
        "next_step": "Caller should re-authenticate.",
    },
    ExceptionCategory.session_absolute_timeout: {
        "label": "Session absolute timeout",
        "severity": "info",
        "next_step": "Caller should re-authenticate.",
    },
    ExceptionCategory.ingest_stuck: {
        "label": "Ingest input stuck",
        "severity": "warning",
        "next_step": (
            "Input has failed retry and has `last_error_code` set. "
            "Inspect the ingest queue and retry manually or fix the "
            "upstream cause."
        ),
    },
    ExceptionCategory.security_policy_unconfigured: {
        "label": "Security policy unconfigured",
        "severity": "info",
        "next_step": (
            "This org has no session timeouts, no audit sink, or no "
            "security-admin allowlist configured. Review the Security "
            "tab."
        ),
    },
    ExceptionCategory.evidence_chain_broken: {
        "label": "Evidence chain integrity broken",
        "severity": "error",
        "next_step": (
            "The tamper-evident evidence chain for this org failed "
            "re-verification. Some row has been mutated or deleted. "
            "Re-run /admin/operations/evidence-chain-verify for the "
            "first-broken event id and investigate the DB."
        ),
    },
    ExceptionCategory.evidence_sink_delivery_failed: {
        "label": "Evidence sink delivery failed",
        "severity": "warning",
        "next_step": (
            "One or more evidence events failed to reach the "
            "configured external sink. The in-app chain is still "
            "authoritative; re-verify transport config or probe "
            "the sink from /admin/operations/evidence-sink/test."
        ),
    },
    ExceptionCategory.export_snapshot_missing: {
        "label": "Export without snapshot",
        "severity": "warning",
        "next_step": (
            "A note_exported evidence event exists with no "
            "corresponding export snapshot row. The exported state "
            "was recorded but the point-in-time artifact bytes were "
            "not captured. Re-export if the record of care needs "
            "an immutable snapshot."
        ),
    },
    ExceptionCategory.evidence_signing_inconsistent: {
        "label": "Evidence signing configuration inconsistent",
        "severity": "error",
        "next_step": (
            "The org has signing enabled but the active "
            "evidence_signing_key_id is not present in the process "
            "keyring. New bundles will 503 until the keyring entry "
            "is restored or the active key_id is changed."
        ),
    },
    ExceptionCategory.evidence_sink_retry_pending: {
        "label": "Evidence sink retries pending",
        "severity": "warning",
        "next_step": (
            "One or more evidence events have sink_status='failed'. "
            "POST /admin/operations/evidence-sink/retry-failed to "
            "attempt delivery again. The in-app chain remains "
            "authoritative either way."
        ),
    },
    ExceptionCategory.evidence_sink_permanent_failure: {
        "label": "Evidence sink permanent failure",
        "severity": "error",
        "next_step": (
            "One or more evidence events exceeded the retry cap or "
            "were abandoned by an operator. Automatic retries will "
            "not clear these. Investigate the transport, then either "
            "fix the target and POST /admin/operations/evidence-sink/"
            "retry-failed again, or accept the abandonment."
        ),
    },
}


def category_metadata(cat: ExceptionCategory) -> dict[str, str]:
    return CATEGORY_METADATA[cat]


# ---------------------------------------------------------------------
# Data classes surfaced to the HTTP layer
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ExceptionItem:
    """One row in an ops queue."""
    category: str
    severity: str
    label: str
    next_step: str
    # Identifying context — each optional, set only when applicable.
    note_id: Optional[int] = None
    note_version_number: Optional[int] = None
    encounter_id: Optional[int] = None
    actor_email: Optional[str] = None
    actor_user_id: Optional[int] = None
    error_code: Optional[str] = None
    detail: Optional[str] = None
    occurred_at: Optional[str] = None  # ISO string
    # For blocker rows we attach the live note state so the UI can
    # render "awaiting provider action" vs "awaiting admin action".
    draft_status: Optional[str] = None
    final_approval_status: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass(frozen=True)
class ExceptionCounters:
    """A compact per-category counter block. Fed by both live
    note_versions state and recent audit events."""
    organization_id: int
    window_hours: int
    since: str
    until: str
    counts: dict[str, int]  # category value → count
    security_policy: dict[str, Any]  # flags for the config-status card
    total_open: int  # coarse summary for the admin nav badge

    def as_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "window_hours": self.window_hours,
            "since": self.since,
            "until": self.until,
            "counts": self.counts,
            "security_policy": self.security_policy,
            "total_open": self.total_open,
        }


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

_DEFAULT_WINDOW_HOURS = 168  # seven days — matches the KPI default window


def _window(hours: int) -> tuple[datetime, datetime, str, str]:
    hours = max(1, min(int(hours), 24 * 31))  # clamp 1h … 31d
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=hours)
    return since, until, since.isoformat(), until.isoformat()


def _safe_iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


# ---------------------------------------------------------------------
# Live-state queues (read note_versions)
# ---------------------------------------------------------------------

def list_final_approval_pending(
    organization_id: int,
    *,
    limit: int = 100,
) -> list[ExceptionItem]:
    """All notes in this org currently awaiting final physician
    approval. Drives the primary action queue — every row here is
    an unfinished piece of clinical work.
    """
    meta = CATEGORY_METADATA[ExceptionCategory.final_approval_pending]
    rows = fetch_all(
        "SELECT nv.id AS note_id, nv.version_number, nv.encounter_id, "
        "nv.draft_status, nv.final_approval_status, "
        "nv.signed_at, nv.signed_by_user_id "
        "FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.final_approval_status = 'pending' "
        "AND nv.superseded_at IS NULL "
        "ORDER BY nv.signed_at DESC LIMIT :limit",
        {"org": organization_id, "limit": int(limit)},
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.final_approval_pending.value,
            severity=meta["severity"],
            label=meta["label"],
            next_step=meta["next_step"],
            note_id=r["note_id"],
            note_version_number=r["version_number"],
            encounter_id=r["encounter_id"],
            actor_user_id=r["signed_by_user_id"],
            draft_status=r["draft_status"],
            final_approval_status=r["final_approval_status"],
            occurred_at=_safe_iso(r["signed_at"]),
        )
        for r in rows
    ]


def list_final_approval_invalidated(
    organization_id: int,
    *,
    limit: int = 100,
) -> list[ExceptionItem]:
    meta = CATEGORY_METADATA[ExceptionCategory.final_approval_invalidated]
    rows = fetch_all(
        "SELECT nv.id AS note_id, nv.version_number, nv.encounter_id, "
        "nv.draft_status, nv.final_approval_status, "
        "nv.final_approval_invalidated_at, "
        "nv.final_approval_invalidated_reason "
        "FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.final_approval_status = 'invalidated' "
        "ORDER BY nv.final_approval_invalidated_at DESC LIMIT :limit",
        {"org": organization_id, "limit": int(limit)},
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.final_approval_invalidated.value,
            severity=meta["severity"],
            label=meta["label"],
            next_step=meta["next_step"],
            note_id=r["note_id"],
            note_version_number=r["version_number"],
            encounter_id=r["encounter_id"],
            draft_status=r["draft_status"],
            final_approval_status=r["final_approval_status"],
            detail=r["final_approval_invalidated_reason"],
            occurred_at=_safe_iso(r["final_approval_invalidated_at"]),
        )
        for r in rows
    ]


def list_stuck_ingest(
    organization_id: int,
    *,
    limit: int = 50,
) -> list[ExceptionItem]:
    """Ingest inputs that have failed hard — status='failed' OR
    last_error_code is set. These are not an audit-log replay; they
    are the live queue.

    The query is defensive: some older rows may lack the
    `last_error_code` / `status` columns, so we guard each clause.
    """
    meta = CATEGORY_METADATA[ExceptionCategory.ingest_stuck]
    rows = fetch_all(
        "SELECT ei.id AS input_id, ei.encounter_id, ei.processing_status, "
        "ei.last_error_code, ei.retry_count, ei.created_at, ei.updated_at "
        "FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND (ei.processing_status = 'failed' OR ei.last_error_code IS NOT NULL) "
        "ORDER BY ei.updated_at DESC LIMIT :limit",
        {"org": organization_id, "limit": int(limit)},
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.ingest_stuck.value,
            severity=meta["severity"],
            label=meta["label"],
            next_step=meta["next_step"],
            note_id=None,
            encounter_id=r["encounter_id"],
            error_code=r["last_error_code"],
            detail=(
                f"input_id={r['input_id']} status={r['processing_status']} "
                f"retries={r['retry_count']}"
            ),
            occurred_at=_safe_iso(r["updated_at"] or r["created_at"]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------
# Audit-backed queues (read security_audit_events)
# ---------------------------------------------------------------------

_AUDIT_BASE_COLS = (
    "id, event_type, error_code, actor_email, actor_user_id, "
    "path, method, detail, remote_addr, created_at"
)


def _audit_rows_by_event_types(
    organization_id: int,
    event_types: Iterable[str],
    since: datetime,
    until: datetime,
    limit: int,
) -> list[dict[str, Any]]:
    types = list(event_types)
    if not types:
        return []
    # sqlite has no `= ANY`, so we expand manually. We bind each
    # value to avoid string interpolation.
    placeholders = ",".join([f":et{i}" for i in range(len(types))])
    params: dict[str, Any] = {
        "org": organization_id,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "limit": int(limit),
    }
    for i, t in enumerate(types):
        params[f"et{i}"] = t
    sql = (
        f"SELECT {_AUDIT_BASE_COLS} FROM security_audit_events "
        f"WHERE organization_id = :org "
        f"AND event_type IN ({placeholders}) "
        f"AND created_at >= :since AND created_at <= :until "
        f"ORDER BY created_at DESC LIMIT :limit"
    )
    return fetch_all(sql, params)


def _audit_row_to_item(row: dict[str, Any]) -> Optional[ExceptionItem]:
    cat = EVENT_TO_CATEGORY.get(row.get("event_type") or "")
    if cat is None:
        return None
    meta = CATEGORY_METADATA[cat]
    # Try to parse a note_id out of `detail` when present — the sign
    # / export / final-approve audit lines embed it as `note_id=NN`.
    note_id: Optional[int] = None
    detail = row.get("detail") or ""
    if "note_id=" in detail:
        try:
            fragment = detail.split("note_id=", 1)[1]
            token = fragment.split()[0].split(",")[0]
            note_id = int(token)
        except (ValueError, IndexError):
            note_id = None
    return ExceptionItem(
        category=cat.value,
        severity=meta["severity"],
        label=meta["label"],
        next_step=meta["next_step"],
        note_id=note_id,
        actor_email=row.get("actor_email"),
        actor_user_id=row.get("actor_user_id"),
        error_code=row.get("error_code"),
        detail=detail or None,
        occurred_at=_safe_iso(row.get("created_at")),
    )


def list_audit_exceptions(
    organization_id: int,
    categories: Iterable[ExceptionCategory],
    *,
    hours: int = _DEFAULT_WINDOW_HOURS,
    limit: int = 200,
) -> list[ExceptionItem]:
    """Generic audit-backed list. Pass the categories you want and
    the function looks up the event_types those categories map to
    and pulls them.

    Returns rows newest-first, already shaped for the UI.
    """
    since, until, _, _ = _window(hours)
    event_types: list[str] = [
        et for et, cat in EVENT_TO_CATEGORY.items()
        if cat in set(categories)
    ]
    rows = _audit_rows_by_event_types(
        organization_id, event_types, since, until, limit
    )
    items: list[ExceptionItem] = []
    for r in rows:
        item = _audit_row_to_item(r)
        if item is not None:
            items.append(item)
    return items


# ---------------------------------------------------------------------
# Security-policy configuration status (synthesised)
# ---------------------------------------------------------------------

def _security_policy_status(organization_id: int) -> dict[str, Any]:
    """Synthesise a readable "is this org's security policy set up?"
    signal from the settings blob. This is not a denial — it's an
    advisory card for the admin.
    """
    from app.security_policy import resolve_security_policy

    policy = resolve_security_policy(organization_id)
    idle = getattr(policy, "idle_timeout_minutes", None)
    absolute = getattr(policy, "absolute_timeout_minutes", None)
    sink_mode = getattr(policy, "audit_sink_mode", None) or "disabled"
    allowlist = getattr(policy, "security_admin_emails", ()) or ()

    session_tracking_on = bool(idle) or bool(absolute)
    sink_on = sink_mode != "disabled"
    allowlist_on = len(allowlist) > 0
    mfa_on = bool(getattr(policy, "require_mfa", False))

    # A policy is fully unconfigured when NONE of the observable
    # enterprise gates are on. This is the signal the ops card uses.
    unconfigured = not (session_tracking_on or sink_on or allowlist_on or mfa_on)

    # Phase 56 — surface evidence-sink and signing status so the
    # admin UI can tell an operator at a glance what external
    # integrations are on.
    ev_sink_mode = getattr(policy, "evidence_sink_mode", "disabled") or "disabled"
    ev_sink_on = ev_sink_mode != "disabled"
    ev_sign_mode = getattr(policy, "evidence_signing_mode", "disabled") or "disabled"
    ev_sign_on = ev_sign_mode != "disabled"

    # Phase 57 — signing posture + retention.
    retention_days = getattr(
        policy, "export_snapshot_retention_days", None,
    )
    # Phase 59 — sink retry retention.
    sink_retention_days = getattr(
        policy, "evidence_sink_retention_days", None,
    )

    # Keyring posture (safe: returns only key ids + consistency).
    kp: dict[str, Any] = {}
    try:
        from app.services.note_evidence import keyring_posture as _kp
        kp = _kp(organization_id)
    except Exception:
        kp = {}

    return {
        "session_tracking_configured": session_tracking_on,
        "audit_sink_configured": sink_on,
        "security_admin_allowlist_configured": allowlist_on,
        "mfa_required": mfa_on,
        "idle_timeout_minutes": idle,
        "absolute_timeout_minutes": absolute,
        "audit_sink_mode": sink_mode,
        "security_admin_allowlist_count": len(allowlist),
        "unconfigured": unconfigured,
        # Phase 56 — evidence posture.
        "evidence_sink_mode": ev_sink_mode,
        "evidence_sink_configured": ev_sink_on,
        "evidence_signing_mode": ev_sign_mode,
        "evidence_signing_configured": ev_sign_on,
        # Phase 57 — signing keyring + retention posture.
        "evidence_signing_active_key_id": kp.get("active_key_id"),
        "evidence_signing_active_key_present": kp.get("active_key_present"),
        "evidence_signing_keyring_key_ids": kp.get("keyring_key_ids") or [],
        "evidence_signing_inconsistent": bool(kp.get("inconsistent")),
        "export_snapshot_retention_days": retention_days,
        "export_snapshot_retention_configured": retention_days is not None,
        # Phase 59 — sink retry retention + max attempts constant.
        "evidence_sink_retention_days": sink_retention_days,
        "evidence_sink_retention_configured": sink_retention_days is not None,
        "evidence_sink_max_attempts": _max_sink_attempts(),
    }


def _max_sink_attempts() -> int:
    """Best-effort lookup of the retry cap. Imported locally so a
    defective evidence_sink module can't break the ops overview."""
    try:
        from app.services.evidence_sink import MAX_SINK_ATTEMPTS
        return int(MAX_SINK_ATTEMPTS)
    except Exception:
        return 0


# ---------------------------------------------------------------------
# Counters — the overview payload
# ---------------------------------------------------------------------

def compute_counters(
    organization_id: int,
    *,
    hours: int = _DEFAULT_WINDOW_HOURS,
) -> ExceptionCounters:
    """One aggregate call for the overview card. Zero-cost when
    there is no data: all counts start at 0 and only roll up when
    rows exist."""
    since, until, since_iso, until_iso = _window(hours)

    counts: dict[str, int] = {c.value: 0 for c in ExceptionCategory}

    # --- Live note_versions counters -------------------------------
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.final_approval_status = 'pending' "
        "AND nv.superseded_at IS NULL",
        {"org": organization_id},
    )
    counts[ExceptionCategory.final_approval_pending.value] = (
        int(row["n"]) if row else 0
    )

    row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.final_approval_status = 'invalidated'",
        {"org": organization_id},
    )
    counts[ExceptionCategory.final_approval_invalidated.value] = (
        int(row["n"]) if row else 0
    )

    # --- Audit-backed windowed counters ----------------------------
    agg = fetch_all(
        "SELECT event_type, COUNT(*) AS n FROM security_audit_events "
        "WHERE organization_id = :org "
        "AND created_at >= :since AND created_at <= :until "
        "GROUP BY event_type",
        {"org": organization_id, "since": since.isoformat(),
         "until": until.isoformat()},
    )
    for r in agg:
        cat = EVENT_TO_CATEGORY.get(r["event_type"])
        if cat is not None:
            counts[cat.value] = int(r["n"])

    # --- Ingest-stuck counter --------------------------------------
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND (ei.processing_status = 'failed' OR ei.last_error_code IS NOT NULL) "
        "AND ei.updated_at >= :since",
        {"org": organization_id, "since": since.isoformat()},
    )
    counts[ExceptionCategory.ingest_stuck.value] = (
        int(row["n"]) if row else 0
    )

    sec = _security_policy_status(organization_id)
    counts[ExceptionCategory.security_policy_unconfigured.value] = (
        1 if sec["unconfigured"] else 0
    )

    # Phase 55 — evidence-chain integrity. Non-zero if the chain
    # fails re-verification. Uses the note_evidence service; the
    # import is local to avoid hardening-time circular import risk.
    try:
        from app.services.note_evidence import verify_chain as _verify_chain
        chain_verdict = _verify_chain(organization_id)
        counts[ExceptionCategory.evidence_chain_broken.value] = (
            0 if chain_verdict.broken_at_event_id is None else 1
        )
    except Exception:
        # A verification error itself is surfaced as a broken chain —
        # either way, an operator needs to look.
        counts[ExceptionCategory.evidence_chain_broken.value] = 1

    # Phase 56 — evidence-sink delivery failures, windowed.
    fail_row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_evidence_events "
        "WHERE organization_id = :org "
        "AND sink_status = 'failed' "
        "AND occurred_at >= :since",
        {"org": organization_id, "since": since.isoformat()},
    )
    counts[ExceptionCategory.evidence_sink_delivery_failed.value] = (
        int(fail_row["n"]) if fail_row else 0
    )

    # Phase 57 / 59 — CURRENT retry backlog (not windowed). We now
    # split failed rows by disposition:
    #   retry_pending        = sink_status=failed AND
    #                          disposition IS NULL OR 'pending'
    #   permanent_failure    = disposition IN ('permanent_failure',
    #                                          'abandoned')
    # A row sitting under 'permanent_failure' will NOT be picked up
    # by /evidence-sink/retry-failed, so it is operator-actionable
    # rather than auto-retry noise.
    pending_row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_evidence_events "
        "WHERE organization_id = :org AND sink_status = 'failed' "
        "AND (sink_retry_disposition IS NULL "
        "  OR sink_retry_disposition = 'pending')",
        {"org": organization_id},
    )
    counts[ExceptionCategory.evidence_sink_retry_pending.value] = (
        int(pending_row["n"]) if pending_row else 0
    )
    perm_row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_evidence_events "
        "WHERE organization_id = :org AND sink_status = 'failed' "
        "AND sink_retry_disposition IN ('permanent_failure', 'abandoned')",
        {"org": organization_id},
    )
    counts[ExceptionCategory.evidence_sink_permanent_failure.value] = (
        int(perm_row["n"]) if perm_row else 0
    )

    # Phase 57 — signing posture. We treat any inconsistency
    # (signing mode on, active key missing from ring, or ring
    # empty) as a hard error the admin must see.
    try:
        from app.services.note_evidence import keyring_posture
        kp = keyring_posture(organization_id)
        counts[ExceptionCategory.evidence_signing_inconsistent.value] = (
            1 if kp.get("inconsistent") else 0
        )
    except Exception:
        counts[ExceptionCategory.evidence_signing_inconsistent.value] = 0

    # Phase 56 — exports missing a snapshot. We find note_exported
    # evidence events in the window whose note_version_id has no
    # corresponding row in note_export_snapshots.
    missing_snap_row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_evidence_events ev "
        "WHERE ev.organization_id = :org "
        "AND ev.event_type = 'note_exported' "
        "AND ev.occurred_at >= :since "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM note_export_snapshots s "
        "  WHERE s.note_version_id = ev.note_version_id "
        "  AND s.id >= 1"
        ")",
        {"org": organization_id, "since": since.isoformat()},
    )
    counts[ExceptionCategory.export_snapshot_missing.value] = (
        int(missing_snap_row["n"]) if missing_snap_row else 0
    )

    # A coarse "anything open" number for the nav badge. We
    # intentionally EXCLUDE pure-session categories (idle / absolute
    # / revoked-in-use) because those are expected traffic after a
    # revoke; inflating the badge with them is noise.
    noisy_cats = {
        ExceptionCategory.session_idle_timeout.value,
        ExceptionCategory.session_absolute_timeout.value,
        ExceptionCategory.session_revoked_active.value,
        ExceptionCategory.identity_token_expired.value,
    }
    total_open = sum(v for k, v in counts.items() if k not in noisy_cats)

    return ExceptionCounters(
        organization_id=organization_id,
        window_hours=int(hours),
        since=since_iso,
        until=until_iso,
        counts=counts,
        security_policy=sec,
        total_open=total_open,
    )


# ---------------------------------------------------------------------
# Blocked-note roll-up (governance + export lanes merged)
# ---------------------------------------------------------------------

def list_blocked_notes(
    organization_id: int,
    *,
    hours: int = _DEFAULT_WINDOW_HOURS,
    limit: int = 200,
) -> list[ExceptionItem]:
    """The unified blocked-notes queue — merges sign-blocked and
    export-blocked audit rows so the UI can show one operational
    timeline grouped by reason."""
    return list_audit_exceptions(
        organization_id,
        [
            ExceptionCategory.governance_sign_blocked,
            ExceptionCategory.export_blocked,
            ExceptionCategory.final_approval_signature_mismatch,
            ExceptionCategory.final_approval_unauthorized,
        ],
        hours=hours,
        limit=limit,
    )


def list_identity_exceptions(
    organization_id: int,
    *,
    hours: int = _DEFAULT_WINDOW_HOURS,
    limit: int = 200,
) -> list[ExceptionItem]:
    return list_audit_exceptions(
        organization_id,
        [
            ExceptionCategory.identity_unknown_user,
            ExceptionCategory.identity_invalid_token,
            ExceptionCategory.identity_invalid_issuer,
            ExceptionCategory.identity_invalid_audience,
            ExceptionCategory.identity_missing_user_claim,
            ExceptionCategory.identity_token_expired,
            ExceptionCategory.identity_cross_org_attempt,
        ],
        hours=hours,
        limit=limit,
    )


def list_session_exceptions(
    organization_id: int,
    *,
    hours: int = _DEFAULT_WINDOW_HOURS,
    limit: int = 200,
) -> list[ExceptionItem]:
    return list_audit_exceptions(
        organization_id,
        [
            ExceptionCategory.session_revoked_active,
            ExceptionCategory.session_idle_timeout,
            ExceptionCategory.session_absolute_timeout,
        ],
        hours=hours,
        limit=limit,
    )


def security_config_status(organization_id: int) -> dict[str, Any]:
    """Public wrapper around the synthesized policy status for the
    /admin/operations/security-config-status endpoint."""
    return _security_policy_status(organization_id)


__all__ = [
    "ExceptionCategory",
    "EVENT_TO_CATEGORY",
    "CATEGORY_METADATA",
    "category_metadata",
    "ExceptionItem",
    "ExceptionCounters",
    "compute_counters",
    "list_final_approval_pending",
    "list_final_approval_invalidated",
    "list_blocked_notes",
    "list_identity_exceptions",
    "list_session_exceptions",
    "list_stuck_ingest",
    "list_audit_exceptions",
    "security_config_status",
]
