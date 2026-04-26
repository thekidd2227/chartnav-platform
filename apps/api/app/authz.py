"""Authorization (RBAC) for ChartNav.

Authentication (who is the caller) lives in `app.auth`. This module is
strictly *authorization*: given a resolved `Caller`, is this action
allowed?

Design goals:
  - Roles and rules are declared once, centrally, with no magic strings
    scattered through route handlers.
  - Every route protection is a small FastAPI dependency.
  - Errors are standardized JSON with a stable `error_code` so clients
    can branch on them.

Roles (must match `users.role`):
  - admin       — full in-org read/write + org metadata management
  - clinician   — charting-side of the state machine; can create/read/append
  - reviewer    — review-side of the state machine; read-only on create/append
  - front_desk  — scheduling-side: create/reschedule encounters, edit patient
                  display fields, drive the scheduled→in_progress transition.
                  CANNOT see transcripts, sign notes, or export audit.
"""

from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException

from app.auth import Caller, require_caller

# -- roles ----------------------------------------------------------------

ROLE_ADMIN = "admin"
ROLE_CLINICIAN = "clinician"
ROLE_REVIEWER = "reviewer"
ROLE_FRONT_DESK = "front_desk"
# Phase A item 2 — RBAC role expansion
# Spec: docs/chartnav/closure/PHASE_A_RBAC_and_Audit_Trail_Spec.md
#   technician     — pre-charts vitals/workup; cannot sign or export
#   biller_coder   — reviews CPT/ICD picks and exports the handoff bundle
ROLE_TECHNICIAN = "technician"
ROLE_BILLER_CODER = "biller_coder"

KNOWN_ROLES: set[str] = {
    ROLE_ADMIN,
    ROLE_CLINICIAN,
    ROLE_REVIEWER,
    ROLE_FRONT_DESK,
    ROLE_TECHNICIAN,
    ROLE_BILLER_CODER,
}

# -- permission surface ---------------------------------------------------
#
# READ surface — who can see what:
#   admin, clinician, reviewer, front_desk  →  encounters, events, org metadata
#   Front desk is specifically DENIED on transcript / findings / note
#   content; those routes opt in by calling `require_clinical_content`.
#
# WRITE surface — who can mutate what:
CAN_CREATE_ENCOUNTER: set[str] = {
    ROLE_ADMIN, ROLE_CLINICIAN, ROLE_FRONT_DESK, ROLE_TECHNICIAN,
}
CAN_CREATE_EVENT: set[str] = {ROLE_ADMIN, ROLE_CLINICIAN}

# Phase A item 2 — coarse-grained capability sets per the spec matrix.
# Fine-grained per-field rules are intentionally deferred (Phase B);
# these are the route-gate primitives the spec acceptance criteria
# require.
CAN_CHART_VITALS: set[str] = {
    # Tech and clinician chart VA / IOP / pre-workup. Admin can chart
    # for support continuity. Front desk cannot.
    ROLE_ADMIN, ROLE_CLINICIAN, ROLE_TECHNICIAN,
}
CAN_CHART_ASSESSMENT: set[str] = {
    # Assessment + plan are clinician/admin only.
    ROLE_ADMIN, ROLE_CLINICIAN,
}
CAN_SIGN: set[str] = {
    # Sign is the author's responsibility; admin retained for break-glass.
    ROLE_ADMIN, ROLE_CLINICIAN,
}
CAN_EXPORT_HANDOFF: set[str] = {
    # Biller exports the PM/RCM handoff bundle (Phase A item 4).
    # Clinicians and admins can export too.
    ROLE_ADMIN, ROLE_CLINICIAN, ROLE_BILLER_CODER,
}
CAN_EDIT_CODES: set[str] = {
    # CPT/ICD picks editable by clinician pre-sign + biller pre-export
    # + admin always. Tech and front desk are excluded.
    ROLE_ADMIN, ROLE_CLINICIAN, ROLE_BILLER_CODER,
}

# Roles that may read raw clinical content (transcripts, findings,
# drafts, signed notes). Front desk is excluded on purpose — they are
# operational, not clinical. Technician reads workup-relevant content
# only; the Phase A spec keeps the read surface coarse and gates
# section-level write paths via CAN_CHART_VITALS / CAN_CHART_ASSESSMENT.
CAN_READ_CLINICAL_CONTENT: set[str] = {
    ROLE_ADMIN, ROLE_CLINICIAN, ROLE_REVIEWER, ROLE_TECHNICIAN, ROLE_BILLER_CODER,
}

