"""Phase 91 — Unified Ophthalmology Workspace State tests."""

from __future__ import annotations

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _get(client, encounter_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/encounters/{encounter_id}/workspace-state", headers=headers
    )


def _patch_visit_mode(client, mode="follow_up", encounter_id=1, headers=CLIN1):
    return client.patch(
        f"/api/v1/encounters/{encounter_id}/workspace-state/visit-mode",
        headers=headers,
        json={"visit_mode": mode},
    )


def _patch_active_laterality(
    client, lat="OD", encounter_id=1, headers=CLIN1
):
    return client.patch(
        f"/api/v1/encounters/{encounter_id}/workspace-state/active-laterality",
        headers=headers,
        json={"active_laterality": lat},
    )


def _patch_encounter_type(client, typ="retina", headers=CLIN1):
    return client.patch(
        "/api/v1/encounters/1/workspace-profile",
        headers=headers,
        json={"encounter_type": typ},
    )


# ---------------------------------------------------------------------------
# GET — baseline shape
# ---------------------------------------------------------------------------


def test_get_returns_baseline_unscheduled_comprehensive_state(client):
    body = _get(client).json()
    assert body["encounter_id"] == 1
    assert body["encounter_type"] == "comprehensive"
    assert body["visit_mode"] == "unscheduled"
    assert body["active_laterality"] == "NA"
    assert body["profile"]["code"] == "comprehensive"
    assert "panel_order" in body["profile"]
    assert "emphasis" in body
    assert isinstance(body["emphasis"]["emphasised_panels"], list)
    assert "laterality_linked_panels" in body
    assert body["laterality_linked_panels"]


def test_get_includes_supported_matrix(client):
    body = _get(client).json()
    modes = {m["code"] for m in body["supported_visit_modes"]}
    assert modes == {
        "intake",
        "surgical_pre_op",
        "post_op",
        "follow_up",
        "lab_review",
        "unscheduled",
    }
    lats = {l["code"] for l in body["supported_active_lateralities"]}
    assert lats == {"OD", "OS", "OU", "NA"}


def test_get_includes_disclosure_with_safe_claims_language(client):
    d = _get(client).json()["disclosure"].lower()
    assert "does not auto-classify" in d
    assert "does not autonomously select an eye" in d
    assert "does not diagnose" in d
    assert "does not add new clinical intelligence" in d


