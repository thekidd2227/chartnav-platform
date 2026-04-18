"""Native clinical layer (phase 18): patients + providers + encounter linkage.

Covers:
- GET /patients / POST /patients CRUD + RBAC + org scoping + search
- GET /providers / POST /providers CRUD + RBAC + org scoping + NPI validation
- duplicate (org, patient_identifier) → 409 patient_identifier_conflict
- duplicate NPI → 409 npi_conflict
- encounters table carries patient_id + provider_id after migration + seed
- standalone mode persists patient/provider linkage end-to-end
- integrated_readthrough blocks native write endpoints with a clear error code
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


# ---------------------------------------------------------------------
# Seed + migration
# ---------------------------------------------------------------------

def test_migration_and_seed_populate_native_clinical_rows(client):
    r = client.get("/patients", headers=ADMIN1)
    assert r.status_code == 200, r.text
    patients = r.json()
    assert len(patients) == 2
    ids = {p["patient_identifier"] for p in patients}
    assert ids == {"PT-1001", "PT-1002"}

    r = client.get("/providers", headers=ADMIN1)
    assert r.status_code == 200, r.text
    providers = r.json()
    assert {p["display_name"] for p in providers} == {"Dr. Carter", "Dr. Patel"}
    # NPI format round-trip.
    carter = next(p for p in providers if p["display_name"] == "Dr. Carter")
    assert carter["npi"] == "1234567893"


def test_seed_links_encounters_to_native_patient_provider(client):
    r = client.get("/encounters", headers=ADMIN1)
    assert r.status_code == 200
    encs = r.json()
    assert len(encs) == 2
    # Both should have patient_id + provider_id populated.
    for e in encs:
        assert e.get("patient_id"), f"missing patient_id: {e}"
        assert e.get("provider_id"), f"missing provider_id: {e}"


# ---------------------------------------------------------------------
# Patients CRUD
# ---------------------------------------------------------------------

def test_admin_can_create_patient(client):
    body = {
        "patient_identifier": "PT-3001",
        "first_name": "Alex",
        "last_name": "Nguyen",
        "date_of_birth": "1990-01-15",
        "sex_at_birth": "male",
    }
    r = client.post("/patients", json=body, headers=ADMIN1)
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["organization_id"] == 1
    assert row["first_name"] == "Alex"
    assert row["is_active"] in (1, True)


def test_clinician_can_create_patient(client):
    body = {
        "patient_identifier": "PT-3002",
        "first_name": "Sam",
        "last_name": "Okafor",
    }
    r = client.post("/patients", json=body, headers=CLIN1)
    assert r.status_code == 201, r.text


def test_reviewer_cannot_create_patient(client):
    body = {
        "patient_identifier": "PT-3003",
        "first_name": "Z",
        "last_name": "Z",
    }
    r = client.post("/patients", json=body, headers=REV1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


def test_patient_identifier_conflict(client):
    body = {
        "patient_identifier": "PT-1001",  # already seeded
        "first_name": "Dup",
        "last_name": "Dup",
    }
    r = client.post("/patients", json=body, headers=ADMIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "patient_identifier_conflict"


def test_patient_list_search_and_scoping(client):
    r = client.get("/patients?q=Morgan", headers=ADMIN1)
    assert r.status_code == 200
    names = [p["first_name"] for p in r.json()]
    assert names == ["Morgan"]

    # Cross-org isolation: ADMIN2 sees only Priya, never Morgan/Jordan.
    r = client.get("/patients", headers=ADMIN2)
    assert r.status_code == 200
    ids = [p["patient_identifier"] for p in r.json()]
    assert ids == ["PT-2001"]


def test_patients_unauth(client):
    r = client.get("/patients")
    assert r.status_code == 401


# ---------------------------------------------------------------------
# Providers CRUD
# ---------------------------------------------------------------------

def test_admin_can_create_provider(client):
    body = {
        "display_name": "Dr. Khan",
        "npi": "1740388693",
        "specialty": "Retina",
    }
    r = client.post("/providers", json=body, headers=ADMIN1)
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["organization_id"] == 1
    assert row["npi"] == "1740388693"


def test_clinician_cannot_create_provider(client):
    body = {"display_name": "Dr. Not-Allowed"}
    r = client.post("/providers", json=body, headers=CLIN1)
    assert r.status_code == 403


def test_invalid_npi_rejected(client):
    body = {"display_name": "Dr. Bad NPI", "npi": "123"}
    r = client.post("/providers", json=body, headers=ADMIN1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_npi"


def test_duplicate_npi_conflict(client):
    body = {"display_name": "Dr. Second", "npi": "1234567893"}  # Dr. Carter's NPI
    r = client.post("/providers", json=body, headers=ADMIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "npi_conflict"


def test_provider_list_scoping(client):
    r = client.get("/providers", headers=ADMIN2)
    assert r.status_code == 200
    names = [p["display_name"] for p in r.json()]
    assert names == ["Dr. Ahmed"]


# ---------------------------------------------------------------------
# Integrated mode semantics
# ---------------------------------------------------------------------

def test_readthrough_mode_rejects_native_writes(client, monkeypatch):
    """In integrated_readthrough, POST /patients returns
    409 native_write_disabled_in_integrated_mode."""
    import importlib
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "integrated_readthrough")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "stub")

    # Reload config so the route re-reads the new mode.
    import app.config
    importlib.reload(app.config)

    body = {
        "patient_identifier": "PT-NOWRITE",
        "first_name": "No",
        "last_name": "Write",
    }
    r = client.post("/patients", json=body, headers=ADMIN1)
    assert r.status_code == 409
    assert (
        r.json()["detail"]["error_code"]
        == "native_write_disabled_in_integrated_mode"
    )

    # Clean up the reload so other tests see standalone again.
    monkeypatch.setenv("CHARTNAV_PLATFORM_MODE", "standalone")
    monkeypatch.setenv("CHARTNAV_INTEGRATION_ADAPTER", "native")
    importlib.reload(app.config)
