"""Phase 29 — Clinical Shortcuts usage audit.

The shortcut catalog itself is static frontend content (no DB seed);
the backend surface is a single POST that records that a clinician
inserted a shortcut, for the same analytics question phase 28 added
for Quick Comments but on a separately-keyed event stream.

Covers:
- clinician records use → 202 + audit event `clinician_shortcut_used`
- empty / whitespace shortcut_id rejected
- note_version_id + encounter_id context surfaces in the event detail
- reviewer → 403 `role_cannot_edit_quick_comments`
- audit detail does NOT contain arbitrary body / draft text (PHI)
- event stream is distinct from the phase-28 quick-comment event
- surface isolation: the endpoint doesn't leak into encounter reads
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}


def test_record_shortcut_use_happy_path(client):
    r = client.post(
        "/me/clinical-shortcuts/used",
        json={
            "shortcut_id": "rd-01",
            "note_version_id": 42,
            "encounter_id": 1,
        },
        headers=CLIN1,
    )
    assert r.status_code == 202, r.text
    assert r.json()["shortcut_id"] == "rd-01"

    # Audit event recorded with the ref + context.
    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    used = [
        ev
        for ev in items
        if ev["event_type"] == "clinician_shortcut_used"
    ]
    assert len(used) == 1
    detail = used[0]["detail"] or ""
    assert "shortcut_id=rd-01" in detail
    assert "note_version_id=42" in detail
    assert "encounter_id=1" in detail


def test_record_shortcut_use_requires_id(client):
    r = client.post(
        "/me/clinical-shortcuts/used",
        json={"shortcut_id": ""},
        headers=CLIN1,
    )
    # Pydantic min_length rejects the empty string at the 422 layer.
    # Either 400 (our in-handler guard) or 422 (validator) is
    # acceptable as long as the write never reaches the audit log.
    assert r.status_code in (400, 422)


def test_reviewer_cannot_record_shortcut_use(client):
    r = client.post(
        "/me/clinical-shortcuts/used",
        json={"shortcut_id": "pvd-01"},
        headers=REV1,
    )
    assert r.status_code == 403
    assert (
        r.json()["detail"]["error_code"] == "role_cannot_edit_quick_comments"
    )


def test_shortcut_audit_does_not_carry_body(client):
    # The endpoint only accepts `shortcut_id` — there is no body
    # field. This asserts the invariant by trying to sneak a body in
    # and confirming it never lands in the audit record.
    r = client.post(
        "/me/clinical-shortcuts/used",
        json={
            "shortcut_id": "amd-03",
            "body": "Should be ignored by the API and never audited.",
        },
        headers=CLIN1,
    )
    assert r.status_code == 202
    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    for ev in items:
        if ev["event_type"] != "clinician_shortcut_used":
            continue
        assert "Should be ignored" not in (ev["detail"] or "")


def test_shortcut_event_type_is_distinct_from_quick_comment(client):
    client.post(
        "/me/clinical-shortcuts/used",
        json={"shortcut_id": "pvd-02"},
        headers=CLIN1,
    )
    client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "sx-01"},
        headers=CLIN1,
    )
    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    types = {ev["event_type"] for ev in items}
    assert "clinician_shortcut_used" in types
    assert "clinician_quick_comment_used" in types


def test_shortcut_events_do_not_appear_on_encounter_reads(client):
    client.post(
        "/me/clinical-shortcuts/used",
        json={"shortcut_id": "amd-01", "encounter_id": 1},
        headers=CLIN1,
    )
    # Encounter detail + events must not surface the shortcut row as
    # if it were an encounter-level event.
    r = client.get("/encounters/1", headers=CLIN1)
    assert r.status_code == 200
    body_text = str(r.json())
    assert "shortcut_id" not in body_text
    r = client.get("/encounters/1/events", headers=CLIN1)
    for ev in r.json():
        assert "shortcut_id=amd-01" not in str(ev.get("event_data", ""))
