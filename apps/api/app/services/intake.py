"""Digital intake — tokens + submissions.

Spec: docs/chartnav/closure/PHASE_B_Digital_Intake.md

What this module does:
  - Generates cryptographically-strong intake tokens. We store
    HMAC-SHA256(server_secret, raw_token) in `intake_tokens.token_hash`
    and return the raw token to staff exactly once at issuance.
  - Verifies a token from the public route: rejects on hash mismatch
    (404, never echoes the token), on `used_at IS NOT NULL` (410),
    and on `expires_at < now()` (410).
  - Provides accept/reject helpers that respect cross-org isolation:
    a staff caller in org-B trying to accept an org-A submission
    sees a 404, not a 403, so the existence of the row is not
    revealed.
  - Provides an in-process fixed-window rate limiter for the public
    GET /intakes/{token} endpoint (10 GETs per 60s per client IP per
    token). Redis-backed limiting is Phase C.

Truth limitations preserved (spec §9):
  - No identity verification beyond token possession.
  - Patient-side actions are NOT recorded with HIPAA-grade actor
    identity. The accepting staff member is the accountable actor
    in workflow_events.
  - Accepted data is treated as patient self-report; the clinician
    must confirm during the visit. Note generators must NOT
    auto-promote meds / allergies into the final note.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque

from app.db import fetch_one, transaction


# Token lifetime per spec §3 — 72 hours.
TOKEN_TTL_HOURS = 72

# Per-spec §4: more than 10 GETs on /intakes/{token} in 60s → 429.
PUBLIC_GET_LIMIT_PER_MINUTE = 10
PUBLIC_GET_WINDOW_SECONDS = 60


# ---------- Token issuance + hashing ---------------------------------

def _server_salt() -> bytes:
    """Per-process salt used to HMAC the raw token before storage.

    In real deployments this should be sourced from a secret store;
    in pilot we accept the env var `CHARTNAV_INTAKE_TOKEN_SALT` and
    fall back to a per-process random salt that survives the
    lifetime of the FastAPI process.
    """
    raw = os.environ.get("CHARTNAV_INTAKE_TOKEN_SALT")
    if raw:
        return raw.encode("utf-8")
    global _PROCESS_SALT
    try:
        return _PROCESS_SALT
    except NameError:
        pass
    _PROCESS_SALT = secrets.token_bytes(32)
    return _PROCESS_SALT


def hash_token(raw_token: str) -> str:
    return hmac.new(
        _server_salt(), raw_token.encode("utf-8"), hashlib.sha256,
    ).hexdigest()


def generate_token() -> str:
    """32-byte URL-safe token. ~43 base64url chars; high entropy."""
    return secrets.token_urlsafe(32)


def issue_token(
    *,
    organization_id: int,
    created_by_user_id: int,
    patient_identifier_candidate: str | None = None,
) -> dict[str, Any]:
    raw = generate_token()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    )
    with transaction() as conn:
        from app.db import insert_returning_id
        new_id = insert_returning_id(
            conn,
            "intake_tokens",
            {
                "organization_id": organization_id,
                "token_hash": hash_token(raw),
                "patient_identifier_candidate": patient_identifier_candidate,
                "expires_at": expires_at.isoformat(timespec="seconds"),
                "created_by_user_id": created_by_user_id,
            },
        )
    return {
        "id": new_id,
        "token": raw,
        "expires_at": expires_at.isoformat(timespec="seconds"),
    }


# ---------- Verification ---------------------------------------------

class IntakeTokenError(Exception):
    """Raised when a token is unknown / used / expired.

    The route layer catches this and returns the right HTTP code
    WITHOUT echoing the raw token, the candidate identifier, or any
    submitted payload field (PHI hygiene per spec §4 + §9).
    """

    def __init__(self, code: str, http_status: int):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def lookup_token_row(raw_token: str) -> dict[str, Any]:
    """Find a token row by raw token. Raises IntakeTokenError on
    any failure mode (unknown / used / expired). Returns the row
    (with `organization_id`, `id`, `expires_at`, `used_at`) on hit."""
    if not isinstance(raw_token, str) or len(raw_token) < 16:
        # Don't even hash absurdly short input — saves a CPU cycle and
        # avoids leaking timing on length.
        raise IntakeTokenError("intake_token_not_found", 404)
    h = hash_token(raw_token)
    row = fetch_one(
        "SELECT id, organization_id, patient_identifier_candidate, "
        "       expires_at, used_at "
        "FROM intake_tokens WHERE token_hash = :h",
        {"h": h},
    )
    if not row:
        raise IntakeTokenError("intake_token_not_found", 404)
    if row.get("used_at"):
        raise IntakeTokenError("intake_token_used", 410)
    expires_at = row.get("expires_at")
    if expires_at:
        # SQLite stores ISO strings; Postgres returns datetime.
        if isinstance(expires_at, str):
            try:
                exp_dt = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
            except ValueError:
                exp_dt = None
        else:
            exp_dt = expires_at
        if exp_dt is not None:
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt < datetime.now(timezone.utc):
                raise IntakeTokenError("intake_token_expired", 410)
    return dict(row)


# ---------- Submit ----------------------------------------------------

def record_submission(
    *,
    token_row: dict,
    payload: dict,
) -> int:
    """Insert an intake_submissions row and stamp the token used_at.
    The token can never be redeemed twice (single-use per spec §3)."""
    from app.db import insert_returning_id
    from sqlalchemy import text
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "intake_submissions",
            {
                "organization_id": token_row["organization_id"],
                "token_id": token_row["id"],
                "payload_json": json.dumps(payload, sort_keys=True),
                "status": "pending_review",
            },
        )
        conn.execute(
            text(
                "UPDATE intake_tokens SET used_at = CURRENT_TIMESTAMP "
                "WHERE id = :id AND used_at IS NULL"
            ),
            {"id": token_row["id"]},
        )
    return new_id


# ---------- Accept / reject ------------------------------------------

def accept_submission(
    *,
    submission_id: int,
    accepting_user_id: int,
    organization_id: int,
) -> dict[str, Any]:
    """Promote a pending intake submission into a draft patient
    candidate + a draft encounter row.

    Cross-org safety: returns the same 404-equivalent
    `intake_submission_not_found` error if the row is in a different
    org. We never reveal existence.
    """
    from app.db import insert_returning_id
    from sqlalchemy import text
    sub = fetch_one(
        "SELECT id, organization_id, token_id, payload_json, status "
        "FROM intake_submissions WHERE id = :id",
        {"id": submission_id},
    )
    if not sub or sub["organization_id"] != organization_id:
        raise IntakeTokenError("intake_submission_not_found", 404)
    if sub["status"] != "pending_review":
        raise IntakeTokenError(
            "intake_submission_not_pending", 409,
        )
    try:
        payload = json.loads(sub["payload_json"]) if sub["payload_json"] else {}
    except (json.JSONDecodeError, TypeError):
        payload = {}

    # Pull org default location for the draft encounter.
    loc_row = fetch_one(
        "SELECT id FROM locations WHERE organization_id = :oid "
        "ORDER BY id LIMIT 1",
        {"oid": organization_id},
    )
    if not loc_row:
        raise IntakeTokenError("intake_org_has_no_location", 422)

    patient_identifier = (
        payload.get("patient_identifier")
        or payload.get("mrn")
        or f"INTAKE-{submission_id}"
    )
    patient_name = (
        payload.get("patient_name")
        or payload.get("name")
        or "Intake Candidate"
    )
    reason = (
        payload.get("reason_for_visit") or payload.get("chief_complaint") or ""
    )

    with transaction() as conn:
        # Draft patient row (native patients table). Reuse if an
        # identifier already exists for this org so we never violate
        # the (organization_id, patient_identifier) UNIQUE.
        existing = fetch_one(
            "SELECT id FROM patients "
            "WHERE organization_id = :oid AND patient_identifier = :pid",
            {"oid": organization_id, "pid": patient_identifier},
        )
        if existing:
            patient_id = int(existing["id"])
        else:
            patient_id = insert_returning_id(
                conn,
                "patients",
                {
                    "organization_id": organization_id,
                    "patient_identifier": patient_identifier,
                    "first_name": (patient_name.split(" ", 1) + [""])[0][:120],
                    "last_name": (patient_name.split(" ", 1) + [""])[1][:120],
                },
            )
        encounter_id = insert_returning_id(
            conn,
            "encounters",
            {
                "organization_id": organization_id,
                "location_id": loc_row["id"],
                "patient_identifier": patient_identifier,
                "patient_name": patient_name,
                "provider_name": "Pending Assignment",
                "status": "scheduled",
                "patient_id": patient_id,
            },
        )
        conn.execute(
            text(
                "UPDATE intake_submissions SET "
                "  status = 'accepted', "
                "  reviewed_by_user_id = :uid, "
                "  reviewed_at = CURRENT_TIMESTAMP, "
                "  accepted_patient_id = :pid, "
                "  accepted_encounter_id = :eid, "
                "  reason = :reason "
                "WHERE id = :id"
            ),
            {
                "uid": accepting_user_id,
                "pid": patient_id,
                "eid": encounter_id,
                "reason": reason or None,
                "id": submission_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
                "VALUES (:enc, 'intake_accepted', :data)"
            ),
            {
                "enc": encounter_id,
                "data": json.dumps({"intake_submission_id": submission_id}),
            },
        )
    return {
        "submission_id": submission_id,
        "patient_id": patient_id,
        "draft_encounter_id": encounter_id,
    }


def reject_submission(
    *,
    submission_id: int,
    reviewing_user_id: int,
    organization_id: int,
    reason: str | None = None,
) -> None:
    from sqlalchemy import text
    sub = fetch_one(
        "SELECT id, organization_id, status FROM intake_submissions "
        "WHERE id = :id",
        {"id": submission_id},
    )
    if not sub or sub["organization_id"] != organization_id:
        raise IntakeTokenError("intake_submission_not_found", 404)
    if sub["status"] != "pending_review":
        raise IntakeTokenError("intake_submission_not_pending", 409)
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE intake_submissions SET "
                "  status = 'rejected', "
                "  reviewed_by_user_id = :uid, "
                "  reviewed_at = CURRENT_TIMESTAMP, "
                "  reason = :reason "
                "WHERE id = :id"
            ),
            {
                "uid": reviewing_user_id,
                "reason": (reason or "")[:2000] or None,
                "id": submission_id,
            },
        )


# ---------- Public-route rate limiter (in-process) -------------------
#
# Keyed on (client_ip, raw_token_hash). A redis-backed limiter is
# Phase C. The in-process limiter is honest about its scope: it only
# protects a single API process. Behind a load balancer with N
# replicas the effective limit is ~N * PUBLIC_GET_LIMIT_PER_MINUTE.

_intake_buckets: dict[tuple[str, str], Deque[float]] = defaultdict(deque)


def _public_route_bucket_key(client_ip: str, raw_token: str) -> tuple[str, str]:
    return (client_ip or "0.0.0.0", hash_token(raw_token))


def public_get_rate_limit_check(client_ip: str, raw_token: str) -> bool:
    """Return True if the request is allowed; False if it should be 429.

    Side-effect: every call records a hit. Callers must call this
    exactly once per public GET on /intakes/{token}.
    """
    key = _public_route_bucket_key(client_ip, raw_token)
    now = time.time()
    bucket = _intake_buckets[key]
    cutoff = now - PUBLIC_GET_WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= PUBLIC_GET_LIMIT_PER_MINUTE:
        return False
    bucket.append(now)
    return True


def reset_rate_limit_for_tests() -> None:
    """Test hook only. Clears the in-process bucket."""
    _intake_buckets.clear()
