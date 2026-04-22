"""Phase 57 — evidence maturity + compliance hardening tests.

Covers:

  Keyring / rotation
    * old bundle signed with key_id "k1" still verifies after
      active key has rotated to "k2", provided k1 remains in the
      keyring
    * dropping k1 from the ring → old bundle reports
      `signing_key_not_in_keyring`
    * active key absent from ring → 503 evidence_signing_key_unknown
      on new bundle issuance
    * signing posture endpoint reports keyring state without
      leaking any secret

  Signed chain seals
    * seal write stamps seal_hash_sha256 and (when signing enabled)
      seal_signature_hex + seal_signing_key_id
    * seal verify returns hash_ok=True + signature_ok=True on
      clean row
    * tampering any canonical field breaks seal verification
    * bulk list with ?verify=true includes per-row verdict
    * single-seal verify endpoint returns the seal payload + verdict

  Sink retry
    * retry endpoint retries only rows with sink_status='failed'
    * increments sink_attempt_count
    * NEVER modifies event_hash / prev_event_hash / content_fingerprint
    * returns per-row results
    * retry is audited
    * retry requires security-admin

  Snapshot retention
    * policy write rejects < 90 days
    * null → no-op sweep
    * sweep in dry_run returns candidate ids without touching rows
    * sweep with dry_run=false clears artifact_json + stamps
      artifact_purged_at/reason, preserves hash + chain linkage
    * sweep does not touch rows younger than retention window
    * retention-sweep audited
    * retention-sweep requires security-admin

  Admin visibility
    * ops overview surfaces evidence_sink_retry_pending and
      evidence_signing_inconsistent
    * /admin/operations/signing-posture returns safe fields only
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

def _ingest_generate(client, encounter_id: int = 1, headers=CLIN1) -> dict:
    client.post(
        f"/encounters/{encounter_id}/inputs",
        json={"input_type": "text_paste", "transcript_text": TRANSCRIPT},
        headers=headers,
    )
    r = client.post(
        f"/encounters/{encounter_id}/notes/generate",
        json={}, headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["note"] if "note" in body else body


def _clear_missing_flags(test_db, note_id: int) -> None:
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_versions SET missing_data_flags = '[]' "
            "WHERE id = :id",
            {"id": note_id},
        )
        conn.commit()
    finally:
        conn.close()


def _sign_approve(client, note_id: int) -> None:
    r = client.post(f"/note-versions/{note_id}/sign", headers=CLIN1)
    assert r.status_code == 200, r.text
    r = client.post(
        f"/note-versions/{note_id}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text


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
    """Reload app.config with the given env overrides. Tests use
    this to simulate keyring changes without restarting."""
    import os
    # Clear any competing env values first.
    for k in list(os.environ):
        if k.startswith("CHARTNAV_EVIDENCE_SIGNING_"):
            del os.environ[k]
    for k, v in env.items():
        os.environ[k] = v
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)


# =========================================================================
# Keyring / rotation
# =========================================================================

def test_old_bundle_verifies_after_rotation_when_old_key_in_ring(
    client, test_db, monkeypatch,
):
    """Sign a bundle with k1, rotate active to k2, verify old bundle:
    still ok because k1 is still in the ring."""
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one", "k2": "secret-two"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k1",
    })

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    old_bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    assert old_bundle["signature"]["key_id"] == "k1"

    # Rotate: active key is now k2, but k1 remains in the ring.
    _set_org_settings(test_db, 1, {"evidence_signing_key_id": "k2"})
    verdict = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=old_bundle, headers=CLIN1,
    ).json()
    assert verdict["body_hash_ok"] is True
    assert verdict["signature"]["ok"] is True
    assert verdict["signature"]["key_id"] == "k1"

    _reload_config({})


def test_old_bundle_fails_verify_when_key_rotated_out(
    client, test_db, monkeypatch,
):
    """Drop k1 from the ring; old bundle reports
    signing_key_not_in_keyring."""
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one", "k2": "secret-two"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k1",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    old_bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    assert old_bundle["signature"]["key_id"] == "k1"

    # Purge k1 from the ring; rotate active to k2.
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k2": "secret-two"}),
    })
    _set_org_settings(test_db, 1, {"evidence_signing_key_id": "k2"})

    verdict = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=old_bundle, headers=CLIN1,
    ).json()
    assert verdict["body_hash_ok"] is True
    assert verdict["signature"]["ok"] is False
    assert verdict["signature"]["error_code"] == "signing_key_not_in_keyring"

    _reload_config({})


def test_new_bundle_503_when_active_key_missing_from_ring(
    client, test_db, monkeypatch,
):
    """Active key_id names a key not in the process ring → 503
    evidence_signing_key_unknown on new bundle issuance."""
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k99",  # not in the ring
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    r = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    )
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["error_code"] == "evidence_signing_key_unknown"

    _reload_config({})


def test_legacy_single_key_env_aliased_as_default(
    client, test_db, monkeypatch,
):
    """The legacy CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY env maps to
    key_id 'default' in the keyring so pre-rotation deploys keep
    working."""
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY": "legacy-secret",
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        # No key_id set — service falls back to "default".
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    assert bundle["signature"]["key_id"] == "default"

    verdict = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle, headers=CLIN1,
    ).json()
    assert verdict["signature"]["ok"] is True

    _reload_config({})


def test_signing_posture_endpoint_never_exposes_secrets(
    client, test_db, monkeypatch,
):
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one", "k2": "secret-two"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k1",
    })
    r = client.get(
        "/admin/operations/signing-posture", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "hmac_sha256"
    assert body["active_key_id"] == "k1"
    assert body["active_key_present"] is True
    assert set(body["keyring_key_ids"]) == {"k1", "k2"}
    assert body["inconsistent"] is False
    # Honest secrecy: no raw secret should leak through any field.
    assert "secret-one" not in json.dumps(body)
    assert "secret-two" not in json.dumps(body)
    _reload_config({})


def test_signing_posture_flags_inconsistent(client, test_db, monkeypatch):
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k99",
    })
    body = client.get(
        "/admin/operations/signing-posture", headers=ADMIN1
    ).json()
    assert body["active_key_id"] == "k99"
    assert body["active_key_present"] is False
    assert body["inconsistent"] is True
    _reload_config({})


# =========================================================================
# Signed chain seals
# =========================================================================

def test_seal_write_stamps_hash_and_signature(
    client, test_db, monkeypatch,
):
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k1",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    r = client.post(
        "/admin/operations/evidence-chain/seal",
        json={"note": "end of day"}, headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["seal_hash_sha256"]) == 64
    assert len(body["seal_signature_hex"]) == 64
    assert body["seal_signing_key_id"] == "k1"
    _reload_config({})


def test_seal_verify_ok_on_clean_row(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    seal = client.post(
        "/admin/operations/evidence-chain/seal",
        json={"note": "clean"}, headers=ADMIN1,
    ).json()
    v = client.get(
        f"/admin/operations/evidence-chain/seals/{seal['id']}/verify",
        headers=ADMIN1,
    ).json()
    assert v["verification"]["ok"] is True
    assert v["verification"]["hash_ok"] is True


def test_seal_verify_detects_tamper(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    seal = client.post(
        "/admin/operations/evidence-chain/seal",
        json={"note": "soon to be tampered"}, headers=ADMIN1,
    ).json()
    # Tamper: change the note text on the row without recomputing hash.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE evidence_chain_seals SET note = 'tampered' "
            "WHERE id = :id", {"id": seal["id"]},
        )
        conn.commit()
    finally:
        conn.close()
    v = client.get(
        f"/admin/operations/evidence-chain/seals/{seal['id']}/verify",
        headers=ADMIN1,
    ).json()
    assert v["verification"]["ok"] is False
    assert v["verification"]["hash_ok"] is False
    assert v["verification"]["error_code"] == "seal_hash_mismatch"


def test_seal_list_with_verify_query_param(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(
        "/admin/operations/evidence-chain/seal",
        json={}, headers=ADMIN1,
    )
    body = client.get(
        "/admin/operations/evidence-chain/seals?verify=true",
        headers=ADMIN1,
    ).json()
    assert "verification" in body["seals"][0]
    assert body["seals"][0]["verification"]["ok"] is True


def test_seal_verify_requires_security_admin(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    seal = client.post(
        "/admin/operations/evidence-chain/seal",
        json={}, headers=ADMIN1,
    ).json()
    r = client.get(
        f"/admin/operations/evidence-chain/seals/{seal['id']}/verify",
        headers=CLIN1,
    )
    assert r.status_code == 403


# =========================================================================
# Sink retry
# =========================================================================

def test_sink_retry_retries_only_failed_and_increments_count(
    client, test_db,
):
    # Failing webhook sink so the first-attempt write records failed.
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    # Confirm the row landed as failed with attempt_count=1.
    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, sink_status, sink_attempt_count, event_hash "
            "FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()
    finally:
        conn.close()
    original_hash = row["event_hash"]
    assert row["sink_status"] == "failed"
    assert row["sink_attempt_count"] == 1

    # Retry endpoint: still failing, so attempt_count climbs but
    # row stays failed. event_hash MUST NOT change.
    r = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={"max_events": 50}, headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attempted"] == 1
    assert body["failed"] == 1
    assert body["sent"] == 0

    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        row2 = conn.execute(
            "SELECT sink_status, sink_attempt_count, event_hash "
            "FROM note_evidence_events WHERE id = :id",
            {"id": row["id"]},
        ).fetchone()
    finally:
        conn.close()
    assert row2["sink_status"] == "failed"
    assert row2["sink_attempt_count"] == 2
    assert row2["event_hash"] == original_hash  # chain untouched


def test_sink_retry_succeeds_after_transport_repair(
    client, test_db, tmp_path,
):
    # Start with a broken webhook; first attempt fails.
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    # Operator "repairs" transport by switching to a working jsonl
    # target, then retries.
    sink_path = str(tmp_path / "repaired.jsonl")
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "jsonl",
        "evidence_sink_target": sink_path,
    })
    r = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={"max_events": 50}, headers=ADMIN1,
    )
    body = r.json()
    assert body["sent"] == 1
    assert body["failed"] == 0

    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT sink_status, sink_attempt_count "
            "FROM note_evidence_events WHERE organization_id = 1"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "sent"
    assert row[1] == 2  # 1 initial + 1 retry


def test_sink_retry_requires_security_admin(client, test_db):
    r = client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={}, headers=CLIN1,
    )
    assert r.status_code == 403


def test_sink_retry_audited(client, test_db):
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    client.post(
        "/admin/operations/evidence-sink/retry-failed",
        json={}, headers=ADMIN1,
    )
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM security_audit_events "
            "WHERE event_type = 'evidence_sink_retry_attempted'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] >= 1


# =========================================================================
# Snapshot retention
# =========================================================================

def test_retention_policy_rejects_below_floor(client, test_db):
    # Writing policy below 90 must 400.
    r = client.put(
        "/admin/security/policy",
        json={"export_snapshot_retention_days": 30},
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "policy_validation_failed"


def test_retention_policy_accepts_null_and_valid_value(client, test_db):
    # Null (retain forever) accepted.
    r_null = client.put(
        "/admin/security/policy",
        json={"export_snapshot_retention_days": None},
        headers=ADMIN1,
    )
    assert r_null.status_code == 200

    # >= floor accepted.
    r_ok = client.put(
        "/admin/security/policy",
        json={"export_snapshot_retention_days": 120},
        headers=ADMIN1,
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["policy"]["export_snapshot_retention_days"] == 120


def test_retention_sweep_noop_when_unconfigured(client, test_db):
    r = client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    ).json()
    assert r["retention_days"] is None
    assert r["candidates_found"] == 0


def test_retention_sweep_dry_run_then_soft_purge(client, test_db):
    # Create an exported note first.
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    # Backdate the snapshot's issued_at to 365 days ago.
    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            "UPDATE note_export_snapshots SET "
            "issued_at = datetime('now', '-365 days') "
            "WHERE note_version_id = :id",
            {"id": note["id"]},
        )
        conn.commit()
    finally:
        conn.close()

    # Configure 90-day retention.
    _set_org_settings(test_db, 1, {
        "export_snapshot_retention_days": 90,
    })

    # Dry run: candidates found, nothing purged.
    dry = client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    ).json()
    assert dry["candidates_found"] == 1
    assert dry["purged"] == 0

    # Snapshot body is still present.
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT artifact_json, artifact_purged_at, "
            "artifact_hash_sha256 FROM note_export_snapshots "
            "WHERE note_version_id = :id",
            {"id": note["id"]},
        ).fetchone()
    finally:
        conn.close()
    assert row[0]  # json still there
    assert row[1] is None  # purged_at null
    original_hash = row[2]

    # Real sweep: purges body but retains hash + linkage.
    real = client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": False}, headers=ADMIN1,
    ).json()
    assert real["purged"] == 1

    conn = sqlite3.connect(test_db)
    try:
        row2 = conn.execute(
            "SELECT artifact_json, artifact_purged_at, "
            "artifact_purged_reason, artifact_hash_sha256, "
            "evidence_chain_event_id "
            "FROM note_export_snapshots WHERE note_version_id = :id",
            {"id": note["id"]},
        ).fetchone()
    finally:
        conn.close()
    assert row2[0] == ""  # body cleared
    assert row2[1] is not None  # purged_at stamped
    assert row2[2]  # reason stamped
    assert row2[3] == original_hash  # hash preserved
    assert row2[4] is not None  # chain linkage preserved


def test_retention_sweep_leaves_young_snapshots_alone(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    _set_org_settings(test_db, 1, {
        "export_snapshot_retention_days": 90,
    })
    r = client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": False}, headers=ADMIN1,
    ).json()
    # Freshly-created snapshot → not a candidate.
    assert r["candidates_found"] == 0
    assert r["purged"] == 0


def test_retention_sweep_audited_and_role_gated(client, test_db):
    client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": True}, headers=ADMIN1,
    )
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM security_audit_events "
            "WHERE event_type = 'export_snapshot_retention_sweep'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] >= 1

    r = client.post(
        "/admin/operations/export-snapshots/retention-sweep",
        json={"dry_run": True}, headers=CLIN1,
    )
    assert r.status_code == 403


# =========================================================================
# Admin visibility (ops overview)
# =========================================================================

def test_ops_overview_surfaces_new_phase57_counters(client, test_db):
    # Cause a sink-failed row.
    _set_org_settings(test_db, 1, {
        "evidence_sink_mode": "webhook",
        "evidence_sink_target": "http://127.0.0.1:1/x",
    })
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    body = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert body["counts"]["evidence_sink_retry_pending"] >= 1
    # signing consistency is green when signing is disabled.
    assert body["counts"]["evidence_signing_inconsistent"] == 0
    # security_policy block surfaces retention + keyring posture.
    sp = body["security_policy"]
    assert "export_snapshot_retention_configured" in sp
    assert sp["evidence_signing_keyring_key_ids"] == []


def test_ops_overview_flags_signing_inconsistent(
    client, test_db, monkeypatch,
):
    _reload_config({
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS":
            json.dumps({"k1": "secret-one"}),
    })
    _set_org_settings(test_db, 1, {
        "evidence_signing_mode": "hmac_sha256",
        "evidence_signing_key_id": "k99",  # not in ring
    })
    body = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert body["counts"]["evidence_signing_inconsistent"] == 1
    _reload_config({})


# =========================================================================
# Regression — pilot flow still green
# =========================================================================

def test_pilot_flow_still_green(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    r = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["draft_status"] == "exported"
