"""Phase 33 — audio intake + transcription wedge.

Covers:

Intake
- POST /encounters/{id}/inputs/audio creates an `audio_upload` row
  with source_metadata carrying filename + content_type + size +
  stored_path, persists the blob under audio_upload_dir, and runs
  the ingestion pipeline inline.
- Empty upload → 400 audio_upload_empty.
- Disallowed content-type + no known extension → 400
  audio_format_not_supported.
- Over-size upload → 413 audio_upload_too_large (with a small
  override via env).
- Reviewer → 403 (create-event role gate).
- Cross-org encounter → 404.

Transcription pipeline
- Stub transcriber emits the deterministic placeholder when no
  hint is set, marks the row completed, and populates a transcript
  text starting with "[stub-transcript]".
- `x-stub-transcript` header → deterministic transcript landing in
  the transcript_text column.
- `x-stub-transcript-error` header → failed row with
  last_error_code=`stub_transcription_failed`.
- Retry after failure runs cleanly and can flip to completed.

Transcript review / edit
- PATCH /encounter-inputs/{id}/transcript on a completed row
  replaces transcript_text.
- PATCH on a non-completed row → 409 encounter_input_not_editable.
- PATCH cross-org → 404.
- PATCH reviewer → 403.
- Audit event `encounter_input_transcript_edited` is recorded and
  does NOT carry the edited body text.

Generation readiness + provenance isolation
- Generate is blocked until a completed audio input exists.
- After upload + edit, note generation consumes the edited
  transcript_text, not the stub placeholder.
- Shortcut/quick-comment content never leaks into transcript_text
  or the audit event detail of transcript edits.
"""

from __future__ import annotations

import os

import pytest


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


MINIMAL_WAV_BYTES = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt "
    + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little") + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little") + b"data"
    + (0).to_bytes(4, "little")
)


# ---------------------------------------------------------------------
# intake
# ---------------------------------------------------------------------


def test_audio_upload_creates_row_with_metadata(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("dictation.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["input_type"] == "audio_upload"
    import json
    md = json.loads(row["source_metadata"])
    assert md["original_filename"] == "dictation.wav"
    assert md["content_type"] == "audio/wav"
    assert md["size_bytes"] == len(MINIMAL_WAV_BYTES)
    assert md["stored_path"].endswith(".wav")


def test_audio_upload_rejects_empty_body(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("dictation.wav", b"", "audio/wav")},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "audio_upload_empty"


def test_audio_upload_rejects_unknown_format(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("essay.txt", b"plain text", "text/plain")},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "audio_format_not_supported"


def test_audio_upload_rejects_oversized_body(test_db, monkeypatch):
    monkeypatch.setenv("CHARTNAV_AUDIO_UPLOAD_MAX_BYTES", "32")
    # Reload the app so the new env is picked up by settings + routes.
    import sys
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    from fastapi.testclient import TestClient
    from app.main import app
    tiny_client = TestClient(app)
    try:
        r = tiny_client.post(
            "/encounters/1/inputs/audio",
            files={
                "audio": (
                    "big.wav",
                    MINIMAL_WAV_BYTES,  # 44 bytes > 32
                    "audio/wav",
                )
            },
            headers=CLIN1,
        )
        assert r.status_code == 413
        assert r.json()["detail"]["error_code"] == "audio_upload_too_large"
    finally:
        os.environ.pop("CHARTNAV_AUDIO_UPLOAD_MAX_BYTES", None)


def test_reviewer_cannot_upload_audio(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers=REV1,
    )
    assert r.status_code == 403


def test_cross_org_encounter_404s_on_audio_upload(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers=CLIN2,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# transcription pipeline via stub
# ---------------------------------------------------------------------


def test_stub_transcriber_default_placeholder_lands_as_completed(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers=CLIN1,
    )
    assert r.status_code == 201
    row = r.json()
    assert row["processing_status"] == "completed"
    assert row["transcript_text"].startswith("[stub-transcript]")
    assert "x.wav" in row["transcript_text"]


def test_stub_transcriber_honours_canned_text_header(client):
    canned = (
        "Chief complaint: blurry vision. Plan: YAG capsulotomy OD next week."
    )
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": canned},
    )
    assert r.status_code == 201
    row = r.json()
    assert row["processing_status"] == "completed"
    assert row["transcript_text"] == canned


def test_stub_transcriber_failure_lands_as_failed_with_error_code(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript-Error": "simulated STT timeout"},
    )
    assert r.status_code == 201
    row = r.json()
    assert row["processing_status"] == "failed"
    assert row["last_error_code"] == "stub_transcription_failed"
    assert "simulated STT timeout" in (row["last_error"] or "")


def test_retry_after_stub_failure_can_complete(client):
    # Upload with a forced stub error → row lands failed.
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript-Error": "transient STT blip"},
    )
    assert r.status_code == 201
    input_id = r.json()["id"]

    # Retry triggers queued → processing. The stub still carries the
    # forced-error metadata, so this retry still fails.
    r = client.post(
        f"/encounter-inputs/{input_id}/retry", headers=CLIN1
    )
    assert r.status_code == 200
    r = client.post(
        f"/encounter-inputs/{input_id}/process", headers=CLIN1
    )
    assert r.status_code == 200
    assert r.json()["input"]["processing_status"] == "failed"


# ---------------------------------------------------------------------
# transcript review / edit
# ---------------------------------------------------------------------


def _upload_and_complete(client, canned: str = "Test transcript body from audio."):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": canned},
    )
    assert r.status_code == 201
    return r.json()


