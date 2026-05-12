"""Phase 22 — Multi-clinic / multi-provider scaling endpoints.

Read + admin-write surface for the four tables added by
``a8b9c0d1e2f3_phase_22_multi_clinic_scaling``:

  * ``provider_location_assignments``
  * ``location_rooms``
  * ``provider_schedule_blocks``
  * ``clinic_operating_hours``

Plus three dashboard summary endpoints:

  * ``GET /locations/{id}/dashboard``
  * ``GET /providers/{id}/dashboard``
  * ``GET /admin/multi-clinic-summary``  (admin only)

Permission model
----------------

  * **admin**       — full read + write across all four resources +
                      admin multi-clinic summary.
  * **clinician / reviewer / technician / front_desk** — read across
                      all four resources + their own location /
                      provider dashboards. (Read is broad because
                      schedule and room metadata is operational, not
                      clinical.)
  * Writes (create / patch) are **admin-only**.

Audit
-----
Every create / patch records a metadata-only audit row. ``detail``
contains only IDs, type / status / day-of-week / capacity values.
Names, opens_at / closes_at strings, and any free-text fields are
not serialized into audit detail.

Cross-org safety
----------------
Patients, providers, locations, rooms, schedule blocks, hours rows,
and assignments are resolved via dedicated ``_resolve_*_in_org``
helpers. Cross-org reads / writes return ``404`` (not ``403``)
preserving the no-existence-leak invariant.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_all, fetch_one, insert_returning_id, transaction


router = APIRouter()


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

_ROOM_TYPES = {"exam", "imaging", "testing", "procedure", "admin", "other"}
_BLOCK_TYPES = {
    "clinic",
    "surgery",
    "injection",
    "testing",
    "admin",
    "unavailable",
    "other",
}
_DAYS = set(range(7))  # 0..6

_ROLE_ADMIN = "admin"
_ROLE_CLINICIAN = "clinician"
_ROLE_REVIEWER = "reviewer"
_ROLE_TECHNICIAN = "technician"
_ROLE_FRONT_DESK = "front_desk"

_READ_ROLES = {
    _ROLE_ADMIN,
    _ROLE_CLINICIAN,
    _ROLE_REVIEWER,
    _ROLE_TECHNICIAN,
    _ROLE_FRONT_DESK,
}
_WRITE_ROLES = {_ROLE_ADMIN}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_read(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err(
            "multi_clinic_role_forbidden",
            f"role {caller.role!r} cannot read multi-clinic resources",
            403,
        )


def _require_write(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err(
            "multi_clinic_role_forbidden",
            f"role {caller.role!r} cannot modify multi-clinic resources; "
            "requires admin",
            403,
        )


def _resolve_provider_in_org(provider_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM providers WHERE id = :id AND organization_id = :org",
        {"id": provider_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "provider_not_found",
            "provider not found in your organization",
            404,
        )
    return int(row["id"])


def _resolve_location_in_org(location_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM locations WHERE id = :id AND organization_id = :org",
        {"id": location_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "location_not_found",
            "location not found in your organization",
            404,
        )
    return int(row["id"])


def _resolve_assignment_in_org(assignment_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM provider_location_assignments "
        "WHERE id = :id AND organization_id = :org",
        {"id": assignment_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "assignment_not_found",
            "assignment not found in your organization",
            404,
        )
    return row


def _resolve_room_in_org(room_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM location_rooms "
        "WHERE id = :id AND organization_id = :org",
        {"id": room_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "room_not_found",
            "room not found in your organization",
            404,
        )
    return row


def _resolve_block_in_org(block_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM provider_schedule_blocks "
        "WHERE id = :id AND organization_id = :org",
        {"id": block_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "schedule_block_not_found",
            "schedule block not found in your organization",
            404,
        )
    return row


def _resolve_hours_in_org(hours_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM clinic_operating_hours "
        "WHERE id = :id AND organization_id = :org",
        {"id": hours_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "operating_hours_not_found",
            "operating hours row not found in your organization",
            404,
        )
    return row


def _validate_room_type(value: str) -> str:
    if value not in _ROOM_TYPES:
        raise _err(
            "invalid_room_type",
            f"room_type must be one of {sorted(_ROOM_TYPES)}",
            400,
        )
    return value


def _validate_block_type(value: str) -> str:
    if value not in _BLOCK_TYPES:
        raise _err(
            "invalid_block_type",
            f"block_type must be one of {sorted(_BLOCK_TYPES)}",
            400,
        )
    return value


def _validate_day_of_week(value: int) -> int:
    if value not in _DAYS:
        raise _err(
            "invalid_day_of_week",
            "day_of_week must be 0..6",
            400,
        )
    return value


def _validate_time_range(start_at: str, end_at: str) -> None:
    # The DB CHECK enforces start_at < end_at, but the layer above
    # also rejects with a 400 before hitting the DB so the error
    # envelope is the same shape as the other validations.
    if not start_at or not end_at:
        raise _err(
            "invalid_time_range",
            "start_at and end_at are required",
            400,
        )
    if start_at >= end_at:
        raise _err(
            "invalid_time_range",
            "start_at must be before end_at",
            400,
        )


def _row_to_dict(row: dict) -> dict:
    out: dict[str, Any] = {}
    for k, v in row.items():
        out[k] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


def _audit(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    detail: str,
) -> None:
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


# ---------------------------------------------------------------------
# Pydantic shapes
# ---------------------------------------------------------------------


class AssignmentCreate(BaseModel):
    provider_id: int
    location_id: int
    is_primary: bool = False
    is_active: bool = True


class AssignmentUpdate(BaseModel):
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    room_type: str = Field(..., min_length=1, max_length=32)
    is_active: bool = True


class RoomUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    room_type: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


class ScheduleBlockCreate(BaseModel):
    provider_id: int
    location_id: int
    start_at: str
    end_at: str
    block_type: str = Field(..., min_length=1, max_length=32)
    capacity: Optional[int] = Field(default=None, ge=0)


class ScheduleBlockUpdate(BaseModel):
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    block_type: Optional[str] = Field(default=None, max_length=32)
    capacity: Optional[int] = Field(default=None, ge=0)


class OperatingHoursCreate(BaseModel):
    location_id: int
    day_of_week: int = Field(..., ge=0, le=6)
    opens_at: Optional[str] = Field(default=None, max_length=8)
    closes_at: Optional[str] = Field(default=None, max_length=8)
    is_closed: bool = False


class OperatingHoursUpdate(BaseModel):
    opens_at: Optional[str] = Field(default=None, max_length=8)
    closes_at: Optional[str] = Field(default=None, max_length=8)
    is_closed: Optional[bool] = None


# ---------------------------------------------------------------------
# Provider-location assignments
# ---------------------------------------------------------------------


@router.get("/provider-location-assignments")
def list_assignments(
    request: Request,
    caller: Caller = Depends(require_caller),
    provider_id: Optional[int] = Query(default=None),
    location_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
) -> dict[str, Any]:
    _require_read(caller)
    sql = (
        "SELECT * FROM provider_location_assignments "
        "WHERE organization_id = :org"
    )
    params: dict[str, Any] = {"org": caller.organization_id}
    if provider_id is not None:
        sql += " AND provider_id = :provider_id"
        params["provider_id"] = provider_id
    if location_id is not None:
        sql += " AND location_id = :location_id"
        params["location_id"] = location_id
    if is_active is not None:
        sql += " AND is_active = :is_active"
        params["is_active"] = is_active
    sql += " ORDER BY id DESC"
    rows = fetch_all(sql, params)
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/provider-location-assignments",
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: AssignmentCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    pid = _resolve_provider_in_org(payload.provider_id, caller)
    lid = _resolve_location_in_org(payload.location_id, caller)

    existing = fetch_one(
        "SELECT * FROM provider_location_assignments "
        "WHERE organization_id = :org AND provider_id = :pid "
        "AND location_id = :lid",
        {"org": caller.organization_id, "pid": pid, "lid": lid},
    )
    if existing:
        return _row_to_dict(existing)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "provider_location_assignments",
            {
                "organization_id": caller.organization_id,
                "provider_id": pid,
                "location_id": lid,
                "is_primary": payload.is_primary,
                "is_active": payload.is_active,
            },
        )
        row = conn.execute(
            text(
                "SELECT * FROM provider_location_assignments "
                "WHERE id = :id"
            ),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="provider_location_assignment_created",
        detail=(
            f"assignment_id={new_id} provider_id={pid} location_id={lid} "
            f"is_primary={payload.is_primary} is_active={payload.is_active}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/provider-location-assignments/{assignment_id}")
def patch_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    existing = _resolve_assignment_in_org(assignment_id, caller)

    sets: dict[str, Any] = {}
    if payload.is_primary is not None:
        sets["is_primary"] = payload.is_primary
    if payload.is_active is not None:
        sets["is_active"] = payload.is_active
    if not sets:
        return _row_to_dict(existing)

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": assignment_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE provider_location_assignments SET "
                f"{', '.join(set_clauses)} WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text(
                "SELECT * FROM provider_location_assignments WHERE id = :id"
            ),
            {"id": assignment_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="provider_location_assignment_updated",
        detail=(
            f"assignment_id={assignment_id} fields_changed={sorted(sets.keys())}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Location rooms
# ---------------------------------------------------------------------


@router.get("/locations/{location_id}/rooms")
def list_rooms(
    location_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
    is_active: Optional[bool] = Query(default=None),
) -> dict[str, Any]:
    _require_read(caller)
    lid = _resolve_location_in_org(location_id, caller)
    sql = (
        "SELECT * FROM location_rooms "
        "WHERE organization_id = :org AND location_id = :lid"
    )
    params: dict[str, Any] = {"org": caller.organization_id, "lid": lid}
    if is_active is not None:
        sql += " AND is_active = :is_active"
        params["is_active"] = is_active
    sql += " ORDER BY name"
    rows = fetch_all(sql, params)
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/locations/{location_id}/rooms",
    status_code=status.HTTP_201_CREATED,
)
def create_room(
    location_id: int,
    payload: RoomCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    lid = _resolve_location_in_org(location_id, caller)
    room_type = _validate_room_type(payload.room_type)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "location_rooms",
            {
                "organization_id": caller.organization_id,
                "location_id": lid,
                "name": payload.name,
                "room_type": room_type,
                "is_active": payload.is_active,
            },
        )
        row = conn.execute(
            text("SELECT * FROM location_rooms WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="location_room_created",
        detail=(
            f"room_id={new_id} location_id={lid} room_type={room_type} "
            f"is_active={payload.is_active}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/location-rooms/{room_id}")
def patch_room(
    room_id: int,
    payload: RoomUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    existing = _resolve_room_in_org(room_id, caller)

    sets: dict[str, Any] = {}
    if payload.name is not None:
        sets["name"] = payload.name
    if payload.room_type is not None:
        sets["room_type"] = _validate_room_type(payload.room_type)
    if payload.is_active is not None:
        sets["is_active"] = payload.is_active
    if not sets:
        return _row_to_dict(existing)

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": room_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE location_rooms SET {', '.join(set_clauses)} "
                "WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM location_rooms WHERE id = :id"),
            {"id": room_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="location_room_updated",
        detail=(
            f"room_id={room_id} fields_changed={sorted(sets.keys())} "
            f"room_type={row['room_type']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Provider schedule blocks
# ---------------------------------------------------------------------


@router.get("/provider-schedule-blocks")
def list_schedule_blocks(
    request: Request,
    caller: Caller = Depends(require_caller),
    provider_id: Optional[int] = Query(default=None),
    location_id: Optional[int] = Query(default=None),
    block_type: Optional[str] = Query(default=None),
    start_after: Optional[str] = Query(default=None),
    start_before: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    _require_read(caller)
    sql = (
        "SELECT * FROM provider_schedule_blocks "
        "WHERE organization_id = :org"
    )
    params: dict[str, Any] = {"org": caller.organization_id}
    if provider_id is not None:
        sql += " AND provider_id = :provider_id"
        params["provider_id"] = provider_id
    if location_id is not None:
        sql += " AND location_id = :location_id"
        params["location_id"] = location_id
    if block_type is not None:
        sql += " AND block_type = :block_type"
        params["block_type"] = block_type
    if start_after is not None:
        sql += " AND start_at >= :start_after"
        params["start_after"] = start_after
    if start_before is not None:
        sql += " AND start_at <= :start_before"
        params["start_before"] = start_before
    sql += " ORDER BY start_at"
    rows = fetch_all(sql, params)
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/provider-schedule-blocks",
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_block(
    payload: ScheduleBlockCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    pid = _resolve_provider_in_org(payload.provider_id, caller)
    lid = _resolve_location_in_org(payload.location_id, caller)
    btype = _validate_block_type(payload.block_type)
    _validate_time_range(payload.start_at, payload.end_at)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "provider_schedule_blocks",
            {
                "organization_id": caller.organization_id,
                "provider_id": pid,
                "location_id": lid,
                "start_at": payload.start_at,
                "end_at": payload.end_at,
                "block_type": btype,
                "capacity": payload.capacity,
            },
        )
        row = conn.execute(
            text("SELECT * FROM provider_schedule_blocks WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="provider_schedule_block_created",
        detail=(
            f"block_id={new_id} provider_id={pid} location_id={lid} "
            f"block_type={btype} capacity={payload.capacity or 'null'}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/provider-schedule-blocks/{block_id}")
def patch_schedule_block(
    block_id: int,
    payload: ScheduleBlockUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    existing = _resolve_block_in_org(block_id, caller)

    sets: dict[str, Any] = {}
    new_start = payload.start_at if payload.start_at is not None else existing["start_at"]
    new_end = payload.end_at if payload.end_at is not None else existing["end_at"]
    if payload.start_at is not None or payload.end_at is not None:
        # Stringify datetime values from the existing row before compare.
        s = new_start.isoformat() if hasattr(new_start, "isoformat") else str(new_start)
        e = new_end.isoformat() if hasattr(new_end, "isoformat") else str(new_end)
        _validate_time_range(s, e)
    if payload.start_at is not None:
        sets["start_at"] = payload.start_at
    if payload.end_at is not None:
        sets["end_at"] = payload.end_at
    if payload.block_type is not None:
        sets["block_type"] = _validate_block_type(payload.block_type)
    if payload.capacity is not None:
        sets["capacity"] = payload.capacity
    if not sets:
        return _row_to_dict(existing)

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": block_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE provider_schedule_blocks SET "
                f"{', '.join(set_clauses)} WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM provider_schedule_blocks WHERE id = :id"),
            {"id": block_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="provider_schedule_block_updated",
        detail=(
            f"block_id={block_id} fields_changed={sorted(sets.keys())} "
            f"block_type={row['block_type']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Clinic operating hours
# ---------------------------------------------------------------------


@router.get("/clinic-operating-hours")
def list_operating_hours(
    request: Request,
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
) -> dict[str, Any]:
    _require_read(caller)
    sql = (
        "SELECT * FROM clinic_operating_hours "
        "WHERE organization_id = :org"
    )
    params: dict[str, Any] = {"org": caller.organization_id}
    if location_id is not None:
        sql += " AND location_id = :location_id"
        params["location_id"] = location_id
    sql += " ORDER BY location_id, day_of_week"
    rows = fetch_all(sql, params)
    items = [_row_to_dict(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.post(
    "/clinic-operating-hours",
    status_code=status.HTTP_201_CREATED,
)
def create_operating_hours(
    payload: OperatingHoursCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    lid = _resolve_location_in_org(payload.location_id, caller)
    dow = _validate_day_of_week(payload.day_of_week)

    if not payload.is_closed:
        if payload.opens_at and payload.closes_at:
            if payload.opens_at >= payload.closes_at:
                raise _err(
                    "invalid_time_range",
                    "opens_at must be before closes_at",
                    400,
                )

    # Upsert behavior: if a row for (org, location, day_of_week)
    # already exists, return it (test contract).
    existing = fetch_one(
        "SELECT * FROM clinic_operating_hours "
        "WHERE organization_id = :org AND location_id = :lid "
        "AND day_of_week = :dow",
        {"org": caller.organization_id, "lid": lid, "dow": dow},
    )
    if existing:
        return _row_to_dict(existing)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "clinic_operating_hours",
            {
                "organization_id": caller.organization_id,
                "location_id": lid,
                "day_of_week": dow,
                "opens_at": payload.opens_at,
                "closes_at": payload.closes_at,
                "is_closed": payload.is_closed,
            },
        )
        row = conn.execute(
            text("SELECT * FROM clinic_operating_hours WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="clinic_operating_hours_created",
        detail=(
            f"hours_id={new_id} location_id={lid} day_of_week={dow} "
            f"is_closed={payload.is_closed}"
        ),
    )
    return _row_to_dict(dict(row))


@router.patch("/clinic-operating-hours/{hours_id}")
def patch_operating_hours(
    hours_id: int,
    payload: OperatingHoursUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write(caller)
    existing = _resolve_hours_in_org(hours_id, caller)

    sets: dict[str, Any] = {}
    if payload.opens_at is not None:
        sets["opens_at"] = payload.opens_at
    if payload.closes_at is not None:
        sets["closes_at"] = payload.closes_at
    if payload.is_closed is not None:
        sets["is_closed"] = payload.is_closed

    # Validate the resulting time range if both endpoints will be set.
    new_opens = payload.opens_at if payload.opens_at is not None else existing.get("opens_at")
    new_closes = payload.closes_at if payload.closes_at is not None else existing.get("closes_at")
    new_closed = payload.is_closed if payload.is_closed is not None else existing.get("is_closed")
    if not new_closed and new_opens and new_closes:
        if new_opens >= new_closes:
            raise _err(
                "invalid_time_range",
                "opens_at must be before closes_at",
                400,
            )

    if not sets:
        return _row_to_dict(existing)

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": hours_id}
    for k, v in sets.items():
        set_clauses.append(f"{k} = :{k}")
        params[k] = v

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE clinic_operating_hours SET "
                f"{', '.join(set_clauses)} WHERE id = :id"
            ),
            params,
        )
        row = conn.execute(
            text("SELECT * FROM clinic_operating_hours WHERE id = :id"),
            {"id": hours_id},
        ).mappings().first()

    _audit(
        request=request,
        caller=caller,
        event_type="clinic_operating_hours_updated",
        detail=(
            f"hours_id={hours_id} fields_changed={sorted(sets.keys())} "
            f"is_closed={row['is_closed']}"
        ),
    )
    return _row_to_dict(dict(row))


# ---------------------------------------------------------------------
# Dashboard summaries
# ---------------------------------------------------------------------


def _count_open_queue(
    org_id: int, *, location_id: Optional[int] = None, provider_id: Optional[int] = None
) -> int:
    sql = (
        "SELECT COUNT(*) AS c FROM work_queue_items "
        "WHERE organization_id = :org AND status IN ('open','in_progress','blocked')"
    )
    params: dict[str, Any] = {"org": org_id}
    if location_id is not None:
        sql += " AND location_id = :lid"
        params["lid"] = location_id
    if provider_id is not None:
        sql += " AND provider_id = :pid"
        params["pid"] = provider_id
    row = fetch_one(sql, params)
    return int(row["c"]) if row else 0


def _count_by_queue_type(
    org_id: int, queue_types: tuple[str, ...], *, location_id: Optional[int] = None, provider_id: Optional[int] = None
) -> int:
    if not queue_types:
        return 0
    placeholders = ",".join(f":t{i}" for i in range(len(queue_types)))
    sql = (
        "SELECT COUNT(*) AS c FROM work_queue_items "
        "WHERE organization_id = :org AND status IN ('open','in_progress') "
        f"AND queue_type IN ({placeholders})"
    )
    params: dict[str, Any] = {"org": org_id}
    for i, t in enumerate(queue_types):
        params[f"t{i}"] = t
    if location_id is not None:
        sql += " AND location_id = :lid"
        params["lid"] = location_id
    if provider_id is not None:
        sql += " AND provider_id = :pid"
        params["pid"] = provider_id
    row = fetch_one(sql, params)
    return int(row["c"]) if row else 0


@router.get("/locations/{location_id}/dashboard")
def location_dashboard(
    location_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read(caller)
    lid = _resolve_location_in_org(location_id, caller)
    org = caller.organization_id

    open_count = _count_open_queue(org, location_id=lid)
    ready_for_workup = _count_by_queue_type(
        org,
        ("ready_for_workup", "front_desk_check_in"),
        location_id=lid,
    )
    imaging_needed = _count_by_queue_type(
        org, ("imaging_needed", "imaging_review"), location_id=lid
    )
    ready_for_doctor = _count_by_queue_type(
        org, ("ready_for_doctor",), location_id=lid
    )
    review_needed = _count_by_queue_type(
        org, ("note_review", "review_needed"), location_id=lid
    )
    provider_count = int(
        (fetch_one(
            "SELECT COUNT(DISTINCT provider_id) AS c FROM provider_location_assignments "
            "WHERE organization_id = :org AND location_id = :lid AND is_active = :a",
            {"org": org, "lid": lid, "a": True},
        ) or {"c": 0})["c"]
    )
    room_count = int(
        (fetch_one(
            "SELECT COUNT(*) AS c FROM location_rooms "
            "WHERE organization_id = :org AND location_id = :lid AND is_active = :a",
            {"org": org, "lid": lid, "a": True},
        ) or {"c": 0})["c"]
    )
    active_blocks_today = int(
        (fetch_one(
            "SELECT COUNT(*) AS c FROM provider_schedule_blocks "
            "WHERE organization_id = :org AND location_id = :lid "
            "AND DATE(start_at) = DATE(CURRENT_TIMESTAMP)",
            {"org": org, "lid": lid},
        ) or {"c": 0})["c"]
    )

    return {
        "location_id": lid,
        "organization_id": org,
        "counts": {
            "open_queue_items": open_count,
            "ready_for_workup": ready_for_workup,
            "imaging_needed": imaging_needed,
            "ready_for_doctor": ready_for_doctor,
            "review_needed": review_needed,
            "provider_count": provider_count,
            "room_count": room_count,
            "active_schedule_blocks_today": active_blocks_today,
        },
    }


@router.get("/providers/{provider_id}/dashboard")
def provider_dashboard(
    provider_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read(caller)
    pid = _resolve_provider_in_org(provider_id, caller)
    org = caller.organization_id

    assigned_queue = _count_open_queue(org, provider_id=pid)
    ready_for_doctor = _count_by_queue_type(
        org, ("ready_for_doctor",), provider_id=pid
    )
    imaging_review = _count_by_queue_type(
        org, ("imaging_review", "imaging_needed"), provider_id=pid
    )
    signoff_needed = _count_by_queue_type(
        org, ("signoff_needed", "ready_for_signoff"), provider_id=pid
    )
    review_needed = _count_by_queue_type(
        org, ("note_review", "review_needed"), provider_id=pid
    )
    schedule_blocks_today = int(
        (fetch_one(
            "SELECT COUNT(*) AS c FROM provider_schedule_blocks "
            "WHERE organization_id = :org AND provider_id = :pid "
            "AND DATE(start_at) = DATE(CURRENT_TIMESTAMP)",
            {"org": org, "pid": pid},
        ) or {"c": 0})["c"]
    )
    locations_today = int(
        (fetch_one(
            "SELECT COUNT(DISTINCT location_id) AS c FROM provider_schedule_blocks "
            "WHERE organization_id = :org AND provider_id = :pid "
            "AND DATE(start_at) = DATE(CURRENT_TIMESTAMP)",
            {"org": org, "pid": pid},
        ) or {"c": 0})["c"]
    )

    return {
        "provider_id": pid,
        "organization_id": org,
        "counts": {
            "assigned_queue_items": assigned_queue,
            "ready_for_doctor": ready_for_doctor,
            "imaging_review": imaging_review,
            "signoff_needed": signoff_needed,
            "review_needed": review_needed,
            "schedule_blocks_today": schedule_blocks_today,
            "locations_today": locations_today,
        },
    }


@router.get("/admin/multi-clinic-summary")
def admin_multi_clinic_summary(
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    if caller.role != _ROLE_ADMIN:
        raise _err(
            "multi_clinic_role_forbidden",
            "admin multi-clinic summary requires admin role",
            403,
        )
    org = caller.organization_id

    # Per-location compact summaries.
    location_rows = fetch_all(
        "SELECT id, name FROM locations WHERE organization_id = :org ORDER BY id",
        {"org": org},
    )
    location_summaries = []
    for loc in location_rows:
        lid = int(loc["id"])
        location_summaries.append(
            {
                "location_id": lid,
                "open_queue_items": _count_open_queue(org, location_id=lid),
                "ready_for_doctor": _count_by_queue_type(
                    org, ("ready_for_doctor",), location_id=lid
                ),
                "active_rooms": int(
                    (fetch_one(
                        "SELECT COUNT(*) AS c FROM location_rooms "
                        "WHERE organization_id = :org AND location_id = :lid "
                        "AND is_active = :a",
                        {"org": org, "lid": lid, "a": True},
                    ) or {"c": 0})["c"]
                ),
                "schedule_blocks_today": int(
                    (fetch_one(
                        "SELECT COUNT(*) AS c FROM provider_schedule_blocks "
                        "WHERE organization_id = :org AND location_id = :lid "
                        "AND DATE(start_at) = DATE(CURRENT_TIMESTAMP)",
                        {"org": org, "lid": lid},
                    ) or {"c": 0})["c"]
                ),
            }
        )

    # Per-provider compact summaries.
    provider_rows = fetch_all(
        "SELECT id FROM providers WHERE organization_id = :org ORDER BY id",
        {"org": org},
    )
    provider_summaries = []
    for prov in provider_rows:
        pid = int(prov["id"])
        provider_summaries.append(
            {
                "provider_id": pid,
                "open_queue_items": _count_open_queue(org, provider_id=pid),
                "schedule_blocks_today": int(
                    (fetch_one(
                        "SELECT COUNT(*) AS c FROM provider_schedule_blocks "
                        "WHERE organization_id = :org AND provider_id = :pid "
                        "AND DATE(start_at) = DATE(CURRENT_TIMESTAMP)",
                        {"org": org, "pid": pid},
                    ) or {"c": 0})["c"]
                ),
            }
        )

    # Aggregate counts: by status / priority / role / queue_type.
    def _group(col: str) -> dict[str, int]:
        rows = fetch_all(
            f"SELECT {col} AS k, COUNT(*) AS c FROM work_queue_items "
            "WHERE organization_id = :org GROUP BY k",
            {"org": org},
        )
        out: dict[str, int] = {}
        for r in rows:
            key = r["k"] if r["k"] is not None else "unassigned"
            out[str(key)] = int(r["c"])
        return out

    def _open_group_by_user() -> dict[str, int]:
        rows = fetch_all(
            "SELECT COALESCE(u.email, 'unassigned') AS k, COUNT(*) AS c "
            "FROM work_queue_items w "
            "LEFT JOIN users u ON u.id = w.assigned_user_id "
            "WHERE w.organization_id = :org "
            "AND w.status IN ('open','in_progress','blocked') "
            "GROUP BY k ORDER BY c DESC, k",
            {"org": org},
        )
        return {str(r["k"]): int(r["c"]) for r in rows}

    def _open_group_by_role() -> dict[str, int]:
        rows = fetch_all(
            "SELECT COALESCE(assigned_role, 'unassigned') AS k, COUNT(*) AS c "
            "FROM work_queue_items "
            "WHERE organization_id = :org "
            "AND status IN ('open','in_progress','blocked') "
            "GROUP BY k ORDER BY c DESC, k",
            {"org": org},
        )
        return {str(r["k"]): int(r["c"]) for r in rows}

    def _stale_group_by_role() -> dict[str, int]:
        rows = fetch_all(
            "SELECT COALESCE(assigned_role, 'unassigned') AS k, COUNT(*) AS c "
            "FROM work_queue_items "
            "WHERE organization_id = :org "
            "AND status IN ('open','in_progress','blocked') "
            "AND due_at IS NOT NULL AND due_at < CURRENT_TIMESTAMP "
            "GROUP BY k ORDER BY c DESC, k",
            {"org": org},
        )
        return {str(r["k"]): int(r["c"]) for r in rows}

    stale_queue_items = int(
        (fetch_one(
            "SELECT COUNT(*) AS c FROM work_queue_items "
            "WHERE organization_id = :org "
            "AND status IN ('open','in_progress','blocked') "
            "AND due_at IS NOT NULL AND due_at < CURRENT_TIMESTAMP",
            {"org": org},
        ) or {"c": 0})["c"]
    )
    due_today_queue_items = int(
        (fetch_one(
            "SELECT COUNT(*) AS c FROM work_queue_items "
            "WHERE organization_id = :org "
            "AND status IN ('open','in_progress','blocked') "
            "AND due_at IS NOT NULL "
            "AND DATE(due_at) = DATE(CURRENT_TIMESTAMP)",
            {"org": org},
        ) or {"c": 0})["c"]
    )

    return {
        "organization_id": org,
        "locations": location_summaries,
        "providers": provider_summaries,
        "queue_by_status": _group("status"),
        "queue_by_priority": _group("priority"),
        "queue_by_assigned_role": _group("assigned_role"),
        "queue_by_queue_type": _group("queue_type"),
        "queue_by_source": _group("source"),
        "open_queue_by_assigned_role": _open_group_by_role(),
        "open_queue_by_assigned_user": _open_group_by_user(),
        "stale_queue_by_assigned_role": _stale_group_by_role(),
        "stale_queue_items": stale_queue_items,
        "due_today_queue_items": due_today_queue_items,
    }
