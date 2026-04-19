"""Phase 25 — signed-note artifact endpoint.

Covers the GET /note-versions/{id}/artifact surface:

- unsigned note → 409 `note_not_signed`
- cross-org artifact request → 404
- signed note default format → canonical chartnav.v1.json, all three
  tiers present (transcript_source, extracted_findings, note),
  edit_applied false when the clinician did not change the text,
  signature content hash deterministic
- provider edit → `edit_applied=true` and generated_draft differs
  from clinician_final
- text format → plain text body with metadata header + hash
- FHIR format → DocumentReference shape with base64 content
- unsupported format → 400 `unsupported_artifact_format`
- audit event `note_version_artifact_issued` is recorded
"""

from __future__ import annotations

import base64
import json


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


TRANSCRIPT = """
Chief complaint: blurry vision right eye for 3 weeks.
History: 64yo female, h/o cataract surgery OD 2 years ago.
OD 20/40, OS 20/20.
IOP 15/17.
Diagnosis: posterior capsular opacification right eye.
Plan: YAG capsulotomy OD.
Follow-up in 4 weeks.
""".strip()


def _ingest(client) -> dict:
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _generate(client, input_id: int) -> dict:
    r = client.post(
        "/encounters/1/notes/generate",
        json={"input_id": input_id},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _sign(client, note_id: int) -> dict:
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------
# gating
# ---------------------------------------------------------------------

def test_unsigned_artifact_is_refused(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]

    r = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["error_code"] == "note_not_signed"


def test_cross_org_artifact_is_404(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "note_not_found"


def test_unsupported_format_is_400(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r = client.get(
        f"/note-versions/{note_id}/artifact?format=xml",
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "unsupported_artifact_format"


# ---------------------------------------------------------------------
# canonical JSON
# ---------------------------------------------------------------------

def test_signed_artifact_json_default(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    assert r.status_code == 200, r.text
    assert r.headers.get("X-ChartNav-Artifact-Variant") == "chartnav.v1.json"
    assert r.headers.get("X-ChartNav-Artifact-Type") == "chartnav.signed_note.v1"
    a = r.json()

    assert a["artifact_version"] == 1
    assert a["artifact_type"] == "chartnav.signed_note.v1"

    # Three tiers present:
    assert a["transcript_source"] is not None
    assert a["transcript_source"]["input_id"] == inp["id"]
    assert "blurry vision" in a["transcript_source"]["transcript_excerpt"]
    assert a["transcript_source"]["transcript_truncated"] is False

    assert a["extracted_findings"] is not None
    assert a["extracted_findings"]["visual_acuity"]["od"] == "20/40"
    assert a["extracted_findings"]["visual_acuity"]["os"] == "20/20"

    assert a["note"]["id"] == note_id
    assert a["note"]["draft_status"] == "signed"
    assert a["note"]["version_number"] == 1
    # No edit → generated_draft equals clinician_final.
    assert a["note"]["edit_applied"] is False
    assert a["note"]["generated_draft"] == a["note"]["clinician_final"]

    # Signature fields populated.
    sig = a["signature"]
    assert sig["signed_at"] is not None
    assert sig["signed_by_email"] == "clin@chartnav.local"
    assert sig["signed_by_user_id"] is not None
    assert len(sig["content_hash_sha256"]) == 64  # hex sha256

    # Export envelope stamped with caller.
    env = a["export_envelope"]
    assert env["issued_by_email"] == "clin@chartnav.local"
    assert env["format_variant"] == "chartnav.v1.json"
    assert env["mime_type"] == "application/vnd.chartnav.signed-note+json"


def test_edited_note_marks_edit_applied(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]

    # Provider edits before signing.
    r = client.patch(
        f"/note-versions/{note_id}",
        json={"note_text": "Final pass. Edited by provider before signing."},
        headers=CLIN1,
    )
    assert r.status_code == 200
    _sign(client, note_id)

    r = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    a = r.json()
    assert a["note"]["edit_applied"] is True
    assert a["note"]["clinician_final"].startswith("Final pass.")
    # Generated draft is the pre-edit text that the orchestrator
    # snapshotted; SOAP body from the deterministic generator starts
    # with SUBJECTIVE.
    assert "SUBJECTIVE" in a["note"]["generated_draft"]


# ---------------------------------------------------------------------
# text variant
# ---------------------------------------------------------------------

def test_text_format_renders_plain_text_with_metadata(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r = client.get(
        f"/note-versions/{note_id}/artifact?format=text",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers.get("X-ChartNav-Artifact-Variant") == "chartnav.v1.text"
    txt = r.text
    # Header lines.
    assert "ChartNav Signed Note" in txt
    assert "Signed by: clin@chartnav.local" in txt
    assert "Content hash (sha256):" in txt
    # Body from the SOAP generator.
    assert "SUBJECTIVE" in txt
    assert "— end of note body —" in txt


# ---------------------------------------------------------------------
# FHIR variant
# ---------------------------------------------------------------------

def test_fhir_format_renders_document_reference(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r = client.get(
        f"/note-versions/{note_id}/artifact?format=fhir",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/fhir+json")
    assert r.headers.get("X-ChartNav-Artifact-Variant") == "fhir.DocumentReference.v1"
    doc = r.json()

    assert doc["resourceType"] == "DocumentReference"
    assert doc["status"] == "current"
    assert doc["docStatus"] == "final"

    # Identifier carries the ChartNav URN scheme.
    ids = doc["identifier"]
    assert ids[0]["system"] == "urn:chartnav:note"
    assert ids[0]["value"] == f"{note_id}:v1"

    # LOINC progress-note typing.
    coding = doc["type"]["coding"][0]
    assert coding["system"] == "http://loinc.org"
    assert coding["code"] == "11506-3"

    # Content is inlined, base64-encoded, and round-trips.
    attachment = doc["content"][0]["attachment"]
    assert attachment["contentType"].startswith("text/plain")
    decoded = base64.b64decode(attachment["data"]).decode("utf-8")
    assert "SUBJECTIVE" in decoded

    # Hash is present and matches the signature hash inside the
    # canonical artifact.
    r2 = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    assert attachment["hash"] == r2.json()["signature"]["content_hash_sha256"]

    # Meta tags the provenance.
    assert doc["meta"]["source"] == "chartnav.v1"
    tags = [t["code"] for t in doc["meta"]["tag"]]
    assert "chartnav.signed_note.v1" in tags


def test_content_hash_is_deterministic(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    r1 = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    r2 = client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    h1 = r1.json()["signature"]["content_hash_sha256"]
    h2 = r2.json()["signature"]["content_hash_sha256"]
    assert h1 == h2


# ---------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------

def test_artifact_request_emits_audit_event(client):
    inp = _ingest(client)
    body = _generate(client, inp["id"])
    note_id = body["note"]["id"]
    _sign(client, note_id)

    client.get(f"/note-versions/{note_id}/artifact", headers=CLIN1)
    client.get(
        f"/note-versions/{note_id}/artifact?format=fhir",
        headers=CLIN1,
    )

    r = client.get(
        "/security-audit-events?limit=200",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    b = r.json()
    items = b["items"] if isinstance(b, dict) else b
    artifact_events = [
        ev for ev in items if ev["event_type"] == "note_version_artifact_issued"
    ]
    assert len(artifact_events) >= 2
    # Detail should record which format variant was emitted.
    details = " ".join(ev["detail"] or "" for ev in artifact_events)
    assert "format=chartnav.v1.json" in details
    assert "format=fhir.DocumentReference.v1" in details
