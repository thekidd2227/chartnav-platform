"""Phase 76 — Retina Visit Summary aggregator tests.

Covers:
- happy path against the seeded Morgan Lee encounter
- empty-artifact baseline (no vitals/scribe/fundus yet → all zero counts)
- cross-org access returns 404, not 403
- role-capability shape varies correctly per caller role
- evidence timeline is chronologically sorted
- metadata-only canary: no clinical free text leaks into the aggregator
  response even when the underlying artifacts contain text body fields
"""

from __future__ import annotations

import json
import re

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def test_summary_baseline_for_seeded_morgan_encounter(client):
    r = client.get(
        "/api/v1/encounters/1/retina-visit-summary",
        headers=CLIN1,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["encounter_id"] == 1
    assert body["patient_identifier"] == "PT-1001"
    assert body["patient_name"] == "Morgan Lee"
    assert body["organization_id"] == 1
    assert body["demo_mode"] is True
    # On a fresh seed there are no vitals/scribe/fundus artifacts yet,
    # so every count is zero and every section is a blocker.
    assert body["vitals"]["count"] == 0
    assert body["visit_draft"]["count"] == 0
    assert body["fundus"]["count"] == 0
    kinds = {b["kind"] for b in body["blockers"]}
    assert "missing_vitals" in kinds
    assert "missing_visit_draft" in kinds
    assert "missing_fundus" in kinds
    assert body["evidence_timeline"] == []
    # Audit disclosure is verbatim metadata-only language.
    assert "metadata-only audit events" in body["audit_disclosure"]
    assert "does not store clinical free text" in body["audit_disclosure"]


def test_summary_cross_org_returns_404(client):
    """Cross-org access must return 404 (not 403), matching the rest
    of the encounter API surface."""
    r = client.get(
        "/api/v1/encounters/1/retina-visit-summary",
        headers=ADMIN2,
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_role_capabilities_vary_per_caller(client):
    for headers, expected in [
        (CLIN1, {"can_review": True, "can_sign": True, "can_create_intake": True}),
        (ADMIN1, {"can_review": True, "can_sign": True, "can_create_intake": True}),
        (TECH1, {"can_review": False, "can_sign": False, "can_create_intake": True}),
        (REV1, {"can_review": True, "can_sign": False, "can_create_intake": False}),
    ]:
        r = client.get(
            "/api/v1/encounters/1/retina-visit-summary", headers=headers
        )
        assert r.status_code == 200, r.text
        caps = r.json()["role_capabilities"]
        for k, v in expected.items():
            assert caps[k] is v, f"{headers} expected {k}={v}, got {caps[k]}"
        assert isinstance(caps["explainer"], str) and len(caps["explainer"]) > 10


def test_summary_includes_vitals_after_create_review_sign(client):
    # Create vitals workup
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "bp_systolic": 120, "bp_diastolic": 78},
    )
    assert r.status_code in (200, 201), r.text
    wid = r.json()["id"]
    # Advance to entered
    r = client.patch(
        f"/api/v1/vitals-workups/{wid}",
        headers=CLIN1,
        json={"advance_to_entered": True},
    )
    assert r.status_code == 200, r.text
    # Review
    r = client.post(
        f"/api/v1/vitals-workups/{wid}/review", headers=CLIN1, json={}
    )
    assert r.status_code in (200, 201), r.text
    # Sign
    r = client.post(
        f"/api/v1/vitals-workups/{wid}/sign",
        headers=CLIN1,
        json={"attested": True},
    )
    assert r.status_code in (200, 201), r.text

    # Now the summary should reflect this
    r = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["vitals"]["count"] == 1
    assert body["vitals"]["latest_status"] == "signed"
    assert body["vitals"]["latest_id"] == wid
    # "vitals_unsigned" blocker must be gone now that it's signed.
    kinds = {b["kind"] for b in body["blockers"]}
    assert "vitals_unsigned" not in kinds
    assert "missing_vitals" not in kinds
    # Timeline must include created + reviewed + signed for this workup.
    events = [
        e for e in body["evidence_timeline"]
        if e["artifact_type"] == "vitals_workup" and e["ref_id"] == wid
    ]
    types = {e["event_type"] for e in events}
    assert types == {"created", "reviewed", "signed"}
    # Sorted chronologically
    timestamps = [e["timestamp"] for e in body["evidence_timeline"]]
    assert timestamps == sorted(timestamps)
    # Every event carries the actor display name from the seeded user.
    for e in events:
        assert e["actor_display_name"] in {
            "Casey Clinician", "ChartNav Admin",
        }, e
        assert e["actor_role"] in {"clinician", "admin"}


def test_timeline_contains_no_clinical_free_text(client):
    """Canary: even if upstream artifacts contained clinical text bodies,
    the aggregator must never serialize them. This is the metadata-only
    audit invariant applied at the cross-artifact level."""
    # Create vitals with technician notes (clinical free text) + BP/temp.
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
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    blob = json.dumps(r.json()).lower()

    # Clinical body values + notes MUST NOT appear anywhere in the
    # serialized summary.
    forbidden_substrings = [
        "hypertensive in clinic",
        "canary text",
        "technician_notes",
        "188",  # BP value
        "102",  # BP value
        "98.6",  # temp value
        "transcript_text",
        "draft_note",
        "findings_json",
        "drawing_json",
    ]
    for needle in forbidden_substrings:
        assert needle not in blob, (
            f"forbidden clinical body fragment leaked into summary: {needle!r}"
        )


def test_summary_unauthenticated_returns_401(client):
    r = client.get("/api/v1/encounters/1/retina-visit-summary")
    # No X-User-Email — header-mode auth must reject.
    assert r.status_code in (401, 403), r.text


def test_summary_unknown_encounter_returns_404(client):
    r = client.get(
        "/api/v1/encounters/99999/retina-visit-summary", headers=ADMIN1
    )
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["error_code"] == "encounter_not_found"
