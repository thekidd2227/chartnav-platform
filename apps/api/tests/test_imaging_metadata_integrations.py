"""Phase 88 — Imaging metadata integrations across Phase 76 / 77 / 81 / 87."""

from __future__ import annotations

CLIN1 = {"X-User-Email": "clin@chartnav.local"}


def _seed_imaging(client, **over):
    payload = {
        "modality": "oct_macula",
        "eye": "OD",
        "status": "uploaded",
        "encounter_id": 1,
        **over,
    }
    r = client.post(
        "/patients/1/imaging-studies", headers=CLIN1, json=payload
    )
    assert r.status_code == 201, r.text
    return r.json()


def _mark_reviewed(client, study_id):
    r = client.patch(
        f"/api/v1/imaging-metadata/{study_id}/review", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Phase 76 — retina visit summary
# ---------------------------------------------------------------------------


def test_phase_76_summary_baseline_includes_empty_imaging_summary(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert "imaging_metadata_summary" in body
    block = body["imaging_metadata_summary"]
    assert block["total_count"] == 0
    assert block["insufficient_data"] is True
    assert "does not interpret images" in body["audit_disclosure"].lower()


def test_phase_76_summary_reflects_seeded_imaging(client):
    _seed_imaging(client, modality="oct_macula", eye="OD")
    _seed_imaging(client, modality="visual_field_24_2", eye="OS")
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    block = body["imaging_metadata_summary"]
    assert block["total_count"] == 2
    assert block["reviewed_count"] == 0
    assert block["unreviewed_count"] == 2
    assert set(block["modality_groups_present"]) >= {"oct", "visual_field"}


def test_phase_76_summary_reflects_review_action(client):
    seeded = _seed_imaging(client)
    _mark_reviewed(client, seeded["id"])
    body = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    ).json()
    assert body["imaging_metadata_summary"]["reviewed_count"] == 1
    assert body["imaging_metadata_summary"]["unreviewed_count"] == 0


# ---------------------------------------------------------------------------
# Phase 77 — packet export
# ---------------------------------------------------------------------------


def test_phase_77_packet_includes_imaging_metadata_summary(client):
    _seed_imaging(client, modality="oct_macula")
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    assert "imaging_metadata_summary" in body
    block = body["imaging_metadata_summary"]
    assert block["total_count"] == 1
    assert "oct" in block["modality_groups_present"]
    assert isinstance(block["summary_hash"], str) and len(block["summary_hash"]) == 64


def test_phase_77_packet_baseline_imaging_block_is_empty(client):
    body = client.get(
        "/api/v1/encounters/1/retina-visit-packet", headers=CLIN1
    ).json()
    block = body["imaging_metadata_summary"]
    assert block["total_count"] == 0
    assert block["insufficient_data"] is True


# ---------------------------------------------------------------------------
# Phase 81 — provider action queue
# ---------------------------------------------------------------------------


def test_phase_81_queue_surfaces_unreviewed_imaging_as_informational(client):
    _seed_imaging(client)
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    informational = queue["buckets"]["informational"]
    imaging = [
        it for it in informational
        if it["specialty_source"] == "imaging"
        and it["category"] == "imaging_metadata_unreviewed"
    ]
    assert len(imaging) == 1
    item = imaging[0]
    assert item["patient_id"] == 1
    assert item["priority_bucket"] == "informational"
    assert "imaging" in queue["sources_present"]


def test_phase_81_queue_does_not_emit_imaging_to_tier_1(client):
    _seed_imaging(client)
    queue = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    for bucket in ("same_day", "this_week", "routine"):
        items = [
            it for it in queue["buckets"][bucket]
            if it["specialty_source"] == "imaging"
        ]
        assert items == [], bucket


def test_phase_81_queue_drops_imaging_item_once_reviewed(client):
    seeded = _seed_imaging(client)
    before = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert any(
        it["specialty_source"] == "imaging"
        for it in before["buckets"]["informational"]
    )
    _mark_reviewed(client, seeded["id"])
    after = client.get(
        "/api/v1/provider-action-queue", headers=CLIN1
    ).json()
    assert not any(
        it["specialty_source"] == "imaging"
        for it in after["buckets"]["informational"]
    )


# ---------------------------------------------------------------------------
# Phase 87 — FHIR DocumentReference
# ---------------------------------------------------------------------------


def test_phase_87_fhir_document_reference_includes_imaging_metadata_summary(client):
    _seed_imaging(client, modality="oct_macula")
    body = client.get(
        "/api/fhir/r4/DocumentReference/1", headers=CLIN1
    ).json()
    extensions = body["extension"]
    imaging_ext = next(
        e for e in extensions
        if e["url"].endswith("/imaging-metadata-summary")
    )
    fields = {x["url"]: x for x in imaging_ext["extension"]}
    assert fields["total-count"]["valueInteger"] == 1
    assert fields["reviewed-count"]["valueInteger"] == 0
    assert fields["unreviewed-count"]["valueInteger"] == 1
    assert isinstance(fields["summary-hash"]["valueString"], str)
    assert len(fields["summary-hash"]["valueString"]) == 64
