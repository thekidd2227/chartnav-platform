"""Phase 19 — transcript-to-note workflow.

Covers:
- creating encounter inputs (text_paste / audio_upload / manual_entry)
- input status defaults (text_paste → completed; audio_upload → queued)
- listing inputs + org scoping
- generating a note from an input → creates extracted_findings + note v1
- regeneration creates v2 without destroying v1
- provider PATCH flips status to `revised` and `generated_by=manual`
- submit-for-review enforces transitions
- sign requires clinician/admin, stamps signed_at + signed_by_user_id
- reviewer role cannot sign
- exported state is distinct from signed
- audit events recorded for generate / submit / sign / export
- signed note is immutable (PATCH → 409 note_immutable)
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------

def test_create_text_paste_input_is_completed_by_default(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["encounter_id"] == 1
    assert row["input_type"] == "text_paste"
    assert row["processing_status"] == "completed"
    assert "blurry vision" in row["transcript_text"]


def test_audio_upload_defaults_to_queued(client):
    r = client.post(
        "/encounters/1/inputs",
        json={
            "input_type": "audio_upload",
            "source_metadata": {"filename": "rec.wav", "duration_s": 180},
        },
        headers=CLIN1,
    )
    assert r.status_code == 201
    assert r.json()["processing_status"] == "queued"


def test_transcript_required_for_text_input(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste"},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "transcript_required"


def test_reviewer_cannot_create_input(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "x"},
        headers=REV1,
    )
    assert r.status_code == 403


def test_cross_org_create_input_is_404(client):
    # CLIN2 tries to ingest to org-1 encounter — looks like 404 to them.
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "x"},
        headers=CLIN2,
    )
    assert r.status_code == 404


def test_list_inputs(client):
    client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=CLIN1,
    )
    r = client.get("/encounters/1/inputs", headers=CLIN1)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    assert items[0]["encounter_id"] == 1


# ---------------------------------------------------------------------
# generation + versioning
# ---------------------------------------------------------------------

def _ingest_and_generate(client, encounter_id=1):
    client.post(
        f"/encounters/{encounter_id}/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=CLIN1,
    )
    r = client.post(
        f"/encounters/{encounter_id}/notes/generate",
        json={},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_generate_creates_findings_and_note_v1(client):
    body = _ingest_and_generate(client)
    assert "note" in body and "findings" in body
    note = body["note"]
    findings = body["findings"]

    assert note["version_number"] == 1
    assert note["draft_status"] == "draft"
    assert note["generated_by"] == "system"
    # SQLite returns 1/0 for booleans; Postgres returns True/False.
    assert bool(note["provider_review_required"]) is True
    assert note["extracted_findings_id"] == findings["id"]
    assert note["source_input_id"] is not None
    assert "SUBJECTIVE" in note["note_text"]
    assert "POSTERIOR CAPSULAR" in note["note_text"].upper() or \
           "capsular" in note["note_text"].lower()

    # Extraction actually picked up numbers from the transcript.
    assert findings["visual_acuity_od"] == "20/40"
    assert findings["visual_acuity_os"] == "20/20"
    assert findings["iop_od"] == "15"
    assert findings["iop_os"] == "17"
    assert findings["chief_complaint"].lower().startswith("blurry")
    assert findings["extraction_confidence"] in {"high", "medium", "low"}
    assert isinstance(findings["structured_json"], dict)
    assert findings["structured_json"].get("follow_up_interval")

    # Missing-data flags should be a list (possibly empty on a rich
    # transcript — what matters is the contract type).
    assert isinstance(note["missing_data_flags"], list)


def test_regeneration_creates_v2_and_preserves_v1(client):
    _ingest_and_generate(client)
    # Second ingest + generate → v2, v1 stays.
    client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT + "\nUpdated."},
        headers=CLIN1,
    )
    r = client.post("/encounters/1/notes/generate", json={}, headers=CLIN1)
    assert r.status_code == 201
    v2 = r.json()["note"]
    assert v2["version_number"] == 2

    listing = client.get("/encounters/1/notes", headers=CLIN1).json()
    assert [n["version_number"] for n in listing] == [2, 1]


def test_generate_requires_completed_input(client):
    # Only audio_upload on this encounter, still queued — generate 409.
    client.post(
        "/encounters/1/inputs",
        json={"input_type": "audio_upload"},
        headers=CLIN1,
    )
    r = client.post("/encounters/1/notes/generate", json={}, headers=CLIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "no_completed_input"


def test_missing_flags_emitted_for_sparse_transcript(client):
    client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "Patient here."},
        headers=CLIN1,
    )
    r = client.post("/encounters/1/notes/generate", json={}, headers=CLIN1)
    note = r.json()["note"]
    assert "visual_acuity_missing" in note["missing_data_flags"]
    assert "iop_missing" in note["missing_data_flags"]
    assert "plan_missing" in note["missing_data_flags"]


# ---------------------------------------------------------------------
# provider workflow
# ---------------------------------------------------------------------

def test_provider_edit_flips_to_revised_and_manual(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.patch(
        f"/note-versions/{note_id}",
        json={"note_text": "Edited by provider.\nFinal pass."},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["draft_status"] == "revised"
    assert updated["generated_by"] == "manual"
    assert "Edited by provider" in updated["note_text"]


def test_submit_for_review_transitions(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.post(
        f"/note-versions/{note_id}/submit-for-review",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["draft_status"] == "provider_review"


def test_reviewer_cannot_sign(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.post(f"/note-versions/{note_id}/sign", headers=REV1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_sign"


def test_clinician_can_sign_and_stamps_metadata(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    signed = r.json()
    assert signed["draft_status"] == "signed"
    assert signed["signed_at"] is not None
    assert signed["signed_by_user_id"] is not None


def test_signed_note_is_immutable(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    r = client.patch(
        f"/note-versions/{note_id}",
        json={"note_text": "should fail"},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "note_immutable"


def test_export_only_from_signed(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    # Cannot export from draft.
    r = client.post(f"/note-versions/{note_id}/export", headers=CLIN1)
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "note_not_signed"
    # Sign then export.
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    r = client.post(f"/note-versions/{note_id}/export", headers=CLIN1)
    assert r.status_code == 200
    exp = r.json()
    assert exp["draft_status"] == "exported"
    assert exp["exported_at"] is not None


def test_cross_org_note_read_is_404(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.get(f"/note-versions/{note_id}", headers=CLIN2)
    assert r.status_code == 404


def test_get_note_version_returns_note_and_findings(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.get(f"/note-versions/{note_id}", headers=CLIN1)
    assert r.status_code == 200
    data = r.json()
    assert data["note"]["id"] == note_id
    assert data["findings"] is not None
    assert data["findings"]["visual_acuity_od"] == "20/40"


# ---------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------

def test_generate_sign_export_emit_audit_events(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    client.post(f"/note-versions/{note_id}/export", headers=CLIN1)

    r = client.get(
        "/security-audit-events?limit=200",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    body = r.json()
    items = body["items"] if isinstance(body, dict) else body
    types = [ev["event_type"] for ev in items]
    assert "note_version_generated" in types
    assert "note_version_signed" in types
    assert "note_version_exported" in types
    assert "encounter_input_created" in types
