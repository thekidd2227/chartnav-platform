"""Phase 88 — Imaging Metadata Review Linkage HTTP routes.

GET   /api/v1/encounters/{encounter_id}/imaging-metadata
PATCH /api/v1/imaging-metadata/{metadata_id}/review

Read-only listing per encounter + provider-driven review state
update. PATCH requires admin or clinician; reviewer / technician /
front_desk get 403. Cross-org access returns 404 (no existence leak).

This phase intentionally does NOT add a POST route. Imaging study
creation continues to flow through the existing Phase 21B pipeline
endpoints (POST /api/v1/patients/{id}/imaging-studies). Phase 88
adds the metadata review surface, not the upload surface.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.imaging_metadata import (
    ImagingMetadataError,
    list_for_encounter,
    mark_reviewed,
)

router = APIRouter(prefix="/api/v1", tags=["imaging-metadata"])


def _translate(exc: ImagingMetadataError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error_code": exc.error_code, "reason": exc.reason},
    )


@router.get("/encounters/{encounter_id}/imaging-metadata")
def get_encounter_imaging_metadata(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return list_for_encounter(encounter_id, caller)
    except ImagingMetadataError as exc:
        raise _translate(exc)


@router.patch("/imaging-metadata/{metadata_id}/review")
def patch_imaging_metadata_review(
    metadata_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return mark_reviewed(metadata_id, caller)
    except ImagingMetadataError as exc:
        raise _translate(exc)
