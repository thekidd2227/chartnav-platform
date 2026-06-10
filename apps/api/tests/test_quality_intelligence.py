"""Phase 89 — IRIS / MIPS Quality Intelligence tests."""

from __future__ import annotations

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _get(client, encounter_id=1, headers=CLIN1, program_year=None):
    qs = f"?program_year={program_year}" if program_year else ""
    return client.get(
        f"/api/v1/encounters/{encounter_id}/quality-measures{qs}",
        headers=headers,
    )


def _post(
    client,
    encounter_id=1,
    measure_id="chartnav_demo_ophth_dr_communication",
    response_type="met",
    exception_code=None,
    headers=CLIN1,
):
    payload = {"response_type": response_type}
    if exception_code is not None:
        payload["exception_code"] = exception_code
    return client.post(
        f"/api/v1/encounters/{encounter_id}/quality-measures/"
        f"{measure_id}/response",
        headers=headers,
        json=payload,
    )


def _analytics(client, headers=CLIN1, program_year=None):
    qs = f"?program_year={program_year}" if program_year else ""
    return client.get(f"/api/v1/analytics/quality{qs}", headers=headers)


# ---------------------------------------------------------------------------
# GET — encounter-scoped projection
# ---------------------------------------------------------------------------


def test_get_returns_seeded_demo_specs_with_internal_demo_flag(client):
    body = _get(client).json()
    assert body["encounter_id"] == 1
    assert body["internal_demo_specs_present"] is True
    assert body["submission_status"] == "not_submitted"
    measure_ids = {it["measure_id"] for it in body["items"]}
    assert "chartnav_demo_ophth_dr_communication" in measure_ids
    assert "chartnav_demo_ophth_poag_iop_documentation" in measure_ids
    assert "chartnav_demo_ophth_dr_screening" in measure_ids
    for item in body["items"]:
        assert item["internal_demo_only"] is True
        assert item["verified_for_submission"] is False
        assert item["submission_status"] == "not_submitted"


def test_get_includes_disclosure_with_safe_language(client):
    body = _get(client).json()
    d = body["disclosure"].lower()
    assert "does not submit to cms" in d
    assert "iris" in d
    assert "does not autonomously compute mips scoring" in d
    assert "does not interpret images" in d
    assert "does not diagnose" in d


def test_get_supported_response_types_are_closed_allowlist(client):
    body = _get(client).json()
    assert set(body["supported_response_types"]) == {
        "met", "exception", "exclusion", "not_applicable", "incomplete",
    }


def test_get_response_status_pending_when_no_response_recorded(client):
    body = _get(client).json()
    applicable = [it for it in body["items"] if it["applicable"]]
    assert len(applicable) >= 1
    for item in applicable:
        assert item["response_status"] in {"pending", "not_applicable"}


def test_get_program_year_filter_works(client):
    # All seeded demo specs are 2026.
    body = _get(client, program_year=2026).json()
    assert body["counts"]["total"] >= 3
    body_empty = _get(client, program_year=2025).json()
    assert body_empty["counts"]["total"] == 0


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_unknown_encounter_returns_404(client):
    assert _get(client, encounter_id=999999).status_code == 404


# ---------------------------------------------------------------------------
# POST — record response
# ---------------------------------------------------------------------------


