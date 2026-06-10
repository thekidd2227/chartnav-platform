"""Phase 85 — Medication safety integrations across Phase 77 / 81 / 82."""

from __future__ import annotations

from datetime import date, timedelta

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _post_med(client, **over):
    payload = {
        "medication_name": "Latanoprost 0.005% drops",
        "medication_class": "pgf2_analog",
        "route": "drops",
        "laterality": "OU",
        "dose_per_day": 1,
        "preservative_flag": True,
        **over,
    }
    return client.post(
        "/api/v1/encounters/1/medications", headers=CLIN1, json=payload
    )


def _post_refill(client, med_id, *, days_supply, refill_date):
    return client.post(
        f"/api/v1/medications/{med_id}/refills",
        headers=CLIN1,
        json={
            "expected_days_supply": days_supply,
            "refill_date": str(refill_date),
        },
    )


def test_phase_82_validation_documents_active_meds_when_present(client):
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication:missing" in by_id
    assert by_id["medication:missing"]["status"] == "missing"
    assert by_id["medication:missing"]["requires_provider_acknowledgement"] is False

    assert _post_med(client).status_code == 201
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication:documented" in by_id
    assert by_id["medication:documented"]["status"] == "pass"
    assert by_id["medication:documented"]["requires_provider_acknowledgement"] is False
    assert "medication:missing" not in by_id


def test_phase_82_validation_emits_refill_gap_warning_informational(client):
    med = _post_med(client).json()
    old = date.today() - timedelta(days=60)
    _post_refill(client, med["id"], days_supply=30, refill_date=old)

    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication:refill_gap" in by_id
    item = by_id["medication:refill_gap"]
    assert item["status"] == "warning"
    # CRITICAL: never requires acknowledgement (never blocks signing).
    assert item["requires_provider_acknowledgement"] is False


def test_phase_81_queue_surfaces_refill_gap_as_informational(client):
    med = _post_med(client).json()
    old = date.today() - timedelta(days=90)
    _post_refill(client, med["id"], days_supply=30, refill_date=old)

    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    informational = queue["buckets"]["informational"]
    medication = [
        it for it in informational
        if it["specialty_source"] == "medication"
        and it["category"] == "medication_refill_gap"
    ]
    assert len(medication) == 1
    item = medication[0]
    assert item["patient_id"] == 1
    assert item["priority_bucket"] == "informational"
    assert "medication" in queue["sources_present"]


def test_phase_81_queue_does_not_emit_tier_1_for_medications(client):
    med = _post_med(client).json()
    old = date.today() - timedelta(days=180)
    _post_refill(client, med["id"], days_supply=30, refill_date=old)

    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    for bucket in ("same_day", "this_week", "routine"):
        med_items = [
            it for it in queue["buckets"][bucket]
            if it["specialty_source"] == "medication"
        ]
        assert med_items == [], (
            f"medication item must never appear in {bucket} bucket"
        )


def test_phase_81_queue_drops_medication_item_once_refill_recorded(client):
    med = _post_med(client).json()
    old = date.today() - timedelta(days=90)
    _post_refill(client, med["id"], days_supply=30, refill_date=old)

    before = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert any(
        it["specialty_source"] == "medication"
        for it in before["buckets"]["informational"]
    )

    # Provider records a fresh refill — gap closes.
    _post_refill(client, med["id"], days_supply=30, refill_date=date.today())

    after = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert not any(
        it["specialty_source"] == "medication"
        for it in after["buckets"]["informational"]
    )


def test_phase_77_packet_includes_medication_safety_summary(client):
    assert _post_med(client).status_code == 201
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "medication_safety_summary" in body
    block = body["medication_safety_summary"]
    assert block["active_medication_count"] == 1
    assert block["preservative_burden"] == 1
    assert block["refill_gap_count"] == 0
    assert "pgf2_analog" in block["medication_classes_present"]
    assert block["insufficient_data"] is False


def test_phase_77_packet_baseline_includes_empty_medication_block(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    block = body["medication_safety_summary"]
    assert block["active_medication_count"] == 0
    assert block["preservative_burden"] == 0
    assert block["refill_gap_count"] == 0
    assert block["allergy_count"] == 0
    assert block["insufficient_data"] is True
