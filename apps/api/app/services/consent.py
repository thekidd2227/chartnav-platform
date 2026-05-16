"""Phase 25A — audio-consent service.

Encounter-level patient consent for audio recording. The intake /
upload pipeline must check `is_consent_granted(encounter_id)`
before accepting audio bytes. Microphone permission is *not*
patient consent — the patient's consent is captured by clinic
staff and logged here.

Statuses
--------
- ``granted``       — consent captured and currently valid
- ``declined``      — patient declined; recording stays blocked
- ``revoked``       — was granted, now withdrawn; recording blocks
- ``not_recorded``  — no consent has been captured yet (default)

Methods
-------
- ``verbal``    — staff confirmed verbal consent
- ``written``   — written acknowledgement on file
- ``demo_fake`` — demo-mode placeholder; never permitted for real PHI
- ``unknown``   — operator captured consent without specifying method

PHI policy
----------
No PHI is persisted in this table. ``note`` is an operator-facing
label (e.g. "verbal consent obtained at intake"). The structured
columns hold only operational metadata.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text

from app.audit import record as emit_security_audit_event
from app.db import transaction, is_sqlite


# ---------------------------------------------------------------
# Idempotent table creation
# ---------------------------------------------------------------
# Phase 25A bootstraps the consent table at service-startup instead
# of via an alembic migration because main currently carries two
# unmerged alembic heads and adding a third would compound the mess.
# The schema below is cross-dialect (SQLite + Postgres) using the
# same portable patterns app.db already enforces.

_TABLE_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS encounter_audio_consent (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id    INTEGER NOT NULL UNIQUE REFERENCES encounters(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    status          VARCHAR(32) NOT NULL,
    actor_user_id   INTEGER         REFERENCES users(id),
    method          VARCHAR(32) NOT NULL,
    note            TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_TABLE_DDL_PG = """
