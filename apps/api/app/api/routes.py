from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
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
    "provider_name, status, patient_id, provider_id, "
    "external_ref, external_source, "
    "scheduled_at, started_at, completed_at, created_at"
)


def _load_encounter_for_caller(encounter_id: int, caller: Caller) -> dict:
    row = fetch_one(
        f"SELECT {ENCOUNTER_COLUMNS} FROM encounters WHERE id = :id",
        {"id": encounter_id},
    )
    if not row or row["organization_id"] != caller.organization_id:
        raise _err("encounter_not_found", "no such encounter in your organization", 404)
    # Phase 20 — tag the source so the frontend can render a
    # source-of-truth chip consistently in every mode.
    return {**row, "_source": "chartnav"}


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
                "document_transmit": info.supports_document_transmit,
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
    if status is not None and status not in ALLOWED_STATUSES:
        raise _err(
            "invalid_status",
            f"must be one of {sorted(ALLOWED_STATUSES)}",
            400,
        )

    # Phase 20 — dispatch through the adapter so integrated modes stop
    # assuming native DB ownership. Standalone mode resolves to the
    # native adapter, which queries the same table the old direct-SQL
    # path did, so behavior is identical.
    from app.integrations import resolve_adapter
    from app.integrations.base import AdapterError

    adapter = resolve_adapter()
    try:
        result = adapter.list_encounters(
            organization_id=caller.organization_id,
            location_id=location_id,
            status=status,
            provider_name=provider_name,
            limit=limit,
            offset=offset,
        )
    except AdapterError as e:
        raise _err(e.error_code, e.reason, 502)

    response.headers["X-Total-Count"] = str(result.total)
    response.headers["X-Limit"] = str(result.limit)
    response.headers["X-Offset"] = str(result.offset)
    return result.items


class EncounterBridgeBody(BaseModel):
    """Body for POST /encounters/bridge (phase 21).

    Fields beyond `external_ref` + `external_source` are mirror hints
    — the bridge uses them to populate the native row's display
    fields on first create. They're optional because callers can also
    pre-fetch the external row via `/encounters/{vendor_id}` and
    forward what they saw.
    """
    external_ref: str = Field(..., min_length=1, max_length=128)
    external_source: str = Field(..., min_length=1, max_length=64)
    patient_identifier: Optional[str] = Field(default=None, max_length=64)
    patient_name: Optional[str] = Field(default=None, max_length=255)
    provider_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None)


