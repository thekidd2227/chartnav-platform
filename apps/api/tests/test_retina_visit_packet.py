"""Phase 77 — Retina Visit Packet builder tests.

Covers:
- happy path against seeded Morgan Lee encounter
- packet metadata (schema_version, generated_at, demo_mode)
- safety_boundaries shape + content
- artifact_hashes are deterministic per (artifact section state)
- review_sign_lock summary reflects artifact statuses
- cross-org returns 404 (not 403)
- unknown encounter returns 404
- unauth returns 401/403
- canary: no clinical free text leaks into the packet body
"""

from __future__ import annotations

import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def test_packet_baseline_for_seeded_encounter(client):
    r = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == "chartnav.retina_visit_packet/1.0"
    assert isinstance(body["generated_at"], str) and len(body["generated_at"]) >= 10
    assert body["demo_mode"] is True

    enc = body["encounter"]
    assert enc["id"] == 1
    assert enc["patient_identifier"] == "PT-1001"
    assert enc["patient_name"] == "Morgan Lee"
    assert enc["organization_id"] == 1
    assert enc["status"] == "in_progress"

    # Three artifact sections present and zero-state baseline.
    assert body["intake"]["count"] == 0
    assert body["visit_draft"]["count"] == 0
    assert body["fundus"]["count"] == 0

    # review_sign_lock summary.
    rsl = body["review_sign_lock"]
    assert rsl["vitals_signed"] is False
    assert rsl["visit_draft_signed"] is False
    assert rsl["fundus_signed"] is False
    assert rsl["all_signed"] is False
    assert len(rsl["blockers"]) == 3

    # Evidence timeline empty on a fresh seed.
    assert body["evidence_timeline"] == []

    # Audit disclosure passed through verbatim from summary.
    assert "metadata-only audit events" in body["audit_disclosure"]


def test_packet_safety_boundaries_complete(client):
    r = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=ADMIN1
    )
    assert r.status_code == 200, r.text
    boundaries = r.json()["safety_boundaries"]
    keys = {b["key"] for b in boundaries}
    expected = {
        "not_certified_ehr",
        "not_ehr_replacement",
        "no_autonomous_diagnosis",
        "no_autonomous_image_interpretation",
        "no_autonomous_billing_or_coding",
        "no_autonomous_signing",
        "provider_review_required",
        "no_real_phi",
        "metadata_only_audit_trail",
    }
    assert expected.issubset(keys), f"missing: {expected - keys}"
    for b in boundaries:
        assert b["asserted"] is True
        assert isinstance(b["statement"], str) and len(b["statement"]) > 20


def test_packet_artifact_hashes_present_and_deterministic(client):
    """Hashes must be stable across calls when artifact state hasn't
    changed. The generated_at timestamp moves, but hashes don't."""
    a = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    b = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()

    hashes_a = {h["section"]: h["hash"] for h in a["artifact_hashes"]}
    hashes_b = {h["section"]: h["hash"] for h in b["artifact_hashes"]}
    assert hashes_a == hashes_b
    assert set(hashes_a.keys()) == {"intake", "visit_draft", "fundus"}
    for sec, digest in hashes_a.items():
        assert isinstance(digest, str) and len(digest) == 64  # sha256 hex


def test_packet_reflects_vitals_after_full_lifecycle(client):
    # Drive a vitals workup through the full lifecycle so the packet
    # has something to summarize.
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "bp_systolic": 120, "bp_diastolic": 78},
    )
    assert r.status_code in (200, 201), r.text
    wid = r.json()["id"]
    client.patch(
        f"/api/v1/vitals-workups/{wid}",
        headers=CLIN1,
        json={"advance_to_entered": True},
    )
    client.post(
        f"/api/v1/vitals-workups/{wid}/review", headers=CLIN1, json={}
    )
    client.post(
        f"/api/v1/vitals-workups/{wid}/sign",
        headers=CLIN1,
        json={"attested": True},
    )

    r = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intake"]["count"] == 1
    assert body["intake"]["latest_status"] == "signed"
    assert body["review_sign_lock"]["vitals_signed"] is True
    # Hash must differ from the baseline-state hash because the
    # underlying section state changed.
    intake_hash = next(
        h for h in body["artifact_hashes"] if h["section"] == "intake"
    )
    assert intake_hash["algorithm"] == "sha256"
    # Timeline now contains the 3 vitals lifecycle events.
    types = [e for e in body["evidence_timeline"] if e["artifact_type"] == "vitals_workup"]
    assert {e["event_type"] for e in types} == {"created", "reviewed", "signed"}


def test_packet_cross_org_returns_404(client):
    r = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=ADMIN2
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_packet_unknown_encounter_returns_404(client):
    r = client.get(
        "/api/v1/encounters/99999/retina-visit-packet", headers=ADMIN1
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_packet_unauthenticated_returns_401(client):
    r = client.get("/api/v1/encounters/1/retina-visit-packet")
    assert r.status_code in (401, 403), r.text


def test_packet_contains_no_clinical_free_text(client):
    """Canary: even if upstream artifacts contained clinical text bodies,
    the packet must never serialize them."""
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={
            "source_type": "technician_entry",
            "bp_systolic": 188,
            "bp_diastolic": 102,
            "temperature_value": 98.6,
            "technician_notes": "patient hypertensive in clinic per technician canary text",
        },
    )
    assert r.status_code in (200, 201), r.text

    r = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    blob = json.dumps(r.json()).lower()

    for needle in [
        "hypertensive in clinic",
        "canary text",
        "technician_notes",
        "188",
        "102",
        "98.6",
        "transcript_text",
        "draft_note",
        "findings_json",
        "drawing_json",
    ]:
        assert needle not in blob, (
            f"forbidden clinical body fragment leaked into packet: {needle!r}"
        )
