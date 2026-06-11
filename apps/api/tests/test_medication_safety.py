"""Phase 90 — Ophthalmic Medication Safety & Adherence Engine tests."""

from __future__ import annotations

from datetime import date, timedelta

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
FRONT1 = {"X-User-Email": "front@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}


def _post_med(client, encounter_id=1, headers=CLIN1, **over):
    payload = {
        "medication_name": "Latanoprost 0.005%",
        "medication_class": "pgf2_analog",
        "route": "drops",
        "laterality": "OU",
        "dose_per_day": 1,
        "preservative_type": "BAK",
        **over,
    }
    return client.post(
        f"/api/v1/encounters/{encounter_id}/ophthalmic-medications",
        headers=headers,
        json=payload,
    )


def _get(client, patient_id=1, headers=CLIN1):
    return client.get(
        f"/api/v1/patients/{patient_id}/medication-safety", headers=headers
    )


def _acknowledge(client, event_id, headers=CLIN1):
    return client.post(
        f"/api/v1/medication-safety-events/{event_id}/acknowledge",
        headers=headers,
    )


def _analytics(client, headers=CLIN1):
    return client.get("/api/v1/analytics/medication-safety", headers=headers)


# ---------------------------------------------------------------------------
# Write — create medication
# ---------------------------------------------------------------------------


def test_post_creates_ophthalmic_medication_with_adherence_fields(client):
    today = date.today()
    r = _post_med(
        client,
        last_fill_date=str(today - timedelta(days=10)),
        days_supply=30,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["medication_name"] == "Latanoprost 0.005%"
    assert body["preservative_type"] == "BAK"
    assert body["preservative_flag"] is True
    assert body["last_fill_date"] is not None
    assert body["days_supply"] == 30
    assert body["active"] is True
    # Refill gap = today - (last_fill + days_supply) = -20 → clamped to 0.
    assert body["refill_gap_days"] == 0


def test_post_rejects_invalid_preservative_type(client):
    r = _post_med(client, preservative_type="rocket_fuel")
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "invalid_preservative_type"


def test_post_rejects_out_of_range_days_supply(client):
    r = _post_med(client, days_supply=400)
    assert r.status_code == 422


def test_post_requires_admin_or_clinician(client):
    assert _post_med(client, headers=TECH1).status_code == 403
    assert _post_med(client, headers=REV1).status_code == 403
    assert _post_med(client, headers=FRONT1).status_code == 403
    assert _post_med(client, headers=ADMIN1).status_code == 201


def test_post_cross_org_returns_404(client):
    assert _post_med(client, headers=ADMIN2).status_code == 404


# ---------------------------------------------------------------------------
# GET — rule engine
# ---------------------------------------------------------------------------


def test_get_baseline_is_empty_with_disclosure(client):
    body = _get(client).json()
    assert body["medications"] == []
    assert body["counts"]["active_events"] == 0
    assert body["signals"]["preservative_burden_count"] == 0
    assert body["signals"]["insufficient_data"] is True
    assert body["submission_status"] == "not_submitted"
    assert body["internal_demo_rules_present"] is True
    assert "does not prescribe" in body["disclosure"].lower()
    assert "does not recommend a medication" in body["disclosure"].lower()
    assert "does not diagnose" in body["disclosure"].lower()


def test_get_preservative_burden_advisory_fires_at_threshold(client):
    # Seed three BAK-preserved drops.
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        assert (
            _post_med(
                client,
                medication_name=f"demo-{klass}",
                medication_class=klass,
                preservative_type="BAK",
            ).status_code
            == 201
        )
    body = _get(client).json()
    rule_keys = {e["rule_key"] for e in body["events"] if e["status"] == "active"}
    assert "ophth_preservative_burden_advisory" in rule_keys
    assert body["signals"]["preservative_burden_count"] == 3


def test_get_preservative_burden_below_threshold_no_event(client):
    for klass in ("pgf2_analog", "beta_blocker"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body = _get(client).json()
    rule_keys = {e["rule_key"] for e in body["events"] if e["status"] == "active"}
    assert "ophth_preservative_burden_advisory" not in rule_keys


def test_get_refill_gap_advisory_fires_when_supply_lapsed(client):
    today = date.today()
    _post_med(
        client,
        last_fill_date=str(today - timedelta(days=60)),
        days_supply=30,
    )
    body = _get(client).json()
    rule_keys = {e["rule_key"] for e in body["events"] if e["status"] == "active"}
    assert "ophth_refill_gap_advisory" in rule_keys
    assert body["signals"]["refill_gap_count"] == 1
    gap = body["signals"]["refill_gaps"][0]
    assert gap["refill_gap_days"] >= 29


def test_get_refill_gap_does_not_fire_when_supply_still_active(client):
    today = date.today()
    _post_med(
        client,
        last_fill_date=str(today - timedelta(days=3)),
        days_supply=30,
    )
    body = _get(client).json()
    rule_keys = {e["rule_key"] for e in body["events"] if e["status"] == "active"}
    assert "ophth_refill_gap_advisory" not in rule_keys


def test_get_duplicate_class_advisory_fires_when_two_same_class_drops(client):
    _post_med(client, medication_name="Drop A", medication_class="beta_blocker")
    _post_med(client, medication_name="Drop B", medication_class="beta_blocker")
    body = _get(client).json()
    rule_keys = {e["rule_key"] for e in body["events"] if e["status"] == "active"}
    assert "ophth_duplicate_class_advisory" in rule_keys


def test_get_messages_never_use_forbidden_recommendation_language(client):
    today = date.today()
    _post_med(
        client,
        last_fill_date=str(today - timedelta(days=60)),
        days_supply=30,
    )
    body = _get(client).json()
    blob = str(body).lower().replace(body["disclosure"].lower(), "")
    for forbidden in (
        "must stop",
        "contraindicated",
        "should prescribe",
        "recommended medication change",
        "discontinue medication",
        "auto-refilled",
        "automated prescription",
        "billing optimization",
    ):
        assert forbidden not in blob, forbidden


def test_get_idempotent_no_event_drift_across_reads(client):
    _post_med(client, medication_name="A", medication_class="pgf2_analog")
    _post_med(client, medication_name="B", medication_class="beta_blocker")
    _post_med(client, medication_name="C", medication_class="alpha_agonist")
    body1 = _get(client).json()
    body2 = _get(client).json()
    assert len(body1["events"]) == len(body2["events"])
    by_id1 = {e["id"] for e in body1["events"]}
    by_id2 = {e["id"] for e in body2["events"]}
    assert by_id1 == by_id2


def test_get_cross_org_returns_404(client):
    assert _get(client, headers=ADMIN2).status_code == 404


# ---------------------------------------------------------------------------
# Acknowledge
# ---------------------------------------------------------------------------


def test_acknowledge_event_marks_status_and_stamps_actor(client):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body = _get(client).json()
    target = [
        e for e in body["events"]
        if e["rule_key"] == "ophth_preservative_burden_advisory"
        and e["status"] == "active"
    ][0]
    r = _acknowledge(client, target["id"])
    assert r.status_code == 200, r.text
    ack = r.json()
    assert ack["status"] == "acknowledged"
    assert ack["acknowledged_by_display_name"] == "Casey Clinician"
    assert ack["acknowledged_by_role"] == "clinician"
    assert ack["acknowledged_at"] is not None


def test_acknowledge_requires_admin_or_clinician(client):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body = _get(client).json()
    target = [
        e for e in body["events"]
        if e["rule_key"] == "ophth_preservative_burden_advisory"
        and e["status"] == "active"
    ][0]
    assert _acknowledge(client, target["id"], headers=TECH1).status_code == 403
    assert _acknowledge(client, target["id"], headers=REV1).status_code == 403


def test_acknowledge_cross_org_returns_404(client):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body = _get(client).json()
    target = [e for e in body["events"] if e["status"] == "active"][0]
    assert _acknowledge(client, target["id"], headers=ADMIN2).status_code == 404


def test_acknowledge_unknown_event_returns_404(client):
    assert _acknowledge(client, 999999).status_code == 404


# ---------------------------------------------------------------------------
# Auto-resolution when condition clears
# ---------------------------------------------------------------------------


def test_event_auto_resolves_when_underlying_condition_clears(client):
    # Seed two BAK drops (below threshold initially).
    a = _post_med(client, medication_name="A", medication_class="pgf2_analog").json()
    b = _post_med(client, medication_name="B", medication_class="beta_blocker").json()
    body = _get(client).json()
    burden_events = [
        e for e in body["events"]
        if e["rule_key"] == "ophth_preservative_burden_advisory"
        and e["status"] == "active"
    ]
    assert burden_events == []
    # Add a third → advisory fires.
    _post_med(client, medication_name="C", medication_class="alpha_agonist")
    body = _get(client).json()
    burden_events = [
        e for e in body["events"]
        if e["rule_key"] == "ophth_preservative_burden_advisory"
        and e["status"] == "active"
    ]
    assert len(burden_events) == 1


# ---------------------------------------------------------------------------
# Analytics rollup
# ---------------------------------------------------------------------------


def test_analytics_lists_seeded_rules_with_zero_counts_baseline(client):
    body = _analytics(client).json()
    assert body["organization_id"] == 1
    assert body["submission_status"] == "not_submitted"
    assert body["internal_demo_rules_present"] is True
    by_key = {r["rule_key"]: r for r in body["rules"]}
    assert "ophth_preservative_burden_advisory" in by_key
    target = by_key["ophth_preservative_burden_advisory"]
    assert target["active"] == 0
    assert target["internal_demo_only"] is True
    assert target["verified_for_clinical_use"] is False


def test_analytics_counts_after_event_acknowledgement(client):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body = _get(client).json()
    target = [
        e for e in body["events"]
        if e["rule_key"] == "ophth_preservative_burden_advisory"
        and e["status"] == "active"
    ][0]
    _acknowledge(client, target["id"])
    body = _analytics(client).json()
    by_key = {r["rule_key"]: r for r in body["rules"]}
    target_rule = by_key["ophth_preservative_burden_advisory"]
    assert target_rule["acknowledged"] >= 1


def test_analytics_cross_org_returns_only_own_org(client):
    for klass in ("pgf2_analog", "beta_blocker", "alpha_agonist"):
        _post_med(
            client,
            medication_name=f"demo-{klass}",
            medication_class=klass,
            preservative_type="BAK",
        )
    body2 = _analytics(client, headers=ADMIN2).json()
    assert body2["organization_id"] == 2
    by_key = {r["rule_key"]: r for r in body2["rules"]}
    for r in by_key.values():
        assert r["active"] == 0
        assert r["acknowledged"] == 0


def test_analytics_does_not_include_forbidden_language(client):
    body = _analytics(client).json()
    blob = str(body).lower().replace(body["disclosure"].lower(), "")
    for forbidden in (
        "must stop",
        "contraindicated",
        "should prescribe",
        "recommended medication change",
        "auto-prescribed",
        "billing optimization",
    ):
        assert forbidden not in blob, forbidden
