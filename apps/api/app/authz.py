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

KNOWN_ROLES: set[str] = {
    ROLE_ADMIN,
    ROLE_CLINICIAN,
    ROLE_REVIEWER,
    ROLE_FRONT_DESK,
}

# -- permission surface ---------------------------------------------------
#
# READ surface — who can see what:
#   admin, clinician, reviewer, front_desk  →  encounters, events, org metadata
#   Front desk is specifically DENIED on transcript / findings / note
#   content; those routes opt in by calling `require_clinical_content`.
#
# WRITE surface — who can mutate what:
CAN_CREATE_ENCOUNTER: set[str] = {ROLE_ADMIN, ROLE_CLINICIAN, ROLE_FRONT_DESK}
CAN_CREATE_EVENT: set[str] = {ROLE_ADMIN, ROLE_CLINICIAN}

# Roles that may read raw clinical content (transcripts, findings,
# drafts, signed notes). Front desk is excluded on purpose — they are
# operational, not clinical.
CAN_READ_CLINICAL_CONTENT: set[str] = {ROLE_ADMIN, ROLE_CLINICIAN, ROLE_REVIEWER}

# Per-transition authorization map. Keys are (from_status, to_status)
# tuples. Values are the set of roles allowed to perform that edge.
# Admin can perform any valid edge; clinicians, reviewers, and front
# desk are partitioned by operational vs review vs scheduling.
TRANSITION_ROLES: dict[tuple[str, str], set[str]] = {
    ("scheduled", "in_progress"):      {ROLE_ADMIN, ROLE_CLINICIAN, ROLE_FRONT_DESK},
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
