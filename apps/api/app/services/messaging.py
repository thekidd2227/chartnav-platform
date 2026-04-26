"""Messaging hardening — provider seam + dispatcher + opt-out parser.

Spec: docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md

What this module is:
  - The honest skeleton ChartNav will plug a real SMS / email vendor
    into when (and only when) Phase C wires one. Today the only
    provider that actually does anything is StubProvider — it logs
    a workflow_events row, returns a synthetic provider_message_id,
    and transitions the message row through the documented state
    machine.
  - A dispatcher that respects opt-out precedence: queued outbound
    to an opted-out patient transitions DIRECTLY to 'opt_out' and
    no provider is called.
  - An inbound STOP / HELP keyword parser. STOP flips opt-in to
    False, stamps opted_out_at, sources the opt-out as
    'inbound-stop', and cancels any queued outbound on that
    channel for that patient.

What this module is NOT (truth limitations §9 of the spec):
  - It does NOT send real SMS or email. The TwilioProviderSkeleton
    raises NotImplementedError on send(). Wiring is Phase C and is
    blocked on operator BAA + carrier credentials.
  - It does NOT register a webhook. Inbound STOP is simulated via
    an admin route in Phase B; real webhook plumbing is Phase C.
  - It does NOT imply carrier-level delivery confirmation. The
    "delivered" status produced by StubProvider means "the stub
    recorded a synthetic delivery" — never carrier ACK. The UI
    enforces this via MessageStatusLabel rendering "Stub-delivered".
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db import fetch_all, fetch_one, insert_returning_id, transaction


# ---------- Channel + status constants -------------------------------

CHANNEL_SMS_STUB = "sms_stub"
CHANNEL_EMAIL_STUB = "email_stub"
ALLOWED_CHANNELS = {CHANNEL_SMS_STUB, CHANNEL_EMAIL_STUB}

# Per spec §4 the legal transitions are:
#   queued -> sent -> delivered
#   queued -> sent -> failed
#   queued -> opt_out
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"sent", "opt_out"},
    "sent": {"delivered", "failed"},
    "delivered": {"read"},  # observed read only
    "failed": set(),
    "opt_out": set(),
    "read": set(),
}


class MessagingError(Exception):
    def __init__(self, code: str, http_status: int = 400):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


# ---------- Provider seam --------------------------------------------

class MessagingProvider:
    """Abstract base. Real implementations live in Phase C."""
    kind: str = "abstract"

    def send(self, *, channel: str, to: str, body: str) -> dict[str, Any]:
        raise NotImplementedError("MessagingProvider.send is abstract")


class StubProvider(MessagingProvider):
    """Phase B default. Returns a synthetic provider_message_id and
    writes a workflow_events row so downstream observers see the
    intent. Does NOT touch any external system."""
    kind: str = "stub"

    def send(self, *, channel: str, to: str, body: str) -> dict[str, Any]:
        if channel not in ALLOWED_CHANNELS:
            raise MessagingError("invalid_channel", 400)
        # 16 hex chars + "stub-" prefix so the ID is obviously
        # synthetic in any log line.
        synthetic = "stub-" + secrets.token_hex(8)
        return {
            "provider_message_id": synthetic,
            "delivered_synthetically": True,
            "advisory": (
                "Stub provider — no real SMS or email transmitted in "
                "Phase B. provider_message_id is a ChartNav-synthetic "
                "value, not a carrier reference."
            ),
        }


class TwilioProviderSkeleton(MessagingProvider):
    """Defines the seam Twilio (or any real provider) will plug
    into in Phase C. The send() method raises NotImplementedError
    deliberately — wiring is gated on operator BAA + credentials,
    neither of which is in scope for Phase B."""
    kind: str = "twilio_skeleton"

    def send(self, *, channel: str, to: str, body: str) -> dict[str, Any]:
        raise NotImplementedError(
            "TwilioProviderSkeleton.send is intentionally not "
            "implemented in Phase B; wiring lands in Phase C."
        )


_default_provider: MessagingProvider = StubProvider()


def get_default_provider() -> MessagingProvider:
    return _default_provider


def set_default_provider_for_tests(p: MessagingProvider) -> None:
    """Test-only seam swap so unit tests can drive failure paths."""
    global _default_provider
    _default_provider = p


# ---------- Preference helpers ---------------------------------------

def get_preference(
    *, organization_id: int, patient_identifier: str, channel: str,
) -> dict | None:
    return fetch_one(
        "SELECT id, organization_id, patient_identifier, channel, "
        "       opted_in, opted_out_at, opt_out_source, updated_at "
        "FROM patient_communication_preferences "
        "WHERE organization_id = :oid AND patient_identifier = :p AND channel = :c",
        {"oid": organization_id, "p": patient_identifier, "c": channel},
    )


def upsert_preference(
    *,
    organization_id: int,
    patient_identifier: str,
    channel: str,
    opted_in: bool,
    source: str,
) -> dict:
    if channel not in ALLOWED_CHANNELS:
        raise MessagingError("invalid_channel", 400)
    existing = get_preference(
        organization_id=organization_id,
        patient_identifier=patient_identifier,
        channel=channel,
    )
    opted_out_at = None if opted_in else datetime.now(timezone.utc).isoformat(timespec="seconds")
    with transaction() as conn:
        if existing:
            conn.execute(
                text(
                    "UPDATE patient_communication_preferences SET "
                    "  opted_in = :oi, opted_out_at = :ooa, "
                    "  opt_out_source = :src, "
                    "  updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :id"
                ),
                {
                    "oi": int(bool(opted_in)),
                    "ooa": opted_out_at,
                    "src": source,
                    "id": existing["id"],
                },
            )
        else:
            insert_returning_id(
                conn,
                "patient_communication_preferences",
                {
                    "organization_id": organization_id,
                    "patient_identifier": patient_identifier,
                    "channel": channel,
                    "opted_in": int(bool(opted_in)),
                    "opted_out_at": opted_out_at,
                    "opt_out_source": source,
                },
            )
    return get_preference(
        organization_id=organization_id,
        patient_identifier=patient_identifier,
        channel=channel,
    ) or {}


def is_opted_in(
    *, organization_id: int, patient_identifier: str, channel: str,
) -> bool:
    pref = get_preference(
        organization_id=organization_id,
        patient_identifier=patient_identifier,
        channel=channel,
    )
    if not pref:
        # Default-deny: no preference means we did NOT collect a
        # consent. The dispatcher refuses to send.
        return False
    return bool(pref.get("opted_in"))


# ---------- Dispatcher -----------------------------------------------

def enqueue_outbound(
    *,
    organization_id: int,
    patient_identifier: str,
    channel: str,
    body: str,
    reminder_id: int | None = None,
) -> dict:
    """Enqueue an outbound message. Honors opt-out: a patient who is
    not opted-in on this channel (or has been STOP'd) gets an
    `opt_out` row and the provider is NOT called."""
    if channel not in ALLOWED_CHANNELS:
        raise MessagingError("invalid_channel", 400)
    opted_in = is_opted_in(
        organization_id=organization_id,
        patient_identifier=patient_identifier,
        channel=channel,
    )
    initial_status = "queued" if opted_in else "opt_out"
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "messages",
            {
                "organization_id": organization_id,
                "reminder_id": reminder_id,
                "patient_identifier": patient_identifier,
                "channel": channel,
                "direction": "outbound",
                "body": body,
                "status": initial_status,
                "provider_kind": "stub",
            },
        )
    if not opted_in:
        return _row(new_id)

    # Hand to the provider. StubProvider returns immediately; any
    # exception flips the row to failed.
    provider = get_default_provider()
    try:
        out = provider.send(channel=channel, to=patient_identifier, body=body)
        provider_id = out.get("provider_message_id")
        _transition(new_id, expected_from="queued", to_status="sent",
                    provider_message_id=provider_id,
                    provider_kind=provider.kind)
        # The stub claims synthetic delivery immediately so end-to-end
        # demos can show the full state-machine. Any real provider
        # reaches "delivered" only on a carrier callback (Phase C).
        if isinstance(provider, StubProvider):
            _transition(new_id, expected_from="sent", to_status="delivered")
    except NotImplementedError:
        _transition(new_id, expected_from="queued", to_status="failed",
                    provider_kind=provider.kind)
    except Exception:
        _transition(new_id, expected_from="queued", to_status="failed",
                    provider_kind=provider.kind)
    return _row(new_id)


def transition_message_status(message_id: int, *, new_status: str) -> dict:
    """Public state-machine transition entry point. 409 on illegal
    transitions (per spec §4)."""
    row = _row(message_id)
    if not row:
        raise MessagingError("message_not_found", 404)
    cur = row["status"]
    if new_status not in ALLOWED_STATUS_TRANSITIONS.get(cur, set()):
        raise MessagingError("invalid_status_transition", 409)
    _transition(message_id, expected_from=cur, to_status=new_status)
    return _row(message_id)


def _transition(
    message_id: int,
    *,
    expected_from: str,
    to_status: str,
    provider_message_id: str | None = None,
    provider_kind: str | None = None,
) -> None:
    fields = ["status = :ns", "updated_at = CURRENT_TIMESTAMP"]
    params: dict[str, Any] = {"id": message_id, "cur": expected_from, "ns": to_status}
    if provider_message_id is not None:
        fields.append("provider_message_id = :pmid")
        params["pmid"] = provider_message_id
    if provider_kind is not None:
        fields.append("provider_kind = :pkind")
        params["pkind"] = provider_kind
    sql = (
        "UPDATE messages SET " + ", ".join(fields) +
        " WHERE id = :id AND status = :cur"
    )
    with transaction() as conn:
        conn.execute(text(sql), params)


def _row(message_id: int) -> dict:
    return fetch_one(
        "SELECT id, organization_id, reminder_id, patient_identifier, "
        "       channel, direction, body, status, provider_message_id, "
        "       provider_kind, created_at, updated_at "
        "FROM messages WHERE id = :id",
        {"id": message_id},
    ) or {}


# ---------- Inbound STOP/HELP parser ---------------------------------

STOP_KEYWORDS = {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}
HELP_KEYWORDS = {"HELP", "INFO"}


def parse_inbound(body: str) -> str:
    """Return 'stop' | 'help' | 'other' for an inbound body."""
    if not body:
        return "other"
    token = body.strip().split()[0].upper().rstrip("!.,")
    if token in STOP_KEYWORDS:
        return "stop"
    if token in HELP_KEYWORDS:
        return "help"
    return "other"


def record_inbound(
    *,
    organization_id: int,
    patient_identifier: str,
    channel: str,
    body: str,
) -> dict:
    """Records the inbound row and, if it parses as STOP, flips the
    preference + cancels any queued outbound on that channel."""
    if channel not in ALLOWED_CHANNELS:
        raise MessagingError("invalid_channel", 400)
    intent = parse_inbound(body)
    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "messages",
            {
                "organization_id": organization_id,
                "reminder_id": None,
                "patient_identifier": patient_identifier,
                "channel": channel,
                "direction": "inbound",
                "body": body,
                "status": "delivered",
                "provider_kind": "stub",
            },
        )
    if intent == "stop":
        upsert_preference(
            organization_id=organization_id,
            patient_identifier=patient_identifier,
            channel=channel,
            opted_in=False,
            source="inbound-stop",
        )
        # Cancel any outbound that has not yet been sent.
        with transaction() as conn:
            conn.execute(
                text(
                    "UPDATE messages SET status = 'opt_out', "
                    "  updated_at = CURRENT_TIMESTAMP "
                    "WHERE organization_id = :oid "
                    "  AND patient_identifier = :p "
                    "  AND channel = :c "
                    "  AND direction = 'outbound' "
                    "  AND status = 'queued'"
                ),
                {
                    "oid": organization_id,
                    "p": patient_identifier,
                    "c": channel,
                },
            )
    return {"id": new_id, "intent": intent}


# ---------- List helpers ---------------------------------------------

def list_messages(
    *, organization_id: int,
) -> list[dict]:
    rows = fetch_all(
        "SELECT id, organization_id, reminder_id, patient_identifier, "
        "       channel, direction, body, status, provider_message_id, "
        "       provider_kind, created_at "
        "FROM messages WHERE organization_id = :oid "
        "ORDER BY created_at DESC, id DESC",
        {"oid": organization_id},
    )
    return [dict(r) for r in rows]
