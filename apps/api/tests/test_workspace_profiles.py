"""Phase 86 — Subspecialty Adaptive Workspace tests."""

from __future__ import annotations

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _get(client, encounter_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/encounters/{encounter_id}/workspace-profile",
        headers=headers,
    )


def _patch(client, encounter_id=1, headers=CLIN1, encounter_type="retina"):
    return client.patch(
        f"/api/v1/encounters/{encounter_id}/workspace-profile",
        headers=headers,
        json={"encounter_type": encounter_type},
    )


# ---------------------------------------------------------------------------
# GET — default + profile structure
# ---------------------------------------------------------------------------


def test_get_returns_comprehensive_profile_by_default(client):
    body = _get(client).json()
    assert body["encounter_id"] == 1
    assert body["encounter_type"] == "comprehensive"
    assert body["encounter_type_label"] == "Comprehensive"
    profile = body["profile"]
    assert profile["code"] == "comprehensive"
    # Phase 88 — imaging_metadata is collapsed-but-accessible in
    # comprehensive; every other panel remains prioritized.
    collapsed_codes = {p["code"] for p in profile["collapsed_panels"]}
    assert collapsed_codes == {"imaging_metadata"}


def test_get_includes_supported_types_matrix(client):
    body = _get(client).json()
    codes = {t["code"] for t in body["supported_encounter_types"]}
    assert codes == {"retina", "glaucoma", "cataract", "comprehensive"}


def test_get_includes_universal_panels_first_in_every_profile(client):
    for typ in ("retina", "glaucoma", "cataract", "comprehensive"):
        if typ != "comprehensive":
            assert _patch(client, encounter_type=typ).status_code == 200
        body = _get(client).json()
        prioritized = [p["code"] for p in body["profile"]["prioritized_panels"]]
        assert prioritized[:2] == ["provider_action_queue", "note_validation"]


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_includes_disclosure_with_safe_claims_language(client):
    body = _get(client).json()
    d = body["disclosure"].lower()
    assert "deterministic" in d
    assert "does not autonomously classify" in d
    assert "does not infer subspecialty" in d
    assert "does not hide data" in d


# ---------------------------------------------------------------------------
# PATCH — provider-driven update
# ---------------------------------------------------------------------------


def test_patch_to_retina_returns_retina_profile(client):
    assert _patch(client, encounter_type="retina").status_code == 200
    body = _get(client).json()
    assert body["encounter_type"] == "retina"
    profile = body["profile"]
    assert profile["code"] == "retina"
    prioritized = [p["code"] for p in profile["prioritized_panels"]]
    # Anti-VEGF rail prioritized.
    assert "anti_vegf_injection" in prioritized
    # Lower-priority panels are collapsed, not hidden.
    collapsed = [p["code"] for p in profile["collapsed_panels"]]
    assert "glaucoma_cockpit" in collapsed
    assert "cataract_workflow" in collapsed


def test_patch_to_glaucoma_returns_glaucoma_profile(client):
    assert _patch(client, encounter_type="glaucoma").status_code == 200
    body = _get(client).json()
    profile = body["profile"]
    assert profile["code"] == "glaucoma"
    prioritized = [p["code"] for p in profile["prioritized_panels"]]
    assert "glaucoma_cockpit" in prioritized
    assert "medication_safety" in prioritized
    collapsed = [p["code"] for p in profile["collapsed_panels"]]
    assert "anti_vegf_injection" in collapsed
    assert "cataract_workflow" in collapsed


def test_patch_to_cataract_returns_cataract_profile(client):
    assert _patch(client, encounter_type="cataract").status_code == 200
    body = _get(client).json()
    profile = body["profile"]
    assert profile["code"] == "cataract"
    prioritized = [p["code"] for p in profile["prioritized_panels"]]
    assert "cataract_workflow" in prioritized
    assert "medication_safety" in prioritized
    collapsed = [p["code"] for p in profile["collapsed_panels"]]
    assert "anti_vegf_injection" in collapsed
    assert "glaucoma_cockpit" in collapsed


def test_patch_to_comprehensive_returns_balanced_profile(client):
    assert _patch(client, encounter_type="retina").status_code == 200
    assert _patch(client, encounter_type="comprehensive").status_code == 200
    body = _get(client).json()
    profile = body["profile"]
    assert profile["code"] == "comprehensive"
    # Phase 88 — imaging_metadata is collapsed-but-accessible in
    # comprehensive (the only panel collapsed in that profile).
    collapsed_codes = {p["code"] for p in profile["collapsed_panels"]}
    assert collapsed_codes == {"imaging_metadata"}
    assert profile["visible_panels"] == []


def test_patch_rejects_unknown_encounter_type(client):
    r = _patch(client, encounter_type="oncology")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_encounter_type"


def test_patch_requires_admin_or_clinician(client):
    assert _patch(client, headers=TECH1).status_code == 403
    assert _patch(client, headers=REV1).status_code == 403
    assert _patch(client, headers=FRONT1).status_code == 403
    assert _patch(client, headers=ADMIN1).status_code == 200


def test_patch_cross_org_returns_404(client):
    r = _patch(client, headers=ADMIN2)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Coverage invariant — no panel is ever hidden
# ---------------------------------------------------------------------------


_KNOWN_PANELS = {
    "provider_action_queue",
    "note_validation",
    "retina_visit_summary",
    "retina_visit_packet",
    "anti_vegf_injection",
    "glaucoma_cockpit",
    "cataract_workflow",
    "disease_staging",
    "medication_safety",
    "quality_intelligence",
    "imaging_metadata",
    "ophthalmic_medication_safety",
}


def test_every_profile_covers_every_known_panel_exactly_once(client):
    for typ in ("retina", "glaucoma", "cataract", "comprehensive"):
        if typ != "comprehensive":
            assert _patch(client, encounter_type=typ).status_code == 200
        body = _get(client).json()
        profile = body["profile"]
        all_codes = [
            *[p["code"] for p in profile["prioritized_panels"]],
            *[p["code"] for p in profile["visible_panels"]],
            *[p["code"] for p in profile["collapsed_panels"]],
        ]
        assert set(all_codes) == _KNOWN_PANELS, typ
        assert len(all_codes) == len(set(all_codes)), typ
        # panel_order must concatenate the three buckets in priority order.
        assert profile["panel_order"] == all_codes