def test_get_emphasis_panel_codes_subset_of_panel_order(client):
    body = _get(client).json()
    panel_order = set(body["profile"]["panel_order"])
    emphasised = set(body["emphasis"]["emphasised_panels"])
    secondary = set(body["emphasis"]["secondary_panels"])
    assert emphasised.issubset(panel_order)
    assert secondary.issubset(panel_order)
    assert emphasised.isdisjoint(secondary)
    assert emphasised | secondary == panel_order


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_unknown_encounter_returns_404(client):
    r = client.get(
        "/api/v1/encounters/999999/workspace-state", headers=CLIN1
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Visit mode PATCH
# ---------------------------------------------------------------------------


def test_patch_visit_mode_to_follow_up_emphasises_follow_up_panels(client):
    body = _patch_visit_mode(client, mode="follow_up").json()
    assert body["visit_mode"] == "follow_up"
    assert body["visit_mode_label"] == "Follow-up"
    emphasised = set(body["emphasis"]["emphasised_panels"])
    # follow-up emphasis includes anti_vegf_injection in any profile
    # that has it on the panel_order.
    panel_order = set(body["profile"]["panel_order"])
    assert "note_validation" in emphasised
    if "anti_vegf_injection" in panel_order:
        assert "anti_vegf_injection" in emphasised


def test_patch_visit_mode_to_surgical_pre_op_emphasises_cataract(client):
    assert _patch_encounter_type(client, typ="cataract").status_code == 200
    body = _patch_visit_mode(client, mode="surgical_pre_op").json()
    assert body["visit_mode"] == "surgical_pre_op"
    emphasised = set(body["emphasis"]["emphasised_panels"])
    assert "cataract_workflow" in emphasised
    assert "ophthalmic_medication_safety" in emphasised


def test_patch_visit_mode_persists(client):
    _patch_visit_mode(client, mode="post_op")
    body = _get(client).json()
    assert body["visit_mode"] == "post_op"


def test_patch_visit_mode_rejects_unknown_mode(client):
    r = _patch_visit_mode(client, mode="time_travel")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_visit_mode"


def test_patch_visit_mode_requires_admin_or_clinician(client):
    assert _patch_visit_mode(client, headers=TECH1).status_code == 403
    assert _patch_visit_mode(client, headers=REV1).status_code == 403
    assert _patch_visit_mode(client, headers=FRONT1).status_code == 403
    assert _patch_visit_mode(client, headers=ADMIN1).status_code == 200


def test_patch_visit_mode_cross_org_returns_404(client):
    assert _patch_visit_mode(client, headers=ADMIN2).status_code == 404


# ---------------------------------------------------------------------------
# Active laterality PATCH
# ---------------------------------------------------------------------------


def test_patch_active_laterality_persists_and_returns_label(client):
    body = _patch_active_laterality(client, lat="OD").json()
    assert body["active_laterality"] == "OD"
    assert body["active_laterality_label"] == "OD · Right eye"
    again = _get(client).json()
    assert again["active_laterality"] == "OD"


def test_patch_active_laterality_supports_all_values(client):
    for lat in ("OD", "OS", "OU", "NA"):
        r = _patch_active_laterality(client, lat=lat)
        assert r.status_code == 200, (lat, r.text)


def test_patch_active_laterality_rejects_unknown(client):
    r = _patch_active_laterality(client, lat="left")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_active_laterality"


def test_patch_active_laterality_requires_admin_or_clinician(client):
    assert _patch_active_laterality(client, headers=TECH1).status_code == 403
    assert _patch_active_laterality(client, headers=REV1).status_code == 403
    assert _patch_active_laterality(client, headers=ADMIN1).status_code == 200


def test_patch_active_laterality_cross_org_returns_404(client):
    assert _patch_active_laterality(client, headers=ADMIN2).status_code == 404


# ---------------------------------------------------------------------------
# Profile integration — every emphasis panel still exists in the profile
# ---------------------------------------------------------------------------


def test_state_reflects_phase_86_profile_change(client):
    assert _patch_encounter_type(client, typ="retina").status_code == 200
    body = _get(client).json()
    assert body["encounter_type"] == "retina"
    assert body["encounter_type_label"] == "Retina"
    panel_order = body["profile"]["panel_order"]
    # All 12 known panels must appear (Phase 86 invariant: never hide
    # data; collapsed but accessible).
    assert len(panel_order) >= 12


def test_state_emphasis_for_each_visit_mode_subset_of_panel_order(client):
    panel_order_baseline = set(_get(client).json()["profile"]["panel_order"])
    for mode in (
        "intake",
        "surgical_pre_op",
        "post_op",
        "follow_up",
        "lab_review",
        "unscheduled",
    ):
        body = _patch_visit_mode(client, mode=mode).json()
        assert set(body["emphasis"]["emphasised_panels"]).issubset(
            panel_order_baseline
        )


# ---------------------------------------------------------------------------
# Safety contract
# ---------------------------------------------------------------------------


def test_response_never_includes_autonomous_classification_language(client):
    _patch_visit_mode(client, mode="follow_up")
    _patch_active_laterality(client, lat="OD")
    body = _get(client).json()
    blob = str(body).lower().replace(body["disclosure"].lower(), "")
    for forbidden in (
        "auto-classified",
        "subspecialty detected",
        "auto-selected eye",
        "auto-staged",
        "diagnosis confirmed",
        "treatment recommended",
    ):
        assert forbidden not in blob, forbidden
