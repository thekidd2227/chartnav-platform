"""Phase 20C — Role-based clinic-dashboard endpoints.

Read-only summary endpoints that aggregate Phase 20B's
``work_queue_items`` + (optionally) the existing ``note_versions``
state into role-specific cards for five clinic operating roles:

  * /dashboards/front-desk  — schedule / check-in / checkout
  * /dashboards/technician  — workup / VA-IOP-refraction /
                               dilation / testing / imaging-needed
  * /dashboards/doctor      — MD command center
  * /dashboards/reviewer    — provider-reviewed AI / workflow safety
  * /dashboards/admin       — operational summary
  * /dashboards/me          — dispatches to the caller's own
                               role's dashboard

Org isolation: every aggregate query filters by
``caller.organization_id``. No cross-org rows ever appear.

RBAC summary: each role can read its own dashboard. The ``admin``
role can read every role's dashboard. Cross-role reads (e.g.,
clinician calling /dashboards/admin) return 403
``role_dashboard_forbidden``.

Audit posture: dashboard reads are NOT individually audited.
They aggregate row counts already protected by the per-resource
audit trail; auditing every paint of a 60-times-a-day dashboard
would flood the audit log without adding evidence value. Drill-
down clicks land on the underlying Phase 20B endpoints which DO
audit metadata-only.

PHI posture: every queue item rendered uses the compact
serializer (``_compact_queue_item``) which includes IDs +
status + queue_type + role + due/created/updated timestamps —
**never** ``payload_json`` body, ``condition_label``, or any
clinical text. Dashboards are operational rollups, not clinical
chart surfaces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import Caller, require_caller
from app.authz import (
    DASHBOARD_ROLES,
    ROLE_ADMIN,
    ROLE_CLINICIAN,
    ROLE_FRONT_DESK,
    ROLE_REVIEWER,
    ROLE_TECHNICIAN,
    forbidden,
)
from app.db import fetch_all, fetch_one


router = APIRouter(tags=["phase-20c-role-dashboards"])


# ============================================================
# Queue type taxonomies — operational lane vocabulary the Phase
# 20A role-workflows plan named. Stored as constants here so a
# single source of truth governs every lane mapping.
# ============================================================

# Front-desk lane queue types (schedule / check-in / checkout /
# follow-up / scheduling).
_FRONT_DESK_QUEUE_TYPES: tuple[str, ...] = (
    "check_in",
    "demographics_review",
    "ready_for_workup",
    "checkout",
    "follow_up",
    "scheduling",
)

# Technician lane queue types (workup / testing / imaging needed /
# ready-for-doctor handoff).
_TECHNICIAN_QUEUE_TYPES: tuple[str, ...] = (
    "technician_workup",
    "va_iop_refraction",
    "dilation",
    "imaging_needed",
    "visual_field_needed",
    "ready_for_doctor",
)

# Doctor / clinician command-center queue types.
_DOCTOR_QUEUE_TYPES: tuple[str, ...] = (
    "ready_for_doctor",
    "provider_review",
    "documentation",
    "signoff_needed",
    "high_priority_clinical",
    "imaging_review",
)

# Reviewer queue types (note review, AI draft review, audit
# exceptions, blocked items).
_REVIEWER_QUEUE_TYPES: tuple[str, ...] = (
    "note_review",
    "diagram_review",
    "ai_draft_review",
    "audit_exception",
    "blocked_review",
)

# Statuses that indicate "still in flight" — counted in lane
# rollups. completed + dismissed are excluded by default.
_OPEN_STATUSES: tuple[str, ...] = ("open", "in_progress", "blocked")
_TERMINAL_STATUSES: tuple[str, ...] = ("completed", "dismissed")
_HIGH_PRIORITY_VALUES: tuple[str, ...] = ("high", "urgent")


# ============================================================
# Compact serializer — strips PHI surface area
# ============================================================


def _compact_queue_item(row: dict) -> dict:
    """Serialize a ``work_queue_items`` row for dashboard display.

    Whitelist-only — callers should use the per-resource
    ``/work-queues/{id}`` Phase 20B endpoint when they need the
    full row including ``payload_json``. The dashboard view
    intentionally does NOT include payload body.
    """
    def _opt_int(key: str) -> Optional[int]:
        return int(row[key]) if row.get(key) is not None else None

    return {
        "id": int(row["id"]),
        "queue_type": row["queue_type"],
        "priority": row["priority"],
        "status": row["status"],
        "assigned_role": row.get("assigned_role"),
        "assigned_user_id": _opt_int("assigned_user_id"),
        "patient_id": _opt_int("patient_id"),
        "encounter_id": _opt_int("encounter_id"),
        "provider_id": _opt_int("provider_id"),
        "location_id": _opt_int("location_id"),
        "due_at": row.get("due_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


# ============================================================
# Aggregation helpers
# ============================================================


def _count_open(
    org_id: int,
    *,
    queue_types: Optional[tuple[str, ...]] = None,
    priority: Optional[str] = None,
    location_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    assigned_user_id: Optional[int] = None,
) -> int:
    """Count work-queue rows in caller's org matching the filters."""
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": org_id}
    placeholders = []
    for status in _OPEN_STATUSES:
        params[f"st_{status}"] = status
        placeholders.append(f":st_{status}")
    clauses.append(f"status IN ({', '.join(placeholders)})")
    if queue_types:
        qt_placeholders = []
        for i, qt in enumerate(queue_types):
            params[f"qt_{i}"] = qt
            qt_placeholders.append(f":qt_{i}")
        clauses.append(f"queue_type IN ({', '.join(qt_placeholders)})")
    if priority is not None:
        clauses.append("priority = :pr")
        params["pr"] = priority
    if location_id is not None:
        clauses.append("location_id = :loc")
        params["loc"] = location_id
    if provider_id is not None:
        clauses.append("provider_id = :prov")
        params["prov"] = provider_id
    if assigned_user_id is not None:
        clauses.append("assigned_user_id = :auid")
        params["auid"] = assigned_user_id
    sql = (
        "SELECT COUNT(*) AS n FROM work_queue_items WHERE "
        + " AND ".join(clauses)
    )
    row = fetch_one(sql, params)
    return int(row["n"]) if row else 0


