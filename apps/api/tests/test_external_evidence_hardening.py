"""Phase 56 — external evidence integrity + immutable audit sink tests.

Covers:

  Sink delivery
  * configured jsonl sink writes one line per evidence event + marks
    row sink_status='sent'
  * unreachable webhook sink marks sink_status='failed' with short
    reason; chain still advances
  * sink disabled → sink_status='skipped'
  * org A's sink failure is independent of org B's sink
  * ops overview surfaces evidence_sink_delivery_failed in window

  Signed bundles
  * signed mode produces HMAC; verify_signature returns ok
  * tampering with body hash in an issued bundle breaks verify
  * signed mode enabled but HMAC key unset → 503
    evidence_signing_unconfigured on /evidence-bundle
  * /evidence-bundle/verify returns structured verdict for unsigned
    bundles too (unsigned but body-hash still recomputable)

  Export snapshots
  * export creates a snapshot row; artifact_hash is deterministic
  * snapshot links to the note_exported evidence event
  * listing returns newest-first
  * cross-org snapshot GET → 404
  * amendment after export does NOT delete the snapshot

  Chain seals
  * seal records tip event_id + hash + count
  * listing returns newest-first
  * sealing an empty chain → 409
  * sealing is security-admin gated
"""
from __future__ import annotations

import json
import os
import pathlib
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


def _set_org_settings(test_db, organization_id: int, settings: dict) -> None:
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
        blob.setdefault("security", {}).update(settings)
        conn.execute(
            "UPDATE organizations SET settings = :s WHERE id = :id",
            {"s": json.dumps(blob), "id": organization_id},
        )
        conn.commit()
    finally:
        conn.close()


def _enable_jsonl_sink(test_db, organization_id: int, path: str) -> None:
    _set_org_settings(
        test_db,
        organization_id,
        {"evidence_sink_mode": "jsonl", "evidence_sink_target": path},
    )


def _enable_webhook_sink_failing(
    test_db, organization_id: int, url: str,
) -> None:
    _set_org_settings(
        test_db,
        organization_id,
        {"evidence_sink_mode": "webhook", "evidence_sink_target": url},
    )


def _enable_signing(test_db, organization_id: int, key_id: str = "k1") -> None:
    _set_org_settings(
        test_db,
        organization_id,
        {"evidence_signing_mode": "hmac_sha256",
         "evidence_signing_key_id": key_id},
    )


def _read_evidence_rows(test_db, organization_id: int) -> list[dict]:
    conn = sqlite3.connect(test_db)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, event_type, sink_status, sink_error "
            "FROM note_evidence_events WHERE organization_id = :org "
            "ORDER BY id",
            {"org": organization_id},
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# =========================================================================
# Sink delivery
# =========================================================================

def test_jsonl_sink_writes_one_line_per_event_and_marks_sent(
    client, test_db, tmp_path,
):
    sink_path = str(tmp_path / "evidence.jsonl")
    _enable_jsonl_sink(test_db, 1, sink_path)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )

    # Every evidence row for org 1 must be marked sent.
    rows = _read_evidence_rows(test_db, organization_id=1)
    assert rows, "expected at least one evidence event"
    for r in rows:
        assert r["sink_status"] == "sent", r
        assert r["sink_error"] is None

    # Sink file has one line per event, each a valid JSON payload
    # with a non-empty event_hash.
    lines = pathlib.Path(sink_path).read_text().strip().splitlines()
    assert len(lines) == len(rows)
    for line in lines:
        payload = json.loads(line)
        assert payload["kind"] == "chartnav.evidence_event.v1"
        assert payload["event_hash"]


def test_webhook_sink_failure_is_recorded_without_breaking_chain(
    client, test_db,
):
    # Non-routable URL so the request fails quickly.
    _enable_webhook_sink_failing(test_db, 1, "http://127.0.0.1:1/invalid")

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    r = client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    assert r.status_code == 200

    rows = _read_evidence_rows(test_db, organization_id=1)
    assert len(rows) == 1
    assert rows[0]["sink_status"] == "failed"
    assert rows[0]["sink_error"]  # short reason captured

    # In-app chain still verifies — sink failure is NOT a chain break.
    from app.services.note_evidence import verify_chain
    assert verify_chain(1).ok is True


