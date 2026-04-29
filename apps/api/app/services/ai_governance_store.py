"""Persistence layer for `AIGovernanceRecord`.

Raw SQL via `app.db`, dialect-portable. Cross-org reads are blocked at
the query layer — every read accepts an `organization_id` filter and
the routes pass the caller's org. There is no helper that lets a caller
bypass org scoping.

`security_events` is stored as a JSON-encoded string in a TEXT column
(see migration `e1f2a3041506`). Encoded on write, decoded on read.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.db import engine, fetch_one, insert_returning_id, transaction
from app.services.ai_governance import AIGovernanceRecord


_TABLE = "ai_governance_log"


def _serialize(record: AIGovernanceRecord) -> dict[str, Any]:
    return {
        "organization_id": record.organization_id,
        "provider": record.provider,
        "model_id": record.model_id,
        "use_case": record.use_case,
        "prompt_hash": record.prompt_hash,
        "output_hash": record.output_hash,
        "phi_redaction_status": record.phi_redaction_status,
        "human_review_required": bool(record.human_review_required),
        "human_review_status": record.human_review_status,
        "human_reviewer_id": record.human_reviewer_id,
        "human_review_timestamp": record.human_review_timestamp,
        "human_review_notes": record.human_review_notes,
        "security_events": json.dumps(record.security_events or []),
        "workflow_id": record.workflow_id,
        "user_id": record.user_id,
        "session_id": record.session_id,
        "patient_identifier": record.patient_identifier,
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
        "latency_ms": record.latency_ms,
    }


def _row_to_record(row: dict[str, Any]) -> AIGovernanceRecord:
    raw_events = row.get("security_events") or "[]"
    try:
        events = json.loads(raw_events) if isinstance(raw_events, str) else list(raw_events)
    except (ValueError, TypeError):
        events = []
    return AIGovernanceRecord(
        id=row.get("id"),
        created_at=row.get("created_at"),
        organization_id=row["organization_id"],
        provider=row.get("provider", "ibm_watsonx"),
        model_id=row.get("model_id", ""),
        use_case=row.get("use_case", "other"),
        prompt_hash=row.get("prompt_hash", ""),
        output_hash=row.get("output_hash", ""),
        phi_redaction_status=row.get("phi_redaction_status", "not_checked"),
        human_review_required=bool(row.get("human_review_required", True)),
        human_review_status=row.get("human_review_status", "pending"),
        human_reviewer_id=row.get("human_reviewer_id"),
        human_review_timestamp=row.get("human_review_timestamp"),
        human_review_notes=row.get("human_review_notes"),
        security_events=events,
        workflow_id=row.get("workflow_id"),
        user_id=row.get("user_id"),
        session_id=row.get("session_id"),
        patient_identifier=row.get("patient_identifier"),
        prompt_tokens=row.get("prompt_tokens"),
        completion_tokens=row.get("completion_tokens"),
        latency_ms=row.get("latency_ms"),
    )


def save_record(record: AIGovernanceRecord) -> int:
    """Insert a new governance row. Returns the new primary key."""
    values = _serialize(record)
    with transaction() as conn:
        new_id = insert_returning_id(conn, _TABLE, values)
    record.id = new_id
    return new_id


def get_record(record_id: int, *, organization_id: int) -> Optional[AIGovernanceRecord]:
    """Fetch one record, scoped to the caller's org. Returns None across orgs."""
    row = fetch_one(
        f"SELECT * FROM {_TABLE} "
        "WHERE id = :id AND organization_id = :org_id",
        {"id": record_id, "org_id": organization_id},
    )
    return _row_to_record(row) if row else None


def list_records(
    *,
    organization_id: int,
    since: datetime,
    review_status: Optional[str] = None,
    use_case: Optional[str] = None,
) -> list[AIGovernanceRecord]:
    """List records for an org since `since`. Cross-org rows excluded."""
    sql = (
        f"SELECT * FROM {_TABLE} "
        "WHERE organization_id = :org_id AND created_at >= :since"
    )
    params: dict[str, Any] = {"org_id": organization_id, "since": since}
    if review_status:
        sql += " AND human_review_status = :review_status"
        params["review_status"] = review_status
    if use_case:
        sql += " AND use_case = :use_case"
        params["use_case"] = use_case
    sql += " ORDER BY created_at DESC"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [_row_to_record(dict(r)) for r in rows]


def append_security_event_row(
    record_id: int,
    *,
    organization_id: int,
    event: dict[str, Any],
) -> Optional[AIGovernanceRecord]:
    """Append one event to a record's `security_events` list.

    Read-modify-write under a transaction. Cross-org access returns None
    without leaking row existence.
    """
    with transaction() as conn:
        row = conn.execute(
            text(
                f"SELECT * FROM {_TABLE} "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {"id": record_id, "org_id": organization_id},
        ).mappings().first()
        if not row:
            return None

        record = _row_to_record(dict(row))
        record.security_events.append(event)
        sev = event.get("severity")
        if sev in ("high", "critical"):
            record.human_review_required = True
            if record.human_review_status == "waived":
                record.human_review_status = "pending"

        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "security_events = :events, "
                "human_review_required = :req, "
                "human_review_status = :status "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {
                "events": json.dumps(record.security_events),
                "req": bool(record.human_review_required),
                "status": record.human_review_status,
                "id": record_id,
                "org_id": organization_id,
            },
        )
    return record


def update_review(
    record_id: int,
    *,
    organization_id: int,
    review_status: str,
    reviewer_id: int,
    notes: Optional[str] = None,
) -> Optional[AIGovernanceRecord]:
    """Set the human-review fields on a record. Org-scoped."""
    with transaction() as conn:
        row = conn.execute(
            text(
                f"SELECT id FROM {_TABLE} "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {"id": record_id, "org_id": organization_id},
        ).first()
        if not row:
            return None
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET "
                "human_review_status = :status, "
                "human_reviewer_id = :reviewer, "
                "human_review_timestamp = :ts, "
                "human_review_notes = :notes "
                "WHERE id = :id AND organization_id = :org_id"
            ),
            {
                "status": review_status,
                "reviewer": reviewer_id,
                "ts": datetime.now(timezone.utc),
                "notes": notes,
                "id": record_id,
                "org_id": organization_id,
            },
        )
    return get_record(record_id, organization_id=organization_id)