@router.post("/encounters/bridge", status_code=status.HTTP_200_OK)
def bridge_encounter(
    payload: EncounterBridgeBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Get-or-create a native encounter tied to an external one.

    - Idempotent on `(organization_id, external_ref, external_source)`.
    - Returns the full native row plus `_bridged: True` on first
      creation, `False` on subsequent resolves.
    - Refused in `standalone` mode (nothing external to bridge from).
    - Works in both integrated modes.
    - admin + clinician can bridge; reviewer cannot.
    """
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_forbidden",
            "only admin or clinician may bridge an external encounter",
            403,
        )
    from app.config import settings as _settings
    if _settings.platform_mode == "standalone":
        raise _err(
            "bridge_not_available_in_standalone_mode",
            "encounter bridging is only supported in integrated modes",
            409,
        )
    if payload.status is not None and payload.status not in ALLOWED_STATUSES:
        raise _err(
            "invalid_status",
            f"status must be one of {sorted(ALLOWED_STATUSES)}",
            400,
        )

    from app.services.bridge import resolve_or_create_bridged_encounter
    from app import audit as _audit

    row = resolve_or_create_bridged_encounter(
        organization_id=caller.organization_id,
        external_ref=payload.external_ref,
        external_source=payload.external_source,
        patient_identifier=payload.patient_identifier,
        patient_name=payload.patient_name,
        provider_name=payload.provider_name,
        status=payload.status,
    )
    if row.get("_bridged"):
        _audit.record(
            event_type="encounter_bridged",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path="/encounters/bridge",
            method="POST",
            detail=(
                f"external_source={payload.external_source} "
                f"external_ref={payload.external_ref} "
                f"native_id={row['id']}"
            ),
        )
    return row


@router.get("/encounters/{encounter_id}")
def get_encounter(
    encounter_id: str, caller: Caller = Depends(require_caller)
) -> dict:
    """Adapter-dispatched encounter read.

    Native adapter keeps the old behavior (includes cross-org 404
    and `encounter_not_found` semantics via `_load_encounter_for_caller`).
    Integrated modes fetch through the resolved adapter; the response
    carries `_source` and `_external_ref` so the UI can render
    source-of-truth correctly.
    """
    from app.config import settings as _settings
    if _settings.platform_mode == "standalone":
        try:
            return _load_encounter_for_caller(int(encounter_id), caller)
        except (ValueError, TypeError):
            raise _err("encounter_not_found", "no such encounter in your organization", 404)

    from app.integrations import resolve_adapter
    from app.integrations.base import AdapterError

    adapter = resolve_adapter()
    try:
        row = adapter.fetch_encounter(str(encounter_id))
    except AdapterError as e:
        if e.error_code == "encounter_not_found":
            raise _err("encounter_not_found", e.reason, 404)
        raise _err(e.error_code, e.reason, 502)
    # Stamp caller's org so the UI scope is explicit even when the
    # adapter doesn't know about ChartNav orgs (FHIR is global-namespace).
    if row.get("organization_id") is None:
        row["organization_id"] = caller.organization_id
    return row


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


def _assert_encounter_write_allowed() -> None:
    """Refuse encounter-creation mutations honestly in integrated modes.

    For create_encounter specifically: both integrated modes currently
    refuse, because creating an encounter that doesn't exist in the
    external EHR yet is a push-back operation we do not implement.
    `update_encounter_status` follows a different path — see its
    handler for the write-through adapter dispatch.
    """
    from app.config import settings as _settings
    mode = _settings.platform_mode
    if mode in {"integrated_readthrough", "integrated_writethrough"}:
        raise _err(
            "encounter_write_unsupported",
            f"encounter creation is disabled in {mode} mode; the external "
            "EHR owns encounter provisioning",
            409,
        )


@router.post("/encounters", status_code=status.HTTP_201_CREATED)
def create_encounter(
    payload: EncounterCreate,
    caller: Caller = Depends(require_create_encounter),
) -> dict:
    _assert_encounter_write_allowed()
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
    # Workflow events are ChartNav-native tracking of operator work,
    # not mutations to the external encounter — they're allowed in
    # every mode. See docs/build/26-platform-mode-and-interoperability.md.
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
    # Read-through is always refused. Write-through goes through the
    # adapter — which may still refuse honestly (FHIR raises
    # AdapterNotSupported because generic R4 status writes are
    # vendor-specific). Standalone keeps the existing native path.
    from app.config import settings as _settings
    mode = _settings.platform_mode
    if mode == "integrated_readthrough":
        raise _err(
            "encounter_write_unsupported",
            "encounter status writes are disabled in integrated_readthrough mode; "
            "the external EHR remains source of record",
            409,
        )
    if mode == "integrated_writethrough":
        from app.integrations import resolve_adapter
        from app.integrations.base import AdapterError, AdapterNotSupported
        adapter = resolve_adapter()
        try:
            result = adapter.update_encounter_status(
                str(encounter_id), payload.status, changed_by=caller.email
            )
        except AdapterNotSupported as e:
            raise _err(
                "adapter_write_not_supported",
                e.reason,
                501,
            )
        except AdapterError as e:
            raise _err(e.error_code, e.reason, 502)
        return result

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


# ===========================================================================
# Native clinical layer (phase 18) — patients + providers
# ===========================================================================
#
# These endpoints are the first-class surface for ChartNav-native clinical
# objects in standalone mode. They still exist in integrated modes but behave
# per the platform-mode contract documented in
# docs/build/26-platform-mode-and-interoperability.md:
#
#   standalone              → full read + write against the native DB
#   integrated_readthrough  → reads only against mirrored rows; writes 403
#                             `native_write_disabled_in_integrated_mode`
#   integrated_writethrough → reads + writes against the native DB
#                             (adapters translate external pushes separately)

PATIENT_COLUMNS = (
    "id, organization_id, external_ref, patient_identifier, "
    "first_name, last_name, date_of_birth, sex_at_birth, is_active, created_at"
)
PROVIDER_COLUMNS = (
    "id, organization_id, external_ref, display_name, npi, specialty, "
    "is_active, created_at"
)


def _native_writes_allowed() -> bool:
    from app.config import settings as _settings
    return _settings.platform_mode in {"standalone", "integrated_writethrough"}


class PatientCreate(BaseModel):
    patient_identifier: str = Field(..., min_length=1, max_length=64)
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    date_of_birth: Optional[str] = Field(default=None, description="ISO date YYYY-MM-DD")
    sex_at_birth: Optional[str] = Field(default=None, max_length=16)
    external_ref: Optional[str] = Field(default=None, max_length=128)


class ProviderCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    npi: Optional[str] = Field(default=None, max_length=16)
    specialty: Optional[str] = Field(default=None, max_length=128)
    external_ref: Optional[str] = Field(default=None, max_length=128)


@router.get("/patients")
def list_patients(
    response: Response,
    caller: Caller = Depends(require_caller),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=False),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = 1")
    if q:
        clauses.append(
            "(patient_identifier LIKE :q OR first_name LIKE :q OR last_name LIKE :q)"
        )
        params["q"] = f"%{q}%"
    where = " WHERE " + " AND ".join(clauses)

    total = int(fetch_one(f"SELECT COUNT(*) AS n FROM patients{where}", params)["n"])
    rows = fetch_all(
        f"SELECT {PATIENT_COLUMNS} FROM patients{where} "
        "ORDER BY id LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


@router.post("/patients", status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    # Admin or clinician can create; reviewers are read-only.
    if caller.role not in {"admin", "clinician"}:
        raise _err("role_forbidden", "admin or clinician only", 403)
    if not _native_writes_allowed():
        raise _err(
            "native_write_disabled_in_integrated_mode",
            "native patient writes are disabled when "
            "CHARTNAV_PLATFORM_MODE=integrated_readthrough",
            409,
        )

    # Uniqueness on (org, patient_identifier) — friendly error instead of 500.
    existing = fetch_one(
        "SELECT id FROM patients WHERE organization_id = :org "
        "AND patient_identifier = :pid",
        {"org": caller.organization_id, "pid": payload.patient_identifier},
    )
    if existing:
        raise _err(
            "patient_identifier_conflict",
            f"patient_identifier {payload.patient_identifier!r} already exists in your organization",
            409,
        )

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "patients",
            {
                "organization_id": caller.organization_id,
                "patient_identifier": payload.patient_identifier,
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "date_of_birth": payload.date_of_birth,
                "sex_at_birth": payload.sex_at_birth,
                "external_ref": payload.external_ref,
            },
        )
    row = fetch_one(
        f"SELECT {PATIENT_COLUMNS} FROM patients WHERE id = :id",
        {"id": new_id},
    )
    return row


@router.get("/providers")
def list_providers(
    response: Response,
    caller: Caller = Depends(require_caller),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None, max_length=100),
    include_inactive: bool = Query(default=False),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = 1")
    if q:
        clauses.append(
            "(display_name LIKE :q OR specialty LIKE :q OR npi LIKE :q)"
        )
        params["q"] = f"%{q}%"
    where = " WHERE " + " AND ".join(clauses)

    total = int(fetch_one(f"SELECT COUNT(*) AS n FROM providers{where}", params)["n"])
    rows = fetch_all(
        f"SELECT {PROVIDER_COLUMNS} FROM providers{where} "
        "ORDER BY id LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return rows


@router.post("/providers", status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ProviderCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    require_admin(caller)
    if not _native_writes_allowed():
        raise _err(
            "native_write_disabled_in_integrated_mode",
            "native provider writes are disabled when "
            "CHARTNAV_PLATFORM_MODE=integrated_readthrough",
            409,
        )

    # NPI format check — 10 digits only when provided.
    if payload.npi is not None:
        npi = payload.npi.strip()
        if npi and (not npi.isdigit() or len(npi) != 10):
            raise _err(
                "invalid_npi",
                "NPI must be exactly 10 digits when provided",
                400,
            )

    if payload.npi:
        dup = fetch_one(
            "SELECT id FROM providers WHERE organization_id = :org AND npi = :npi",
            {"org": caller.organization_id, "npi": payload.npi},
        )
        if dup:
            raise _err("npi_conflict", "another provider in your org already uses this NPI", 409)

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "providers",
            {
                "organization_id": caller.organization_id,
                "display_name": payload.display_name,
                "npi": payload.npi,
                "specialty": payload.specialty,
                "external_ref": payload.external_ref,
            },
        )
    row = fetch_one(
        f"SELECT {PROVIDER_COLUMNS} FROM providers WHERE id = :id",
        {"id": new_id},
    )
    return row


# ===========================================================================
# Transcript ingestion + note drafting + signoff (phase 19)
# ===========================================================================
#
# The ChartNav wedge: operator feeds an encounter's input (paste, audio
# metadata, manual notes, or an imported transcript), a generator
# produces extracted findings + a draft note, a provider reviews and
# signs. Export is a separate state so the UI can distinguish "signed"
# from "handed off."
#
# Trust model — enforced in both data model + UI:
#   1. encounter_inputs  = raw transcript-derived source of truth
#   2. extracted_findings = structured facts the generator saw
#   3. note_versions     = narrative drafts; only the signed version is
#                          authoritative; edits create new versions.
# Each tier is a separate table so the three stages stay distinguishable
# at audit time.

import json as _json  # namespaced to avoid clobbering existing `json` import

from app.services.note_generator import generate_draft

INPUT_TYPES = {"audio_upload", "text_paste", "manual_entry", "imported_transcript"}
INPUT_STATUSES = {"queued", "processing", "completed", "failed", "needs_review"}

NOTE_STATUSES = {"draft", "provider_review", "revised", "signed", "exported"}
NOTE_FORMATS = {"soap", "assessment_plan", "consult_note", "freeform"}

# Allowed forward transitions on note_versions.draft_status.
# Regeneration intentionally bypasses this table by creating a NEW row.
NOTE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"provider_review", "revised", "signed"},
    "provider_review": {"revised", "signed", "draft"},
    "revised": {"provider_review", "signed"},
    "signed": {"exported"},
    "exported": set(),
}


INPUT_COLUMNS = (
    "id, encounter_id, input_type, processing_status, transcript_text, "
    "confidence_summary, source_metadata, created_by_user_id, "
    "retry_count, last_error, last_error_code, "
    "started_at, finished_at, worker_id, "
    "claimed_by, claimed_at, "
    "created_at, updated_at"
)
FINDINGS_COLUMNS = (
    "id, encounter_id, input_id, chief_complaint, hpi_summary, "
    "visual_acuity_od, visual_acuity_os, iop_od, iop_os, "
    "structured_json, extraction_confidence, created_at"
)
NOTE_COLUMNS = (
    "id, encounter_id, version_number, draft_status, note_format, "
    "note_text, generated_note_text, source_input_id, "
    "extracted_findings_id, generated_by, "
    "provider_review_required, missing_data_flags, signed_at, "
    "signed_by_user_id, exported_at, created_at, updated_at"
)


def _findings_row_to_dict(row: dict) -> dict:
    d = dict(row)
    try:
        d["structured_json"] = _json.loads(d.get("structured_json") or "{}")
    except Exception:
        d["structured_json"] = {}
    return d


def _note_row_to_dict(row: dict) -> dict:
    d = dict(row)
    raw = d.get("missing_data_flags")
    try:
        d["missing_data_flags"] = _json.loads(raw) if raw else []
    except Exception:
        d["missing_data_flags"] = []
    return d


def _assert_note_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = NOTE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise _err(
            "invalid_note_transition",
            f"cannot move note from {current!r} to {target!r}",
            400,
        )


# ---------------------------------------------------------------------------
# Encounter inputs
# ---------------------------------------------------------------------------

class EncounterInputCreate(BaseModel):
    input_type: str = Field(..., description="one of INPUT_TYPES")
    transcript_text: Optional[str] = None
    processing_status: Optional[str] = Field(default=None)
    confidence_summary: Optional[str] = Field(default=None, max_length=32)
    source_metadata: Optional[dict[str, Any]] = None


@router.post(
    "/encounters/{encounter_id}/inputs",
    status_code=status.HTTP_201_CREATED,
)
def create_encounter_input(
    encounter_id: int,
    payload: EncounterInputCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    # Same RBAC as event-creation — clinicians + admins can ingest;
    # reviewers are read-only.
    require_create_event(caller)
    _load_encounter_for_caller(encounter_id, caller)  # 404 if cross-org

    if payload.input_type not in INPUT_TYPES:
        raise _err(
            "invalid_input_type",
            f"input_type must be one of {sorted(INPUT_TYPES)}",
            400,
        )
    requested_status = payload.processing_status or _default_status(payload)
    if requested_status not in INPUT_STATUSES:
        raise _err(
            "invalid_processing_status",
            f"processing_status must be one of {sorted(INPUT_STATUSES)}",
            400,
        )
    if payload.input_type in {"text_paste", "manual_entry", "imported_transcript"}:
        if not (payload.transcript_text or "").strip():
            raise _err(
                "transcript_required",
                f"input_type={payload.input_type!r} requires transcript_text",
                400,
            )

    # Every input now enters the pipeline at `queued`; the ingestion
    # service transitions it through `processing → completed | failed`.
    # Callers can still override to `queued` explicitly for an audio
    # upload that hasn't been dispatched yet, but cannot ship a row
    # straight to `completed` — the pipeline owns that transition.
    initial_status = requested_status if requested_status == "queued" else "queued"

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "encounter_inputs",
            {
                "encounter_id": encounter_id,
                "input_type": payload.input_type,
                "processing_status": initial_status,
                "transcript_text": payload.transcript_text,
                "confidence_summary": payload.confidence_summary,
                "source_metadata": (
                    _json.dumps(payload.source_metadata, sort_keys=True)
                    if payload.source_metadata is not None
                    else None
                ),
                "created_by_user_id": caller.user_id,
            },
        )

    from app import audit as _audit
    _audit.record(
        event_type="encounter_input_created",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounters/{encounter_id}/inputs",
        method="POST",
        detail=f"input_type={payload.input_type}",
    )

    # Text-type inputs have all the material the pipeline needs now —
    # run it inline so existing callers (and tests) see `completed`.
    # Audio uploads stay `queued` for a future STT worker to pick up.
    # Failures are persisted on the row; the HTTP response carries the
    # terminal state either way. We do NOT raise — the row is created,
    # the pipeline outcome is inspectable on the returned body.
    if payload.input_type in {"text_paste", "manual_entry", "imported_transcript"}:
        from app.services import ingestion as _ingest
        try:
            _ingest.run_ingestion_now(new_id)
        except _ingest.IngestionError:
            # Swallow — the failed row is persisted and the client
            # sees `processing_status=failed` + `last_error_code` in
            # the response. Retrying is an explicit operator action.
            pass

    row = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": new_id},
    )
    return row


def _default_status(payload: "EncounterInputCreate") -> str:
    # Everything enters at `queued` now; the pipeline owns all
    # transitions. Kept as a named helper so the contract remains
    # grep-able when vendors plug in.
    return "queued"


@router.get("/encounters/{encounter_id}/inputs")
def list_encounter_inputs(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _load_encounter_for_caller(encounter_id, caller)
    return fetch_all(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs "
        "WHERE encounter_id = :eid ORDER BY id DESC",
        {"eid": encounter_id},
    )


# ---------------------------------------------------------------------------
# Note generation / listing / read / patch / review / sign / export
# ---------------------------------------------------------------------------

class NoteGenerateBody(BaseModel):
    input_id: Optional[int] = Field(
        default=None,
        description="Specific encounter_input to source from. Defaults "
        "to the most recent completed input on the encounter.",
    )
    note_format: Optional[str] = Field(default="soap")


class NotePatchBody(BaseModel):
    note_text: Optional[str] = None
    draft_status: Optional[str] = None
    note_format: Optional[str] = None


class NoteSubmitBody(BaseModel):
    pass


class NoteSignBody(BaseModel):
    pass


def _load_note_for_caller(note_id: int, caller: Caller) -> dict:
    row = fetch_one(
        f"SELECT {NOTE_COLUMNS}, "
        "(SELECT organization_id FROM encounters WHERE id = note_versions.encounter_id) AS _org "
        f"FROM note_versions WHERE id = :id",
        {"id": note_id},
    )
    if row is None or row["_org"] is None:
        raise _err("note_not_found", "no such note version", 404)
    if row["_org"] != caller.organization_id:
        # Same semantics as encounter not-found: cross-org = 404.
        raise _err("note_not_found", "no such note version", 404)
    row = dict(row)
    row.pop("_org", None)
    return _note_row_to_dict(row)


@router.post(
    "/encounters/{encounter_id}/notes/generate",
    status_code=status.HTTP_201_CREATED,
)
def generate_note(
    encounter_id: int,
    payload: NoteGenerateBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    require_create_event(caller)  # admin + clinician only
    enc = _load_encounter_for_caller(encounter_id, caller)

    fmt = payload.note_format or "soap"
    if fmt not in NOTE_FORMATS:
        raise _err(
            "invalid_note_format",
            f"note_format must be one of {sorted(NOTE_FORMATS)}",
            400,
        )

    # Orchestrator owns the pipeline (phase 22). It translates
    # resolution failures (input not found / not ready) into clean
    # error codes we forward straight through.
    from app.services.note_orchestrator import (
        OrchestrationError, run_note_generation,
    )
    try:
        output = run_note_generation(
            encounter_id=encounter_id,
            input_id=payload.input_id,
            patient_display=(
                enc.get("patient_name") or enc.get("patient_identifier") or "<patient>"
            ),
            provider_display=enc.get("provider_name") or "<provider>",
            note_format=fmt,
        )
    except OrchestrationError as e:
        raise _err(e.error_code, e.reason, e.status_code)

    new_note_id = output.note_id
    findings_id = output.findings_id
    next_version = output.version_number

    from app import audit as _audit
    _audit.record(
        event_type="note_version_generated",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounters/{encounter_id}/notes/generate",
        method="POST",
        detail=(
            f"note_id={new_note_id} version={next_version} "
            f"findings_id={findings_id}"
        ),
    )

    note_row = fetch_one(
        f"SELECT {NOTE_COLUMNS} FROM note_versions WHERE id = :id",
        {"id": new_note_id},
    )
    findings_row = fetch_one(
        f"SELECT {FINDINGS_COLUMNS} FROM extracted_findings WHERE id = :id",
        {"id": findings_id},
    )
    return {
        "note": _note_row_to_dict(note_row),
        "findings": _findings_row_to_dict(findings_row),
    }


@router.get("/encounters/{encounter_id}/notes")
def list_encounter_notes(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _load_encounter_for_caller(encounter_id, caller)
    rows = fetch_all(
        f"SELECT {NOTE_COLUMNS} FROM note_versions "
        "WHERE encounter_id = :eid ORDER BY version_number DESC",
        {"eid": encounter_id},
    )
    return [_note_row_to_dict(r) for r in rows]


@router.get("/note-versions/{note_id}")
def get_note_version(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    note = _load_note_for_caller(note_id, caller)
    findings = None
    if note.get("extracted_findings_id"):
        row = fetch_one(
            f"SELECT {FINDINGS_COLUMNS} FROM extracted_findings WHERE id = :id",
            {"id": note["extracted_findings_id"]},
        )
        if row:
            findings = _findings_row_to_dict(row)
    return {"note": note, "findings": findings}


@router.patch("/note-versions/{note_id}")
def patch_note_version(
    note_id: int,
    payload: NotePatchBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    require_create_event(caller)
    note = _load_note_for_caller(note_id, caller)

    if note["draft_status"] in {"signed", "exported"}:
        raise _err(
            "note_immutable",
            f"note is {note['draft_status']!r} and cannot be edited; "
            "regenerate or start a revision",
            409,
        )

    updates: dict[str, Any] = {"updated_at": text("CURRENT_TIMESTAMP")}  # type: ignore[dict-item]
    set_parts: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": note_id}

    if payload.note_text is not None:
        set_parts.append("note_text = :text")
        params["text"] = payload.note_text
        # Any provider edit promotes "draft" → "revised" implicitly, so
        # the UI can distinguish generator output from provider-edited.
        if note["draft_status"] == "draft":
            set_parts.append("draft_status = 'revised'")
            set_parts.append("generated_by = 'manual'")

    if payload.note_format is not None:
        if payload.note_format not in NOTE_FORMATS:
            raise _err(
                "invalid_note_format",
                f"note_format must be one of {sorted(NOTE_FORMATS)}",
                400,
            )
        set_parts.append("note_format = :fmt")
        params["fmt"] = payload.note_format

    if payload.draft_status is not None:
        if payload.draft_status not in NOTE_STATUSES:
            raise _err(
                "invalid_note_status",
                f"draft_status must be one of {sorted(NOTE_STATUSES)}",
                400,
            )
        _assert_note_transition(note["draft_status"], payload.draft_status)
        set_parts.append("draft_status = :ds")
        params["ds"] = payload.draft_status

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE note_versions SET {', '.join(set_parts)} "
                "WHERE id = :id"
            ),
            params,
        )

    updated = _load_note_for_caller(note_id, caller)
    return updated


@router.post("/note-versions/{note_id}/submit-for-review")
def submit_note_for_review(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    require_create_event(caller)
    note = _load_note_for_caller(note_id, caller)
    _assert_note_transition(note["draft_status"], "provider_review")
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET draft_status = 'provider_review', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": note_id},
        )

    from app import audit as _audit
    _audit.record(
        event_type="note_version_submitted",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/submit-for-review",
        method="POST",
        detail=f"note_id={note_id}",
    )
    return _load_note_for_caller(note_id, caller)


@router.post("/note-versions/{note_id}/sign")
def sign_note(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    # Only admin + clinician can sign — reviewers can read notes but
    # cannot legally attest to the content.
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_sign",
            "only admin or clinician may sign a note version",
            403,
        )
    note = _load_note_for_caller(note_id, caller)
    if note["draft_status"] == "signed":
        raise _err("note_already_signed", "note is already signed", 409)
    if note["draft_status"] not in {"draft", "provider_review", "revised"}:
        raise _err(
            "invalid_note_transition",
            f"cannot sign from {note['draft_status']!r}",
            400,
        )

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET "
                "draft_status = 'signed', "
                "signed_at = CURRENT_TIMESTAMP, "
                "signed_by_user_id = :uid, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": note_id, "uid": caller.user_id},
        )

    from app import audit as _audit
    _audit.record(
        event_type="note_version_signed",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/sign",
        method="POST",
        detail=f"note_id={note_id} version={note['version_number']}",
    )
    return _load_note_for_caller(note_id, caller)


@router.post("/note-versions/{note_id}/export")
def export_note(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Mark a signed note as handed off (copy/download/paste etc.).

    Export is a separate state from sign: the provider may sign at
    11:07 and hand off to the EHR at 11:30, and we want both timestamps.
    """
    require_create_event(caller)
    note = _load_note_for_caller(note_id, caller)
    if note["draft_status"] != "signed":
        raise _err(
            "note_not_signed",
            "only signed notes can be exported",
            409,
        )
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET draft_status = 'exported', "
                "exported_at = CURRENT_TIMESTAMP, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": note_id},
        )

    from app import audit as _audit
    _audit.record(
        event_type="note_version_exported",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/export",
        method="POST",
        detail=f"note_id={note_id}",
    )
    return _load_note_for_caller(note_id, caller)


