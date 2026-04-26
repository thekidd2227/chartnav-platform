from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
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
    "scheduled_at, started_at, completed_at, created_at, "
    "template_key"
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
    # Phase A item 1 — encounter templates. If unset the row defaults
    # to "general_ophthalmology" via the column default; an unknown
    # key is rejected with 400 so we never silently fall back to a
    # different specialty than the caller asked for.
    template_key: Optional[str] = Field(default=None, max_length=64)


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
        # Wave 7: explicit org-granted privilege to perform final
        # physician approval. UI uses this to surface the dedicated
        # approval affordance and hide it for everyone else.
        "is_authorized_final_signer": bool(caller.is_authorized_final_signer),
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


# ---------- Encounter templates (Phase A item 1) ----------
#
# Spec: docs/chartnav/closure/PHASE_A_Ophthalmology_Encounter_Templates.md
#
# Read-only catalog. Any authenticated caller may read it because the
# template list is needed by the create-encounter modal for every
# clinic role that can create encounters (admin / clinician / front_desk).
# The advisor-review banner discipline lives on the frontend; backend
# returns the truth that the list is ChartNav-curated, not a clinical
# validation marker.

@router.get("/encounter-templates")
def list_encounter_templates(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Return the four ChartNav-curated ophthalmology templates.

    The response shape is intentionally stable — the frontend renders
    the selector directly off ``items``. ``advisory_only`` is a
    persistent reminder that templates are not clinically validated
    until a practicing ophthalmologist advisor sign-off is recorded.
    """
    from app.services.encounter_templates import (  # local import to avoid cycle
        list_templates,
        DEFAULT_TEMPLATE_KEY,
    )
    return {
        "items": list_templates(),
        "default_key": DEFAULT_TEMPLATE_KEY,
        "advisory_only": True,
        "advisor_review_status": "pending",
    }


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


# ---------- Phase A item 3 — encounter revisions + immutability ----------
#
# Spec: docs/chartnav/closure/PHASE_A_Structured_Charting_and_Attestation.md
#
# §4 Acceptance criteria:
#   - GET /encounters/{id}/revisions  -> revision list, newest first
#     Visible to admin / clinician (author or same-org) / reviewer
#     same-org. Forbidden for front_desk and technician.
#   - PATCH /encounters/{id} on a signed encounter -> 409 with
#     {"error_code": "ENCOUNTER_LOCKED_AFTER_SIGN", "signed_at": ...}.

class EncounterPatchBody(BaseModel):
    """Mutable fields on the encounter row.

    Phase A only exposes ``template_key`` here — the only structured
    field on the row today. Future structured-fields work attaches via
    the same gate. Identity/scheduling fields live on dedicated
    routes and are not patchable through this surface.
    """
    template_key: Optional[str] = Field(default=None, max_length=64)
    reason: Optional[str] = Field(default=None, max_length=512)


@router.patch("/encounters/{encounter_id}")
def patch_encounter(
    encounter_id: int,
    payload: EncounterPatchBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Patch an encounter's structured fields. Refused after sign."""
    from app.services.encounter_audit import (
        is_encounter_signed,
        encounter_signed_at,
        record_revision,
    )
    from app.services.encounter_templates import is_valid_template_key

    encounter = _load_encounter_for_caller(encounter_id, caller)

    # §4 immutability gate. The encounter is "signed" once any of its
    # note_versions has a non-null signed_at OR the encounter status
    # is `completed`. We surface the older of the two timestamps so
    # auditors can reproduce the lock decision.
    if is_encounter_signed(encounter):
        with transaction() as conn:
            sa_ts = encounter_signed_at(conn, encounter_id) or str(
                encounter.get("completed_at") or encounter.get("created_at")
            )
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "ENCOUNTER_LOCKED_AFTER_SIGN",
                "reason": "this encounter has been signed; further "
                          "structured-field mutations are refused",
                "signed_at": sa_ts,
            },
        )

    # Role gate: clinicians + admins can mutate template_key pre-sign.
    # Front_desk + technician + biller_coder + reviewer cannot.
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_patch_encounter",
            f"role '{caller.role}' may not patch encounter structured fields",
            403,
        )

    set_parts: list[str] = []
    params: dict[str, Any] = {"id": encounter_id}
    revisions_to_record: list[tuple[str, Any, Any]] = []

    if payload.template_key is not None:
        if not is_valid_template_key(payload.template_key):
            raise _err(
                "unknown_template_key",
                "template_key must be one of: retina, glaucoma, "
                "anterior_segment_cataract, general_ophthalmology",
                400,
            )
        if payload.template_key != encounter.get("template_key"):
            set_parts.append("template_key = :template_key")
            params["template_key"] = payload.template_key
            revisions_to_record.append(
                ("template_key", encounter.get("template_key"), payload.template_key)
            )

    if not set_parts:
        return encounter

    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE encounters SET {', '.join(set_parts)} "
                "WHERE id = :id"
            ),
            params,
        )
        for field_path, before, after in revisions_to_record:
            record_revision(
                conn,
                encounter_id=encounter_id,
                actor_user_id=caller.user_id,
                field_path=field_path,
                before=before,
                after=after,
                reason=payload.reason,
            )

    return _load_encounter_for_caller(encounter_id, caller)


# ---------- Phase A item 4 — PM/RCM continuity export ------------------
#
# Spec: docs/chartnav/closure/PHASE_A_PM_RCM_Continuity_and_Integration_Path.md
#
# Truth boundary repeated: NO PM/RCM integration ships in Phase A.
# Nothing in this code path sends a claim. The export is a manual
# handoff bundle the biller imports by hand.

@router.post("/encounters/{encounter_id}/export", status_code=200)
def export_encounter_handoff(
    encounter_id: int,
    fmt: str = "json",
    caller: Caller = Depends(require_caller),
) -> Any:
    """Produce the canonical handoff payload for a signed encounter.

    Query string ``fmt`` selects the response shape:
      json (default) — JSON object
      csv            — text/csv (single-row superbill)
      pdf            — application/pdf (single-page minimal PDF)
      manifest       — JSON object describing the available formats

    Refused with 409 if the encounter is not signed yet.
    Refused with 403 if the caller's role is not in CAN_EXPORT_HANDOFF.
    """
    from app.authz import CAN_EXPORT_HANDOFF
    from app.services.handoff_export import (
        build_handoff_payload,
        render_csv,
        render_pdf_body,
        render_pdf_bytes,
        get_signed_note_text,
    )
    encounter = _load_encounter_for_caller(encounter_id, caller)

    if caller.role not in CAN_EXPORT_HANDOFF:
        raise _err(
            "role_cannot_export_handoff",
            f"role '{caller.role}' may not export the PM/RCM handoff bundle",
            403,
        )

    try:
        payload = build_handoff_payload(encounter_id)
    except ValueError as e:
        # No signed-attestation row yet ⇒ encounter is not signed.
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "encounter_not_signed",
                "reason": str(e),
            },
        )

    if fmt == "csv":
        body = render_csv(payload)
        return Response(content=body, media_type="text/csv")
    if fmt == "pdf":
        text_body = render_pdf_body(payload, get_signed_note_text(encounter_id))
        body = render_pdf_bytes(text_body)
        return Response(content=body, media_type="application/pdf")
    if fmt == "manifest":
        return {
            "encounter_id": encounter_id,
            "schema_version": payload["schema_version"],
            "formats": {
                "json": f"/encounters/{encounter_id}/export?fmt=json",
                "csv": f"/encounters/{encounter_id}/export?fmt=csv",
                "pdf": f"/encounters/{encounter_id}/export?fmt=pdf",
            },
            "advisory_only": True,
            "no_pm_rcm_integration": True,
        }
    return payload


@router.get("/encounters/{encounter_id}/revisions")
def list_encounter_revisions(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Return the encounter's edit history.

    Visible to admin / clinician / reviewer same-org. Front desk +
    technician + biller_coder are refused so the audit surface stays
    confined to roles that read the clinical record.
    """
    _load_encounter_for_caller(encounter_id, caller)
    if caller.role not in {"admin", "clinician", "reviewer"}:
        raise _err(
            "role_cannot_read_revisions",
            f"role '{caller.role}' may not read encounter revisions",
            403,
        )
    from app.services.encounter_audit import (
        list_revisions_for_encounter,
        get_attestation_for_encounter,
    )
    return {
        "encounter_id": encounter_id,
        "items": list_revisions_for_encounter(encounter_id),
        "attestation": get_attestation_for_encounter(encounter_id),
    }


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

    # Phase A item 1 — encounter templates. Reject unknown keys with 400
    # so a typo at the modal never silently writes the wrong specialty.
    # If the caller omits the key the column default
    # ("general_ophthalmology") applies on the INSERT.
    from app.services.encounter_templates import is_valid_template_key  # local import to avoid cycle
    if payload.template_key is not None and not is_valid_template_key(payload.template_key):
        raise _err(
            "unknown_template_key",
            "template_key must be one of: retina, glaucoma, "
            "anterior_segment_cataract, general_ophthalmology",
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

        encounter_payload: dict[str, Any] = {
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
        }
        if payload.template_key is not None:
            encounter_payload["template_key"] = payload.template_key
        new_id = insert_returning_id(conn, "encounters", encounter_payload)

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

NOTE_FORMATS = {"soap", "assessment_plan", "consult_note", "freeform"}

# Phase 54 — canonical lifecycle unification.
#
# The authoritative set of lifecycle states AND the allowed
# transitions live in `app.services.note_lifecycle`. Routes MUST NOT
# redefine either. Earlier phases kept a parallel `NOTE_STATUSES`
# set and `NOTE_TRANSITIONS` dict here; both have been removed in
# favour of a single source of truth.
#
# If you need to validate a status string: `status in LIFECYCLE_STATES`.
# If you need to validate a transition: `can_transition(cur, tgt)`.
# If you need to authorize a transition: `role_permits_edge(cur, tgt, role)`.
from app.services.note_lifecycle import (  # noqa: E402 — pinned to public surface
    LIFECYCLE_STATES as NOTE_STATUSES,
    can_transition as _canonical_can_transition,
)


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
    "signed_by_user_id, exported_at, created_at, updated_at, "
    # Phase 49 — lifecycle governance columns.
    "reviewed_at, reviewed_by_user_id, content_fingerprint, "
    "attestation_text, amended_at, amended_by_user_id, "
    "amended_from_note_id, amendment_reason, "
    "superseded_at, superseded_by_note_id, "
    # Phase 52 — Wave 7 final-approval columns.
    "final_approval_status, final_approved_at, final_approved_by_user_id, "
    "final_approval_signature_text, final_approval_invalidated_at, "
    "final_approval_invalidated_reason"
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
    """Phase 54 — thin adapter that delegates to the canonical
    lifecycle service. Kept as a named helper so existing call sites
    (PATCH /note-versions/{id}, POST submit-for-review) read
    identically, but the rule table they enforce is now the one and
    only `LIFECYCLE_TRANSITIONS` in `note_lifecycle.py`.
    """
    if current == target:
        return
    edge_err = _canonical_can_transition(current, target)
    if edge_err is not None:
        raise _err("invalid_note_transition", edge_err, 400)


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


@router.get("/encounter-inputs/{input_id:int}")
def get_encounter_input(
    input_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Single-row read for an `encounter_inputs` row.

    Phase-35 addition. Both mobile and desktop poll the per-row
    state (queued → processing → completed | failed) when async
    ingestion is enabled, so they need a cheap one-row endpoint
    rather than refetching the whole encounter list.

    Cross-org → 404 via the encounter-load helper, same masking
    contract as every other input read.
    """
    row = fetch_one(
        "SELECT ei.*, e.organization_id AS _org "
        "FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE ei.id = :id",
        {"id": input_id},
    )
    if row is None or row.get("_org") != caller.organization_id:
        raise _err(
            "encounter_input_not_found",
            "no such encounter input",
            404,
        )
    out = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    return out


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

    # Phase 54 — immutability after any signed state. Wave 3
    # introduced `amended`; a signed amendment is itself a record of
    # care and must not be edited in place. Legacy code only guarded
    # `signed`/`exported`, which meant PATCH silently passed through
    # on amendment rows — that was a drift site.
    if note["draft_status"] in {"signed", "exported", "amended"}:
        raise _err(
            "note_immutable",
            f"note is {note['draft_status']!r} and cannot be edited; "
            "regenerate or issue an amendment",
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
        # Phase 54 — canonical transition check. Delegates to
        # `can_transition`, so PATCH obeys exactly the same rule table
        # as /sign, /review, /amend, /final-approve, /export.
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
    from app.services.note_lifecycle import (
        compute_release_blockers,
        content_fingerprint,
        default_attestation_text,
        hard_blockers,
        role_permits_edge,
    )

    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_sign",
            "only admin or clinician may sign a note version",
            403,
        )
    note = _load_note_for_caller(note_id, caller)
    current_status = note["draft_status"]

    if not role_permits_edge(current_status, "signed", caller.role):
        raise _err(
            "role_cannot_sign_from_state",
            f"role {caller.role!r} cannot drive sign from state "
            f"{current_status!r}",
            403,
        )

    # Release-gate check. Blockers with severity=error stop the sign;
    # warn-level blockers (e.g. low extraction confidence) surface in
    # the response but do not block — the pre-sign UI checkpoint is
    # where the clinician explicitly acknowledges them.
    findings_row = None
    fid = note.get("extracted_findings_id")
    if fid:
        frow = fetch_one(
            f"SELECT {FINDINGS_COLUMNS} FROM extracted_findings WHERE id = :id",
            {"id": fid},
        )
        findings_row = dict(frow) if frow else None
    blockers = compute_release_blockers(note, findings_row, target="signed")
    hard = hard_blockers(blockers)
    if hard:
        from app import audit as _audit
        _audit.record(
            event_type="note_sign_blocked",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/sign",
            method="POST",
            error_code="sign_blocked_by_gate",
            detail=(
                f"note_id={note_id} version={note['version_number']} "
                f"blockers={sorted({b.code for b in hard})}"
            ),
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "sign_blocked_by_gate",
                "reason": "one or more release gates are blocking this sign",
                "blockers": [b.as_dict() for b in blockers],
            },
        )

    # Freeze the attestation statement + content fingerprint at the
    # moment of the transaction so future reads reproduce what the
    # signer actually attested to. Prefer `full_name` when available
    # — it is the real clinician identifier visible on the chart —
    # and fall back to email for dev/header-auth mode where a user
    # row may have been seeded without full_name.
    signer_display = (caller.full_name or caller.email).strip() or caller.email
    signed_at_iso_preview = datetime.now(timezone.utc).isoformat()
    attestation = default_attestation_text(
        signer_display=signer_display,
        signed_at_iso=signed_at_iso_preview,
    )
    fingerprint = content_fingerprint(note.get("note_text"))

    # Wave 7: every freshly signed note enters the final-approval
    # gate in state `pending`. Export will be blocked until an
    # authorized doctor performs final approval. This is
    # server-authoritative and additive — downstream systems that
    # do not care about the gate simply observe the `signed` state
    # as before.
    from app.services.note_final_approval import approval_state_on_sign
    initial_final_approval = approval_state_on_sign()

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET "
                "draft_status = 'signed', "
                "signed_at = CURRENT_TIMESTAMP, "
                "signed_by_user_id = :uid, "
                "content_fingerprint = :fp, "
                "attestation_text = :att, "
                "final_approval_status = :fa_status, "
                "final_approved_at = NULL, "
                "final_approved_by_user_id = NULL, "
                "final_approval_signature_text = NULL, "
                "final_approval_invalidated_at = NULL, "
                "final_approval_invalidated_reason = NULL, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {
                "id": note_id,
                "uid": caller.user_id,
                "fp": fingerprint,
                "att": attestation,
                "fa_status": initial_final_approval,
            },
        )

        # Phase A item 3 — write the first-class attestation row so
        # the attestation is auditable independently of the note body.
        # docs/chartnav/closure/PHASE_A_Structured_Charting_and_Attestation.md
        from app.services.encounter_audit import record_attestation
        encounter_row = conn.execute(
            text(
                "SELECT id, organization_id, location_id, "
                "patient_identifier, patient_name, provider_name, "
                "status, scheduled_at, started_at, completed_at, "
                "created_at, template_key "
                "FROM encounters WHERE id = :eid"
            ),
            {"eid": int(note["encounter_id"])},
        ).mappings().first()
        if encounter_row:
            record_attestation(
                conn,
                encounter_id=int(note["encounter_id"]),
                encounter_snapshot=dict(encounter_row),
                attested_by_user_id=caller.user_id,
                typed_name=signer_display,
                attestation_text=attestation,
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
        detail=(
            f"note_id={note_id} version={note['version_number']} "
            f"fingerprint={fingerprint[:12]}"
        ),
    )
    # Phase 55 — immutable evidence chain. The general audit log is
    # append-only-by-convention; this chain is tamper-evident.
    try:
        from app.services.note_evidence import (
            EvidenceEventType,
            record_evidence_event,
        )
        record_evidence_event(
            organization_id=caller.organization_id,
            note_version_id=note_id,
            encounter_id=int(note["encounter_id"]),
            event_type=EvidenceEventType.note_signed.value,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            draft_status="signed",
            final_approval_status=initial_final_approval,
            content_fingerprint=fingerprint,
            detail={"version_number": note["version_number"]},
        )
    except Exception:  # pragma: no cover — chain failures never break sign
        import logging as _lg
        _lg.getLogger("chartnav.evidence").warning(
            "evidence chain append failed on sign", exc_info=True
        )
    return _load_note_for_caller(note_id, caller)


