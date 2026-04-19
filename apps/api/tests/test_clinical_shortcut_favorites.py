"""Phase 30 — Clinical Shortcut favorites.

Parallel to the phase-28 quick-comment favorites surface but keyed on
the static-catalog stable-string refs (`pvd-01`, `dme-03`, …).
Covers:
- happy path create + idempotent upsert
- list scoping (own only, same org different user excluded)
- unfavorite via query param + idempotent second-call removed=0
- reviewer 403 on all three operations
- audit events `clinician_shortcut_favorited` / `_unfavorited`
- surface isolation — favorites do not leak into encounter reads
- empty shortcut_ref rejected
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}


# ---------------------------------------------------------------------
# happy path + idempotency
# ---------------------------------------------------------------------


def test_favorite_shortcut_happy_path(client):
    r = client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "dme-02"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["shortcut_ref"] == "dme-02"
    assert row["user_id"] is not None
    assert row["organization_id"] is not None


def test_favorite_shortcut_is_idempotent(client):
    r1 = client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "mac-03"},
        headers=CLIN1,
    )
    assert r1.status_code == 201
    id1 = r1.json()["id"]
    # Second identical POST returns the existing row (upsert).
    r2 = client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "mac-03"},
        headers=CLIN1,
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == id1
    # List has exactly one row for that ref.
    rows = client.get(
        "/me/clinical-shortcuts/favorites", headers=CLIN1
    ).json()
    assert [r["shortcut_ref"] for r in rows].count("mac-03") == 1


# ---------------------------------------------------------------------
# scoping
# ---------------------------------------------------------------------


def test_list_shortcut_favorites_is_own_only(client):
    client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "vasc-03"},
        headers=CLIN1,
    )
    client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "post-04"},
        headers=ADMIN1,
    )
    clin_refs = [
        r["shortcut_ref"]
        for r in client.get(
            "/me/clinical-shortcuts/favorites", headers=CLIN1
        ).json()
    ]
    admin_refs = [
        r["shortcut_ref"]
        for r in client.get(
            "/me/clinical-shortcuts/favorites", headers=ADMIN1
        ).json()
    ]
    assert "vasc-03" in clin_refs
    assert "post-04" not in clin_refs
    assert "post-04" in admin_refs
    assert "vasc-03" not in admin_refs


# ---------------------------------------------------------------------
# unfavorite
# ---------------------------------------------------------------------


def test_unfavorite_shortcut_removes_row(client):
    client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "pvd-02"},
        headers=CLIN1,
    )
    r = client.delete(
        "/me/clinical-shortcuts/favorites?shortcut_ref=pvd-02",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["removed"] == 1

    # Second delete is a clean no-op.
    r2 = client.delete(
        "/me/clinical-shortcuts/favorites?shortcut_ref=pvd-02",
        headers=CLIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["removed"] == 0


# ---------------------------------------------------------------------
# role gate
# ---------------------------------------------------------------------


def test_reviewer_cannot_touch_shortcut_favorites(client):
    r = client.get(
        "/me/clinical-shortcuts/favorites", headers=REV1
    )
    assert r.status_code == 403
    r = client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "rd-01"},
        headers=REV1,
    )
    assert r.status_code == 403
    r = client.delete(
        "/me/clinical-shortcuts/favorites?shortcut_ref=rd-01",
        headers=REV1,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------


def test_shortcut_favorite_requires_ref(client):
    # Pydantic min_length=1 rejects the empty string at 422.
    r = client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": ""},
        headers=CLIN1,
    )
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------
# audit events
# ---------------------------------------------------------------------


def test_shortcut_favorite_lifecycle_audit(client):
    client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "vasc-02"},
        headers=CLIN1,
    )
    client.delete(
        "/me/clinical-shortcuts/favorites?shortcut_ref=vasc-02",
        headers=CLIN1,
    )
    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    types = {ev["event_type"] for ev in items}
    assert "clinician_shortcut_favorited" in types
    assert "clinician_shortcut_unfavorited" in types


# ---------------------------------------------------------------------
# surface isolation
# ---------------------------------------------------------------------


def test_shortcut_favorites_not_on_encounter_reads(client):
    client.post(
        "/me/clinical-shortcuts/favorites",
        json={"shortcut_ref": "amd-03"},
        headers=CLIN1,
    )
    r = client.get("/encounters/1", headers=CLIN1)
    assert "shortcut_ref" not in str(r.json())
    r = client.get("/encounters/1/events", headers=CLIN1)
    for ev in r.json():
        assert "amd-03" not in str(ev.get("event_data", ""))