# Per-transition authorization map. Keys are (from_status, to_status)
# tuples. Values are the set of roles allowed to perform that edge.
# Admin can perform any valid edge; clinicians, reviewers, technicians,
# and front desk are partitioned by operational vs review vs scheduling.
TRANSITION_ROLES: dict[tuple[str, str], set[str]] = {
    # Front desk + tech can move a scheduled encounter into the
    # in-progress lane (front desk on check-in, tech when starting workup).
    ("scheduled", "in_progress"):      {ROLE_ADMIN, ROLE_CLINICIAN, ROLE_FRONT_DESK, ROLE_TECHNICIAN},
    ("in_progress", "draft_ready"):    {ROLE_ADMIN, ROLE_CLINICIAN},
    ("draft_ready", "in_progress"):    {ROLE_ADMIN, ROLE_CLINICIAN},  # rework back to charting
    ("draft_ready", "review_needed"):  {ROLE_ADMIN, ROLE_REVIEWER},
    ("review_needed", "draft_ready"):  {ROLE_ADMIN, ROLE_REVIEWER},   # kick back
    ("review_needed", "completed"):    {ROLE_ADMIN, ROLE_REVIEWER},
}


# -- error helpers --------------------------------------------------------

def forbidden(error_code: str, reason: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"error_code": error_code, "reason": reason},
    )


# -- dependencies ---------------------------------------------------------

def require_roles(*roles: str):
    """FastAPI dependency: allow only callers whose role is in `roles`."""
    allowed: set[str] = set(roles)

    def _dep(caller: Caller = Depends(require_caller)) -> Caller:
        if caller.role not in allowed:
            raise forbidden(
                "role_forbidden",
                f"role '{caller.role}' is not permitted; requires one of {sorted(allowed)}",
            )
        return caller

    return _dep


def require_admin(caller: Caller = Depends(require_caller)) -> Caller:
    """Admin-only actions (metadata management)."""
    if caller.role != ROLE_ADMIN:
        raise forbidden(
            "role_admin_required",
            f"role '{caller.role}' is not permitted; requires 'admin'",
        )
    return caller


def require_admin_or_clinician_lead(
    caller: Caller = Depends(require_caller),
) -> Caller:
    """Phase 2 item 2 — Admin Dashboard.

    Spec: PHASE_B_Admin_Dashboard_and_Operational_Metrics.md §3.

    Allows `admin` callers and `clinician AND is_lead = True`. All
    other roles (reviewer, front_desk, technician, biller_coder,
    general clinician) are forbidden with the dashboard-specific
    error code so frontends can render the documented "not
    available for your role" empty state.
    """
    if caller.role == ROLE_ADMIN:
        return caller
    if caller.role == ROLE_CLINICIAN and getattr(caller, "is_lead", False):
        return caller
    raise forbidden(
        "role_cannot_view_admin_dashboard",
        f"role '{caller.role}' is not permitted; admin or clinician-lead required",
    )


def require_create_encounter(caller: Caller = Depends(require_caller)) -> Caller:
    if caller.role not in CAN_CREATE_ENCOUNTER:
        raise forbidden(
            "role_cannot_create_encounter",
            f"role '{caller.role}' may not create encounters",
        )
    return caller


def require_create_event(caller: Caller = Depends(require_caller)) -> Caller:
    if caller.role not in CAN_CREATE_EVENT:
        raise forbidden(
            "role_cannot_create_event",
            f"role '{caller.role}' may not create workflow events",
        )
    return caller


def require_clinical_content(caller: Caller = Depends(require_caller)) -> Caller:
    """Gate routes that expose raw clinical content.

    Transcripts, extracted findings, note_version bodies, and signed
    artifacts are only for admin / clinician / reviewer. Front desk
    callers hit 403 `role_cannot_read_clinical` so the UI can hide
    those tiers and the backend stays the source of truth.
    """
    if caller.role not in CAN_READ_CLINICAL_CONTENT:
        raise forbidden(
            "role_cannot_read_clinical",
            f"role '{caller.role}' may not read clinical content",
        )
    return caller


def assert_can_transition(caller: Caller, from_status: str, to_status: str) -> None:
    """Raise 403 if the caller's role may not drive this transition.

    Note: this does NOT validate whether the transition itself is permitted
    by the state machine — that is the route's job (400 invalid_transition).
    """
    allowed = TRANSITION_ROLES.get((from_status, to_status))
    if allowed is None:
        # No role map entry for this edge. Admin may still pass; everyone
        # else hits this as a safety net so unknown edges never silently
        # escalate.
        if caller.role == ROLE_ADMIN:
            return
        raise forbidden(
            "role_cannot_transition",
            f"role '{caller.role}' may not perform transition "
            f"{from_status} -> {to_status}",
        )
    if caller.role not in allowed:
        raise forbidden(
            "role_cannot_transition",
            f"role '{caller.role}' may not perform transition "
            f"{from_status} -> {to_status}; allowed roles: {sorted(allowed)}",
        )