@router.post("/note-versions/{note_id}/export")
def export_note(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Mark a signed or amended note as handed off (copy/download/paste etc.).

    Export is a separate state from sign: the provider may sign at
    11:07 and hand off to the EHR at 11:30, and we want both timestamps.
    Amendments (draft_status='amended') can also be exported — once
    an amendment is itself signed upstream, the export action carries
    it through the same audit path.
    """
    require_create_event(caller)
    note = _load_note_for_caller(note_id, caller)

    # Phase 54 — canonical gate. The lifecycle service already
    # encodes "only signed or amended → exported" in
    # `LIFECYCLE_TRANSITIONS`. Route through it rather than inlining
    # the set here; `compute_release_blockers(..., target="exported")`
    # then contributes the Wave 7 final-approval gate on top.
    from app.services.note_lifecycle import (
        compute_release_blockers,
        hard_blockers,
    )
    edge_err = _canonical_can_transition(note["draft_status"], "exported")
    if edge_err is not None:
        raise _err(
            "note_not_signed",
            "only signed or amended notes can be exported",
            409,
        )
    export_blockers = compute_release_blockers(note, None, target="exported")
    export_hard = hard_blockers(export_blockers)
    if export_hard:
        from app import audit as _audit
        _audit.record(
            event_type="note_export_blocked",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/export",
            method="POST",
            error_code="export_blocked_by_gate",
            detail=(
                f"note_id={note_id} version={note['version_number']} "
                f"blockers={sorted({b.code for b in export_hard})}"
            ),
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "export_blocked_by_gate",
                "reason": "one or more release gates are blocking this export",
                "blockers": [b.as_dict() for b in export_blockers],
            },
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
    # Phase 55 — evidence chain append.
    # Phase 56 — export snapshot capture (linked to the chain event).
    evidence_event_id: Optional[int] = None
    try:
        from app.services.note_evidence import (
            EvidenceEventType,
            record_evidence_event,
        )
        ev = record_evidence_event(
            organization_id=caller.organization_id,
            note_version_id=note_id,
            encounter_id=int(note["encounter_id"]),
            event_type=EvidenceEventType.note_exported.value,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            draft_status="exported",
            final_approval_status=note.get("final_approval_status"),
            content_fingerprint=note.get("content_fingerprint"),
            detail={"version_number": note["version_number"]},
        )
        evidence_event_id = ev.id
    except Exception:  # pragma: no cover
        import logging as _lg
        _lg.getLogger("chartnav.evidence").warning(
            "evidence chain append failed on export", exc_info=True
        )

    # Phase 56 — export snapshot. Build the canonical artifact using
    # the existing Phase-25 builder and persist the byte-exact JSON +
    # SHA-256 so the record of what we actually handed off survives
    # later amendments or drift on the source row.
    try:
        from app.services.note_artifact import (
            ArtifactError,
            build_artifact,
        )
        from app.services.note_export_snapshots import persist_snapshot
        artifact = build_artifact(
            note_id=note_id,
            caller_email=caller.email,
            caller_user_id=caller.user_id,
            caller_organization_id=caller.organization_id,
        )
        # Re-read the row post-export-transition so the snapshot
        # reflects draft_status='exported' + exported_at.
        refreshed = _load_note_for_caller(note_id, caller)
        persist_snapshot(
            organization_id=caller.organization_id,
            note_row=refreshed,
            artifact=artifact,
            evidence_chain_event_id=evidence_event_id,
            issued_by_user_id=caller.user_id,
            issued_by_email=caller.email,
        )
    except ArtifactError:
        # The artifact gate refused the build — this should not happen
        # immediately after a successful export, but if it does, the
        # export state already committed and we emit an audit-only
        # trace so the admin plane surfaces the missing snapshot.
        from app import audit as _audit
        _audit.record(
            event_type="note_export_snapshot_failed",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/export",
            method="POST",
            detail=f"note_id={note_id} reason=artifact_gate_refused",
        )
    except Exception:  # pragma: no cover
        import logging as _lg
        _lg.getLogger("chartnav.evidence").warning(
            "export snapshot persist failed", exc_info=True
        )

    return _load_note_for_caller(note_id, caller)


# ---------------------------------------------------------------------------
# Phase 49 — lifecycle governance routes
# ---------------------------------------------------------------------------

class NoteAmendBody(BaseModel):
    note_text: str = Field(..., min_length=10, max_length=40_000)
    reason: str = Field(..., min_length=4, max_length=500)


class NoteFinalApprovalBody(BaseModel):
    # Wave 7 — typed signature. The doctor types their exact stored
    # `full_name`; server compares case-sensitively. `max_length` is a
    # defence-in-depth cap; the actual `users.full_name` column is
    # VARCHAR(255). `min_length=1` is enforced purely to give pydantic
    # a non-empty string; the real mismatch error path comes from the
    # signature comparison service, so the caller sees a consistent
    # structured reason whether they sent "", " ", or a wrong name.
    signature_text: str = Field(..., min_length=1, max_length=255)


@router.get("/note-versions/{note_id}/release-blockers")
def note_release_blockers(
    note_id: int,
    target: str = Query("signed"),
    caller: Caller = Depends(require_caller),
) -> dict:
    """Return the live list of release blockers for this note + target.
    Empty list means the note is clear to transition to `target`."""
    from app.services.note_lifecycle import (
        LIFECYCLE_STATES,
        compute_release_blockers,
        fingerprint_matches,
    )
    if target not in LIFECYCLE_STATES:
        raise _err(
            "invalid_target_state",
            f"target must be one of {sorted(LIFECYCLE_STATES)}",
            400,
        )
    note = _load_note_for_caller(note_id, caller)
    findings_row = None
    fid = note.get("extracted_findings_id")
    if fid:
        frow = fetch_one(
            f"SELECT {FINDINGS_COLUMNS} FROM extracted_findings WHERE id = :id",
            {"id": fid},
        )
        findings_row = dict(frow) if frow else None
    blockers = compute_release_blockers(note, findings_row, target=target)
    fp_status = fingerprint_matches(note)
    return {
        "note_id": note_id,
        "current_status": note.get("draft_status"),
        "target": target,
        "blockers": [b.as_dict() for b in blockers],
        "fingerprint_ok": fp_status,
    }


@router.post("/note-versions/{note_id}/review")
def review_note(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Reviewer (or admin) attests to having reviewed the draft.

    Advances the draft_status to `reviewed` when the transition is
    permitted, and sets `reviewed_at` / `reviewed_by_user_id`. This
    is a first-class governance marker — separate from the
    `provider_review` workflow stage, which only indicates the note
    is *awaiting* review."""
    from app.services.note_lifecycle import (
        can_transition,
        role_permits_edge,
    )
    if caller.role not in {"admin", "reviewer"}:
        raise _err(
            "role_cannot_review",
            "only admin or reviewer may mark a note as reviewed",
            403,
        )
    note = _load_note_for_caller(note_id, caller)
    current = note["draft_status"]
    # Check the lifecycle-order invariant BEFORE the role-from-state
    # guard so the error message the caller sees reflects the real
    # problem (the edge is invalid, not the role).
    edge_err = can_transition(current, "reviewed")
    if edge_err is not None:
        raise _err("invalid_note_transition", edge_err, 400)
    if not role_permits_edge(current, "reviewed", caller.role):
        raise _err(
            "role_cannot_review_from_state",
            f"role {caller.role!r} cannot advance to reviewed from "
            f"state {current!r}",
            403,
        )
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET "
                "draft_status = 'reviewed', "
                "reviewed_at = CURRENT_TIMESTAMP, "
                "reviewed_by_user_id = :uid, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": note_id, "uid": caller.user_id},
        )

    from app import audit as _audit
    _audit.record(
        event_type="note_version_reviewed",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/review",
        method="POST",
        detail=f"note_id={note_id} version={note['version_number']}",
    )
    return _load_note_for_caller(note_id, caller)


