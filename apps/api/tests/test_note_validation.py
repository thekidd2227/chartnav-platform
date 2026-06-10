"""Phase 82 — Note Validation Rail tests."""

from __future__ import annotations

import json
from datetime import date, timedelta

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}

URL = "/api/v1/encounters/1/note-validation"


def _val(client, encounter_id=1, headers=CLIN1):
    r = client.get(
        f"/api/v1/encounters/{encounter_id}/note-validation",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _by_id(body, check_id):
    return next((c for c in body["checks"] if c["check_id"] == check_id), None)


def test_baseline_returns_deterministic_checks_for_seeded_encounter(client):
    body = _val(client)
    assert body["encounter_id"] == 1
    assert body["organization_id"] == 1
    assert body["demo_mode"] is True

    # All four laterality source checks are present (vitals/fundus + patient
    # ones because seeded encounter 1 has a patient_id).
    for source in ("vitals", "fundus", "anti_vegf", "cataract"):
        check = _by_id(body, f"laterality:{source}")
        assert check is not None
        # No data yet on fresh seed -> missing.
        assert check["status"] == "missing"
        assert check["category"] == "laterality"

    # Follow-up check warns (no cadence yet).
    fu = _by_id(body, "follow_up:interval")
    assert fu is not None
    assert fu["status"] == "warning"
    assert fu["requires_provider_acknowledgement"] is True

    # No unsigned upstream yet -> pass.
    up = _by_id(body, "unsigned:upstream")
    assert up is not None
    assert up["status"] == "pass"

    # No visit draft yet -> missing.
    vd = _by_id(body, "review_state:visit_draft")
    assert vd is not None
    assert vd["status"] == "missing"

    # Attestation pass always present.
    assert _by_id(body, "review_state:attestation")["status"] == "pass"

    # Disclosure language present.
    d = body["disclosure"].lower()
    assert "does not diagnose" in d
    assert "provider attestation remains required" in d


def test_vitals_iop_makes_laterality_pass_for_vitals_source(client):
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={
            "source_type": "technician_entry",
            "iop_od": 18,
            "iop_os": 16,
            "iop_method": "applanation",
        },
    )
    assert r.status_code in (200, 201), r.text

    body = _val(client)
    vitals = _by_id(body, "laterality:vitals")
    assert vitals["status"] == "pass"
    assert vitals["laterality"] == "OU"
    assert "OD" in vitals["detail"] and "OS" in vitals["detail"]


def test_laterality_rollup_warning_when_sources_disagree(client):
    # Vitals: OD only
    client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "iop_od": 18, "iop_method": "applanation"},
    )
    # Fundus: OS only — DISJOINT with vitals -> rollup warning
    client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "lattice from 5 to 7 OS", "laterality": "OS"},
    )

    body = _val(client)
    rollup = _by_id(body, "laterality:rollup")
    assert rollup is not None
    assert rollup["status"] == "warning"
    assert rollup["requires_provider_acknowledgement"] is True
    assert "differs across surfaces" in rollup["detail"]


def test_laterality_rollup_pass_when_sources_share_eye(client):
    # Both vitals and fundus on OD.
    client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "iop_od": 18, "iop_method": "applanation"},
    )
    client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "horseshoe tear 10:30 OD", "laterality": "OD"},
    )
    body = _val(client)
    rollup = _by_id(body, "laterality:rollup")
    assert rollup is not None
    assert rollup["status"] == "pass"
    assert rollup["laterality"] == "OD"


def test_follow_up_interval_pass_when_anti_vegf_interval_recorded(client):
    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(date.today() - timedelta(days=5)),
            "interval_weeks": 6,
        },
    )
    body = _val(client)
    fu = _by_id(body, "follow_up:interval")
    assert fu["status"] == "pass"
    assert fu["source"] == "anti_vegf"
    assert fu["laterality"] == "OD"
    assert "6 week" in fu["detail"]


def test_follow_up_interval_pass_when_cataract_cadence_recorded(client):
    client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OS",
            "postop_day_1_status": "scheduled",
        },
    )
    body = _val(client)
    fu = _by_id(body, "follow_up:interval")
    assert fu["status"] == "pass"
    assert fu["source"] == "cataract"
    assert fu["laterality"] == "OS"


def test_unsigned_upstream_warning_for_unsigned_vitals(client):
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "bp_systolic": 120, "bp_diastolic": 78},
    )
    assert r.status_code in (200, 201), r.text
    wid = r.json()["id"]

    body = _val(client)
    check = _by_id(body, f"unsigned:vitals:{wid}")
    assert check is not None
    assert check["status"] == "warning"
    assert check["requires_provider_acknowledgement"] is True
    assert check["source_artifact_id"] == wid


def test_unsigned_upstream_warning_for_unsigned_fundus_carries_laterality(client):
    r = client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "horseshoe tear 10:30 OD", "laterality": "OD"},
    )
    assert r.status_code in (200, 201), r.text
    fid = r.json()["chart_id"]

    body = _val(client)
    check = _by_id(body, f"unsigned:fundus:{fid}")
    assert check is not None
    assert check["status"] == "warning"
    assert check["laterality"] == "OD"


def test_visit_draft_warning_when_not_finalized(client):
    r = client.post(
        "/patients/1/scribe-sessions",
        headers=CLIN1,
        json={
            "input_mode": "transcript",
            "transcript_text": "Demo transcript only.",
            "encounter_id": 1,
        },
    )
    assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]

    body = _val(client)
    check = _by_id(body, f"review_state:visit_draft:{sid}")
    assert check is not None
    assert check["status"] == "warning"
    assert check["requires_provider_acknowledgement"] is True


def test_totals_and_ack_required_aggregate_correctly(client):
    # Force one warning: laterality disagreement.
    client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={"source_type": "technician_entry", "iop_od": 18, "iop_method": "applanation"},
    )
    client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "lattice from 5 to 7 OS", "laterality": "OS"},
    )

    body = _val(client)
    assert body["totals"]["pass"] >= 2
    assert body["totals"]["warning"] >= 1
    assert body["acknowledgements_required"] >= 1


def test_cross_org_returns_404(client):
    r = client.get(URL, headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_unknown_encounter_returns_404(client):
    r = client.get(
        "/api/v1/encounters/99999/note-validation", headers=ADMIN1
    )
    assert r.status_code == 404


def test_unauthenticated_returns_401(client):
    r = client.get(URL)
    assert r.status_code in (401, 403)


def test_no_forbidden_clinical_language(client):
    # Build up a busy encounter to maximize surface area.
    client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLIN1,
        json={
            "source_type": "technician_entry",
            "iop_od": 28,
            "iop_method": "applanation",
            "technician_notes": "Provider canary text about progression.",
        },
    )
    client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLIN1,
        json={"findings_text": "horseshoe tear 10:30 OD", "laterality": "OD"},
    )
    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(date.today() - timedelta(days=2)),
            "interval_weeks": 4,
            "authorization_status": "approved",
        },
    )
    client.post(
        "/api/v1/patients/1/cataract-workflow/records",
        headers=CLIN1,
        json={
            "surgery_eye": "OS",
            "planned_surgery_date": "2026-09-01",
            "complications_flag": True,
            "complication_note": "Provider canary complication note.",
        },
    )

    body = _val(client)
    blob = json.dumps(body).lower()
    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "surgery recommended",
        "rapid progression",
        "stage iii",
        "stage iv",
        "iol power",
        "phaco recommended",
        "flacs recommended",
        "order placed",
        "billing code",
        # Provider canary text must not leak.
        "canary text",
        "canary complication note",
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase leaked into note-validation: {forbidden!r}"
        )
