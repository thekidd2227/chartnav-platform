from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth import Caller, ensure_same_org, require_caller
from app.authz import (
    KNOWN_ROLES,
    assert_can_transition,
    require_admin,
    require_create_encounter,
    require_create_event,
)
from app.db import (
    fetch_all,
    fetch_one,
    insert_returning_id,
    transaction,
)

router = APIRouter()

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


# ---------- Event schema ----------
#
# Allowlist of event_type values + per-type required keys for
# `event_data`. Types that aren't listed here are rejected.
# `manual_note` is the generic operator-authored event; it just
# requires a `note` key.
#
# Server-written types (encounter_created, status_changed) are
# recorded automatically by the mutation handlers — they're included
# here so the validator doesn't need a second bypass path.
EVENT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "encounter_created":      ("status",),
    "status_changed":         ("old_status", "new_status"),
    "note_draft_requested":   ("requested_by",),
    "note_draft_completed":   ("template",),
    "note_reviewed":          ("reviewer",),
    "manual_note":            ("note",),
}


def _validate_event(event_type: str, event_data: Any) -> Optional[dict]:
    """Return a normalized dict payload, or raise 400 on violation.

    - `event_type` must be in EVENT_SCHEMAS.
    - `event_data` must be a JSON object (dict) with all required keys.
      `None` is accepted only for types with no required keys.
    """
    if event_type not in EVENT_SCHEMAS:
        raise _err(
            "invalid_event_type",
            f"must be one of {sorted(EVENT_SCHEMAS.keys())}",
            400,
        )
    required = EVENT_SCHEMAS[event_type]
    if event_data is None:
        if required:
            raise _err(
                "invalid_event_data",
                f"{event_type} requires keys: {list(required)}",
                400,
            )
        return None
    if not isinstance(event_data, dict):
        raise _err(
            "invalid_event_data",
            f"{event_type} event_data must be a JSON object",
            400,
        )
    missing = [k for k in required if k not in event_data]
    if missing:
        raise _err(
            "invalid_event_data",
            f"{event_type} missing required keys: {missing}",
            400,
        )
    return event_data


# ---------- standardized errors ----------

def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


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
    row = fetch_one(
        f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = :id",
        {"id": encounter_id},
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


# ---------- Admin payloads ----------

_EMAIL_RE = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=_EMAIL_RE)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: str


class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=255, pattern=_EMAIL_RE)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


# ---------- Open endpoints ----------

