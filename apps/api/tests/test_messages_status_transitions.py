"""Phase 2 item 4 — message state-machine transitions.

Spec: docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md §4.

Valid transitions:
  queued -> sent -> delivered
  queued -> sent -> failed
  queued -> opt_out
Invalid (e.g. delivered -> queued) returns 409.
"""
from __future__ import annotations

from sqlalchemy import text

from .conftest import ADMIN1


def _force_status(message_id: int, status: str) -> None:
    from app.db import transaction
    with transaction() as conn:
        conn.execute(
            text("UPDATE messages SET status = :s WHERE id = :id"),
            {"s": status, "id": message_id},
        )


def _opt_in_and_enqueue(client) -> int:
    client.patch(
        "/patients/PT-STATE/preferences",
        json={"channel": "sms_stub", "opted_in": True, "source": "x"},
        headers=ADMIN1,
    )
    r = client.post(
        "/messages/enqueue",
        json={"patient_identifier": "PT-STATE", "channel": "sms_stub",
              "body": "hi"},
        headers=ADMIN1,
    )
    assert r.status_code == 201
    return int(r.json()["id"])


def test_invalid_transition_delivered_to_queued_returns_409(client):
    mid = _opt_in_and_enqueue(client)
    # Stub already drove the row to delivered. Try to move it back.
    r = client.post(
        f"/messages/{mid}/transition",
        json={"status": "queued"},
        headers=ADMIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "invalid_status_transition"


def test_legal_chain_queued_sent_delivered(client):
    mid = _opt_in_and_enqueue(client)
    # Force back to queued so we can re-walk legitimately.
    _force_status(mid, "queued")
    r1 = client.post(
        f"/messages/{mid}/transition", json={"status": "sent"}, headers=ADMIN1,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "sent"
    r2 = client.post(
        f"/messages/{mid}/transition", json={"status": "delivered"}, headers=ADMIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "delivered"


def test_legal_chain_queued_sent_failed(client):
    mid = _opt_in_and_enqueue(client)
    _force_status(mid, "queued")
    r1 = client.post(
        f"/messages/{mid}/transition", json={"status": "sent"}, headers=ADMIN1,
    )
    assert r1.status_code == 200
    r2 = client.post(
        f"/messages/{mid}/transition", json={"status": "failed"}, headers=ADMIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "failed"


def test_legal_queued_to_opt_out(client):
    mid = _opt_in_and_enqueue(client)
    _force_status(mid, "queued")
    r = client.post(
        f"/messages/{mid}/transition", json={"status": "opt_out"}, headers=ADMIN1,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "opt_out"


def test_transition_unknown_message_404(client):
    r = client.post(
        "/messages/9999999/transition", json={"status": "sent"}, headers=ADMIN1,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "message_not_found"
