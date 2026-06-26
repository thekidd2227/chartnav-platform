"""Phase 20B — Structured-data layer route handlers.

Endpoints land under five logical resource groups:

  * /segments + /patients/{id}/segments  — patient segmentation
  * /patients/{id}/tags                  — lightweight tagging
  * /patients/{id}/problem-list          — structured problem list
  * /workflow-templates + stages         — clinic workflow templates
  * /work-queues                         — cross-tab task queue
  * /role-views                          — saved per-role views

RBAC summary (per Phase 20A plan):
  * ``admin``                — full write across every resource
  * ``admin + clinician``    — write segments-on-patient, tags,
                                problem list items, queue items
  * ``reviewer``             — read-only on every resource
  * ``front_desk``           — (additive role planned for Phase 20C;
                                falls into the read-only bucket here)
  * ``technician``           — (additive role planned for Phase 20C;
                                read + queue claim/progress)

Org isolation: every resolver checks ``organization_id`` against the
caller and returns 404 (not 403) on cross-org access — preserves
the existing no-existence-leak invariant.

Audit: every write emits a ``security_audit_events`` row whose
``detail`` is metadata-only (entity ID + action + a small set of
typed fields like status / priority / queue_type). NEVER:
  * raw criteria_json / payload_json / filters_json / columns_json
  * raw condition_label text (clinician-authored, may shadow PHI)
  * raw segment.description / template.description / tag value
  * any clinical body text from related encounters / notes / artifacts
"""

from __future__ import annotations

import json
from datetime import date, datetime
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
from pydantic import BaseModel, Field

from app.audit import record as audit_record
from app.auth import Caller, ensure_same_org, require_caller
from app.authz import (
    ROLE_ADMIN,
    ROLE_CLINICIAN,
    ROLE_REVIEWER,
    forbidden,
    require_admin,
    require_roles,
)
from app.db import fetch_all, fetch_one, insert_returning_id, transaction


router = APIRouter(tags=["phase-20b-structured-data"])


# ============================================================
# Constants + validation helpers
# ============================================================

PROBLEM_STATUSES: frozenset[str] = frozenset(
    {"active", "monitoring", "inactive", "resolved"}
)
EYE_VALUES: frozenset[str] = frozenset({"OD", "OS", "OU"})
QUEUE_PRIORITIES: frozenset[str] = frozenset(
    {"low", "normal", "high", "urgent"}
)
QUEUE_STATUSES: frozenset[str] = frozenset(
    {"open", "in_progress", "blocked", "completed", "dismissed"}
)
VIEW_PRESET_ROLES: frozenset[str] = frozenset(
    {"admin", "clinician", "reviewer", "front_desk", "technician"}
)
WORKFLOW_OWNER_ROLES: frozenset[str] = VIEW_PRESET_ROLES


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _require_write_role(caller: Caller, *, allowed: set[str]) -> None:
    if caller.role not in allowed:
        raise forbidden(
            "role_forbidden",
            f"role '{caller.role}' is not permitted; "
            f"requires one of {sorted(allowed)}",
        )


def _validate_json_object(
    raw: Any, *, field_name: str, allow_array: bool = False
) -> Optional[str]:
    """Validate that ``raw`` is None or a JSON-serializable object/array,
    return its serialized form for storage. Reject scalars + strings."""
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        if isinstance(raw, list) and not allow_array:
            raise _err(
                "invalid_payload",
                f"'{field_name}' must be a JSON object",
                400,
            )
        try:
            return json.dumps(raw)
        except (TypeError, ValueError) as e:
            raise _err(
                "invalid_payload",
                f"'{field_name}' is not JSON-serializable: {e}",
                400,
            )
    raise _err(
        "invalid_payload",
        f"'{field_name}' must be a JSON object"
        + (" or array" if allow_array else ""),
        400,
    )


def _parse_json_field(raw: Optional[str]) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


# ============================================================
# Org-scoped resolvers (404 on cross-org; no existence leak)
# ============================================================