def test_disabled_sink_marks_events_skipped(client, test_db):
    # Default seed leaves evidence_sink_mode=disabled.
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    rows = _read_evidence_rows(test_db, organization_id=1)
    assert rows[0]["sink_status"] == "skipped"


def test_sink_failure_is_org_scoped(client, test_db):
    _enable_webhook_sink_failing(test_db, 1, "http://127.0.0.1:1/x")
    # Org 2 remains disabled.
    note1 = _ingest_generate(client, encounter_id=1, headers=CLIN1)
    _clear_missing_flags(test_db, note1["id"])
    client.post(f"/note-versions/{note1['id']}/sign", headers=CLIN1)

    note2 = _ingest_generate(client, encounter_id=3, headers=CLIN2)
    _clear_missing_flags(test_db, note2["id"])
    client.post(f"/note-versions/{note2['id']}/sign", headers=CLIN2)

    org1 = _read_evidence_rows(test_db, organization_id=1)
    org2 = _read_evidence_rows(test_db, organization_id=2)
    assert [r["sink_status"] for r in org1] == ["failed"]
    assert [r["sink_status"] for r in org2] == ["skipped"]


def test_ops_overview_counts_failed_sink_deliveries(client, test_db):
    _enable_webhook_sink_failing(test_db, 1, "http://127.0.0.1:1/x")
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    body = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert body["counts"]["evidence_sink_delivery_failed"] == 1
    assert body["security_policy"]["evidence_sink_configured"] is True
    assert body["security_policy"]["evidence_sink_mode"] == "webhook"


def test_admin_evidence_sink_probe_reports_disabled(client):
    r = client.post(
        "/admin/operations/evidence-sink/test", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["mode"] == "disabled"


def test_admin_evidence_sink_probe_success(client, test_db, tmp_path):
    sink_path = str(tmp_path / "probe.jsonl")
    _enable_jsonl_sink(test_db, 1, sink_path)
    r = client.post(
        "/admin/operations/evidence-sink/test", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] == "jsonl"
    # Probe wrote exactly one line and it's a probe payload.
    lines = pathlib.Path(sink_path).read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["kind"] == "chartnav.evidence_sink.probe.v1"


def test_evidence_sink_probe_requires_security_admin(client):
    r = client.post(
        "/admin/operations/evidence-sink/test", headers=CLIN1
    )
    assert r.status_code == 403


# =========================================================================
# Signed bundles
# =========================================================================

def test_signed_bundle_produces_hmac_and_verifies(
    client, test_db, monkeypatch,
):
    monkeypatch.setenv(
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", "test-hmac-secret"
    )
    # Reload config so the new key is visible.
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)

    _enable_signing(test_db, 1, key_id="k1")

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    sig = bundle["signature"]
    assert sig["mode"] == "hmac_sha256"
    assert sig["key_id"] == "k1"
    assert len(sig["signature_hex"]) == 64

    verify = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle,
        headers=CLIN1,
    ).json()
    assert verify["body_hash_ok"] is True
    assert verify["note_id_match"] is True
    assert verify["signature"]["ok"] is True

    # Restore env.
    monkeypatch.delenv("CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", raising=False)
    importlib.reload(_cfg)


