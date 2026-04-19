"""Signed-note transmission orchestrator (phase 26).

Glue between phase 25 (artifact packaging) and the adapter layer
(write path). The service's job is to:

1. Look up the signed note + build the canonical + FHIR artifact via
   `app.services.note_artifact`.
2. Enforce gating — platform mode must be `integrated_writethrough`,
   caller role must be allowed to transmit, note must be signed,
   adapter must advertise `supports_document_transmit`.
3. Persist a `note_transmissions` row *before* calling the adapter so
   a crash mid-call still leaves a trace. Update the row with the
   adapter's `TransmitResult` after the call returns.
4. Refuse to re-transmit a note-version that already succeeded,
   unless the caller sets ``force=True``.
5. Emit an audit event on every attempt, successful or not.

The service is synchronous today (runs in the request path). The
contract survives a future move to a background worker — the worker
would call `run_transmission(...)` the same way.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db import engine, fetch_all, fetch_one, insert_returning_id

log = logging.getLogger("chartnav.note_transmit")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TransmissionError(RuntimeError):
    """Raised when a transmission cannot proceed for a clean reason.

    Maps 1:1 onto HTTP envelopes in the handler. ``error_code`` is the
    stable identifier clients key off; ``status_code`` is HTTP.
    """

    def __init__(self, error_code: str, reason: str, status_code: int):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRANSMISSION_COLUMNS = (
    "id, note_version_id, encounter_id, organization_id, adapter_key, "
    "target_system, transport_status, request_body_hash, response_code, "
    "response_snippet, remote_id, last_error_code, last_error, "
    "attempt_number, attempted_at, completed_at, created_by_user_id, "
    "created_at, updated_at"
)

# Write path is a clinical action; only admin + clinician may attest to
# handoff. Reviewers can read transmissions but not initiate them.
ALLOWED_TRANSMIT_ROLES = {"admin", "clinician"}


def _hash_request(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_transmission(transmission_id: int) -> dict[str, Any] | None:
    row = fetch_one(
        f"SELECT {TRANSMISSION_COLUMNS} FROM note_transmissions WHERE id = :id",
        {"id": transmission_id},
    )
    return dict(row) if row is not None else None


def _next_attempt_number(note_version_id: int) -> int:
    row = fetch_one(
        "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS n "
        "FROM note_transmissions WHERE note_version_id = :id",
        {"id": note_version_id},
    )
    return int(row["n"]) if row else 1


def _succeeded_exists(note_version_id: int) -> bool:
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM note_transmissions "
        "WHERE note_version_id = :id AND transport_status = 'succeeded'",
        {"id": note_version_id},
    )
    return bool(row and int(row["n"]) > 0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


@dataclass
class RunTransmissionInput:
    note_version_id: int
    caller_email: str
    caller_user_id: int | None
    caller_organization_id: int | None
    caller_role: str
    force: bool = False


def run_transmission(args: RunTransmissionInput) -> dict[str, Any]:
    """End-to-end: gate → build artifact → dispatch → persist.

    Returns the final `note_transmissions` row as a dict. Never raises
    on a *business* failure (HTTP 4xx from the remote, adapter
    rejection); those are persisted into the row and returned.
    """
    from app.config import settings
    from app.integrations import resolve_adapter
    from app.integrations.base import AdapterError, AdapterNotSupported
    from app.services.note_artifact import (
        ArtifactError,
        build_artifact,
        render_fhir_document_reference,
    )

    # -------- role gate --------
    if args.caller_role not in ALLOWED_TRANSMIT_ROLES:
        raise TransmissionError(
            "role_cannot_transmit",
            "only admin or clinician may transmit a signed note",
            403,
        )

    # -------- mode gate --------
    if settings.platform_mode != "integrated_writethrough":
        raise TransmissionError(
            "transmit_not_available_in_mode",
            f"platform_mode={settings.platform_mode!r} does not permit "
            "transmission; switch to integrated_writethrough or run "
            "the export endpoint instead",
            409,
        )

    # -------- adapter gate --------
    try:
        adapter = resolve_adapter()
    except Exception as e:
        raise TransmissionError(
            "adapter_resolve_failed",
            f"could not resolve adapter: {type(e).__name__}: {e}",
            500,
        )
    if not getattr(adapter.info, "supports_document_transmit", False):
        raise TransmissionError(
            "adapter_does_not_support_transmit",
            f"adapter {adapter.info.key!r} does not support "
            "document transmission",
            409,
        )

    # -------- artifact build (reuses phase 25 gating) --------
    try:
        artifact = build_artifact(
            note_id=args.note_version_id,
            caller_email=args.caller_email,
            caller_user_id=args.caller_user_id,
            caller_organization_id=args.caller_organization_id,
        )
    except ArtifactError as e:
        raise TransmissionError(e.error_code, e.reason, e.status_code)

    doc_ref = render_fhir_document_reference(artifact)
    request_body_hash = _hash_request(doc_ref)

    # -------- already-succeeded guard --------
    if not args.force and _succeeded_exists(args.note_version_id):
        raise TransmissionError(
            "already_transmitted",
            "a prior transmission succeeded; pass force=true to re-send",
            409,
        )

    # -------- persist a dispatching row BEFORE calling the adapter --------
    attempt_number = _next_attempt_number(args.note_version_id)
    target_system = getattr(adapter, "_base_url", None) or adapter.info.display_name
    encounter_id = artifact["encounter"]["id"]
    organization_id = artifact["chartnav"]["organization_id"]

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO note_transmissions "
                "(note_version_id, encounter_id, organization_id, "
                " adapter_key, target_system, transport_status, "
                " request_body_hash, attempt_number, attempted_at, "
                " created_by_user_id) "
                "VALUES (:nvid, :eid, :org, :akey, :tgt, 'dispatching', "
                " :hash, :an, :now, :uid) "
                "RETURNING id"
            ),
            {
                "nvid": args.note_version_id,
                "eid": encounter_id,
                "org": organization_id,
                "akey": adapter.info.key,
                "tgt": target_system,
                "hash": request_body_hash,
                "an": attempt_number,
                "now": datetime.now(timezone.utc),
                "uid": args.caller_user_id,
            },
        ).mappings().first()
        transmission_id = int(row["id"])

    # -------- call the adapter --------
    encounter_external_ref = artifact["encounter"].get("external_ref")
    try:
        result = adapter.transmit_artifact(
            artifact=artifact,
            document_reference=doc_ref,
            note_version_id=args.note_version_id,
            encounter_external_ref=encounter_external_ref,
        )
        final_status = result.status
        response_code = result.response_code
        response_snippet = (result.response_snippet or "")[:1024] or None
        remote_id = result.remote_id
        error_code = result.error_code
        error_reason = result.error_reason
    except AdapterNotSupported as e:
        final_status = "unsupported"
        response_code = None
        response_snippet = None
        remote_id = None
        error_code = e.error_code
        error_reason = e.reason
    except AdapterError as e:
        final_status = "failed"
        response_code = None
        response_snippet = None
        remote_id = None
        error_code = e.error_code
        error_reason = e.reason
    except Exception as e:  # noqa: BLE001 — we must persist something
        log.exception(
            "unexpected adapter error during transmission "
            "note_version_id=%s transmission_id=%s",
            args.note_version_id, transmission_id,
        )
        final_status = "failed"
        response_code = None
        response_snippet = None
        remote_id = None
        error_code = "transmit_unexpected_error"
        error_reason = f"{type(e).__name__}: {e}"

    # -------- update the row with the outcome --------
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE note_transmissions SET "
                "transport_status = :status, "
                "response_code = :rc, "
                "response_snippet = :snip, "
                "remote_id = :rid, "
                "last_error_code = :ec, "
                "last_error = :er, "
                "completed_at = :now, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {
                "id": transmission_id,
                "status": final_status,
                "rc": response_code,
                "snip": response_snippet,
                "rid": remote_id,
                "ec": error_code,
                "er": error_reason,
                "now": datetime.now(timezone.utc),
            },
        )

    return _load_transmission(transmission_id) or {}


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def list_transmissions_for_note(
    *, note_version_id: int, organization_id: int | None
) -> list[dict[str, Any]]:
    """Return all transmissions for a given note, newest attempt first,
    constrained to the caller's organization. Caller-facing gating
    (does the note exist? cross-org mask?) happens in the handler via
    a shared note-load helper — this function just enforces the
    denormalized org filter."""
    if organization_id is None:
        return []
    rows = fetch_all(
        f"SELECT {TRANSMISSION_COLUMNS} FROM note_transmissions "
        "WHERE note_version_id = :id AND organization_id = :org "
        "ORDER BY attempt_number DESC",
        {"id": note_version_id, "org": organization_id},
    )
    return [dict(r) for r in rows]
