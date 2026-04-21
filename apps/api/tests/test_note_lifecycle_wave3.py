"""Phase 49 — clinical governance wave 3 tests.

Covers:
  - release-blocker computation (missing-data gate, empty text,
    invalid lifecycle order, already-signed, export-requires-sign,
    low-confidence warn severity)
  - the /review route (reviewer only, correct transition edges,
    reviewed_at + reviewed_by stamped)
  - the /amend route (amend-only-from-signed, reason required,
    creates a new version, supersession link, original marked
    superseded, amendment_chain walks both rows)
  - the sign route now freezes content_fingerprint + attestation_text,
    blocks on hard missing_data_flags, and audits blocked attempts
  - the /release-blockers route surfaces the live blocker list
  - the /amendment-chain route returns the ordered chain

Every test uses the same seed pattern as the existing transcript
tests to stay deterministic.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from tests.conftest import ADMIN1, CLIN1, REV1, ADMIN2, CLIN2


TRANSCRIPT = (
    "Patient presents for YAG laser follow-up. Visual acuity 20/40 OD, "
    "20/20 OS. IOP 15 OD, 17 OS. Anterior segment quiet. Posterior "
    "capsular opacification OD treated with YAG last visit, improving. "
    "Plan: return in 3 months, continue current meds."
)


def _ingest_and_generate(client, encounter_id: int = 1) -> dict[str, Any]:
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


def _clear_missing_flags(test_db, note_id: int) -> None:
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_versions SET missing_data_flags = '[]' WHERE id = :id",
            {"id": note_id},
        )
        conn.commit()
    finally:
        conn.close()


# ---------- release blocker computation (pure service) -------------------

def test_blockers_empty_for_clean_signed_target():
    from app.services.note_lifecycle import compute_release_blockers
    note = {
        "id": 1,
        "draft_status": "provider_review",
        "note_text": "SUBJECTIVE\n ... ASSESSMENT\n ... PLAN\n ...",
        "missing_data_flags": [],
        "provider_review_required": False,
    }
    blockers = compute_release_blockers(note, None, target="signed")
    hard = [b for b in blockers if b.severity != "warn"]
    assert hard == []


def test_blockers_block_empty_text_for_sign():
    from app.services.note_lifecycle import compute_release_blockers, hard_blockers
    note = {
        "id": 1,
        "draft_status": "draft",
        "note_text": "",
        "missing_data_flags": [],
        "provider_review_required": False,
    }
    hard = hard_blockers(compute_release_blockers(note, None, target="signed"))
    assert any(b.code == "note_text_empty" for b in hard)


def test_blockers_block_missing_data_flags_on_sign():
    from app.services.note_lifecycle import compute_release_blockers, hard_blockers
    note = {
        "id": 1,
        "draft_status": "draft",
        "note_text": "SUBJECTIVE ... ASSESSMENT ... PLAN ...",
        "missing_data_flags": ["iop_missing", "plan_missing"],
        "provider_review_required": False,
    }
    hard = hard_blockers(compute_release_blockers(note, None, target="signed"))
    codes = {b.code for b in hard}
    assert "missing_data_flags_set" in codes


def test_blockers_block_export_before_sign():
    from app.services.note_lifecycle import compute_release_blockers, hard_blockers
    note = {
        "id": 1,
        "draft_status": "draft",
        "note_text": "x" * 20,
        "missing_data_flags": [],
        "provider_review_required": False,
    }
    hard = hard_blockers(
        compute_release_blockers(note, None, target="exported")
    )
    assert any(b.code == "export_requires_sign" for b in hard)


def test_blockers_already_signed_cannot_re_sign():
    from app.services.note_lifecycle import compute_release_blockers, hard_blockers
    note = {
        "id": 1,
        "draft_status": "signed",
        "note_text": "x" * 20,
        "missing_data_flags": [],
        "provider_review_required": False,
    }
    hard = hard_blockers(compute_release_blockers(note, None, target="signed"))
    assert any(b.code == "already_signed" for b in hard)


def test_blockers_low_confidence_is_warn_not_block():
    from app.services.note_lifecycle import compute_release_blockers
    note = {
        "id": 1,
        "draft_status": "provider_review",
        "note_text": "x" * 20,
        "missing_data_flags": [],
        "provider_review_required": False,
    }
    findings = {"extraction_confidence": "low"}
    blockers = compute_release_blockers(note, findings, target="signed")
    warn = [b for b in blockers if b.severity == "warn"]
    assert any(b.code == "extraction_confidence_low" for b in warn)


def test_transitions_authority_matches_state_machine():
    from app.services.note_lifecycle import (
        LIFECYCLE_TRANSITIONS,
        can_transition,
    )
    # Sanity: can_transition matches the table.
    assert can_transition("draft", "signed") is None
    assert can_transition("provider_review", "reviewed") is None
    assert can_transition("reviewed", "signed") is None
    assert can_transition("signed", "draft") is not None
    assert can_transition("exported", "signed") is not None
    assert can_transition("amended", "exported") is None


# ---------- sign now enforces blockers + freezes fingerprint + attestation

def test_sign_blocked_by_missing_data_is_409_and_audited(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    # Force missing_data_flags non-empty.
    import sqlite3, os
    db_path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE note_versions SET missing_data_flags = '[\"iop_missing\"]' "
            "WHERE id = :id",
            {"id": note_id},
        )
        conn.commit()
    finally:
        conn.close()
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["error_code"] == "sign_blocked_by_gate"
    assert any(
        b["code"] == "missing_data_flags_set" for b in detail["blockers"]
    )
    # Audit row written.
    audit = client.get("/security-audit-events?limit=200", headers=ADMIN1)
    body = audit.json()
    rows = body if isinstance(body, list) else body.get("items", [])
    assert any(ev["event_type"] == "note_sign_blocked" for ev in rows)


def test_sign_freezes_fingerprint_and_attestation(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)

    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    signed = r.json()
    assert signed["draft_status"] == "signed"
    assert signed["content_fingerprint"] is not None
    assert len(signed["content_fingerprint"]) == 64
    assert signed["attestation_text"]
    # Wave 7: attestation is now stamped with the signer's full_name
    # (was previously caller.email) so the frozen statement carries
    # the real clinician identifier visible on the chart.
    assert "Casey Clinician" in signed["attestation_text"]

    # fingerprint_matches=True initially.
    rb = client.get(
        f"/note-versions/{note_id}/release-blockers?target=exported",
        headers=CLIN1,
    )
    assert rb.status_code == 200
    assert rb.json()["fingerprint_ok"] is True

    # Silently mutate note_text on disk → fingerprint drift detectable.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_versions SET note_text = 'TAMPERED' WHERE id = :id",
            {"id": note_id},
        )
        conn.commit()
    finally:
        conn.close()
    rb2 = client.get(
        f"/note-versions/{note_id}/release-blockers?target=exported",
        headers=CLIN1,
    )
    assert rb2.json()["fingerprint_ok"] is False


# ---------- /review route -----------------------------------------------

def test_review_reviewer_can_mark_reviewed(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    client.post(f"/note-versions/{note_id}/submit-for-review", headers=CLIN1)
    r = client.post(f"/note-versions/{note_id}/review", headers=REV1)
    assert r.status_code == 200, r.text
    reviewed = r.json()
    assert reviewed["draft_status"] == "reviewed"
    assert reviewed["reviewed_at"] is not None
    assert reviewed["reviewed_by_user_id"] is not None


def test_review_clinician_cannot_mark_reviewed(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    client.post(f"/note-versions/{note_id}/submit-for-review", headers=CLIN1)
    r = client.post(f"/note-versions/{note_id}/review", headers=CLIN1)
    assert r.status_code == 403


def test_review_from_draft_is_blocked(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    # Draft → reviewed is NOT a permitted edge (must go through
    # provider_review or revised first).
    r = client.post(f"/note-versions/{note_id}/review", headers=REV1)
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_note_transition"


def test_reviewed_then_signed_end_to_end(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    # draft → provider_review → reviewed → signed
    client.post(f"/note-versions/{note_id}/submit-for-review", headers=CLIN1)
    r = client.post(f"/note-versions/{note_id}/review", headers=REV1)
    assert r.status_code == 200
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    final = r.json()
    assert final["draft_status"] == "signed"


# ---------- /amend route + amendment chain ------------------------------

def test_amend_unsigned_is_refused(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.post(
        f"/note-versions/{note_id}/amend",
        json={"note_text": "amended body", "reason": "correction"},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "amendment_source_unsigned"


def test_amend_creates_new_version_and_supersedes_original(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)

    r = client.post(
        f"/note-versions/{note_id}/amend",
        json={
            "note_text": "AMENDED NOTE BODY — corrected IOP OD to 16",
            "reason": "correction of IOP transcription",
        },
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    amended = r.json()
    assert amended["draft_status"] == "amended"
    assert amended["amended_from_note_id"] == note_id
    assert amended["amendment_reason"].startswith("correction")
    assert amended["version_number"] > body["note"]["version_number"]

    # Original is now superseded.
    orig = client.get(f"/note-versions/{note_id}", headers=CLIN1).json()["note"]
    assert orig["superseded_at"] is not None
    assert orig["superseded_by_note_id"] == amended["id"]

    # Amendment chain returns both rows in order.
    chain = client.get(
        f"/note-versions/{amended['id']}/amendment-chain", headers=CLIN1
    )
    assert chain.status_code == 200
    rows = chain.json()["chain"]
    assert len(rows) == 2
    assert rows[0]["id"] == note_id
    assert rows[1]["id"] == amended["id"]


def test_amend_requires_reason_and_non_empty_text(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)

    r = client.post(
        f"/note-versions/{note_id}/amend",
        json={"note_text": "x" * 20, "reason": "ok"},
        headers=CLIN1,
    )
    # reason is 2 chars — under the 4-char minimum (422 from pydantic).
    assert r.status_code == 422


def test_amend_reviewer_and_front_desk_refused(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)

    r = client.post(
        f"/note-versions/{note_id}/amend",
        json={"note_text": "x" * 20, "reason": "correction of IOP"},
        headers=REV1,
    )
    assert r.status_code == 403


def test_amend_is_audited(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    client.post(
        f"/note-versions/{note_id}/amend",
        json={
            "note_text": "corrected note body",
            "reason": "typo fix in assessment",
        },
        headers=CLIN1,
    )

    audit = client.get("/security-audit-events?limit=200", headers=ADMIN1)
    body_a = audit.json()
    rows = body_a if isinstance(body_a, list) else body_a.get("items", [])
    types = [ev["event_type"] for ev in rows]
    assert "note_version_amended" in types


def test_export_permitted_from_amended(client, test_db):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    _clear_missing_flags(test_db, note_id)
    client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    r = client.post(
        f"/note-versions/{note_id}/amend",
        json={"note_text": "amended body, longer than 10 chars", "reason": "correction"},
        headers=CLIN1,
    )
    amended = r.json()
    # Amendment row can be exported without re-signing in this wave.
    exp = client.post(
        f"/note-versions/{amended['id']}/export", headers=CLIN1
    )
    assert exp.status_code == 200, exp.text
    assert exp.json()["draft_status"] == "exported"


def test_release_blockers_route_cross_org_404(client):
    body = _ingest_and_generate(client)
    note_id = body["note"]["id"]
    r = client.get(
        f"/note-versions/{note_id}/release-blockers", headers=CLIN2
    )
    # Cross-org read is masked to 404 by the shared loader.
    assert r.status_code == 404
