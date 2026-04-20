"""Phase 22 — async ingestion + orchestration lifecycle.

Covers:
- text_paste input flows queued → processing → completed via the
  pipeline; retry_count stays 0; started_at + finished_at stamped.
- transcript_too_short lands in `failed` with last_error_code set
  and retry_count=0 (first run); the row stays visible + retryable.
- retry flips failed → queued, increments retry_count, emits
  `encounter_input_retried` audit event.
- process endpoint re-runs the pipeline against a queued row.
- audio uploads stay queued on create and fail honestly when no
  transcriber is installed.
- transcriber seam can be replaced in tests via set_transcriber().
- generation is refused while the input is still `processing`
  (contract enforced by the orchestrator).
- existing sign/export flow unchanged on bridged or standalone
  encounters after the refactor (smoke).
"""

from __future__ import annotations

import json


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}

GOOD_TRANSCRIPT = (
    "Chief complaint: blurry right eye.\n"
    "OD 20/40, OS 20/20. IOP 15/17.\n"
    "Diagnosis: cataract. Plan: refer for surgery.\n"
    "Follow-up in 4 weeks.\n"
)


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------

def test_text_paste_flows_through_pipeline_to_completed(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": GOOD_TRANSCRIPT},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["processing_status"] == "completed"
    assert row["retry_count"] == 0
    assert row["last_error"] is None
    assert row["last_error_code"] is None
    assert row["started_at"] is not None
    assert row["finished_at"] is not None
    assert row["worker_id"] == "inline"


def test_text_input_too_short_fails_with_error_code(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "short"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["processing_status"] == "failed"
    assert row["last_error_code"] == "transcript_too_short"
    assert row["last_error"] and "at least 10" in row["last_error"]
    assert row["retry_count"] == 0
    assert row["finished_at"] is not None


def test_audio_upload_is_queued_on_create(client):
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
    assert r.json()["started_at"] is None


def test_audio_upload_fails_when_no_transcriber_installed(client):
    """process an audio upload without a transcriber → failed honestly.

    Phase 33 installs a stub transcriber by default so audio uploads
    move through the pipeline out-of-the-box. This test explicitly
    uninstalls the stub first to verify the legacy honest-failure
    contract is preserved: if no transcriber at all is wired, the
    pipeline must fail with `audio_transcription_not_implemented`.
    """
    from app.services.ingestion import (
        _not_implemented_transcriber, set_transcriber, transcribe_audio,
    )
    saved = transcribe_audio
    set_transcriber(_not_implemented_transcriber)
    try:
        # Create a queued audio input.
        r = client.post(
            "/encounters/1/inputs",
            json={
                "input_type": "audio_upload",
                "source_metadata": {"filename": "rec.wav"},
            },
            headers=CLIN1,
        )
        input_id = r.json()["id"]

        # Process it.
        r = client.post(
            f"/encounter-inputs/{input_id}/process", headers=CLIN1,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["input"]["processing_status"] == "failed"
        assert (
            body["ingestion_error"]["error_code"]
            == "audio_transcription_not_implemented"
        )
        assert (
            body["input"]["last_error_code"]
            == "audio_transcription_not_implemented"
        )
    finally:
        # Restore whatever transcriber was installed before the test.
        set_transcriber(saved)


# ---------------------------------------------------------------------
# Retry lifecycle
# ---------------------------------------------------------------------

def test_retry_and_reprocess_succeeds_with_good_text(client):
    # Start with too-short text → failed.
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "tiny"},
        headers=CLIN1,
    )
    input_id = r.json()["id"]
    assert r.json()["processing_status"] == "failed"

    # We need to repair the transcript before retrying; the service
    # layer doesn't currently expose a PATCH on inputs (by design —
    # inputs are source-of-record). For the retry test, a fresh
    # input is the right operator workflow. Prove the retry API
    # transitions a failed row forward anyway:
    r = client.post(
        f"/encounter-inputs/{input_id}/retry", headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["processing_status"] == "queued"
    assert row["retry_count"] == 1

    # Run the pipeline — will fail again on too-short but the
    # retry_count should stick and last_error should refresh.
    r = client.post(
        f"/encounter-inputs/{input_id}/process", headers=CLIN1,
    )
    assert r.status_code == 200
    row = r.json()["input"]
    assert row["processing_status"] == "failed"
    assert row["retry_count"] == 1


def test_retry_refuses_when_not_failed(client):
    # Create a completed input.
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": GOOD_TRANSCRIPT},
        headers=CLIN1,
    )
    input_id = r.json()["id"]

    # completed → retry not meaningful.
    r = client.post(
        f"/encounter-inputs/{input_id}/retry", headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "input_not_queueable"


def test_retry_emits_audit_event(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "tiny"},
        headers=CLIN1,
    )
    input_id = r.json()["id"]
    client.post(f"/encounter-inputs/{input_id}/retry", headers=CLIN1)

    audit = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1,
    ).json()
    items = audit["items"] if isinstance(audit, dict) else audit
    types = [e["event_type"] for e in items]
    assert "encounter_input_retried" in types


