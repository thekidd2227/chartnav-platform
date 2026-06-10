"""Phase 82 — Note Validation Rail HTTP route.

GET /api/v1/encounters/{encounter_id}/note-validation

Read-only deterministic validation across structured workflow data
the provider already entered. Same auth + cross-org semantics as the
rest of the encounter surface (404 on cross-org).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.note_validation import ValidationError, build_validation

router = APIRouter(prefix="/api/v1", tags=["note-validation"])


@router.get("/encounters/{encounter_id}/note-validation")
def get_note_validation(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_validation(encounter_id, caller)
    except ValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )
