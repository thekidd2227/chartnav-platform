"""Phase 88 — Imaging Metadata Review Linkage tests."""

from __future__ import annotations

from datetime import datetime, timezone

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _seed_imaging_study(
    client,
    *,
    headers=CLIN1,
    patient_id=1,
    encounter_id=1,
    modality="oct_macula",
    eye="OD",
    status="uploaded",
):
    payload = {
        "modality": modality,
        "eye": eye,
        "status": status,
        "encounter_id": encounter_id,
    }
    r = client.post(
        f"/patients/{patient_id}/imaging-studies",
        headers=headers,
        json=payload,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _get(client, encounter_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/encounters/{encounter_id}/imaging-metadata",
        headers=headers,
    )


def _patch_review(client, metadata_id, headers=CLIN1):
    return client.patch(
        f"/api/v1/imaging-metadata/{metadata_id}/review",
        headers=headers,
    )


# ---------------------------------------------------------------------------
# GET — encounter scope
# ---------------------------------------------------------------------------


def test_get_baseline_returns_empty_with_disclosure(client):
    body = _get(client).json()
    assert body["items"] == []
    assert body["counts"]["total"] == 0
    assert body["counts"]["reviewed"] == 0
    assert body["counts"]["unreviewed"] == 0
    assert "does not interpret images" in body["disclosure"].lower()
    assert "does not infer findings from imaging" in body["disclosure"].lower()
    assert "metadata only" in body["disclosure"].lower()


def test_get_lists_seeded_imaging_study_with_full_projection(client):
    seeded = _seed_imaging_study(client, modality="oct_macula", eye="OD")
    body = _get(client).json()
    assert body["counts"]["total"] == 1
    item = body["items"][0]
    assert item["id"] == seeded["id"]
    assert item["modality"] == "oct_macula"
    assert item["modality_group"] == "oct"
    assert item["laterality"] == "OD"
    assert item["review_status"] == "uploaded"
    assert item["reviewed_by_display"] is None
    assert item["reviewed_at"] is None
    assert isinstance(item["metadata_hash"], str)
    assert len(item["metadata_hash"]) == 64


def test_get_buckets_by_modality_group(client):
    _seed_imaging_study(client, modality="oct_macula", eye="OD")
    _seed_imaging_study(client, modality="oct_rnfl", eye="OS")
    _seed_imaging_study(client, modality="visual_field_24_2", eye="OD")
    _seed_imaging_study(client, modality="biometry_packet", eye="OU")
    body = _get(client).json()
    groups = body["by_modality_group"]
    assert sorted(groups.keys()) == [
        "biometry",
        "oct",
        "visual_field",
    ]
    assert len(groups["oct"]) == 2
    assert len(groups["visual_field"]) == 1
    assert len(groups["biometry"]) == 1
    assert "biometry" in body["modality_groups_present"]


def test_get_orders_newest_first(client):
    a = _seed_imaging_study(client, modality="oct_macula", eye="OD")
    b = _seed_imaging_study(client, modality="oct_rnfl", eye="OS")
    body = _get(client).json()
    ids = [it["id"] for it in body["items"]]
    assert ids[0] == b["id"]
    assert ids[-1] == a["id"]


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_unknown_encounter_returns_404(client):
    r = client.get(
        "/api/v1/encounters/999999/imaging-metadata", headers=CLIN1
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH — provider review
# ---------------------------------------------------------------------------


def test_patch_marks_study_reviewed_and_stamps_actor(client):
    seeded = _seed_imaging_study(client)
    r = _patch_review(client, seeded["id"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["review_status"] == "reviewed"
    assert body["reviewed_by_display"] == "Casey Clinician"
    assert body["reviewed_by_role"] == "clinician"
    assert body["reviewed_at"] is not None


def test_patch_reflects_reviewed_state_in_subsequent_get(client):
    seeded = _seed_imaging_study(client)
    _patch_review(client, seeded["id"])
    body = _get(client).json()
    item = body["items"][0]
    assert item["review_status"] == "reviewed"
    assert body["counts"]["reviewed"] == 1
    assert body["counts"]["unreviewed"] == 0


def test_patch_requires_admin_or_clinician(client):
    seeded = _seed_imaging_study(client)
    assert _patch_review(client, seeded["id"], headers=TECH1).status_code == 403
    assert _patch_review(client, seeded["id"], headers=REV1).status_code == 403
    assert _patch_review(client, seeded["id"], headers=FRONT1).status_code == 403
    assert _patch_review(client, seeded["id"], headers=ADMIN1).status_code == 200


def test_patch_cross_org_returns_404(client):
    seeded = _seed_imaging_study(client)
    assert (
        _patch_review(client, seeded["id"], headers=ADMIN2).status_code == 404
    )


def test_patch_unknown_metadata_returns_404(client):
    r = _patch_review(client, 999999)
    assert r.status_code == 404


def test_patch_is_idempotent(client):
    seeded = _seed_imaging_study(client)
    first = _patch_review(client, seeded["id"]).json()
    second = _patch_review(client, seeded["id"]).json()
    assert first["review_status"] == "reviewed"
    assert second["review_status"] == "reviewed"
    # second timestamp >= first
    assert second["reviewed_at"] >= first["reviewed_at"]


# ---------------------------------------------------------------------------
# Metadata hash determinism
# ---------------------------------------------------------------------------


def test_metadata_hash_is_stable_across_reads(client):
    _seed_imaging_study(client)
    body_a = _get(client).json()
    body_b = _get(client).json()
    assert body_a["items"][0]["metadata_hash"] == body_b["items"][0]["metadata_hash"]


def test_metadata_hash_changes_after_review(client):
    seeded = _seed_imaging_study(client)
    before = _get(client).json()["items"][0]["metadata_hash"]
    _patch_review(client, seeded["id"])
    after = _get(client).json()["items"][0]["metadata_hash"]
    assert before != after


# ---------------------------------------------------------------------------
# No image interpretation surface
# ---------------------------------------------------------------------------


def test_response_never_includes_findings_or_interpretation(client):
    _seed_imaging_study(client)
    _seed_imaging_study(client, modality="visual_field_24_2", eye="OS")
    body = _get(client).json()
    blob = str(body).lower()
    # Strip out the legitimate boundary copy first.
    blob = blob.replace(body["disclosure"].lower(), "")
    for forbidden in (
        "diagnosis confirmed",
        "treatment recommended",
        "image interpreted",
        "ai interpretation",
        "auto-classified",
        "drusen detected",
        "rnfl thinning detected",
        "vf defect detected",
        "macular edema detected",
        "findings:",
        "impression:",
    ):
        assert forbidden not in blob, forbidden


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_get_requires_authentication(client):
    r = client.get("/api/v1/encounters/1/imaging-metadata")
    assert r.status_code in {401, 403}


def test_patch_requires_authentication(client):
    seeded = _seed_imaging_study(client)
    r = client.patch(f"/api/v1/imaging-metadata/{seeded['id']}/review")
    assert r.status_code in {401, 403}
