"""Phase 58 — practice backup / restore / reinstall recovery tests.

Covers:

  Build path
    * create endpoint returns a bundle with envelope + hash + counts
    * bundle round-trips (re-submit for validate returns ok=true)
    * bundle is deterministic given the same DB state (same hash)
    * history records the creation
    * role guard (only admin can create)

  Validation path
    * shape-level malformed bundle → malformed_bundle
    * version mismatch → backup_incompatible_bundle_version
    * tampered body → backup_hash_mismatch
    * cross-org mismatch → backup_org_mismatch
    * role guard

  Restore path
    * dry-run mode never writes + does not require confirm
    * non-empty target refuses with restore_target_not_empty
    * merge mode rejected with restore_mode_unsupported
    * cross-org bundle rejected
    * unsupported bundle_version rejected
    * missing confirm_destructive rejected when dry_run=false
    * full round-trip: org1 creates, org2 (empty) restores — refused
    * full round-trip: delete-and-reinstall (simulated by wiping
      org1's clinical tables) → restore succeeds + counts match
    * role guard (security-admin only)

  History
    * endpoint returns both backup_created and restore_applied
      events
    * cross-org isolation
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

def _ingest_sign(client, test_db, encounter_id: int = 1, headers=CLIN1) -> dict:
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
    # Clear the missing-data flags so sign is allowed.
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


def _wipe_clinical(test_db, organization_id: int = 1) -> None:
    """Simulate a 'delete + reinstall' for an org: drop all clinical
    rows but leave the org + users + seeded settings so the org is
    empty per the backup restore contract."""
    conn = sqlite3.connect(test_db)
    try:
        # Order matters — children first.
        conn.executescript(
            """
            DELETE FROM note_evidence_events;
            DELETE FROM note_export_snapshots;
            DELETE FROM evidence_chain_seals;
            DELETE FROM note_versions
              WHERE encounter_id IN (
                SELECT id FROM encounters WHERE organization_id = 1
              );
            DELETE FROM extracted_findings
              WHERE encounter_id IN (
                SELECT id FROM encounters WHERE organization_id = 1
              );
            DELETE FROM encounter_inputs
              WHERE encounter_id IN (
                SELECT id FROM encounters WHERE organization_id = 1
              );
            DELETE FROM workflow_events
              WHERE encounter_id IN (
                SELECT id FROM encounters WHERE organization_id = 1
              );
            DELETE FROM encounters WHERE organization_id = 1;
            DELETE FROM patients WHERE organization_id = 1;
            DELETE FROM providers WHERE organization_id = 1;
            DELETE FROM locations WHERE organization_id = 1;
            """
        )
        conn.commit()
    finally:
        conn.close()


# =========================================================================
# Create / download
# =========================================================================

def test_create_returns_bundle_with_envelope_and_counts(client, test_db):
    _ingest_sign(client, test_db)
    r = client.post(
        "/admin/practice-backup/create",
        json={"note": "weekly"}, headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["record_id"]
    assert len(body["hash_sha256"]) == 64
    assert body["bytes_size"] > 0
    # Seed creates 2 encounters for demo-eye-clinic; one note was
    # generated + signed in _ingest_sign.
    assert body["counts"]["encounters"] >= 1
    assert body["counts"]["note_versions"] >= 1
    # Bundle envelope carries the hash.
    envelope = body["bundle"]["envelope"]
    assert envelope["body_hash_sha256"] == body["hash_sha256"]
    assert body["bundle"]["bundle_version"] == "chartnav.practice_backup.v1"


def test_create_bundle_round_trips_validate(client, test_db):
    _ingest_sign(client, test_db)
    created = client.post(
        "/admin/practice-backup/create",
        json={}, headers=ADMIN1,
    ).json()
    v = client.post(
        "/admin/practice-backup/validate",
        json={"bundle": created["bundle"]}, headers=ADMIN1,
    ).json()
    assert v["ok"] is True
    assert v["body_hash_ok"] is True
    assert v["source_organization_id"] == 1


def test_create_is_deterministic_for_same_state(client, test_db):
    _ingest_sign(client, test_db)
    a = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()
    b = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()
    # Envelope.issued_at differs per call, but body_hash is over the
    # body EXCLUDING envelope → stable.
    assert a["hash_sha256"] == b["hash_sha256"]


def test_create_role_guard_requires_admin(client):
    r = client.post(
        "/admin/practice-backup/create", json={}, headers=CLIN1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_admin_required"


def test_create_records_history(client, test_db):
    _ingest_sign(client, test_db)
    client.post(
        "/admin/practice-backup/create",
        json={"note": "test"}, headers=ADMIN1,
    )
    h = client.get(
        "/admin/practice-backup/history", headers=ADMIN1,
    ).json()
    assert len(h["history"]) >= 1
    assert h["history"][0]["event_type"] == "backup_created"
    assert h["history"][0]["encounter_count"] >= 1
    assert h["history"][0]["note"] == "test"


def test_download_returns_attachment(client, test_db):
    _ingest_sign(client, test_db)
    r = client.get(
        "/admin/practice-backup/download", headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    assert (
        r.headers["content-type"].split(";")[0]
        == "application/vnd.chartnav.practice-backup+json"
    )
    assert "attachment" in r.headers["content-disposition"]
    assert "chartnav-backup-org1" in r.headers["content-disposition"]
    # Body parses as a valid bundle.
    bundle = json.loads(r.content)
    assert bundle["bundle_version"] == "chartnav.practice_backup.v1"


# =========================================================================
# Validation failure paths
# =========================================================================

def test_validate_rejects_malformed(client, test_db):
    r = client.post(
        "/admin/practice-backup/validate",
        json={"bundle": {"just": "junk"}}, headers=ADMIN1,
    ).json()
    assert r["ok"] is False
    assert r["error_code"] == "malformed_bundle"


def test_validate_rejects_wrong_version(client, test_db):
    _ingest_sign(client, test_db)
    b = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    b["bundle_version"] = "chartnav.practice_backup.v999"
    # Recompute body hash to avoid hash-mismatch firing first.
    import hashlib as _h
    import json as _j
    body_only = {k: v for k, v in b.items() if k != "envelope"}
    new_hash = _h.sha256(
        _j.dumps(body_only, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
    b["envelope"]["body_hash_sha256"] = new_hash
    r = client.post(
        "/admin/practice-backup/validate", json={"bundle": b}, headers=ADMIN1,
    ).json()
    assert r["ok"] is False
    assert r["error_code"] == "backup_incompatible_bundle_version"


def test_validate_detects_tampered_body(client, test_db):
    _ingest_sign(client, test_db)
    b = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    # Tamper without updating envelope hash.
    b["organization"]["name"] = "Tampered"
    r = client.post(
        "/admin/practice-backup/validate", json={"bundle": b}, headers=ADMIN1,
    ).json()
    assert r["ok"] is False
    assert r["error_code"] == "backup_hash_mismatch"


def test_validate_detects_cross_org_bundle(client, test_db):
    # Org 1 creates a bundle.
    _ingest_sign(client, test_db)
    b = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    # Org 2 admin validates it.
    r = client.post(
        "/admin/practice-backup/validate",
        json={"bundle": b}, headers=ADMIN2,
    ).json()
    assert r["ok"] is False
    assert r["error_code"] == "backup_org_mismatch"


# =========================================================================
# Restore path
# =========================================================================

def test_restore_refuses_non_empty_target(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle,
            "mode": "empty_target_only",
            "dry_run": False,
            "confirm_destructive": True,
        },
        headers=ADMIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "restore_target_not_empty"


def test_restore_refuses_merge_mode(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    # Even dry-run refuses unsupported mode.
    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle,
            "mode": "merge_preserve_existing",
            "dry_run": True,
            "confirm_destructive": False,
        },
        headers=ADMIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "restore_mode_unsupported"


def test_restore_refuses_cross_org(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    # Admin2 (different org) tries to restore an org1 bundle.
    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": True, "confirm_destructive": False,
        },
        headers=ADMIN2,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "backup_org_mismatch"


def test_restore_dry_run_does_not_write(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    _wipe_clinical(test_db, 1)

    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": True, "confirm_destructive": False,
        },
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True
    assert body["applied_counts"]["note_versions"] == 1

    # Confirm no rows actually landed.
    conn = sqlite3.connect(test_db)
    try:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM note_versions"
        ).fetchone()[0]
    finally:
        conn.close()
    assert cnt == 0


def test_restore_requires_confirm_destructive(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    _wipe_clinical(test_db, 1)

    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": False, "confirm_destructive": False,
        },
        headers=ADMIN1,
    )
    assert r.status_code == 409
    assert (
        r.json()["detail"]["error_code"] == "restore_requires_confirmation"
    )


def test_restore_round_trip_after_wipe(client, test_db):
    # Recovery scenario: create backup → wipe → restore.
    note = _ingest_sign(client, test_db)
    bundle_resp = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()
    bundle = bundle_resp["bundle"]
    hash_pre = bundle_resp["hash_sha256"]

    _wipe_clinical(test_db, 1)

    # Dry-run first.
    dry = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": True, "confirm_destructive": False,
        },
        headers=ADMIN1,
    ).json()
    assert dry["dry_run"] is True

    # Real restore.
    real = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": False, "confirm_destructive": True,
        },
        headers=ADMIN1,
    )
    assert real.status_code == 200, real.text
    rb = real.json()
    assert rb["dry_run"] is False
    assert rb["applied_counts"]["encounters"] >= 1
    assert rb["applied_counts"]["note_versions"] == 1

    # Sanity: the restored note is queryable.
    got = client.get(f"/note-versions/{note['id']}", headers=CLIN1)
    assert got.status_code == 200
    assert got.json()["note"]["id"] == note["id"]

    # A fresh backup after restore matches the pre-wipe hash (state
    # is deterministically restored). This is a strong contract.
    reissued = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()
    assert reissued["hash_sha256"] == hash_pre


def test_restore_role_guard_security_admin(client, test_db):
    _ingest_sign(client, test_db)
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    # Clinician cannot restore even in dry-run.
    r = client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": True, "confirm_destructive": False,
        },
        headers=CLIN1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "security_admin_required"


# =========================================================================
# History & regressions
# =========================================================================

def test_history_includes_both_event_types(client, test_db):
    _ingest_sign(client, test_db)
    # Issue + wipe + restore.
    bundle = client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    ).json()["bundle"]
    _wipe_clinical(test_db, 1)
    client.post(
        "/admin/practice-backup/restore",
        json={
            "bundle": bundle, "mode": "empty_target_only",
            "dry_run": False, "confirm_destructive": True,
        },
        headers=ADMIN1,
    )
    h = client.get(
        "/admin/practice-backup/history", headers=ADMIN1,
    ).json()
    types = [r["event_type"] for r in h["history"]]
    assert "backup_created" in types
    assert "restore_applied" in types


def test_history_cross_org_isolation(client, test_db):
    _ingest_sign(client, test_db)
    client.post(
        "/admin/practice-backup/create", json={}, headers=ADMIN1,
    )
    org2 = client.get(
        "/admin/practice-backup/history", headers=ADMIN2,
    ).json()
    # Org 2 sees nothing from org 1.
    assert all(
        r["event_type"] is not None for r in org2["history"]
    ), org2
    org2_org_ids = {
        r.get("organization_id", 2) for r in org2["history"]
    }
    assert org2_org_ids.issubset({2})


def test_pilot_flow_still_green_after_phase58(client, test_db):
    """Backup/restore adds endpoints but does not alter lifecycle,
    evidence, or admin flows. Quick sanity on the canonical pipeline."""
    note = _ingest_sign(client, test_db)
    r = client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    assert r.status_code == 200
    r = client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["draft_status"] == "exported"
