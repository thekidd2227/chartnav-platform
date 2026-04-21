"""Phase 52 — clinical approval and record finalization wave 7 tests.

Covers:

  - pure service layer:
      * compare_typed_signature case-sensitivity
      * compare_typed_signature whitespace policy
      * is_authorized_final_signer gate (inactive user, missing flag)
      * export_requires_final_approval matrix

  - /me surface exposes is_authorized_final_signer

  - sign now stamps final_approval_status='pending'

  - export is blocked while approval is pending, allowed when
    approved, blocked again when invalidated; both blocks audit

  - /final-approve:
      * unauthorized (flag=false) → 403 role_cannot_final_approve + audit
      * signature mismatch (wrong case)   → 422 signature_mismatch + audit
      * signature mismatch (wrong string) → 422 signature_mismatch + audit
      * empty signature                    → 422 signature_required + audit
      * valid → approval persists, signature_text stored verbatim
      * already approved → 409 already_approved
      * unsigned (draft) → 409 not_signable_state
      * cross-org note → 404 (org isolation)

  - /amend invalidates prior approval on the superseded row:
      * final_approval_status flipped to 'invalidated'
      * invalidation reason stamped
      * note_final_approval_invalidated audit event emitted (only when
        prior approval was 'approved', not merely 'pending')

  - The signer full_name is frozen into the attestation text on sign
    (Wave 7 UX fix — was previously email).

Every test uses the same seed pattern and fixture set as Wave 3.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from tests.conftest import ADMIN1, CLIN1, REV1, CLIN2


TRANSCRIPT = (
    "Patient presents for YAG laser follow-up. Visual acuity 20/40 OD, "
    "20/20 OS. IOP 15 OD, 17 OS. Anterior segment quiet. Plan: return "
    "in 3 months, continue current meds."
)


# ---------- helpers -------------------------------------------------------

def _ingest_and_generate(client, encounter_id: int = 1, headers=CLIN1) -> dict[str, Any]:
    """Ingest a transcript + generate a note. Returns the inner note
    object (the generate endpoint wraps the row in `{"note": {...}}`)."""
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
    # `/notes/generate` returns {"note": {...}, ...}. Return the note
    # row directly so callers can do `note["id"]` without wrapping.
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


def _sign(client, note_id: int, headers=CLIN1) -> dict:
    r = client.post(f"/note-versions/{note_id}/sign", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _find_audit_events(test_db, event_type: str) -> list[dict]:
    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_type, actor_email, error_code, detail "
            "FROM security_audit_events WHERE event_type = :et "
            "ORDER BY id",
            {"et": event_type},
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _get_note(client, note_id: int, headers=CLIN1) -> dict:
    """Fetch the latest server-side view of a note row.
    `GET /note-versions/{id}` returns `{"note": {...}, "findings": {...}}`
    — return the inner row so callers can dot into columns directly."""
    r = client.get(f"/note-versions/{note_id}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    return body["note"] if "note" in body else body


# =========================================================================
# Pure service
# =========================================================================

def test_compare_typed_signature_case_sensitive_exact_match():
    from app.services.note_final_approval import compare_typed_signature
    r = compare_typed_signature(
        typed="Casey Clinician",
        stored_full_name="Casey Clinician",
    )
    assert r.matched is True
    assert r.reason is None


def test_compare_typed_signature_rejects_different_case():
    from app.services.note_final_approval import compare_typed_signature
    r = compare_typed_signature(
        typed="casey clinician",
        stored_full_name="Casey Clinician",
    )
    assert r.matched is False
    assert r.reason == "signature_mismatch"


def test_compare_typed_signature_rejects_wrong_name():
    from app.services.note_final_approval import compare_typed_signature
    r = compare_typed_signature(
        typed="Someone Else",
        stored_full_name="Casey Clinician",
    )
    assert r.matched is False
    assert r.reason == "signature_mismatch"


def test_compare_typed_signature_rejects_empty_typed():
    from app.services.note_final_approval import compare_typed_signature
    r = compare_typed_signature(typed="", stored_full_name="Casey Clinician")
    assert r.matched is False
    assert r.reason == "signature_required"


def test_compare_typed_signature_trims_edge_whitespace_only():
    from app.services.note_final_approval import compare_typed_signature
    # Leading/trailing trim is explicit policy.
    r = compare_typed_signature(
        typed="  Casey Clinician\n",
        stored_full_name="Casey Clinician",
    )
    assert r.matched is True
    # Interior whitespace NOT collapsed.
    r2 = compare_typed_signature(
        typed="Casey  Clinician",  # two interior spaces
        stored_full_name="Casey Clinician",
    )
    assert r2.matched is False
    assert r2.reason == "signature_mismatch"


def test_compare_typed_signature_flags_missing_stored_name():
    from app.services.note_final_approval import compare_typed_signature
    r = compare_typed_signature(typed="Casey", stored_full_name=None)
    assert r.matched is False
    assert r.expected_empty is True
    assert r.reason == "signer_has_no_stored_name"


def test_is_authorized_final_signer_requires_flag_and_active():
    from app.services.note_final_approval import is_authorized_final_signer
    assert is_authorized_final_signer(
        {"is_authorized_final_signer": True, "is_active": True}
    ) is True
    assert is_authorized_final_signer(
        {"is_authorized_final_signer": False, "is_active": True}
    ) is False
    # Inactive users cannot approve even with the flag — defence in
    # depth; removing a user should remove approval authority.
    assert is_authorized_final_signer(
        {"is_authorized_final_signer": True, "is_active": False}
    ) is False
    assert is_authorized_final_signer({}) is False
    assert is_authorized_final_signer(None) is False  # type: ignore[arg-type]


def test_export_requires_final_approval_matrix():
    from app.services.note_final_approval import export_requires_final_approval
    # Legacy rows (NULL status) are not gated.
    assert export_requires_final_approval({"final_approval_status": None}) is False
    assert export_requires_final_approval({}) is False
    # Pending + invalidated block export.
    assert export_requires_final_approval({"final_approval_status": "pending"}) is True
    assert export_requires_final_approval({"final_approval_status": "invalidated"}) is True
    # Approved allows export.
    assert export_requires_final_approval({"final_approval_status": "approved"}) is False


# =========================================================================
# /me exposes the flag
# =========================================================================

def test_me_exposes_is_authorized_final_signer(client):
    # Seeded: clin@chartnav.local is authorized; rev@chartnav.local is not.
    r_clin = client.get("/me", headers=CLIN1)
    assert r_clin.status_code == 200
    assert r_clin.json().get("is_authorized_final_signer") is True

    r_rev = client.get("/me", headers=REV1)
    assert r_rev.status_code == 200
    assert r_rev.json().get("is_authorized_final_signer") is False


# =========================================================================
# Sign stamps final_approval_status='pending' + full_name in attestation
# =========================================================================

def test_sign_stamps_pending_final_approval(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    signed = _sign(client, note["id"])
    assert signed["final_approval_status"] == "pending"
    assert signed["final_approved_at"] is None
    assert signed["final_approved_by_user_id"] is None
    assert signed["final_approval_signature_text"] is None
    # Attestation text freezes with the signer's full_name, not email
    # (Wave 7 changed this from `caller.email`). Casey Clinician is the
    # seeded full_name for clin@chartnav.local.
    assert signed["attestation_text"] is not None
    assert "Casey Clinician" in signed["attestation_text"]


# =========================================================================
# Export is gated on final approval
# =========================================================================

def test_export_blocked_while_final_approval_pending(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert r.status_code == 409, r.text
    body = r.json()["detail"]
    assert body["error_code"] == "export_blocked_by_gate"
    codes = {b["code"] for b in body["blockers"]}
    assert "final_approval_pending" in codes

    audits = _find_audit_events(test_db, "note_export_blocked")
    assert len(audits) >= 1
    assert audits[-1]["error_code"] == "export_blocked_by_gate"


def test_export_succeeds_after_final_approval(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    approved = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["final_approval_status"] == "approved"

    exported = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert exported.status_code == 200, exported.text
    assert exported.json()["draft_status"] == "exported"


# =========================================================================
# /final-approve — unauthorized
# =========================================================================

def test_final_approve_refuses_unauthorized_clinician(client, test_db):
    # Use northside org — Noa Clinician (CLIN2) is not flagged.
    note = _ingest_and_generate(client, encounter_id=3, headers=CLIN2)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"], headers=CLIN2)

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Noa Clinician"},
        headers=CLIN2,
    )
    assert r.status_code == 403, r.text
    body = r.json()["detail"]
    assert body["error_code"] == "role_cannot_final_approve"

    audits = _find_audit_events(test_db, "note_final_approval_unauthorized")
    assert len(audits) >= 1
    assert audits[-1]["error_code"] == "role_cannot_final_approve"


def test_final_approve_refuses_admin_without_flag(client, test_db):
    # ADMIN1 is NOT flagged. Role alone is insufficient.
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "ChartNav Admin"},
        headers=ADMIN1,
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["error_code"] == "role_cannot_final_approve"


def test_final_approve_refuses_reviewer(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Riley Reviewer"},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_final_approve"


# =========================================================================
# /final-approve — signature matching
# =========================================================================

def test_final_approve_rejects_wrong_case(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "casey clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error_code"] == "signature_mismatch"

    audits = _find_audit_events(test_db, "note_final_approval_signature_mismatch")
    assert len(audits) >= 1


def test_final_approve_rejects_wrong_name(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Someone Else"},
        headers=CLIN1,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "signature_mismatch"


def test_final_approve_rejects_whitespace_only(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    # pydantic min_length=1 accepts "   ", so this exercises the
    # post-trim check in compare_typed_signature.
    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "   "},
        headers=CLIN1,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "signature_required"


# =========================================================================
# /final-approve — success path
# =========================================================================

def test_final_approve_success_persists_fields(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["final_approval_status"] == "approved"
    assert row["final_approved_at"] is not None
    assert row["final_approved_by_user_id"] is not None
    assert row["final_approval_signature_text"] == "Casey Clinician"

    audits = _find_audit_events(test_db, "note_final_approved")
    assert len(audits) == 1
    assert audits[0]["actor_email"] == "clin@chartnav.local"


def test_final_approve_preserves_typed_verbatim_with_trim(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    # Typed with trailing newline — trimmed for compare, stored
    # verbatim-after-trim for audit.
    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician\n"},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    assert r.json()["final_approval_signature_text"] == "Casey Clinician"


def test_final_approve_idempotent_second_attempt_refused(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    first = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert first.status_code == 200

    second = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert second.status_code == 409
    assert second.json()["detail"]["error_code"] == "already_approved"


# =========================================================================
# /final-approve — state conflicts
# =========================================================================

def test_final_approve_refuses_unsigned_note(client, test_db):
    note = _ingest_and_generate(client)  # draft_status=draft
    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "not_signable_state"


def test_final_approve_cross_org_returns_404(client, test_db):
    # Note belongs to demo org; try to approve from northside.
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])

    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Noa Clinician"},
        headers=CLIN2,
    )
    # Same 404 shape the existing org-scope tests expect — the note
    # does not exist from the caller's org perspective.
    assert r.status_code == 404, r.text


# =========================================================================
# Amendment invalidates prior approval
# =========================================================================

def test_amendment_invalidates_approved_original(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])
    # Approve the original.
    approve = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert approve.status_code == 200

    # Now amend.
    amend = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended after review.\nASSESSMENT: corrected "
                "IOP. PLAN: continue meds.\n"
            ),
            "reason": "corrected IOP reading",
        },
        headers=CLIN1,
    )
    assert amend.status_code == 201, amend.text

    # Reload the ORIGINAL row and assert the approval was invalidated.
    original = _get_note(client, note["id"])
    assert original["final_approval_status"] == "invalidated"
    assert original["final_approval_invalidated_at"] is not None
    assert original["final_approval_invalidated_reason"] is not None
    # Preserved: original still shows who approved + the verbatim
    # signature, so the audit trail remains intact.
    assert original["final_approved_by_user_id"] is not None
    assert original["final_approval_signature_text"] == "Casey Clinician"

    invalidation_audits = _find_audit_events(
        test_db, "note_final_approval_invalidated"
    )
    assert len(invalidation_audits) == 1


def test_amendment_of_pending_does_not_emit_invalidation_audit(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])
    # Do NOT approve. Sign leaves status=pending.

    amend = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended pre-approval.\nASSESSMENT: fine.\nPLAN: fine.\n"
            ),
            "reason": "early edit after sign",
        },
        headers=CLIN1,
    )
    assert amend.status_code == 201

    original = _get_note(client, note["id"])
    # Status still flips to 'invalidated' (the pending approval no
    # longer applies to the record of care), but the dedicated
    # `note_final_approval_invalidated` audit event is ONLY emitted
    # when a real approval was invalidated — not when a mere pending.
    assert original["final_approval_status"] == "invalidated"
    invalidation_audits = _find_audit_events(
        test_db, "note_final_approval_invalidated"
    )
    assert invalidation_audits == []


def test_export_blocked_after_approval_invalidated_by_amendment(client, test_db):
    note = _ingest_and_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign(client, note["id"])
    client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    amend_resp = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended.\nASSESSMENT: corrected.\nPLAN: continue.\n"
            ),
            "reason": "correction needed",
        },
        headers=CLIN1,
    )
    assert amend_resp.status_code == 201

    # Export attempt on the ORIGINAL now fails with invalidated blocker.
    r = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert r.status_code == 409
    body = r.json()["detail"]
    assert body["error_code"] == "export_blocked_by_gate"
    codes = {b["code"] for b in body["blockers"]}
    assert "final_approval_invalidated" in codes