def test_post_records_met_response_and_actor(client):
    r = _post(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["response_type"] == "met"
    assert body["responded_by_display"] == "Casey Clinician"
    assert body["responded_by_role"] == "clinician"
    assert body["encounter_id"] == 1
    assert body["measure_id"] == "chartnav_demo_ophth_dr_communication"


def test_post_records_exception_with_valid_code(client):
    r = _post(client, response_type="exception", exception_code="patient_refused")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["response_type"] == "exception"
    assert body["exception_code"] == "patient_refused"


def test_post_rejects_exception_code_with_non_exception_type(client):
    r = _post(client, response_type="met", exception_code="patient_refused")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_exception_code"


def test_post_rejects_invalid_response_type(client):
    r = _post(client, response_type="passing")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_response_type"


def test_post_rejects_exception_code_not_in_spec(client):
    r = _post(client, response_type="exception", exception_code="not_in_spec")
    assert r.status_code == 422


def test_post_unknown_measure_id_returns_404(client):
    r = _post(client, measure_id="not_a_real_measure")
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "measure_spec_not_found"


def test_post_requires_admin_or_clinician(client):
    assert _post(client, headers=TECH1).status_code == 403
    assert _post(client, headers=REV1).status_code == 403
    assert _post(client, headers=FRONT1).status_code == 403
    assert _post(client, headers=ADMIN1).status_code == 201


def test_post_cross_org_returns_404(client):
    assert _post(client, headers=ADMIN2).status_code == 404


def test_post_is_upsert_idempotent(client):
    first = _post(client, response_type="met").json()
    second = _post(client, response_type="incomplete").json()
    # Same row id (UPDATE, not INSERT).
    assert second["id"] == first["id"]
    assert second["response_type"] == "incomplete"


def test_post_reflects_in_subsequent_get(client):
    _post(client)
    body = _get(client).json()
    by_id = {it["measure_id"]: it for it in body["items"]}
    target = by_id["chartnav_demo_ophth_dr_communication"]
    assert target["response_status"] == "met"
    assert target["responded_by_display"] == "Casey Clinician"


# ---------------------------------------------------------------------------
# Analytics rollup
# ---------------------------------------------------------------------------


def test_analytics_baseline_lists_specs_with_zero_responses(client):
    body = _analytics(client).json()
    assert body["organization_id"] == 1
    assert body["submission_status"] == "not_submitted"
    assert body["internal_demo_specs_present"] is True
    by_id = {m["measure_id"]: m for m in body["measures"]}
    target = by_id["chartnav_demo_ophth_dr_communication"]
    assert target["response_counts"] == {
        "met": 0, "exception": 0, "exclusion": 0,
        "not_applicable": 0, "incomplete": 0,
    }
    assert target["total_responses"] == 0
    assert target["verified_for_submission"] is False
    assert target["internal_demo_only"] is True
    assert target["submission_status"] == "not_submitted"


def test_analytics_counts_responses(client):
    _post(client, response_type="met")
    body = _analytics(client).json()
    by_id = {m["measure_id"]: m for m in body["measures"]}
    target = by_id["chartnav_demo_ophth_dr_communication"]
    assert target["response_counts"]["met"] == 1
    assert target["total_responses"] == 1


def test_analytics_includes_disclosure(client):
    body = _analytics(client).json()
    d = body["disclosure"].lower()
    assert "does not submit to cms" in d
    assert "internal_demo_only" in d or "verified by a qualified operator" in d


def test_analytics_program_year_filter(client):
    body = _analytics(client, program_year=2026).json()
    assert len(body["measures"]) >= 3
    body_empty = _analytics(client, program_year=2025).json()
    assert body_empty["measures"] == []


def test_analytics_cross_org_returns_only_own_org_data(client):
    _post(client, response_type="met")
    body_2 = _analytics(client, headers=ADMIN2).json()
    assert body_2["organization_id"] == 2
    for m in body_2["measures"]:
        assert m["total_responses"] == 0


# ---------------------------------------------------------------------------
# Safety contract canary
# ---------------------------------------------------------------------------


def test_response_never_includes_submission_or_scoring_language(client):
    _post(client, response_type="met")
    body = _get(client).json()
    blob = str(body).lower().replace(body["disclosure"].lower(), "")
    for forbidden in (
        "submitted to cms",
        "submitted to iris",
        "submitted to payer",
        "mips score",
        "auto-submitted",
        "auto-billed",
        "auto-coded",
        "guaranteed compliance",
        "billing optimization",
        "certified quality reporting",
        "automatic mips submission",
        "iris connected",
    ):
        assert forbidden not in blob, forbidden


def test_analytics_never_includes_submission_or_scoring_language(client):
    body = _analytics(client).json()
    blob = str(body).lower().replace(body["disclosure"].lower(), "")
    for forbidden in (
        "submitted to cms",
        "submitted to iris",
        "submitted to payer",
        "mips score",
        "auto-submitted",
        "guaranteed compliance",
        "iris connected",
    ):
        assert forbidden not in blob, forbidden
