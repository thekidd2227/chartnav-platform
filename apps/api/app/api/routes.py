from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
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


def _nonempty_str(v: Any, label: str, max_len: int = 2000) -> str:
    if not isinstance(v, str) or not v.strip():
        raise _err(
            "invalid_event_data",
            f"{label} must be a non-empty string",
            400,
        )
    if len(v) > max_len:
        raise _err(
            "invalid_event_data",
            f"{label} must be <= {max_len} characters",
            400,
        )
    return v


def _validate_event(event_type: str, event_data: Any) -> Optional[dict]:
    """Return a normalized dict payload, or raise 400 on violation.

    - `event_type` must be in EVENT_SCHEMAS.
    - `event_data` must be a JSON object (dict) with all required keys.
    - Per-type value types / enum membership are enforced below.
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

    # Per-type value discipline (phase 14 hardening).
    if event_type == "status_changed":
        for k in ("old_status", "new_status"):
            if event_data[k] not in ALLOWED_STATUSES:
                raise _err(
                    "invalid_event_data",
                    f"status_changed.{k} must be one of {sorted(ALLOWED_STATUSES)}",
                    400,
                )
    elif event_type == "encounter_created":
        if event_data["status"] not in ALLOWED_STATUSES:
            raise _err(
                "invalid_event_data",
                f"encounter_created.status must be one of {sorted(ALLOWED_STATUSES)}",
                400,
            )
    elif event_type == "manual_note":
        _nonempty_str(event_data["note"], "manual_note.note", max_len=4000)
    elif event_type == "note_draft_requested":
        _nonempty_str(event_data["requested_by"], "note_draft_requested.requested_by", max_len=255)
        # template is optional but, if present, must be a non-empty string
        if "template" in event_data:
            _nonempty_str(event_data["template"], "note_draft_requested.template", max_len=255)
    elif event_type == "note_draft_completed":
        _nonempty_str(event_data["template"], "note_draft_completed.template", max_len=255)
        if "length_words" in event_data:
            lw = event_data["length_words"]
            if not isinstance(lw, int) or lw < 0:
                raise _err(
                    "invalid_event_data",
                    "note_draft_completed.length_words must be a non-negative int",
                    400,
                )
    elif event_type == "note_reviewed":
        _nonempty_str(event_data["reviewer"], "note_reviewed.reviewer", max_len=255)

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


class OrganizationSettings(BaseModel):
    """Typed subset of organization-level preferences.

    Any field is optional; unset keys simply mean "no override". An
    `extensions` bucket lets operators stash forward-compat values
    without a schema bump — everything else is rejected.
    """
    default_provider_name: Optional[str] = Field(default=None, max_length=255)
    encounter_page_size: Optional[int] = Field(default=None, ge=10, le=200)
    audit_page_size: Optional[int] = Field(default=None, ge=10, le=200)
    feature_flags: Optional[dict[str, bool]] = None
    extensions: Optional[dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    settings: Optional[OrganizationSettings] = None


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


# ---------- Platform (phase 16) ----------

@router.get("/platform")
def platform_info(caller: Caller = Depends(require_caller)) -> dict:
    """Runtime platform mode + active adapter.

    Any authenticated caller can read this — the frontend needs it to
    render mode-aware UI (banner, admin panel, source-of-truth badges).
    No secrets leak: only the adapter's self-description, not config.
    """
    from app.config import settings as _settings
    from app.integrations import resolve_adapter

    adapter = resolve_adapter()
    info = adapter.info
    return {
        "platform_mode": _settings.platform_mode,
        "integration_adapter": _settings.integration_adapter,
        "adapter": {
            "key": info.key,
            "display_name": info.display_name,
            "description": info.description,
            "supports": {
                "patient_read": info.supports_patient_read,
                "patient_write": info.supports_patient_write,
                "encounter_read": info.supports_encounter_read,
                "encounter_write": info.supports_encounter_write,
                "document_write": info.supports_document_write,
            },
            "source_of_truth": {
                k: v.value for k, v in info.source_of_truth.items()
            },
        },
    }


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
    response: Response,
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
    q: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = 1")
    if q:
        clauses.append("name LIKE :q")
        params["q"] = f"%{q}%"
    where = " WHERE " + " AND ".join(clauses)

    total_row = fetch_one(f"SELECT COUNT(*) AS n FROM locations{where}", params)
    total = int(total_row["n"]) if total_row else 0

    rows = fetch_all(
        "SELECT id, organization_id, name, is_active, created_at "
        f"FROM locations{where} ORDER BY id LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


@router.get("/users")
def list_users(
    response: Response,
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
    q: Optional[str] = Query(default=None, max_length=200),
    role: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = 1")
    if q:
        clauses.append("(email LIKE :q OR full_name LIKE :q)")
        params["q"] = f"%{q}%"
    if role:
        if role not in KNOWN_ROLES:
            raise _err(
                "invalid_role",
                f"role must be one of {sorted(KNOWN_ROLES)}",
                400,
            )
        clauses.append("role = :role")
        params["role"] = role
    where = " WHERE " + " AND ".join(clauses)

    total_row = fetch_one(f"SELECT COUNT(*) AS n FROM users{where}", params)
    total = int(total_row["n"]) if total_row else 0

    rows = fetch_all(
        "SELECT id, organization_id, email, full_name, role, is_active, "
        f"invited_at, created_at FROM users{where} "
        "ORDER BY id LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


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
    "id, organization_id, email, full_name, role, is_active, invited_at, "
    "invitation_expires_at, invitation_accepted_at, created_at"
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
                "invited_at": _now_iso(),
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


# =========================================================================
# Organization settings (admin PATCH; everyone in-org can GET)
# =========================================================================

def _hydrate_org(row: dict) -> dict:
    s = row.get("settings")
    if s:
        try:
            row["settings"] = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    return row


@router.get("/organization")
def get_organization(caller: Caller = Depends(require_caller)) -> dict:
    row = fetch_one(
        "SELECT id, name, slug, settings, created_at FROM organizations "
        "WHERE id = :org",
        {"org": caller.organization_id},
    )
    if not row:
        raise _err("organization_not_found", "no such organization", 404)
    return _hydrate_org(row)


@router.patch("/organization")
def patch_organization(
    payload: OrganizationUpdate, caller: Caller = Depends(require_admin)
) -> dict:
    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.settings is not None:
        # Normalize to only the set fields — avoids polluting the JSON
        # blob with a bunch of nulls from the pydantic model.
        normalized = payload.settings.model_dump(exclude_none=True)
        blob = json.dumps(normalized, sort_keys=True)
        if len(blob) > 16_384:
            raise _err(
                "settings_too_large",
                "settings JSON must be <= 16 KB",
                400,
            )
        updates["settings"] = blob

    if updates:
        with transaction() as conn:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                text(
                    f"UPDATE organizations SET {set_clause} WHERE id = :org"
                ),
                {**updates, "org": caller.organization_id},
            )

    row = fetch_one(
        "SELECT id, name, slug, settings, created_at FROM organizations "
        "WHERE id = :org",
        {"org": caller.organization_id},
    )
    return _hydrate_org(row or {})


# =========================================================================
# Security audit event read (admin only)
# =========================================================================
#
# Scoping rule:
#   Return rows where organization_id = caller.org
#   OR organization_id IS NULL (pre-auth failures carry no caller identity,
#   so they belong to "everyone who admins the system". An admin in
#   another org inspecting their own org's audit log cannot tell whether
#   a null-org row originated from a request targeting a sibling org —
#   but that's the correct property: unauth attempts are visible to
#   every admin, auth'd-cross-org denials are NOT visible here.)
# =========================================================================

_AUDIT_COLS = (
    "id, event_type, request_id, actor_email, actor_user_id, organization_id, "
    "path, method, error_code, detail, remote_addr, created_at"
)


@router.get("/security-audit-events")
def list_security_audit_events(
    response: Response,
    caller: Caller = Depends(require_admin),
    event_type: Optional[str] = Query(default=None),
    error_code: Optional[str] = Query(default=None),
    actor_email: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    clauses: list[str] = [
        "(organization_id = :org OR organization_id IS NULL)"
    ]
    params: dict[str, Any] = {"org": caller.organization_id}
    if event_type:
        clauses.append("event_type = :event_type")
        params["event_type"] = event_type
    if error_code:
        clauses.append("error_code = :error_code")
        params["error_code"] = error_code
    if actor_email:
        clauses.append("actor_email = :actor_email")
        params["actor_email"] = actor_email
    if q:
        clauses.append("(path LIKE :q OR detail LIKE :q)")
        params["q"] = f"%{q}%"
    where = " WHERE " + " AND ".join(clauses)

    total_row = fetch_one(
        f"SELECT COUNT(*) AS n FROM security_audit_events{where}", params
    )
    total = int(total_row["n"]) if total_row else 0

    rows = fetch_all(
        f"SELECT {_AUDIT_COLS} FROM security_audit_events{where} "
        "ORDER BY id DESC LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


# =========================================================================
# Invitation workflow (scaffolded — no email delivery)
# =========================================================================
#
# The raw token is returned exactly once on POST /users/{id}/invite.
# Only its sha256 hash is stored. Accept is unauthenticated (the token
# IS the credential) but strictly checks:
#   - token exists and matches a user
#   - the user is active
#   - invitation_accepted_at is null
#   - invitation_expires_at is in the future
# On success the hash is cleared so the same token can't be replayed.
#
# Email delivery is out of scope. The admin receives the invite URL
# back and is expected to share it out-of-band.
# =========================================================================

INVITE_TTL_DAYS = 7


class InviteAcceptBody(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/users/{user_id}/invite", status_code=status.HTTP_201_CREATED)
def admin_invite_user(
    user_id: int, caller: Caller = Depends(require_admin)
) -> dict:
    """Create or re-issue an invitation for a user in caller's org.

    Returns the raw token ONCE. Previous invitations for the same user
    are effectively revoked (they compared against the old hash, which
    we're about to overwrite).
    """
    with transaction() as conn:
        row = conn.execute(
            text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        if not row or row["organization_id"] != caller.organization_id:
            raise _err("user_not_found", "no such user in your organization", 404)
        if not row["is_active"]:
            raise _err(
                "user_inactive",
                "cannot invite an inactive user; reactivate first",
                400,
            )
        if row["invitation_accepted_at"] is not None:
            raise _err(
                "user_already_accepted",
                "user has already accepted a prior invitation",
                400,
            )

        raw_token = secrets.token_urlsafe(32)
        hashed = _hash_token(raw_token)
        expires = (
            datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)
        ).replace(microsecond=0).isoformat()

        conn.execute(
            text(
                "UPDATE users SET invitation_token_hash = :h, "
                "invitation_expires_at = :exp WHERE id = :id"
            ),
            {"h": hashed, "exp": expires, "id": user_id},
        )

    return {
        "user_id": user_id,
        "invitation_token": raw_token,  # returned once, never stored raw
        "invitation_expires_at": expires,
        "ttl_days": INVITE_TTL_DAYS,
    }


@router.post("/invites/accept")
def accept_invite(payload: InviteAcceptBody) -> dict:
    """Unauthenticated — the token IS the credential.

    Rate-limited by the path-level middleware below (/invites/accept is
    added to the rate-limit protected prefixes via app.middleware).
    """
    h = _hash_token(payload.token)
    row = fetch_one(
        "SELECT id, organization_id, email, full_name, role, is_active, "
        "invited_at, invitation_expires_at, invitation_accepted_at "
        "FROM users WHERE invitation_token_hash = :h",
        {"h": h},
    )
    if not row:
        raise _err("invalid_invite", "invitation token is invalid", 400)
    if not row["is_active"]:
        raise _err("invalid_invite", "invitation target is inactive", 400)
    if row["invitation_accepted_at"] is not None:
        raise _err("invalid_invite", "invitation has already been accepted", 400)

    expires = row["invitation_expires_at"]
    try:
        exp_dt = (
            datetime.fromisoformat(expires.replace(" ", "T"))
            if isinstance(expires, str) else expires
        )
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
    except Exception:  # pragma: no cover
        raise _err("invalid_invite", "invitation expiry is malformed", 400)
    if exp_dt < datetime.now(timezone.utc):
        raise _err("invite_expired", "invitation has expired", 400)

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE users SET invitation_accepted_at = CURRENT_TIMESTAMP, "
                "invitation_token_hash = NULL WHERE id = :id"
            ),
            {"id": row["id"]},
        )
    return {
        "user_id": row["id"],
        "email": row["email"],
        "organization_id": row["organization_id"],
        "role": row["role"],
        "accepted": True,
    }


# =========================================================================
# Audit export — CSV, admin-only, honors filters + org scoping
# =========================================================================

@router.get("/security-audit-events/export", include_in_schema=True)
def export_security_audit_events(
    caller: Caller = Depends(require_admin),
    event_type: Optional[str] = Query(default=None),
    error_code: Optional[str] = Query(default=None),
    actor_email: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, max_length=200),
):
    from fastapi.responses import Response as _PlainResponse

    clauses: list[str] = [
        "(organization_id = :org OR organization_id IS NULL)"
    ]
    params: dict[str, Any] = {"org": caller.organization_id}
    if event_type:
        clauses.append("event_type = :event_type")
        params["event_type"] = event_type
    if error_code:
        clauses.append("error_code = :error_code")
        params["error_code"] = error_code
    if actor_email:
        clauses.append("actor_email = :actor_email")
        params["actor_email"] = actor_email
    if q:
        clauses.append("(path LIKE :q OR detail LIKE :q)")
        params["q"] = f"%{q}%"
    where = " WHERE " + " AND ".join(clauses)

    rows = fetch_all(
        f"SELECT {_AUDIT_COLS} FROM security_audit_events{where} "
        "ORDER BY id DESC",
        params,
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "created_at", "event_type", "error_code", "actor_email",
        "actor_user_id", "organization_id", "method", "path",
        "request_id", "remote_addr", "detail",
    ])
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("created_at"), r.get("event_type"),
            r.get("error_code"), r.get("actor_email"),
            r.get("actor_user_id"), r.get("organization_id"),
            r.get("method"), r.get("path"),
            r.get("request_id"), r.get("remote_addr"),
            r.get("detail") or "",
        ])

    filename = f"chartnav-audit-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    return _PlainResponse(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =========================================================================
# Bulk user import — admin, strictly org-scoped, fail-safe per row
# =========================================================================

class BulkUserInput(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=_EMAIL_RE)
    full_name: Optional[str] = Field(default=None, max_length=255)
    role: str


class BulkUsersBody(BaseModel):
    users: list[BulkUserInput] = Field(..., min_length=1, max_length=500)


@router.post("/users/bulk", status_code=status.HTTP_200_OK)
def admin_bulk_create_users(
    payload: BulkUsersBody, caller: Caller = Depends(require_admin)
) -> dict:
    """Create many users at once. Each row is validated independently:

    - Created rows are returned in `created`.
    - Duplicate emails are returned in `skipped` with reason.
    - Invalid roles / other errors land in `errors`.

    Partial failure does NOT abort the batch — operators get a clear
    summary they can act on.
    """
    created: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    with transaction() as conn:
        for i, u in enumerate(payload.users):
            if u.role not in KNOWN_ROLES:
                errors.append(
                    {"row": i, "email": u.email, "error_code": "invalid_role"}
                )
                continue
            existing = conn.execute(
                text("SELECT id FROM users WHERE email = :e"), {"e": u.email}
            ).mappings().first()
            if existing:
                skipped.append(
                    {"row": i, "email": u.email, "error_code": "user_email_taken"}
                )
                continue
            try:
                new_id = insert_returning_id(
                    conn,
                    "users",
                    {
                        "organization_id": caller.organization_id,
                        "email": u.email,
                        "full_name": u.full_name,
                        "role": u.role,
                        "invited_at": _now_iso(),
                    },
                )
                row = conn.execute(
                    text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
                    {"id": new_id},
                ).mappings().first()
                created.append(dict(row))
            except Exception as e:  # pragma: no cover — defensive
                errors.append(
                    {"row": i, "email": u.email, "error_code": "insert_failed", "detail": str(e)}
                )

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "summary": {
            "requested": len(payload.users),
            "created": len(created),
            "skipped": len(skipped),
            "errors": len(errors),
        },
    }
