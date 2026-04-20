"""Phase 36 — browser-mic capture provenance on the upload endpoint.

The new `X-Capture-Source` header is the only contract change on the
backend in this phase. Tests:

- header absent → defaults to `file-upload` in source_metadata
  (preserves phase-33 behaviour).
- header `browser-mic` → persisted on source_metadata.capture_source.
- header `file-upload` → persisted as-is.
- bogus value → 400 audio_capture_source_invalid (no silent acceptance).
- shared encounter consistency: a browser-mic upload and a file-upload
  to the same encounter both land on the same shared list.
- audit detail records capture_source for ops visibility.
"""

from __future__ import annotations

import json


CLIN1 = {"X-User-Email": "clin@chartnav.local"}
ADMIN1 = {"X-User-Email": "admin@chartnav.local"}

MINIMAL_WAV_BYTES = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt "
    + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little") + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little") + b"data"
    + (0).to_bytes(4, "little")
)


def test_capture_source_defaults_to_file_upload_when_header_absent(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Stub-Transcript": "From a file."},
    )
    assert r.status_code == 201, r.text
    md = json.loads(r.json()["source_metadata"])
    assert md["capture_source"] == "file-upload"


def test_capture_source_browser_mic_is_persisted(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={
            "audio": (
                "chartnav-dictation-2026-04-19-22-15-00.webm",
                MINIMAL_WAV_BYTES,
                "audio/webm",
            ),
        },
        headers={
            **CLIN1,
            "X-Capture-Source": "browser-mic",
            "X-Stub-Transcript": "Live mic dictation body.",
        },
    )
    assert r.status_code == 201, r.text
    md = json.loads(r.json()["source_metadata"])
    assert md["capture_source"] == "browser-mic"
    assert md["original_filename"].startswith("chartnav-dictation-")


def test_capture_source_file_upload_explicit_is_persisted(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={
            **CLIN1,
            "X-Capture-Source": "file-upload",
            "X-Stub-Transcript": "Explicit file upload.",
        },
    )
    assert r.status_code == 201
    md = json.loads(r.json()["source_metadata"])
    assert md["capture_source"] == "file-upload"


def test_capture_source_invalid_value_rejected(client):
    r = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("d.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={**CLIN1, "X-Capture-Source": "ambient-listener"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "audio_capture_source_invalid"


def test_browser_and_file_uploads_share_one_encounter(client):
    """Mobile/desktop continuity sanity: a browser-mic recording and a
    hand-uploaded file on the same encounter both land on the same
    shared list and both flow through the same ingestion seam."""
    rA = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("recording.webm", MINIMAL_WAV_BYTES, "audio/webm")},
        headers={
            **CLIN1,
            "X-Capture-Source": "browser-mic",
            "X-Stub-Transcript": "Recorded body.",
        },
    )
    rB = client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("hand.wav", MINIMAL_WAV_BYTES, "audio/wav")},
        headers={
            **CLIN1,
            "X-Capture-Source": "file-upload",
            "X-Stub-Transcript": "Uploaded body.",
        },
    )
    assert rA.status_code == 201 and rB.status_code == 201
    listing = client.get(
        "/encounters/1/inputs", headers=CLIN1
    ).json()
    by_id = {r["id"]: r for r in listing}
    a, b = by_id[rA.json()["id"]], by_id[rB.json()["id"]]
    assert json.loads(a["source_metadata"])["capture_source"] == "browser-mic"
    assert json.loads(b["source_metadata"])["capture_source"] == "file-upload"
    # Both completed against the SAME encounter, no fork.
    assert a["encounter_id"] == b["encounter_id"] == 1
    assert a["processing_status"] == b["processing_status"] == "completed"


def test_audit_detail_records_capture_source(client):
    client.post(
        "/encounters/1/inputs/audio",
        files={"audio": ("r.webm", MINIMAL_WAV_BYTES, "audio/webm")},
        headers={
            **CLIN1,
            "X-Capture-Source": "browser-mic",
            "X-Stub-Transcript": "x",
        },
    )
    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    uploads = [
        ev for ev in items
        if ev["event_type"] == "encounter_input_audio_uploaded"
    ]
    assert any(
        "capture_source=browser-mic" in (ev.get("detail") or "")
        for ev in uploads
    )
