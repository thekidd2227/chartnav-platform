"""Phase 84 — Disease staging engine tests."""

from __future__ import annotations

import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _post(client, headers=CLIN1, encounter_id=1, **over):
    payload = {
        "diagnosis_code": "h35.31",
        "staging_system": "amd_areds",
        "stage_value": "Category 3",
        **over,
    }
    return client.post(
        f"/api/v1/encounters/{encounter_id}/disease-staging",
        headers=headers,
        json=payload,
    )


def _get(client, patient_id=1, headers=CLIN1, **params):
    qs = ""
    if params:
        qs = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(
        f"/api/v1/patients/{patient_id}/disease-staging{qs}",
        headers=headers,
    )


def test_post_creates_a_stage_record_with_actor_metadata(client):
    r = _post(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["diagnosis_code"] == "h35.31"
    assert body["staging_system"] == "amd_areds"
    assert body["staging_system_label"] == "AMD · AREDS"
    assert body["stage_value"] == "Category 3"
    assert body["prior_stage"] is None
    assert body["progression_detected"] is None
    assert body["elapsed_days_since_prior"] is None
    assert body["patient_id"] == 1
    assert body["encounter_id"] == 1
    assert body["staged_by_display_name"] == "Casey Clinician"
    assert body["staged_by_role"] == "clinician"


def test_post_supports_all_staging_systems_and_their_stages(client):
    cases = [
        ("amd_areds", "Category 1"),
        ("diabetic_etdrs", "Mild NPDR"),
        ("diabetic_etdrs", "High-risk PDR"),
        ("glaucoma_poag", "Mild"),
        ("glaucoma_poag", "Severe"),
        ("keratoconus_amsler_krumeich", "Stage IV"),
        ("dry_eye_dews", "Severity 2"),
    ]
    for system, stage in cases:
        r = _post(
            client,
            staging_system=system,
            stage_value=stage,
            diagnosis_code=f"dx-{system}",
        )
        assert r.status_code == 201, (system, stage, r.text)


def test_post_rejects_unknown_staging_system(client):
    r = _post(client, staging_system="my_custom_system")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_staging_system"


def test_post_rejects_stage_value_not_in_system(client):
    r = _post(client, staging_system="glaucoma_poag", stage_value="Mild NPDR")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_stage_value"


def test_post_rejects_prior_stage_not_in_system(client):
    r = _post(
        client,
        staging_system="amd_areds",
        stage_value="Category 3",
        prior_stage="Severe",
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_prior_stage"


def test_post_requires_admin_or_clinician(client):
    assert _post(client, headers=TECH1).status_code == 403
    assert _post(client, headers=REV1).status_code == 403
    assert _post(client, headers=FRONT1).status_code == 403
    assert _post(client, headers=ADMIN1).status_code == 201
    assert (
        _post(client, headers=CLIN1, diagnosis_code="dx-clin").status_code
        == 201
    )


def test_progression_detected_is_deterministic_equality(client):
    # Two records on the same dx: progression flag is set when the new
    # stage differs from the previous row's stage.
    a = _post(client, stage_value="Category 2")
    assert a.status_code == 201
    b = _post(client, stage_value="Category 3")
    assert b.status_code == 201

    body = _get(client).json()
    records = body["records"]
    assert len(records) == 2
    # Newest first: the second insert.
    assert records[0]["stage_value"] == "Category 3"
    assert records[0]["progression_detected"] is True
    # First insert had no prior row → None (not assumed).
    assert records[1]["progression_detected"] is None


def test_regression_is_treated_as_progression_detected(client):
    """Stage moving *down* still flips progression_detected — ChartNav
    never assumes direction; it only flags change."""
    assert _post(client, stage_value="Category 4").status_code == 201
    assert _post(client, stage_value="Category 2").status_code == 201
    body = _get(client).json()
    assert body["records"][0]["progression_detected"] is True


def test_unchanged_stage_is_not_progression(client):
    assert _post(client, stage_value="Category 3").status_code == 201
    assert _post(client, stage_value="Category 3").status_code == 201
    body = _get(client).json()
    assert body["records"][0]["progression_detected"] is False


def test_list_supports_diagnosis_filter(client):
    assert _post(client, diagnosis_code="h35.31").status_code == 201
    assert (
        _post(
            client,
            staging_system="glaucoma_poag",
            stage_value="Mild",
            diagnosis_code="h40.1",
        ).status_code
        == 201
    )
    full = _get(client).json()
    assert len(full["records"]) == 2

    filtered = _get(client, diagnosis_code="h35.31").json()
    assert len(filtered["records"]) == 1
    assert filtered["records"][0]["diagnosis_code"] == "h35.31"


def test_latest_by_diagnosis_map_groups_correctly(client):
    assert _post(client, stage_value="Category 2").status_code == 201
    assert _post(client, stage_value="Category 4").status_code == 201
    body = _get(client).json()
    latest = body["latest_by_diagnosis"]
    assert "h35.31" in latest
    assert latest["h35.31"]["stage_value"] == "Category 4"


def test_supported_systems_list_is_complete(client):
    body = _get(client).json()
    codes = [s["code"] for s in body["supported_systems"]]
    assert set(codes) == {
        "amd_areds",
        "diabetic_etdrs",
        "glaucoma_poag",
        "keratoconus_amsler_krumeich",
        "dry_eye_dews",
    }


def test_disclosure_boundary_language(client):
    body = _get(client).json()
    d = body["disclosure"].lower()
    assert "provider-entered" in d
    assert "does not stage disease" in d
    assert "does not infer progression" in d
    assert "does not recommend" in d


def test_cross_org_returns_404_on_get_and_post(client):
    r = _get(client, headers=ADMIN2)
    assert r.status_code == 404
    r = _post(client, headers=ADMIN2)
    assert r.status_code == 404


def test_unknown_patient_returns_404(client):
    r = _get(client, patient_id=99999)
    assert r.status_code == 404


def test_unknown_encounter_returns_404(client):
    r = _post(client, encounter_id=99999)
    assert r.status_code == 404


def test_unauthenticated_returns_401(client):
    r = client.get("/api/v1/patients/1/disease-staging")
    assert r.status_code in (401, 403)
    r = client.post(
        "/api/v1/encounters/1/disease-staging",
        json={
            "diagnosis_code": "x",
            "staging_system": "amd_areds",
            "stage_value": "Category 1",
        },
    )
    assert r.status_code in (401, 403)


def test_no_forbidden_clinical_language_in_response(client):
    """Canary: no autonomous-clinical-decision phrasings appear anywhere
    in the staging response, even after several inserts."""
    assert _post(client, stage_value="Category 2").status_code == 201
    assert _post(client, stage_value="Category 4").status_code == 201
    body = _get(client).json()
    blob = json.dumps(body).lower()
    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "surgery recommended",
        "escalation recommended",
        "rapid progression",
        "stage iii confirmed",
        "iol power",
        "order placed",
        "billing code",
        "ai stages",
        "auto-staged",
    ]:
        assert forbidden not in blob, (
            f"forbidden phrase leaked into disease-staging: {forbidden!r}"
        )
