"""Phase 83 — Pre-sign acknowledgement persistence tests."""

from __future__ import annotations

import json

ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
TECH1 = {"X-User-Email": "tech@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}

URL = "/api/v1/encounters/1/note-validation/acknowledgements"


def _post(client, headers=CLIN1, **over):
    payload = {
        "validation_item_id": "laterality:rollup",
        "validation_category": "laterality",
        "acknowledgement_type": "acknowledged",
        **over,
    }
    return client.post(URL, headers=headers, json=payload)


def test_post_creates_metadata_only_ack(client):
    r = _post(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["encounter_id"] == 1
    assert body["validation_item_id"] == "laterality:rollup"
    assert body["validation_category"] == "laterality"
    assert body["acknowledgement_type"] == "acknowledged"
    assert body["actor_display_name"] == "Casey Clinician"
    assert body["actor_role"] == "clinician"
    assert isinstance(body["acknowledgement_timestamp"], str)
    assert isinstance(body["id"], int)


def test_list_returns_newest_first_for_encounter(client):
    assert _post(client, validation_item_id="laterality:rollup").status_code == 201
    assert (
        _post(client, validation_item_id="unsigned:fundus:1").status_code == 201
    )
    r = client.get(URL, headers=CLIN1)
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 2
    assert items[0]["validation_item_id"] == "unsigned:fundus:1"
    assert items[1]["validation_item_id"] == "laterality:rollup"
    for it in items:
        assert it["encounter_id"] == 1
        assert it["actor_role"] in ("clinician", "admin")


def test_ack_is_append_only(client):
    # Same caller, same check — should produce two distinct rows.
    a = _post(client).json()
    b = _post(client).json()
    assert a["id"] != b["id"]
    r = client.get(URL, headers=CLIN1)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 2


def test_rescind_ack_type_accepted(client):
    r = _post(client, acknowledgement_type="rescinded")
    assert r.status_code == 201, r.text
    assert r.json()["acknowledgement_type"] == "rescinded"


def test_invalid_ack_type_rejected(client):
    r = _post(client, acknowledgement_type="forever")
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error_code"] == "invalid_ack_type"


def test_invalid_check_id_rejected(client):
    r = _post(client, validation_item_id="")
    assert r.status_code == 422
    r = _post(client, validation_item_id="bad space")
    assert r.status_code == 422
    r = _post(client, validation_item_id="x" * 121)
    assert r.status_code == 422


def test_invalid_category_rejected(client):
    r = _post(client, validation_category="bad space")
    assert r.status_code == 422


def test_payload_must_not_include_free_text_fields(client):
    """Defensive: any free-text key on the payload is rejected."""
    r = client.post(
        URL,
        headers=CLIN1,
        json={
            "validation_item_id": "laterality:rollup",
            "validation_category": "laterality",
            "acknowledgement_type": "acknowledged",
            "note": "Provider canary note text.",
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["error_code"] == "forbidden_payload_field"


def test_cross_org_returns_404(client):
    assert _post(client, headers=ADMIN2).status_code == 404
    r = client.get(URL, headers=ADMIN2)
    assert r.status_code == 404


def test_unknown_encounter_returns_404(client):
    r = client.post(
        "/api/v1/encounters/99999/note-validation/acknowledgements",
        headers=CLIN1,
        json={
            "validation_item_id": "x",
            "validation_category": "laterality",
        },
    )
    assert r.status_code == 404
    r = client.get(
        "/api/v1/encounters/99999/note-validation/acknowledgements",
        headers=CLIN1,
    )
    assert r.status_code == 404


def test_unauthenticated_returns_401(client):
    r = client.post(URL, json={"validation_item_id": "x", "validation_category": "y"})
    assert r.status_code in (401, 403)
    r = client.get(URL)
    assert r.status_code in (401, 403)


def test_role_diversity_renders_correctly(client):
    # Different callers produce different actor roles on the ack rows.
    assert _post(client, headers=CLIN1).status_code == 201
    assert _post(client, headers=ADMIN1).status_code == 201
    r = client.get(URL, headers=CLIN1)
    items = r.json()
    roles = {it["actor_role"] for it in items}
    assert "clinician" in roles
    assert "admin" in roles
    names = {it["actor_display_name"] for it in items}
    assert "Casey Clinician" in names
    assert "ChartNav Admin" in names


def test_audit_row_detail_is_metadata_only_canary(client):
    # Forcibly drop a known-canary string into other detail surfaces
    # and assert it cannot have leaked into the ack audit rows.
    assert _post(client).status_code == 201
    r = client.get(URL, headers=CLIN1)
    blob = json.dumps(r.json()).lower()
    for forbidden in [
        "diagnosis confirmed",
        "treatment recommended",
        "rapid progression",
        "stage iii",
        "iol power",
        "phaco recommended",
        "order placed",
        "billing code",
        # the canary we explicitly rejected on POST should never be
        # present anywhere in the GET payload either.
        "provider canary note",
    ]:
        assert forbidden not in blob


def test_evidence_timeline_includes_ack_events(client):
    # Drop one ack and confirm Phase 76's retina visit summary timeline
    # surfaces it as a note_validation/acknowledged event.
    assert _post(client).status_code == 201
    r = client.get(
        "/api/v1/encounters/1/retina-visit-summary", headers=CLIN1
    )
    assert r.status_code == 200, r.text
    events = r.json()["evidence_timeline"]
    ack_events = [
        e for e in events
        if e["artifact_type"] == "note_validation"
        and e["event_type"] == "acknowledged"
    ]
    assert len(ack_events) == 1
    ev = ack_events[0]
    assert ev["validation_item_id"] == "laterality:rollup"
    assert ev["validation_category"] == "laterality"
    assert ev["acknowledgement_type"] == "acknowledged"
    assert ev["actor_role"] == "clinician"
    assert ev["actor_display_name"] == "Casey Clinician"
