"""Phase 83 — Note Validation Acknowledgement persistence service.

Persists provider acknowledgement of Phase 82 note-validation warnings
to ``security_audit_events`` as metadata-only audit rows. The audit
trail is append-only by design; new acknowledgements add new rows,
the most recent row per ``(encounter, validation_item_id, actor)``
serves as the "currently acknowledged" record.

Hard rule (matching every Phase 1+2 surface): the audit ``detail``
column carries only metadata fields encoded as JSON — no clinical
free text, no findings, no diagnosis language. The acknowledgement
payload deliberately accepts no free-text fields.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.audit import record as audit_record
from app.auth import Caller
from app.db import engine


VALID_ACK_TYPES = frozenset({"acknowledged", "rescinded"})
EVENT_TYPE = "note_validation_acknowledged"


@dataclass
class AckError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encounter_or_404(conn, encounter_id: int, org_id: int) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": org_id},
    ).fetchone()
    if row is None:
        raise AckError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    eid, oid, pid = row
    return {"id": int(eid), "organization_id": int(oid), "patient_id": pid}


def _actor_profile(conn, user_id: int) -> dict[str, str | None]:
    row = conn.execute(
        sa_text("SELECT full_name, email, role FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    if row is None:
        return {"display_name": None, "email": None, "role": None}
    full_name, email, role = row
    return {
        "display_name": full_name or email,
        "email": email,
        "role": role,
    }


def _validate_check_id(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise AckError(
            "invalid_check_id",
            "validation_item_id must be a non-empty string",
            422,
        )
    if len(value) > 120:
        raise AckError(
            "invalid_check_id",
            "validation_item_id must be at most 120 characters",
            422,
        )
    # Only ASCII letters / digits / : / _ / -
    for ch in value:
        if not (ch.isalnum() or ch in (":", "_", "-", ".")):
            raise AckError(
                "invalid_check_id",
                "validation_item_id contains an unsupported character",
                422,
            )
    return value


def _validate_category(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise AckError(
            "invalid_category",
            "validation_category must be a non-empty string",
            422,
        )
    if len(value) > 60:
        raise AckError(
            "invalid_category",
            "validation_category must be at most 60 characters",
            422,
        )
    for ch in value:
        if not (ch.isalnum() or ch in ("_", "-")):
            raise AckError(
                "invalid_category",
                "validation_category contains an unsupported character",
                422,
            )
    return value


def _validate_ack_type(value: Any) -> str:
    if value not in VALID_ACK_TYPES:
        raise AckError(
            "invalid_ack_type",
            f"acknowledgement_type must be one of {sorted(VALID_ACK_TYPES)}",
            422,
        )
    return value


def _detail_payload(
    *,
    encounter_id: int,
    validation_item_id: str,
    validation_category: str,
    acknowledgement_type: str,
    actor_id: int,
    actor_display_name: str | None,
    actor_role: str | None,
    timestamp: str,
) -> str:
    return json.dumps(
        {
            "encounter_id": encounter_id,
            "validation_item_id": validation_item_id,
            "validation_category": validation_category,
            "acknowledgement_type": acknowledgement_type,
            "actor_id": actor_id,
            "actor_display_name": actor_display_name,
            "actor_role": actor_role,
            "acknowledgement_timestamp": timestamp,
        },
        sort_keys=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_acknowledgement(
    encounter_id: int,
    caller: Caller,
    payload: dict[str, Any],
    *,
    request_id: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Record a provider acknowledgement of one validation warning."""
    item_id = _validate_check_id(payload.get("validation_item_id"))
    category = _validate_category(payload.get("validation_category"))
    ack_type = _validate_ack_type(
        payload.get("acknowledgement_type", "acknowledged")
    )

    # Reject any unexpected free-text keys defensively.
    forbidden_keys = {
        "note", "notes", "detail", "details", "finding", "findings",
        "diagnosis", "text", "comment", "comments", "body", "message",
    }
    extra = set(payload.keys()) - {
        "validation_item_id",
        "validation_category",
        "acknowledgement_type",
    }
    intersecting = extra & forbidden_keys
    if intersecting:
        raise AckError(
            "forbidden_payload_field",
            (
                "acknowledgement payload must not include free-text "
                f"fields: {sorted(intersecting)}"
            ),
            422,
        )

    with engine.connect() as conn:
        encounter = _encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        profile = _actor_profile(conn, caller.user_id)

    now = datetime.now(timezone.utc).isoformat()
    detail = _detail_payload(
        encounter_id=encounter["id"],
        validation_item_id=item_id,
        validation_category=category,
        acknowledgement_type=ack_type,
        actor_id=caller.user_id,
        actor_display_name=profile["display_name"],
        actor_role=profile["role"],
        timestamp=now,
    )

    audit_record(
        event_type=EVENT_TYPE,
        request_id=request_id,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=path,
        method="POST",
        detail=detail,
    )

    # Fetch the row we just wrote (most recent row matching our metadata).
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, created_at FROM security_audit_events "
                "WHERE event_type = :et AND organization_id = :oid "
                "AND actor_user_id = :auid AND detail = :detail "
                "ORDER BY id DESC LIMIT 1"
            ),
            {
                "et": EVENT_TYPE,
                "oid": caller.organization_id,
                "auid": caller.user_id,
                "detail": detail,
            },
        ).fetchone()

    return _build_ack_dto(row, detail) if row else _build_ack_dto(None, detail)


