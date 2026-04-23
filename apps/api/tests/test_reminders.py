"""Phase 63 — reminders CRUD + complete contract tests.

Covers:
  POST   /reminders                happy path, role gating, org-scoping of
                                   encounter_id
  GET    /reminders                list + filter by status + by due window
  GET    /reminders/{id}           read-one + cross-org refusal
  PATCH  /reminders/{id}           partial update + invalid status refusal
                                   + completed sets completed_at + by
  POST   /reminders/{id}/complete  idempotent + clinician only
  DELETE /reminders/{id}           soft-cancel flips status, doesn't delete
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def test_create_reminder_happy_path(client):
    due = _iso(datetime(2026, 5, 1, 14, 0))
    r = client.post(
        "/reminders",
        json={
            "title": "Follow up with glaucoma patient",
            "body": "Recheck IOP if not done by next week.",
            "due_at": due,
        },
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "Follow up with glaucoma patient"
    assert body["status"] == "pending"
    assert body["due_at"].startswith("2026-05-01")
    assert body["created_by_user_id"] > 0
    assert body["completed_at"] is None


def test_create_reminder_reviewer_forbidden(client):
    r = client.post(
        "/reminders",
        json={"title": "nope", "due_at": _iso(datetime(2026, 5, 1))},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


def test_create_reminder_unknown_encounter_404(client):
    r = client.post(
        "/reminders",
        json={
            "title": "bad enc",
            "due_at": _iso(datetime(2026, 5, 1)),
            "encounter_id": 99999,
        },
        headers=CLIN1,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "encounter_not_found"


def test_create_reminder_cross_org_encounter_refused(client, seeded_ids):
    # Grab an encounter from org 2 and try to pin it from org 1.
    r = client.get("/encounters", headers=ADMIN2)
    assert r.status_code == 200
    enc_list = r.json()
    enc_list = enc_list if isinstance(enc_list, list) else enc_list.get("items", [])
    assert enc_list, "expected org 2 to have seeded encounters"
    other_enc_id = enc_list[0]["id"]

    r = client.post(
        "/reminders",
        json={
            "title": "cross-org attempt",
            "due_at": _iso(datetime(2026, 5, 1)),
            "encounter_id": other_enc_id,
        },
        headers=CLIN1,
    )
    assert r.status_code in (403, 404), r.text


def test_list_reminders_scoped_and_filtered(client):
    base = datetime(2026, 5, 10, 9, 0)
    # Seed three reminders for org 1.
    titles = ["A", "B", "C"]
    ids = []
    for i, t in enumerate(titles):
        r = client.post(
            "/reminders",
            json={"title": t, "due_at": _iso(base + timedelta(days=i))},
            headers=CLIN1,
        )
        ids.append(r.json()["id"])
    # Seed one for org 2 — must not leak.
    client.post(
        "/reminders",
        json={"title": "OTHER", "due_at": _iso(base)},
        headers=ADMIN2,
    )

    r = client.get("/reminders", headers=CLIN1)
    assert r.status_code == 200
    rows = r.json()
    org1_titles = {row["title"] for row in rows}
    assert org1_titles >= {"A", "B", "C"}
    assert "OTHER" not in org1_titles

    # Status filter — complete one, then filter.
    rid = ids[1]
    r = client.post(f"/reminders/{rid}/complete", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    r = client.get("/reminders?status=pending", headers=CLIN1)
    assert r.status_code == 200
    titles_pending = [row["title"] for row in r.json() if row["title"] in titles]
    assert "B" not in titles_pending

    # Due-window filter — only B+C are within the window.
    frm = _iso(base + timedelta(days=1))
    to = _iso(base + timedelta(days=2))
    r = client.get(
        f"/reminders?due_from={frm}&due_to={to}", headers=CLIN1,
    )
    assert r.status_code == 200
    in_window = {row["title"] for row in r.json() if row["title"] in titles}
    assert in_window == {"B", "C"}


def test_patch_reminder_partial_update_and_invalid_status(client):
    due = _iso(datetime(2026, 5, 20, 10, 0))
    r = client.post(
        "/reminders",
        json={"title": "initial title", "due_at": due},
        headers=CLIN1,
    )
    rid = r.json()["id"]

    # Partial: body only.
    r = client.patch(
        f"/reminders/{rid}",
        json={"body": "now with more detail"},
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["body"] == "now with more detail"
    assert r.json()["title"] == "initial title"

    # Status = completed marks completed_at + completed_by.
    r = client.patch(
        f"/reminders/{rid}",
        json={"status": "completed"},
        headers=CLIN1,
    )
    assert r.status_code == 200
    row = r.json()
    assert row["status"] == "completed"
    assert row["completed_at"] is not None
    assert row["completed_by_user_id"] is not None

    # Invalid status.
    r = client.patch(
        f"/reminders/{rid}",
        json={"status": "bananas"},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_status"


def test_complete_endpoint_is_idempotent(client):
    r = client.post(
        "/reminders",
        json={"title": "one", "due_at": _iso(datetime(2026, 6, 1))},
        headers=CLIN1,
    )
    rid = r.json()["id"]
    a = client.post(f"/reminders/{rid}/complete", headers=CLIN1).json()
    b = client.post(f"/reminders/{rid}/complete", headers=CLIN1).json()
    assert a["status"] == "completed" == b["status"]
    assert a["completed_at"] == b["completed_at"]


def test_delete_reminder_soft_cancels(client):
    r = client.post(
        "/reminders",
        json={"title": "cancel me", "due_at": _iso(datetime(2026, 6, 1))},
        headers=CLIN1,
    )
    rid = r.json()["id"]
    r = client.delete(f"/reminders/{rid}", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # Row still exists — read-one still succeeds.
    r = client.get(f"/reminders/{rid}", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cross_org_read_refused(client):
    # Create in org 1.
    r = client.post(
        "/reminders",
        json={"title": "org1 only", "due_at": _iso(datetime(2026, 6, 1))},
        headers=CLIN1,
    )
    rid = r.json()["id"]
    # Read from org 2 must not leak.
    r = client.get(f"/reminders/{rid}", headers=CLIN2)
    assert r.status_code in (403, 404)


def test_reminder_attached_to_encounter(client, seeded_ids):
    # Pick an encounter belonging to the smaller-numbered org (org 1
    # in the seed order); the seed's org slug varies across builds.
    org_ids = sorted(seeded_ids["orgs"].values())
    assert org_ids, "at least one org must be seeded"
    target_org = org_ids[0]
    enc_ids = [
        eid for (pid, (eid, org, status)) in seeded_ids["encs"].items()
        if org == target_org
    ]
    assert enc_ids
    eid = enc_ids[0]
    r = client.post(
        "/reminders",
        json={
            "title": "check labs",
            "due_at": _iso(datetime(2026, 6, 15)),
            "encounter_id": eid,
        },
        headers=CLIN1,
    )
    assert r.status_code == 201
    rid = r.json()["id"]
    # Filter by encounter_id.
    r = client.get(f"/reminders?encounter_id={eid}", headers=CLIN1)
    assert r.status_code == 200
    assert any(row["id"] == rid for row in r.json())