# ===========================================================================
# Signed-note artifact (phase 25)
# ===========================================================================
#
# GET /note-versions/{id}/artifact?format=json|text|fhir
#
# Returns a packaged, provenance-bearing view of a signed note. Three
# format variants share a single canonical builder:
#
#   json  → application/vnd.chartnav.signed-note+json  (default)
#   text  → text/plain; charset=utf-8
#   fhir  → application/fhir+json  (DocumentReference R4)
#
# This is a **read**. It does not mutate state — the existing POST
# /export endpoint continues to own the state transition
# draft_status=signed → exported. Artifact retrieval can happen before
# or after that transition; both are operationally valid.
#
# Org scoping reuses the same cross-org → 404 contract as other note
# reads. Unsigned notes return 409 `note_not_signed` — the point of the
# artifact is to package a clinician-attested document; half-attested
# is not a thing ChartNav emits.

@router.get("/note-versions/{note_id}/artifact")
def get_note_artifact(
    note_id: int,
    response: Response,
    format: Optional[str] = Query(None, description="json | text | fhir"),
    caller: Caller = Depends(require_caller),
):
    from app.services.note_artifact import ArtifactError, build_for_format

    try:
        body, mime, variant = build_for_format(
            note_id=note_id,
            format_variant=format,
            caller_email=caller.email,
            caller_user_id=caller.user_id,
            caller_organization_id=caller.organization_id,
        )
    except ArtifactError as e:
        raise _err(e.error_code, e.reason, e.status_code)

    from app import audit as _audit
    _audit.record(
        event_type="note_version_artifact_issued",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/artifact",
        method="GET",
        detail=f"note_id={note_id} format={variant}",
    )

    # All three variants need a custom Content-Type. Text goes through
    # the generic Response so it isn't double-encoded; json + fhir go
    # through JSONResponse with an explicit media_type so downstream
    # clients can distinguish a ChartNav canonical artifact
    # (``application/vnd.chartnav.signed-note+json``) from a generic
    # FHIR document (``application/fhir+json``).
    extra_headers = {
        "X-ChartNav-Artifact-Variant": variant,
        "X-ChartNav-Artifact-Type": "chartnav.signed_note.v1",
    }
    if isinstance(body, str):
        return Response(content=body, media_type=mime, headers=extra_headers)
    return JSONResponse(content=body, media_type=mime, headers=extra_headers)


