"""Phase 86 — Subspecialty Adaptive Workspace HTTP routes.

GET   /api/v1/encounters/{encounter_id}/workspace-profile
PATCH /api/v1/encounters/{encounter_id}/workspace-profile

The GET returns the resolved profile + panel ordering. The PATCH
lets admin / clinician change the encounter's subspecialty type;
reviewer / technician / front_desk get 403. Cross-org access
returns 404 (no existence leak).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Caller, require_caller
from app.services.workspace_profiles import (
    WorkspaceProfileError,
    resolve_for_encounter,
    set_encounter_type,
)

router = APIRouter(prefix="/api/v1", tags=["workspace-profile"])


def _translate(exc: WorkspaceProfileError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


class WorkspaceProfilePatch(BaseModel):
    encounter_type: str = Field(..., min_length=1, max_length=24)


@router.get("/encounters/{encounter_id}/workspace-profile")
def get_workspace_profile(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return resolve_for_encounter(encounter_id, caller)
    except WorkspaceProfileError as exc:
        raise _translate(exc)


@router.patch("/encounters/{encounter_id}/workspace-profile")
def patch_workspace_profile(
    encounter_id: int,
    payload: WorkspaceProfilePatch,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return set_encounter_type(
            encounter_id, caller, payload.encounter_type
        )
    except WorkspaceProfileError as exc:
        raise _translate(exc)
