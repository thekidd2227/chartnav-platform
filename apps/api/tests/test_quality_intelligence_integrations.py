"""Phase 89 — Quality intelligence integrations across Phase 76 / 77 / 81 / 82."""

from __future__ import annotations

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _seed_vitals_workup(client, encounter_id=1):
    # Phase 60 vitals workup. The /api/v1/encounters/{id}/vitals-workup
    # endpoint creates one row.
    return client.post(
        f"/api/v1/encounters/{encounter_id}/vitals-workups",
        headers=CLIN1,
        json={"iop_od": "16", "iop_os": "15"},
    )


def _record_quality(
    client,
    encounter_id=1,
    measure_id="chartnav_demo_ophth_dr_communication",
    response_type="met",
):
    return client.post(
        f"/api/v1/encounters/{encounter_id}/quality-measures/"
        f"{measure_id}/response",
        headers=CLIN1,
        json={"response_type": response_type},
    )


# ---------------------------------------------------------------------------
# Phase 76 — retina visit summary
# ---------------------------------------------------------------------------


def test_phase_76_summary_embeds_quality_intelligence_summary(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert "quality_intelligence_summary" in body
    block = body["quality_intelligence_summary"]
    # Seeded demo specs are present, so total_count is non-zero.
    assert block["total_count"] >= 3
    assert block["internal_demo_specs_present"] is True
    assert block["submission_status"] == "not_submitted"
    assert "does not submit to cms" in body["audit_disclosure"].lower()


def test_phase_76_summary_reflects_provider_response(client):
    _record_quality(client, response_type="met")
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    block = body["quality_intelligence_summary"]
    assert block["completed_count"] >= 1


# ---------------------------------------------------------------------------
# Phase 77 — packet export
# ---------------------------------------------------------------------------


def test_phase_77_packet_includes_quality_intelligence_summary(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "quality_intelligence_summary" in body
    block = body["quality_intelligence_summary"]
    assert block["submission_status"] == "not_submitted"


def test_phase_77_packet_quality_block_reflects_response(client):
    _record_quality(client)
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    block = body["quality_intelligence_summary"]
    assert block["completed_count"] >= 1


# ---------------------------------------------------------------------------
# Phase 81 — provider action queue
# ---------------------------------------------------------------------------


def test_phase_81_queue_surfaces_incomplete_quality_as_informational(client):
    # Seed some structured work so quality items qualify.
    assert _seed_vitals_workup(client).status_code == 201
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    informational = queue["buckets"]["informational"]
    quality = [
        it for it in informational
        if it["specialty_source"] == "quality"
        and it["category"] == "quality_measure_incomplete"
    ]
    assert len(quality) >= 1
    item = quality[0]
    assert item["priority_bucket"] == "informational"
    assert item["patient_id"] == 1
    assert item["encounter_id"] == 1
    assert "quality" in queue["sources_present"]


def test_phase_81_queue_does_not_emit_quality_to_tier_1(client):
    assert _seed_vitals_workup(client).status_code == 201
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    for bucket in ("same_day", "this_week", "routine"):
        quality = [
            it for it in queue["buckets"][bucket]
            if it["specialty_source"] == "quality"
        ]
        assert quality == [], bucket


def test_phase_81_queue_quality_item_does_not_fire_on_empty_encounter(client):
    # No structured work on the seeded encounter — quality items must
    # NOT fire even though applicable specs exist (otherwise every
    # blank encounter would pollute the queue).
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    quality = [
        it for it in queue["buckets"]["informational"]
        if it["specialty_source"] == "quality"
    ]
    assert quality == []


def test_phase_81_queue_drops_quality_item_once_all_responses_recorded(client):
    assert _seed_vitals_workup(client).status_code == 201
    # Record responses for all three demo measures.
    _record_quality(client, measure_id="chartnav_demo_ophth_dr_communication")
    _record_quality(
        client,
        measure_id="chartnav_demo_ophth_poag_iop_documentation",
        response_type="not_applicable",
    )
    _record_quality(
        client,
        measure_id="chartnav_demo_ophth_dr_screening",
        response_type="exclusion",
    )
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    quality = [
        it for it in queue["buckets"]["informational"]
        if it["specialty_source"] == "quality"
    ]
    assert quality == []


# ---------------------------------------------------------------------------
# Phase 82 — note validation rail
# ---------------------------------------------------------------------------


def test_phase_82_validation_emits_quality_incomplete_when_open(client):
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "quality:incomplete" in by_id
    item = by_id["quality:incomplete"]
    assert item["status"] == "warning"
    # CRITICAL: never requires acknowledgement (never blocks signing).
    assert item["requires_provider_acknowledgement"] is False


def test_phase_82_validation_emits_quality_documented_when_all_responded(client):
    _record_quality(client, measure_id="chartnav_demo_ophth_dr_communication")
    _record_quality(
        client,
        measure_id="chartnav_demo_ophth_poag_iop_documentation",
        response_type="not_applicable",
    )
    _record_quality(
        client,
        measure_id="chartnav_demo_ophth_dr_screening",
        response_type="exclusion",
    )
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "quality:documented" in by_id
    assert by_id["quality:documented"]["status"] == "pass"
    assert by_id["quality:documented"]["requires_provider_acknowledgement"] is False