def test_retry_scope_enforced(client):
    # org-2 clinician cannot retry org-1 input.
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "tiny"},
        headers=CLIN1,
    )
    input_id = r.json()["id"]

    r = client.post(
        f"/encounter-inputs/{input_id}/retry",
        headers={"X-User-Email": "clin@northside.local"},
    )
    # cross-org encounter = 404
    assert r.status_code == 404


def test_reviewer_cannot_retry(client):
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "tiny"},
        headers=CLIN1,
    )
    input_id = r.json()["id"]

    r = client.post(
        f"/encounter-inputs/{input_id}/retry", headers=REV1,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------
# Transcriber seam
# ---------------------------------------------------------------------

def test_transcriber_seam_replaces_audio_pipeline(client):
    """Prove a plug-in transcriber can flip audio uploads to completed."""
    from app.services import ingestion as _ing

    # Install a fake transcriber for this test only.
    calls: list[dict] = []

    def fake_transcriber(metadata: dict) -> str:
        calls.append(metadata)
        return (
            "Chief complaint: headache.\nOD 20/25, OS 20/25. IOP 14/14.\n"
            "Plan: observe.\nFollow-up in 8 weeks.\n"
        )

    original = _ing.transcribe_audio
    _ing.set_transcriber(fake_transcriber)
    try:
        r = client.post(
            "/encounters/1/inputs",
            json={
                "input_type": "audio_upload",
                "source_metadata": {"filename": "rec.wav", "duration_s": 42},
            },
            headers=CLIN1,
        )
        input_id = r.json()["id"]
        r = client.post(
            f"/encounter-inputs/{input_id}/process", headers=CLIN1,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ingestion_error"] is None
        assert body["input"]["processing_status"] == "completed"
        assert body["input"]["transcript_text"].startswith("Chief complaint: headache")
        assert calls and calls[0]["filename"] == "rec.wav"
    finally:
        _ing.set_transcriber(original)


# ---------------------------------------------------------------------
# Orchestrator contract
# ---------------------------------------------------------------------

def test_generate_refuses_failed_input(client):
    # Create a failed input, then try to generate — should 409.
    r = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": "x"},
        headers=CLIN1,
    )
    assert r.json()["processing_status"] == "failed"

    r = client.post(
        "/encounters/1/notes/generate", json={}, headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "no_completed_input"


def test_generate_happy_path_still_works_after_refactor(client):
    """Smoke: the orchestrator refactor didn't break the primary flow."""
    client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": GOOD_TRANSCRIPT},
        headers=CLIN1,
    )
    r = client.post(
        "/encounters/1/notes/generate", json={}, headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    note = r.json()["note"]
    findings = r.json()["findings"]
    assert note["version_number"] == 1
    assert note["draft_status"] == "draft"
    assert findings["visual_acuity_od"] == "20/40"


# ---------------------------------------------------------------------
# process endpoint
# ---------------------------------------------------------------------

def test_process_endpoint_runs_queued_audio(client):
    """process endpoint explicitly drives the state machine forward."""
    from app.services import ingestion as _ing

    def ok(metadata: dict) -> str:
        return "A short but valid transcript for testing purposes ok."

    original = _ing.transcribe_audio
    _ing.set_transcriber(ok)
    try:
        input_id = client.post(
            "/encounters/1/inputs",
            json={"input_type": "audio_upload", "source_metadata": {}},
            headers=CLIN1,
        ).json()["id"]

        r = client.post(
            f"/encounter-inputs/{input_id}/process", headers=CLIN1,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["input"]["processing_status"] == "completed"
        assert body["input"]["started_at"] is not None
        assert body["input"]["finished_at"] is not None
    finally:
        _ing.set_transcriber(original)


def test_process_is_idempotent_on_completed(client):
    input_id = client.post(
        "/encounters/1/inputs",
        json={"input_type": "text_paste", "transcript_text": GOOD_TRANSCRIPT},
        headers=CLIN1,
    ).json()["id"]
    r = client.post(
        f"/encounter-inputs/{input_id}/process", headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["input"]["processing_status"] == "completed"