def _resolve_patient(patient_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM patients WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("patient_not_found", "patient not found", 404)
    return int(row["id"])


def _resolve_segment(segment_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM patient_segments "
        "WHERE id = :id AND organization_id = :org",
        {"id": segment_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("segment_not_found", "segment not found", 404)
    return dict(row)


def _resolve_tag(tag_id: int, patient_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM patient_tags "
        "WHERE id = :id AND patient_id = :pid AND organization_id = :org",
        {"id": tag_id, "pid": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("tag_not_found", "tag not found", 404)
    return dict(row)


def _resolve_problem(item_id: int, patient_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM patient_problem_list "
        "WHERE id = :id AND patient_id = :pid AND organization_id = :org",
        {"id": item_id, "pid": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("problem_item_not_found", "problem item not found", 404)
    return dict(row)


def _resolve_template(template_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM clinic_workflow_templates "
        "WHERE id = :id AND organization_id = :org",
        {"id": template_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("template_not_found", "workflow template not found", 404)
    return dict(row)


def _resolve_stage(stage_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM clinic_workflow_stages "
        "WHERE id = :id AND organization_id = :org",
        {"id": stage_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("stage_not_found", "workflow stage not found", 404)
    return dict(row)


def _resolve_queue_item(item_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM work_queue_items "
        "WHERE id = :id AND organization_id = :org",
        {"id": item_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("queue_item_not_found", "queue item not found", 404)
    return dict(row)


def _resolve_view_preset(preset_id: int, caller: Caller) -> dict:
    row = fetch_one(
        "SELECT * FROM role_view_presets "
        "WHERE id = :id AND organization_id = :org",
        {"id": preset_id, "org": caller.organization_id},
    )
    if not row:
        raise _err("preset_not_found", "role view preset not found", 404)
    return dict(row)


def _check_org_match(
    table: str,
    fk_id: int,
    caller: Caller,
    not_found_code: str,
) -> None:
    """Verify a referenced row in ``table`` exists in caller's org.
    Raises 404 with ``not_found_code`` on cross-org or missing."""
    row = fetch_one(
        f"SELECT id FROM {table} WHERE id = :id AND organization_id = :org",
        {"id": fk_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(not_found_code, f"{not_found_code.replace('_', ' ')}", 404)


def _audit(
    request: Request,
    caller: Caller,
    *,
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


def _serialize_segment(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "name": row["name"],
        "description": row.get("description"),
        "segment_type": row["segment_type"],
        "criteria_json": _parse_json_field(row.get("criteria_json")),
        "is_active": bool(row.get("is_active", True)),
        "created_by_user_id": (
            int(row["created_by_user_id"])
            if row.get("created_by_user_id") is not None
            else None
        ),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _serialize_membership(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "segment_id": int(row["segment_id"]),
        "source": row["source"],
        "reason": row.get("reason"),
        "created_at": row.get("created_at"),
    }


def _serialize_tag(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "tag": row["tag"],
        "color": row.get("color"),
        "created_by_user_id": (
            int(row["created_by_user_id"])
            if row.get("created_by_user_id") is not None
            else None
        ),
        "created_at": row.get("created_at"),
    }


def _serialize_problem(row: dict) -> dict:
    onset = row.get("onset_date")
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "patient_id": int(row["patient_id"]),
        "condition_code": row.get("condition_code"),
        "condition_label": row["condition_label"],
        "specialty": row.get("specialty"),
        "eye": row.get("eye"),
        "status": row["status"],
        "onset_date": onset.isoformat() if isinstance(onset, date) else onset,
        "last_reviewed_at": row.get("last_reviewed_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _serialize_template(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "name": row["name"],
        "specialty": row.get("specialty"),
        "role_owner": row["role_owner"],
        "description": row.get("description"),
        "is_active": bool(row.get("is_active", True)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _serialize_stage(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "template_id": int(row["template_id"]),
        "name": row["name"],
        "stage_order": int(row["stage_order"]),
        "role_owner": row["role_owner"],
        "sla_minutes": (
            int(row["sla_minutes"])
            if row.get("sla_minutes") is not None
            else None
        ),
        "created_at": row.get("created_at"),
    }


def _serialize_queue_item(row: dict) -> dict:
    def _opt_int(key: str) -> Optional[int]:
        return int(row[key]) if row.get(key) is not None else None

    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "location_id": _opt_int("location_id"),
        "patient_id": _opt_int("patient_id"),
        "encounter_id": _opt_int("encounter_id"),
        "provider_id": _opt_int("provider_id"),
        "queue_type": row["queue_type"],
        "priority": row["priority"],
        "status": row["status"],
        "assigned_role": row.get("assigned_role"),
        "assigned_user_id": _opt_int("assigned_user_id"),
        "due_at": row.get("due_at"),
        "source": row["source"],
        "payload_json": _parse_json_field(row.get("payload_json")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "completed_at": row.get("completed_at"),
    }


def _serialize_view_preset(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "organization_id": int(row["organization_id"]),
        "role": row["role"],
        "name": row["name"],
        "filters_json": _parse_json_field(row.get("filters_json")),
        "columns_json": _parse_json_field(row.get("columns_json")),
        "is_default": bool(row.get("is_default", False)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


# ============================================================
# Pydantic input models
# ============================================================


class SegmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    segment_type: str = Field(..., min_length=1, max_length=64)
    criteria_json: Optional[Any] = None
    is_active: bool = True


class SegmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    segment_type: Optional[str] = Field(
        default=None, min_length=1, max_length=64
    )
    criteria_json: Optional[Any] = None
    is_active: Optional[bool] = None


class MembershipCreate(BaseModel):
    segment_id: int
    source: str = Field(..., min_length=1, max_length=64)
    reason: Optional[str] = Field(default=None, max_length=2000)


class TagCreate(BaseModel):
    tag: str = Field(..., min_length=1, max_length=64)
    color: Optional[str] = Field(default=None, max_length=32)


class ProblemCreate(BaseModel):
    condition_code: Optional[str] = Field(default=None, max_length=64)
    condition_label: str = Field(..., min_length=1, max_length=255)
    specialty: Optional[str] = Field(default=None, max_length=64)
    eye: Optional[str] = None
    status: str = "active"
    onset_date: Optional[date] = None
    last_reviewed_at: Optional[datetime] = None


class ProblemUpdate(BaseModel):
    condition_code: Optional[str] = Field(default=None, max_length=64)
    condition_label: Optional[str] = Field(
        default=None, min_length=1, max_length=255
    )
    specialty: Optional[str] = Field(default=None, max_length=64)
    eye: Optional[str] = None
    status: Optional[str] = None
    onset_date: Optional[date] = None
    last_reviewed_at: Optional[datetime] = None


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    specialty: Optional[str] = Field(default=None, max_length=64)
    role_owner: str = Field(..., min_length=1, max_length=32)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    specialty: Optional[str] = Field(default=None, max_length=64)
    role_owner: Optional[str] = Field(
        default=None, min_length=1, max_length=32
    )
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class StageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    stage_order: int = Field(..., ge=0)
    role_owner: str = Field(..., min_length=1, max_length=32)
    sla_minutes: Optional[int] = Field(default=None, ge=0)


class StageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    stage_order: Optional[int] = Field(default=None, ge=0)
    role_owner: Optional[str] = Field(
        default=None, min_length=1, max_length=32
    )
    sla_minutes: Optional[int] = Field(default=None, ge=0)


class QueueItemCreate(BaseModel):
    location_id: Optional[int] = None
    patient_id: Optional[int] = None
    encounter_id: Optional[int] = None
    provider_id: Optional[int] = None
    queue_type: str = Field(..., min_length=1, max_length=64)
    priority: str = "normal"
    status: str = "open"
    assigned_role: Optional[str] = Field(default=None, max_length=32)
    assigned_user_id: Optional[int] = None
    due_at: Optional[datetime] = None
    source: str = "manual"
    payload_json: Optional[Any] = None


class QueueItemUpdate(BaseModel):
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_role: Optional[str] = Field(default=None, max_length=32)
    assigned_user_id: Optional[int] = None
    due_at: Optional[datetime] = None
    payload_json: Optional[Any] = None
    completed_at: Optional[datetime] = None


class ViewPresetCreate(BaseModel):
    role: str
    name: str = Field(..., min_length=1, max_length=200)
    filters_json: Optional[Any] = None
    columns_json: Optional[Any] = None
    is_default: bool = False


class ViewPresetUpdate(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    filters_json: Optional[Any] = None
    columns_json: Optional[Any] = None
    is_default: Optional[bool] = None


# ============================================================
# /segments  + /patients/{id}/segments
# ============================================================


@router.get("/segments")
def list_segments(
    response: Response,
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
    q: Optional[str] = Query(default=None, max_length=200),
    segment_type: Optional[str] = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = true")
    if q:
        clauses.append("name LIKE :q")
        params["q"] = f"%{q}%"
    if segment_type:
        clauses.append("segment_type = :st")
        params["st"] = segment_type
    where = " WHERE " + " AND ".join(clauses)
    total_row = fetch_one(
        f"SELECT COUNT(*) AS n FROM patient_segments{where}", params
    )
    total = int(total_row["n"]) if total_row else 0
    rows = fetch_all(
        f"SELECT * FROM patient_segments{where} "
        "ORDER BY id DESC LIMIT :lim OFFSET :off",
        {**params, "lim": limit, "off": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    return [_serialize_segment(r) for r in rows]


@router.post("/segments", status_code=status.HTTP_201_CREATED)
def create_segment(
    payload: SegmentCreate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    criteria_serialized = _validate_json_object(
        payload.criteria_json, field_name="criteria_json"
    )
    # Uniqueness on (organization_id, name) is enforced by the
    # uq_segments_org_name constraint; map IntegrityError to 409.
    try:
        with transaction() as conn:
            seg_id = insert_returning_id(
                conn,
                "patient_segments",
                {
                    "organization_id": caller.organization_id,
                    "name": payload.name,
                    "description": payload.description,
                    "segment_type": payload.segment_type,
                    "criteria_json": criteria_serialized,
                    "is_active": payload.is_active,
                    "created_by_user_id": caller.user_id,
                },
            )
    except Exception as e:
        if "uq_segments_org_name" in str(e) or "UNIQUE" in str(e).upper():
            raise _err(
                "segment_name_conflict",
                "a segment with this name already exists",
                409,
            )
        raise
    _audit(
        request,
        caller,
        event_type="segment_created",
        detail=f"segment_id={seg_id} segment_type={payload.segment_type}",
    )
    row = _resolve_segment(seg_id, caller)
    return _serialize_segment(row)


@router.patch("/segments/{segment_id}")
def update_segment(
    segment_id: int,
    payload: SegmentUpdate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    _resolve_segment(segment_id, caller)
    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.segment_type is not None:
        updates["segment_type"] = payload.segment_type
    if payload.criteria_json is not None:
        updates["criteria_json"] = _validate_json_object(
            payload.criteria_json, field_name="criteria_json"
        )
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates_with_filters = {
        **updates,
        "id": segment_id,
        "org": caller.organization_id,
    }
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                f"UPDATE patient_segments SET {set_clause}, "
                f"updated_at = CURRENT_TIMESTAMP "
                f"WHERE id = :id AND organization_id = :org"
            ),
            updates_with_filters,
        )
    _audit(
        request,
        caller,
        event_type="segment_updated",
        detail=f"segment_id={segment_id} fields={sorted(updates.keys())}",
    )
    row = _resolve_segment(segment_id, caller)
    return _serialize_segment(row)


@router.get("/patients/{patient_id}/segments")
def list_patient_segments(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _resolve_patient(patient_id, caller)
    rows = fetch_all(
        "SELECT m.*, s.name AS segment_name, s.segment_type AS "
        "segment_segment_type "
        "FROM patient_segment_memberships m "
        "JOIN patient_segments s ON s.id = m.segment_id "
        "WHERE m.organization_id = :org AND m.patient_id = :pid "
        "ORDER BY m.id DESC",
        {"org": caller.organization_id, "pid": patient_id},
    )
    return [_serialize_membership(r) for r in rows]


@router.post(
    "/patients/{patient_id}/segments", status_code=status.HTTP_201_CREATED
)
def add_patient_segment(
    patient_id: int,
    payload: MembershipCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    _resolve_segment(payload.segment_id, caller)
    # Idempotent: if membership exists, return existing.
    existing = fetch_one(
        "SELECT * FROM patient_segment_memberships "
        "WHERE organization_id = :org AND patient_id = :pid "
        "AND segment_id = :sid",
        {
            "org": caller.organization_id,
            "pid": patient_id,
            "sid": payload.segment_id,
        },
    )
    if existing:
        return _serialize_membership(dict(existing))
    with transaction() as conn:
        mem_id = insert_returning_id(
            conn,
            "patient_segment_memberships",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient_id,
                "segment_id": payload.segment_id,
                "source": payload.source,
                "reason": payload.reason,
            },
        )
    _audit(
        request,
        caller,
        event_type="segment_membership_added",
        detail=(
            f"membership_id={mem_id} segment_id={payload.segment_id} "
            f"patient_id={patient_id} source={payload.source}"
        ),
    )
    row = fetch_one(
        "SELECT * FROM patient_segment_memberships WHERE id = :id",
        {"id": mem_id},
    )
    return _serialize_membership(dict(row))


@router.delete("/patients/{patient_id}/segments/{segment_id}")
def remove_patient_segment(
    patient_id: int,
    segment_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    _resolve_segment(segment_id, caller)
    row = fetch_one(
        "SELECT id FROM patient_segment_memberships "
        "WHERE organization_id = :org AND patient_id = :pid "
        "AND segment_id = :sid",
        {
            "org": caller.organization_id,
            "pid": patient_id,
            "sid": segment_id,
        },
    )
    if not row:
        raise _err("membership_not_found", "membership not found", 404)
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                "DELETE FROM patient_segment_memberships "
                "WHERE id = :id AND organization_id = :org"
            ),
            {"id": int(row["id"]), "org": caller.organization_id},
        )
    _audit(
        request,
        caller,
        event_type="segment_membership_removed",
        detail=(
            f"membership_id={int(row['id'])} segment_id={segment_id} "
            f"patient_id={patient_id}"
        ),
    )
    return {"removed": True, "membership_id": int(row["id"])}


# ============================================================
# /patients/{id}/tags
# ============================================================


@router.get("/patients/{patient_id}/tags")
def list_patient_tags(
    patient_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _resolve_patient(patient_id, caller)
    rows = fetch_all(
        "SELECT * FROM patient_tags "
        "WHERE organization_id = :org AND patient_id = :pid "
        "ORDER BY tag ASC",
        {"org": caller.organization_id, "pid": patient_id},
    )
    return [_serialize_tag(r) for r in rows]


@router.post(
    "/patients/{patient_id}/tags", status_code=status.HTTP_201_CREATED
)
def add_patient_tag(
    patient_id: int,
    payload: TagCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    # Idempotent on (org, patient, tag).
    existing = fetch_one(
        "SELECT * FROM patient_tags "
        "WHERE organization_id = :org AND patient_id = :pid AND tag = :tag",
        {
            "org": caller.organization_id,
            "pid": patient_id,
            "tag": payload.tag,
        },
    )
    if existing:
        return _serialize_tag(dict(existing))
    with transaction() as conn:
        tag_id = insert_returning_id(
            conn,
            "patient_tags",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient_id,
                "tag": payload.tag,
                "color": payload.color,
                "created_by_user_id": caller.user_id,
            },
        )
    _audit(
        request,
        caller,
        event_type="patient_tag_added",
        detail=f"tag_id={tag_id} patient_id={patient_id}",
    )
    row = _resolve_tag(tag_id, patient_id, caller)
    return _serialize_tag(row)


@router.delete("/patients/{patient_id}/tags/{tag_id}")
def delete_patient_tag(
    patient_id: int,
    tag_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    _resolve_tag(tag_id, patient_id, caller)
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                "DELETE FROM patient_tags "
                "WHERE id = :id AND patient_id = :pid "
                "AND organization_id = :org"
            ),
            {
                "id": tag_id,
                "pid": patient_id,
                "org": caller.organization_id,
            },
        )
    _audit(
        request,
        caller,
        event_type="patient_tag_removed",
        detail=f"tag_id={tag_id} patient_id={patient_id}",
    )
    return {"removed": True, "tag_id": tag_id}


# ============================================================
# /patients/{id}/problem-list
# ============================================================


@router.get("/patients/{patient_id}/problem-list")
def list_problem_list(
    patient_id: int,
    caller: Caller = Depends(require_caller),
    specialty: Optional[str] = Query(default=None, max_length=64),
    item_status: Optional[str] = Query(
        default=None, alias="status", max_length=32
    ),
    eye: Optional[str] = Query(default=None, max_length=2),
) -> list[dict]:
    _resolve_patient(patient_id, caller)
    clauses = ["organization_id = :org", "patient_id = :pid"]
    params: dict[str, Any] = {
        "org": caller.organization_id,
        "pid": patient_id,
    }
    if specialty:
        clauses.append("specialty = :sp")
        params["sp"] = specialty
    if item_status:
        if item_status not in PROBLEM_STATUSES:
            raise _err(
                "invalid_payload",
                f"status must be one of {sorted(PROBLEM_STATUSES)}",
                400,
            )
        clauses.append("status = :st")
        params["st"] = item_status
    if eye:
        if eye not in EYE_VALUES:
            raise _err(
                "invalid_payload",
                f"eye must be one of {sorted(EYE_VALUES)}",
                400,
            )
        clauses.append("eye = :eye")
        params["eye"] = eye
    where = " WHERE " + " AND ".join(clauses)
    rows = fetch_all(
        f"SELECT * FROM patient_problem_list{where} ORDER BY id DESC",
        params,
    )
    return [_serialize_problem(r) for r in rows]


@router.post(
    "/patients/{patient_id}/problem-list",
    status_code=status.HTTP_201_CREATED,
)
def add_problem_item(
    patient_id: int,
    payload: ProblemCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    if payload.status not in PROBLEM_STATUSES:
        raise _err(
            "invalid_payload",
            f"status must be one of {sorted(PROBLEM_STATUSES)}",
            400,
        )
    if payload.eye is not None and payload.eye not in EYE_VALUES:
        raise _err(
            "invalid_payload",
            f"eye must be null or one of {sorted(EYE_VALUES)}",
            400,
        )
    with transaction() as conn:
        item_id = insert_returning_id(
            conn,
            "patient_problem_list",
            {
                "organization_id": caller.organization_id,
                "patient_id": patient_id,
                "condition_code": payload.condition_code,
                "condition_label": payload.condition_label,
                "specialty": payload.specialty,
                "eye": payload.eye,
                "status": payload.status,
                "onset_date": payload.onset_date,
                "last_reviewed_at": payload.last_reviewed_at,
            },
        )
    # Audit detail: METADATA-ONLY. condition_label is intentionally
    # excluded — clinician-authored free-text may shadow PHI.
    _audit(
        request,
        caller,
        event_type="problem_item_added",
        detail=(
            f"item_id={item_id} patient_id={patient_id} "
            f"specialty={payload.specialty} eye={payload.eye} "
            f"status={payload.status}"
        ),
    )
    row = _resolve_problem(item_id, patient_id, caller)
    return _serialize_problem(row)


@router.patch("/patients/{patient_id}/problem-list/{item_id}")
def update_problem_item(
    patient_id: int,
    item_id: int,
    payload: ProblemUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    _resolve_patient(patient_id, caller)
    existing = _resolve_problem(item_id, patient_id, caller)

    updates: dict[str, Any] = {}
    if payload.condition_code is not None:
        updates["condition_code"] = payload.condition_code
    if payload.condition_label is not None:
        updates["condition_label"] = payload.condition_label
    if payload.specialty is not None:
        updates["specialty"] = payload.specialty
    if payload.eye is not None:
        if payload.eye not in EYE_VALUES:
            raise _err(
                "invalid_payload",
                f"eye must be one of {sorted(EYE_VALUES)}",
                400,
            )
        updates["eye"] = payload.eye
    if payload.status is not None:
        if payload.status not in PROBLEM_STATUSES:
            raise _err(
                "invalid_payload",
                f"status must be one of {sorted(PROBLEM_STATUSES)}",
                400,
            )
        updates["status"] = payload.status
    if payload.onset_date is not None:
        updates["onset_date"] = payload.onset_date
    if payload.last_reviewed_at is not None:
        updates["last_reviewed_at"] = payload.last_reviewed_at
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                f"UPDATE patient_problem_list SET {set_clause}, "
                f"updated_at = CURRENT_TIMESTAMP "
                f"WHERE id = :id AND patient_id = :pid "
                f"AND organization_id = :org"
            ),
            {
                **updates,
                "id": item_id,
                "pid": patient_id,
                "org": caller.organization_id,
            },
        )
    _audit(
        request,
        caller,
        event_type="problem_item_updated",
        detail=(
            f"item_id={item_id} patient_id={patient_id} "
            f"fields={sorted(updates.keys())}"
        ),
    )
    row = _resolve_problem(item_id, patient_id, caller)
    return _serialize_problem(row)


# ============================================================
# /workflow-templates  + /workflow-templates/{id}/stages
# ============================================================


@router.get("/workflow-templates")
def list_workflow_templates(
    caller: Caller = Depends(require_caller),
    include_inactive: bool = Query(default=False),
    specialty: Optional[str] = Query(default=None, max_length=64),
    role_owner: Optional[str] = Query(default=None, max_length=32),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if not include_inactive:
        clauses.append("is_active = true")
    if specialty:
        clauses.append("specialty = :sp")
        params["sp"] = specialty
    if role_owner:
        clauses.append("role_owner = :ro")
        params["ro"] = role_owner
    where = " WHERE " + " AND ".join(clauses)
    rows = fetch_all(
        f"SELECT * FROM clinic_workflow_templates{where} "
        "ORDER BY id DESC",
        params,
    )
    return [_serialize_template(r) for r in rows]


@router.post(
    "/workflow-templates", status_code=status.HTTP_201_CREATED
)
def create_workflow_template(
    payload: TemplateCreate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    if payload.role_owner not in WORKFLOW_OWNER_ROLES:
        raise _err(
            "invalid_payload",
            f"role_owner must be one of {sorted(WORKFLOW_OWNER_ROLES)}",
            400,
        )
    try:
        with transaction() as conn:
            tmpl_id = insert_returning_id(
                conn,
                "clinic_workflow_templates",
                {
                    "organization_id": caller.organization_id,
                    "name": payload.name,
                    "specialty": payload.specialty,
                    "role_owner": payload.role_owner,
                    "description": payload.description,
                    "is_active": payload.is_active,
                },
            )
    except Exception as e:
        if "uq_wftmpl_org_name" in str(e) or "UNIQUE" in str(e).upper():
            raise _err(
                "template_name_conflict",
                "a workflow template with this name already exists",
                409,
            )
        raise
    _audit(
        request,
        caller,
        event_type="workflow_template_created",
        detail=(
            f"template_id={tmpl_id} role_owner={payload.role_owner} "
            f"specialty={payload.specialty}"
        ),
    )
    row = _resolve_template(tmpl_id, caller)
    return _serialize_template(row)


@router.patch("/workflow-templates/{template_id}")
def update_workflow_template(
    template_id: int,
    payload: TemplateUpdate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    _resolve_template(template_id, caller)
    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.specialty is not None:
        updates["specialty"] = payload.specialty
    if payload.role_owner is not None:
        if payload.role_owner not in WORKFLOW_OWNER_ROLES:
            raise _err(
                "invalid_payload",
                f"role_owner must be one of {sorted(WORKFLOW_OWNER_ROLES)}",
                400,
            )
        updates["role_owner"] = payload.role_owner
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                f"UPDATE clinic_workflow_templates SET {set_clause}, "
                f"updated_at = CURRENT_TIMESTAMP "
                f"WHERE id = :id AND organization_id = :org"
            ),
            {
                **updates,
                "id": template_id,
                "org": caller.organization_id,
            },
        )
    _audit(
        request,
        caller,
        event_type="workflow_template_updated",
        detail=(
            f"template_id={template_id} fields={sorted(updates.keys())}"
        ),
    )
    row = _resolve_template(template_id, caller)
    return _serialize_template(row)


@router.get("/workflow-templates/{template_id}/stages")
def list_workflow_stages(
    template_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    _resolve_template(template_id, caller)
    rows = fetch_all(
        "SELECT * FROM clinic_workflow_stages "
        "WHERE organization_id = :org AND template_id = :tid "
        "ORDER BY stage_order ASC, id ASC",
        {"org": caller.organization_id, "tid": template_id},
    )
    return [_serialize_stage(r) for r in rows]


@router.post(
    "/workflow-templates/{template_id}/stages",
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_stage(
    template_id: int,
    payload: StageCreate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    _resolve_template(template_id, caller)
    if payload.role_owner not in WORKFLOW_OWNER_ROLES:
        raise _err(
            "invalid_payload",
            f"role_owner must be one of {sorted(WORKFLOW_OWNER_ROLES)}",
            400,
        )
    try:
        with transaction() as conn:
            stage_id = insert_returning_id(
                conn,
                "clinic_workflow_stages",
                {
                    "organization_id": caller.organization_id,
                    "template_id": template_id,
                    "name": payload.name,
                    "stage_order": payload.stage_order,
                    "role_owner": payload.role_owner,
                    "sla_minutes": payload.sla_minutes,
                },
            )
    except Exception as e:
        if (
            "uq_wfstage_org_template_order" in str(e)
            or "UNIQUE" in str(e).upper()
        ):
            raise _err(
                "stage_order_conflict",
                "a stage with this stage_order already exists in this template",
                409,
            )
        raise
    _audit(
        request,
        caller,
        event_type="workflow_stage_created",
        detail=(
            f"stage_id={stage_id} template_id={template_id} "
            f"order={payload.stage_order} role_owner={payload.role_owner}"
        ),
    )
    row = _resolve_stage(stage_id, caller)
    return _serialize_stage(row)


@router.patch("/workflow-stages/{stage_id}")
def update_workflow_stage(
    stage_id: int,
    payload: StageUpdate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    _resolve_stage(stage_id, caller)
    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.stage_order is not None:
        updates["stage_order"] = payload.stage_order
    if payload.role_owner is not None:
        if payload.role_owner not in WORKFLOW_OWNER_ROLES:
            raise _err(
                "invalid_payload",
                f"role_owner must be one of {sorted(WORKFLOW_OWNER_ROLES)}",
                400,
            )
        updates["role_owner"] = payload.role_owner
    if payload.sla_minutes is not None:
        updates["sla_minutes"] = payload.sla_minutes
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    try:
        with transaction() as conn:
            from sqlalchemy import text as _t

            conn.execute(
                _t(
                    f"UPDATE clinic_workflow_stages SET {set_clause} "
                    f"WHERE id = :id AND organization_id = :org"
                ),
                {**updates, "id": stage_id, "org": caller.organization_id},
            )
    except Exception as e:
        if (
            "uq_wfstage_org_template_order" in str(e)
            or "UNIQUE" in str(e).upper()
        ):
            raise _err(
                "stage_order_conflict",
                "a stage with this stage_order already exists in this template",
                409,
            )
        raise
    _audit(
        request,
        caller,
        event_type="workflow_stage_updated",
        detail=f"stage_id={stage_id} fields={sorted(updates.keys())}",
    )
    row = _resolve_stage(stage_id, caller)
    return _serialize_stage(row)


# ============================================================
# /work-queues
# ============================================================


@router.get("/work-queues")
def list_work_queue(
    response: Response,
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
    patient_id: Optional[int] = Query(default=None),
    encounter_id: Optional[int] = Query(default=None),
    provider_id: Optional[int] = Query(default=None),
    queue_type: Optional[str] = Query(default=None, max_length=64),
    priority: Optional[str] = Query(default=None, max_length=32),
    item_status: Optional[str] = Query(
        default=None, alias="status", max_length=32
    ),
    assigned_role: Optional[str] = Query(default=None, max_length=32),
    assigned_user_id: Optional[int] = Query(default=None),
    due_before: Optional[datetime] = Query(default=None),
    due_after: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if location_id is not None:
        clauses.append("location_id = :lid")
        params["lid"] = location_id
    if patient_id is not None:
        clauses.append("patient_id = :pid")
        params["pid"] = patient_id
    if encounter_id is not None:
        clauses.append("encounter_id = :eid")
        params["eid"] = encounter_id
    if provider_id is not None:
        clauses.append("provider_id = :prid")
        params["prid"] = provider_id
    if queue_type is not None:
        clauses.append("queue_type = :qt")
        params["qt"] = queue_type
    if priority is not None:
        if priority not in QUEUE_PRIORITIES:
            raise _err(
                "invalid_payload",
                f"priority must be one of {sorted(QUEUE_PRIORITIES)}",
                400,
            )
        clauses.append("priority = :pr")
        params["pr"] = priority
    if item_status is not None:
        if item_status not in QUEUE_STATUSES:
            raise _err(
                "invalid_payload",
                f"status must be one of {sorted(QUEUE_STATUSES)}",
                400,
            )
        clauses.append("status = :st")
        params["st"] = item_status
    if assigned_role is not None:
        clauses.append("assigned_role = :ar")
        params["ar"] = assigned_role
    if assigned_user_id is not None:
        clauses.append("assigned_user_id = :auid")
        params["auid"] = assigned_user_id
    if due_before is not None:
        clauses.append("due_at <= :db")
        params["db"] = due_before
    if due_after is not None:
        clauses.append("due_at >= :da")
        params["da"] = due_after
    where = " WHERE " + " AND ".join(clauses)
    total_row = fetch_one(
        f"SELECT COUNT(*) AS n FROM work_queue_items{where}", params
    )
    total = int(total_row["n"]) if total_row else 0
    rows = fetch_all(
        f"SELECT * FROM work_queue_items{where} "
        "ORDER BY id DESC LIMIT :lim OFFSET :off",
        {**params, "lim": limit, "off": offset},
    )
    response.headers["X-Total-Count"] = str(total)
    return [_serialize_queue_item(r) for r in rows]


@router.post("/work-queues", status_code=status.HTTP_201_CREATED)
def create_work_queue_item(
    payload: QueueItemCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    if payload.priority not in QUEUE_PRIORITIES:
        raise _err(
            "invalid_payload",
            f"priority must be one of {sorted(QUEUE_PRIORITIES)}",
            400,
        )
    if payload.status not in QUEUE_STATUSES:
        raise _err(
            "invalid_payload",
            f"status must be one of {sorted(QUEUE_STATUSES)}",
            400,
        )
    # Verify all referenced entities live in caller's org. 404 (not 403)
    # on cross-org per the no-existence-leak invariant.
    if payload.location_id is not None:
        _check_org_match(
            "locations", payload.location_id, caller, "location_not_found"
        )
    if payload.patient_id is not None:
        _resolve_patient(payload.patient_id, caller)
    if payload.encounter_id is not None:
        _check_org_match(
            "encounters",
            payload.encounter_id,
            caller,
            "encounter_not_found",
        )
    if payload.provider_id is not None:
        _check_org_match(
            "providers", payload.provider_id, caller, "provider_not_found"
        )
    if payload.assigned_user_id is not None:
        _check_org_match(
            "users",
            payload.assigned_user_id,
            caller,
            "user_not_found",
        )
    payload_serialized = _validate_json_object(
        payload.payload_json, field_name="payload_json", allow_array=True
    )

    completed_at = None
    if payload.status == "completed":
        completed_at = datetime.utcnow()

    with transaction() as conn:
        item_id = insert_returning_id(
            conn,
            "work_queue_items",
            {
                "organization_id": caller.organization_id,
                "location_id": payload.location_id,
                "patient_id": payload.patient_id,
                "encounter_id": payload.encounter_id,
                "provider_id": payload.provider_id,
                "queue_type": payload.queue_type,
                "priority": payload.priority,
                "status": payload.status,
                "assigned_role": payload.assigned_role,
                "assigned_user_id": payload.assigned_user_id,
                "due_at": payload.due_at,
                "source": payload.source,
                "payload_json": payload_serialized,
                "completed_at": completed_at,
            },
        )
    _audit(
        request,
        caller,
        event_type="queue_item_created",
        detail=(
            f"item_id={item_id} queue_type={payload.queue_type} "
            f"priority={payload.priority} status={payload.status}"
        ),
    )
    row = _resolve_queue_item(item_id, caller)
    return _serialize_queue_item(row)


@router.patch("/work-queues/{item_id}")
def update_work_queue_item(
    item_id: int,
    payload: QueueItemUpdate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    _require_write_role(caller, allowed={ROLE_ADMIN, ROLE_CLINICIAN})
    existing = _resolve_queue_item(item_id, caller)
    updates: dict[str, Any] = {}
    if payload.priority is not None:
        if payload.priority not in QUEUE_PRIORITIES:
            raise _err(
                "invalid_payload",
                f"priority must be one of {sorted(QUEUE_PRIORITIES)}",
                400,
            )
        updates["priority"] = payload.priority
    old_status = existing["status"]
    new_status = payload.status if payload.status is not None else old_status
    if payload.status is not None:
        if payload.status not in QUEUE_STATUSES:
            raise _err(
                "invalid_payload",
                f"status must be one of {sorted(QUEUE_STATUSES)}",
                400,
            )
        updates["status"] = payload.status
    if payload.assigned_role is not None:
        updates["assigned_role"] = payload.assigned_role
    if payload.assigned_user_id is not None:
        _check_org_match(
            "users", payload.assigned_user_id, caller, "user_not_found"
        )
        updates["assigned_user_id"] = payload.assigned_user_id
    if payload.due_at is not None:
        updates["due_at"] = payload.due_at
    if payload.payload_json is not None:
        updates["payload_json"] = _validate_json_object(
            payload.payload_json,
            field_name="payload_json",
            allow_array=True,
        )
    if payload.completed_at is not None:
        updates["completed_at"] = payload.completed_at
    # Auto-stamp completed_at when transitioning to completed.
    if (
        new_status == "completed"
        and old_status != "completed"
        and "completed_at" not in updates
    ):
        updates["completed_at"] = datetime.utcnow()
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with transaction() as conn:
        from sqlalchemy import text as _t

        conn.execute(
            _t(
                f"UPDATE work_queue_items SET {set_clause}, "
                f"updated_at = CURRENT_TIMESTAMP "
                f"WHERE id = :id AND organization_id = :org"
            ),
            {**updates, "id": item_id, "org": caller.organization_id},
        )
    _audit(
        request,
        caller,
        event_type="queue_item_updated",
        detail=(
            f"item_id={item_id} old_status={old_status} "
            f"new_status={new_status} fields={sorted(updates.keys())}"
        ),
    )
    row = _resolve_queue_item(item_id, caller)
    return _serialize_queue_item(row)


# ============================================================
# /role-views
# ============================================================


@router.get("/role-views")
def list_role_views(
    caller: Caller = Depends(require_caller),
    role: Optional[str] = Query(default=None, max_length=32),
    include_non_default: bool = Query(default=True),
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": caller.organization_id}
    if role is not None:
        if role not in VIEW_PRESET_ROLES:
            raise _err(
                "invalid_payload",
                f"role must be one of {sorted(VIEW_PRESET_ROLES)}",
                400,
            )
        clauses.append("role = :ro")
        params["ro"] = role
    if not include_non_default:
        clauses.append("is_default = true")
    where = " WHERE " + " AND ".join(clauses)
    rows = fetch_all(
        f"SELECT * FROM role_view_presets{where} "
        "ORDER BY role ASC, is_default DESC, id ASC",
        params,
    )
    return [_serialize_view_preset(r) for r in rows]


@router.post("/role-views", status_code=status.HTTP_201_CREATED)
def create_role_view(
    payload: ViewPresetCreate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    if payload.role not in VIEW_PRESET_ROLES:
        raise _err(
            "invalid_payload",
            f"role must be one of {sorted(VIEW_PRESET_ROLES)}",
            400,
        )
    filters_serialized = _validate_json_object(
        payload.filters_json, field_name="filters_json", allow_array=True
    )
    columns_serialized = _validate_json_object(
        payload.columns_json, field_name="columns_json", allow_array=True
    )

    try:
        with transaction() as conn:
            from sqlalchemy import text as _t

            # If is_default=true, unset other defaults for same (org, role).
            if payload.is_default:
                conn.execute(
                    _t(
                        "UPDATE role_view_presets SET is_default = false "
                        "WHERE organization_id = :org AND role = :ro "
                        "AND is_default = true"
                    ),
                    {"org": caller.organization_id, "ro": payload.role},
                )
            preset_id = insert_returning_id(
                conn,
                "role_view_presets",
                {
                    "organization_id": caller.organization_id,
                    "role": payload.role,
                    "name": payload.name,
                    "filters_json": filters_serialized,
                    "columns_json": columns_serialized,
                    "is_default": payload.is_default,
                },
            )
    except Exception as e:
        if "uq_rvp_org_role_name" in str(e) or "UNIQUE" in str(e).upper():
            raise _err(
                "preset_name_conflict",
                "a role view preset with this name already exists for the role",
                409,
            )
        raise
    _audit(
        request,
        caller,
        event_type="role_view_created",
        detail=(
            f"preset_id={preset_id} role={payload.role} "
            f"is_default={payload.is_default}"
        ),
    )
    row = _resolve_view_preset(preset_id, caller)
    return _serialize_view_preset(row)


@router.patch("/role-views/{preset_id}")
def update_role_view(
    preset_id: int,
    payload: ViewPresetUpdate,
    request: Request,
    caller: Caller = Depends(require_admin),
) -> dict:
    existing = _resolve_view_preset(preset_id, caller)
    updates: dict[str, Any] = {}
    if payload.role is not None:
        if payload.role not in VIEW_PRESET_ROLES:
            raise _err(
                "invalid_payload",
                f"role must be one of {sorted(VIEW_PRESET_ROLES)}",
                400,
            )
        updates["role"] = payload.role
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.filters_json is not None:
        updates["filters_json"] = _validate_json_object(
            payload.filters_json,
            field_name="filters_json",
            allow_array=True,
        )
    if payload.columns_json is not None:
        updates["columns_json"] = _validate_json_object(
            payload.columns_json,
            field_name="columns_json",
            allow_array=True,
        )
    if payload.is_default is not None:
        updates["is_default"] = payload.is_default
    if not updates:
        raise _err("invalid_payload", "no updatable fields supplied", 400)
    target_role = updates.get("role", existing["role"])
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with transaction() as conn:
        from sqlalchemy import text as _t

        # If we're setting is_default=true, unset siblings first.
        if updates.get("is_default") is True:
            conn.execute(
                _t(
                    "UPDATE role_view_presets SET is_default = false "
                    "WHERE organization_id = :org AND role = :ro "
                    "AND id != :id AND is_default = true"
                ),
                {
                    "org": caller.organization_id,
                    "ro": target_role,
                    "id": preset_id,
                },
            )
        conn.execute(
            _t(
                f"UPDATE role_view_presets SET {set_clause}, "
                f"updated_at = CURRENT_TIMESTAMP "
                f"WHERE id = :id AND organization_id = :org"
            ),
            {**updates, "id": preset_id, "org": caller.organization_id},
        )
    _audit(
        request,
        caller,
        event_type="role_view_updated",
        detail=(
            f"preset_id={preset_id} fields={sorted(updates.keys())}"
        ),
    )
    row = _resolve_view_preset(preset_id, caller)
    return _serialize_view_preset(row)
