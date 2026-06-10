"""Phase 87 — FHIR R4 read-only export tests."""

from __future__ import annotations

import base64
import hashlib
import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}

FHIR_MEDIA = "application/fhir+json"


def _get(client, path, headers=CLIN1):
    return client.get(path, headers=headers)


# ---------------------------------------------------------------------------
# Patient export
# ---------------------------------------------------------------------------


def test_patient_export_returns_fhir_r4_patient_resource(client):
    r = _get(client, "/api/fhir/r4/Patient/1")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(FHIR_MEDIA)
    body = r.json()
    assert body["resourceType"] == "Patient"
    assert body["id"] == "1"
    assert body["meta"]["source"].startswith("urn:chartnav:organization:")
    assert isinstance(body["identifier"], list) and body["identifier"]
    assert body["identifier"][0]["system"] == "urn:chartnav:patient-identifier"
    assert isinstance(body["name"], list) and body["name"][0].get("text")
    assert body["gender"] in {"male", "female", "other", "unknown"}
    assert isinstance(body["active"], bool)


def test_patient_export_normalizes_gender_to_value_set(client):
    body = _get(client, "/api/fhir/r4/Patient/1").json()
    assert body["gender"] in {"male", "female", "other", "unknown"}


def test_patient_export_includes_external_ref_when_present(client):
    body = _get(client, "/api/fhir/r4/Patient/1").json()
    systems = {idn["system"] for idn in body["identifier"]}
    # external_ref is optional; if present must be a distinct identifier.
    if any(s == "urn:chartnav:external-ref" for s in systems):
        ext = [idn for idn in body["identifier"]
               if idn["system"] == "urn:chartnav:external-ref"][0]
        assert isinstance(ext["value"], str) and ext["value"]


