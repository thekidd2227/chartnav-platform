"""Phase 25A — GH-001 audio-consent gate tests.

Surface under test:
- GET /encounters/{id}/audio-consent
- PUT /encounters/{id}/audio-consent

Covers:
- Default state is `not_recorded` / recording NOT permitted.
- admin / clinician / front_desk / technician can set consent.
- reviewer is read-only (403 on PUT).
- recording_permitted flips True only when status=granted.
- Invalid status / method returns 400 with structured error.
- Cross-org access returns 404 (no existence leak).
- Audit row `audio_consent_updated` is written, detail carries no PHI.
- `note` is operator-facing label, capped at 500 chars.
"""

from __future__ import annotations

from tests.conftest import ADMIN1, CLIN1, REV1, FRONT1, TECH1, ADMIN2, CLIN2


def _first_encounter_id(client, headers) -> int:
    r = client.get("/encounters", headers=headers)
    assert r.status_code == 200, r.text
    encs = r.json()
    assert len(encs) >= 1, "seed should provide at least one encounter"
    return encs[0]["id"]


# ---------------------------------------------------------------
# Default state
# ---------------------------------------------------------------

def test_get_consent_default_is_not_recorded(client):
    eid = _first_encounter_id(client, ADMIN1)
    r = client.get(f"/encounters/{eid}/audio-consent", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encounter_id"] == eid
    assert body["status"] == "not_recorded"
    assert body["method"] == "unknown"
    assert body["recording_permitted"] is False
    assert body["actor_user_id"] is None
    assert body["note"] is None


def test_reviewer_can_read_consent(client):
    eid = _first_encounter_id(client, ADMIN1)
    r = client.get(f"/encounters/{eid}/audio-consent", headers=REV1)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "not_recorded"


# ---------------------------------------------------------------
# Set consent — happy path per role
# ---------------------------------------------------------------

def test_clinician_can_grant_consent_and_recording_permitted_flips(client):
    eid = _first_encounter_id(client, CLIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal", "note": "verbal consent at intake"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "granted"
    assert body["method"] == "verbal"
    assert body["recording_permitted"] is True
    assert body["note"] == "verbal consent at intake"

    # Read back returns the granted state.
    r2 = client.get(f"/encounters/{eid}/audio-consent", headers=CLIN1)
    assert r2.status_code == 200
    assert r2.json()["recording_permitted"] is True


def test_admin_can_set_consent(client):
    eid = _first_encounter_id(client, ADMIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=ADMIN1,
        json={"status": "granted", "method": "written"},
    )
    assert r.status_code == 200, r.text


def test_front_desk_can_set_consent(client):
    eid = _first_encounter_id(client, FRONT1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=FRONT1,
        json={"status": "granted", "method": "verbal"},
    )
    assert r.status_code == 200, r.text


def test_technician_can_set_consent(client):
    eid = _first_encounter_id(client, TECH1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=TECH1,
        json={"status": "granted", "method": "verbal"},
    )
    assert r.status_code == 200, r.text


def test_revoking_consent_blocks_recording(client):
    eid = _first_encounter_id(client, CLIN1)
    # Grant first.
    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal"},
    )
    # Now revoke.
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "revoked", "method": "verbal"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["recording_permitted"] is False


def test_declined_status_blocks_recording(client):
    eid = _first_encounter_id(client, CLIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "declined", "method": "verbal"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["recording_permitted"] is False


# ---------------------------------------------------------------
# RBAC negatives
# ---------------------------------------------------------------

def test_reviewer_cannot_set_consent(client):
    eid = _first_encounter_id(client, REV1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=REV1,
        json={"status": "granted", "method": "verbal"},
    )
    assert r.status_code == 403, r.text
    body = r.json()
    assert body["detail"]["error_code"] == "forbidden"


# ---------------------------------------------------------------
# Validation
# ---------------------------------------------------------------

def test_invalid_status_returns_400(client):
    eid = _first_encounter_id(client, CLIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "totally-fake", "method": "verbal"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["error_code"] == "invalid_status"


def test_invalid_method_returns_400(client):
    eid = _first_encounter_id(client, CLIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "telepathy"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["error_code"] == "invalid_method"


def test_note_too_long_rejected_by_pydantic(client):
    eid = _first_encounter_id(client, CLIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal", "note": "x" * 501},
    )
    # Pydantic max_length=500 → 422 before our service code runs.
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------
# Cross-org isolation — both GET and PUT must return 404, no leak
# ---------------------------------------------------------------

def test_cross_org_get_returns_404(client):
    # Encounter belongs to org 1; org-2 admin must see 404, not 403/200.
    eid = _first_encounter_id(client, ADMIN1)
    r = client.get(f"/encounters/{eid}/audio-consent", headers=ADMIN2)
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_cross_org_put_returns_404(client):
    eid = _first_encounter_id(client, ADMIN1)
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=ADMIN2,
        json={"status": "granted", "method": "verbal"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_cross_org_put_does_not_leak_state(client):
    # Org1 grants consent. Org2 GET on same encounter id returns 404,
    # not the granted state.
    eid = _first_encounter_id(client, CLIN1)
    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal"},
    )
    r = client.get(f"/encounters/{eid}/audio-consent", headers=CLIN2)
    assert r.status_code == 404


# ---------------------------------------------------------------
# Audit event
# ---------------------------------------------------------------

def test_set_consent_writes_audit_event_with_no_phi(client):
    eid = _first_encounter_id(client, CLIN1)
    secret_note = "PRIVATE_CONSENT_TOKEN_ZZZ"
    r = client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal", "note": secret_note},
    )
    assert r.status_code == 200

    from app.db import fetch_all
    rows = fetch_all(
        "SELECT event_type, detail FROM security_audit_events "
        "WHERE event_type = 'audio_consent_updated' ORDER BY id"
    )
    assert len(rows) >= 1
    # All rows for this event type carry structured detail only.
    for row in rows:
        detail = row["detail"] or ""
        assert "status=granted" in detail
        assert "method=verbal" in detail
        # The operator-facing note must NOT leak into the audit row.
        assert secret_note not in detail


def test_audit_event_records_status_change(client):
    eid = _first_encounter_id(client, CLIN1)
    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal"},
    )
    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "revoked", "method": "verbal"},
    )

    from app.db import fetch_all
    rows = fetch_all(
        "SELECT detail FROM security_audit_events "
        "WHERE event_type = 'audio_consent_updated' ORDER BY id"
    )
    details = [r["detail"] or "" for r in rows]
    assert any("status=granted" in d for d in details)
    assert any("status=revoked" in d for d in details)


# ---------------------------------------------------------------
# is_consent_granted() helper (used by the upload pipeline gate)
# ---------------------------------------------------------------

def test_is_consent_granted_helper(client):
    """The audio upload pipeline calls is_consent_granted(eid, org_id).
    This test verifies the helper returns True only after status=granted."""
    eid = _first_encounter_id(client, CLIN1)
    from app.services.consent import is_consent_granted
    # Look up org id directly from the encounter row.
    from app.db import fetch_one
    enc = fetch_one("SELECT organization_id FROM encounters WHERE id = :eid", {"eid": eid})
    assert enc is not None
    oid = enc["organization_id"]

    assert is_consent_granted(eid, oid) is False  # default not_recorded

    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "granted", "method": "verbal"},
    )
    assert is_consent_granted(eid, oid) is True

    client.put(
        f"/encounters/{eid}/audio-consent",
        headers=CLIN1,
        json={"status": "revoked", "method": "verbal"},
    )
    assert is_consent_granted(eid, oid) is False
