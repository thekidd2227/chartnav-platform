"""Phase 84 — Disease staging integrations across Phase 76 / 77 / 81 / 82."""

from __future__ import annotations

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _post_stage(client, **over):
    payload = {
        "diagnosis_code": "h35.31",
        "staging_system": "amd_areds",
        "stage_value": "Category 3",
        **over,
    }
    return client.post(
        "/api/v1/encounters/1/disease-staging",
        headers=CLIN1,
        json=payload,
    )


def test_phase_76_summary_baseline_includes_empty_staging_block(client):
    r = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "disease_staging_summary" in body
    block = body["disease_staging_summary"]
    assert block["record_count"] == 0
    assert block["latest_by_diagnosis"] == []
    assert block["insufficient_data"] is True
    # Disclosure mentions staging boundary.
    assert "disease staging" in body["audit_disclosure"].lower()


def test_phase_76_summary_surfaces_latest_stage_per_diagnosis(client):
    assert _post_stage(client, stage_value="Category 2").status_code == 201
    assert _post_stage(client, stage_value="Category 4").status_code == 201
    assert (
        _post_stage(
            client,
            diagnosis_code="h40.1",
            staging_system="glaucoma_poag",
            stage_value="Moderate",
        ).status_code
        == 201
    )

    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    block = body["disease_staging_summary"]
    assert block["record_count"] == 2
    by_dx = {r["diagnosis_code"]: r for r in block["latest_by_diagnosis"]}
    assert by_dx["h35.31"]["stage_value"] == "Category 4"
    assert by_dx["h35.31"]["progression_detected"] is True
    assert by_dx["h40.1"]["stage_value"] == "Moderate"
    assert by_dx["h40.1"]["progression_detected"] is None


def test_phase_77_packet_includes_disease_staging_summary(client):
    assert _post_stage(client, stage_value="Category 4").status_code == 201
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "disease_staging_summary" in body
    assert body["disease_staging_summary"]["record_count"] == 1


def test_phase_82_validation_documents_stage_when_present(client):
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "staging:missing" in by_id
    assert by_id["staging:missing"]["status"] == "missing"
    assert by_id["staging:missing"]["requires_provider_acknowledgement"] is False

    assert _post_stage(client).status_code == 201
    body = client.get(
        "/api/v1/encounters/1/note-validation", headers=CLIN1
    ).json()
    by_id = {c["check_id"]: c for c in body["checks"]}
    assert "staging:documented" in by_id
    assert by_id["staging:documented"]["status"] == "pass"
    # The missing variant is gone now.
    assert "staging:missing" not in by_id


def test_phase_81_queue_surfaces_missing_stage_as_informational(client):
    # Seed a retina activity so the patient qualifies for the queue.
    from datetime import date, timedelta

    assert (
        client.post(
            "/api/v1/patients/1/anti-vegf-injections",
            headers=CLIN1,
            json={
                "eye": "OD",
                "injection_date": str(date.today() - timedelta(days=14)),
                "interval_weeks": 8,
                "authorization_status": "approved",
            },
        ).status_code
        == 201
    )

    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    informational = queue["buckets"]["informational"]
    staging = [
        it for it in informational
        if it["specialty_source"] == "staging"
        and it["category"] == "staging_missing"
    ]
    assert len(staging) == 1
    item = staging[0]
    assert item["patient_id"] == 1
    assert item["priority_bucket"] == "informational"
    assert item["insufficient_data"] is True
    # 'staging' must show up among sources_present.
    assert "staging" in queue["sources_present"]


def test_phase_81_queue_drops_staging_item_once_stage_is_recorded(client):
    from datetime import date, timedelta

    client.post(
        "/api/v1/patients/1/anti-vegf-injections",
        headers=CLIN1,
        json={
            "eye": "OD",
            "injection_date": str(date.today() - timedelta(days=14)),
            "interval_weeks": 8,
        },
    )
    before = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert any(
        it["specialty_source"] == "staging"
        for it in before["buckets"]["informational"]
    )
    assert _post_stage(client).status_code == 201
    after = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert not any(
        it["specialty_source"] == "staging"
        for it in after["buckets"]["informational"]
    )
