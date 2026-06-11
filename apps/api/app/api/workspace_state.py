"""Phase 91 — Unified Ophthalmology Workspace State HTTP routes.

GET   /api/v1/encounters/{encounter_id}/workspace-state
PATCH /api/v1/encounters/{encounter_id}/workspace-state/visit-mode
PATCH /api/v1/encounters/{encounter_id}/workspace-state/active-laterality

Read returns the unified workspace state (profile + emphasis +
active laterality + metadata). The two PATCH endpoints let an admin
or clinician set the provider-driven values; cross-org access
returns 404 (no existence leak).

ChartNav does NOT auto-classify the visit mode, does NOT
autonomously select an eye, does NOT add new clinical intelligence,
and does NOT generate diagnoses.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.workspace_state import (
    WorkspaceStateError,
    resolve_state_for_encounter,
    set_active_laterality,
    set_visit_mode,
)

router = APIRouter(prefix="/api/v1", tags=["workspace-state"])


def _translate(exc: WorkspaceStateError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class VisitModePatch(BaseModel):
    visit_mode: str = Field(..., min_length=1, max_length=24)


class ActiveLateralityPatch(BaseModel):
    active_laterality: str = Field(..., min_length=1, max_length=4)


@router.get("/encounters/{encounter_id}/workspace-state")
def get_workspace_state(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return resolve_state_for_encounter(encounter_id, caller)
    except WorkspaceStateError as exc:
        raise _translate(exc)


@router.patch(
    "/encounters/{encounter_id}/workspace-state/visit-mode"
)
def patch_visit_mode(
    encounter_id: int,
    payload: VisitModePatch,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return set_visit_mode(encounter_id, caller, payload.visit_mode)
    except WorkspaceStateError as exc:
        raise _translate(exc)


@router.patch(
    "/encounters/{encounter_id}/workspace-state/active-laterality"
)
def patch_active_laterality(
    encounter_id: int,
    payload: ActiveLateralityPatch,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return set_active_laterality(
            encounter_id, caller, payload.active_laterality
        )
    except WorkspaceStateError as exc:
        raise _translate(exc)
