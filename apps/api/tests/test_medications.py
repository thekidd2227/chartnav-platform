"""Phase 85 — Ophthalmic Medication Safety & Adherence Engine tests."""

from __future__ import annotations

from datetime import date, timedelta

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _post_med(client, headers=CLIN1, encounter_id=1, **over):
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
        f"/api/v1/encounters/{encounter_id}/medications",
        headers=headers,
        json=payload,
    )


def _post_refill(client, med_id, *, days_supply=30, refill_date=None, headers=CLIN1):
    payload = {"expected_days_supply": days_supply}
    if refill_date is not None:
        payload["refill_date"] = str(refill_date)
    return client.post(
        f"/api/v1/medications/{med_id}/refills",
        headers=headers,
        json=payload,
    )


def _post_allergy(client, headers=CLIN1, patient_id=1, **over):
    payload = {
        "substance": "Penicillin",
        "reaction_type": "rash",
        "severity": "moderate",
        **over,
    }
    return client.post(
        f"/api/v1/patients/{patient_id}/medication-allergies",
        headers=headers,
        json=payload,
    )


def _get(client, patient_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/patients/{patient_id}/medications", headers=headers
    )


# ---------------------------------------------------------------------------
# Write — create medication
# ---------------------------------------------------------------------------


def test_post_creates_medication_with_actor_metadata(client):
    r = _post_med(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["medication_name"] == "Latanoprost 0.005% drops"
    assert body["medication_class"] == "pgf2_analog"
    assert body["medication_class_label"] == "Prostaglandin F2α analog"
    assert body["route"] == "drops"
    assert body["laterality"] == "OU"
    assert body["dose_per_day"] == 1
    assert body["preservative_flag"] is True
    assert body["patient_id"] == 1
    assert body["encounter_id"] == 1
    assert body["recorded_by_role"] == "clinician"
    assert body["recorded_by_display_name"] == "Casey Clinician"
    assert body["is_active"] is True


def test_post_supports_all_classes_routes_lateralities(client):
    cases = [
        ("pgf2_analog", "drops", "OD"),
        ("beta_blocker", "drops", "OS"),
        ("alpha_agonist", "drops", "OU"),
        ("carbonic_anhydrase_inhibitor", "oral", "NA"),
        ("rho_kinase_inhibitor", "drops", "OU"),
        ("combination_drop", "drops", "OU"),
        ("steroid_drop", "drops", "OD"),
        ("nsaid_drop", "drops", "OS"),
        ("antibiotic_drop", "drops", "OU"),
        ("anti_vegf_intravitreal", "intravitreal", "OD"),
        ("lubricant", "drops", "OU"),
        ("oral_systemic_other", "oral", "NA"),
    ]
    for med_class, route, lat in cases:
        r = _post_med(
            client,
            medication_class=med_class,
            route=route,
            laterality=lat,
            medication_name=f"name-{med_class}",
        )
        assert r.status_code == 201, (med_class, route, lat, r.text)


def test_post_rejects_unknown_class(client):
    r = _post_med(client, medication_class="my_custom_class")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_medication_class"


def test_post_rejects_unknown_route(client):
    r = _post_med(client, route="topical_patch")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_route"


def test_post_rejects_unknown_laterality(client):
    r = _post_med(client, laterality="left")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_laterality"


def test_post_rejects_out_of_range_dose(client):
    r = _post_med(client, dose_per_day=99)
    assert r.status_code == 422


def test_post_requires_admin_or_clinician(client):
    assert _post_med(client, headers=TECH1).status_code == 403
    assert _post_med(client, headers=REV1).status_code == 403
    assert _post_med(client, headers=FRONT1).status_code == 403
    assert _post_med(client, headers=ADMIN1).status_code == 201


def test_post_rejects_cross_org_encounter(client):
    r = _post_med(client, headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


# ---------------------------------------------------------------------------
# Refills
# ---------------------------------------------------------------------------


def test_refill_inserts_and_associates_with_medication(client):
    med = _post_med(client).json()
    r = _post_refill(client, med["id"], days_supply=30)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["medication_id"] == med["id"]
    assert body["expected_days_supply"] == 30
    assert body["patient_id"] == med["patient_id"]
    assert body["refill_date"] is not None


def test_refill_rejects_invalid_days_supply(client):
    med = _post_med(client).json()
    assert _post_refill(client, med["id"], days_supply=0).status_code == 422
    assert _post_refill(client, med["id"], days_supply=400).status_code == 422


def test_refill_requires_admin_or_clinician(client):
    med = _post_med(client).json()
    assert _post_refill(
        client, med["id"], days_supply=30, headers=TECH1
    ).status_code == 403


def test_refill_cross_org_returns_404(client):
    med = _post_med(client).json()
    assert _post_refill(
        client, med["id"], days_supply=30, headers=ADMIN2
    ).status_code == 404


# ---------------------------------------------------------------------------
# Discontinue
# ---------------------------------------------------------------------------


def test_discontinue_marks_medication_inactive(client):
    med = _post_med(client).json()
    r = client.patch(
        f"/api/v1/medications/{med['id']}/discontinue",
        headers=CLIN1,
        json={"discontinued_on": str(date.today() - timedelta(days=1))},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["discontinued_on"] is not None
    assert body["is_active"] is False


def test_discontinue_cross_org_returns_404(client):
    med = _post_med(client).json()
    r = client.patch(
        f"/api/v1/medications/{med['id']}/discontinue",
        headers=ADMIN2,
        json={},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Allergies
# ---------------------------------------------------------------------------


def test_allergy_inserts_with_enum_validation(client):
    r = _post_allergy(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["substance"] == "Penicillin"
    assert body["severity"] == "moderate"
    assert body["reaction_type"] == "rash"
    assert body["reaction_type_label"] == "Rash"


def test_allergy_rejects_unknown_severity(client):
    r = _post_allergy(client, severity="catastrophic")
    assert r.status_code == 422


def test_allergy_rejects_unknown_reaction_type(client):
    r = _post_allergy(client, reaction_type="hallucination")
    assert r.status_code == 422


def test_allergy_requires_admin_or_clinician(client):
    assert _post_allergy(client, headers=TECH1).status_code == 403


# ---------------------------------------------------------------------------
# GET — signals
# ---------------------------------------------------------------------------


def test_get_baseline_is_empty_with_disclosure(client):
    body = _get(client).json()
    assert body["medications"] == []
    assert body["refills"] == []
    assert body["allergies"] == []
    assert body["signals"]["polypharmacy_count"] == 0
    assert body["signals"]["preservative_burden"] == 0
    assert body["signals"]["refill_gaps"] == []
    assert body["signals"]["allergy_matches"] == []
    assert body["signals"]["insufficient_data"] is True
    assert "does not prescribe" in body["disclosure"].lower()
    assert "does not refill" in body["disclosure"].lower()
    assert "does not contact the pharmacy" in body["disclosure"].lower()


def test_get_includes_supported_metadata_matrix(client):
    body = _get(client).json()
    codes = {c["code"] for c in body["supported_medication_classes"]}
    assert "pgf2_analog" in codes
    assert "anti_vegf_intravitreal" in codes
    assert set(body["supported_routes"]) == {"drops", "oral", "intravitreal"}
    assert set(body["supported_lateralities"]) == {"OD", "OS", "OU", "NA"}


def test_get_polypharmacy_count_only_counts_active(client):
    a = _post_med(client, medication_name="A", medication_class="pgf2_analog").json()
    _post_med(client, medication_name="B", medication_class="beta_blocker")
    client.patch(
        f"/api/v1/medications/{a['id']}/discontinue",
        headers=CLIN1,
        json={"discontinued_on": str(date.today() - timedelta(days=1))},
    )
    body = _get(client).json()
    assert body["signals"]["polypharmacy_count"] == 1


def test_get_preservative_burden_sums_dose_per_day_for_preserved_drops(client):
    _post_med(
        client,
        medication_name="Latanoprost",
        medication_class="pgf2_analog",
        route="drops",
        dose_per_day=1,
        preservative_flag=True,
    )
    _post_med(
        client,
        medication_name="Timolol",
        medication_class="beta_blocker",
        route="drops",
        dose_per_day=2,
        preservative_flag=True,
    )
    # Non-drop should not count.
    _post_med(
        client,
        medication_name="Acetazolamide",
        medication_class="carbonic_anhydrase_inhibitor",
        route="oral",
        laterality="NA",
        dose_per_day=2,
        preservative_flag=True,
    )
    # Unpreserved drop should not count.
    _post_med(
        client,
        medication_name="Preservative-free lube",
        medication_class="lubricant",
        route="drops",
        dose_per_day=4,
        preservative_flag=False,
    )
    body = _get(client).json()
    assert body["signals"]["preservative_burden"] == 1 + 2  # = 3


def test_get_refill_gap_is_detected_when_supply_lapsed(client):
    med = _post_med(client).json()
    old = date.today() - timedelta(days=60)
    assert _post_refill(client, med["id"], days_supply=30, refill_date=old).status_code == 201
    body = _get(client).json()
    gap_meds = body["signals"]["refill_gaps"]
    assert len(gap_meds) == 1
    assert gap_meds[0]["medication_id"] == med["id"]
    assert gap_meds[0]["gap_days"] >= 29


def test_get_refill_gap_not_flagged_when_supply_still_active(client):
    med = _post_med(client).json()
    recent = date.today() - timedelta(days=5)
    _post_refill(client, med["id"], days_supply=30, refill_date=recent)
    body = _get(client).json()
    assert body["signals"]["refill_gaps"] == []
    med_row = next(m for m in body["medications"] if m["id"] == med["id"])
    assert med_row["refill_gap"]["status"] == "on_track"


def test_get_refill_gap_status_is_no_history_when_no_refills(client):
    med = _post_med(client).json()
    body = _get(client).json()
    med_row = next(m for m in body["medications"] if m["id"] == med["id"])
    assert med_row["refill_gap"]["status"] == "no_history"
    assert med_row["refill_gap"]["has_history"] is False
    assert med_row["refill_gap"]["gap_days"] is None


def test_get_allergy_match_is_literal_substring(client):
    _post_allergy(client, substance="latanoprost", severity="severe")
    _post_med(
        client, medication_name="Latanoprost 0.005% drops"
    )
    body = _get(client).json()
    matches = body["signals"]["allergy_matches"]
    assert len(matches) == 1
    assert matches[0]["allergy_severity"] == "severe"


def test_get_allergy_match_does_not_match_unrelated_substance(client):
    _post_allergy(client, substance="Penicillin")
    _post_med(client, medication_name="Latanoprost 0.005% drops")
    body = _get(client).json()
    assert body["signals"]["allergy_matches"] == []


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


def test_get_excludes_discontinued_medications_from_active_signals(client):
    a = _post_med(
        client,
        medication_name="Drop A",
        preservative_flag=True,
        dose_per_day=2,
    ).json()
    client.patch(
        f"/api/v1/medications/{a['id']}/discontinue",
        headers=CLIN1,
        json={"discontinued_on": str(date.today() - timedelta(days=1))},
    )
    body = _get(client).json()
    assert body["signals"]["polypharmacy_count"] == 0
    assert body["signals"]["preservative_burden"] == 0


# ---------------------------------------------------------------------------
# Safety contract canary
# ---------------------------------------------------------------------------


def test_no_recommendations_or_autonomous_phrases_in_response(client):
    _post_med(client)
    _post_allergy(client)
    body = _get(client).json()
    blob = str(body).lower()
    for forbidden in (
        "recommend",
        "auto-refill",
        "prescription written",
        "auto-prescribed",
        "auto-dose",
        "contact the pharmacy",
        "do not exceed",
        "increase dose",
        "decrease dose",
        "discontinue medication",
        "suggested treatment",
        "drug interaction detected",
    ):
        # Disclosure may contain "does not recommend" — strip that exception.
        body_minus_disclosure = blob.replace(body["disclosure"].lower(), "")
        assert forbidden not in body_minus_disclosure, forbidden
