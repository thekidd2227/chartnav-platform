"""Provider action review queue routes.

Phase 11. Endpoints under
`/patients/{patient_id}/provider-action-items...`:

  POST   /patients/{patient_id}/provider-action-items/generate
  GET    /patients/{patient_id}/provider-action-items
  GET    /patients/{patient_id}/provider-action-items/{action_id}
  POST   /patients/{patient_id}/provider-action-items/{action_id}/accept
  POST   /patients/{patient_id}/provider-action-items/{action_id}/dismiss
  POST   /patients/{patient_id}/provider-action-items/{action_id}/complete

RBAC:
  admin / clinician — generate / accept / dismiss / complete + read.
  reviewer — read-only on this surface (matches the read-only convention
             on patient_summaries / scribe_sessions).

Org isolation: the patient is resolved inside the caller's org first;
cross-org returns 404 patient_not_found (no existence leak). The
`get_action_item` query is also `(organization_id, patient_id)` scoped
so an action_id from another org/patient looks like 404
provider_action_item_not_found.

Audit: every mutation emits a metadata-only `provider_action_item_*`
event. `title` and `reason` are NEVER written to the audit log — the
detail field encodes only ids and lifecycle markers.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit import record as audit_record
from app.auth import Caller, require_caller
from app.db import fetch_one
from app.services.provider_action_items import (
    ALL_ACTION_TYPES,
    ALL_PRIORITIES,
    ALL_STATUSES,
    GenerateResult,
    ImmutableProviderActionItem,
    InvalidProviderActionTransition,
    ProviderActionItem,
    accept_action_item,
    complete_action_item,
    dismiss_action_item,
    generate_action_items,
    get_action_item,
    list_action_items,
)


router = APIRouter(tags=["provider-action-items"])


_WRITE_ROLES: set[str] = {"admin", "clinician"}
_READ_ROLES: set[str] = {"admin", "clinician", "reviewer"}


# --- helpers -----------------------------------------------------------


def _err(code: str, reason: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error_code": code, "reason": reason},
    )


def _resolve_patient_in_org(patient_id: int, caller: Caller) -> int:
    row = fetch_one(
        "SELECT id FROM patients WHERE id = :id AND organization_id = :org",
        {"id": patient_id, "org": caller.organization_id},
    )
    if not row:
        raise _err(
            "patient_not_found",
            "patient not found in your organization",
            404,
        )
    return int(row["id"])


def _require_write_role(caller: Caller) -> None:
    if caller.role not in _WRITE_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot mutate provider action items; "
            "requires admin or clinician",
            403,
        )


def _require_read_role(caller: Caller) -> None:
    if caller.role not in _READ_ROLES:
        raise _err(
            "role_forbidden",
            f"role {caller.role!r} cannot read provider action items",
            403,
        )


def _get_or_404(
    action_id: int, *, caller: Caller, patient_id: int
) -> ProviderActionItem:
    item = get_action_item(
        action_id,
        organization_id=caller.organization_id,
        patient_id=patient_id,
    )
    if item is None:
        raise _err(
            "provider_action_item_not_found",
            "action item not found in your organization",
            404,
        )
    return item


def _audit_item(
    *,
    request: Request,
    caller: Caller,
    event_type: str,
    item: ProviderActionItem,
) -> None:
    """Metadata-only audit. Title and reason are NEVER included."""
    detail = (
        f"action_id={item.id} "
        f"patient_id={item.patient_id} "
        f"encounter_id={item.encounter_id} "
        f"action_type={item.action_type} "
        f"priority={item.priority} "
        f"status={item.status} "
        f"source_type={item.source_type} "
        f"source_id={item.source_id}"
    )
    audit_record(
        event_type=event_type,
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


def _audit_generated(
    *,
    request: Request,
    caller: Caller,
    patient_id: int,
    result: GenerateResult,
) -> None:
    detail = (
        f"patient_id={patient_id} "
        f"batch_id={result.batch_id} "
        f"generated_count={result.generated_count} "
        f"created_count={result.created_count} "
        f"reused_count={result.reused_count}"
    )
    audit_record(
        event_type="provider_action_items_generated",
        request_id=getattr(request.state, "request_id", None),
        actor_email=caller.email,
        actor_user_id=caller.user_id,
        organization_id=caller.organization_id,
        path=request.url.path,
        method=request.method,
        error_code=None,
        detail=detail,
        remote_addr=(request.client.host if request.client else None),
    )


def _translate_lifecycle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ImmutableProviderActionItem):
        return _err(
            "provider_action_item_immutable",
            f"action item is {exc.current_status} and cannot be modified",
            409,
        )
    if isinstance(exc, InvalidProviderActionTransition):
        return _err(
            "provider_action_invalid_transition",
            f"cannot {exc.action} from status {exc.current_status}",
            409,
        )
    raise exc


# --- routes ------------------------------------------------------------


@router.post("/patients/{patient_id}/provider-action-items/generate")
def generate_provider_action_items(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    result = generate_action_items(
        organization_id=caller.organization_id, patient_id=pid
    )
    _audit_generated(request=request, caller=caller, patient_id=pid, result=result)
    return result.to_response()


@router.get("/patients/{patient_id}/provider-action-items")
def list_provider_action_items(
    patient_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    action_type: Optional[str] = Query(default=None),
    encounter_id: Optional[int] = Query(default=None),
) -> dict[str, Any]:
    _require_read_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)

    if status is not None and status not in ALL_STATUSES:
        raise _err("invalid_status_filter", f"unknown status {status!r}", 400)
    if priority is not None and priority not in ALL_PRIORITIES:
        raise _err(
            "invalid_priority_filter",
            f"unknown priority {priority!r}",
            400,
        )
    if action_type is not None and action_type not in ALL_ACTION_TYPES:
        raise _err(
            "invalid_action_type_filter",
            f"unknown action_type {action_type!r}",
            400,
        )

    items = list_action_items(
        organization_id=caller.organization_id,
        patient_id=pid,
        status=status,
        priority=priority,
        action_type=action_type,
        encounter_id=encounter_id,
    )
    return {
        "items": [i.to_response() for i in items],
        "total": len(items),
    }


@router.get(
    "/patients/{patient_id}/provider-action-items/{action_id}"
)
def get_provider_action_item(
    patient_id: int,
    action_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_read_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    item = _get_or_404(action_id, caller=caller, patient_id=pid)
    return item.to_response()


@router.post(
    "/patients/{patient_id}/provider-action-items/{action_id}/accept"
)
def accept_provider_action_item(
    patient_id: int,
    action_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    item = _get_or_404(action_id, caller=caller, patient_id=pid)
    try:
        next_item = accept_action_item(item, user_id=caller.user_id)
    except (ImmutableProviderActionItem, InvalidProviderActionTransition) as e:
        raise _translate_lifecycle_error(e)
    _audit_item(
        request=request,
        caller=caller,
        event_type="provider_action_item_accepted",
        item=next_item,
    )
    return next_item.to_response()


@router.post(
    "/patients/{patient_id}/provider-action-items/{action_id}/dismiss"
)
def dismiss_provider_action_item(
    patient_id: int,
    action_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    item = _get_or_404(action_id, caller=caller, patient_id=pid)
    try:
        next_item = dismiss_action_item(item, user_id=caller.user_id)
    except (ImmutableProviderActionItem, InvalidProviderActionTransition) as e:
        raise _translate_lifecycle_error(e)
    _audit_item(
        request=request,
        caller=caller,
        event_type="provider_action_item_dismissed",
        item=next_item,
    )
    return next_item.to_response()


@router.post(
    "/patients/{patient_id}/provider-action-items/{action_id}/complete"
)
def complete_provider_action_item(
    patient_id: int,
    action_id: int,
    request: Request,
    caller: Caller = Depends(require_caller),
) -> dict[str, Any]:
    _require_write_role(caller)
    pid = _resolve_patient_in_org(patient_id, caller)
    item = _get_or_404(action_id, caller=caller, patient_id=pid)
    try:
        next_item = complete_action_item(item, user_id=caller.user_id)
    except (ImmutableProviderActionItem, InvalidProviderActionTransition) as e:
        raise _translate_lifecycle_error(e)
    _audit_item(
        request=request,
        caller=caller,
        event_type="provider_action_item_completed",
        item=next_item,
    )
    return next_item.to_response()