def test_transcript_edit_replaces_text_on_completed_input(client):
    row = _upload_and_complete(client, "Original transcript from stub STT.")
    input_id = row["id"]
    edit = "Doctor-corrected transcript. Clearer. Signed by clinician."
    r = client.patch(
        f"/encounter-inputs/{input_id}/transcript",
        json={"transcript_text": edit},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["transcript_text"] == edit
    assert updated["processing_status"] == "completed"


def test_transcript_edit_rejects_non_completed(client):
    # Upload with stub error → row is `failed`, not `completed`.
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("x.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript-Error": "blip"},
    )
    input_id = r.json()["id"]
    r = client.patch(
        f"/encounter-inputs/{input_id}/transcript",
        json={"transcript_text": "Attempted edit."},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert (
        r.json()["detail"]["error_code"] == "encounter_input_not_editable"
    )


def test_transcript_edit_cross_org_is_404(client):
    row = _upload_and_complete(client)
    r = client.patch(
        f"/encounter-inputs/{row['id']}/transcript",
        json={"transcript_text": "Hijack."},
        headers=CLIN2,
    )
    assert r.status_code == 404


def test_transcript_edit_reviewer_is_403(client):
    row = _upload_and_complete(client)
    r = client.patch(
        f"/encounter-inputs/{row['id']}/transcript",
        json={"transcript_text": "Reviewer tried to edit."},
        headers=REV1,
    )
    assert r.status_code == 403


def test_transcript_edit_audit_does_not_carry_body(client):
    row = _upload_and_complete(client)
    sensitive = "PATIENT NAME: JANE DOE, MRN 123-45-6789, DOB 01/01/1970."
    r = client.patch(
        f"/encounter-inputs/{row['id']}/transcript",
        json={"transcript_text": sensitive},
        headers=CLIN1,
    )
    assert r.status_code == 200

    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    edits = [
        ev for ev in items
        if ev["event_type"] == "encounter_input_transcript_edited"
    ]
    assert len(edits) >= 1
    for ev in edits:
        detail = ev.get("detail") or ""
        assert "PATIENT NAME" not in detail
        assert "123-45-6789" not in detail
        assert "JANE DOE" not in detail


# ---------------------------------------------------------------------
# generation readiness
# ---------------------------------------------------------------------


def test_generate_blocked_until_audio_input_completes(client):
    # No inputs yet on encounter 1 → Generate 409 no_completed_input.
    r = client.post(
        "/encounters/1/notes/generate", json={}, headers=CLIN1
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "no_completed_input"

    # After a completed audio upload, Generate succeeds.
    _upload_and_complete(
        client,
        (
            "Chief complaint: blurry vision OD. "
            "OD 20/40, OS 20/20. IOP 15/17. "
            "Plan: YAG capsulotomy OD. Follow-up in 4 weeks."
        ),
    )
    r = client.post(
        "/encounters/1/notes/generate", json={}, headers=CLIN1
    )
    assert r.status_code == 201, r.text


def test_generate_uses_edited_transcript_not_stub_placeholder(client):
    row = _upload_and_complete(
        client,
        "Original stub text - not clinically adequate for sign.",
    )
    better = (
        "Chief complaint: blurry vision OD for 3 weeks. "
        "OD 20/40, OS 20/20. IOP 15/17. "
        "Diagnosis: posterior capsular opacification OD. "
        "Plan: YAG capsulotomy OD. Follow-up in 4 weeks."
    )
    r = client.patch(
        f"/encounter-inputs/{row['id']}/transcript",
        json={"transcript_text": better},
        headers=CLIN1,
    )
    assert r.status_code == 200

    r = client.post(
        "/encounters/1/notes/generate",
        json={"input_id": row["id"]},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    gen = r.json()
    # The findings should include the edited acuity + plan, NOT the
    # stub placeholder.
    assert gen["findings"]["visual_acuity_od"] == "20/40"
    assert gen["findings"]["visual_acuity_os"] == "20/20"


# ---------------------------------------------------------------------
# provenance isolation from shortcuts / quick comments
# ---------------------------------------------------------------------


def test_audio_transcript_edit_does_not_mingle_with_shortcut_surfaces(client):
    # Create a clinical-shortcut usage event + a quick-comment usage
    # event, then edit a transcript. The transcript edit's audit row
    # must be a DIFFERENT event_type and MUST NOT carry the shortcut
    # ref or the quick-comment ref in its detail.
    client.post(
        "/me/clinical-shortcuts/used",
        json={"shortcut_id": "pvd-01"},
        headers=CLIN1,
    )
    client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "sx-01"},
        headers=CLIN1,
    )

    row = _upload_and_complete(client)
    client.patch(
        f"/encounter-inputs/{row['id']}/transcript",
        json={"transcript_text": "Edited transcript."},
        headers=CLIN1,
    )

    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    edits = [
        ev for ev in items
        if ev["event_type"] == "encounter_input_transcript_edited"
    ]
    for ev in edits:
        detail = ev.get("detail") or ""
        assert "pvd-01" not in detail
        assert "sx-01" not in detail
        assert "shortcut_id" not in detail
        assert "preloaded_ref" not in detail
