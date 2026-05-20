"""Phase 63C-1 — pin the smoke's exact payloads against the live route
schemas.

The Phase 63B audit identified four backend 500s on the iMac stack
when the new `scripts/demo/phase63c_functional_smoke.sh` exercised
Vitals / VisitDraft / Fundus / manual_note.

This test file pins the **exact JSON payloads the smoke sends** to
the **exact routes the smoke targets** against a freshly migrated
+ seeded test DB. If any route schema changes a field name or makes
a previously-optional field required, this test breaks before the
smoke runs — surfacing the bug at PR time, not on the operator's
machine.

These tests intentionally use the smoke's payloads verbatim. They
are NOT the place to test broader workflow behaviour — that is
covered by test_vitals_workup.py, test_fundus_charts.py, and
test_ambient_documentation.py.
"""

from __future__ import annotations


# The smoke's payloads, copied verbatim from
# scripts/demo/phase63c_functional_smoke.sh. Keep these in sync.
SMOKE_VITALS_PAYLOAD = {
    "source_type": "technician_entry",
    "heart_rate_bpm": 72,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 78,
    "temperature_value": 98.6,
    "temperature_unit": "F",
    "spo2_pct": 99,
    "respiratory_rate_bpm": 16,
    "weight_lb": 170,
    "height_in": 70,
}

SMOKE_SCRIBE_PAYLOAD = {
    "encounter_id": 1,
    "fake_data_context": True,
    "transcript_text": (
        "Demo transcript only. Patient reports blurry vision OD x 2 weeks."
    ),
}

SMOKE_FUNDUS_PAYLOAD = {
    "findings_text": "horseshoe tear at 10:30 OD",
    "laterality": "OD",
    "fake_data_context": True,
}

SMOKE_MANUAL_NOTE_STRING_PAYLOAD = {
    "event_type": "manual_note",
    "event_data": "hello",
}

SMOKE_MANUAL_NOTE_OBJECT_PAYLOAD = {
    "event_type": "manual_note",
    "event_data": {"note": "smoke ok"},
}

CLINICIAN_HEADERS = {"X-User-Email": "clin@chartnav.local"}


def test_smoke_vitals_payload_creates_workup_on_morgan_encounter(
    client, seeded_ids
) -> None:
    """The Phase 63C smoke's vitals POST must return 201 against a
    fresh seed. Unknown smoke-only fields (heart_rate_bpm, spo2_pct,
    etc.) are intentionally non-canonical aliases the operator's UI
    might send — Pydantic drops them and the workup is created
    with the canonical fields it does recognise."""
    r = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_VITALS_PAYLOAD,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["organization_id"] == 1
    assert body["encounter_id"] == 1
    assert body["status"] == "draft"
    # Temperature came through canonically.
    assert body["temperature_value"] == 98.6
    assert body["temperature_unit"] == "F"
    assert "id" in body


def test_smoke_scribe_payload_creates_session_on_morgan_encounter(
    client, seeded_ids
) -> None:
    r = client.post(
        "/patients/1/scribe-sessions",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_SCRIBE_PAYLOAD,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["patient_id"] == 1
    assert body["encounter_id"] == 1
    assert body["status"] == "draft"
    assert body["transcript_text"].startswith("Demo transcript only.")
    assert "id" in body


def test_smoke_fundus_payload_generates_chart_on_morgan_encounter(
    client, seeded_ids
) -> None:
    r = client.post(
        "/api/v1/encounters/1/fundus-charts/generate",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_FUNDUS_PAYLOAD,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["laterality"] == "OD"
    assert body["status"] == "draft"
    assert "chart_id" in body
    assert "drawing_json" in body
    drawing = body["drawing_json"]
    assert isinstance(drawing, dict)
    elements = drawing.get("elements", [])
    # The deterministic stub recognises "horseshoe tear" + 10:30 OD.
    assert any(
        el.get("type") == "horseshoe_tear" and el.get("laterality") == "OD"
        for el in elements
    ), f"expected horseshoe_tear OD in {elements!r}"


def test_smoke_manual_note_string_is_rejected_400(client, seeded_ids) -> None:
    """Frontend (apps/web/src/utils/shapeEventData.ts) wraps free-text
    as {note: ...}; the backend rejects raw strings. The smoke pins
    this contract."""
    r = client.post(
        "/encounters/1/events",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_MANUAL_NOTE_STRING_PAYLOAD,
    )
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["error_code"] == "invalid_event_data"


def test_smoke_manual_note_object_is_accepted_201(client, seeded_ids) -> None:
    r = client.post(
        "/encounters/1/events",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_MANUAL_NOTE_OBJECT_PAYLOAD,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["event_type"] == "manual_note"
    assert body["event_data"] == {"note": "smoke ok"}


def test_smoke_vitals_full_lifecycle_matches_state_machine(client, seeded_ids) -> None:
    """Phase 63C-2 — the smoke's vitals lifecycle (create → enter →
    review → sign) must match the backend state machine. Pins:

      draft  --PATCH advance_to_entered:true-->  entered
      entered  --POST .../review-->              reviewed
      reviewed  --POST .../sign attested:true--> signed

    Skipping the `advance_to_entered` PATCH causes review to return
    409 invalid_transition (this was the Phase 63C-2 smoke bug)."""
    create = client.post(
        "/api/v1/encounters/1/vitals-workups",
        headers=CLINICIAN_HEADERS,
        json=SMOKE_VITALS_PAYLOAD,
    )
    assert create.status_code == 201, create.text
    wid = create.json()["id"]
    assert create.json()["status"] == "draft"

    # Pin: review without entering must 409 (this is what bit the
    # smoke pre-63C-2). If the backend ever loosens this rule, the
    # smoke can drop the intermediate PATCH — until then it can't.
    bad = client.post(
        f"/api/v1/vitals-workups/{wid}/review",
        headers=CLINICIAN_HEADERS,
        json={},
    )
    assert bad.status_code == 409, bad.text
    assert bad.json()["detail"]["error_code"] == "invalid_transition"

    # Now drive the correct sequence the smoke uses.
    enter = client.patch(
        f"/api/v1/vitals-workups/{wid}",
        headers=CLINICIAN_HEADERS,
        json={"advance_to_entered": True},
    )
    assert enter.status_code == 200, enter.text
    assert enter.json()["status"] == "entered"

    review = client.post(
        f"/api/v1/vitals-workups/{wid}/review",
        headers=CLINICIAN_HEADERS,
        json={},
    )
    assert review.status_code == 200, review.text
    assert review.json()["status"] == "reviewed"

    sign = client.post(
        f"/api/v1/vitals-workups/{wid}/sign",
        headers=CLINICIAN_HEADERS,
        json={"attested": True},
    )
    assert sign.status_code == 200, sign.text
    assert sign.json()["status"] == "signed"

    # Pin: signed is terminal — sign cannot be replayed (immutable).
    replay = client.post(
        f"/api/v1/vitals-workups/{wid}/sign",
        headers=CLINICIAN_HEADERS,
        json={"attested": True},
    )
    assert replay.status_code in (409, 422), replay.text