CREATE TABLE IF NOT EXISTS encounter_audio_consent (
    id              SERIAL PRIMARY KEY,
    encounter_id    INTEGER NOT NULL UNIQUE REFERENCES encounters(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    status          VARCHAR(32) NOT NULL,
    actor_user_id   INTEGER         REFERENCES users(id),
    method          VARCHAR(32) NOT NULL,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS ix_encounter_audio_consent_org_status "
    "ON encounter_audio_consent (organization_id, status)"
)

_ensured: bool = False


def ensure_table() -> None:
    """Idempotent table + index creation. Safe to call repeatedly."""
    global _ensured
    if _ensured:
        return
    with transaction() as conn:
        ddl = _TABLE_DDL_SQLITE if is_sqlite() else _TABLE_DDL_PG
        conn.execute(text(ddl))
        conn.execute(text(_INDEX_DDL))
    _ensured = True


# ---------------------------------------------------------------
# Constants
# ---------------------------------------------------------------

STATUS_GRANTED = "granted"
STATUS_DECLINED = "declined"
STATUS_REVOKED = "revoked"
STATUS_NOT_RECORDED = "not_recorded"

KNOWN_STATUSES: frozenset[str] = frozenset({
    STATUS_GRANTED, STATUS_DECLINED, STATUS_REVOKED, STATUS_NOT_RECORDED,
})

METHOD_VERBAL = "verbal"
METHOD_WRITTEN = "written"
METHOD_DEMO_FAKE = "demo_fake"
METHOD_UNKNOWN = "unknown"

KNOWN_METHODS: frozenset[str] = frozenset({
    METHOD_VERBAL, METHOD_WRITTEN, METHOD_DEMO_FAKE, METHOD_UNKNOWN,
})

# Statuses that permit recording. Anything else BLOCKS the upload pipeline.
PERMITTED_STATUSES: frozenset[str] = frozenset({STATUS_GRANTED})


# ---------------------------------------------------------------
# Errors
# ---------------------------------------------------------------

class ConsentError(RuntimeError):
    """Raised when consent operations fail."""
    def __init__(self, error_code: str, reason: str):
        super().__init__(reason)
        self.error_code = error_code
        self.reason = reason


# ---------------------------------------------------------------
# Read model
# ---------------------------------------------------------------

@dataclass(frozen=True)
class ConsentRecord:
    encounter_id: int
    organization_id: int
    status: str
    method: str
    actor_user_id: Optional[int]
    note: Optional[str]
    created_at: _dt.datetime
    updated_at: _dt.datetime

    def is_recording_permitted(self) -> bool:
        return self.status in PERMITTED_STATUSES


def _coerce_dt(value) -> _dt.datetime:
    """SQLite returns TIMESTAMP columns as strings; Postgres returns
    datetimes. Normalize to an aware UTC datetime in both cases."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=_dt.timezone.utc)
        return value
    # SQLite ISO8601 string.
    s = str(value)
    try:
        dt = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        # Fall back to a permissive parse for "YYYY-MM-DD HH:MM:SS" form.
        dt = _dt.datetime.strptime(s.split(".")[0], "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt


def _row_to_record(row: dict) -> ConsentRecord:
    return ConsentRecord(
        encounter_id=row["encounter_id"],
        organization_id=row["organization_id"],
        status=row["status"],
        method=row["method"],
        actor_user_id=row.get("actor_user_id"),
        note=row.get("note"),
        created_at=_coerce_dt(row["created_at"]),
        updated_at=_coerce_dt(row["updated_at"]),
    )


# ---------------------------------------------------------------
# Public API
# ---------------------------------------------------------------

def get_consent(encounter_id: int, organization_id: int) -> ConsentRecord:
    """Return the consent record for an encounter, or a synthesized
    ``not_recorded`` record if none exists yet. Always organization-
    scoped: callers must pass the requesting user's organization_id
    so we can prove org-isolation at the service boundary."""
    ensure_table()
    with transaction() as conn:
        row = conn.execute(
            text(
                "SELECT encounter_id, organization_id, status, method, "
                "actor_user_id, note, created_at, updated_at "
                "FROM encounter_audio_consent "
                "WHERE encounter_id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).mappings().first()
    if row is None:
        now = _dt.datetime.now(_dt.timezone.utc)
        return ConsentRecord(
            encounter_id=encounter_id,
            organization_id=organization_id,
            status=STATUS_NOT_RECORDED,
            method=METHOD_UNKNOWN,
            actor_user_id=None,
            note=None,
            created_at=now,
            updated_at=now,
        )
    return _row_to_record(dict(row))


def is_consent_granted(encounter_id: int, organization_id: int) -> bool:
    """Convenience helper used by the audio upload pipeline.
    Returns True only if a stored record has status=granted."""
    return get_consent(encounter_id, organization_id).is_recording_permitted()


def set_consent(
    *,
    encounter_id: int,
    organization_id: int,
    status: str,
    method: str,
    actor_user_id: Optional[int],
    actor_email: Optional[str],
    note: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ConsentRecord:
    """Upsert the consent record for an encounter.

    Validates status + method against known sets. Emits a
    `audio_consent_updated` security audit event with no PHI.
    """
    if status not in KNOWN_STATUSES:
        raise ConsentError("invalid_status", f"unknown status: {status!r}")
    if method not in KNOWN_METHODS:
        raise ConsentError("invalid_method", f"unknown method: {method!r}")
    if note is not None:
        note = note.strip()
        if len(note) > 500:
            raise ConsentError("note_too_long", "note must be 500 chars or fewer")
        if not note:
            note = None

    ensure_table()
    now = _dt.datetime.now(_dt.timezone.utc)
    with transaction() as conn:
        # Verify the encounter actually belongs to this org. Returning
        # 404 (caller-translated) here is what gives us cross-org
        # no-existence-leak: a requester from org B asking about an
        # encounter in org A sees the same response as if the encounter
        # did not exist at all.
        owner = conn.execute(
            text("SELECT organization_id FROM encounters WHERE id = :eid"),
            {"eid": encounter_id},
        ).mappings().first()
        if owner is None or owner["organization_id"] != organization_id:
            raise ConsentError("not_found", "encounter not found in this organization")
        # Upsert.
        existing = conn.execute(
            text(
                "SELECT id FROM encounter_audio_consent "
                "WHERE encounter_id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).mappings().first()
        if existing is None:
            conn.execute(
                text(
                    "INSERT INTO encounter_audio_consent ("
                    "encounter_id, organization_id, status, method, "
                    "actor_user_id, note, created_at, updated_at"
                    ") VALUES ("
                    ":eid, :oid, :status, :method, :uid, :note, :now, :now"
                    ")"
                ),
                {
                    "eid": encounter_id, "oid": organization_id,
                    "status": status, "method": method,
                    "uid": actor_user_id, "note": note, "now": now,
                },
            )
        else:
            conn.execute(
                text(
                    "UPDATE encounter_audio_consent SET "
                    "status = :status, method = :method, "
                    "actor_user_id = :uid, note = :note, updated_at = :now "
                    "WHERE encounter_id = :eid AND organization_id = :oid"
                ),
                {
                    "status": status, "method": method, "uid": actor_user_id,
                    "note": note, "now": now,
                    "eid": encounter_id, "oid": organization_id,
                },
            )

    # Audit event AFTER the commit. Detail intentionally carries only
    # the structured columns (no PHI).
    emit_security_audit_event(
        event_type="audio_consent_updated",
        request_id=request_id,
        actor_email=actor_email,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        path=f"/encounters/{encounter_id}/audio-consent",
        method="PUT",
        error_code=None,
        detail=f"status={status} method={method}",
        remote_addr=None,
    )

    return get_consent(encounter_id, organization_id)
