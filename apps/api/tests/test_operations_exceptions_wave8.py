"""Phase 53 — Wave 8 operations & exceptions control plane tests.

Covers:

  - pure service layer
      * category taxonomy + metadata shape
      * EVENT_TO_CATEGORY mapping round-trips
      * _window clamps correctly

  - HTTP routes
      * /admin/operations/overview counters reflect live and
        windowed sources; security-policy status honest
      * /admin/operations/blocked-notes merges sign+export rows
      * /admin/operations/final-approval-queue returns pending
        + invalidated from note_versions
      * /admin/operations/identity-exceptions returns real
        auth-denial events; scim_configured=False honest flag
      * /admin/operations/session-exceptions
      * /admin/operations/stuck-ingest reads encounter_inputs
      * /admin/operations/security-config-status flags unconfigured
      * /admin/operations/categories publishes the taxonomy
      * every route: 403 for non-admin clinician, 403 for reviewer,
        200 for admin (default seeded — empty allowlist implies
        admin == security_admin)

  - cross-org isolation
      * counters + lists scoped to caller.organization_id

  - no regressions: sign / approve / export pipeline still works
"""
from __future__ import annotations

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


def _seed_audit_row(
    test_db,
    *,
    event_type: str,
    organization_id: int,
    actor_email: str = "probe@example.com",
    error_code: str | None = None,
    detail: str | None = None,
) -> None:
    """Write a raw security_audit_events row. Used to manufacture
    identity / session exceptions without actually exercising the
    full auth path, which is brittle under the TestClient."""
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "INSERT INTO security_audit_events "
            "(event_type, request_id, actor_email, organization_id, "
            "error_code, detail, created_at) "
            "VALUES (:et, :rid, :email, :org, :ec, :det, "
            "CURRENT_TIMESTAMP)",
            {
                "et": event_type,
                "rid": "test",
                "email": actor_email,
                "org": organization_id,
                "ec": error_code,
                "det": detail,
            },
        )
        conn.commit()
    finally:
        conn.close()


# =========================================================================
# Pure service
# =========================================================================

def test_categories_enum_is_stable_and_all_metadata_covered():
    from app.services.operations_exceptions import (
        CATEGORY_METADATA,
        ExceptionCategory,
    )
    # Every enum value has metadata.
    for c in ExceptionCategory:
        meta = CATEGORY_METADATA[c]
        assert meta["label"]
        assert meta["severity"] in {"info", "warning", "error"}
        assert meta["next_step"]


def test_event_to_category_covers_known_denial_types():
    from app.services.operations_exceptions import EVENT_TO_CATEGORY
    # Spot-check the codes we know the platform emits today.
    assert "note_sign_blocked" in EVENT_TO_CATEGORY
    assert "note_export_blocked" in EVENT_TO_CATEGORY
    assert "note_final_approval_invalidated" in EVENT_TO_CATEGORY
    assert "note_final_approval_signature_mismatch" in EVENT_TO_CATEGORY
    assert "note_final_approval_unauthorized" in EVENT_TO_CATEGORY
    assert "unknown_user" in EVENT_TO_CATEGORY
    assert "token_expired" in EVENT_TO_CATEGORY
    assert "session_revoked" in EVENT_TO_CATEGORY


def test_window_clamps_extreme_input():
    from app.services.operations_exceptions import _window
    since, until, _, _ = _window(0)   # clamped up to 1h
    assert (until - since).total_seconds() >= 3600 - 1
    since, until, _, _ = _window(10_000)  # clamped down to 31d
    assert (until - since).days <= 31


# =========================================================================
# /admin/operations/overview — counters
# =========================================================================

def test_overview_requires_security_admin(client):
    # Reviewer + clinician cannot read.
    r_clin = client.get("/admin/operations/overview", headers=CLIN1)
    assert r_clin.status_code == 403
    assert r_clin.json()["detail"]["error_code"] == "security_admin_required"

    r_rev = client.get("/admin/operations/overview", headers=REV1)
    assert r_rev.status_code == 403


def test_overview_returns_zeroes_for_fresh_org(client):
    r = client.get("/admin/operations/overview", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organization_id"] == 1
    assert "counts" in body
    # Every category key is present so the UI never has to guard.
    assert "final_approval_pending" in body["counts"]
    assert "governance_sign_blocked" in body["counts"]
    assert "identity_unknown_user" in body["counts"]
    assert body["counts"]["final_approval_pending"] == 0
    # security_policy block is populated and honest.
    sec = body["security_policy"]
    assert sec["session_tracking_configured"] in (True, False)
    assert sec["audit_sink_configured"] in (True, False)
    assert "unconfigured" in sec


def test_overview_counts_live_final_approval_pending(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    # Now this org has exactly one pending final approval.
    r = client.get("/admin/operations/overview", headers=ADMIN1)
    body = r.json()
    assert body["counts"]["final_approval_pending"] == 1
    # total_open reflects it.
    assert body["total_open"] >= 1


def test_overview_counts_sign_blocked_audit_events(client, test_db):
    # Simulate a blocked-sign by poking the audit row directly.
    # The route layer already emits these on real missing-data
    # blocks; the service-level contract we are testing is:
    # "N audit rows → N in the counter for the window".
    for _ in range(3):
        _seed_audit_row(
            test_db,
            event_type="note_sign_blocked",
            organization_id=1,
            error_code="sign_blocked_by_gate",
            detail="note_id=99 blockers=['note_text_empty']",
        )
    r = client.get("/admin/operations/overview", headers=ADMIN1)
    assert r.json()["counts"]["governance_sign_blocked"] == 3


def test_overview_counters_are_org_scoped(client, test_db):
    _seed_audit_row(
        test_db, event_type="note_sign_blocked", organization_id=1,
        error_code="sign_blocked_by_gate",
    )
    _seed_audit_row(
        test_db, event_type="note_sign_blocked", organization_id=2,
        error_code="sign_blocked_by_gate",
    )
    r1 = client.get("/admin/operations/overview", headers=ADMIN1).json()
    r2 = client.get("/admin/operations/overview", headers=ADMIN2).json()
    assert r1["counts"]["governance_sign_blocked"] == 1
    assert r2["counts"]["governance_sign_blocked"] == 1


def test_security_policy_status_flags_unconfigured(client):
    # Fresh org — no timeouts, no sink, no allowlist → unconfigured.
    r = client.get(
        "/admin/operations/security-config-status", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["unconfigured"] is True
    assert body["session_tracking_configured"] is False
    assert body["audit_sink_configured"] is False
    assert body["mfa_required"] is False


# =========================================================================
# /admin/operations/blocked-notes
# =========================================================================

def test_blocked_notes_surfaces_real_sign_block(client, test_db):
    # Generate a note but DO NOT clear missing_data_flags — sign
    # will be blocked by the real gate. This exercises the audit
    # write path end-to-end.
    note = _ingest_generate(client)
    r = client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    assert r.status_code == 409  # sign_blocked_by_gate

    r = client.get("/admin/operations/blocked-notes", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"], "expected at least one blocked-sign row"
    cats = {it["category"] for it in body["items"]}
    assert "governance_sign_blocked" in cats
    # Each row carries the operational context the UI needs.
    top = body["items"][0]
    assert "label" in top and top["label"]
    assert "next_step" in top and top["next_step"]
    assert "severity" in top


def test_blocked_notes_requires_security_admin(client):
    r = client.get("/admin/operations/blocked-notes", headers=CLIN1)
    assert r.status_code == 403


# =========================================================================
# /admin/operations/final-approval-queue
# =========================================================================

def test_final_approval_queue_lists_pending(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    r = client.get(
        "/admin/operations/final-approval-queue", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["pending"]) == 1
    item = body["pending"][0]
    assert item["category"] == "final_approval_pending"
    assert item["note_id"] == note["id"]
    assert item["final_approval_status"] == "pending"
    assert body["invalidated"] == []


def test_final_approval_queue_lists_invalidated(client, test_db):
    # Create signed+approved note, then amend to invalidate.
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    amend = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": "SUBJECTIVE: amended.\nASSESSMENT: ok.\nPLAN: ok.\n",
            "reason": "typo fix on IOP",
        },
        headers=CLIN1,
    )
    assert amend.status_code == 201

    r = client.get(
        "/admin/operations/final-approval-queue", headers=ADMIN1
    )
    body = r.json()
    assert len(body["invalidated"]) == 1
    item = body["invalidated"][0]
    assert item["note_id"] == note["id"]
    assert item["final_approval_status"] == "invalidated"
    assert item["detail"]  # reason string present


# =========================================================================
# /admin/operations/identity-exceptions
# =========================================================================

def test_identity_exceptions_surfaces_unknown_user_and_token_denials(
    client, test_db,
):
    _seed_audit_row(
        test_db, event_type="unknown_user", organization_id=1,
        error_code="unknown_user",
        detail="claim=email=stranger@example.com",
    )
    _seed_audit_row(
        test_db, event_type="invalid_issuer", organization_id=1,
        error_code="invalid_issuer",
    )
    _seed_audit_row(
        test_db, event_type="cross_org_access_forbidden",
        organization_id=1,
        error_code="cross_org_access_forbidden",
    )
    r = client.get(
        "/admin/operations/identity-exceptions", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    # Honest metadata: no fake SCIM claim.
    assert body["scim_configured"] is False
    assert body["oidc_identity_mapping"] == "email_claim_lookup"
    cats = {it["category"] for it in body["items"]}
    assert "identity_unknown_user" in cats
    assert "identity_invalid_issuer" in cats
    assert "identity_cross_org_attempt" in cats


def test_identity_exceptions_requires_security_admin(client):
    r = client.get("/admin/operations/identity-exceptions", headers=CLIN1)
    assert r.status_code == 403


# =========================================================================
# /admin/operations/session-exceptions
# =========================================================================

def test_session_exceptions_surfaces_revocations(client, test_db):
    _seed_audit_row(
        test_db, event_type="session_revoked", organization_id=1,
        error_code="session_revoked",
    )
    _seed_audit_row(
        test_db, event_type="session_idle_timeout", organization_id=1,
        error_code="session_idle_timeout",
    )
    r = client.get("/admin/operations/session-exceptions", headers=ADMIN1)
    body = r.json()
    cats = {it["category"] for it in body["items"]}
    assert "session_revoked_active" in cats
    assert "session_idle_timeout" in cats


# =========================================================================
# /admin/operations/stuck-ingest
# =========================================================================

def test_stuck_ingest_surfaces_failed_inputs(client, test_db):
    # Manufacture a failed ingest row.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "INSERT INTO encounter_inputs "
            "(encounter_id, input_type, processing_status, last_error_code, "
            "retry_count, created_at, updated_at) "
            "VALUES (1, 'text_paste', 'failed', 'stub_transcription_failed', "
            "3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )
        conn.commit()
    finally:
        conn.close()

    r = client.get("/admin/operations/stuck-ingest", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["error_code"] == "stub_transcription_failed"
    assert body["items"][0]["category"] == "ingest_stuck"


# =========================================================================
# /admin/operations/categories
# =========================================================================

def test_categories_endpoint_publishes_taxonomy(client):
    r = client.get("/admin/operations/categories", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    values = {c["value"] for c in body["categories"]}
    assert "final_approval_pending" in values
    assert "governance_sign_blocked" in values
    assert "identity_unknown_user" in values
    # Every row has label + severity + next_step for the UI.
    for c in body["categories"]:
        assert c["label"]
        assert c["severity"] in {"info", "warning", "error"}
        assert c["next_step"]


# =========================================================================
# Cross-org isolation
# =========================================================================

def test_ops_endpoints_scope_to_caller_org(client, test_db):
    # Create a pending approval in org 1; admin from org 2 must
    # not see it.
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    org1 = client.get(
        "/admin/operations/final-approval-queue", headers=ADMIN1
    ).json()
    org2 = client.get(
        "/admin/operations/final-approval-queue", headers=ADMIN2
    ).json()
    assert len(org1["pending"]) == 1
    assert len(org2["pending"]) == 0


# =========================================================================
# Regression — pilot flow still works
# =========================================================================

def test_pilot_flow_still_green_after_wave8(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    signed = client.post(
        f"/note-versions/{note['id']}/sign", headers=CLIN1
    ).json()
    assert signed["draft_status"] == "signed"
    approved = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    ).json()
    assert approved["final_approval_status"] == "approved"
    exported = client.post(
        f"/note-versions/{note['id']}/export", headers=CLIN1
    ).json()
    assert exported["draft_status"] == "exported"
