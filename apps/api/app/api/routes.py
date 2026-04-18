from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter()

DB_PATH = Path(__file__).resolve().parents[2] / "chartnav.db"

# ----- State machine -----
#
# Forward flow:
#   scheduled -> in_progress -> draft_ready -> review_needed -> completed
#
# Rework flow (explicit, documented):
#   review_needed -> draft_ready      (reviewer kicks back for rewrite)
#   draft_ready   -> in_progress      (draft rejected, return to charting)
#
# All other transitions are rejected with 400 invalid_transition.
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


# ---------- Core / existing endpoints ----------

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "chartnav-api", "version": "0.1.0"}


@router.get("/organizations")
def list_organizations() -> list[dict]:
    return fetch_all(
        "SELECT id, name, slug, created_at FROM organizations ORDER BY id"
    )


@router.get("/locations")
def list_locations() -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, name, created_at FROM locations ORDER BY id"
    )


@router.get("/users")
def list_users() -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, email, full_name, role, created_at "
        "FROM users ORDER BY id"
    )


# ---------- Encounter endpoints ----------

ENCOUNTER_COLUMNS = (
    "id, organization_id, location_id, patient_identifier, patient_name, "
    "provider_name, status, scheduled_at, started_at, completed_at, created_at"
)


@router.get("/encounters")
def list_encounters(
    organization_id: Optional[int] = Query(default=None, ge=1),
    location_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[str] = Query(default=None),
    provider_name: Optional[str] = Query(default=None),
) -> list[dict]:
    clauses: list[str] = []
    params: list = []

    if organization_id is not None:
        clauses.append("organization_id = ?")
        params.append(organization_id)
    if location_id is not None:
        clauses.append("location_id = ?")
        params.append(location_id)
    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"invalid_status: must be one of {sorted(ALLOWED_STATUSES)}",
            )
        clauses.append("status = ?")
        params.append(status)
    if provider_name is not None:
        clauses.append("provider_name = ?")
        params.append(provider_name)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT {ENCOUNTER_COLUMNS} FROM encounters{where} ORDER BY id"
    return fetch_all(query, tuple(params))


@router.get("/encounters/{encounter_id}")
def get_encounter(encounter_id: int) -> dict:
    row = fetch_one(
        f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = ?",
        (encounter_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="encounter_not_found")
    return row


@router.get("/encounters/{encounter_id}/events")
def list_encounter_events(encounter_id: int) -> list[dict]:
    exists = fetch_one(
        "SELECT id FROM encounters WHERE id = ?", (encounter_id,)
    )
    if not exists:
        raise HTTPException(status_code=404, detail="encounter_not_found")
    rows = fetch_all(
        "SELECT id, encounter_id, event_type, event_data, created_at "
        "FROM workflow_events WHERE encounter_id = ? ORDER BY id",
        (encounter_id,),
    )
    return [_hydrate_event(r) for r in rows]


@router.post("/encounters", status_code=status.HTTP_201_CREATED)
def create_encounter(payload: EncounterCreate) -> dict:
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_status: must be one of {sorted(ALLOWED_STATUSES)}",
        )
    # New encounters must begin at 'scheduled' OR 'in_progress' (walk-in);
    # deeper states cannot be forged at creation time.
    if payload.status not in {"scheduled", "in_progress"}:
        raise HTTPException(
            status_code=400,
            detail="invalid_initial_status: new encounters must start at scheduled or in_progress",
        )

    conn = _connect()
    try:
        org = conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (payload.organization_id,),
        ).fetchone()
        if not org:
            raise HTTPException(status_code=400, detail="organization_not_found")
        loc = conn.execute(
            "SELECT id, organization_id FROM locations WHERE id = ?",
            (payload.location_id,),
        ).fetchone()
        if not loc:
            raise HTTPException(status_code=400, detail="location_not_found")
        if loc["organization_id"] != payload.organization_id:
            raise HTTPException(
                status_code=400, detail="location_does_not_belong_to_organization"
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
                payload.organization_id,
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
                json.dumps({"status": payload.status}, sort_keys=True),
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
def create_encounter_event(encounter_id: int, payload: EventCreate) -> dict:
    conn = _connect()
    try:
        exists = conn.execute(
            "SELECT id FROM encounters WHERE id = ?", (encounter_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="encounter_not_found")

        if payload.event_data is None:
            event_data_str: Optional[str] = None
        elif isinstance(payload.event_data, str):
            event_data_str = payload.event_data
        else:
            event_data_str = json.dumps(payload.event_data, sort_keys=True)

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
def update_encounter_status(encounter_id: int, payload: StatusUpdate) -> dict:
    new_status = payload.status
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_status: must be one of {sorted(ALLOWED_STATUSES)}",
        )

    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = ?",
            (encounter_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="encounter_not_found")

        previous_status = row["status"]

        # Idempotent no-op: same state in, same state out, no event recorded.
        if new_status == previous_status:
            return dict(row)

        allowed_next = ALLOWED_TRANSITIONS.get(previous_status, set())
        if new_status not in allowed_next:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"invalid_transition: {previous_status} -> {new_status} "
                    f"is not permitted; allowed next states from "
                    f"{previous_status}: {sorted(allowed_next) or 'none (terminal)'}"
                ),
            )

        started_at = row["started_at"]
        completed_at = row["completed_at"]
        now = _now_iso()

        if new_status == "in_progress" and not started_at:
            started_at = now
        if new_status == "completed":
            completed_at = now
            if not started_at:
                started_at = now

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
