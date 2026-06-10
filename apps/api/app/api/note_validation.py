"""Phase 82 — Note Validation Rail HTTP route.
Phase 83 — Acknowledgement persistence + listing.

GET  /api/v1/encounters/{encounter_id}/note-validation
POST /api/v1/encounters/{encounter_id}/note-validation/acknowledgements
GET  /api/v1/encounters/{encounter_id}/note-validation/acknowledgements

Read-only deterministic validation across structured workflow data
the provider already entered. Same auth + cross-org semantics as the
rest of the encounter surface (404 on cross-org).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth import Caller, require_caller
from app.services.note_validation import ValidationError, build_validation
from app.services.note_validation_acknowledgements import (
    AckError,
    create_acknowledgement,
    list_acknowledgements,
)

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


class AcknowledgementCreate(BaseModel):
    # Allow extras through Pydantic so the service-side free-text canary
    # can explicitly 422 them — preserves our error_code semantics.
    model_config = ConfigDict(extra="allow")
    validation_item_id: str = Field(..., min_length=1, max_length=120)
    validation_category: str = Field(..., min_length=1, max_length=60)
    acknowledgement_type: Optional[str] = "acknowledged"


@router.post(
    "/encounters/{encounter_id}/note-validation/acknowledgements",
    status_code=201,
)
def post_note_validation_acknowledgement(
    encounter_id: int,
    payload: AcknowledgementCreate,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict:
    rid = request.headers.get("X-Request-ID")
    try:
        return create_acknowledgement(
            encounter_id,
            caller,
            payload.model_dump(exclude_none=True),
            request_id=rid,
            path=str(request.url.path) if request else None,
        )
    except AckError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )


@router.get(
    "/encounters/{encounter_id}/note-validation/acknowledgements"
)
def get_note_validation_acknowledgements(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> list[dict]:
    try:
        return list_acknowledgements(encounter_id, caller)
    except AckError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )
