"""Phase 59 — evidence operations, trust, retention closure tests.

Covers:

  Unified trust verdict
    * verified   when body hash + HMAC signature both ok
    * unsigned_ok when bundle has mode=disabled and body hash ok
    * failed_tamper when body hash recomputes differently
    * failed_signature when body hash ok but signature_hex mutated
    * stale_key when signing key_id is not in this host's keyring
    * stale_config when signing enabled but no keys configured

  Retry disposition lifecycle
    * first transport failure marks sink_retry_disposition='pending'
    * subsequent failures stay 'pending' until attempt_count crosses
      MAX_SINK_ATTEMPTS; then auto-promotes to 'permanent_failure'
    * successful retry clears disposition back to None
    * retry endpoint only picks pending/NULL rows (permanent_failure
      and abandoned rows are left alone)

  Abandon endpoint
    * 'failed' row flips to 'abandoned' + previous disposition surfaced
    * non-failed row → 409 abandon_not_applicable
    * cross-org/missing id → 404 evidence_event_not_found
    * security-admin only
    * audited

  Retention sweep
    * no-op when evidence_sink_retention_days is null
    * policy rejects < 7 days
    * dry-run returns candidates without clearing
    * real sweep clears sink_error only on abandoned /
      permanent_failure rows older than retention; NEVER touches
      canonical chain columns
    * audited + security-admin gated

  Ops overview
    * retry_pending counter counts only pending rows
    * permanent_failure counter counts auto-promoted + abandoned
    * security_policy block surfaces evidence_sink_max_attempts +
      retention config
"""
from __future__ import annotations

import json
import sqlite3

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


TRANSCRIPT = (
    "Patient presents for follow-up. VA 20/20 OD, 20/25 OS. IOP 14 OD, "
    "16 OS. Anterior segment quiet. Plan: continue current meds."
)


# ---------- helpers -------------------------------------------------------

def _ingest_sign(client, test_db, headers=CLIN1, encounter_id: int = 1) -> dict:
    client.post(
        f"/encounters/{encounter_id}/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=headers,
    )
    gen = client.post(
        f"/encounters/{encounter_id}/notes/generate",
        json={}, headers=headers,
    )
    assert gen.status_code == 201, gen.text
    note = gen.json()["note"]
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_versions SET missing_data_flags = '[]' WHERE id = :id",
            {"id": note["id"]},
        )
        conn.commit()
    finally:
        conn.close()
    r = client.post(f"/note-versions/{note['id']}/sign", headers=headers)
    assert r.status_code == 200, r.text
    return note


def _set_org_settings(test_db, organization_id: int, updates: dict) -> None:
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT settings FROM organizations WHERE id = :id",
            {"id": organization_id},
        ).fetchone()
        blob = {}
        if row and row[0]:
            try:
                blob = json.loads(row[0])
            except Exception:
                blob = {}
        blob.setdefault("security", {}).update(updates)
        conn.execute(
            "UPDATE organizations SET settings = :s WHERE id = :id",
            {"s": json.dumps(blob), "id": organization_id},
        )
        conn.commit()
    finally:
        conn.close()


def _reload_config(env: dict[str, str]) -> None:
    import os
    for k in list(os.environ):
        if k.startswith("CHARTNAV_EVIDENCE_SIGNING_"):
            del os.environ[k]
    for k, v in env.items():
        os.environ[k] = v
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)


# =========================================================================
# Unified trust verdict
# =========================================================================

def test_classify_bundle_trust_verified_and_unsigned(client, test_db):
    """Pure service-layer check: verified + unsigned_ok are the
    only ok=true categories."""
    from app.services.note_evidence import classify_bundle_trust
    v = classify_bundle_trust(
        True, {"mode": "hmac_sha256", "ok": True, "error_code": None}
    )
    assert v["category"] == "verified"
    assert v["ok"] is True
    v2 = classify_bundle_trust(True, {"mode": "disabled"})
    assert v2["category"] == "unsigned_ok"
    assert v2["ok"] is True


def test_classify_bundle_trust_failure_categories():
    from app.services.note_evidence import classify_bundle_trust
    # Tamper.
    t = classify_bundle_trust(
        False, {"mode": "hmac_sha256", "ok": True}
    )
    assert t["category"] == "failed_tamper"
    # Signature-only failure.
    s = classify_bundle_trust(
        True,
        {"mode": "hmac_sha256", "ok": False,
         "error_code": "signature_mismatch"},
    )
    assert s["category"] == "failed_signature"
    # Stale key.
    k = classify_bundle_trust(
        True,
        {"mode": "hmac_sha256", "ok": False,
         "error_code": "signing_key_not_in_keyring"},
    )
    assert k["category"] == "stale_key"
    # Stale config.
    c = classify_bundle_trust(
        True,
        {"mode": "hmac_sha256", "ok": False,
         "error_code": "evidence_signing_unconfigured"},
    )
    assert c["category"] == "stale_config"
    # Unverifiable.
    u = classify_bundle_trust(
        True,
        {"mode": "hmac_sha256", "ok": False,
         "error_code": "malformed_signature"},
    )
    assert u["category"] == "unverifiable"


def test_verify_endpoint_includes_unified_trust_field(client, test_db):
    note = _ingest_sign(client, test_db)
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    r = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle, headers=CLIN1,
    ).json()
    assert "trust" in r
    assert r["trust"]["category"] in {"verified", "unsigned_ok"}


# =========================================================================
# Retry disposition lifecycle
# =========================================================================

def test_first_failure_marks_disposition_pending(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT sink_status, sink_retry_disposition, sink_attempt_count "
            "FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()
    finally:
        conn.close()
    assert row["sink_status"] == "failed"
    assert row["sink_retry_disposition"] == "pending"
    assert row["sink_attempt_count"] == 1


def test_retry_cap_auto_promotes_to_permanent_failure(client, test_db):
    """Drive the row past MAX_SINK_ATTEMPTS via repeated retries."""
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)

    from app.services.evidence_sink import MAX_SINK_ATTEMPTS
    # Initial attempt already happened on sign. We need
    # MAX_SINK_ATTEMPTS-1 more to cross the cap.
    for _ in range(MAX_SINK_ATTEMPTS - 1):
        r = client.post(
            "/admin/operations/evidence-sink/retry-failed",
            json={}, headers=ADMIN1,
        )
        assert r.status_code == 200

    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT sink_status, sink_retry_disposition, sink_attempt_count "
            "FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()
    finally:
        conn.close()
    assert row["sink_attempt_count"] >= MAX_SINK_ATTEMPTS
    assert row["sink_retry_disposition"] == "permanent_failure"

    # Next retry-failed call finds no rows (permanent_failure is
    # excluded from the retry pool).
    r = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={}, headers=ADMIN1,
    ).json()
    assert r["attempted"] == 0


def test_successful_retry_clears_disposition(client, test_db, tmp_path):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    # Repair transport.
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "jsonl",
        "evidence_sink_target": str(tmp_path / "sink.jsonl"),
    })
    r = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={}, headers=ADMIN1,
    ).json()
    assert r["sent"] == 1

    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT sink_status, sink_retry_disposition "
            "FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()
    finally:
        conn.close()
    assert row["sink_status"] == "sent"
    assert row["sink_retry_disposition"] is None


# =========================================================================
# Abandon endpoint
# =========================================================================

def test_abandon_failed_event_flips_disposition(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    r = client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "known-bad SIEM URL"},
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["previous_disposition"] == "pending"
    assert body["new_disposition"] == "abandoned"

    # Retry-failed will not touch it.
    r2 = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={}, headers=ADMIN1,
    ).json()
    assert r2["attempted"] == 0


def test_abandon_sent_event_returns_409(client, test_db, tmp_path):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "jsonl",
        "evidence_sink_target": str(tmp_path / "ok.jsonl"),
    })
    _ingest_sign(client, test_db)  # sent=success, nothing to abandon
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    r = client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "x"}, headers=ADMIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "abandon_not_applicable"


def test_abandon_requires_security_admin(client, test_db):
    r = client.post(
        "/admin/operations/evidence-events/1/abandon",
        json={"reason": "x"}, headers=CLIN1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "security_admin_required"


def test_abandon_cross_org_returns_404(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    # Admin of org 2 cannot abandon an org 1 event.
    r = client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "nope"}, headers=ADMIN2,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "evidence_event_not_found"


def test_abandon_is_audited(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "ops decision"}, headers=ADMIN1,
    )
    conn = sqlite3.connect(test_db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM security_audit_events "
            "WHERE event_type = 'evidence_event_abandoned'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n >= 1


# =========================================================================
# Retention sweep
# =========================================================================

def test_sink_retention_policy_rejects_below_floor(client, test_db):
    r = client.put(
        "/admin/security/policy",
        json={"evidence_sink_retention_days": 3},
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "policy_validation_failed"


def test_sink_retention_policy_accepts_valid_and_null(client, test_db):
    r_ok = client.put(
        "/admin/security/policy",
        json={"evidence_sink_retention_days": 30}, headers=ADMIN1,
    )
    assert r_ok.status_code == 200
    assert (
        r_ok.json()["policy"]["evidence_sink_retention_days"] == 30
    )
    r_null = client.put(
        "/admin/security/policy",
        json={"evidence_sink_retention_days": None}, headers=ADMIN1,
    )
    assert r_null.status_code == 200


def test_sink_retention_sweep_noop_when_unconfigured(client, test_db):
    r = client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    ).json()
    assert r["retention_days"] is None
    assert r["candidates_found"] == 0


def test_sink_retention_sweep_clears_noise_not_chain(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    # Abandon the event, then backdate sink_attempted_at.
    client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "backdated"}, headers=ADMIN1,
    )
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_evidence_events SET "
            "sink_attempted_at = datetime('now', '-30 days') "
            "WHERE id = :id", {"id": eid},
        )
        conn.commit()
        before = conn.execute(
            "SELECT sink_error, event_hash, prev_event_hash FROM "
            "note_evidence_events WHERE id = :id", {"id": eid},
        ).fetchone()
    finally:
        conn.close()
    assert before[0] is not None
    original_hash = before[1]

    _set_org_settings(test_db, 1, {"evidence_sink_retention_days": 7})

    # Dry run first.
    dry = client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    ).json()
    assert dry["candidates_found"] == 1
    assert dry["cleared"] == 0

    real = client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": False}, headers=ADMIN1,
    ).json()
    assert real["cleared"] == 1

    conn = sqlite3.connect(test_db)
    try:
        after = conn.execute(
            "SELECT sink_error, event_hash, prev_event_hash, "
            "sink_retry_disposition FROM note_evidence_events "
            "WHERE id = :id", {"id": eid},
        ).fetchone()
    finally:
        conn.close()
    assert after[0] is None  # sink_error cleared
    assert after[1] == original_hash  # canonical hash preserved
    assert after[3] == "abandoned"  # disposition preserved


def test_sink_retention_sweep_leaves_young_rows_alone(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "fresh"}, headers=ADMIN1,
    )
    _set_org_settings(test_db, 1, {"evidence_sink_retention_days": 7})
    r = client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": False}, headers=ADMIN1,
    ).json()
    # The row was abandoned just now, so well within the 7-day
    # window — nothing cleared.
    assert r["candidates_found"] == 0


def test_sink_retention_sweep_role_guard_and_audit(client, test_db):
    r = client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": True}, headers=CLIN1,
    )
    assert r.status_code == 403
    # Admin call emits audit.
    client.post(
        "/admin/operations/evidence-sink/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    )
    conn = sqlite3.connect(test_db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM security_audit_events "
            "WHERE event_type = 'evidence_sink_retention_sweep'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n >= 1


# =========================================================================
# Ops overview counters
# =========================================================================

def test_ops_overview_distinguishes_pending_vs_permanent(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    _ingest_sign(client, test_db)
    # One pending row in the overview.
    ov = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert ov["counts"]["evidence_sink_retry_pending"] == 1
    assert ov["counts"]["evidence_sink_permanent_failure"] == 0

    # Abandon → flips to permanent_failure bucket.
    conn = sqlite3.connect(test_db)
    try:
        eid = conn.execute(
            "SELECT id FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()[0]
    finally:
        conn.close()
    client.post(
        f"/admin/operations/evidence-events/{eid}/abandon",
        json={"reason": "x"}, headers=ADMIN1,
    )
    ov2 = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert ov2["counts"]["evidence_sink_retry_pending"] == 0
    assert ov2["counts"]["evidence_sink_permanent_failure"] == 1


def test_overview_security_policy_block_exposes_max_attempts(client, test_db):
    r = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    sp = r["security_policy"]
    assert "evidence_sink_max_attempts" in sp
    assert sp["evidence_sink_max_attempts"] >= 1
    assert "evidence_sink_retention_configured" in sp


# =========================================================================
# Regression — lifecycle, backup, evidence still good
# =========================================================================

def test_pilot_flow_still_green_after_phase59(client, test_db):
    note = _ingest_sign(client, test_db)
    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"}, headers=CLIN1,
    )
    assert r.status_code == 200
    r = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["draft_status"] == "exported"
