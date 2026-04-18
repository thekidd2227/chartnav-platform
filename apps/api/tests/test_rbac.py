from tests.conftest import ADMIN1, CLIN1, CLIN2, REV1


def _mk_encounter_body(org_id: int, loc_id: int, patient: str):
    return {
        "organization_id": org_id,
        "location_id": loc_id,
        "patient_identifier": patient,
        "patient_name": None,
        "provider_name": "Dr. Test",
        "status": "scheduled",
    }


def test_admin_can_create_encounter(client, seeded_ids):
    org_id = seeded_ids["orgs"]["demo-eye-clinic"]
    loc_id = seeded_ids["locs_by_org"][org_id]
    r = client.post(
        "/encounters",
        headers=ADMIN1,
        json=_mk_encounter_body(org_id, loc_id, "PT-A-ADMIN"),
    )
    assert r.status_code == 201, r.json()


def test_clinician_can_create_encounter(client, seeded_ids):
    org_id = seeded_ids["orgs"]["demo-eye-clinic"]
    loc_id = seeded_ids["locs_by_org"][org_id]
    r = client.post(
        "/encounters",
        headers=CLIN1,
        json=_mk_encounter_body(org_id, loc_id, "PT-A-CLIN"),
    )
    assert r.status_code == 201


def test_reviewer_cannot_create_encounter(client, seeded_ids):
    org_id = seeded_ids["orgs"]["demo-eye-clinic"]
    loc_id = seeded_ids["locs_by_org"][org_id]
    r = client.post(
        "/encounters",
        headers=REV1,
        json=_mk_encounter_body(org_id, loc_id, "PT-A-REV"),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_create_encounter"


def test_reviewer_cannot_add_event(client, seeded_ids):
    enc_id = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc_id}/events",
        headers=REV1,
        json={"event_type": "note_added"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_create_event"


def test_clinician_can_perform_operational_transition(client, seeded_ids):
    # PT-1001 starts at in_progress → draft_ready is a clinician edge.
    enc_id = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc_id}/status", headers=CLIN1, json={"status": "draft_ready"}
    )
    assert r.status_code == 200, r.json()
    assert r.json()["status"] == "draft_ready"


def test_clinician_cannot_perform_reviewer_transition(client, seeded_ids):
    # PT-1002 is at review_needed; completing it is a reviewer/admin edge.
    enc_id = seeded_ids["encs"]["PT-1002"][0]
    r = client.post(
        f"/encounters/{enc_id}/status", headers=CLIN1, json={"status": "completed"}
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_transition"


def test_reviewer_can_complete_review(client, seeded_ids):
    enc_id = seeded_ids["encs"]["PT-1002"][0]
    r = client.post(
        f"/encounters/{enc_id}/status", headers=REV1, json={"status": "completed"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_reviewer_can_kick_back(client, seeded_ids):
    # move PT-1002 back: review_needed -> draft_ready
    enc_id = seeded_ids["encs"]["PT-1002"][0]
    r = client.post(
        f"/encounters/{enc_id}/status", headers=REV1, json={"status": "draft_ready"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "draft_ready"


def test_cross_org_mutate_blocked_404(client, seeded_ids):
    # CLIN2 tries to mutate PT-1001 (org1)
    enc_id = seeded_ids["encs"]["PT-1001"][0]
    r = client.post(
        f"/encounters/{enc_id}/status", headers=CLIN2, json={"status": "draft_ready"}
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_invalid_transition_400_preserved(client, seeded_ids):
    enc_id = seeded_ids["encs"]["PT-1001"][0]  # in_progress
    r = client.post(
        f"/encounters/{enc_id}/status", headers=ADMIN1, json={"status": "completed"}
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_transition"


def test_status_change_writes_workflow_event(client, seeded_ids):
    # PT-2001 at scheduled; CLIN2 advances to in_progress.
    enc_id = seeded_ids["encs"]["PT-2001"][0]
    before = client.get(f"/encounters/{enc_id}/events", headers=CLIN2).json()
    r = client.post(
        f"/encounters/{enc_id}/status", headers=CLIN2, json={"status": "in_progress"}
    )
    assert r.status_code == 200
    after = client.get(f"/encounters/{enc_id}/events", headers=CLIN2).json()
    assert len(after) == len(before) + 1
    last = after[-1]
    assert last["event_type"] == "status_changed"
    assert last["event_data"]["old_status"] == "scheduled"
    assert last["event_data"]["new_status"] == "in_progress"
    assert last["event_data"]["changed_by"] == "clin@northside.local"


def test_cross_org_create_body_mismatch_403(client, seeded_ids):
    org2 = seeded_ids["orgs"]["northside-retina"]
    loc2 = seeded_ids["locs_by_org"][org2]
    r = client.post(
        "/encounters",
        headers=ADMIN1,  # org1 admin
        json=_mk_encounter_body(org2, loc2, "PT-EVIL"),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "cross_org_access_forbidden"
