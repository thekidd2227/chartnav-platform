from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import Caller, ensure_same_org, require_caller
from app.authz import (
    assert_can_transition,
    require_create_encounter,
    require_create_event,
)

router = APIRouter()

DB_PATH = Path(__file__).resolve().parents[2] / "chartnav.db"

# ----- State machine -----
ALLOWED_STATUSES: set[str] = {
    "scheduled",
    "in_progress",
    "draft_ready",
    "review_needed",
    "completed",
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"in_progress"},
    "in_progress": {"draft_ready"},
    "draft_ready": {"review_needed", "in_progress"},
    "review_needed": {"completed", "draft_ready"},
    "completed": set(),
}


# ---------- standardized errors ----------

def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


# ---------- DB helpers ----------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hydrate_event(row: dict) -> dict:
    data = row.get("event_data")
    if data:
        try:
            row["event_data"] = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass
    return row


ENCOUNTER_COLUMNS = (
    "id, organization_id, location_id, patient_identifier, patient_name, "
    "provider_name, status, scheduled_at, started_at, completed_at, created_at"
)


def _load_encounter_for_caller(encounter_id: int, caller: Caller) -> dict:
    """Fetch an encounter, or 404 — same response whether the encounter
    doesn't exist at all or belongs to another org. This prevents
    cross-org existence probing."""
    row = fetch_one(
        f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = ?",
        (encounter_id,),
    )
    if not row or row["organization_id"] != caller.organization_id:
        raise _err("encounter_not_found", "no such encounter in your organization", 404)
    return row


# ---------- Pydantic models ----------

class EncounterCreate(BaseModel):
    organization_id: int
    location_id: int
    patient_identifier: str = Field(..., min_length=1, max_length=255)
    patient_name: Optional[str] = Field(default=None, max_length=255)
    provider_name: str = Field(..., min_length=1, max_length=255)
    scheduled_at: Optional[datetime] = None
    status: str = "scheduled"


class EventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)
    event_data: Optional[Any] = None


class StatusUpdate(BaseModel):
    status: str


# ---------- Open endpoints ----------

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "chartnav-api", "version": "0.1.0"}


# ---------- Identity ----------

@router.get("/me")
def me(caller: Caller = Depends(require_caller)) -> dict:
    return {
        "user_id": caller.user_id,
        "email": caller.email,
        "full_name": caller.full_name,
        "role": caller.role,
        "organization_id": caller.organization_id,
    }


# ---------- Org metadata (now org-scoped, all roles) ----------

@router.get("/organizations")
def list_organizations(caller: Caller = Depends(require_caller)) -> list[dict]:
    # Caller only ever sees their own org.
    return fetch_all(
        "SELECT id, name, slug, created_at FROM organizations "
        "WHERE id = ? ORDER BY id",
        (caller.organization_id,),
    )


@router.get("/locations")
def list_locations(caller: Caller = Depends(require_caller)) -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, name, created_at FROM locations "
        "WHERE organization_id = ? ORDER BY id",
        (caller.organization_id,),
    )


@router.get("/users")
def list_users(caller: Caller = Depends(require_caller)) -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, email, full_name, role, created_at "
        "FROM users WHERE organization_id = ? ORDER BY id",
        (caller.organization_id,),
    )


# ---------- Encounters (authed + org-scoped + RBAC) ----------

@router.get("/encounters")
def list_encounters(
    caller: Caller = Depends(require_caller),
    organization_id: Optional[int] = Query(default=None, ge=1),
    location_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[str] = Query(default=None),
    provider_name: Optional[str] = Query(default=None),
) -> list[dict]:
    if organization_id is not None and organization_id != caller.organization_id:
        raise _err(
            "cross_org_access_forbidden",
            "requested organization does not match caller's organization",
            403,
        )

    clauses: list[str] = ["organization_id = ?"]
    params: list = [caller.organization_id]

    if location_id is not None:
        clauses.append("location_id = ?")
        params.append(location_id)
    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise _err(
                "invalid_status",
                f"must be one of {sorted(ALLOWED_STATUSES)}",
                400,
            )
        clauses.append("status = ?")
        params.append(status)
    if provider_name is not None:
        clauses.append("provider_name = ?")
        params.append(provider_name)

    where = f" WHERE {' AND '.join(clauses)}"
    query = f"SELECT {ENCOUNTER_COLUMNS} FROM encounters{where} ORDER BY id"
    return fetch_all(query, tuple(params))


@router.get("/encounters/{encounter_id}")
def get_encounter(
    encounter_id: int, caller: Caller = Depends(require_caller)
) -> dict:
    return _load_encounter_for_caller(encounter_id, caller)


@router.get("/encounters/{encounter_id}/events")
def list_encounter_events(
    encounter_id: int, caller: Caller = Depends(require_caller)
) -> list[dict]:
    _load_encounter_for_caller(encounter_id, caller)
    rows = fetch_all(
        "SELECT id, encounter_id, event_type, event_data, created_at "
        "FROM workflow_events WHERE encounter_id = ? ORDER BY id",
        (encounter_id,),
    )
    return [_hydrate_event(r) for r in rows]


