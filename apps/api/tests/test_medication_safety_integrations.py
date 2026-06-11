"""Phase 90 — Medication safety integrations across Phase 76 / 77 / 81 / 82."""

from __future__ import annotations

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _seed_three_bak_drops(client, encounter_id=1):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        assert (
            client.post(
                f"/api/v1/encounters/{encounter_id}/ophthalmic-medications",
                headers=CLIN1,
                json={
                    "medication_name": f"demo-{klass}",
                    "medication_class": klass,
                    "route": "drops",
                    "laterality": "OU",
                    "dose_per_day": 1,
                    "preservative_type": "BAK",
                },
            ).status_code
            == 201
        )


# ---------------------------------------------------------------------------
# Phase 76 — retina visit summary
# ---------------------------------------------------------------------------


def test_phase_76_summary_baseline_includes_empty_medication_safety_block(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert "ophthalmic_medication_safety_summary" in body
    block = body["ophthalmic_medication_safety_summary"]
    assert block["active_medication_count"] == 0
    assert block["active_event_count"] == 0
    assert block["submission_status"] == "not_submitted"
    assert "provider-reviewed workflow support" in block["boundary_note"].lower()
    assert "does not prescribe" in body["audit_disclosure"].lower()


def test_phase_76_summary_reflects_active_safety_event(client):
    _seed_three_bak_drops(client)
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    block = body["ophthalmic_medication_safety_summary"]
    assert block["active_medication_count"] == 3
    assert block["preservative_burden_count"] == 3
    assert block["active_event_count"] >= 1


# ---------------------------------------------------------------------------
# Phase 77 — packet export
# ---------------------------------------------------------------------------


def test_phase_77_packet_includes_ophthalmic_medication_safety_summary(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "ophthalmic_medication_safety_summary" in body
    block = body["ophthalmic_medication_safety_summary"]
    assert block["submission_status"] == "not_submitted"
    assert "provider-reviewed workflow support" in block["boundary_note"].lower()


def test_phase_77_packet_reflects_seeded_safety_events(client):
    _seed_three_bak_drops(client)
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    block = body["ophthalmic_medication_safety_summary"]
    assert block["preservative_burden_count"] == 3
    assert block["active_event_count"] >= 1


# ---------------------------------------------------------------------------
# Phase 81 — provider action queue
# ---------------------------------------------------------------------------


def test_phase_81_queue_surfaces_medication_safety_as_informational(client):
    _seed_three_bak_drops(client)
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    informational = queue["buckets"]["informational"]
    safety = [
        it for it in informational
        if it["specialty_source"] == "medication_safety"
        and it["category"] == "medication_safety_event_active"
    ]
    assert len(safety) >= 1
    item = safety[0]
    assert item["priority_bucket"] == "informational"
    assert item["patient_id"] == 1
    assert "medication_safety" in queue["sources_present"]


def test_phase_81_queue_does_not_emit_medication_safety_to_tier_1(client):
    _seed_three_bak_drops(client)
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    for bucket in ("same_day", "this_week", "routine"):
        items = [
            it for it in queue["buckets"][bucket]
            if it["specialty_source"] == "medication_safety"
        ]
        assert items == [], bucket


def test_phase_81_queue_drops_medication_safety_item_when_acknowledged(client):
    _seed_three_bak_drops(client)
    body = client.get(
        "/api/v1/patients/1/medication-safety", headers=CLIN1
    ).json()
    active_events = [e for e in body["events"] if e["status"] == "active"]
    for ev in active_events:
        client.post(
            f"/api/v1/medication-safety-events/{ev['id']}/acknowledge",
            headers=CLIN1,
        )
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    items = [
        it for it in queue["buckets"]["informational"]
        if it["specialty_source"] == "medication_safety"
    ]
    assert items == []


# ---------------------------------------------------------------------------
# Phase 82 — note validation
# ---------------------------------------------------------------------------


def test_phase_82_validation_emits_medication_safety_warning_when_active(client):
    _seed_three_bak_drops(client)
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication_safety:active" in by_id
    item = by_id["medication_safety:active"]
    assert item["status"] == "warning"
    # CRITICAL: never requires acknowledgement on the rail (rule-level
    # acknowledgement is handled by Phase 90's event endpoint).
    assert item["requires_provider_acknowledgement"] is False


def test_phase_82_validation_emits_medication_safety_clear_when_none(client):
    # Seed one BAK drop (below threshold) so we have an active med
    # without an active safety event.
    client.post(
        "/api/v1/encounters/1/ophthalmic-medications",
        headers=CLIN1,
        json={
            "medication_name": "Lone drop",
            "medication_class": "pgf2_analog",
            "route": "drops",
            "laterality": "OU",
            "dose_per_day": 1,
            "preservative_type": "preservative_free",
        },
    )
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication_safety:clear" in by_id
    assert by_id["medication_safety:clear"]["status"] == "pass"


def test_phase_82_validation_emits_no_medications_pass_when_empty(client):
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "medication_safety:no_medications" in by_id
    assert by_id["medication_safety:no_medications"]["status"] == "pass"
