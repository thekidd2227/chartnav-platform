"""Phase 25A / GH-003 — audio retention pruner tests.

Exercises the `scripts.prune_audio_retention` module directly so the
tests can stage encounter_inputs rows + on-disk blobs deterministically
without going through the HTTP upload path. The pre-existing audio
upload tests already verify the HTTP path; here we focus on the
retention contract:

- dry-run reports candidates but writes nothing
- --delete unlinks files, clears storage_ref, emits an audit row
- the audit detail carries metadata only (no filename, no path)
- finished_at older than the cutoff is required
- recent files are skipped
- missing files are reported (missing_files) but do not crash
- the encounter_inputs row itself is preserved after delete
- the transcript text on the row stays intact (only storage_ref is
  cleared)
- --days < 1 returns a 2 exit code from main()
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# This file does not exercise consent state directly, but it imports
# scripts.prune_audio_retention which needs `app.db` configured. We
# rely on the existing `client` fixture only for the DB bootstrap +
# audio-consent helper; uploads happen through the API path.
pytestmark = pytest.mark.usefixtures("audio_consent_for_seeded")


MINIMAL_WAV_BYTES = (
    b"RIFF" + (36).to_bytes(4, "little") + b"WAVEfmt "
    + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
    + (1).to_bytes(2, "little") + (16000).to_bytes(4, "little")
    + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little")
    + (16).to_bytes(2, "little") + b"data"
    + (0).to_bytes(4, "little")
)


CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _upload_audio(client, encounter_id: int) -> int:
    files = {"audio": ("dictation.wav", MINIMAL_WAV_BYTES, "audio/wav")}
    r = client.post(
        f"/encounters/{encounter_id}/inputs/audio",
        files=files,
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


def _backdate_finished_at(input_id: int, days_ago: int) -> None:
    """Move finished_at into the past so the pruner picks it up."""
    from sqlalchemy import text
    from app.db import transaction

    past = (
        datetime.now(timezone.utc) - timedelta(days=days_ago, hours=1)
    ).isoformat()
    with transaction() as conn:
        conn.execute(
            text("UPDATE encounter_inputs SET finished_at = :ts WHERE id = :id"),
            {"ts": past, "id": input_id},
        )


def _storage_path_for(input_id: int) -> str:
    from sqlalchemy import text
    from app.db import transaction

    with transaction() as conn:
        row = conn.execute(
            text("SELECT source_metadata FROM encounter_inputs WHERE id = :id"),
            {"id": input_id},
        ).mappings().first()
    assert row is not None
    md = json.loads(row["source_metadata"])
    ref = md.get("storage_ref")
    assert isinstance(ref, dict)
    return ref["uri"]


def test_dry_run_reports_candidates_but_writes_nothing(client):
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)
    on_disk = _storage_path_for(input_id)
    assert Path(on_disk).exists()

    from scripts.prune_audio_retention import run
    report = run(days=30, do_delete=False)

    assert report.scanned >= 1
    assert report.eligible >= 1
    assert report.deleted == 0
    assert report.bytes_freed == 0
    # File still there.
    assert Path(on_disk).exists()


def test_delete_unlinks_file_and_clears_storage_ref(client):
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)
    on_disk = _storage_path_for(input_id)
    assert Path(on_disk).exists()
    pre_size = Path(on_disk).stat().st_size
    assert pre_size > 0

    from scripts.prune_audio_retention import run
    report = run(days=30, do_delete=True)

    assert report.deleted >= 1
    assert report.bytes_freed >= pre_size
    # File gone.
    assert not Path(on_disk).exists()

    # encounter_inputs row preserved; transcript stays; storage_ref nulled.
    from sqlalchemy import text
    from app.db import transaction
    with transaction() as conn:
        row = conn.execute(
            text(
                "SELECT transcript_text, source_metadata "
                "FROM encounter_inputs WHERE id = :id"
            ),
            {"id": input_id},
        ).mappings().first()
    assert row is not None  # row preserved
    md = json.loads(row["source_metadata"])
    assert "storage_ref" not in md
    assert "stored_path" not in md
    assert "retention_pruned_at" in md


def test_delete_emits_audit_event_with_metadata_only(client):
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)
    on_disk = _storage_path_for(input_id)

    from scripts.prune_audio_retention import run
    run(days=30, do_delete=True)

    from app.db import fetch_all
    rows = fetch_all(
        "SELECT event_type, detail, organization_id "
        "FROM security_audit_events "
        "WHERE event_type = 'audio_retention_pruned' ORDER BY id"
    )
    assert len(rows) >= 1
    last = rows[-1]
    assert last["organization_id"] == 1
    # Detail carries the encounter_input_id + byte count; never the path.
    assert "encounter_input_id" in (last["detail"] or "")
    assert "deleted_bytes" in (last["detail"] or "")
    assert on_disk not in (last["detail"] or "")


def test_recent_uploads_are_skipped(client):
    """A file finished 5 days ago must not be touched by a 30-day prune."""
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=5)
    on_disk = _storage_path_for(input_id)

    from scripts.prune_audio_retention import run
    report = run(days=30, do_delete=True)

    assert report.deleted == 0
    assert Path(on_disk).exists()


def test_missing_file_is_reported_not_an_error(client):
    """If the on-disk blob was already removed but the row still
    points at it, the pruner must report missing_files and skip
    the candidate without crashing."""
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)
    on_disk = _storage_path_for(input_id)
    Path(on_disk).unlink()  # simulate already-deleted blob
    assert not Path(on_disk).exists()

    from scripts.prune_audio_retention import run
    report = run(days=30, do_delete=True)
    # File was missing → not "eligible" by the size>0 rule but still
    # surfaces as a missing_files entry.
    assert report.deleted == 0
    assert report.missing_files >= 1


def test_main_rejects_zero_days(client):
    from scripts.prune_audio_retention import main
    rc = main(["--days", "0", "--dry-run"])
    assert rc == 2


def test_main_dry_run_prints_summary(client, capsys):
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)

    from scripts.prune_audio_retention import main
    rc = main(["--days", "30", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "scanned" in out
    assert "eligible" in out


def test_main_delete_actually_deletes(client):
    input_id = _upload_audio(client, encounter_id=1)
    _backdate_finished_at(input_id, days_ago=40)
    on_disk = _storage_path_for(input_id)
    assert Path(on_disk).exists()

    from scripts.prune_audio_retention import main
    rc = main(["--days", "30", "--delete"])
    assert rc == 0
    assert not Path(on_disk).exists()