@router.post("/encounters", status_code=status.HTTP_201_CREATED)
def create_encounter(
    payload: EncounterCreate,
    caller: Caller = Depends(require_create_encounter),
) -> dict:
    if payload.status not in ALLOWED_STATUSES:
        raise _err(
            "invalid_status",
            f"must be one of {sorted(ALLOWED_STATUSES)}",
            400,
        )
    if payload.status not in {"scheduled", "in_progress"}:
        raise _err(
            "invalid_initial_status",
            "new encounters must start at scheduled or in_progress",
            400,
        )

    ensure_same_org(caller, payload.organization_id)

    conn = _connect()
    try:
        loc = conn.execute(
            "SELECT id, organization_id FROM locations WHERE id = ?",
            (payload.location_id,),
        ).fetchone()
        if not loc:
            raise _err("location_not_found", "no such location", 400)
        if loc["organization_id"] != caller.organization_id:
            raise _err(
                "cross_org_access_forbidden",
                "location does not belong to caller's organization",
                403,
            )

        started_at = _now_iso() if payload.status == "in_progress" else None

        cur = conn.execute(
            """
            INSERT INTO encounters (
                organization_id, location_id, patient_identifier, patient_name,
                provider_name, status, scheduled_at, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                caller.organization_id,
                payload.location_id,
                payload.patient_identifier,
                payload.patient_name,
                payload.provider_name,
                payload.status,
                payload.scheduled_at.isoformat() if payload.scheduled_at else None,
                started_at,
                None,
            ),
        )
        new_id = cur.lastrowid

        conn.execute(
            "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
            "VALUES (?, ?, ?)",
            (
                new_id,
                "encounter_created",
                json.dumps(
                    {"status": payload.status, "created_by": caller.email},
                    sort_keys=True,
                ),
            ),
        )
        conn.commit()

        row = conn.execute(
            f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = ?",
            (new_id,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.post(
    "/encounters/{encounter_id}/events", status_code=status.HTTP_201_CREATED
)
def create_encounter_event(
    encounter_id: int,
    payload: EventCreate,
    caller: Caller = Depends(require_create_event),
) -> dict:
    _load_encounter_for_caller(encounter_id, caller)

    if payload.event_data is None:
        event_data_str: Optional[str] = None
    elif isinstance(payload.event_data, str):
        event_data_str = payload.event_data
    else:
        event_data_str = json.dumps(payload.event_data, sort_keys=True)

    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
            "VALUES (?, ?, ?)",
            (encounter_id, payload.event_type, event_data_str),
        )
        new_id = cur.lastrowid
        conn.commit()

        row = conn.execute(
            "SELECT id, encounter_id, event_type, event_data, created_at "
            "FROM workflow_events WHERE id = ?",
            (new_id,),
        ).fetchone()
        return _hydrate_event(dict(row))
    finally:
        conn.close()


@router.post("/encounters/{encounter_id}/status")
def update_encounter_status(
    encounter_id: int,
    payload: StatusUpdate,
    caller: Caller = Depends(require_caller),
) -> dict:
    new_status = payload.status
    if new_status not in ALLOWED_STATUSES:
        raise _err(
            "invalid_status",
            f"must be one of {sorted(ALLOWED_STATUSES)}",
            400,
        )

    row = _load_encounter_for_caller(encounter_id, caller)
    previous_status = row["status"]

    # same-state = no-op (still 200 OK)
    if new_status == previous_status:
        return row

    allowed_next = ALLOWED_TRANSITIONS.get(previous_status, set())
    if new_status not in allowed_next:
        raise _err(
            "invalid_transition",
            (
                f"{previous_status} -> {new_status} is not permitted; "
                f"allowed next states from {previous_status}: "
                f"{sorted(allowed_next) or 'none (terminal)'}"
            ),
            400,
        )

    # RBAC gate: caller's role must cover this specific edge.
    assert_can_transition(caller, previous_status, new_status)

    started_at = row["started_at"]
    completed_at = row["completed_at"]
    now = _now_iso()

    if new_status == "in_progress" and not started_at:
        started_at = now
    if new_status == "completed":
        completed_at = now
        if not started_at:
            started_at = now

    conn = _connect()
    try:
        conn.execute(
            "UPDATE encounters SET status = ?, started_at = ?, completed_at = ? "
            "WHERE id = ?",
            (new_status, started_at, completed_at, encounter_id),
        )
        conn.execute(
            "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
            "VALUES (?, ?, ?)",
            (
                encounter_id,
                "status_changed",
                json.dumps(
                    {
                        "old_status": previous_status,
                        "new_status": new_status,
                        "changed_by": caller.email,
                    },
                    sort_keys=True,
                ),
            ),
        )
        conn.commit()

        updated = conn.execute(
            f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = ?",
            (encounter_id,),
        ).fetchone()
        return dict(updated)
    finally:
        conn.close()