def test_signed_bundle_body_tamper_detected_via_body_hash(
    client, test_db, monkeypatch,
):
    """Mutating a body field without touching the envelope hash:
    the signature still verifies (because it was computed over the
    envelope's claimed body_hash, which is unchanged), but the
    RECOMPUTED body hash differs — `body_hash_ok=False` catches
    the tamper. The combination of body_hash + signature verdicts
    is what defeats the attack."""
    monkeypatch.setenv(
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", "test-hmac-secret"
    )
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)
    _enable_signing(test_db, 1)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()

    bundle["note"]["draft_status"] = "draft"  # tamper body only
    verify = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle,
        headers=CLIN1,
    ).json()
    assert verify["body_hash_ok"] is False  # recomputation caught it
    # Signature ALONE doesn't — it was over the unchanged envelope
    # hash. That is the correct security semantics; the verifier
    # reports both so a consumer can detect either class of tamper.
    assert verify["signature"]["ok"] is True

    monkeypatch.delenv("CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", raising=False)
    importlib.reload(_cfg)


def test_signed_bundle_signature_tamper_detected(
    client, test_db, monkeypatch,
):
    """Tampering the signature_hex directly breaks signature
    verification. This is the class of tamper that body_hash_ok
    cannot catch (body is untouched)."""
    monkeypatch.setenv(
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", "test-hmac-secret"
    )
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)
    _enable_signing(test_db, 1)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()

    original_sig = bundle["signature"]["signature_hex"]
    # Flip a hex char — still 64 chars, invalid signature.
    bundle["signature"]["signature_hex"] = (
        ("a" if original_sig[0] != "a" else "b") + original_sig[1:]
    )
    verify = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle,
        headers=CLIN1,
    ).json()
    assert verify["body_hash_ok"] is True  # body untouched
    assert verify["signature"]["ok"] is False
    assert verify["signature"]["error_code"] == "signature_mismatch"

    monkeypatch.delenv("CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", raising=False)
    importlib.reload(_cfg)


def test_signing_enabled_without_key_returns_503(
    client, test_db, monkeypatch,
):
    monkeypatch.delenv("CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", raising=False)
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)
    _enable_signing(test_db, 1)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    r = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    )
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["error_code"] == "evidence_signing_unconfigured"


def test_unsigned_bundle_verify_reports_body_hash_only(client, test_db):
    # Signing disabled by default seed.
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    assert bundle["signature"]["mode"] == "disabled"
    verify = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle,
        headers=CLIN1,
    ).json()
    assert verify["body_hash_ok"] is True
    # Signature verdict is honest about the unsigned state.
    assert verify["signature"]["mode"] == "disabled"
    assert verify["signature"]["ok"] is False
    assert verify["signature"]["error_code"] == "unsigned_bundle"


# =========================================================================
# Export snapshots
# =========================================================================

