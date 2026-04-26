"""Phase 2 item 3 — intake tokens (issuance + public read).

Spec: docs/chartnav/closure/PHASE_B_Digital_Intake.md §4.

Per the Phase 2 reviewer guidance:
  - intake tokens MUST be scoped, unguessable, and expire (72h).
  - rate limiting MUST be endpoint-specific and covered by tests.
  - NO PHI may be exposed from invalid, expired, or wrong-org
    tokens — error responses never echo the candidate identifier
    or the raw token.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .conftest import ADMIN1, ADMIN2, CLIN1, REV1, TECH1, BILLING1


# -------- helpers ---------------------------------------------------

def _issue(client, headers=ADMIN1, candidate=None):
    body = {"patient_identifier_candidate": candidate} if candidate else {}
    r = client.post("/intakes/tokens", json=body, headers=headers)
    return r


# -------- token issuance --------------------------------------------

def test_admin_can_issue_token(client):
    r = _issue(client, headers=ADMIN1)
    assert r.status_code == 201, r.text
    body = r.json()
    assert "token" in body
    assert isinstance(body["token"], str) and len(body["token"]) >= 32
    assert body["url"].startswith("/intake/")
    assert body["url"].endswith(body["token"])
    # expires_at is in the future, ~72h out.
    exp = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    delta = exp - datetime.now(timezone.utc)
    assert delta > timedelta(hours=71)
    assert delta < timedelta(hours=73)


def test_clinician_cannot_issue_token(client):
    r = _issue(client, headers=CLIN1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_issue_intake_token"


def test_reviewer_cannot_issue_token(client):
    r = _issue(client, headers=REV1)
    assert r.status_code == 403


def test_technician_cannot_issue_token(client):
    r = _issue(client, headers=TECH1)
    assert r.status_code == 403


def test_biller_cannot_issue_token(client):
    r = _issue(client, headers=BILLING1)
    assert r.status_code == 403


def test_unauthenticated_cannot_issue_token(client):
    r = client.post("/intakes/tokens", json={})
    assert r.status_code == 401


# -------- token rotation: 2nd token does not invalidate the first ---

def test_rotate_token_does_not_invalidate_first(client):
    a = _issue(client, headers=ADMIN1, candidate="PT-ROT").json()
    b = _issue(client, headers=ADMIN1, candidate="PT-ROT").json()
    # The first token still resolves before either is used.
    r1 = client.get(f"/intakes/{a['token']}")
    r2 = client.get(f"/intakes/{b['token']}")
    assert r1.status_code == 200
    assert r2.status_code == 200


# -------- public GET — happy path -----------------------------------

def test_public_get_returns_form_schema_and_branding(client):
    issued = _issue(client, headers=ADMIN1).json()
    from app.services.intake import reset_rate_limit_for_tests
    reset_rate_limit_for_tests()
    r = client.get(f"/intakes/{issued['token']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "form_schema" in body
    assert "organization_branding" in body
    assert body["organization_branding"]["name"]
    # PHI hygiene: no token, no candidate identifier.
    flat = str(body)
    assert issued["token"] not in flat


# -------- public GET — unknown token --------------------------------

def test_public_get_unknown_token_returns_404_and_no_phi(client):
    from app.services.intake import reset_rate_limit_for_tests
    reset_rate_limit_for_tests()
    r = client.get("/intakes/totally-bogus-token-value-32-chars-xyz")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["error_code"] == "intake_token_not_found"
    # PHI hygiene: do not echo the bogus token in the reason.
    assert "totally-bogus" not in detail["reason"].lower()


# -------- public GET — expired --------------------------------------

def test_public_get_expired_token_returns_410(client):
    from app.db import transaction
    from app.services.intake import reset_rate_limit_for_tests
    issued = _issue(client, headers=ADMIN1).json()
    # Force the row's expires_at into the past.
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(
        timespec="seconds"
    )
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE intake_tokens SET expires_at = :p "
                "WHERE id = :id"
            ),
            {"p": past, "id": issued["id"]},
        )
    reset_rate_limit_for_tests()
    r = client.get(f"/intakes/{issued['token']}")
    assert r.status_code == 410
    assert r.json()["detail"]["error_code"] == "intake_token_expired"


# -------- public GET — used (single-use) ----------------------------

def test_public_get_used_token_returns_410(client):
    from app.services.intake import reset_rate_limit_for_tests
    issued = _issue(client, headers=ADMIN1).json()
    reset_rate_limit_for_tests()
    sub = client.post(
        f"/intakes/{issued['token']}/submit",
        json={"patient_name": "Pat Doe", "reason_for_visit": "Eye pain",
              "consent": True},
    )
    assert sub.status_code == 201
    reset_rate_limit_for_tests()
    # A second GET on the same token must now be 410 (used).
    r = client.get(f"/intakes/{issued['token']}")
    assert r.status_code == 410
    assert r.json()["detail"]["error_code"] == "intake_token_used"


# -------- rate limiting --------------------------------------------

def test_public_get_rate_limit_returns_429_after_threshold(client):
    from app.services.intake import (
        PUBLIC_GET_LIMIT_PER_MINUTE,
        reset_rate_limit_for_tests,
    )
    issued = _issue(client, headers=ADMIN1).json()
    reset_rate_limit_for_tests()
    # The first PUBLIC_GET_LIMIT_PER_MINUTE requests succeed; the
    # next one is 429.
    last_status = None
    for _ in range(PUBLIC_GET_LIMIT_PER_MINUTE):
        last_status = client.get(f"/intakes/{issued['token']}").status_code
    assert last_status == 200
    r = client.get(f"/intakes/{issued['token']}")
    assert r.status_code == 429
    assert r.json()["detail"]["error_code"] == "rate_limited"
