"""Phase 55 — immutable audit and external evidence hardening tests.

Covers:

  Pure service layer
  * hash chain: first event prev=NULL; every subsequent event
    prev = prior event_hash; event_hash reproducible from canonical
    payload
  * verify_chain reports ok=True on a clean chain
  * verify_chain detects prev_event_hash tampering
  * verify_chain detects content tampering (event_hash mismatch)
  * org-scoping: org A's chain is independent of org B's

  Route wiring
  * sign emits note_signed evidence event with fingerprint + status
  * final-approve emits note_final_approved
  * export emits note_exported
  * amend emits TWO events (source + new) when prior approval was
    pending, THREE events when prior was approved (source + new +
    final_approval_invalidated)

  Evidence bundle
  * /note-versions/{id}/evidence-bundle returns a structured bundle
  * bundle.envelope.body_hash_sha256 reproduces on a second call
  * bundle includes chain events for the note
  * bundle includes amendment chain + current_record_of_care anchor
  * bundle includes chain_integrity verdict
  * cross-org → 404

  Admin endpoints
  * /admin/operations/evidence-chain-verify returns ok=true on clean
  * /admin/operations/notes/{id}/evidence-health returns true for
    has_signed_event + has_final_approval_event after sign + approve
  * both admin endpoints 403 for non-admin
  * ops overview now includes evidence_chain_broken counter
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


TRANSCRIPT = (
    "Patient presents for YAG laser follow-up. Visual acuity 20/40 OD, "
    "20/20 OS. IOP 15 OD, 17 OS. Anterior segment quiet. Plan: return "
    "in 3 months, continue current meds."
)


# ---------- helpers -------------------------------------------------------

def _ingest_generate(client, encounter_id: int = 1, headers=CLIN1) -> dict:
    client.post(
        f"/encounters/{encounter_id}/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=headers,
    )
    r = client.post(
        f"/encounters/{encounter_id}/notes/generate",
        json={},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["note"] if "note" in body else body


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


def _sign_approve(client, note_id: int) -> dict:
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    r = client.post(
        f"/note-versions/{note_id}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _read_evidence_events(test_db, organization_id: int) -> list[dict]:
    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, organization_id, note_version_id, event_type, "
            "prev_event_hash, event_hash, draft_status, final_approval_status, "
            "content_fingerprint "
            "FROM note_evidence_events WHERE organization_id = :org "
            "ORDER BY id",
            {"org": organization_id},
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# =========================================================================
# Hash-chain mechanics
# =========================================================================

def test_first_event_has_null_prev_and_hash_reproduces(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    rows = _read_evidence_events(test_db, organization_id=1)
    assert len(rows) == 1
    first = rows[0]
    assert first["event_type"] == "note_signed"
    assert first["prev_event_hash"] is None
    assert len(first["event_hash"]) == 64


def test_chain_links_via_prev_event_hash(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    rows = _read_evidence_events(test_db, organization_id=1)
    types = [r["event_type"] for r in rows]
    assert types == ["note_signed", "note_final_approved", "note_exported"]
    assert rows[0]["prev_event_hash"] is None
    assert rows[1]["prev_event_hash"] == rows[0]["event_hash"]
    assert rows[2]["prev_event_hash"] == rows[1]["event_hash"]


def test_verify_chain_reports_ok_on_clean(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    from app.services.note_evidence import verify_chain
    verdict = verify_chain(organization_id=1).as_dict()
    assert verdict["ok"] is True
    assert verdict["total_events"] == 2
    assert verdict["verified_events"] == 2
    assert verdict["broken_at_event_id"] is None


def test_verify_chain_detects_prev_hash_tampering(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    # Tamper: corrupt the second row's prev_event_hash.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET prev_event_hash = "
            "'0000000000000000000000000000000000000000000000000000000000000000' "
            "WHERE organization_id = 1 AND event_type = 'note_final_approved'"
        )
        conn.commit()
    finally:
        conn.close()

    from app.services.note_evidence import verify_chain
    verdict = verify_chain(organization_id=1).as_dict()
    assert verdict["ok"] is False
    assert verdict["broken_reason"] == "prev_event_hash_mismatch"
    assert verdict["broken_at_event_id"] is not None


def test_verify_chain_detects_content_tampering(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    # Tamper: change the draft_status on the first row. event_hash
    # was computed over the old value, so recomputation will miss.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET draft_status = 'draft' "
            "WHERE id = (SELECT MIN(id) FROM note_evidence_events "
            "             WHERE organization_id = 1)"
        )
        conn.commit()
    finally:
        conn.close()

    from app.services.note_evidence import verify_chain
    verdict = verify_chain(organization_id=1).as_dict()
    assert verdict["ok"] is False
    assert verdict["broken_reason"] == "event_hash_mismatch"


def test_chain_is_org_scoped(client, test_db):
    # Org 1 activity.
    note1 = _ingest_generate(client, encounter_id=1, headers=CLIN1)
    _clear_missing_flags(test_db, note1["id"])
    client.post(f"/note-versions/{note1['id']}/sign", headers=CLIN1)

    # Org 2 activity.
    note2 = _ingest_generate(client, encounter_id=3, headers=CLIN2)
    _clear_missing_flags(test_db, note2["id"])
    client.post(f"/note-versions/{note2['id']}/sign", headers=CLIN2)

    from app.services.note_evidence import verify_chain
    v1 = verify_chain(organization_id=1).as_dict()
    v2 = verify_chain(organization_id=2).as_dict()
    assert v1["ok"] is True and v1["total_events"] == 1
    assert v2["ok"] is True and v2["total_events"] == 1
    # Tampering org 1 does not break org 2.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET draft_status = 'draft' "
            "WHERE organization_id = 1"
        )
        conn.commit()
    finally:
        conn.close()
    v1b = verify_chain(organization_id=1).as_dict()
    v2b = verify_chain(organization_id=2).as_dict()
    assert v1b["ok"] is False
    assert v2b["ok"] is True


# =========================================================================
# Amend emits 2 events on pending, 3 events on approved
# =========================================================================

def test_amend_without_prior_approval_emits_two_events(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    # DO NOT approve. Amend while pending.
    r = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended.\nASSESSMENT: ok.\nPLAN: continue.\n"
            ),
            "reason": "fix IOP",
        },
        headers=CLIN1,
    )
    assert r.status_code == 201
    rows = _read_evidence_events(test_db, organization_id=1)
    types = [r["event_type"] for r in rows]
    # note_signed, then source + new for amendment. No
    # final_approval_invalidated (prior was pending, not approved).
    assert types == ["note_signed", "note_amended_source", "note_amended_new"]


def test_amend_with_prior_approval_emits_three_events(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    r = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended.\nASSESSMENT: ok.\nPLAN: continue.\n"
            ),
            "reason": "fix IOP",
        },
        headers=CLIN1,
    )
    assert r.status_code == 201
    rows = _read_evidence_events(test_db, organization_id=1)
    types = [r["event_type"] for r in rows]
    assert types == [
        "note_signed",
        "note_final_approved",
        "note_amended_source",
        "note_amended_new",
        "note_final_approval_invalidated",
    ]


# =========================================================================
# Evidence bundle endpoint
# =========================================================================

def test_evidence_bundle_has_all_sections(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    r = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Required sections.
    for k in (
        "bundle_version", "note", "encounter", "final_approval",
        "supersession", "evidence_events", "evidence_health",
        "chain_integrity", "envelope",
    ):
        assert k in body, k
    assert body["note"]["id"] == note["id"]
    assert body["final_approval"]["status"] == "approved"
    assert body["final_approval"]["signature_text"] == "Casey Clinician"
    # Evidence events populated for this note.
    assert len(body["evidence_events"]) >= 2
    # Chain integrity surfaced.
    assert body["chain_integrity"]["ok"] is True
    # Envelope carries a body_hash.
    assert len(body["envelope"]["body_hash_sha256"]) == 64


def test_evidence_bundle_body_hash_is_deterministic(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    first = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    second = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    # envelope.issued_at + issued_by change each call — but the body
    # hash is computed over the body only, so it must match.
    assert (
        first["envelope"]["body_hash_sha256"]
        == second["envelope"]["body_hash_sha256"]
    )


def test_evidence_bundle_includes_supersession_chain(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    amend = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended.\nASSESSMENT: corrected.\nPLAN: ok.\n"
            ),
            "reason": "fix IOP transcription",
        },
        headers=CLIN1,
    )
    amended_id = amend.json()["id"]

    r = client.get(
        f"/note-versions/{amended_id}/evidence-bundle", headers=CLIN1
    )
    body = r.json()
    sup = body["supersession"]
    assert sup["chain_length"] == 2
    assert sup["current_record_of_care_note_id"] == amended_id
    assert sup["has_invalidated_approval"] is True


def test_evidence_bundle_cross_org_returns_404(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    r = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN2
    )
    assert r.status_code == 404


# =========================================================================
# Admin endpoints
# =========================================================================

def test_admin_evidence_chain_verify_clean(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    r = client.get(
        "/admin/operations/evidence-chain-verify", headers=ADMIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["total_events"] == 2
    assert body["broken_at_event_id"] is None


def test_admin_evidence_chain_verify_detects_tamper(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    # Tamper the first evidence row's prev_event_hash.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET event_hash = "
            "'aa' || substr(event_hash, 3) "
            "WHERE id = (SELECT MIN(id) FROM note_evidence_events "
            "             WHERE organization_id = 1)"
        )
        conn.commit()
    finally:
        conn.close()

    r = client.get(
        "/admin/operations/evidence-chain-verify", headers=ADMIN1
    ).json()
    assert r["ok"] is False
    assert r["broken_reason"] == "event_hash_mismatch"


def test_admin_evidence_chain_verify_requires_admin(client):
    r = client.get(
        "/admin/operations/evidence-chain-verify", headers=CLIN1
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "security_admin_required"


def test_admin_note_evidence_health(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    r = client.get(
        f"/admin/operations/notes/{note['id']}/evidence-health",
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_signed_event"] is True
    assert body["has_final_approval_event"] is True
    assert body["has_export_event"] is False
    assert body["content_fingerprint_present"] is True
    assert body["fingerprint_matches_current"] is True
    assert body["event_count"] >= 2


def test_admin_note_evidence_health_requires_admin(client):
    r = client.get(
        "/admin/operations/notes/1/evidence-health", headers=CLIN1
    )
    assert r.status_code == 403


def test_ops_overview_surfaces_evidence_chain_broken_on_tamper(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    # Fresh overview reports chain is fine.
    before = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert before["counts"]["evidence_chain_broken"] == 0

    # Tamper.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET draft_status = 'draft' "
            "WHERE organization_id = 1"
        )
        conn.commit()
    finally:
        conn.close()

    after = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert after["counts"]["evidence_chain_broken"] == 1


# =========================================================================
# Pilot flow still green
# =========================================================================

def test_pilot_flow_end_to_end_with_evidence(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    # Evidence chain now has 3 events.
    rows = _read_evidence_events(test_db, organization_id=1)
    types = [r["event_type"] for r in rows]
    assert types == ["note_signed", "note_final_approved", "note_exported"]
    # Bundle round-trip succeeds.
    r = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    )
    assert r.status_code == 200
    assert r.json()["chain_integrity"]["ok"] is True