def test_patient_export_unknown_patient_returns_404_operation_outcome(client):
    r = _get(client, "/api/fhir/r4/Patient/999999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith(FHIR_MEDIA)
    body = r.json()
    assert body["resourceType"] == "OperationOutcome"
    assert body["issue"][0]["code"] == "not-found"


def test_patient_export_cross_org_returns_404(client):
    # ADMIN2 belongs to a different organization than patient 1.
    r = _get(client, "/api/fhir/r4/Patient/1", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["resourceType"] == "OperationOutcome"


def test_patient_export_requires_authentication(client):
    r = client.get("/api/fhir/r4/Patient/1")
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Encounter export
# ---------------------------------------------------------------------------


def test_encounter_export_returns_fhir_r4_encounter_resource(client):
    r = _get(client, "/api/fhir/r4/Encounter/1")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(FHIR_MEDIA)
    body = r.json()
    assert body["resourceType"] == "Encounter"
    assert body["id"] == "1"
    assert body["status"] in {
        "planned",
        "in-progress",
        "finished",
        "cancelled",
        "unknown",
    }
    assert body["class"]["code"] == "AMB"
    assert isinstance(body["identifier"], list) and body["identifier"]


def test_encounter_export_embeds_workspace_profile_extension(client):
    body = _get(client, "/api/fhir/r4/Encounter/1").json()
    urls = {e["url"] for e in body.get("extension", [])}
    assert any(u.endswith("/workspace-profile") for u in urls)


def test_encounter_export_embeds_review_sign_lock_extension(client):
    body = _get(client, "/api/fhir/r4/Encounter/1").json()
    rsl = [
        e for e in body.get("extension", [])
        if e["url"].endswith("/review-sign-lock")
    ]
    assert len(rsl) == 1
    inner = {x["url"]: x["valueBoolean"] for x in rsl[0]["extension"]}
    assert set(inner.keys()) == {
        "vitals_signed",
        "visit_draft_signed",
        "fundus_signed",
        "all_signed",
    }
    for v in inner.values():
        assert isinstance(v, bool)


def test_encounter_export_reflects_phase_86_encounter_type_after_patch(client):
    assert (
        client.patch(
            "/api/v1/encounters/1/workspace-profile",
            headers=CLIN1,
            json={"encounter_type": "retina"},
        ).status_code
        == 200
    )
    body = _get(client, "/api/fhir/r4/Encounter/1").json()
    codes = []
    for typ in body.get("type", []):
        for c in typ.get("coding", []):
            codes.append(c.get("code"))
    assert "retina" in codes


def test_encounter_export_unknown_encounter_returns_404(client):
    r = _get(client, "/api/fhir/r4/Encounter/999999")
    assert r.status_code == 404
    assert r.json()["resourceType"] == "OperationOutcome"


def test_encounter_export_cross_org_returns_404(client):
    r = _get(client, "/api/fhir/r4/Encounter/1", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["resourceType"] == "OperationOutcome"


def test_encounter_export_requires_authentication(client):
    r = client.get("/api/fhir/r4/Encounter/1")
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# DocumentReference export
# ---------------------------------------------------------------------------


def test_document_reference_export_returns_fhir_r4_document_reference(client):
    r = _get(client, "/api/fhir/r4/DocumentReference/1")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(FHIR_MEDIA)
    body = r.json()
    assert body["resourceType"] == "DocumentReference"
    assert body["id"] == "retina-visit-packet-1"
    assert body["status"] == "current"
    assert body["docStatus"] in {"preliminary", "final"}


def test_document_reference_attachment_carries_packet_and_hash(client):
    body = _get(client, "/api/fhir/r4/DocumentReference/1").json()
    content = body["content"][0]["attachment"]
    assert content["contentType"] == "application/fhir+json"
    data_b64 = content["data"]
    blob = base64.b64decode(data_b64)
    # The attachment must be valid JSON (the packet body).
    decoded = json.loads(blob)
    assert decoded["schema_version"].startswith("chartnav.retina_visit_packet/")
    # Size matches what the adapter reported.
    assert content["size"] == len(blob)
    # Hash (base64-of-sha256-bytes) matches the recomputed digest.
    expected_hash = hashlib.sha256(blob).digest()
    assert base64.b64decode(content["hash"]) == expected_hash


def test_document_reference_packet_integrity_extension_is_consistent(client):
    body = _get(client, "/api/fhir/r4/DocumentReference/1").json()
    blob = base64.b64decode(body["content"][0]["attachment"]["data"])
    integrity = next(
        e for e in body["extension"]
        if e["url"].endswith("/packet-integrity")
    )
    fields = {x["url"]: x for x in integrity["extension"]}
    assert fields["algorithm"]["valueCode"] == "sha256"
    expected_hex = hashlib.sha256(blob).hexdigest()
    assert fields["packet-hash-hex"]["valueString"] == expected_hex
    assert fields["packet-bytes"]["valueInteger"] == len(blob)
    assert fields["packet-generated-at"]["valueDateTime"]
    assert isinstance(fields["all-signed"]["valueBoolean"], bool)


def test_document_reference_secondary_identifier_carries_packet_hash(client):
    body = _get(client, "/api/fhir/r4/DocumentReference/1").json()
    hash_idn = next(
        i for i in body["identifier"]
        if i["system"] == "urn:chartnav:packet-hash:sha256"
    )
    assert len(hash_idn["value"]) == 64  # sha256 hex length


def test_document_reference_unknown_encounter_returns_404(client):
    r = _get(client, "/api/fhir/r4/DocumentReference/999999")
    assert r.status_code == 404
    assert r.json()["resourceType"] == "OperationOutcome"


def test_document_reference_cross_org_returns_404(client):
    r = _get(client, "/api/fhir/r4/DocumentReference/1", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["resourceType"] == "OperationOutcome"


def test_document_reference_requires_authentication(client):
    r = client.get("/api/fhir/r4/DocumentReference/1")
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Read-only contract: no FHIR write routes
# ---------------------------------------------------------------------------


def test_no_fhir_post_route_exists_for_patient(client):
    r = client.post(
        "/api/fhir/r4/Patient",
        headers=CLIN1,
        json={"resourceType": "Patient"},
    )
    assert r.status_code in {404, 405}


def test_no_fhir_post_route_exists_for_encounter(client):
    r = client.post(
        "/api/fhir/r4/Encounter",
        headers=CLIN1,
        json={"resourceType": "Encounter"},
    )
    assert r.status_code in {404, 405}


def test_no_fhir_put_route_exists_for_patient(client):
    r = client.put(
        "/api/fhir/r4/Patient/1",
        headers=CLIN1,
        json={"resourceType": "Patient"},
    )
    assert r.status_code in {404, 405}


def test_no_fhir_bulk_export_route_exists(client):
    r = client.get("/api/fhir/r4/$export", headers=CLIN1)
    assert r.status_code == 404


def test_no_smart_metadata_route_exists(client):
    # SMART-on-FHIR discovery endpoint is intentionally out of scope.
    r = client.get(
        "/api/fhir/r4/.well-known/smart-configuration", headers=CLIN1
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Allowed read roles — every authenticated org member can read.
# ---------------------------------------------------------------------------


def test_patient_export_allowed_for_every_authenticated_role(client):
    for headers in (ADMIN1, CLIN1, TECH1, REV1):
        r = _get(client, "/api/fhir/r4/Patient/1", headers=headers)
        assert r.status_code == 200, (headers, r.text)


def test_encounter_export_allowed_for_every_authenticated_role(client):
    for headers in (ADMIN1, CLIN1, TECH1, REV1):
        r = _get(client, "/api/fhir/r4/Encounter/1", headers=headers)
        assert r.status_code == 200, (headers, r.text)


def test_document_reference_export_allowed_for_every_authenticated_role(client):
    for headers in (ADMIN1, CLIN1, TECH1, REV1):
        r = _get(client, "/api/fhir/r4/DocumentReference/1", headers=headers)
        assert r.status_code == 200, (headers, r.text)
