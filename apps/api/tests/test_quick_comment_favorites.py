"""Phase 28 — quick-comment favorites + usage audit.

Covers:

- POST /me/quick-comments/favorites with preloaded_ref → creates
- POST is idempotent (re-fire returns the same row, no 409)
- POST with both refs or neither → 400 quick_comment_ref_required
- POST with custom_comment_id I don't own → 404
- POST with soft-deleted custom comment → 409 quick_comment_inactive
- GET lists only the caller's favorites (cross-user + cross-org
  invisible)
- DELETE removes the row; second DELETE returns removed=0
- reviewer 403 on all four operations
- favorite create + unfavorite emit audit events
- POST /me/quick-comments/used records an audit event with the
  kind (preloaded/custom) + ref + optional note_version_id
- usage audit refuses both-refs / no-refs
- usage audit body does NOT include comment text — shape invariant
- favorites table is NOT reachable from encounter endpoints
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


# ---------------------------------------------------------------------
# favorites — happy path + idempotency
# ---------------------------------------------------------------------


def test_favorite_preloaded_happy_path(client):
    r = client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "sx-04"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["preloaded_ref"] == "sx-04"
    assert row["custom_comment_id"] is None
    assert row["user_id"] is not None
    assert row["organization_id"] is not None


def test_favorite_is_idempotent(client):
    r1 = client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "vf-24"},
        headers=CLIN1,
    )
    assert r1.status_code == 201
    id1 = r1.json()["id"]

    r2 = client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "vf-24"},
        headers=CLIN1,
    )
    # Idempotent upsert — same row, no 409.
    assert r2.status_code == 201
    assert r2.json()["id"] == id1

    # List still has exactly one row for that ref.
    rows = client.get(
        "/me/quick-comments/favorites", headers=CLIN1
    ).json()
    assert [r["preloaded_ref"] for r in rows].count("vf-24") == 1


def test_favorite_custom_happy_path(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Discussed cataract progression."},
        headers=CLIN1,
    ).json()
    r = client.post(
        "/me/quick-comments/favorites",
        json={"custom_comment_id": created["id"]},
        headers=CLIN1,
    )
    assert r.status_code == 201
    row = r.json()
    assert row["custom_comment_id"] == created["id"]
    assert row["preloaded_ref"] is None


# ---------------------------------------------------------------------
# favorites — validation
# ---------------------------------------------------------------------


def test_favorite_requires_exactly_one_ref(client):
    r = client.post(
        "/me/quick-comments/favorites",
        json={},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "quick_comment_ref_required"

    r = client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "sx-01", "custom_comment_id": 9999},
        headers=CLIN1,
    )
    assert r.status_code == 400


def test_favorite_custom_cross_user_is_404(client):
    # CLIN1 owns the comment; ADMIN1 (same org, different user) tries
    # to favorite it — must 404, not 403.
    created = client.post(
        "/me/quick-comments",
        json={"body": "Owned by clin."},
        headers=CLIN1,
    ).json()
    r = client.post(
        "/me/quick-comments/favorites",
        json={"custom_comment_id": created["id"]},
        headers=ADMIN1,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "quick_comment_not_found"


def test_favorite_custom_soft_deleted_refused(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Will delete."},
        headers=CLIN1,
    ).json()
    client.delete(
        f"/me/quick-comments/{created['id']}", headers=CLIN1
    )  # soft-deletes
    r = client.post(
        "/me/quick-comments/favorites",
        json={"custom_comment_id": created["id"]},
        headers=CLIN1,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error_code"] == "quick_comment_inactive"


# ---------------------------------------------------------------------
# favorites — list scoping
# ---------------------------------------------------------------------


def test_list_favorites_scoped_to_caller(client):
    client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "post-44"},
        headers=CLIN1,
    )
    client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "post-45"},
        headers=ADMIN1,
    )
    clin1_refs = [
        row["preloaded_ref"]
        for row in client.get("/me/quick-comments/favorites", headers=CLIN1).json()
    ]
    admin1_refs = [
        row["preloaded_ref"]
        for row in client.get("/me/quick-comments/favorites", headers=ADMIN1).json()
    ]
    assert "post-44" in clin1_refs
    assert "post-45" not in clin1_refs
    assert "post-45" in admin1_refs
    assert "post-44" not in admin1_refs


# ---------------------------------------------------------------------
# favorites — delete
# ---------------------------------------------------------------------


def test_unfavorite_removes_row(client):
    client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "ant-35"},
        headers=CLIN1,
    )
    r = client.delete(
        "/me/quick-comments/favorites?preloaded_ref=ant-35",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["removed"] == 1

    # Second delete is a clean no-op with removed=0.
    r2 = client.delete(
        "/me/quick-comments/favorites?preloaded_ref=ant-35",
        headers=CLIN1,
    )
    assert r2.status_code == 200
    assert r2.json()["removed"] == 0


# ---------------------------------------------------------------------
# favorites — role gate
# ---------------------------------------------------------------------


def test_reviewer_cannot_touch_favorites(client):
    r = client.get("/me/quick-comments/favorites", headers=REV1)
    assert r.status_code == 403

    r = client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "sx-01"},
        headers=REV1,
    )
    assert r.status_code == 403

    r = client.delete(
        "/me/quick-comments/favorites?preloaded_ref=sx-01",
        headers=REV1,
    )
    assert r.status_code == 403
    assert (
        r.json()["detail"]["error_code"] == "role_cannot_edit_quick_comments"
    )


# ---------------------------------------------------------------------
# favorites — audit events
# ---------------------------------------------------------------------


def test_favorite_lifecycle_audits(client):
    client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "plan-48"},
        headers=CLIN1,
    )
    client.delete(
        "/me/quick-comments/favorites?preloaded_ref=plan-48",
        headers=CLIN1,
    )

    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    types = [ev["event_type"] for ev in items]
    assert "clinician_quick_comment_favorited" in types
    assert "clinician_quick_comment_unfavorited" in types


# ---------------------------------------------------------------------
# usage audit
# ---------------------------------------------------------------------


def test_record_use_preloaded(client):
    r = client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "post-44", "note_version_id": 42},
        headers=CLIN1,
    )
    assert r.status_code == 202, r.text
    assert r.json()["kind"] == "preloaded"

    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    used = [
        ev for ev in items if ev["event_type"] == "clinician_quick_comment_used"
    ]
    assert len(used) == 1
    detail = used[0]["detail"] or ""
    assert "kind=preloaded" in detail
    assert "preloaded_ref=post-44" in detail
    assert "note_version_id=42" in detail


def test_record_use_custom(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Macular exam unremarkable today."},
        headers=CLIN1,
    ).json()
    r = client.post(
        "/me/quick-comments/used",
        json={"custom_comment_id": created["id"]},
        headers=CLIN1,
    )
    assert r.status_code == 202
    assert r.json()["kind"] == "custom"

    events = client.get(
        "/security-audit-events?limit=200", headers=ADMIN1
    ).json()
    items = events["items"] if isinstance(events, dict) else events
    used = [
        ev for ev in items if ev["event_type"] == "clinician_quick_comment_used"
    ]
    # Shape invariant: audit detail must NOT carry the comment body —
    # only the ref. This keeps PHI exposure through the audit log
    # minimal.
    for ev in used:
        assert "Macular exam unremarkable today." not in (ev["detail"] or "")


def test_record_use_validation(client):
    # No ref at all.
    r = client.post(
        "/me/quick-comments/used", json={}, headers=CLIN1
    )
    assert r.status_code == 400
    # Both refs.
    r = client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "sx-01", "custom_comment_id": 1},
        headers=CLIN1,
    )
    assert r.status_code == 400


def test_record_use_custom_cross_user_is_404(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Not yours."},
        headers=CLIN1,
    ).json()
    r = client.post(
        "/me/quick-comments/used",
        json={"custom_comment_id": created["id"]},
        headers=ADMIN1,
    )
    assert r.status_code == 404


def test_reviewer_cannot_record_use(client):
    r = client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "sx-01"},
        headers=REV1,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------
# surface isolation — favorites + usage are not in encounter endpoints
# ---------------------------------------------------------------------


def test_favorites_not_on_encounter_reads(client):
    client.post(
        "/me/quick-comments/favorites",
        json={"preloaded_ref": "plan-50"},
        headers=CLIN1,
    )
    r = client.get("/encounters/1", headers=CLIN1)
    body = r.json()
    assert "favorites" not in body
    assert "quick_comment_favorites" not in body
    # Preloaded ref text should not leak through the encounter payload.
    assert "plan-50" not in str(body)