@router.get("/health")
def health() -> dict[str, str]:
    """Liveness — cheap, never touches the DB."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    """Readiness — pings the DB. 503 if the DB isn't reachable.

    Operators: wire this into your compose/orchestrator healthcheck
    instead of `/health` when you want to gate traffic on DB wiring.
    """
    try:
        fetch_one("SELECT 1 AS ok")
        return {"status": "ready", "database": "ok"}
    except Exception as e:  # pragma: no cover — defensive
        raise _err("not_ready", f"database unreachable: {e}", 503)


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "chartnav-api", "version": "0.1.0"}


@router.get("/metrics", include_in_schema=False)
def metrics_endpoint():
    """Prometheus text exposition. Unauthed — restrict at the edge."""
    from fastapi.responses import PlainTextResponse
    from app.metrics import metrics as _m

    return PlainTextResponse(
        _m.render(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )


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


# ---------- Org metadata (authed + org-scoped) ----------

@router.get("/organizations")
def list_organizations(caller: Caller = Depends(require_caller)) -> list[dict]:
    return fetch_all(
        "SELECT id, name, slug, created_at FROM organizations "
        "WHERE id = :org ORDER BY id",
        {"org": caller.organization_id},
    )


@router.get("/locations")
def list_locations(
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
) -> list[dict]:
    if include_inactive:
        return fetch_all(
            "SELECT id, organization_id, name, is_active, created_at "
            "FROM locations WHERE organization_id = :org ORDER BY id",
            {"org": caller.organization_id},
        )
    return fetch_all(
        "SELECT id, organization_id, name, is_active, created_at "
        "FROM locations WHERE organization_id = :org AND is_active = 1 "
        "ORDER BY id",
        {"org": caller.organization_id},
    )


@router.get("/users")
def list_users(
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
) -> list[dict]:
    if include_inactive:
        return fetch_all(
            "SELECT id, organization_id, email, full_name, role, is_active, "
            "created_at FROM users WHERE organization_id = :org ORDER BY id",
            {"org": caller.organization_id},
        )
    return fetch_all(
        "SELECT id, organization_id, email, full_name, role, is_active, "
        "created_at FROM users WHERE organization_id = :org AND is_active = 1 "
        "ORDER BY id",
        {"org": caller.organization_id},
    )


# ---------- Encounters (authed + org-scoped + RBAC) ----------

@router.get("/encounters")
def list_encounters(
    response: Response,
    caller: Caller = Depends(require_caller),
    organization_id: Optional[int] = Query(default=None, ge=1),
    location_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[str] = Query(default=None),
    provider_name: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """List encounters scoped to the caller's org.

    Backward compatible: still returns a JSON array. Pagination metadata
    is exposed on response headers so existing clients that ignore
    pagination keep working:

        X-Total-Count : full filtered count (ignoring limit/offset)
        X-Limit       : echo of the limit applied
        X-Offset      : echo of the offset applied
    """
    if organization_id is not None and organization_id != caller.organization_id:
        raise _err(
            "cross_org_access_forbidden",
            "requested organization does not match caller's organization",
            403,
        )

    clauses: list[str] = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}

    if location_id is not None:
        clauses.append("location_id = :loc")
        params["loc"] = location_id
    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise _err(
                "invalid_status",
                f"must be one of {sorted(ALLOWED_STATUSES)}",
                400,
            )
        clauses.append("status = :status")
        params["status"] = status
    if provider_name is not None:
        clauses.append("provider_name = :provider")
        params["provider"] = provider_name

    where = " WHERE " + " AND ".join(clauses)

    count_row = fetch_one(f"SELECT COUNT(*) AS n FROM encounters{where}", params)
    total = int(count_row["n"]) if count_row else 0

    page_params = {**params, "limit": limit, "offset": offset}
    rows = fetch_all(
        f"SELECT {ENCOUNTER_COLUMNS} FROM encounters{where} "
        "ORDER BY id LIMIT :limit OFFSET :offset",
        page_params,
    )

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


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
        "FROM workflow_events WHERE encounter_id = :enc ORDER BY id",
        {"enc": encounter_id},
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

    with transaction() as conn:
        loc = conn.execute(
            text("SELECT id, organization_id FROM locations WHERE id = :id"),
            {"id": payload.location_id},
        ).mappings().first()
        if not loc:
            raise _err("location_not_found", "no such location", 400)
        if loc["organization_id"] != caller.organization_id:
            raise _err(
                "cross_org_access_forbidden",
                "location does not belong to caller's organization",
                403,
            )

        started_at = _now_iso() if payload.status == "in_progress" else None

        new_id = insert_returning_id(
            conn,
            "encounters",
            {
                "organization_id": caller.organization_id,
                "location_id": payload.location_id,
                "patient_identifier": payload.patient_identifier,
                "patient_name": payload.patient_name,
                "provider_name": payload.provider_name,
                "status": payload.status,
                "scheduled_at": (
                    payload.scheduled_at.isoformat()
                    if payload.scheduled_at
                    else None
                ),
                "started_at": started_at,
                "completed_at": None,
            },
        )

        conn.execute(
            text(
                "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
                "VALUES (:enc, :type, :data)"
            ),
            {
                "enc": new_id,
                "type": "encounter_created",
                "data": json.dumps(
                    {"status": payload.status, "created_by": caller.email},
                    sort_keys=True,
                ),
            },
        )

        row = conn.execute(
            text(f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()
        return dict(row)


@router.post(
    "/encounters/{encounter_id}/events", status_code=status.HTTP_201_CREATED
)
def create_encounter_event(
    encounter_id: int,
    payload: EventCreate,
    caller: Caller = Depends(require_create_event),
) -> dict:
    _load_encounter_for_caller(encounter_id, caller)

    # Validate event_type + event_data shape.
    validated = _validate_event(payload.event_type, payload.event_data)
    event_data_str = json.dumps(validated, sort_keys=True) if validated is not None else None

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "workflow_events",
            {
                "encounter_id": encounter_id,
                "event_type": payload.event_type,
                "event_data": event_data_str,
            },
        )
        row = conn.execute(
            text(
                "SELECT id, encounter_id, event_type, event_data, created_at "
                "FROM workflow_events WHERE id = :id"
            ),
            {"id": new_id},
        ).mappings().first()
        return _hydrate_event(dict(row))


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

    # same-state = no-op
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

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE encounters SET status = :s, started_at = :sa, "
                "completed_at = :ca WHERE id = :id"
            ),
            {
                "s": new_status,
                "sa": started_at,
                "ca": completed_at,
                "id": encounter_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
                "VALUES (:enc, :type, :data)"
            ),
            {
                "enc": encounter_id,
                "type": "status_changed",
                "data": json.dumps(
                    {
                        "old_status": previous_status,
                        "new_status": new_status,
                        "changed_by": caller.email,
                    },
                    sort_keys=True,
                ),
            },
        )
        updated = conn.execute(
            text(f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = :id"),
            {"id": encounter_id},
        ).mappings().first()
        return dict(updated)


# =========================================================================
# Admin CRUD — users + locations (admin role only; strictly org-scoped)
# =========================================================================

USER_COLUMNS = (
    "id, organization_id, email, full_name, role, is_active, created_at"
)
LOCATION_COLUMNS = "id, organization_id, name, is_active, created_at"


@router.post("/users", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: UserCreate, caller: Caller = Depends(require_admin)
) -> dict:
    if payload.role not in KNOWN_ROLES:
        raise _err(
            "invalid_role",
            f"role must be one of {sorted(KNOWN_ROLES)}",
            400,
        )
    with transaction() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :e"),
            {"e": payload.email},
        ).mappings().first()
        if existing:
            raise _err("user_email_taken", "email already in use", 409)

        new_id = insert_returning_id(
            conn,
            "users",
            {
                "organization_id": caller.organization_id,
                "email": payload.email,
                "full_name": payload.full_name,
                "role": payload.role,
            },
        )
        row = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()
        return dict(row)


@router.patch("/users/{user_id}")
def admin_update_user(
    user_id: int,
    payload: UserUpdate,
    caller: Caller = Depends(require_admin),
) -> dict:
    # Validate role if provided, and prevent the caller from demoting
    # themselves or deactivating their own account (foot-gun protection).
    if payload.role is not None and payload.role not in KNOWN_ROLES:
        raise _err(
            "invalid_role",
            f"role must be one of {sorted(KNOWN_ROLES)}",
            400,
        )

    with transaction() as conn:
        row = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        if not row or row["organization_id"] != caller.organization_id:
            raise _err("user_not_found", "no such user in your organization", 404)

        if user_id == caller.user_id:
            if payload.role is not None and payload.role != "admin":
                raise _err(
                    "cannot_demote_self",
                    "an admin cannot remove their own admin role",
                    400,
                )
            if payload.is_active is False:
                raise _err(
                    "cannot_deactivate_self",
                    "an admin cannot deactivate their own account",
                    400,
                )

        updates: dict[str, Any] = {}
        if payload.email is not None:
            # Uniqueness check (case-sensitive; matches prior contract)
            clash = conn.execute(
                text("SELECT id FROM users WHERE email = :e AND id != :id"),
                {"e": payload.email, "id": user_id},
            ).mappings().first()
            if clash:
                raise _err("user_email_taken", "email already in use", 409)
            updates["email"] = payload.email
        if payload.full_name is not None:
            updates["full_name"] = payload.full_name
        if payload.role is not None:
            updates["role"] = payload.role
        if payload.is_active is not None:
            updates["is_active"] = bool(payload.is_active)

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                text(f"UPDATE users SET {set_clause} WHERE id = :id"),
                {**updates, "id": user_id},
            )
        updated = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        return dict(updated)


@router.delete("/users/{user_id}")
def admin_deactivate_user(
    user_id: int, caller: Caller = Depends(require_admin)
) -> dict:
    """Soft-delete — sets is_active = 0. Preserves audit/history FKs."""
    if user_id == caller.user_id:
        raise _err(
            "cannot_deactivate_self",
            "an admin cannot deactivate their own account",
            400,
        )
    with transaction() as conn:
        row = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        if not row or row["organization_id"] != caller.organization_id:
            raise _err("user_not_found", "no such user in your organization", 404)

        conn.execute(
            text("UPDATE users SET is_active = 0 WHERE id = :id"),
            {"id": user_id},
        )
        updated = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        return dict(updated)


@router.post("/locations", status_code=status.HTTP_201_CREATED)
def admin_create_location(
    payload: LocationCreate, caller: Caller = Depends(require_admin)
) -> dict:
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "locations",
            {"organization_id": caller.organization_id, "name": payload.name},
        )
        row = conn.execute(
            text(f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = :id"),
            {"id": new_id},
        ).mappings().first()
        return dict(row)


@router.patch("/locations/{location_id}")
def admin_update_location(
    location_id: int,
    payload: LocationUpdate,
    caller: Caller = Depends(require_admin),
) -> dict:
    with transaction() as conn:
        row = conn.execute(
            text(f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = :id"),
            {"id": location_id},
        ).mappings().first()
        if not row or row["organization_id"] != caller.organization_id:
            raise _err(
                "location_not_found",
                "no such location in your organization",
                404,
            )
        updates: dict[str, Any] = {}
        if payload.name is not None:
            updates["name"] = payload.name
        if payload.is_active is not None:
            updates["is_active"] = bool(payload.is_active)
        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                text(f"UPDATE locations SET {set_clause} WHERE id = :id"),
                {**updates, "id": location_id},
            )
        updated = conn.execute(
            text(f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = :id"),
            {"id": location_id},
        ).mappings().first()
        return dict(updated)


@router.delete("/locations/{location_id}")
def admin_deactivate_location(
    location_id: int, caller: Caller = Depends(require_admin)
) -> dict:
    with transaction() as conn:
        row = conn.execute(
            text(f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = :id"),
            {"id": location_id},
        ).mappings().first()
        if not row or row["organization_id"] != caller.organization_id:
            raise _err(
                "location_not_found",
                "no such location in your organization",
                404,
            )
        conn.execute(
            text("UPDATE locations SET is_active = 0 WHERE id = :id"),
            {"id": location_id},
        )
        updated = conn.execute(
            text(f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = :id"),
            {"id": location_id},
        ).mappings().first()
        return dict(updated)