@router.post("/note-versions/{note_id}/amend", status_code=status.HTTP_201_CREATED)
def amend_note(
    note_id: int,
    payload: NoteAmendBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Create an amendment of a signed (or previously amended) note.
    Returns the NEW note_versions row. The original is marked
    superseded. Only admin + clinician may amend."""
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_amend",
            "only admin or clinician may amend a signed note",
            403,
        )
    original = _load_note_for_caller(note_id, caller)
    from app.services.note_amendments import AmendmentError, amend_signed_note
    try:
        new_row = amend_signed_note(
            original_note=original,
            new_text=payload.note_text,
            reason=payload.reason,
            caller_user_id=caller.user_id,
        )
    except AmendmentError as e:
        raise _err(e.code, e.message, 409)

    # Wave 7 — invalidate prior final approval on the superseded row.
    #
    # An amendment means the original signed record is no longer the
    # record of care. Any final physician approval that existed on it
    # is therefore no longer attested to the active version; flip its
    # final_approval_status to 'invalidated' and stamp a reason. The
    # original's existing `final_approved_at` / signature text are
    # preserved — the invalidation is additive so the audit trail
    # still shows that approval once existed.
    prior_status = original.get("final_approval_status")
    prior_was_approved = (prior_status == "approved")
    if prior_status in {"approved", "pending"}:
        from app.services.note_final_approval import (
            invalidation_reason_for_amendment,
        )
        invalidation_reason = invalidation_reason_for_amendment()
        with transaction() as conn:
            conn.execute(
                text(
                    "UPDATE note_versions SET "
                    "final_approval_status = 'invalidated', "
                    "final_approval_invalidated_at = CURRENT_TIMESTAMP, "
                    "final_approval_invalidated_reason = :reason, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :id"
                ),
                {"id": note_id, "reason": invalidation_reason},
            )

    from app import audit as _audit
    _audit.record(
        event_type="note_version_amended",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/amend",
        method="POST",
        detail=(
            f"original_note_id={note_id} "
            f"amended_note_id={new_row.get('id')} "
            f"reason={(payload.reason or '').strip()[:120]}"
        ),
    )
    if prior_was_approved:
        _audit.record(
            event_type="note_final_approval_invalidated",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/amend",
            method="POST",
            detail=(
                f"original_note_id={note_id} "
                f"amended_note_id={new_row.get('id')} "
                "cause=amendment"
            ),
        )

    # Phase 55 — evidence chain: record the amendment from both sides
    # (source is now superseded; the new row is an amendment) and, if
    # prior final-approval was invalidated, record the invalidation
    # as a distinct chain event. Three appends in the same org chain
    # keep the forensic reconstruction clean.
    try:
        from app.services.note_evidence import (
            EvidenceEventType,
            record_evidence_event,
        )
        new_note_id = int(new_row["id"])
        encounter_id = int(original["encounter_id"])
        # (1) Source side — original is now superseded.
        record_evidence_event(
            organization_id=caller.organization_id,
            note_version_id=note_id,
            encounter_id=encounter_id,
            event_type=EvidenceEventType.note_amended_source.value,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            draft_status=original.get("draft_status"),
            final_approval_status=(
                "invalidated" if prior_status in {"approved", "pending"}
                else original.get("final_approval_status")
            ),
            content_fingerprint=original.get("content_fingerprint"),
            detail={
                "superseded_by_note_id": new_note_id,
                "amendment_reason": (payload.reason or "").strip()[:500],
            },
        )
        # (2) New amendment side.
        record_evidence_event(
            organization_id=caller.organization_id,
            note_version_id=new_note_id,
            encounter_id=encounter_id,
            event_type=EvidenceEventType.note_amended_new.value,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            draft_status="amended",
            final_approval_status=None,
            content_fingerprint=None,  # freshly amended — not yet signed
            detail={
                "amended_from_note_id": note_id,
                "amendment_reason": (payload.reason or "").strip()[:500],
            },
        )
        # (3) Approval-invalidated — only when a real approval existed.
        if prior_was_approved:
            record_evidence_event(
                organization_id=caller.organization_id,
                note_version_id=note_id,
                encounter_id=encounter_id,
                event_type=EvidenceEventType.note_final_approval_invalidated.value,
                actor_user_id=caller.user_id,
                actor_email=caller.email,
                draft_status=original.get("draft_status"),
                final_approval_status="invalidated",
                content_fingerprint=original.get("content_fingerprint"),
                detail={
                    "cause": "amendment",
                    "amended_by_note_id": new_note_id,
                },
            )
    except Exception:  # pragma: no cover
        import logging as _lg
        _lg.getLogger("chartnav.evidence").warning(
            "evidence chain append failed on amend", exc_info=True
        )
    return _load_note_for_caller(int(new_row["id"]), caller)


@router.get("/note-versions/{note_id}/amendment-chain")
def note_amendment_chain(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Walk the full amendment chain for this note. The caller must
    have access to the underlying encounter via the existing
    `_load_note_for_caller` guard.

    Phase 54 — the chain is the authoritative record-of-care
    structure. Response includes:
      - chain: ordered list oldest → newest with signing + approval
        state on every link
      - current_record_of_care_note_id: the single link that is NOT
        superseded (amendments roll forward; the tail is the current
        record)
      - has_invalidated_approval: convenience flag; true iff any
        link carries final_approval_status == 'invalidated'
    """
    _load_note_for_caller(note_id, caller)  # enforces same-org
    from app.services.note_amendments import amendment_chain
    chain = amendment_chain(note_id)
    current_tail: int | None = None
    has_invalidated = False
    for link in chain:
        if link.get("superseded_at") is None:
            current_tail = int(link["id"])
        if link.get("final_approval_status") == "invalidated":
            has_invalidated = True
    return {
        "note_id": note_id,
        "chain": chain,
        "current_record_of_care_note_id": current_tail,
        "has_invalidated_approval": has_invalidated,
    }


# ---------------------------------------------------------------------------
# Phase 52 — Wave 7 final physician approval route
# ---------------------------------------------------------------------------

@router.post("/note-versions/{note_id}/final-approve")
def note_final_approve(
    note_id: int,
    payload: NoteFinalApprovalBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Perform final physician approval on a signed note.

    Required conditions (all enforced server-side):

      1. The caller is an authorized final signer for their org
         (`users.is_authorized_final_signer = true`). Role alone is
         insufficient.
      2. The note exists, is same-org, and is in a signable state
         (signed / exported / amended) and not superseded.
      3. The note is not already approved (idempotent guard).
      4. The typed signature string equals `caller.full_name`
         EXACTLY. Comparison is case-sensitive; leading/trailing
         whitespace is trimmed on both sides but interior whitespace
         is preserved.

    Every failure path emits an audit event. Success stamps the four
    final-approval columns and emits `note_final_approved`.
    """
    from app.services.note_final_approval import (
        can_attempt_final_approval,
        compare_typed_signature,
        is_authorized_final_signer,
    )
    from app import audit as _audit

    # -- 1. Org-scope first (404 on cross-org, per existence-hiding policy).
    # This must run before authz so a cross-org caller cannot probe
    # the existence of notes in other organizations by comparing
    # 403 vs. 404.
    note = _load_note_for_caller(note_id, caller)

    # -- 2. Caller authz -----------------------------------------------
    caller_row = fetch_one(
        "SELECT id, email, full_name, role, organization_id, "
        "is_active, is_authorized_final_signer "
        "FROM users WHERE id = :uid",
        {"uid": caller.user_id},
    )
    if not is_authorized_final_signer(dict(caller_row) if caller_row else {}):
        _audit.record(
            event_type="note_final_approval_unauthorized",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/final-approve",
            method="POST",
            error_code="role_cannot_final_approve",
            detail=(
                f"note_id={note_id} role={caller.role!r} "
                "reason=caller_not_authorized_final_signer"
            ),
        )
        raise _err(
            "role_cannot_final_approve",
            (
                "final physician approval requires an authorized final "
                "signer; this account does not carry that privilege"
            ),
            403,
        )

    # -- 3. Note exists + acceptable state (org-scope already enforced)
    pre = can_attempt_final_approval(note)
    if not pre.ok:
        _audit.record(
            event_type="note_final_approval_invalid_state",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/final-approve",
            method="POST",
            error_code=pre.reason or "invalid_state",
            detail=(
                f"note_id={note_id} version={note['version_number']} "
                f"reason={pre.reason}"
            ),
        )
        # 409 for state conflict (already approved, superseded,
        # unsigned) so the client can distinguish from authz failures.
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": pre.reason or "invalid_state",
                "reason": pre.detail or "invalid state for final approval",
            },
        )

    # -- 3. Signature match (case-sensitive exact) --------------------
    cmp = compare_typed_signature(
        typed=payload.signature_text,
        stored_full_name=caller.full_name,
    )
    if not cmp.matched:
        # Never include the typed value in the audit detail — it may
        # include a misspelled name that is not interesting to log.
        _audit.record(
            event_type="note_final_approval_signature_mismatch",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/note-versions/{note_id}/final-approve",
            method="POST",
            error_code=cmp.reason or "signature_mismatch",
            detail=(
                f"note_id={note_id} version={note['version_number']} "
                f"reason={cmp.reason}"
            ),
        )
        # 422 for a signature mismatch — it is a validation failure
        # on the payload rather than a state or authz conflict.
        # 400 if the stored name is missing (it is a system setup
        # problem; no amount of retyping will fix it).
        status_code = 400 if cmp.expected_empty else 422
        raise HTTPException(
            status_code=status_code,
            detail={
                "error_code": cmp.reason or "signature_mismatch",
                "reason": (
                    "no stored full_name on this account; cannot perform "
                    "final approval until a name is recorded"
                )
                if cmp.expected_empty
                else (
                    "typed signature does not match the doctor's stored "
                    "name exactly (case-sensitive)"
                ),
            },
        )

    # -- 4. Persist approval + audit ----------------------------------
    # Preserve the typed signature verbatim — not the stored name —
    # so the audit trail reflects exactly what the doctor typed.
    signature_verbatim = (payload.signature_text or "").strip()
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE note_versions SET "
                "final_approval_status = 'approved', "
                "final_approved_at = CURRENT_TIMESTAMP, "
                "final_approved_by_user_id = :uid, "
                "final_approval_signature_text = :sig, "
                "final_approval_invalidated_at = NULL, "
                "final_approval_invalidated_reason = NULL, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {
                "id": note_id,
                "uid": caller.user_id,
                "sig": signature_verbatim,
            },
        )

    _audit.record(
        event_type="note_final_approved",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/final-approve",
        method="POST",
        detail=(
            f"note_id={note_id} version={note['version_number']}"
        ),
    )
    # Phase 55 — evidence chain append.
    try:
        from app.services.note_evidence import (
            EvidenceEventType,
            record_evidence_event,
        )
        record_evidence_event(
            organization_id=caller.organization_id,
            note_version_id=note_id,
            encounter_id=int(note["encounter_id"]),
            event_type=EvidenceEventType.note_final_approved.value,
            actor_user_id=caller.user_id,
            actor_email=caller.email,
            draft_status=note.get("draft_status"),
            final_approval_status="approved",
            content_fingerprint=note.get("content_fingerprint"),
            detail={
                "signature_text": signature_verbatim,
                "version_number": note["version_number"],
            },
        )
    except Exception:  # pragma: no cover
        import logging as _lg
        _lg.getLogger("chartnav.evidence").warning(
            "evidence chain append failed on final-approve", exc_info=True
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


@router.patch("/me/quick-comments/{comment_id:int}")
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


@router.delete("/me/quick-comments/{comment_id:int}")
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


# ===========================================================================
# Quick-comment favorites + usage audit (phase 28)
# ===========================================================================
#
# Favorites
# ---------
# A per-user bag of pins. Each row references exactly one of:
# - a preloaded comment by its stable string id (e.g. "sx-01"), OR
# - a doctor's custom comment by its DB id.
#
# POST is idempotent (409-free upsert) so the UI can call "favorite"
# without tracking state. DELETE is body-based (same shape as POST)
# so the UI doesn't need to carry the favorite row id.
#
# Usage audit
# -----------
# A thin, honest "which quick comments do doctors actually reach for"
# signal. Emits a single audit event `clinician_quick_comment_used`
# per insertion; the detail string carries the ref identifier + the
# optional note_version_id so a reviewer can correlate without the
# audit log ever storing the comment body (PHI-minimising).


QC_FAV_COLUMNS = (
    "id, organization_id, user_id, preloaded_ref, custom_comment_id, "
    "created_at"
)


class QuickCommentFavoriteBody(BaseModel):
    preloaded_ref: Optional[str] = Field(
        None, min_length=1, max_length=64,
    )
    custom_comment_id: Optional[int] = None


class QuickCommentUsageBody(BaseModel):
    preloaded_ref: Optional[str] = Field(
        None, min_length=1, max_length=64,
    )
    custom_comment_id: Optional[int] = None
    note_version_id: Optional[int] = None
    encounter_id: Optional[int] = None


def _validate_exactly_one_ref(
    preloaded_ref: Optional[str],
    custom_comment_id: Optional[int],
) -> None:
    has_pre = bool(preloaded_ref and preloaded_ref.strip())
    has_custom = custom_comment_id is not None
    if has_pre == has_custom:
        # Either both empty or both populated — neither is valid.
        raise _err(
            "quick_comment_ref_required",
            "exactly one of preloaded_ref or custom_comment_id must be set",
            400,
        )


def _assert_custom_owned_by_caller(
    custom_comment_id: int, caller: Caller
) -> None:
    row = fetch_one(
        "SELECT organization_id, user_id, is_active "
        "FROM clinician_quick_comments WHERE id = :id",
        {"id": custom_comment_id},
    )
    if row is None:
        raise _err("quick_comment_not_found", "no such quick comment", 404)
    if (
        row["organization_id"] != caller.organization_id
        or row["user_id"] != caller.user_id
    ):
        # Mask cross-user + cross-org behind a 404 — same pattern as
        # the create/patch route for quick comments themselves.
        raise _err("quick_comment_not_found", "no such quick comment", 404)
    if not row["is_active"]:
        raise _err(
            "quick_comment_inactive",
            "cannot favorite a soft-deleted comment",
            409,
        )


@router.get("/me/quick-comments/favorites")
def list_my_quick_comment_favorites(
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _require_quick_comment_role(caller)
    rows = fetch_all(
        f"SELECT {QC_FAV_COLUMNS} FROM clinician_quick_comment_favorites "
        "WHERE organization_id = :org AND user_id = :uid "
        "ORDER BY created_at ASC, id ASC",
        {"org": caller.organization_id, "uid": caller.user_id},
    )
    return [dict(r) for r in rows]


@router.post(
    "/me/quick-comments/favorites", status_code=status.HTTP_201_CREATED,
)
def favorite_quick_comment(
    payload: QuickCommentFavoriteBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_quick_comment_role(caller)
    _validate_exactly_one_ref(payload.preloaded_ref, payload.custom_comment_id)

    if payload.custom_comment_id is not None:
        _assert_custom_owned_by_caller(payload.custom_comment_id, caller)

    # Idempotent upsert: if the row already exists, return it instead
    # of 409-ing. Keeps the UI simple — a star button just re-fires
    # POST on every click.
    existing = fetch_one(
        f"SELECT {QC_FAV_COLUMNS} FROM clinician_quick_comment_favorites "
        "WHERE user_id = :uid AND organization_id = :org AND ("
        "  (preloaded_ref IS NOT NULL AND preloaded_ref = :pre) OR "
        "  (custom_comment_id IS NOT NULL AND custom_comment_id = :cid)"
        ")",
        {
            "org": caller.organization_id,
            "uid": caller.user_id,
            "pre": payload.preloaded_ref,
            "cid": payload.custom_comment_id,
        },
    )
    if existing is not None:
        return dict(existing)

    with transaction() as conn:
        new_id = conn.execute(
            text(
                "INSERT INTO clinician_quick_comment_favorites "
                "(organization_id, user_id, preloaded_ref, custom_comment_id) "
                "VALUES (:org, :uid, :pre, :cid) RETURNING id"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "pre": (payload.preloaded_ref or "").strip() or None,
                "cid": payload.custom_comment_id,
            },
        ).mappings().first()["id"]

    from app import audit as _audit
    _audit.record(
        event_type="clinician_quick_comment_favorited",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/quick-comments/favorites",
        method="POST",
        detail=(
            f"favorite_id={new_id} "
            + (
                f"preloaded_ref={payload.preloaded_ref}"
                if payload.preloaded_ref
                else f"custom_comment_id={payload.custom_comment_id}"
            )
        ),
    )

    row = fetch_one(
        f"SELECT {QC_FAV_COLUMNS} FROM clinician_quick_comment_favorites "
        "WHERE id = :id",
        {"id": int(new_id)},
    )
    return dict(row)


@router.delete("/me/quick-comments/favorites")
def unfavorite_quick_comment(
    preloaded_ref: Optional[str] = Query(
        None, min_length=1, max_length=64,
        description="preloaded favorite to remove",
    ),
    custom_comment_id: Optional[int] = Query(
        None, description="custom comment id to unfavorite",
    ),
    caller: Caller = Depends(require_caller),
) -> dict:
    # DELETE takes query params rather than a JSON body so that every
    # HTTP client (including proxies + TestClient's `.delete()`)
    # transports the input reliably — some layers strip DELETE bodies.
    _require_quick_comment_role(caller)
    _validate_exactly_one_ref(preloaded_ref, custom_comment_id)

    with transaction() as conn:
        result = conn.execute(
            text(
                "DELETE FROM clinician_quick_comment_favorites "
                "WHERE user_id = :uid AND organization_id = :org AND ("
                "  (preloaded_ref IS NOT NULL AND preloaded_ref = :pre) OR "
                "  (custom_comment_id IS NOT NULL AND custom_comment_id = :cid)"
                ")"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "pre": preloaded_ref,
                "cid": custom_comment_id,
            },
        )
        removed = result.rowcount if result.rowcount is not None else 0

    if removed > 0:
        from app import audit as _audit
        _audit.record(
            event_type="clinician_quick_comment_unfavorited",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path="/me/quick-comments/favorites",
            method="DELETE",
            detail=(
                f"preloaded_ref={preloaded_ref}"
                if preloaded_ref
                else f"custom_comment_id={custom_comment_id}"
            ),
        )

    return {"removed": int(removed)}


@router.post(
    "/me/quick-comments/used", status_code=status.HTTP_202_ACCEPTED,
)
def record_quick_comment_use(
    payload: QuickCommentUsageBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Record that a clinician just inserted a quick comment.

    Deliberately a thin audit signal, not a new table. The existing
    audit pipeline captures user, org, path, method, timestamp,
    request_id — we only need to add *which* comment (the ref) and
    optional note context (`note_version_id`, `encounter_id`).

    PHI minimisation: the comment body is NEVER sent over the wire to
    this endpoint — only the ref identifier. Downstream analytics
    can join the ref back to the body (which the comment-author
    sees on their own pad) without the audit log duplicating content.

    Returns 202 Accepted: the event is informational. The draft has
    already been mutated client-side; this call is a best-effort
    telemetry signal, and failures should never block the clinician.
    """
    _require_quick_comment_role(caller)
    _validate_exactly_one_ref(payload.preloaded_ref, payload.custom_comment_id)

    if payload.custom_comment_id is not None:
        # Still mask cross-user + cross-org behind 404 so the audit
        # event can't be abused to test for existence of another
        # user's custom comments.
        _assert_custom_owned_by_caller(payload.custom_comment_id, caller)

    kind = "preloaded" if payload.preloaded_ref else "custom"
    ref_detail = (
        f"preloaded_ref={payload.preloaded_ref}"
        if payload.preloaded_ref
        else f"custom_comment_id={payload.custom_comment_id}"
    )
    ctx_parts: list[str] = []
    if payload.note_version_id is not None:
        ctx_parts.append(f"note_version_id={payload.note_version_id}")
    if payload.encounter_id is not None:
        ctx_parts.append(f"encounter_id={payload.encounter_id}")
    ctx = (" " + " ".join(ctx_parts)) if ctx_parts else ""

    from app import audit as _audit
    _audit.record(
        event_type="clinician_quick_comment_used",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/quick-comments/used",
        method="POST",
        detail=f"kind={kind} {ref_detail}{ctx}",
    )
    return {"recorded": True, "kind": kind}


# ===========================================================================
# Clinical Shortcuts usage audit (phase 29)
# ===========================================================================
#
# Parallel to phase-28's `/me/quick-comments/used` but for the
# clinician-specialist shorthand pack shipped client-side. Kept as a
# separate endpoint (not a param on the quick-comments one) so the
# two usage streams are cleanly separable for analytics — shorthand
# phrase-bank usage is a different ergonomic question than clipboard-
# style quick-comment usage.
#
# The shortcut catalog lives on the frontend as static content; the
# backend never needs to know the full list, only the ref (string id)
# the doctor just inserted. PHI-minimising: no body, no draft text.


CLINICAL_SHORTCUT_ID_MAX = 64


class ClinicalShortcutUsageBody(BaseModel):
    shortcut_id: str = Field(..., min_length=1, max_length=CLINICAL_SHORTCUT_ID_MAX)
    note_version_id: Optional[int] = None
    encounter_id: Optional[int] = None


@router.post(
    "/me/clinical-shortcuts/used", status_code=status.HTTP_202_ACCEPTED,
)
def record_clinical_shortcut_use(
    payload: ClinicalShortcutUsageBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Record that a clinician inserted a Clinical Shortcut.

    Thin audit signal, same rules as the phase-28 quick-comment usage
    endpoint: admin/clinician only, reviewer → 403, PHI-minimising
    (no body, only the shortcut ref). Returns 202 Accepted — best-
    effort telemetry; a failure must not block the clinician.
    """
    # Reuse the quick-comment role gate — specialist shorthand is
    # clinician-authored content insertion, same class of action.
    _require_quick_comment_role(caller)

    shortcut_id = payload.shortcut_id.strip()
    if not shortcut_id:
        raise _err(
            "shortcut_id_required",
            "shortcut_id is required and must be non-empty",
            400,
        )

    ctx_parts: list[str] = []
    if payload.note_version_id is not None:
        ctx_parts.append(f"note_version_id={payload.note_version_id}")
    if payload.encounter_id is not None:
        ctx_parts.append(f"encounter_id={payload.encounter_id}")
    ctx = (" " + " ".join(ctx_parts)) if ctx_parts else ""

    from app import audit as _audit
    _audit.record(
        event_type="clinician_shortcut_used",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/clinical-shortcuts/used",
        method="POST",
        detail=f"shortcut_id={shortcut_id}{ctx}",
    )
    return {"recorded": True, "shortcut_id": shortcut_id}


# ===========================================================================
# Clinical Shortcut favorites (phase 30)
# ===========================================================================
#
# Parallel to the phase-28 quick-comment favorites surface, keyed on
# the shortcut catalog's stable string ids. Kept as a separate table
# and a separate URL namespace so the two favoritism models evolve
# independently (quick-comment favorites reference DB rows and care
# about soft-delete; shortcut favorites reference frontend-bundle
# content that cannot be soft-deleted). Idempotent POST upsert so the
# UI star button can re-fire without state tracking.


CLINICAL_SHORTCUT_FAV_COLUMNS = (
    "id, organization_id, user_id, shortcut_ref, created_at"
)


class ClinicalShortcutFavoriteBody(BaseModel):
    shortcut_ref: str = Field(
        ..., min_length=1, max_length=CLINICAL_SHORTCUT_ID_MAX,
    )


@router.get("/me/clinical-shortcuts/favorites")
def list_my_shortcut_favorites(
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _require_quick_comment_role(caller)
    rows = fetch_all(
        f"SELECT {CLINICAL_SHORTCUT_FAV_COLUMNS} "
        "FROM clinician_shortcut_favorites "
        "WHERE organization_id = :org AND user_id = :uid "
        "ORDER BY created_at ASC, id ASC",
        {"org": caller.organization_id, "uid": caller.user_id},
    )
    return [dict(r) for r in rows]


@router.post(
    "/me/clinical-shortcuts/favorites",
    status_code=status.HTTP_201_CREATED,
)
def favorite_clinical_shortcut(
    payload: ClinicalShortcutFavoriteBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_quick_comment_role(caller)
    ref = payload.shortcut_ref.strip()
    if not ref:
        raise _err(
            "shortcut_ref_required",
            "shortcut_ref is required and must be non-empty",
            400,
        )

    existing = fetch_one(
        f"SELECT {CLINICAL_SHORTCUT_FAV_COLUMNS} "
        "FROM clinician_shortcut_favorites "
        "WHERE user_id = :uid AND organization_id = :org "
        "AND shortcut_ref = :ref",
        {
            "uid": caller.user_id,
            "org": caller.organization_id,
            "ref": ref,
        },
    )
    if existing is not None:
        return dict(existing)

    with transaction() as conn:
        new_id = conn.execute(
            text(
                "INSERT INTO clinician_shortcut_favorites "
                "(organization_id, user_id, shortcut_ref) "
                "VALUES (:org, :uid, :ref) RETURNING id"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "ref": ref,
            },
        ).mappings().first()["id"]

    from app import audit as _audit
    _audit.record(
        event_type="clinician_shortcut_favorited",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/clinical-shortcuts/favorites",
        method="POST",
        detail=f"favorite_id={new_id} shortcut_ref={ref}",
    )

    row = fetch_one(
        f"SELECT {CLINICAL_SHORTCUT_FAV_COLUMNS} "
        "FROM clinician_shortcut_favorites WHERE id = :id",
        {"id": int(new_id)},
    )
    return dict(row)


@router.delete("/me/clinical-shortcuts/favorites")
def unfavorite_clinical_shortcut(
    shortcut_ref: str = Query(
        ..., min_length=1, max_length=CLINICAL_SHORTCUT_ID_MAX,
        description="shortcut to unpin",
    ),
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_quick_comment_role(caller)
    ref = shortcut_ref.strip()
    if not ref:
        raise _err("shortcut_ref_required", "shortcut_ref is required", 400)

    with transaction() as conn:
        result = conn.execute(
            text(
                "DELETE FROM clinician_shortcut_favorites "
                "WHERE user_id = :uid AND organization_id = :org "
                "AND shortcut_ref = :ref"
            ),
            {
                "uid": caller.user_id,
                "org": caller.organization_id,
                "ref": ref,
            },
        )
        removed = result.rowcount if result.rowcount is not None else 0

    if removed > 0:
        from app import audit as _audit
        _audit.record(
            event_type="clinician_shortcut_unfavorited",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path="/me/clinical-shortcuts/favorites",
            method="DELETE",
            detail=f"shortcut_ref={ref}",
        )
    return {"removed": int(removed)}


# ===========================================================================
# Shortcut usage-summary admin report (phase 31)
# ===========================================================================
#
# Thin operational read on top of the existing audit stream. Answers
# "which Clinical Shortcuts are the doctors in this org actually
# reaching for?" without standing up a new storage layer.
#
# Reads `security_audit_events` where event_type='clinician_shortcut_used',
# parses `shortcut_id=<ref>` out of the detail string, and aggregates
# per-ref counts + last-used-at. Admin-gated; org-scoped. PHI-minimising:
# the summary never emits note_version_id or encounter_id — only the
# catalog ref + count + timestamp.


def _build_shortcut_usage_summary(
    *,
    organization_id: int,
    days: int,
    limit: int,
    by_user: bool,
) -> dict:
    """Pure-python aggregator shared by the JSON + CSV endpoints.

    Extracted so both HTTP handlers hit the exact same query + parse
    + ranking + trimming logic. Staying below the handler layer keeps
    PHI-minimisation obvious at the type level: the dict returned here
    is the entire analytics surface.
    """
    import re
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    rows = fetch_all(
        "SELECT actor_email, detail, created_at FROM security_audit_events "
        "WHERE event_type = :etype "
        "AND organization_id = :org "
        "AND created_at >= :since",
        {
            "etype": "clinician_shortcut_used",
            "org": organization_id,
            "since": cutoff,
        },
    )
    pattern = re.compile(r"\bshortcut_id=([A-Za-z0-9_\-]+)")

    total = 0
    distinct_refs: set[str] = set()

    if by_user:
        # Group by (actor_email, shortcut_ref). Events whose
        # actor_email is NULL (shouldn't happen for clinician-initiated
        # audits) are grouped under an empty-string key; the UI can
        # decide whether to render them.
        per_bucket: dict[tuple[str, str], dict] = {}
        for row in rows:
            detail = (row.get("detail") or "").strip()
            m = pattern.search(detail)
            if not m:
                continue
            ref = m.group(1)
            email = (row.get("actor_email") or "").strip()
            key = (email, ref)
            ts = row.get("created_at")
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")
            bucket = per_bucket.get(key)
            if bucket is None:
                per_bucket[key] = {"count": 1, "last_used_at": ts_str}
            else:
                bucket["count"] += 1
                if ts_str > (bucket["last_used_at"] or ""):
                    bucket["last_used_at"] = ts_str
            total += 1
            distinct_refs.add(ref)
        items = [
            {
                "user_email": email,
                "shortcut_ref": ref,
                "count": b["count"],
                "last_used_at": b["last_used_at"],
            }
            for (email, ref), b in per_bucket.items()
        ]
        # Rank most-used first; stable secondary sort on (email, ref)
        # so equal-count ties have a deterministic order.
        items.sort(
            key=lambda r: (-r["count"], r["user_email"], r["shortcut_ref"])
        )
        items = items[: int(limit)]
        return {
            "window_days": int(days),
            "organization_id": organization_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "by_user": True,
            "total_events": total,
            "distinct_refs": len(distinct_refs),
            "distinct_users": len({email for (email, _ref) in per_bucket}),
            "items": items,
        }

    counts: dict[str, int] = {}
    last_seen: dict[str, str] = {}
    for row in rows:
        detail = (row.get("detail") or "").strip()
        m = pattern.search(detail)
        if not m:
            continue
        ref = m.group(1)
        counts[ref] = counts.get(ref, 0) + 1
        total += 1
        ts = row.get("created_at")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")
        prev = last_seen.get(ref, "")
        if ts_str > prev:
            last_seen[ref] = ts_str
    items = [
        {
            "shortcut_ref": ref,
            "count": count,
            "last_used_at": last_seen.get(ref),
        }
        for ref, count in counts.items()
    ]
    items.sort(key=lambda r: (-r["count"], r["shortcut_ref"]))
    items = items[: int(limit)]
    return {
        "window_days": int(days),
        "organization_id": organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_user": False,
        "total_events": total,
        "distinct_refs": len(counts),
        "items": items,
    }


@router.get("/admin/shortcut-usage-summary")
def shortcut_usage_summary(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Rolling window in days (1-365). Default 30.",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Max ranked rows to return. Default 50.",
    ),
    by_user: bool = Query(
        False,
        description=(
            "If true, group by (user_email, shortcut_ref) instead of "
            "just shortcut_ref."
        ),
    ),
    caller: Caller = Depends(require_admin),
) -> dict:
    """Rollup of `clinician_shortcut_used` audit events.

    Intentionally narrow. No encounter join, no comment-body exposure.
    Ranked descending by count within the window.

    Admin-only because it's an operational lens on clinician-behaviour
    patterns, not a per-patient data view. Cross-org queries are
    blocked by the `organization_id` filter on the audit table (every
    event carries it). When `by_user=true`, the breakdown still stays
    inside the caller's org.
    """
    return _build_shortcut_usage_summary(
        organization_id=caller.organization_id,
        days=int(days),
        limit=int(limit),
        by_user=bool(by_user),
    )


@router.get(
    "/admin/shortcut-usage-summary/export",
    include_in_schema=True,
)
def shortcut_usage_summary_csv(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    by_user: bool = Query(False),
    caller: Caller = Depends(require_admin),
):
    """CSV export of the shortcut-usage summary.

    Ops-friendly, not fancy. Columns change with `by_user`:
      aggregate  → shortcut_ref, count, last_used_at
      by_user    → user_email, shortcut_ref, count, last_used_at

    Same admin/org/window constraints as the JSON endpoint. Filename
    pattern: `chartnav-shortcut-usage-YYYYMMDDTHHMMSSZ[-by-user].csv`.
    """
    from datetime import datetime
    from fastapi.responses import Response as _PlainResponse

    summary = _build_shortcut_usage_summary(
        organization_id=caller.organization_id,
        days=int(days),
        limit=int(limit),
        by_user=bool(by_user),
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    if summary["by_user"]:
        writer.writerow(["user_email", "shortcut_ref", "count", "last_used_at"])
        for r in summary["items"]:
            writer.writerow([
                r.get("user_email") or "",
                r.get("shortcut_ref") or "",
                r.get("count") or 0,
                r.get("last_used_at") or "",
            ])
    else:
        writer.writerow(["shortcut_ref", "count", "last_used_at"])
        for r in summary["items"]:
            writer.writerow([
                r.get("shortcut_ref") or "",
                r.get("count") or 0,
                r.get("last_used_at") or "",
            ])

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = "-by-user" if summary["by_user"] else ""
    filename = f"chartnav-shortcut-usage-{stamp}{suffix}.csv"
    return _PlainResponse(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ===========================================================================
# Audio intake + transcript review (phase 33)
# ===========================================================================
#
# Two new surfaces on top of the phase-22 ingestion pipeline:
#
# POST /encounters/{id}/inputs/audio
#   Multipart file upload. Writes the audio blob to
#   `settings.audio_upload_dir/<encounter_id>/<uuid>.<ext>`, creates an
#   `encounter_inputs` row with `input_type='audio_upload'` and
#   `source_metadata` populated with filename/content_type/size/
#   stored_path/original_filename, and kicks the ingestion pipeline
#   inline. The stub transcriber (installed at app bootstrap) returns
#   a deterministic placeholder OR honours the `stub_transcript` /
#   `stub_transcript_error` hints in the `X-Stub-*` headers so tests
#   can drive the state machine without shipping binary fixtures.
#
# PATCH /encounter-inputs/{id}/transcript
#   Doctor review/edit on a completed input. Lets the clinician hand-
#   correct stub / STT output BEFORE note generation. Audit-logged
#   with `encounter_input_transcript_edited`. Cross-org → 404.
#   Only admin/clinician; reviewer → 403 (read-only role).
#
# Provenance stays crisp: the `source_metadata` carries the upload
# details; `transcript_text` is the text (edited or not) that goes
# into note generation. Clinical Shortcuts + Quick Comments are a
# *separate* surface (clinician clipboard, not encounter data) and
# must not leak into either column.


AUDIO_ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "audio/webm", "audio/flac",
    "audio/aac",
    # Some browsers upload Blob without a recognisable content-type
    # when the user drags-and-drops; fall back to the extension check
    # inside the handler for those.
    "application/octet-stream",
}
AUDIO_ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".mp4", ".m4a", ".ogg", ".webm", ".flac", ".aac",
}


def _audio_upload_root() -> "Path":
    from pathlib import Path
    from app.config import settings
    root = Path(settings.audio_upload_dir)
    if not root.is_absolute():
        # Resolve relative to the API package root so different CWDs
        # (tests, prod, docker) land in the same place.
        root = Path(__file__).resolve().parents[2] / settings.audio_upload_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.post(
    "/encounters/{encounter_id}/inputs/audio",
    status_code=status.HTTP_201_CREATED,
)
async def create_encounter_audio_input(
    encounter_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Accept a doctor audio upload and queue it for transcription.

    Multipart form-data with a single `audio` part. The handler:

    1. Validates role + encounter ownership.
    2. Reads the upload body, enforcing
       `settings.audio_upload_max_bytes`.
    3. Writes the blob to
       `<audio_upload_dir>/<encounter_id>/<uuid>.<ext>`.
    4. Creates an `encounter_inputs` row with `input_type='audio_upload'`
       and source metadata carrying the upload fingerprint.
    5. Runs the ingestion pipeline inline so the caller sees the
       resulting status in the response body. Stub transcription is
       synchronous; a real STT adapter would queue-and-return.
    """
    from fastapi import Request  # noqa: F401 — imported up top already
    from pathlib import Path
    import secrets
    from app.config import settings as _settings

    require_create_event(caller)
    _load_encounter_for_caller(encounter_id, caller)

    form = await request.form()
    upload = form.get("audio")
    if upload is None or not hasattr(upload, "read"):
        raise _err(
            "audio_upload_missing",
            "multipart field `audio` is required",
            400,
        )
    original_filename = getattr(upload, "filename", None) or "upload"
    content_type = (getattr(upload, "content_type", None) or "").lower()

    lower_name = original_filename.lower()
    ext = ""
    for candidate in AUDIO_ALLOWED_EXTENSIONS:
        if lower_name.endswith(candidate):
            ext = candidate
            break
    content_ok = content_type in AUDIO_ALLOWED_CONTENT_TYPES
    if not content_ok and not ext:
        raise _err(
            "audio_format_not_supported",
            (
                "only audio/wav, mp3, mp4/m4a, ogg, webm, flac, aac "
                "uploads are accepted"
            ),
            400,
        )

    body = await upload.read()
    if not isinstance(body, (bytes, bytearray)) or len(body) == 0:
        raise _err(
            "audio_upload_empty",
            "uploaded audio file is empty",
            400,
        )
    max_bytes = int(_settings.audio_upload_max_bytes)
    if len(body) > max_bytes:
        raise _err(
            "audio_upload_too_large",
            f"upload exceeds max size of {max_bytes} bytes",
            413,
        )

    # Phase 35 — persist via the storage abstraction so `stored_path`
    # is no longer the contract. `storage_ref` is the opaque handle
    # the rest of the system passes around; we still write
    # `stored_path` alongside it for back-compat with phase-33
    # readers that haven't been updated yet.
    from app.services.audio_storage import (
        StorageError as _StorageError,
        resolve_storage as _resolve_storage,
        storage_ref_to_legacy_path as _legacy_path,
    )
    storage = _resolve_storage()
    try:
        storage_ref = storage.put(
            encounter_id=encounter_id,
            ext=ext,
            body=bytes(body),
            content_type=content_type or "application/octet-stream",
        )
    except _StorageError as e:
        raise _err(e.error_code, e.reason, 500)

    # Tests inject stub-transcript hints via headers so the HTTP path
    # can drive queued → completed / failed deterministically without
    # mutating the module-level transcriber.
    stub_transcript = request.headers.get("x-stub-transcript")
    stub_transcript_error = request.headers.get("x-stub-transcript-error")

    # Phase 36 — capture provenance. The frontend sets these on a
    # browser-mic recording so audit + downstream tooling can tell
    # the difference between a hand-uploaded file and a live
    # recording. Bounded enum — anything else is a 400, NOT a silent
    # acceptance, because future schemas will key off the value.
    capture_source_raw = (
        request.headers.get("x-capture-source") or ""
    ).strip().lower()
    if capture_source_raw and capture_source_raw not in {
        "browser-mic", "file-upload",
    }:
        raise _err(
            "audio_capture_source_invalid",
            (
                "X-Capture-Source must be 'browser-mic' or "
                "'file-upload' when set"
            ),
            400,
        )
    capture_source = capture_source_raw or "file-upload"

    legacy_stored_path = _legacy_path(storage_ref)
    metadata: dict[str, Any] = {
        "original_filename": original_filename,
        # Phase-33 `filename` was the on-disk name; preserve a
        # short identifier even when the storage backend doesn't
        # use a filesystem path.
        "filename": (legacy_stored_path or "").rsplit("/", 1)[-1] or "audio",
        "content_type": content_type or "application/octet-stream",
        "size_bytes": len(body),
        "storage_ref": storage_ref,
        "capture_source": capture_source,
    }
    if legacy_stored_path:
        # Back-compat for phase-33 readers + audit dashboards.
        metadata["stored_path"] = legacy_stored_path
    if stub_transcript:
        metadata["stub_transcript"] = stub_transcript
    if stub_transcript_error:
        metadata["stub_transcript_error"] = stub_transcript_error

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "encounter_inputs",
            {
                "encounter_id": encounter_id,
                "input_type": "audio_upload",
                "processing_status": "queued",
                "transcript_text": None,
                "confidence_summary": None,
                "source_metadata": _json.dumps(metadata, sort_keys=True),
                "created_by_user_id": caller.user_id,
            },
        )

    from app import audit as _audit
    _audit.record(
        event_type="encounter_input_audio_uploaded",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounters/{encounter_id}/inputs/audio",
        method="POST",
        detail=(
            f"input_id={new_id} bytes={len(body)} "
            f"content_type={metadata['content_type']} "
            f"scheme={storage_ref.get('scheme')} "
            f"mode={_settings.audio_ingest_mode} "
            f"capture_source={capture_source}"
        ),
    )

    # Phase 35 — pipeline mode gate. `inline` (default for dev/test)
    # runs the ingestion synchronously so the caller sees the
    # terminal state in the response. `async` (production) leaves
    # the row at `queued` and returns immediately so the request
    # path is never blocked on a slow STT vendor — the worker loop
    # picks it up.
    if _settings.audio_ingest_mode == "inline":
        from app.services import ingestion as _ingest
        try:
            _ingest.run_ingestion_now(new_id)
        except _ingest.IngestionError:
            # Failure already persisted on the row.
            pass

    row = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": new_id},
    )
    return row


class TranscriptEditBody(BaseModel):
    transcript_text: str = Field(
        ..., min_length=1,
        description="clinician-edited transcript; replaces the current text",
    )


@router.patch("/encounter-inputs/{input_id}/transcript")
def patch_encounter_input_transcript(
    input_id: int,
    payload: TranscriptEditBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Clinician review/edit of a completed input's transcript.

    Gated:
    - admin / clinician only (reviewer 403).
    - cross-org → 404 via the shared input-load helper.
    - the input must be in a terminal-completed state; we do NOT let
      a clinician overwrite a row mid-STT (that would race the
      pipeline's own writes).

    The edit is persisted in-place with a fresh `updated_at`. The
    `transcript_text` column is what note generation reads, so this
    edit flows straight into the next draft without any additional
    machinery. Audit event records who edited what and the new
    length; the body itself is NOT duplicated into the audit detail
    (PHI minimisation).
    """
    require_create_event(caller)

    row = fetch_one(
        "SELECT ei.id, ei.encounter_id, ei.processing_status, "
        "ei.transcript_text, e.organization_id "
        "FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE ei.id = :id",
        {"id": input_id},
    )
    if row is None or row["organization_id"] != caller.organization_id:
        raise _err(
            "encounter_input_not_found",
            "no such encounter input",
            404,
        )
    if row["processing_status"] != "completed":
        raise _err(
            "encounter_input_not_editable",
            (
                f"transcript can only be edited when processing_status"
                f"='completed' (current: {row['processing_status']!r})"
            ),
            409,
        )

    new_text = payload.transcript_text.strip()
    if len(new_text) < 10:
        raise _err(
            "transcript_too_short",
            "transcript must be at least 10 characters after trim",
            400,
        )

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE encounter_inputs SET "
                "transcript_text = :text, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": input_id, "text": new_text},
        )

    from app import audit as _audit
    _audit.record(
        event_type="encounter_input_transcript_edited",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/encounter-inputs/{input_id}/transcript",
        method="PATCH",
        # PHI minimisation: record size + encounter ref, not content.
        detail=(
            f"input_id={input_id} encounter_id={row['encounter_id']} "
            f"chars={len(new_text)}"
        ),
    )

    updated = fetch_one(
        f"SELECT {INPUT_COLUMNS} FROM encounter_inputs WHERE id = :id",
        {"id": input_id},
    )
    return updated


# ===========================================================================
# Deployment / observability surface (phase 37)
# ===========================================================================
#
# Six admin-only read endpoints + one public capability manifest +
# one public deployment manifest. ChartNav's own admin section, LCC,
# and SourceDeck all read from the same data — there is one
# capability with three lenses.
#
# Auth model:
#  - /admin/deployment/*    → admin-only (require_admin), org-scoped
#  - /admin/deployment/config-actual → admin-only, masked secrets
#  - /capability/manifest   → public (SourceDeck catalog)
#  - /deployment/manifest   → public (release fingerprint)
#
# PHI minimisation: aggregates and counts only. The deepest a
# control-plane reader sees is `(input_id, status, last_error_code)`.


@router.get("/admin/deployment/overview")
def deployment_overview(
    hours: int = Query(24, ge=1, le=720),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_overview(
        organization_id=caller.organization_id, hours=int(hours),
    )


@router.get("/admin/deployment/locations")
def deployment_locations(
    hours: int = Query(24, ge=1, le=720),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_locations(
        organization_id=caller.organization_id, hours=int(hours),
    )


@router.get("/admin/deployment/alerts")
def deployment_alerts(
    hours: int = Query(24, ge=1, le=720),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_alerts(
        organization_id=caller.organization_id, hours=int(hours),
    )


@router.get("/admin/deployment/jobs")
def deployment_jobs(
    limit: int = Query(50, ge=1, le=500),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_jobs(
        organization_id=caller.organization_id, limit=int(limit),
    )


@router.get("/admin/deployment/qa")
def deployment_qa(
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_qa(organization_id=caller.organization_id)


@router.get("/admin/deployment/config-actual")
def deployment_config_actual(
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services.capability_manifest import deployment_config_actual as _cfg
    return _cfg()


@router.get("/deployment/manifest")
def deployment_manifest_public() -> dict:
    """Public release/runtime fingerprint. SourceDeck reads this to
    confirm a deployed instance matches the catalog version it
    expects. No tenant data — only the build identity + which seams
    are wired."""
    from app.services import deployment_telemetry as _telem
    return _telem.deployment_manifest()


@router.get("/capability/manifest")
def capability_manifest_public() -> dict:
    """Public capability catalog read used by SourceDeck. No tenant
    data — only the capability descriptor + setup inputs +
    prerequisites + implementation modes."""
    from app.services.capability_manifest import (
        capability_card, card_to_dict,
    )
    return card_to_dict(capability_card())


# =====================================================================
# Phase 38 — /me/custom-shortcuts (per-clinician authored shortcuts)
# ---------------------------------------------------------------------
# Shares the shape of /me/quick-comments but keys a different concern:
# authored shortcut fragments that live alongside the catalog
# Clinical Shortcuts shipped in the frontend bundle. Reviewers +
# front desk are excluded — this is a clinician / admin surface.
# =====================================================================

CS_COLUMNS = (
    "id, organization_id, user_id, shortcut_ref, group_name, body, "
    "tags, is_active, created_at, updated_at"
)
CS_MAX_BODY_CHARS = 4000
CS_MAX_REF_CHARS = 64
CS_MAX_GROUP_CHARS = 64


class CustomShortcutBody(BaseModel):
    shortcut_ref: Optional[str] = Field(
        None, min_length=1, max_length=CS_MAX_REF_CHARS,
        description=(
            "stable per-user ref; server auto-generates 'my-<uuid>' "
            "when omitted"
        ),
    )
    group_name: Optional[str] = Field(None, max_length=CS_MAX_GROUP_CHARS)
    body: str = Field(..., min_length=1, max_length=CS_MAX_BODY_CHARS)
    tags: Optional[list[str]] = None


class CustomShortcutPatchBody(BaseModel):
    group_name: Optional[str] = Field(None, max_length=CS_MAX_GROUP_CHARS)
    body: Optional[str] = Field(None, min_length=1, max_length=CS_MAX_BODY_CHARS)
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


def _require_custom_shortcut_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_cannot_edit_custom_shortcuts",
            "only admin or clinician may author custom shortcuts",
            403,
        )


def _cs_row_to_dict(row: Any) -> dict:
    d = dict(row)
    tags_raw = d.get("tags")
    if tags_raw:
        try:
            d["tags"] = json.loads(tags_raw)
        except (ValueError, TypeError):
            d["tags"] = []
    else:
        d["tags"] = []
    return d


def _load_custom_shortcut_for_caller(
    shortcut_id: int, caller: Caller
) -> dict[str, Any]:
    row = fetch_one(
        f"SELECT {CS_COLUMNS} FROM clinician_custom_shortcuts WHERE id = :id",
        {"id": shortcut_id},
    )
    if row is None:
        raise _err("custom_shortcut_not_found", "no such custom shortcut", 404)
    row = _cs_row_to_dict(row)
    if (
        row["organization_id"] != caller.organization_id
        or row["user_id"] != caller.user_id
    ):
        # Mask cross-user / cross-org behind a 404 (same pattern as QC).
        raise _err("custom_shortcut_not_found", "no such custom shortcut", 404)
    return row


@router.get("/me/custom-shortcuts")
def list_my_custom_shortcuts(
    include_inactive: bool = Query(False, description="Include soft-deleted"),
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _require_custom_shortcut_role(caller)
    sql = (
        f"SELECT {CS_COLUMNS} FROM clinician_custom_shortcuts "
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
    return [_cs_row_to_dict(r) for r in rows]


@router.post("/me/custom-shortcuts", status_code=status.HTTP_201_CREATED)
def create_my_custom_shortcut(
    payload: CustomShortcutBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_custom_shortcut_role(caller)
    body = payload.body.strip()
    if not body:
        raise _err(
            "custom_shortcut_body_required",
            "body is required and must be non-empty",
            400,
        )
    group_name = (payload.group_name or "My patterns").strip() or "My patterns"
    if payload.shortcut_ref and payload.shortcut_ref.strip():
        ref = payload.shortcut_ref.strip()
    else:
        # Auto-mint a namespaced ref so each per-user entry has a
        # stable string id the audit stream + favorites surface can
        # key on, analogous to 'pvd-01' in the catalog pack.
        import uuid
        ref = f"my-{uuid.uuid4().hex[:12]}"
    tags_json: Optional[str] = None
    if payload.tags:
        cleaned = [t.strip() for t in payload.tags if t and t.strip()]
        if cleaned:
            tags_json = json.dumps(cleaned)

    with transaction() as conn:
        new_id = conn.execute(
            text(
                "INSERT INTO clinician_custom_shortcuts "
                "(organization_id, user_id, shortcut_ref, group_name, "
                " body, tags, is_active) "
                "VALUES (:org, :uid, :ref, :grp, :body, :tags, :active) "
                "RETURNING id"
            ),
            {
                "org": caller.organization_id,
                "uid": caller.user_id,
                "ref": ref,
                "grp": group_name,
                "body": body,
                "tags": tags_json,
                "active": True,
            },
        ).mappings().first()["id"]

    from app import audit as _audit
    _audit.record(
        event_type="clinician_custom_shortcut_created",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/me/custom-shortcuts",
        method="POST",
        detail=f"custom_shortcut_id={new_id} ref={ref} chars={len(body)}",
    )

    return _load_custom_shortcut_for_caller(int(new_id), caller)


@router.patch("/me/custom-shortcuts/{shortcut_id:int}")
def update_my_custom_shortcut(
    shortcut_id: int,
    payload: CustomShortcutPatchBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_custom_shortcut_role(caller)
    existing = _load_custom_shortcut_for_caller(shortcut_id, caller)

    set_parts: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": shortcut_id}
    changed: list[str] = []

    if payload.body is not None:
        body = payload.body.strip()
        if not body:
            raise _err(
                "custom_shortcut_body_required",
                "body must be non-empty when provided",
                400,
            )
        set_parts.append("body = :body")
        params["body"] = body
        changed.append("body")

    if payload.group_name is not None:
        grp = payload.group_name.strip() or "My patterns"
        set_parts.append("group_name = :grp")
        params["grp"] = grp
        changed.append("group")

    if payload.tags is not None:
        cleaned = [t.strip() for t in payload.tags if t and t.strip()]
        set_parts.append("tags = :tags")
        params["tags"] = json.dumps(cleaned) if cleaned else None
        changed.append("tags")

    if payload.is_active is not None:
        set_parts.append("is_active = :active")
        params["active"] = payload.is_active
        changed.append("active")

    if len(set_parts) == 1:
        # Only the updated_at bump — surface a soft 200 with unchanged row.
        return existing

    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE clinician_custom_shortcuts SET "
                + ", ".join(set_parts)
                + " WHERE id = :id"
            ),
            params,
        )

    from app import audit as _audit
    _audit.record(
        event_type="clinician_custom_shortcut_updated",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/me/custom-shortcuts/{shortcut_id}",
        method="PATCH",
        detail=f"custom_shortcut_id={shortcut_id} changed={','.join(changed)}",
    )

    return _load_custom_shortcut_for_caller(shortcut_id, caller)


@router.delete("/me/custom-shortcuts/{shortcut_id:int}")
def delete_my_custom_shortcut(
    shortcut_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_custom_shortcut_role(caller)
    existing = _load_custom_shortcut_for_caller(shortcut_id, caller)
    if not existing.get("is_active", True):
        return existing
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE clinician_custom_shortcuts "
                "SET is_active = :active, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": shortcut_id, "active": False},
        )
    from app import audit as _audit
    _audit.record(
        event_type="clinician_custom_shortcut_soft_deleted",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/me/custom-shortcuts/{shortcut_id}",
        method="DELETE",
        detail=f"custom_shortcut_id={shortcut_id}",
    )
    return _load_custom_shortcut_for_caller(shortcut_id, caller)


# =====================================================================
# Phase 47 — /admin/kpi/* — pilot KPI / ROI scorecard
# ---------------------------------------------------------------------
# Admin-only. Org-scoped. Derived entirely from existing lifecycle
# timestamps (encounter_inputs + note_versions + encounters).
# =====================================================================

@router.get("/admin/kpi/overview")
def kpi_overview_route(
    hours: int = Query(24 * 7, ge=1, le=24 * 90),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services.kpi_scorecard import kpi_overview
    return kpi_overview(
        organization_id=caller.organization_id,
        hours=int(hours),
    )


@router.get("/admin/kpi/providers")
def kpi_providers_route(
    hours: int = Query(24 * 7, ge=1, le=24 * 90),
    caller: Caller = Depends(require_admin),
) -> dict:
    from app.services.kpi_scorecard import kpi_providers
    return kpi_providers(
        organization_id=caller.organization_id,
        hours=int(hours),
    )


@router.get("/admin/kpi/compare")
def kpi_compare_route(
    hours: int = Query(24 * 7, ge=1, le=24 * 90),
    caller: Caller = Depends(require_admin),
) -> dict:
    """Current window vs. previous window of the same width, in one
    payload. The UI uses this for the before / after comparison mode
    on the pilot scorecard."""
    from app.services.kpi_scorecard import kpi_compare
    return kpi_compare(
        organization_id=caller.organization_id,
        hours=int(hours),
    )


@router.get("/admin/kpi/export.csv")
def kpi_export_csv_route(
    hours: int = Query(24 * 7, ge=1, le=24 * 90),
    caller: Caller = Depends(require_admin),
) -> Response:
    """Flat CSV of the per-provider scorecard. Suitable for pilot
    reporting and before/after comparisons."""
    from app.services.kpi_scorecard import kpi_providers, kpi_csv_rows

    payload = kpi_providers(
        organization_id=caller.organization_id,
        hours=int(hours),
    )
    rows = kpi_csv_rows(payload)
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)

    # Audit the export so ops can see who pulled a pilot scorecard.
    from app import audit as _audit
    _audit.record(
        event_type="admin_kpi_export",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/kpi/export.csv",
        method="GET",
        detail=f"hours={hours} provider_rows={len(rows) - 1}",
    )

    filename = f"chartnav-kpi-org{caller.organization_id}-{hours}h.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# =====================================================================
# Phase 48 — /admin/security/* — enterprise control-plane wave 2
# ---------------------------------------------------------------------
# Four surfaces, all gated by `require_security_admin`:
#   GET  /admin/security/policy             — read org security posture
#   PUT  /admin/security/policy             — update org security posture
#   GET  /admin/security/sessions           — list active + revoked
#   POST /admin/security/sessions/{id}/revoke — admin-initiated revoke
#   POST /admin/security/audit-sink/test    — probe the configured sink
# =====================================================================

class SecurityPolicyPatchBody(BaseModel):
    require_mfa: Optional[bool] = None
    idle_timeout_minutes: Optional[int] = None
    absolute_timeout_minutes: Optional[int] = None
    audit_sink_mode: Optional[str] = None
    audit_sink_target: Optional[str] = None
    security_admin_emails: Optional[list[str]] = None
    # Phase 56 — evidence sink + signing keys.
    evidence_sink_mode: Optional[str] = None
    evidence_sink_target: Optional[str] = None
    evidence_signing_mode: Optional[str] = None
    evidence_signing_key_id: Optional[str] = None
    # Phase 57 — export snapshot retention (days or null).
    export_snapshot_retention_days: Optional[int] = None
    # Phase 59 — evidence sink retry-noise retention (days or null).
    evidence_sink_retention_days: Optional[int] = None


class SessionRevokeBody(BaseModel):
    reason: Optional[str] = None


@router.get("/admin/security/policy")
def security_policy_read(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Read-only view of the org's security policy. Any admin can
    READ (so the admin panel can show state on first open), but
    only a security-admin may WRITE (see PUT below)."""
    if caller.role != "admin":
        raise _err(
            "role_admin_required",
            f"role '{caller.role}' is not permitted; requires 'admin'",
            403,
        )
    from app.security_policy import resolve_security_policy, caller_is_security_admin
    policy = resolve_security_policy(caller.organization_id)
    return {
        "organization_id": caller.organization_id,
        "caller_is_security_admin": caller_is_security_admin(caller),
        "policy": policy.as_public_dict(),
    }


@router.put("/admin/security/policy")
def security_policy_update(
    payload: SecurityPolicyPatchBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    from app.security_policy import (
        PolicyValidationError,
        caller_is_security_admin,
        resolve_security_policy,
        update_security_policy,
    )
    if not caller_is_security_admin(caller):
        raise _err(
            "security_admin_required",
            "this action requires the security-admin role for this organization",
            403,
        )
    patch = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    try:
        updated = update_security_policy(caller.organization_id, patch)
    except PolicyValidationError as e:
        raise _err(e.code, e.message, 400)

    from app import audit as _audit
    _audit.record(
        event_type="admin_security_policy_updated",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/security/policy",
        method="PUT",
        detail=f"keys={sorted(patch.keys())}",
    )
    return {
        "organization_id": caller.organization_id,
        "caller_is_security_admin": True,
        "policy": updated.as_public_dict(),
    }


@router.get("/admin/security/sessions")
def security_sessions_list(
    include_revoked: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    caller: Caller = Depends(require_caller),
) -> dict:
    from app.security_policy import caller_is_security_admin
    if not caller_is_security_admin(caller):
        raise _err(
            "security_admin_required",
            "this action requires the security-admin role for this organization",
            403,
        )
    from app.session_governance import list_sessions
    rows = list_sessions(
        organization_id=caller.organization_id,
        include_revoked=bool(include_revoked),
        limit=int(limit),
    )
    return {
        "organization_id": caller.organization_id,
        "include_revoked": bool(include_revoked),
        "sessions": rows,
    }


@router.post("/admin/security/sessions/{session_id:int}/revoke")
def security_sessions_revoke(
    session_id: int,
    payload: SessionRevokeBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    from app.security_policy import caller_is_security_admin
    if not caller_is_security_admin(caller):
        raise _err(
            "security_admin_required",
            "this action requires the security-admin role for this organization",
            403,
        )
    from app.session_governance import admin_revoke_session
    row = admin_revoke_session(
        organization_id=caller.organization_id,
        session_id=session_id,
        reason=(payload.reason or "admin_terminated").strip() or "admin_terminated",
        by_user_id=caller.user_id,
    )
    from app import audit as _audit
    _audit.record(
        event_type="admin_session_revoked",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/admin/security/sessions/{session_id}/revoke",
        method="POST",
        detail=f"session_id={session_id} reason={payload.reason or 'admin_terminated'}",
    )
    return {"session": row}


@router.post("/admin/security/audit-sink/test")
def security_audit_sink_test(
    caller: Caller = Depends(require_caller),
) -> dict:
    from app.security_policy import caller_is_security_admin
    if not caller_is_security_admin(caller):
        raise _err(
            "security_admin_required",
            "this action requires the security-admin role for this organization",
            403,
        )
    from app.services.audit_sink import probe
    result = probe(caller.organization_id)
    from app import audit as _audit
    _audit.record(
        event_type="admin_audit_sink_test",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/security/audit-sink/test",
        method="POST",
        detail=f"mode={result.get('mode')} ok={result.get('ok')}",
    )
    return result


# ===========================================================================
# Phase 53 — Wave 8 enterprise operations & exceptions control plane
# ===========================================================================
#
# Admin-facing read surface that aggregates actionable exception state
# across the platform into a single ops queue. All endpoints are gated
# by `caller_is_security_admin(caller)` so they are consistent with
# the /admin/security/* pattern. Zero writes; this entire surface is
# observation.

def _require_security_admin_inline(caller: Caller) -> None:
    """Inline guard that mirrors the existing /admin/security/* style.
    Keeps the ops surface consistent with the rest of the admin
    plane."""
    from app.security_policy import caller_is_security_admin
    if not caller_is_security_admin(caller):
        raise _err(
            "security_admin_required",
            "this action requires the security-admin role for this organization",
            403,
        )


@router.get("/admin/operations/overview")
def admin_operations_overview(
    hours: int = Query(default=168, ge=1, le=24 * 31),
    caller: Caller = Depends(require_caller),
) -> dict:
    """Aggregate counters for every operational exception category,
    plus a synthesized security-policy status card. This is the
    single call the admin nav + overview tab makes on mount."""
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import compute_counters
    return compute_counters(caller.organization_id, hours=hours).as_dict()


@router.get("/admin/operations/blocked-notes")
def admin_operations_blocked_notes(
    hours: int = Query(default=168, ge=1, le=24 * 31),
    limit: int = Query(default=200, ge=1, le=500),
    caller: Caller = Depends(require_caller),
) -> dict:
    """Merged sign-blocked + export-blocked + approval-denial audit
    rows. Used by the Blocked Notes tab."""
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import list_blocked_notes
    items = list_blocked_notes(caller.organization_id, hours=hours, limit=limit)
    return {
        "organization_id": caller.organization_id,
        "hours": int(hours),
        "items": [it.as_dict() for it in items],
    }


@router.get("/admin/operations/final-approval-queue")
def admin_operations_final_approval_queue(
    limit: int = Query(default=100, ge=1, le=500),
    caller: Caller = Depends(require_caller),
) -> dict:
    """Live-state pending + invalidated final-approval rows. This is
    the primary clinical-ops queue: every row is a piece of
    unfinished work visible to the admin plane."""
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import (
        list_final_approval_pending,
        list_final_approval_invalidated,
    )
    pending = list_final_approval_pending(caller.organization_id, limit=limit)
    invalidated = list_final_approval_invalidated(
        caller.organization_id, limit=limit,
    )
    return {
        "organization_id": caller.organization_id,
        "pending": [it.as_dict() for it in pending],
        "invalidated": [it.as_dict() for it in invalidated],
    }


@router.get("/admin/operations/identity-exceptions")
def admin_operations_identity_exceptions(
    hours: int = Query(default=168, ge=1, le=24 * 31),
    limit: int = Query(default=200, ge=1, le=500),
    caller: Caller = Depends(require_caller),
) -> dict:
    """Identity / provisioning failure events. This surface is
    intentionally narrow — it reports what actually happens
    (unknown_user, invalid_issuer, token_expired, cross-org attempt,
    etc.). The repo does not implement SCIM today; there is no
    SCIM-conflict queue to emit, and this endpoint does not pretend
    otherwise."""
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import list_identity_exceptions
    items = list_identity_exceptions(
        caller.organization_id, hours=hours, limit=limit,
    )
    return {
        "organization_id": caller.organization_id,
        "hours": int(hours),
        "items": [it.as_dict() for it in items],
        "scim_configured": False,
        "oidc_identity_mapping": "email_claim_lookup",
    }


@router.get("/admin/operations/session-exceptions")
def admin_operations_session_exceptions(
    hours: int = Query(default=168, ge=1, le=24 * 31),
    limit: int = Query(default=200, ge=1, le=500),
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import list_session_exceptions
    items = list_session_exceptions(
        caller.organization_id, hours=hours, limit=limit,
    )
    return {
        "organization_id": caller.organization_id,
        "hours": int(hours),
        "items": [it.as_dict() for it in items],
    }


@router.get("/admin/operations/stuck-ingest")
def admin_operations_stuck_ingest(
    limit: int = Query(default=50, ge=1, le=500),
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import list_stuck_ingest
    items = list_stuck_ingest(caller.organization_id, limit=limit)
    return {
        "organization_id": caller.organization_id,
        "items": [it.as_dict() for it in items],
    }


@router.get("/admin/operations/security-config-status")
def admin_operations_security_config_status(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Synthesized card: is this org's security policy configured?
    Not a denial event — an advisory card for the admin surface."""
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import security_config_status
    return security_config_status(caller.organization_id)


# ---------------------------------------------------------------------------
# Phase 55 — immutable evidence chain + forensic bundle export
# ---------------------------------------------------------------------------

@router.get("/note-versions/{note_id}/evidence-bundle")
def note_evidence_bundle(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Forensic evidence bundle for a single note. Assembled from the
    row, the encounter, the amendment chain, the per-org evidence
    chain events that reference this note, plus a body-hash envelope
    so consumers can re-verify the bundle independently.

    Same org-scope contract as every other note read: cross-org → 404.
    Any authenticated org member may issue a bundle for their own
    org's notes; the result is a read + hash, not a mutation.
    """
    note = _load_note_for_caller(note_id, caller)
    # Pull the encounter row (org is already enforced, but the bundle
    # needs the whole row for patient/provider context).
    encounter = fetch_one(
        "SELECT id, organization_id, status, patient_identifier, "
        "patient_name, provider_name, external_ref, external_source, "
        "created_at FROM encounters WHERE id = :id",
        {"id": note["encounter_id"]},
    )
    if encounter is None:
        raise _err("encounter_not_found", "note has no owning encounter", 500)

    signer = None
    if note.get("signed_by_user_id"):
        signer = fetch_one(
            "SELECT id, email, full_name FROM users WHERE id = :id",
            {"id": note["signed_by_user_id"]},
        )

    final_approver = None
    if note.get("final_approved_by_user_id"):
        final_approver = fetch_one(
            "SELECT id, email, full_name FROM users WHERE id = :id",
            {"id": note["final_approved_by_user_id"]},
        )

    from app.services.note_evidence import (
        EvidenceSigningError,
        build_evidence_bundle,
    )
    try:
        bundle = build_evidence_bundle(
            note_row=note,
            encounter_row=dict(encounter),
            signer_row=dict(signer) if signer else None,
            final_approver_row=dict(final_approver) if final_approver else None,
            caller_email=caller.email,
            caller_user_id=caller.user_id,
        )
    except EvidenceSigningError as e:
        # Org requires signing but the process has no HMAC key.
        # Returning 503 signals a misconfiguration, not a client bug.
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": e.error_code,
                "reason": e.reason,
            },
        )

    from app import audit as _audit
    _audit.record(
        event_type="note_evidence_bundle_issued",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=f"/note-versions/{note_id}/evidence-bundle",
        method="GET",
        detail=(
            f"note_id={note_id} "
            f"body_hash={bundle['envelope']['body_hash_sha256'][:12]}"
        ),
    )
    return bundle


@router.post("/note-versions/{note_id}/evidence-bundle/verify")
def note_evidence_bundle_verify(
    note_id: int,
    payload: dict,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Verify a previously-issued evidence bundle.

    Body: the bundle JSON as returned by
    GET /note-versions/{id}/evidence-bundle.

    Returns a structured verdict:
      { "body_hash_ok": bool, "signature": {...}, "note_id_match": bool }

    `body_hash_ok` is recomputed locally over the bundle body (minus
    envelope) — it confirms the payload has not been mutated in
    transit. `signature` reports whether the HMAC signature
    verifies against the host's signing key. `note_id_match`
    confirms the bundle references the URL path note_id; a mismatch
    indicates a caller tried to verify a bundle against the wrong
    resource.
    """
    _load_note_for_caller(note_id, caller)  # org scope + 404
    if not isinstance(payload, dict):
        raise _err(
            "malformed_bundle",
            "request body must be the JSON bundle as issued",
            400,
        )
    claimed_note_id = (payload.get("note") or {}).get("id")
    note_match = (int(claimed_note_id) == note_id) if claimed_note_id else False

    # Recompute the body hash locally. Copy the bundle and strip
    # envelope + signature before hashing — those are metadata about
    # the issuance, not the body proper.
    import json as _json
    body_only = {
        k: v for k, v in payload.items()
        if k not in ("envelope", "signature")
    }
    canonical = _json.dumps(
        body_only, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    import hashlib as _hashlib
    recomputed = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    claimed_hash = (payload.get("envelope") or {}).get("body_hash_sha256")
    body_hash_ok = bool(claimed_hash) and (recomputed == claimed_hash)

    from app.services.note_evidence import (
        classify_bundle_trust, verify_signature,
    )
    sig_verdict = verify_signature(payload)
    trust = classify_bundle_trust(body_hash_ok, sig_verdict)

    return {
        "note_id": note_id,
        "note_id_match": note_match,
        "body_hash_ok": body_hash_ok,
        "recomputed_body_hash": recomputed,
        "claimed_body_hash": claimed_hash,
        "signature": sig_verdict,
        # Phase 59 — unified operator-facing trust verdict. Folds
        # body_hash + signature into one actionable category so an
        # operator does not have to combine two fields mentally.
        "trust": trust,
    }


@router.get("/admin/operations/evidence-chain-verify")
def admin_evidence_chain_verify(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Re-verify the org's evidence chain end-to-end. Returns a
    structured verdict (ok / broken + first-broken-event-id).
    Non-destructive read; safe to call from the admin UI at any
    time."""
    _require_security_admin_inline(caller)
    from app.services.note_evidence import verify_chain
    return verify_chain(caller.organization_id).as_dict()


@router.get("/admin/operations/notes/{note_id}/evidence-health")
def admin_note_evidence_health(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Per-note evidence-health card. Used by the admin lifecycle
    surface to answer 'is this note's evidence complete?'.
    Security-admin scoped like the rest of /admin/operations/*."""
    _require_security_admin_inline(caller)
    note = _load_note_for_caller(note_id, caller)
    from app.services.note_evidence import note_evidence_health
    return note_evidence_health(note).as_dict()


# ---------------------------------------------------------------------------
# Phase 56 — export snapshots + chain seals + evidence-sink probe
# ---------------------------------------------------------------------------

@router.get("/note-versions/{note_id}/export-snapshots")
def note_export_snapshots_list(
    note_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Snapshot history for this note. Most-recent-first. Same
    org-scope contract as every other note read."""
    _load_note_for_caller(note_id, caller)
    from app.services.note_export_snapshots import list_snapshots_for_note
    rows = list_snapshots_for_note(note_id)
    return {
        "note_id": note_id,
        "snapshots": [
            {
                "id": int(r["id"]),
                "evidence_chain_event_id": r.get("evidence_chain_event_id"),
                "artifact_hash_sha256": r.get("artifact_hash_sha256"),
                "content_fingerprint": r.get("content_fingerprint"),
                "issued_at": (
                    r["issued_at"].isoformat()
                    if hasattr(r.get("issued_at"), "isoformat")
                    else r.get("issued_at")
                ),
                "issued_by_user_id": r.get("issued_by_user_id"),
                "issued_by_email": r.get("issued_by_email"),
                # Phase 57 — purge metadata. `artifact_purged_at`
                # null means the heavy body is still present.
                "artifact_purged_at": (
                    r["artifact_purged_at"].isoformat()
                    if hasattr(r.get("artifact_purged_at"), "isoformat")
                    else r.get("artifact_purged_at")
                ),
                "artifact_purged_reason": r.get("artifact_purged_reason"),
            }
            for r in rows
        ],
    }


@router.get("/note-versions/{note_id}/export-snapshots/{snapshot_id}")
def note_export_snapshot_get(
    note_id: int,
    snapshot_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Return a specific snapshot including the captured artifact
    JSON. Org-scope enforced on both the note and the snapshot —
    snapshot must belong to the same org as the caller."""
    _load_note_for_caller(note_id, caller)
    from app.services.note_export_snapshots import get_snapshot
    snap = get_snapshot(snapshot_id)
    if not snap or int(snap["note_version_id"]) != note_id:
        raise _err(
            "snapshot_not_found",
            "no such export snapshot for this note",
            404,
        )
    if int(snap["organization_id"]) != caller.organization_id:
        raise _err("snapshot_not_found", "no such export snapshot", 404)
    # artifact_json is stored as compact canonical text; parse for
    # transport convenience. Phase 57 — a purged snapshot keeps the
    # row but clears artifact_json; return null body in that case so
    # the consumer sees the honest "body no longer present" state
    # without having to parse an empty string.
    import json as _json
    raw = snap.get("artifact_json") or ""
    artifact = None
    if raw:
        try:
            artifact = _json.loads(raw)
        except Exception:
            artifact = None
    return {
        "id": int(snap["id"]),
        "note_version_id": int(snap["note_version_id"]),
        "encounter_id": int(snap["encounter_id"]),
        "evidence_chain_event_id": snap.get("evidence_chain_event_id"),
        "artifact_hash_sha256": snap["artifact_hash_sha256"],
        "content_fingerprint": snap.get("content_fingerprint"),
        "issued_at": (
            snap["issued_at"].isoformat()
            if hasattr(snap.get("issued_at"), "isoformat")
            else snap.get("issued_at")
        ),
        "issued_by_user_id": snap.get("issued_by_user_id"),
        "issued_by_email": snap.get("issued_by_email"),
        "artifact": artifact,
        "artifact_purged_at": (
            snap["artifact_purged_at"].isoformat()
            if hasattr(snap.get("artifact_purged_at"), "isoformat")
            else snap.get("artifact_purged_at")
        ),
        "artifact_purged_reason": snap.get("artifact_purged_reason"),
    }


class EvidenceChainSealBody(BaseModel):
    # Optional human-readable note on what was being sealed.
    note: str = Field(default="", max_length=500)


@router.post("/admin/operations/evidence-chain/seal")
def admin_evidence_chain_seal(
    payload: EvidenceChainSealBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Seal the current tip of the org's evidence chain. Persists
    the tip event_id + event_hash + event_count so subsequent
    verification runs can detect silent rewinds (drop an event,
    re-hash the chain: the tip hash changes but a stored seal says
    what it WAS)."""
    _require_security_admin_inline(caller)
    tip = fetch_one(
        "SELECT id, event_hash FROM note_evidence_events "
        "WHERE organization_id = :org "
        "ORDER BY id DESC LIMIT 1",
        {"org": caller.organization_id},
    )
    if not tip:
        raise _err(
            "evidence_chain_empty",
            "no evidence events exist for this organization; "
            "cannot seal an empty chain",
            409,
        )
    cnt_row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_evidence_events "
        "WHERE organization_id = :org",
        {"org": caller.organization_id},
    )
    event_count = int(cnt_row["n"]) if cnt_row else 0

    # Phase 57 — compute the seal hash at write time. We stamp a
    # known sealed_at so the hash is deterministic relative to what
    # gets stored. Then optionally sign it with the org's active
    # HMAC key.
    from datetime import datetime, timezone
    from app.services.note_evidence import (
        EvidenceSigningError,
        compute_seal_hash,
        sign_seal_hash,
    )
    sealed_at = datetime.now(timezone.utc)
    sealed_at_iso = sealed_at.isoformat()
    note_str = (payload.note or "").strip()[:500] or None
    seal_hash = compute_seal_hash(
        organization_id=caller.organization_id,
        tip_event_id=int(tip["id"]),
        tip_event_hash=tip["event_hash"],
        event_count=event_count,
        sealed_at_iso=sealed_at_iso,
        sealed_by_user_id=caller.user_id,
        sealed_by_email=caller.email,
        note=note_str,
    )
    try:
        signed = sign_seal_hash(seal_hash, caller.organization_id)
    except EvidenceSigningError as e:
        raise HTTPException(
            status_code=503,
            detail={"error_code": e.error_code, "reason": e.reason},
        )
    sig_hex = signed["signature_hex"] if signed else None
    sig_kid = signed["signing_key_id"] if signed else None

    with transaction() as conn:
        new_row = conn.execute(
            text(
                "INSERT INTO evidence_chain_seals ("
                " organization_id, tip_event_id, tip_event_hash, "
                " event_count, sealed_at, sealed_by_user_id, "
                " sealed_by_email, note, "
                " seal_hash_sha256, seal_signature_hex, "
                " seal_signing_key_id"
                ") VALUES ("
                " :org, :tid, :th, :n, :sa, :uid, :email, :note, "
                " :sh, :ss, :kid"
                ") RETURNING id, sealed_at"
            ),
            {
                "org": caller.organization_id,
                "tid": int(tip["id"]),
                "th": tip["event_hash"],
                "n": event_count,
                "sa": sealed_at_iso,
                "uid": caller.user_id,
                "email": caller.email,
                "note": note_str,
                "sh": seal_hash,
                "ss": sig_hex,
                "kid": sig_kid,
            },
        ).mappings().first()

    from app import audit as _audit
    _audit.record(
        event_type="evidence_chain_sealed",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/operations/evidence-chain/seal",
        method="POST",
        detail=(
            f"tip_event_id={tip['id']} event_count={event_count} "
            f"tip_hash={str(tip['event_hash'])[:12]} "
            f"seal_hash={seal_hash[:12]} "
            f"signed={'yes' if sig_hex else 'no'}"
        ),
    )
    return {
        "id": int(new_row["id"]),
        "organization_id": caller.organization_id,
        "tip_event_id": int(tip["id"]),
        "tip_event_hash": tip["event_hash"],
        "event_count": event_count,
        "sealed_at": sealed_at_iso,
        "seal_hash_sha256": seal_hash,
        "seal_signature_hex": sig_hex,
        "seal_signing_key_id": sig_kid,
    }


@router.get("/admin/operations/evidence-chain/seals")
def admin_evidence_chain_seals(
    verify: bool = Query(default=False),
    caller: Caller = Depends(require_caller),
) -> dict:
    """List recorded seals, newest first.

    Phase 57 — pass `?verify=true` to re-verify each seal's hash
    (and signature if present) as part of the response. When
    verify=false (default) the call is a cheap read; verify=true is
    O(N) hash computations — safe at the operational scale but not
    the default.
    """
    _require_security_admin_inline(caller)
    rows = fetch_all(
        "SELECT id, organization_id, tip_event_id, tip_event_hash, "
        "event_count, sealed_at, sealed_by_user_id, sealed_by_email, "
        "note, seal_hash_sha256, seal_signature_hex, "
        "seal_signing_key_id "
        "FROM evidence_chain_seals WHERE organization_id = :org "
        "ORDER BY id DESC LIMIT 200",
        {"org": caller.organization_id},
    )
    from app.services.note_evidence import verify_seal_row
    out = []
    for r in rows:
        r = dict(r)
        if hasattr(r.get("sealed_at"), "isoformat"):
            r["sealed_at"] = r["sealed_at"].isoformat()
        if verify:
            r["verification"] = verify_seal_row(r)
        out.append(r)
    return {
        "organization_id": caller.organization_id,
        "seals": out,
    }


@router.get("/admin/operations/evidence-chain/seals/{seal_id}/verify")
def admin_evidence_chain_seal_verify(
    seal_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Verify a single seal row. Returns the verification verdict
    plus the seal payload itself so the admin can see what was
    recomputed from what."""
    _require_security_admin_inline(caller)
    row = fetch_one(
        "SELECT id, organization_id, tip_event_id, tip_event_hash, "
        "event_count, sealed_at, sealed_by_user_id, sealed_by_email, "
        "note, seal_hash_sha256, seal_signature_hex, "
        "seal_signing_key_id "
        "FROM evidence_chain_seals WHERE id = :id",
        {"id": int(seal_id)},
    )
    if not row or int(row["organization_id"]) != caller.organization_id:
        raise _err("seal_not_found", "no such chain seal", 404)
    row = dict(row)
    if hasattr(row.get("sealed_at"), "isoformat"):
        row["sealed_at"] = row["sealed_at"].isoformat()

    from app.services.note_evidence import verify_seal_row
    verdict = verify_seal_row(row)
    # Strip the signature columns from the returned seal payload so
    # the verdict is the single source of truth for signed state.
    return {
        "seal": {
            "id": int(row["id"]),
            "tip_event_id": int(row["tip_event_id"]),
            "tip_event_hash": row["tip_event_hash"],
            "event_count": int(row["event_count"]),
            "sealed_at": row.get("sealed_at"),
            "sealed_by_user_id": row.get("sealed_by_user_id"),
            "sealed_by_email": row.get("sealed_by_email"),
            "note": row.get("note"),
        },
        "verification": verdict,
    }


@router.get("/admin/operations/signing-posture")
def admin_signing_posture(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Safe read-only view of the org's signing posture. Never
    exposes secret material; only key ids + consistency verdict."""
    _require_security_admin_inline(caller)
    from app.services.note_evidence import keyring_posture
    return keyring_posture(caller.organization_id)


class EvidenceSinkRetryBody(BaseModel):
    # Small, bounded retry window so a stuck backlog can't turn
    # into a giant single transaction. 100 per call is the cap.
    max_events: int = Field(default=100, ge=1, le=500)


@router.post("/admin/operations/evidence-sink/retry-failed")
def admin_evidence_sink_retry(
    payload: EvidenceSinkRetryBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Retry evidence events whose previous sink delivery failed.

    Scope:
      - only events in this org
      - only rows with sink_status='failed'
      - up to `max_events` per call (default 100, cap 500)
      - increments sink_attempt_count on each row touched
      - NEVER modifies any canonical evidence column
      - audited per-call with `evidence_sink_retry_attempted`

    Returns `{attempted, sent, failed, skipped, events}` so the
    operator sees both the per-call summary and the per-row outcome
    for support diagnosis.
    """
    _require_security_admin_inline(caller)
    from app.services.evidence_sink import retry_failed_deliveries
    result = retry_failed_deliveries(
        caller.organization_id, max_events=payload.max_events,
    )
    from app import audit as _audit
    _audit.record(
        event_type="evidence_sink_retry_attempted",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/operations/evidence-sink/retry-failed",
        method="POST",
        detail=(
            f"attempted={result.attempted} sent={result.sent} "
            f"failed={result.failed} skipped={result.skipped}"
        ),
    )
    return {
        "attempted": result.attempted,
        "sent": result.sent,
        "failed": result.failed,
        "skipped": result.skipped,
        "events": result.events,
    }


class SnapshotRetentionSweepBody(BaseModel):
    # Operator-initiated sweep. Default dry_run=True so an accident
    # does not soft-purge anything without a deliberate second call.
    dry_run: bool = True


@router.post("/admin/operations/export-snapshots/retention-sweep")
def admin_export_snapshot_retention_sweep(
    payload: SnapshotRetentionSweepBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Apply the org's export-snapshot retention policy.

    Operator flow:
      1. POST with dry_run=true → see candidate ids + counts.
      2. POST with dry_run=false → soft-purge those bodies.

    Safety:
      - retention must be explicitly configured (null → no-op)
      - floor 90 days enforced at policy-write time
      - row + hash + linkage preserved; only artifact_json cleared
      - audited with `export_snapshot_retention_sweep`
    """
    _require_security_admin_inline(caller)
    from app.services.note_export_snapshots import sweep_retention
    result = sweep_retention(
        caller.organization_id, dry_run=payload.dry_run,
    )
    from app import audit as _audit
    _audit.record(
        event_type="export_snapshot_retention_sweep",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/operations/export-snapshots/retention-sweep",
        method="POST",
        detail=(
            f"dry_run={result.dry_run} retention_days={result.retention_days} "
            f"candidates={result.candidates_found} purged={result.purged}"
        ),
    )
    return result.as_dict()


class EvidenceEventAbandonBody(BaseModel):
    reason: str = Field(default="", max_length=500)


@router.post("/admin/operations/evidence-events/{event_id}/abandon")
def admin_evidence_event_abandon(
    event_id: int,
    payload: EvidenceEventAbandonBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Operator-initiated 'give up' on a failed evidence delivery.

    Flips `sink_retry_disposition` to 'abandoned' so the retry
    sweep will not pick the row up again. The evidence chain row
    itself is untouched; only the sink-tracking columns move.
    Audited as `evidence_event_abandoned`."""
    _require_security_admin_inline(caller)
    from app.services.evidence_sink import abandon_event
    result = abandon_event(
        evidence_event_id=event_id,
        organization_id=caller.organization_id,
        operator_reason=payload.reason,
    )
    from app import audit as _audit
    if result.ok:
        _audit.record(
            event_type="evidence_event_abandoned",
            request_id=None,
            actor_email=caller.email,
            actor_user_id=caller.user_id,
            organization_id=caller.organization_id,
            path=f"/admin/operations/evidence-events/{event_id}/abandon",
            method="POST",
            detail=(
                f"event_id={event_id} "
                f"prev={result.previous_disposition or 'none'} "
                f"new={result.new_disposition}"
            ),
        )
        return {
            "ok": True,
            "evidence_event_id": result.evidence_event_id,
            "previous_disposition": result.previous_disposition,
            "new_disposition": result.new_disposition,
        }
    status_code = (
        404 if result.error_code == "evidence_event_not_found" else 409
    )
    raise HTTPException(
        status_code=status_code,
        detail={
            "error_code": result.error_code or "abandon_failed",
            "reason": result.reason or "could not abandon event",
        },
    )


@router.post("/admin/operations/evidence-sink/retention-sweep")
def admin_evidence_sink_retention_sweep(
    payload: SnapshotRetentionSweepBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Apply the org's `evidence_sink_retention_days` policy by
    clearing `sink_error` on abandoned / permanent_failure rows
    older than the window. The canonical evidence chain is
    untouched — only the operational noise column moves.

    Operator flow mirrors the snapshot retention sweep: dry_run=true
    lists candidates; dry_run=false performs the clear."""
    _require_security_admin_inline(caller)
    from app.services.evidence_sink import sweep_sink_retention
    result = sweep_sink_retention(
        caller.organization_id, dry_run=bool(payload.dry_run),
    )
    from app import audit as _audit
    _audit.record(
        event_type="evidence_sink_retention_sweep",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/operations/evidence-sink/retention-sweep",
        method="POST",
        detail=(
            f"dry_run={result.dry_run} "
            f"retention_days={result.retention_days} "
            f"candidates={result.candidates_found} "
            f"cleared={result.cleared}"
        ),
    )
    return result.as_dict()


@router.post("/admin/operations/evidence-sink/test")
def admin_evidence_sink_test(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Probe the configured evidence sink with a synthetic event.
    Does NOT touch the DB chain — this is a transport test only."""
    _require_security_admin_inline(caller)
    from app.services.evidence_sink import probe_evidence_sink
    result = probe_evidence_sink(caller.organization_id)
    from app import audit as _audit
    _audit.record(
        event_type="admin_evidence_sink_test",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/operations/evidence-sink/test",
        method="POST",
        detail=(
            f"mode={result.get('mode')} ok={result.get('ok')} "
            f"error={result.get('error_code') or '-'}"
        ),
    )
    return result


# ---------------------------------------------------------------------------
# Phase 58 — practice backup / restore / reinstall recovery
# ---------------------------------------------------------------------------

class PracticeBackupCreateBody(BaseModel):
    # Optional operator note (e.g. "quarterly archive") — stored on
    # the history record, not inside the bundle.
    note: str = Field(default="", max_length=500)


@router.post("/admin/practice-backup/create")
def practice_backup_create(
    payload: PracticeBackupCreateBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Assemble a backup bundle for the caller's org. Returns the
    bundle JSON directly so the browser can save-as via a download
    prompt. The server does NOT persist the bundle bytes — only a
    small metadata record."""
    if caller.role != "admin":
        raise _err(
            "role_admin_required",
            "only admin may create a practice backup",
            403,
        )
    from app.services.practice_backup import build_backup, record_history
    built = build_backup(
        organization_id=caller.organization_id,
        issued_by_user_id=caller.user_id,
        issued_by_email=caller.email,
    )
    record_id = record_history(
        organization_id=caller.organization_id,
        event_type="backup_created",
        created_by_user_id=caller.user_id,
        created_by_email=caller.email,
        bundle_version=built.payload.get("bundle_version") or "",
        schema_version=built.payload.get("schema_version") or "",
        artifact_bytes_size=len(built.canonical_bytes),
        artifact_hash_sha256=built.hash_sha256,
        counts=built.counts,
        note=(payload.note or "").strip() or None,
    )

    from app import audit as _audit
    _audit.record(
        event_type="practice_backup_created",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/practice-backup/create",
        method="POST",
        detail=(
            f"record_id={record_id} hash={built.hash_sha256[:12]} "
            f"bytes={len(built.canonical_bytes)}"
        ),
    )
    return {
        "record_id": record_id,
        "bundle": built.payload,
        "hash_sha256": built.hash_sha256,
        "bytes_size": len(built.canonical_bytes),
        "counts": built.counts,
    }


@router.get("/admin/practice-backup/download")
def practice_backup_download(
    caller: Caller = Depends(require_caller),
):
    """Same bundle as /create, delivered as an attachment so the
    browser shows a native Save-As dialog. The endpoint is
    idempotent (no write) but still audited since it exposes
    cross-table org state to a file on the operator's disk."""
    if caller.role != "admin":
        raise _err(
            "role_admin_required",
            "only admin may download a practice backup",
            403,
        )
    from app.services.practice_backup import build_backup, record_history
    built = build_backup(
        organization_id=caller.organization_id,
        issued_by_user_id=caller.user_id,
        issued_by_email=caller.email,
    )
    record_history(
        organization_id=caller.organization_id,
        event_type="backup_created",
        created_by_user_id=caller.user_id,
        created_by_email=caller.email,
        bundle_version=built.payload.get("bundle_version") or "",
        schema_version=built.payload.get("schema_version") or "",
        artifact_bytes_size=len(built.canonical_bytes),
        artifact_hash_sha256=built.hash_sha256,
        counts=built.counts,
        note="download",
    )
    from app import audit as _audit
    _audit.record(
        event_type="practice_backup_downloaded",
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/practice-backup/download",
        method="GET",
        detail=(
            f"hash={built.hash_sha256[:12]} "
            f"bytes={len(built.canonical_bytes)}"
        ),
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"chartnav-backup-org{caller.organization_id}-{stamp}.json"
    return Response(
        content=built.canonical_bytes,
        media_type="application/vnd.chartnav.practice-backup+json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-ChartNav-Backup-Hash-SHA256": built.hash_sha256,
            "X-ChartNav-Backup-Version": built.payload.get("bundle_version") or "",
        },
    )


@router.get("/admin/practice-backup/history")
def practice_backup_history(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Metadata history of backup + restore events for this org.
    The bundle bytes themselves are not server-persisted; this
    endpoint returns the hashes + timestamps so an operator can
    correlate a downloaded file against what was issued."""
    if caller.role != "admin":
        raise _err(
            "role_admin_required",
            "only admin may view practice backup history",
            403,
        )
    from app.services.practice_backup import list_history
    return {
        "organization_id": caller.organization_id,
        "history": list_history(caller.organization_id),
    }


class PracticeBackupValidateBody(BaseModel):
    bundle: dict


@router.post("/admin/practice-backup/validate")
def practice_backup_validate(
    payload: PracticeBackupValidateBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Validate an uploaded bundle WITHOUT writing. Returns the
    structured verdict. Admins use this to verify a downloaded file
    round-trips correctly before attempting restore."""
    if caller.role != "admin":
        raise _err(
            "role_admin_required",
            "only admin may validate a practice backup",
            403,
        )
    from app.services.practice_backup import validate_backup
    verdict = validate_backup(
        payload.bundle,
        expected_organization_id=caller.organization_id,
    )
    return verdict.as_dict()


class PracticeBackupRestoreBody(BaseModel):
    bundle: dict
    # Default 'empty_target_only' — the only supported mode today.
    mode: str = Field(default="empty_target_only", max_length=32)
    # Hard default true for safety: a missing flag defaults to
    # dry-run, so an accidental POST never destroys anything.
    dry_run: bool = True
    # Must be explicitly true for a real write.
    confirm_destructive: bool = False


@router.post("/admin/practice-backup/restore")
def practice_backup_restore(
    payload: PracticeBackupRestoreBody,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Restore a bundle into the caller's org.

    SAFETY (enforced at the route layer):
      - security-admin only (separate from plain admin).
      - bundle must validate (hash + shape + version).
      - source organization in the bundle must equal caller's org.
      - target org must be empty (no encounters/patients/notes).
      - dry_run=true returns counts without writing.
      - confirm_destructive=true required for a real write.

    Returns a RestoreResult. On failure raises a 4xx with a
    precise error_code so the operator can diagnose."""
    _require_security_admin_inline(caller)

    from app.services.practice_backup import (
        RestoreError, restore_backup, validate_backup, record_history,
    )
    verdict = validate_backup(
        payload.bundle, expected_organization_id=caller.organization_id,
    )
    if not verdict.ok:
        raise HTTPException(
            status_code=(
                404
                if verdict.error_code == "backup_org_mismatch"
                else 400
            ),
            detail={
                "error_code": verdict.error_code or "invalid_bundle",
                "reason": verdict.reason or "bundle failed validation",
            },
        )

    try:
        result = restore_backup(
            bundle=payload.bundle,
            target_organization_id=caller.organization_id,
            mode=payload.mode,
            confirm_destructive=bool(payload.confirm_destructive),
            dry_run=bool(payload.dry_run),
        )
    except RestoreError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"error_code": e.code, "reason": e.reason},
        )

    if not result.dry_run:
        record_history(
            organization_id=caller.organization_id,
            event_type="restore_applied",
            created_by_user_id=caller.user_id,
            created_by_email=caller.email,
            bundle_version=verdict.bundle_version or "",
            schema_version=verdict.schema_version or "",
            artifact_bytes_size=None,
            artifact_hash_sha256=verdict.claimed_hash,
            counts=result.applied_counts,
            note=f"mode={result.mode}",
        )

    from app import audit as _audit
    _audit.record(
        event_type=(
            "practice_backup_restore_dry_run"
            if result.dry_run else "practice_backup_restore_applied"
        ),
        request_id=None,
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path="/admin/practice-backup/restore",
        method="POST",
        detail=(
            f"dry_run={result.dry_run} mode={result.mode} "
            f"hash={(verdict.claimed_hash or '')[:12]} "
            f"applied={sum(result.applied_counts.values())}"
        ),
    )
    return result.as_dict()


@router.get("/admin/operations/categories")
def admin_operations_categories(
    caller: Caller = Depends(require_caller),
) -> dict:
    """Publish the full category taxonomy + metadata so the UI can
    render labels and remediation copy without inlining it.
    """
    _require_security_admin_inline(caller)
    from app.services.operations_exceptions import (
        CATEGORY_METADATA,
        ExceptionCategory,
    )
    return {
        "categories": [
            {"value": c.value, **CATEGORY_METADATA[c]}
            for c in ExceptionCategory
        ],
    }


# =====================================================================
# Phase 63 — Reminders (calendar + follow-up nudges)
# =====================================================================
#
# A `reminder` is a lightweight clinician work item with a due date.
# It can attach to a specific encounter, a specific patient (by MRN
# string), or nothing in particular (a free-floating operational
# nudge). Reminders are org-scoped and show up on the calendar alongside
# encounters, so "what still needs attention today / this week" is
# one glanceable surface.
#
# Contract:
#   GET    /reminders                  list (filter by status + date range)
#   POST   /reminders                  create (admin | clinician)
#   GET    /reminders/{id}             read one
#   PATCH  /reminders/{id}             update title/body/due_at/status
#   POST   /reminders/{id}/complete    mark completed (sets completed_*)
#   DELETE /reminders/{id}             soft: flips status to 'cancelled'
#
# All routes enforce `organization_id == caller.organization_id`.

REMINDER_COLUMNS = (
    "id, organization_id, encounter_id, patient_identifier, title, "
    "body, due_at, status, completed_at, completed_by_user_id, "
    "created_by_user_id, created_at, updated_at"
)

_REMINDER_STATUSES = {"pending", "completed", "cancelled"}


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    body: Optional[str] = Field(default=None, max_length=4000)
    due_at: datetime
    encounter_id: Optional[int] = None
    patient_identifier: Optional[str] = Field(default=None, max_length=64)


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    body: Optional[str] = Field(default=None, max_length=4000)
    due_at: Optional[datetime] = None
    status: Optional[str] = None


def _reminder_row_to_dict(r: dict) -> dict:
    # SQLite returns datetimes as strings; leave them for the client.
    return dict(r)


def _assert_reminder_encounter_in_org(
    caller: Caller, encounter_id: Optional[int]
) -> None:
    if encounter_id is None:
        return
    enc = fetch_one(
        "SELECT id, organization_id FROM encounters WHERE id = :id",
        {"id": encounter_id},
    )
    if not enc:
        raise _err("encounter_not_found", "encounter does not exist", 404)
    ensure_same_org(caller, int(enc["organization_id"]))


@router.get("/reminders")
def list_reminders(
    response: Response,
    caller: Caller = Depends(require_caller),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_in: Optional[str] = Query(default=None, alias="status"),
    due_from: Optional[datetime] = Query(default=None),
    due_to: Optional[datetime] = Query(default=None),
    encounter_id: Optional[int] = Query(default=None),
    patient_identifier: Optional[str] = Query(default=None, max_length=64),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if status_in:
        # Comma-separated list; ignore unknowns.
        wanted = [
            s.strip() for s in status_in.split(",")
            if s.strip() in _REMINDER_STATUSES
        ]
        if wanted:
            placeholders = ",".join(f":s{i}" for i in range(len(wanted)))
            clauses.append(f"status IN ({placeholders})")
            for i, s in enumerate(wanted):
                params[f"s{i}"] = s
    if due_from is not None:
        clauses.append("due_at >= :from")
        params["from"] = due_from
    if due_to is not None:
        clauses.append("due_at <= :to")
        params["to"] = due_to
    if encounter_id is not None:
        clauses.append("encounter_id = :eid")
        params["eid"] = encounter_id
    if patient_identifier:
        clauses.append("patient_identifier = :pid")
        params["pid"] = patient_identifier
    where = " WHERE " + " AND ".join(clauses)

    total = int(
        fetch_one(f"SELECT COUNT(*) AS n FROM reminders{where}", params)["n"]
    )
    rows = fetch_all(
        f"SELECT {REMINDER_COLUMNS} FROM reminders{where} "
        "ORDER BY due_at ASC, id ASC LIMIT :limit OFFSET :offset",
        {**params, "limit": limit, "offset": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    return [_reminder_row_to_dict(r) for r in rows]


@router.post("/reminders", status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    if caller.role not in {"admin", "clinician"}:
        raise _err("role_forbidden", "admin or clinician only", 403)
    _assert_reminder_encounter_in_org(caller, payload.encounter_id)
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "reminders",
            {
                "organization_id": caller.organization_id,
                "encounter_id": payload.encounter_id,
                "patient_identifier": payload.patient_identifier,
                "title": payload.title,
                "body": payload.body,
                "due_at": payload.due_at,
                "status": "pending",
                "created_by_user_id": caller.user_id,
            },
        )
    row = fetch_one(
        f"SELECT {REMINDER_COLUMNS} FROM reminders WHERE id = :id",
        {"id": new_id},
    )
    return _reminder_row_to_dict(row)


def _load_reminder_for_caller(reminder_id: int, caller: Caller) -> dict:
    row = fetch_one(
        f"SELECT {REMINDER_COLUMNS} FROM reminders WHERE id = :id",
        {"id": reminder_id},
    )
    if not row:
        raise _err("reminder_not_found", "reminder does not exist", 404)
    ensure_same_org(caller, int(row["organization_id"]))
    return row


@router.get("/reminders/{reminder_id}")
def get_reminder(
    reminder_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    return _reminder_row_to_dict(_load_reminder_for_caller(reminder_id, caller))


@router.patch("/reminders/{reminder_id}")
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    caller: Caller = Depends(require_caller),
) -> dict:
    if caller.role not in {"admin", "clinician"}:
        raise _err("role_forbidden", "admin or clinician only", 403)
    _load_reminder_for_caller(reminder_id, caller)
    set_parts: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": reminder_id}
    if payload.title is not None:
        set_parts.append("title = :title")
        params["title"] = payload.title
    if payload.body is not None:
        set_parts.append("body = :body")
        params["body"] = payload.body
    if payload.due_at is not None:
        set_parts.append("due_at = :due")
        params["due"] = payload.due_at
    if payload.status is not None:
        if payload.status not in _REMINDER_STATUSES:
            raise _err(
                "invalid_status",
                f"status must be one of {sorted(_REMINDER_STATUSES)}",
                400,
            )
        set_parts.append("status = :status")
        params["status"] = payload.status
        if payload.status == "completed":
            set_parts.append("completed_at = CURRENT_TIMESTAMP")
            set_parts.append("completed_by_user_id = :uid")
            params["uid"] = caller.user_id
    with transaction() as conn:
        conn.execute(
            text(
                f"UPDATE reminders SET {', '.join(set_parts)} WHERE id = :id"
            ),
            params,
        )
    row = fetch_one(
        f"SELECT {REMINDER_COLUMNS} FROM reminders WHERE id = :id",
        {"id": reminder_id},
    )
    return _reminder_row_to_dict(row)


@router.post("/reminders/{reminder_id}/complete")
def complete_reminder(
    reminder_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    if caller.role not in {"admin", "clinician"}:
        raise _err("role_forbidden", "admin or clinician only", 403)
    r = _load_reminder_for_caller(reminder_id, caller)
    if r["status"] == "completed":
        # Idempotent — return the existing row.
        return _reminder_row_to_dict(r)
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE reminders SET status = 'completed', "
                "completed_at = CURRENT_TIMESTAMP, "
                "completed_by_user_id = :uid, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": reminder_id, "uid": caller.user_id},
        )
    row = fetch_one(
        f"SELECT {REMINDER_COLUMNS} FROM reminders WHERE id = :id",
        {"id": reminder_id},
    )
    return _reminder_row_to_dict(row)


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_200_OK)
def cancel_reminder(
    reminder_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    if caller.role not in {"admin", "clinician"}:
        raise _err("role_forbidden", "admin or clinician only", 403)
    _load_reminder_for_caller(reminder_id, caller)
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE reminders SET status = 'cancelled', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": reminder_id},
        )
    row = fetch_one(
        f"SELECT {REMINDER_COLUMNS} FROM reminders WHERE id = :id",
        {"id": reminder_id},
    )
    return _reminder_row_to_dict(row)


# =====================================================================
# Phase 2 item 1 — Referring providers + consult letters
# Spec: docs/chartnav/closure/PHASE_B_Referring_Provider_Communication.md
# =====================================================================

REFERRING_PROVIDER_COLUMNS = (
    "id, organization_id, name, practice, npi_10, phone, fax, email, "
    "created_at"
)

CONSULT_LETTER_COLUMNS = (
    "id, organization_id, encounter_id, note_version_id, "
    "referring_provider_id, rendered_pdf_storage_ref, delivery_status, "
    "delivered_via, sent_at, created_at"
)


class ReferringProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    practice: Optional[str] = Field(default=None, max_length=255)
    npi_10: str = Field(..., min_length=10, max_length=10)
    phone: Optional[str] = Field(default=None, max_length=64)
    fax: Optional[str] = Field(default=None, max_length=64)
    email: Optional[str] = Field(default=None, max_length=255)


class ConsultLetterCreate(BaseModel):
    referring_provider_id: int
    delivery_channel: str = Field(default="download")


@router.get("/referring-providers")
def list_referring_providers(
    caller: Caller = Depends(require_caller),
) -> dict:
    rows = fetch_all(
        f"SELECT {REFERRING_PROVIDER_COLUMNS} FROM referring_providers "
        f"WHERE organization_id = :oid ORDER BY name",
        {"oid": caller.organization_id},
    )
    return {"items": [dict(r) for r in rows]}


@router.post("/referring-providers", status_code=201)
def create_referring_provider(
    body: ReferringProviderCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    if caller.role not in {"admin", "clinician"}:
        raise _err(
            "role_forbidden",
            "only admin or clinician may register referring providers",
            403,
        )
    from app.services.consult_letters import is_valid_npi10
    if not is_valid_npi10(body.npi_10):
        raise _err(
            "invalid_npi_10",
            "NPI must be a 10-digit number passing the CMS Luhn check",
            400,
        )
    existing = fetch_one(
        "SELECT id FROM referring_providers "
        "WHERE organization_id = :oid AND npi_10 = :npi",
        {"oid": caller.organization_id, "npi": body.npi_10},
    )
    if existing:
        raise _err(
            "duplicate_referring_provider",
            "a referring provider with that NPI already exists in your "
            "organization",
            409,
        )
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "referring_providers",
            {
                "organization_id": caller.organization_id,
                "name": body.name,
                "practice": body.practice,
                "npi_10": body.npi_10,
                "phone": body.phone,
                "fax": body.fax,
                "email": body.email,
            },
        )
    row = fetch_one(
        f"SELECT {REFERRING_PROVIDER_COLUMNS} FROM referring_providers "
        f"WHERE id = :id",
        {"id": new_id},
    )
    return dict(row)


@router.post("/note-versions/{note_version_id}/consult-letter", status_code=201)
def create_consult_letter(
    note_version_id: int,
    body: ConsultLetterCreate,
    caller: Caller = Depends(require_caller),
) -> dict:
    """Render (or return the existing) consult letter for a signed note
    and a referring provider.

    - 422 if the note version is not signed.
    - 404 if the note version is in a different org.
    - 404 if the referring provider is in a different org.
    - 200 (idempotent) if a letter already exists for this
      (note_version_id, referring_provider_id) pair.
    - 400 on unknown delivery_channel.
    """
    from app.services.consult_letters import (
        VALID_CHANNELS,
        dispatch_delivery,
        render_letter_pdf,
    )
    note = fetch_one(
        "SELECT nv.id, nv.encounter_id, nv.signed_at, nv.note_text, "
        "e.organization_id, e.patient_identifier, e.patient_name, "
        "e.provider_name, e.scheduled_at, e.completed_at "
        "FROM note_versions nv JOIN encounters e ON nv.encounter_id = e.id "
        "WHERE nv.id = :id",
        {"id": note_version_id},
    )
    if not note or note["organization_id"] != caller.organization_id:
        raise _err(
            "note_version_not_found",
            "no such note version in your organization",
            404,
        )
    if not note.get("signed_at"):
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "note_not_signed",
                "reason": "consult letter requires a signed note version",
            },
        )
    if body.delivery_channel not in VALID_CHANNELS:
        raise _err(
            "invalid_delivery_channel",
            f"delivery_channel must be one of {VALID_CHANNELS}",
            400,
        )
    rp = fetch_one(
        f"SELECT {REFERRING_PROVIDER_COLUMNS} FROM referring_providers "
        f"WHERE id = :id",
        {"id": body.referring_provider_id},
    )
    if not rp or rp["organization_id"] != caller.organization_id:
        raise _err(
            "referring_provider_not_found",
            "no such referring provider in your organization",
            404,
        )

    existing = fetch_one(
        f"SELECT {CONSULT_LETTER_COLUMNS} FROM consult_letters "
        f"WHERE note_version_id = :nv AND referring_provider_id = :rp",
        {"nv": note_version_id, "rp": body.referring_provider_id},
    )
    if existing:
        return {**dict(existing), "_idempotent": True}

    org_row = fetch_one(
        "SELECT name FROM organizations WHERE id = :id",
        {"id": caller.organization_id},
    ) or {"name": ""}
    pdf_bytes = render_letter_pdf(
        encounter=dict(note),
        note_text=note.get("note_text") or "",
        referring_provider=dict(rp),
        org_name=org_row.get("name", ""),
    )

    delivery = dispatch_delivery(
        channel=body.delivery_channel,
        referring_provider=dict(rp),
    )
    storage_ref = (
        f"consult-letters/{note_version_id}/{body.referring_provider_id}.pdf"
    )
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "consult_letters",
            {
                "organization_id": caller.organization_id,
                "encounter_id": note["encounter_id"],
                "note_version_id": note_version_id,
                "referring_provider_id": body.referring_provider_id,
                "rendered_pdf_storage_ref": storage_ref,
                "pdf_bytes": pdf_bytes,
                "delivery_status": delivery["delivery_status"],
                "delivered_via": delivery["delivered_via"],
                "sent_at": delivery["sent_at"],
            },
        )
    row = fetch_one(
        f"SELECT {CONSULT_LETTER_COLUMNS} FROM consult_letters WHERE id = :id",
        {"id": new_id},
    )
    return {
        **dict(row),
        "advisory": delivery["advisory"],
    }


@router.get("/consult-letters/{letter_id}/pdf")
def download_consult_letter_pdf(
    letter_id: int,
    caller: Caller = Depends(require_caller),
) -> Response:
    row = fetch_one(
        "SELECT id, organization_id, pdf_bytes "
        "FROM consult_letters WHERE id = :id",
        {"id": letter_id},
    )
    if not row or row["organization_id"] != caller.organization_id:
        raise _err(
            "consult_letter_not_found",
            "no such consult letter in your organization",
            404,
        )
    return Response(content=row["pdf_bytes"], media_type="application/pdf")