def _list_recent(
    org_id: int,
    *,
    queue_types: Optional[tuple[str, ...]] = None,
    statuses: tuple[str, ...] = _OPEN_STATUSES,
    priority: Optional[str] = None,
    location_id: Optional[int] = None,
    assigned_user_id: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    clauses = ["organization_id = :org"]
    params: dict[str, Any] = {"org": org_id, "lim": limit}
    placeholders = []
    for i, st in enumerate(statuses):
        params[f"st_{i}"] = st
        placeholders.append(f":st_{i}")
    clauses.append(f"status IN ({', '.join(placeholders)})")
    if queue_types:
        qt_placeholders = []
        for i, qt in enumerate(queue_types):
            params[f"qt_{i}"] = qt
            qt_placeholders.append(f":qt_{i}")
        clauses.append(f"queue_type IN ({', '.join(qt_placeholders)})")
    if priority is not None:
        clauses.append("priority = :pr")
        params["pr"] = priority
    if location_id is not None:
        clauses.append("location_id = :loc")
        params["loc"] = location_id
    if assigned_user_id is not None:
        clauses.append("assigned_user_id = :auid")
        params["auid"] = assigned_user_id
    sql = (
        "SELECT * FROM work_queue_items WHERE "
        + " AND ".join(clauses)
        + " ORDER BY "
        # urgent > high > normal > low — naive ordering by string
        # would put low first; an explicit CASE keeps the
        # buyer-facing order consistent.
        + "CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 "
        + "WHEN 'normal' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, "
        + "due_at IS NULL, due_at ASC, id DESC "
        + "LIMIT :lim"
    )
    rows = fetch_all(sql, params)
    return [_compact_queue_item(r) for r in rows]


def _summary_by(
    org_id: int, column: str
) -> dict[str, int]:
    """Group-by-column count of all work_queue_items in caller org.

    ``column`` MUST be one of {status, priority, queue_type,
    assigned_role} — controlled by callers, not by user input.
    """
    sql = (
        f"SELECT {column} AS k, COUNT(*) AS n FROM work_queue_items "
        "WHERE organization_id = :org GROUP BY k ORDER BY n DESC"
    )
    rows = fetch_all(sql, {"org": org_id})
    return {(r["k"] or "_null"): int(r["n"]) for r in rows}


def _count_overdue(org_id: int) -> int:
    """Count open/in-progress queue items past their due_at.

    Pass ``datetime`` (not a pre-serialized ISO string) so
    SQLAlchemy uses the column's native binding for the
    comparison — string-based ISO comparisons can drift across
    timezone-suffix variants in SQLite text storage.
    """
    now = datetime.now(timezone.utc)
    sql = (
        "SELECT COUNT(*) AS n FROM work_queue_items "
        "WHERE organization_id = :org "
        "AND status IN ('open', 'in_progress') "
        "AND due_at IS NOT NULL AND due_at < :now"
    )
    row = fetch_one(sql, {"org": org_id, "now": now})
    return int(row["n"]) if row else 0


def _count_unsigned_notes(org_id: int) -> int:
    """Count note_versions still awaiting provider sign-off.

    The ``note_versions`` schema uses ``draft_status`` (not
    ``status``); values are draft | provider_review | revised |
    signed | exported. "Unsigned" means anything pre-``signed``.
    """
    sql = (
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.draft_status IN ('draft', 'provider_review', 'revised')"
    )
    row = fetch_one(sql, {"org": org_id})
    return int(row["n"]) if row else 0


# ============================================================
# RBAC helper — admin can view any role's dashboard via ?role=
# ============================================================


def _resolve_dashboard_role(
    caller: Caller, *, requested_role: str
) -> str:
    """Return the role whose dashboard the caller is allowed to view.

    Non-admins may only view their own role's dashboard. Admin can
    view any DASHBOARD_ROLES dashboard.
    """
    if requested_role not in DASHBOARD_ROLES:
        raise forbidden(
            "role_dashboard_unknown",
            f"unknown dashboard role '{requested_role}'; "
            f"allowed: {sorted(DASHBOARD_ROLES)}",
        )
    if caller.role == ROLE_ADMIN:
        return requested_role
    if caller.role != requested_role:
        raise forbidden(
            "role_dashboard_forbidden",
            f"caller role '{caller.role}' cannot view '{requested_role}' "
            "dashboard",
        )
    return caller.role


# ============================================================
# /dashboards/front-desk
# ============================================================


@router.get("/dashboards/front-desk")
def front_desk_dashboard(
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
    role: Optional[str] = Query(default=None, max_length=32),
) -> dict:
    requested = role or ROLE_FRONT_DESK
    _resolve_dashboard_role(caller, requested_role=requested)
    org = caller.organization_id

    return {
        "role": ROLE_FRONT_DESK,
        "scope": {"organization_id": org, "location_id": location_id},
        "counts": {
            "today_queue_count": _count_open(
                org, queue_types=_FRONT_DESK_QUEUE_TYPES,
                location_id=location_id,
            ),
            "check_in_pending_count": _count_open(
                org, queue_types=("check_in",), location_id=location_id
            ),
            "ready_for_workup_count": _count_open(
                org, queue_types=("ready_for_workup",),
                location_id=location_id,
            ),
            "checkout_pending_count": _count_open(
                org, queue_types=("checkout",), location_id=location_id
            ),
            "follow_up_needed_count": _count_open(
                org, queue_types=("follow_up", "scheduling"),
                location_id=location_id,
            ),
        },
        "recent_or_due_items": _list_recent(
            org, queue_types=_FRONT_DESK_QUEUE_TYPES,
            location_id=location_id,
        ),
    }


# ============================================================
# /dashboards/technician
# ============================================================


@router.get("/dashboards/technician")
def technician_dashboard(
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
    role: Optional[str] = Query(default=None, max_length=32),
) -> dict:
    requested = role or ROLE_TECHNICIAN
    _resolve_dashboard_role(caller, requested_role=requested)
    org = caller.organization_id

    return {
        "role": ROLE_TECHNICIAN,
        "scope": {"organization_id": org, "location_id": location_id},
        "counts": {
            "workup_pending_count": _count_open(
                org,
                queue_types=("technician_workup", "va_iop_refraction"),
                location_id=location_id,
            ),
            "imaging_needed_count": _count_open(
                org, queue_types=("imaging_needed",),
                location_id=location_id,
            ),
            "dilation_pending_count": _count_open(
                org, queue_types=("dilation",), location_id=location_id
            ),
            "testing_pending_count": _count_open(
                org, queue_types=("visual_field_needed",),
                location_id=location_id,
            ),
            "ready_for_doctor_count": _count_open(
                org, queue_types=("ready_for_doctor",),
                location_id=location_id,
            ),
        },
        "assigned_items": _list_recent(
            org,
            queue_types=_TECHNICIAN_QUEUE_TYPES,
            assigned_user_id=caller.user_id,
            location_id=location_id,
        ),
    }


# ============================================================
# /dashboards/doctor
# ============================================================


@router.get("/dashboards/doctor")
def doctor_dashboard(
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
    provider_id: Optional[int] = Query(default=None),
    role: Optional[str] = Query(default=None, max_length=32),
) -> dict:
    requested = role or ROLE_CLINICIAN
    _resolve_dashboard_role(caller, requested_role=requested)
    org = caller.organization_id

    return {
        "role": ROLE_CLINICIAN,
        "scope": {
            "organization_id": org,
            "location_id": location_id,
            "provider_id": provider_id,
        },
        "counts": {
            "ready_for_doctor_count": _count_open(
                org, queue_types=("ready_for_doctor",),
                location_id=location_id, provider_id=provider_id,
            ),
            "documentation_in_progress_count": _count_open(
                org, queue_types=("documentation",),
                location_id=location_id, provider_id=provider_id,
            ),
            "notes_ready_for_signoff_count": _count_open(
                org, queue_types=("signoff_needed",),
                location_id=location_id, provider_id=provider_id,
            ),
            "high_priority_items_count": (
                _count_open(
                    org, queue_types=_DOCTOR_QUEUE_TYPES,
                    priority="urgent",
                    location_id=location_id, provider_id=provider_id,
                )
                + _count_open(
                    org, queue_types=_DOCTOR_QUEUE_TYPES,
                    priority="high",
                    location_id=location_id, provider_id=provider_id,
                )
            ),
            "imaging_ready_for_review_count": _count_open(
                org, queue_types=("imaging_review",),
                location_id=location_id, provider_id=provider_id,
            ),
        },
        "assigned_provider_items": _list_recent(
            org,
            queue_types=_DOCTOR_QUEUE_TYPES,
            assigned_user_id=caller.user_id,
            location_id=location_id,
        ),
    }


# ============================================================
# /dashboards/reviewer
# ============================================================


@router.get("/dashboards/reviewer")
def reviewer_dashboard(
    caller: Caller = Depends(require_caller),
    role: Optional[str] = Query(default=None, max_length=32),
) -> dict:
    requested = role or ROLE_REVIEWER
    _resolve_dashboard_role(caller, requested_role=requested)
    org = caller.organization_id

    return {
        "role": ROLE_REVIEWER,
        "scope": {"organization_id": org},
        "counts": {
            "notes_awaiting_review_count": _count_open(
                org, queue_types=("note_review",)
            ),
            "diagram_proposals_review_count": _count_open(
                org, queue_types=("diagram_review",)
            ),
            "ai_draft_review_count": _count_open(
                org, queue_types=("ai_draft_review",)
            ),
            "audit_exceptions_count": _count_open(
                org, queue_types=("audit_exception",)
            ),
            "blocked_items_count": _count_open(
                org, queue_types=("blocked_review",)
            ),
        },
        "review_needed_items": _list_recent(
            org, queue_types=_REVIEWER_QUEUE_TYPES
        ),
    }


# ============================================================
# /dashboards/admin
# ============================================================


@router.get("/dashboards/admin")
def admin_dashboard(
    caller: Caller = Depends(require_caller),
    role: Optional[str] = Query(default=None, max_length=32),
) -> dict:
    # Admin dashboard is admin-only by design (cross-role aggregates
    # over the full org). _resolve_dashboard_role enforces this.
    requested = role or ROLE_ADMIN
    _resolve_dashboard_role(caller, requested_role=requested)
    org = caller.organization_id

    by_status = _summary_by(org, "status")
    by_priority = _summary_by(org, "priority")
    by_role = _summary_by(org, "assigned_role")
    by_queue_type = _summary_by(org, "queue_type")

    total_open = sum(by_status.get(s, 0) for s in _OPEN_STATUSES)

    # Role-view-presets summary — admin cares about how many saved
    # views per role (Phase 20B drives this; reading it here gives
    # admin a quick "who has a default preset?" view).
    rvp_rows = fetch_all(
        "SELECT role, COUNT(*) AS n FROM role_view_presets "
        "WHERE organization_id = :org GROUP BY role",
        {"org": org},
    )
    role_view_presets_summary = {r["role"]: int(r["n"]) for r in rvp_rows}

    # Location + provider snapshots — basic counts only (Phase 22
    # adds proper multi-clinic aggregates).
    location_summary = {
        "active_count": int(
            (
                fetch_one(
                    "SELECT COUNT(*) AS n FROM locations "
                    "WHERE organization_id = :org AND is_active = 1",
                    {"org": org},
                )
                or {"n": 0}
            )["n"]
        ),
    }
    provider_summary = {
        "total_count": int(
            (
                fetch_one(
                    "SELECT COUNT(*) AS n FROM providers "
                    "WHERE organization_id = :org",
                    {"org": org},
                )
                or {"n": 0}
            )["n"]
        ),
    }

    return {
        "role": ROLE_ADMIN,
        "scope": {"organization_id": org},
        "counts": {
            "total_open_queue_items": total_open,
            "overdue_queue_items": _count_overdue(org),
            "unsigned_notes_count": _count_unsigned_notes(org),
        },
        "work_queue_by_status": by_status,
        "work_queue_by_priority": by_priority,
        "work_queue_by_role": by_role,
        "work_queue_by_queue_type": by_queue_type,
        "location_summary": location_summary,
        "provider_summary": provider_summary,
        "role_view_presets_summary": role_view_presets_summary,
    }


# ============================================================
# /dashboards/me — dispatches to caller's own role
# ============================================================


@router.get("/dashboards/me")
def my_dashboard(
    caller: Caller = Depends(require_caller),
    location_id: Optional[int] = Query(default=None),
    provider_id: Optional[int] = Query(default=None),
) -> dict:
    # Explicit role=None on every dispatch — calling a FastAPI
    # route handler directly from Python (rather than via HTTP)
    # leaves Query(...) defaults as Query objects rather than
    # None, which would short-circuit the "role or DEFAULT"
    # fallback inside each handler.
    if caller.role == ROLE_ADMIN:
        return admin_dashboard(caller=caller, role=None)
    if caller.role == ROLE_CLINICIAN:
        return doctor_dashboard(
            caller=caller,
            location_id=location_id,
            provider_id=provider_id,
            role=None,
        )
    if caller.role == ROLE_REVIEWER:
        return reviewer_dashboard(caller=caller, role=None)
    if caller.role == ROLE_FRONT_DESK:
        return front_desk_dashboard(
            caller=caller, location_id=location_id, role=None
        )
    if caller.role == ROLE_TECHNICIAN:
        return technician_dashboard(
            caller=caller, location_id=location_id, role=None
        )
    raise forbidden(
        "role_dashboard_unknown",
        f"caller role '{caller.role}' has no dashboard",
    )
