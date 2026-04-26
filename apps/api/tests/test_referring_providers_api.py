"""Phase 2 item 1 — referring_providers CRUD + NPI-10 validation.

Spec: docs/chartnav/closure/PHASE_B_Referring_Provider_Communication.md §4.
"""
from __future__ import annotations

from .conftest import ADMIN1, CLIN1, REV1, ADMIN2


# A small set of CMS Luhn-valid NPIs. The CMS LUHN_10 algorithm
# prefixes "80840" before the first 9 digits and checks digit 10.
# These have been computed offline so the tests do not depend on the
# implementation under test for the input data.
VALID_NPI_A = "1234567893"  # Luhn-valid 10-digit NPI
VALID_NPI_B = "1003000001"  # Luhn-valid 10-digit NPI
INVALID_NPI = "1234567890"  # not Luhn-valid


# -------- NPI validator (pure function) ------------------------------

def test_is_valid_npi10_accepts_known_good():
    from app.services.consult_letters import is_valid_npi10
    assert is_valid_npi10(VALID_NPI_A) is True
    assert is_valid_npi10(VALID_NPI_B) is True


def test_is_valid_npi10_rejects_known_bad():
    from app.services.consult_letters import is_valid_npi10
    assert is_valid_npi10(INVALID_NPI) is False
    assert is_valid_npi10("abcdefghij") is False
    assert is_valid_npi10("12345") is False
    assert is_valid_npi10("") is False


# -------- CRUD --------------------------------------------------------

def test_create_referring_provider_admin_can(client):
    r = client.post(
        "/referring-providers",
        json={
            "name": "Dr. Olivia Optometrist",
            "practice": "Sample Optometry",
            "npi_10": VALID_NPI_A,
            "email": "olivia@example.com",
        },
        headers=ADMIN1,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Dr. Olivia Optometrist"
    assert body["npi_10"] == VALID_NPI_A


def test_create_referring_provider_clinician_can(client):
    r = client.post(
        "/referring-providers",
        json={"name": "Dr. C", "npi_10": VALID_NPI_A},
        headers=CLIN1,
    )
    assert r.status_code == 201


def test_create_referring_provider_reviewer_forbidden(client):
    r = client.post(
        "/referring-providers",
        json={"name": "Dr. R", "npi_10": VALID_NPI_A},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


def test_create_referring_provider_rejects_bad_npi(client):
    r = client.post(
        "/referring-providers",
        json={"name": "Dr. Bad", "npi_10": INVALID_NPI},
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_npi_10"


def test_create_referring_provider_unique_per_org(client):
    client.post(
        "/referring-providers",
        json={"name": "Dr. Dupe", "npi_10": VALID_NPI_A},
        headers=ADMIN1,
    )
    r = client.post(
        "/referring-providers",
        json={"name": "Dr. Dupe Twice", "npi_10": VALID_NPI_A},
        headers=ADMIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "duplicate_referring_provider"


def test_list_referring_providers_org_scoped(client):
    # Create one in org1, one in org2 with the SAME npi (different orgs
    # are allowed to coexist).
    client.post(
        "/referring-providers",
        json={"name": "Dr. Org1", "npi_10": VALID_NPI_A},
        headers=ADMIN1,
    )
    client.post(
        "/referring-providers",
        json={"name": "Dr. Org2", "npi_10": VALID_NPI_A},
        headers=ADMIN2,
    )
    r1 = client.get("/referring-providers", headers=ADMIN1)
    r2 = client.get("/referring-providers", headers=ADMIN2)
    names1 = [r["name"] for r in r1.json()["items"]]
    names2 = [r["name"] for r in r2.json()["items"]]
    assert "Dr. Org1" in names1 and "Dr. Org2" not in names1
    assert "Dr. Org2" in names2 and "Dr. Org1" not in names2
