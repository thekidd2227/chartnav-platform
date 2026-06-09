"""Phase 81 — Provider Action Item Queue HTTP route.

GET /api/v1/provider-action-queue

Caller-org-scoped (same convention as the Phase 78 anti-VEGF
readiness queue — the queue belongs to the authenticated caller's
organization, not a path-specified provider id). Read-only; pure
aggregation over Phases 78/79/80 + signed-lock data. No schema.

Distinct from the older per-patient ``/patients/{id}/provider-action-items``
surface (Phase 20-era), which stays untouched.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import Caller, require_caller
from app.services.provider_action_queue import build_action_queue

router = APIRouter(prefix="/api/v1", tags=["provider-action-queue"])


@router.get("/provider-action-queue")
def get_provider_action_queue(
    caller: Caller = Depends(require_caller),
) -> dict:
    return build_action_queue(caller)
