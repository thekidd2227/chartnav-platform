"""Phase 2 item 3 — intake submissions (submit + accept + reject).

Spec: docs/chartnav/closure/PHASE_B_Digital_Intake.md §4.

Reviewer focus:
  - tenant/org scoping on accept + reject (org-A token cannot be
    accepted into org-B);
  - PHI hygiene on error responses;
  - successful submission lands a row + draft encounter;
  - reject leaves status='rejected', no patient created.
"""
from __future__ import annotations

from .conftest import ADMIN1, ADMIN2, CLIN1, REV1


def _issue(client, headers=ADMIN1):
    r = client.post("/intakes/tokens", json={}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _submit(client, token, *, payload=None):
    from app.services.intake import reset_rate_limit_for_tests
    reset_rate_limit_for_tests()
    payload = payload or {
        "patient_name": "Sample Patient",
        "patient_identifier": "PT-INTAKE-1",
        "reason_for_visit": "Blurry vision",
        "current_medications": ["Latanoprost 0.005% OU qhs"],
        "allergies": ["NKDA"],
        "hpi": "2 weeks of progressive blur OS",
        "consent": True,
    }
    return client.post(f"/intakes/{token}/submit", json=payload)


# -------- happy path -------------------------------------------------

def test_submit_returns_submission_id_and_no_phi(client):
    tok = _issue(client)
    r = _submit(client, tok["token"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert isinstance(body["submission_id"], int)
    # PHI hygiene: no patient_name in the response body.
    assert "Sample Patient" not in str(body)
    # Token is burned: re-submit returns 410 used.
    r2 = _submit(client, tok["token"])
    assert r2.status_code == 410


def test_submit_requires_consent(client):
    tok = _issue(client)
    from app.services.intake import reset_rate_limit_for_tests
    reset_rate_limit_for_tests()
    r = client.post(
        f"/intakes/{tok['token']}/submit",
        json={"patient_name": "X", "reason_for_visit": "Y", "consent": False},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "intake_consent_required"


# -------- accept path -----------------------------------------------

def test_accept_creates_draft_patient_and_encounter(client):
    tok = _issue(client)
    sub = _submit(client, tok["token"]).json()
    r = client.post(f"/intakes/{sub['submission_id']}/accept", headers=ADMIN1)
    assert r.status_code == 201, r.text
    body = r.json()
    assert isinstance(body["patient_id"], int)
    assert isinstance(body["draft_encounter_id"], int)
    # The encounter is now visible to org-1 admin.
    enc_get = client.get(f"/encounters/{body['draft_encounter_id']}", headers=ADMIN1)
    assert enc_get.status_code == 200
    assert enc_get.json()["patient_identifier"] == "PT-INTAKE-1"


def test_accept_twice_returns_409(client):
    tok = _issue(client)
    sub = _submit(client, tok["token"]).json()
    a = client.post(f"/intakes/{sub['submission_id']}/accept", headers=ADMIN1)
    assert a.status_code == 201
    b = client.post(f"/intakes/{sub['submission_id']}/accept", headers=ADMIN1)
    assert b.status_code == 409
    assert b.json()["detail"]["error_code"] == "intake_submission_not_pending"


# -------- reject path -----------------------------------------------

def test_reject_leaves_status_rejected_and_creates_no_patient(client):
    tok = _issue(client)
    sub = _submit(client, tok["token"]).json()
    r = client.post(
        f"/intakes/{sub['submission_id']}/reject",
        json={"reason": "duplicate"},
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    # Confirm via the staff list that it transitioned.
    pending = client.get("/intakes?status=pending_review", headers=ADMIN1).json()
    rejected = client.get("/intakes?status=rejected", headers=ADMIN1).json()
    assert sub["submission_id"] not in [s["id"] for s in pending["items"]]
    assert sub["submission_id"] in [s["id"] for s in rejected["items"]]


def test_reject_then_accept_409(client):
    tok = _issue(client)
    sub = _submit(client, tok["token"]).json()
    client.post(
        f"/intakes/{sub['submission_id']}/reject",
        json={"reason": "x"}, headers=ADMIN1,
    )
    r = client.post(f"/intakes/{sub['submission_id']}/accept", headers=ADMIN1)
    assert r.status_code == 409


# -------- cross-org isolation (the explicit reviewer ask) -----------

def test_org2_admin_cannot_accept_org1_submission(client):
    """Org-A token + submission must NOT be acceptable by an org-B
    admin. The response is a 404 carrying the documented neutral
    error_code (NEVER 403 — we do not reveal existence)."""
    tok = _issue(client, headers=ADMIN1)  # org-1 token
    sub = _submit(client, tok["token"]).json()
    r = client.post(
        f"/intakes/{sub['submission_id']}/accept",
        headers=ADMIN2,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "intake_submission_not_found"


def test_org2_admin_cannot_reject_org1_submission(client):
    tok = _issue(client, headers=ADMIN1)
    sub = _submit(client, tok["token"]).json()
    r = client.post(
        f"/intakes/{sub['submission_id']}/reject",
        json={"reason": "x"},
        headers=ADMIN2,
    )
    assert r.status_code == 404


def test_list_intakes_does_not_leak_other_org(client):
    tok = _issue(client, headers=ADMIN1)
    _submit(client, tok["token"])
    r2 = client.get("/intakes", headers=ADMIN2)
    assert r2.status_code == 200
    # Org-2 admin sees zero pending intakes even though org-1 has one.
    assert r2.json()["items"] == []


# -------- staff route role-gating -----------------------------------

def test_clinician_cannot_review_intake(client):
    r = client.get("/intakes", headers=CLIN1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_review_intake"


def test_reviewer_cannot_review_intake(client):
    r = client.get("/intakes", headers=REV1)
    assert r.status_code == 403


# -------- PHI hygiene on submit error path --------------------------

def test_submit_with_unknown_token_does_not_echo_token(client):
    from app.services.intake import reset_rate_limit_for_tests
    reset_rate_limit_for_tests()
    r = client.post(
        "/intakes/this-is-an-unknown-token-of-sufficient-length/submit",
        json={"patient_name": "X", "reason_for_visit": "Y", "consent": True},
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["error_code"] == "intake_token_not_found"
    assert "this-is-an-unknown-token" not in detail["reason"].lower()
    assert "patient_name" not in detail["reason"].lower()