# ===========================================================================
# Signed-note transmission (phase 26)
# ===========================================================================
#
# POST /note-versions/{id}/transmit          — initiate a transmission
# GET  /note-versions/{id}/transmissions     — list attempts for a note
#
# This is the **write path**. It reuses the phase-25 artifact builder
# for the payload, routes to the adapter's `transmit_artifact` method,
# and persists the outcome (success OR failure) into
# `note_transmissions`. A failed remote call is a normal business
# event, not an exception — the UI renders it from the same row shape.
#
# Gating is strict:
# - caller role: admin | clinician (reviewers can read the history
#   but cannot initiate transmissions)
# - platform mode: `integrated_writethrough` only
# - note: signed (or exported); unsigned → 409
# - adapter: must advertise `supports_document_transmit`
# - idempotency: a succeeded transmission blocks further attempts
#   unless the caller passes `force=true`


class NoteTransmitBody(BaseModel):
    force: bool = False


def _load_note_transmission_for_caller(
    transmission: dict[str, Any], caller: Caller
) -> dict[str, Any]:
    """Apply the same cross-org → 404 mask as other note-derived rows."""
    if transmission.get("organization_id") != caller.organization_id:
        raise _err(
            "transmission_not_found",
            "no such transmission",
            404,
        )
    return transmission


