"""Phase 77 — Retina Visit Packet HTTP route.

GET /api/v1/encounters/{encounter_id}/retina-visit-packet

Returns a self-describing JSON document built from the Phase 76
aggregator plus packet-level metadata (schema_version, generated_at,
artifact_hashes, safety_boundaries). Same auth + cross-org semantics
as the rest of the encounter surface — 404 on unknown / cross-org.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import Caller, require_caller
from app.services.retina_visit_packet import build_packet
from app.services.retina_visit_summary import SummaryError

router = APIRouter(prefix="/api/v1", tags=["retina-visit-packet"])


@router.get("/encounters/{encounter_id}/retina-visit-packet")
def get_retina_visit_packet(
    encounter_id: int,
    caller: Caller = Depends(require_caller),
) -> dict:
    try:
        return build_packet(encounter_id, caller)
    except SummaryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "reason": exc.reason},
        )