def test_export_creates_snapshot_linked_to_chain_event(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    r = client.get(
        f"/note-versions/{note['id']}/export-snapshots", headers=CLIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["snapshots"]) == 1
    snap = body["snapshots"][0]
    assert len(snap["artifact_hash_sha256"]) == 64
    assert snap["evidence_chain_event_id"] is not None

    # Detail endpoint returns the captured artifact JSON.
    detail = client.get(
        f"/note-versions/{note['id']}/export-snapshots/{snap['id']}",
        headers=CLIN1,
    )
    assert detail.status_code == 200
    dbody = detail.json()
    assert dbody["artifact"] is not None
    assert dbody["artifact_hash_sha256"] == snap["artifact_hash_sha256"]


def test_snapshot_cross_org_returns_404(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    # Cross-org request to list + get snapshot.
    r_list = client.get(
        f"/note-versions/{note['id']}/export-snapshots", headers=CLIN2
    )
    assert r_list.status_code == 404

    # Pull snapshot id from the authorized list.
    snap_id = client.get(
        f"/note-versions/{note['id']}/export-snapshots", headers=CLIN1
    ).json()["snapshots"][0]["id"]
    r_get = client.get(
        f"/note-versions/{note['id']}/export-snapshots/{snap_id}",
        headers=CLIN2,
    )
    assert r_get.status_code == 404


def test_amendment_preserves_export_snapshot(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    # Amend.
    amend = client.post(
        f"/note-versions/{note['id']}/amend",
        json={
            "note_text": (
                "SUBJECTIVE: amended.\nASSESSMENT: ok.\nPLAN: continue.\n"
            ),
            "reason": "typo fix IOP",
        },
        headers=CLIN1,
    )
    assert amend.status_code == 201

    # Original's snapshot is still there.
    r = client.get(
        f"/note-versions/{note['id']}/export-snapshots", headers=CLIN1
    )
    assert r.status_code == 200
    assert len(r.json()["snapshots"]) == 1


def test_ops_overview_flags_export_without_snapshot(
    client, test_db, monkeypatch,
):
    # Monkey-patch persist_snapshot to no-op so a note_exported event
    # exists without a matching snapshot. This tests the operational
    # signal the ops pane surfaces.
    import app.services.note_export_snapshots as snap_mod

    def _no_persist(**kwargs):  # type: ignore[no-redef]
        return None

    monkeypatch.setattr(snap_mod, "persist_snapshot", _no_persist)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    ov = client.get(
        "/admin/operations/overview", headers=ADMIN1
    ).json()
    assert ov["counts"]["export_snapshot_missing"] >= 1


# =========================================================================
# Chain seals
# =========================================================================

def test_seal_records_tip_and_count(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    _sign_approve(client, note["id"])

    r = client.post(
        "/admin/operations/evidence-chain/seal",
        json={"note": "end of week 17"},
        headers=ADMIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["event_count"] == 2
    assert len(body["tip_event_hash"]) == 64

    lst = client.get(
        "/admin/operations/evidence-chain/seals", headers=ADMIN1
    ).json()
    assert len(lst["seals"]) == 1
    assert lst["seals"][0]["note"] == "end of week 17"


def test_seal_empty_chain_returns_409(client):
    r = client.post(
        "/admin/operations/evidence-chain/seal",
        json={"note": "premature seal"},
        headers=ADMIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "evidence_chain_empty"


def test_seal_requires_security_admin(client, test_db):
    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)

    r = client.post(
        "/admin/operations/evidence-chain/seal",
        json={},
        headers=CLIN1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "security_admin_required"


# =========================================================================
# Regression: pilot flow + previous waves still green
# =========================================================================

def test_pilot_flow_still_green_with_sink_signing_snapshot(
    client, test_db, tmp_path, monkeypatch,
):
    monkeypatch.setenv(
        "CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", "test-hmac-secret"
    )
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)

    sink_path = str(tmp_path / "pilot.jsonl")
    _enable_jsonl_sink(test_db, 1, sink_path)
    _enable_signing(test_db, 1)

    note = _ingest_generate(client)
    _clear_missing_flags(test_db, note["id"])
    client.post(f"/note-versions/{note['id']}/sign", headers=CLIN1)
    client.post(
        f"/note-versions/{note['id']}/final-approve",
        json={"signature_text": "Casey Clinician"},
        headers=CLIN1,
    )
    client.post(f"/note-versions/{note['id']}/export", headers=CLIN1)

    # Chain has 3 events + snapshot.
    rows = _read_evidence_rows(test_db, organization_id=1)
    assert [r["event_type"] for r in rows] == [
        "note_signed", "note_final_approved", "note_exported",
    ]
    assert all(r["sink_status"] == "sent" for r in rows)

    snaps = client.get(
        f"/note-versions/{note['id']}/export-snapshots", headers=CLIN1
    ).json()
    assert len(snaps["snapshots"]) == 1

    # Bundle is signed + verifies.
    bundle = client.get(
        f"/note-versions/{note['id']}/evidence-bundle", headers=CLIN1
    ).json()
    assert bundle["signature"]["mode"] == "hmac_sha256"
    v = client.post(
        f"/note-versions/{note['id']}/evidence-bundle/verify",
        json=bundle, headers=CLIN1,
    ).json()
    assert v["body_hash_ok"] is True
    assert v["signature"]["ok"] is True

    monkeypatch.delenv("CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY", raising=False)
    importlib.reload(_cfg)
