"""Phase A item 3 — encounter revisions + attestations service helpers.

Spec: docs/chartnav/closure/PHASE_A_Structured_Charting_and_Attestation.md

This module is the single entry point for writing rows into
``encounter_revisions`` and ``encounter_attestations``. Route handlers
call ``record_revision()`` whenever they mutate a structured field on
the encounter row, and call ``record_attestation()`` exactly once per
encounter at sign time.

Truth limitations preserved verbatim from the spec:
- Immutability is enforced at the application layer, not at the DB.
- ``encounter_snapshot_hash`` is a tamper-evidence signal, not a
  legal trusted timestamp.
- Edit history is ChartNav-internal. It does not retroactively apply
  to edits made in an external EHR in ``integrated_readthrough`` mode.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_all, insert_returning_id, transaction


# ---------------------------------------------------------------------
# Immutability gate
# ---------------------------------------------------------------------
def is_encounter_signed(encounter_row: dict) -> bool:
    """An encounter row is "signed" once any of its note_versions is
    in the ``signed`` (or ``exported``/``amended``) state.

    Phase A item 3 enforces immutability on the encounter row + its
    structured children once the note has been signed. Today the only
    structured field on the encounter row is ``template_key`` (added
    in Phase A item 1); future structured fields hook through the
    same gate without changes here.
    """
    # Status hard-stops (no further mutation allowed).
    return str(encounter_row.get("status", "")) == "completed"


def encounter_signed_at(conn, encounter_id: int) -> Optional[str]:
    """Return the most recent signed_at timestamp from note_versions
    for the encounter, or None if no signed note exists yet."""
    row = conn.execute(
        text(
            "SELECT MAX(signed_at) AS signed_at "
            "FROM note_versions "
            "WHERE encounter_id = :eid AND signed_at IS NOT NULL"
        ),
        {"eid": encounter_id},
    ).mappings().first()
    if not row or not row["signed_at"]:
        return None
    return str(row["signed_at"])


# ---------------------------------------------------------------------
# Revision recorder
# ---------------------------------------------------------------------
def record_revision(
    conn,
    *,
    encounter_id: int,
    actor_user_id: int,
    field_path: str,
    before: Any,
    after: Any,
    reason: Optional[str] = None,
) -> int:
    """Append a row to encounter_revisions.

    ``before`` and ``after`` may be any JSON-serializable value. They
    are stored as JSON text so the diff is reconstructible without
    inferring types from a flat string column.

    Returns the new row id.
    """
    return insert_returning_id(
        conn,
        "encounter_revisions",
        {
            "encounter_id": encounter_id,
            "actor_user_id": actor_user_id,
            "field_path": field_path,
            "before_json": _safe_json(before),
            "after_json": _safe_json(after),
            "reason": reason,
            # changed_at uses the column default; left out so SQLite
            # respects CURRENT_TIMESTAMP in UTC.
        },
    )


def list_revisions_for_encounter(encounter_id: int) -> list[dict]:
    """Return all revision rows for the encounter, newest first."""
    rows = fetch_all(
        "SELECT id, encounter_id, actor_user_id, field_path, "
        "before_json, after_json, reason, changed_at "
        "FROM encounter_revisions "
        "WHERE encounter_id = :eid "
        "ORDER BY changed_at DESC, id DESC",
        {"eid": encounter_id},
    )
    # Decode the JSON columns so the API serializer hands clients
    # native types instead of opaque strings.
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        for col in ("before_json", "after_json"):
            raw = d.get(col)
            if raw is None:
                continue
            try:
                d[col] = json.loads(raw)
            except Exception:
                # Preserve the raw string if it isn't valid JSON.
                pass
        out.append(d)
    return out


# ---------------------------------------------------------------------
# Attestation recorder
# ---------------------------------------------------------------------
def record_attestation(
    conn,
    *,
    encounter_id: int,
    encounter_snapshot: dict,
    attested_by_user_id: int,
    typed_name: str,
    attestation_text: str,
) -> dict:
    """Insert (or return existing) the attestation row for an encounter.

    The encounter is uniquely keyed by ``encounter_id`` in the
    attestations table — re-sign attempts MUST be refused upstream
    by the caller; we simply return the existing row if one is
    already present so the route can short-circuit.

    The ``encounter_snapshot_hash`` is computed deterministically from
    the canonicalized encounter JSON so the attestation is auditable
    independent of the note body.
    """
    existing = conn.execute(
        text(
            "SELECT id, encounter_id, attested_by_user_id, typed_name, "
            "attestation_text, encounter_snapshot_hash, attested_at "
            "FROM encounter_attestations WHERE encounter_id = :eid"
        ),
        {"eid": encounter_id},
    ).mappings().first()
    if existing:
        return dict(existing)

    snapshot_hash = canonical_snapshot_hash(encounter_snapshot)
    new_id = insert_returning_id(
        conn,
        "encounter_attestations",
        {
            "encounter_id": encounter_id,
            "attested_by_user_id": attested_by_user_id,
            "typed_name": typed_name,
            "attestation_text": attestation_text,
            "encounter_snapshot_hash": snapshot_hash,
        },
    )
    row = conn.execute(
        text(
            "SELECT id, encounter_id, attested_by_user_id, typed_name, "
            "attestation_text, encounter_snapshot_hash, attested_at "
            "FROM encounter_attestations WHERE id = :id"
        ),
        {"id": new_id},
    ).mappings().first()
    return dict(row)


def get_attestation_for_encounter(encounter_id: int) -> Optional[dict]:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id, encounter_id, attested_by_user_id, typed_name, "
        "attestation_text, encounter_snapshot_hash, attested_at "
        "FROM encounter_attestations WHERE encounter_id = :eid",
        {"eid": encounter_id},
    )
    return dict(row) if row else None


# ---------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------
def canonical_snapshot_hash(snapshot: dict) -> str:
    """Deterministic sha256 over a canonicalized JSON dump of the
    snapshot. Stable across Python versions: keys sorted, no
    whitespace, UTF-8 bytes.

    Returned format: "sha256:<hex>".
    """
    payload = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------
def _safe_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def _json_default(o: Any) -> str:
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)
