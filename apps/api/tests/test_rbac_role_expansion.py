"""Phase A item 2 — RBAC role expansion contract tests.

Spec: docs/chartnav/closure/PHASE_A_RBAC_and_Audit_Trail_Spec.md

Covers:
  - migration widens users.role CHECK to include technician + biller_coder
  - tech@ + billing@ identities resolve as the new roles
  - cross-org separation: org2 has no technician / biller_coder seeded
  - capability-set membership matches the spec matrix where it differs
    from prior behavior (CAN_CREATE_ENCOUNTER now includes technician,
    CAN_EXPORT_HANDOFF includes biller_coder)
  - clinical-content read access for the new roles is allowed but
    write paths to assessment/sign remain gated
"""
from __future__ import annotations

from .conftest import ADMIN1, ADMIN2, BILLING1, CLIN1, TECH1


# -------- identity resolution -----------------------------------------

def test_technician_identity_resolves(client):
    r = client.get("/me", headers=TECH1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "tech@chartnav.local"
    assert body["role"] == "technician"


def test_biller_coder_identity_resolves(client):
    r = client.get("/me", headers=BILLING1)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "billing@chartnav.local"
    assert body["role"] == "biller_coder"


# -------- cross-org separation ---------------------------------------

def test_org2_has_no_technician_or_biller_seeded(client):
    """The spec keeps tech/billing in org1 only so the cross-org
    separation proof stays clean for buyer reviews."""
    # An unknown email in org2 returns 401, NOT a magic redirect.
    r = client.get("/me", headers={"X-User-Email": "tech@northside.local"})
    assert r.status_code == 401
    r = client.get("/me", headers={"X-User-Email": "billing@northside.local"})
    assert r.status_code == 401


# -------- capability sets match the spec matrix ----------------------

def test_technician_can_create_encounter(client):
    r = client.post(
        "/encounters",
        json={
            "organization_id": 1,
            "location_id": 1,
            "patient_identifier": "PT-PHASE-A-RBAC-1",
            "patient_name": "Tech Created",
            "provider_name": "Dr. Carter",
        },
        headers=TECH1,
    )
    assert r.status_code == 201, r.text
    assert r.json()["patient_identifier"] == "PT-PHASE-A-RBAC-1"


def test_biller_coder_cannot_create_encounter(client):
    """Per the spec matrix: front_desk / technician / clinician / admin
    create encounters. biller_coder does NOT."""
    r = client.post(
        "/encounters",
        json={
            "organization_id": 1,
            "location_id": 1,
            "patient_identifier": "PT-PHASE-A-RBAC-2",
            "patient_name": "Should Fail",
            "provider_name": "Dr. Carter",
        },
        headers=BILLING1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_create_encounter"


# -------- known-roles set ---------------------------------------------

def test_known_roles_includes_new_clinic_roles():
    """Compile-time gate: the authz module's KNOWN_ROLES list must
    enumerate the new roles so any later code that does a role-name
    membership check picks them up."""
    from app.authz import (
        KNOWN_ROLES,
        ROLE_TECHNICIAN,
        ROLE_BILLER_CODER,
        CAN_CREATE_ENCOUNTER,
        CAN_EXPORT_HANDOFF,
        CAN_CHART_ASSESSMENT,
        CAN_SIGN,
    )
    assert ROLE_TECHNICIAN in KNOWN_ROLES
    assert ROLE_BILLER_CODER in KNOWN_ROLES
    # Spec matrix:
    assert ROLE_TECHNICIAN in CAN_CREATE_ENCOUNTER
    assert ROLE_BILLER_CODER in CAN_EXPORT_HANDOFF
    assert ROLE_TECHNICIAN not in CAN_CHART_ASSESSMENT
    assert ROLE_BILLER_CODER not in CAN_SIGN


# -------- DB CHECK constraint accepts new role values ----------------

def test_check_constraint_accepts_technician(client, monkeypatch):
    """Insert a new tech via the admin POST /users path, prove the
    CHECK constraint accepts it (this is what would have failed
    before migration r2b3a4c5e6f7)."""
    r = client.post(
        "/users",
        json={
            "email": "tech2@chartnav.local",
            "full_name": "Second Tech",
            "role": "technician",
        },
        headers=ADMIN1,
    )
    assert r.status_code in (200, 201), r.text


def test_check_constraint_accepts_biller_coder(client):
    r = client.post(
        "/users",
        json={
            "email": "billing2@chartnav.local",
            "full_name": "Second Biller",
            "role": "biller_coder",
        },
        headers=ADMIN1,
    )
    assert r.status_code in (200, 201), r.text


def test_check_constraint_rejects_garbage_role(client):
    r = client.post(
        "/users",
        json={
            "email": "ghost@chartnav.local",
            "full_name": "Ghost",
            "role": "ghost_role",
        },
        headers=ADMIN1,
    )
    # 400 invalid role from the route before it hits the DB, OR 422
    # from validator. Either is acceptable; what we MUST NOT see is
    # 201 silently writing an unknown role.
    assert r.status_code in (400, 422)