@router.post("/note-versions/{note_id}/transmit", status_code=status.HTTP_200_OK)
def transmit_note_version(
    note_id: int,
    payload: NoteTransmitBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    from app.services.note_transmit import (
        RunTransmissionInput,
        TransmissionError,
        run_transmission,
    )

    # Pre-check: confirm the note is visible to this caller at all.
    # Reuses the existing cross-org → 404 mask so a 403 on the role
    # check never leaks existence of another org's note.
    _load_note_for_caller(note_id, caller)

    try:
        row = run_transmission(
            RunTransmissionInput(
                note_version_id=note_id,
                caller_email=caller.email,
                caller_user_id=caller.user_id,
                caller_organization_id=caller.organization_id,
                caller_role=caller.role,
                force=payload.force,
            )
        )
    except TransmissionError as e:
        raise _err(e.error_code, e.reason, e.status_code)

    from app import audit as _audit
    _audit.record(
        event_type="note_version_transmitted",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/transmit",
        method="POST",
        detail=(
            f"note_id={note_id} transmission_id={row.get('id')} "
            f"adapter={row.get('adapter_key')} "
            f"status={row.get('transport_status')} "
            f"attempt={row.get('attempt_number')}"
        ),
    )
    return row


@router.get("/note-versions/{note_id}/transmissions")
def list_note_transmissions(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    # Reuse the note-level cross-org mask — if the note itself is not
    # visible to this caller, neither are its transmissions.
    _load_note_for_caller(note_id, caller)

    from app.services.note_transmit import list_transmissions_for_note

    rows = list_transmissions_for_note(
        note_version_id=note_id,
        organization_id=caller.organization_id,
    )
    return rows


# ===========================================================================
# Async ingestion lifecycle (phase 22)
# ===========================================================================

@router.post("/encounter-inputs/{input_id}/process", status_code=status.HTTP_200_OK)
def process_encounter_input(
    input_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Synchronously run the ingestion pipeline for a queued input.

    Primary use: audio uploads that a worker would normally pick up.
    Operators can also call this against text-type rows to retry
    after a failed run — call `retry` first to flip `failed` →
    `queued`, then `process`.
    """
    require_create_event(caller)

    row = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    if row is None:
        raise _err("input_not_found", "no such encounter input", 404)
    _load_encounter_for_caller(row["encounter_id"], caller)  # scope

    from app.services import ingestion as _ingest
    try:
        _ingest.run_ingestion_now(input_id)
    except _ingest.IngestionError as e:
        # Pipeline already persisted the terminal state on the row.
        # Still surface the error code to the client so they know
        # the current attempt failed.
        updated = fetch_one(
            f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
            {"id": input_id},
        )
        return {"input": updated, "ingestion_error": {
            "error_code": e.error_code, "reason": e.reason,
        }}

    updated = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    return {"input": updated, "ingestion_error": None}


@router.post("/encounter-inputs/{input_id}/retry", status_code=status.HTTP_200_OK)
def retry_encounter_input(
    input_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Flip a `failed` / `needs_review` input back to `queued` + increment retry_count.

    Does NOT automatically re-run the pipeline; callers chain this
    with `POST /encounter-inputs/{id}/process` for the full retry.
    """
    require_create_event(caller)

    row = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    if row is None:
        raise _err("input_not_found", "no such encounter input", 404)
    _load_encounter_for_caller(row["encounter_id"], caller)

    from app.services import ingestion as _ingest
    try:
        _ingest.enqueue_input(input_id)
    except _ingest.NotReadyToProcess as e:
        raise _err(e.error_code, e.reason, 409)
    except _ingest.IngestionError as e:
        raise _err(e.error_code, e.reason, 400)

    from app import audit as _audit
    _audit.record(
        event_type="encounter_input_retried",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounter-inputs/{input_id}/retry",
        method="POST",
        detail=f"input_id={input_id}",
    )

    updated = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    return updated


# ===========================================================================
# Background worker surfaces + bridged-encounter refresh (phase 23)
# ===========================================================================

@router.post("/workers/tick", status_code=status.HTTP_200_OK)
def worker_tick(caller: Caller = Depends(require_caller)) -> dict:
    """Claim-and-process one queued input.

    Admin-only HTTP hook for driving the worker remotely (ops
    console, smoke tests, scheduled cron calling curl). A deployment
    with a real worker process calls `app.services.worker.run_one()`
    directly; this endpoint is the same function behind HTTP so
    operators aren't locked out.

    Returns `{processed: bool, ...tick}` — `processed=false` means
    the queue was empty. Always 200 regardless of success or
    failure of the claimed row (the row itself carries the terminal
    state in `last_error` / `last_error_code`).
    """
    require_admin(caller)
    from app.services import worker as _worker

    tick = _worker.run_one()
    if tick is None:
        return {"processed": False, "queue_empty": True}
    return {
        "processed": True,
        "input_id": tick.input_id,
        "status": tick.status,
        "ingestion_error": tick.ingestion_error,
    }


@router.post("/workers/drain", status_code=status.HTTP_200_OK)
def worker_drain(caller: Caller = Depends(require_caller)) -> dict:
    """Drain the queue. Returns the run summary.

    Admin-only. Capped at 100 ticks by the service layer so a
    runaway queue can't spin the process forever. Safe to call from
    a cron or a smoke script. Not cheap — never put this on a user
    request path.
    """
    require_admin(caller)
    from app.services import worker as _worker

    summary = _worker.run_until_empty()
    return summary


@router.post("/workers/requeue-stale", status_code=status.HTTP_200_OK)
def worker_requeue_stale(caller: Caller = Depends(require_caller)) -> dict:
    """Recover any stale `processing` rows.

    Stale = claim older than `CHARTNAV_WORKER_CLAIM_TTL_SECONDS`
    (default 900s = 15 minutes). Idempotent; safe to call on every
    worker-tick or from a recovery cron.
    """
    require_admin(caller)
    from app.services import worker as _worker

    n = _worker.requeue_stale_claims()
    return {"recovered": int(n)}


class BridgeRefreshBody(BaseModel):
    """Optional body for /encounters/{id}/refresh.

    Reserved for future knobs (e.g. `dry_run: bool`); today the
    request carries no parameters but having the model means we can
    extend without breaking clients.
    """
    pass


@router.post("/encounters/{encounter_id}/refresh", status_code=status.HTTP_200_OK)
def refresh_bridged_encounter(
    encounter_id: int,
    payload: BridgeRefreshBody | None = None,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Re-fetch the external shell + reconcile mirror fields.

    Only works on bridged encounters (rows with `external_ref` +
    `external_source` set). Preserves source-of-truth:
    ChartNav-native workflow is untouched; only the mirror fields
    (`patient_identifier`, `patient_name`, `provider_name`, `status`)
    can change. Admin + clinician can invoke; reviewer cannot.

    Refuses with 409 `not_bridged` on standalone-native rows, 404
    `encounter_not_found` cross-org, 409 `external_source_mismatch`
    if the deployment's active adapter no longer matches the
    historical source.
    """
    require_create_event(caller)
    _load_encounter_for_caller(encounter_id, caller)  # scope + 404

    from app.services.bridge_sync import (
        BridgeRefreshError,
        refresh_bridged_encounter as _refresh,
    )

    try:
        result = _refresh(
            native_id=encounter_id,
            organization_id=caller.organization_id,
        )
    except BridgeRefreshError as e:
        raise _err(e.error_code, e.reason, e.status_code)

    from app import audit as _audit
    _audit.record(
        event_type="encounter_refreshed",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounters/{encounter_id}/refresh",
        method="POST",
        detail=(
            f"native_id={encounter_id} refreshed={result['refreshed']} "
            f"mirrored={list(result['mirrored'].keys())}"
        ),
    )
    return result


# ===========================================================================
# Clinician quick-comment pad (phase 27)
# ===========================================================================
#
# Per-user, org-scoped bag of short reusable comment snippets the
# clinician can click into a draft. NOT linked to any encounter or
# note version — these are a doctor's personal clipboard. The 50
# preloaded ophthalmology picks are UI content shipped with the
# frontend; this table only stores what the doctor explicitly wrote.
#
# Visibility: each user sees only their own comments. There is no
# "shared organization library" surface today (keep scope narrow).
# A cross-user lookup of someone else's comment — even in the same
# org — returns 404, same masking contract as other note-scoped rows.


QC_COLUMNS = (
    "id, organization_id, user_id, body, is_active, "
    "created_at, updated_at"
)
QC_MAX_BODY_CHARS = 2000


class QuickCommentBody(BaseModel):
    body: str = Field(..., min_length=1, max_length=QC_MAX_BODY_CHARS)


class QuickCommentPatchBody(BaseModel):
    body: Optional[str] = Field(None, min_length=1, max_length=QC_MAX_BODY_CHARS)
    is_active: Optional[bool] = None


def _require_quick_comment_role(caller: Caller) -> None:
    # Reviewers cannot author clinician comments — keep the seam
    # consistent with the sign/patch rules.
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_edit_quick_comments",
            "only admin or clinician may author quick comments",
            403,
        )


def _load_quick_comment_for_caller(
    comment_id: int, caller: Caller
) -> dict[str, Any]:
    row = fetch_one(
        f"SELECT {QC_COLUMNS} FROM clinician_quick_comments WHERE id = :id",
        {"id": comment_id},
    )
    if row is None:
        raise _err("quick_comment_not_found", "no such quick comment", 404)
    row = dict(row)
    # Mask cross-user + cross-org behind a 404 — mirrors the
    # note-not-found pattern so existence of another user's comment
    # is never leaked via status code.
    if (
        row["organization_id"] != caller.organization_id
        or row["user_id"] != caller.user_id
    ):
        raise _err("quick_comment_not_found", "no such quick comment", 404)
    return row


@router.get("/me/quick-comments")
def list_my_quick_comments(
    include_inactive: bool = Query(False, description="Include soft-deleted"),
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _require_quick_comment_role(caller)
    sql = (
        f"SELECT {QC_COLUMNS} FROM clinician_quick_comments "
        "WHERE organization_id = :org AND user_id = :uid"
    )
    params: dict[str, Any] = {
        "org": caller.organization_id,
        "uid": caller.user_id,
    }
    if not include_inactive:
        sql += " AND is_active = :active"
        params["active"] = True
    sql += " ORDER BY updated_at DESC, id DESC"
    rows = fetch_all(sql, params)
    return [dict(r) for r in rows]


@router.post("/me/quick-comments", status_code=status.HTTP_201_CREATED)
def create_my_quick_comment(
    payload: QuickCommentBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_quick_comment_role(caller)
    body = payload.body.strip()
    if not body:
        raise _err(
            "quick_comment_body_required",
            "body is required and must be non-empty",
            400,
        )

    with transaction() as conn:
        new_id = conn.execute(
            text(
                "INSERT INTO clinician_quick_comments "
                "(organization_id, user_id, body, is_active) "
                "VALUES (:org, :uid, :body, :active) RETURNING id"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "body": body,
                "active": True,
            },
        ).mappings().first()["id"]

    from app import audit as _audit
    _audit.record(
        event_type="clinician_quick_comment_created",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/quick-comments",
        method="POST",
        detail=f"quick_comment_id={new_id} chars={len(body)}",
    )

    return _load_quick_comment_for_caller(int(new_id), caller)


@router.patch("/me/quick-comments/{comment_id}")
def update_my_quick_comment(
    comment_id: int,
    payload: QuickCommentPatchBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_quick_comment_role(caller)
    existing = _load_quick_comment_for_caller(comment_id, caller)

    set_parts: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": comment_id}
    changed: list[str] = []

    if payload.body is not None:
        body = payload.body.strip()
        if not body:
            raise _err(
                "quick_comment_body_required",
                "body must be non-empty",
                400,
            )
        set_parts.append("body = :body")
        params["body"] = body
        changed.append("body")
    if payload.is_active is not None:
        set_parts.append("is_active = :active")
        params["active"] = payload.is_active
        changed.append("is_active")

    if not changed:
        # Noop — return the unchanged row so the client can refresh
        # without thinking about 304 semantics.
        return existing

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE clinician_quick_comments SET "
                f"{', '.join(set_parts)} "
                "WHERE id = :id"
            ),
            params,
        )

    from app import audit as _audit
    _audit.record(
        event_type="clinician_quick_comment_updated",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/me/quick-comments/{comment_id}",
        method="PATCH",
        detail=f"quick_comment_id={comment_id} changed={','.join(changed)}",
    )

    return _load_quick_comment_for_caller(comment_id, caller)


@router.delete("/me/quick-comments/{comment_id}")
def delete_my_quick_comment(
    comment_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    # Soft delete via is_active=false. Mirrors the pattern used for
    # locations + users so audit/history queries still resolve refs.
    _require_quick_comment_role(caller)
    existing = _load_quick_comment_for_caller(comment_id, caller)
    if not existing["is_active"]:
        # Already deleted; idempotent.
        return existing

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE clinician_quick_comments SET "
                "is_active = :active, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": comment_id, "active": False},
        )

    from app import audit as _audit
    _audit.record(
        event_type="clinician_quick_comment_deleted",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/me/quick-comments/{comment_id}",
        method="DELETE",
        detail=f"quick_comment_id={comment_id} soft=true",
    )

    return _load_quick_comment_for_caller(comment_id, caller)