def list_acknowledgements(
    encounter_id: int, caller: Caller
) -> list[dict[str, Any]]:
    """Return chronological (newest-first) acknowledgements for one encounter."""
    with engine.connect() as conn:
        _encounter_or_404(conn, encounter_id, caller.organization_id)
        rows = conn.execute(
            sa_text(
                "SELECT id, created_at, detail "
                "FROM security_audit_events "
                "WHERE event_type = :et AND organization_id = :oid "
                "ORDER BY id DESC"
            ),
            {"et": EVENT_TYPE, "oid": caller.organization_id},
        ).fetchall()

    out: list[dict[str, Any]] = []
    for rid, created_at, raw_detail in rows:
        ack = _build_ack_dto((rid, created_at), raw_detail)
        if ack and ack["encounter_id"] == encounter_id:
            out.append(ack)
    return out


def list_for_summary_timeline(
    encounter_id: int, organization_id: int
) -> list[dict[str, Any]]:
    """Return ack rows shaped for the retina-visit-summary evidence timeline."""
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT id, created_at, detail "
                "FROM security_audit_events "
                "WHERE event_type = :et AND organization_id = :oid "
                "ORDER BY id ASC"
            ),
            {"et": EVENT_TYPE, "oid": organization_id},
        ).fetchall()
    out: list[dict[str, Any]] = []
    for rid, created_at, raw_detail in rows:
        ack = _build_ack_dto((rid, created_at), raw_detail)
        if ack and ack["encounter_id"] == encounter_id:
            out.append(
                {
                    "artifact_type": "note_validation",
                    "event_type": "acknowledged",
                    "ref_id": ack["id"],
                    "timestamp": ack["acknowledgement_timestamp"],
                    "actor_display_name": ack["actor_display_name"],
                    "actor_role": ack["actor_role"],
                    "validation_item_id": ack["validation_item_id"],
                    "validation_category": ack["validation_category"],
                    "acknowledgement_type": ack["acknowledgement_type"],
                }
            )
    return out


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_ack_dto(
    row: tuple[Any, Any] | None, detail: str | None
) -> dict[str, Any] | None:
    if detail is None:
        return None
    try:
        meta = json.loads(detail)
    except (ValueError, TypeError):
        return None
    rid: Any = None
    created_at: Any = None
    if row is not None:
        rid, created_at = row
    return {
        "id": int(rid) if rid is not None else None,
        "audit_created_at": str(created_at) if created_at is not None else None,
        "encounter_id": int(meta.get("encounter_id"))
        if meta.get("encounter_id") is not None
        else None,
        "organization_id": None,  # callers receive this via path scoping
        "actor_id": int(meta.get("actor_id"))
        if meta.get("actor_id") is not None
        else None,
        "actor_display_name": meta.get("actor_display_name"),
        "actor_role": meta.get("actor_role"),
        "validation_item_id": meta.get("validation_item_id"),
        "validation_category": meta.get("validation_category"),
        "acknowledgement_type": meta.get("acknowledgement_type"),
        "acknowledgement_timestamp": meta.get("acknowledgement_timestamp"),
    }


__all__ = [
    "AckError",
    "EVENT_TYPE",
    "VALID_ACK_TYPES",
    "create_acknowledgement",
    "list_acknowledgements",
    "list_for_summary_timeline",
]
