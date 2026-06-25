"""Patient chart foundation (reconciled, mainline-wins).

Covers the patient-detail surface that backs the PatientChart UI:
- GET /patients/{id}                — extended demographics + cross-org 404
- PATCH /patients/{id}              — admin/clinician edit, reviewer 403,
                                      MRN/whitelist enforcement, insurance JSON
- GET /patients/{id}/encounters     — patient-scoped list + cross-org 404
- GET /patients/{id}/chart-sections — registry payload shape
- audit events on view + update

Retinal-diagram artifact behavior is owned by the mainline contract test
`tests/test_eye_diagrams.py` (the `/patients/{id}/eye-diagrams` API on
`chart_artifacts.drawing_json`). The earlier stash's `vector_json`
`/artifacts` API was superseded and intentionally removed in the
reconciliation (see docs/engineering/patient-chart-retina-reconciliation-matrix.md).
"""
from __future__ import annotations

import sqlite3


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _patient_id(client, headers, identifier: str) -> int:
    rows = client.get("/patients", headers=headers).json()
    return next(p["id"] for p in rows if p["patient_identifier"] == identifier)


def _audit_event_types(test_db) -> list[str]:
    conn = sqlite3.connect(test_db)
    try:
        return [
            r[0]
            for r in conn.execute(
                "SELECT event_type FROM security_audit_events ORDER BY id"
            ).fetchall()
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------
# GET /patients/{id}
# ---------------------------------------------------------------------

def test_get_patient_returns_extended_demographics(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == pid
    assert body["patient_identifier"] == "PT-1001"
    for key in (
        "middle_name", "preferred_name", "display_name", "pronouns",
        "gender_identity", "preferred_language", "race", "ethnicity",
        "email", "phone",
        "address_line1", "address_city", "address_state", "address_postal_code",
        "emergency_contact_name", "emergency_contact_phone",
        "insurance_metadata", "updated_at",
    ):
        assert key in body, f"missing field {key!r}"


def test_get_patient_cross_org_404(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "patient_not_found"


def test_get_patient_unknown_404(client):
    r = client.get("/patients/999999", headers=ADMIN1)
    assert r.status_code == 404


# ---------------------------------------------------------------------
# PATCH /patients/{id}
# ---------------------------------------------------------------------

def test_patch_patient_admin_can_edit(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.patch(
        f"/patients/{pid}",
        json={
            "email": "morgan@example.com",
            "phone": "+1-555-0100",
            "preferred_language": "en",
            "pronouns": "she/her",
            "address_line1": "123 Vision Way",
            "address_city": "Austin",
            "address_state": "TX",
            "address_postal_code": "78701",
            "emergency_contact_name": "Pat Lee",
            "emergency_contact_phone": "+1-555-0199",
            "emergency_contact_relationship": "spouse",
            "insurance_metadata": {"payer": "Acme", "member_id": "X-1"},
        },
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "morgan@example.com"
    assert body["pronouns"] == "she/her"
    assert body["insurance_metadata"] == {"payer": "Acme", "member_id": "X-1"}
    assert body["updated_at"]


def test_patch_patient_clinician_allowed(client):
    pid = _patient_id(client, CLIN1, "PT-1001")
    r = client.patch(
        f"/patients/{pid}", json={"phone": "+1-555-0200"}, headers=CLIN1
    )
    assert r.status_code == 200
    assert r.json()["phone"] == "+1-555-0200"


def test_patch_patient_reviewer_403(client):
    pid = _patient_id(client, REV1, "PT-1001")
    r = client.patch(f"/patients/{pid}", json={"phone": "x"}, headers=REV1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


def test_patch_patient_cross_org_404(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.patch(f"/patients/{pid}", json={"phone": "x"}, headers=ADMIN2)
    assert r.status_code == 404


def test_patch_patient_does_not_allow_mrn_change(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    # Non-whitelisted fields are dropped (model ignores them, then the
    # whitelist filters); MRN and external linkage must be unchanged.
    r = client.patch(
        f"/patients/{pid}",
        json={"patient_identifier": "PT-9999", "external_ref": "mallory"},
        headers=ADMIN1,
    )
    assert r.status_code == 200
    assert r.json()["patient_identifier"] == "PT-1001"
    assert r.json()["external_ref"] is None


def test_patch_patient_invalid_insurance_metadata(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.patch(
        f"/patients/{pid}",
        json={"insurance_metadata": "not-a-json-object"},
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_insurance_metadata"


# ---------------------------------------------------------------------
# GET /patients/{id}/encounters
# ---------------------------------------------------------------------

def test_list_patient_encounters_scoped(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}/encounters", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert all(e["patient_id"] == pid for e in body)
    assert r.headers["X-Total-Count"] == "1"


def test_list_patient_encounters_cross_org_404(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}/encounters", headers=ADMIN2)
    assert r.status_code == 404


# ---------------------------------------------------------------------
# GET /patients/{id}/chart-sections
# ---------------------------------------------------------------------

def test_chart_sections_registry_shape(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}/chart-sections", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["patient_id"] == pid
    sections = body["sections"]
    keys = [s["key"] for s in sections]
    for required in (
        "overview", "encounters", "allergies", "medications", "labs",
        "radiology", "orders", "documents", "consults", "isolation",
        "eye_diagrams",
    ):
        assert required in keys, f"missing chart section {required}"
    for s in sections:
        assert {"key", "label", "status", "description"} <= set(s.keys())
        assert s["status"] in {"active", "placeholder", "unavailable"}
    by_key = {s["key"]: s for s in sections}
    assert by_key["overview"]["status"] == "active"
    assert by_key["encounters"]["status"] == "active"
    assert by_key["eye_diagrams"]["status"] == "active"
    assert by_key["medications"]["status"] == "placeholder"


def test_chart_sections_cross_org_404(client):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    r = client.get(f"/patients/{pid}/chart-sections", headers=ADMIN2)
    assert r.status_code == 404


# ---------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------

def test_audit_records_view_and_update(client, test_db):
    pid = _patient_id(client, ADMIN1, "PT-1001")
    client.get(f"/patients/{pid}", headers=ADMIN1)
    client.patch(f"/patients/{pid}", json={"phone": "+1-555-0123"}, headers=ADMIN1)
    types = _audit_event_types(test_db)
    for required in ("patient_viewed", "patient_updated"):
        assert required in types, f"missing audit event: {required} in {types}"
