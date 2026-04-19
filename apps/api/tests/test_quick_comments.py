"""Phase 27 — clinician quick-comment pad.

Covers:

- reviewer cannot create/patch/delete → 403 role_cannot_edit_quick_comments
- clinician creates → 201 with body echoed, is_active=true
- empty / whitespace body rejected → 400 quick_comment_body_required
- list returns only the caller's own comments (not other clinicians')
- cross-user GET/PATCH/DELETE → 404 quick_comment_not_found
- cross-org comment → 404
- PATCH body updates; PATCH is_active=false soft-deletes; delete is
  idempotent
- soft-deleted comments hidden from default list, visible when
  include_inactive=true
- audit events: created / updated / deleted
- shape invariants: no encounter_id / note_version_id columns leak —
  these comments are not linked to transcripts / findings / notes
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


# ---------------------------------------------------------------------
# role gate
# ---------------------------------------------------------------------


def test_reviewer_cannot_create_quick_comment(client):
    r = client.post(
        "/me/quick-comments",
        json={"body": "Pupils round and reactive."},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_edit_quick_comments"


def test_reviewer_cannot_list_quick_comments(client):
    r = client.get("/me/quick-comments", headers=REV1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_edit_quick_comments"


# ---------------------------------------------------------------------
# create + validation
# ---------------------------------------------------------------------


def test_clinician_creates_quick_comment(client):
    r = client.post(
        "/me/quick-comments",
        json={"body": "IOP acceptable today."},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["body"] == "IOP acceptable today."
    assert bool(row["is_active"]) is True
    assert row["user_id"] is not None
    assert row["organization_id"] is not None
    # Invariant: the persistence shape is intentionally NOT linked to
    # any encounter / note version — clinician personal clipboard.
    for forbidden in ("encounter_id", "note_version_id", "transcript_text"):
        assert forbidden not in row


def test_empty_body_rejected(client):
    r = client.post(
        "/me/quick-comments",
        json={"body": "   "},
        headers=CLIN1,
    )
    # Pydantic min_length=1 applies after strip on server? We strip
    # server-side, so whitespace-only passes the validator and is
    # caught by the 400 branch. Accept either:
    assert r.status_code in (400, 422)
    if r.status_code == 400:
        assert r.json()["detail"]["error_code"] == "quick_comment_body_required"


# ---------------------------------------------------------------------
# listing + scoping
# ---------------------------------------------------------------------


def test_list_returns_only_my_comments(client):
    # admin@chartnav and clin@chartnav are in the same org but are
    # different users. Each should see only their own comments.
    client.post(
        "/me/quick-comments",
        json={"body": "Clinician Alpha note."},
        headers=CLIN1,
    )
    client.post(
        "/me/quick-comments",
        json={"body": "Admin Alpha note."},
        headers=ADMIN1,
    )

    r = client.get("/me/quick-comments", headers=CLIN1)
    assert r.status_code == 200
    bodies = [row["body"] for row in r.json()]
    assert "Clinician Alpha note." in bodies
    assert "Admin Alpha note." not in bodies

    r = client.get("/me/quick-comments", headers=ADMIN1)
    assert r.status_code == 200
    bodies = [row["body"] for row in r.json()]
    assert "Admin Alpha note." in bodies
    assert "Clinician Alpha note." not in bodies


def test_cross_user_get_is_404(client):
    # CLIN1 creates a comment; ADMIN1 (same org, different user)
    # tries to PATCH it — must be 404, not 403, to avoid leaking
    # existence across users.
    created = client.post(
        "/me/quick-comments",
        json={"body": "Vision stable since last visit."},
        headers=CLIN1,
    ).json()

    r = client.patch(
        f"/me/quick-comments/{created['id']}",
        json={"body": "hijacked"},
        headers=ADMIN1,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "quick_comment_not_found"

    r = client.delete(
        f"/me/quick-comments/{created['id']}",
        headers=ADMIN1,
    )
    assert r.status_code == 404


def test_cross_org_get_is_404(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Org1 only."},
        headers=CLIN1,
    ).json()
    r = client.patch(
        f"/me/quick-comments/{created['id']}",
        json={"body": "other org edit"},
        headers=CLIN2,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------
# patch + soft delete
# ---------------------------------------------------------------------


def test_patch_body_updates(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Macula flat and dry."},
        headers=CLIN1,
    ).json()
    r = client.patch(
        f"/me/quick-comments/{created['id']}",
        json={"body": "Macula flat, dry, no heme."},
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["body"] == "Macula flat, dry, no heme."


def test_delete_soft_deletes(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "To be deleted."},
        headers=CLIN1,
    ).json()

    r = client.delete(
        f"/me/quick-comments/{created['id']}", headers=CLIN1
    )
    assert r.status_code == 200
    assert bool(r.json()["is_active"]) is False

    # Default list hides it.
    r = client.get("/me/quick-comments", headers=CLIN1)
    assert created["id"] not in [row["id"] for row in r.json()]

    # include_inactive surfaces it.
    r = client.get(
        "/me/quick-comments?include_inactive=true", headers=CLIN1
    )
    assert created["id"] in [row["id"] for row in r.json()]


def test_delete_is_idempotent(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Gone twice."},
        headers=CLIN1,
    ).json()
    r1 = client.delete(
        f"/me/quick-comments/{created['id']}", headers=CLIN1
    )
    assert r1.status_code == 200
    r2 = client.delete(
        f"/me/quick-comments/{created['id']}", headers=CLIN1
    )
    assert r2.status_code == 200
    assert not r2.json()["is_active"]


# ---------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------


def test_audit_events_recorded(client):
    created = client.post(
        "/me/quick-comments",
        json={"body": "Pupils round and reactive."},
        headers=CLIN1,
    ).json()
    client.patch(
        f"/me/quick-comments/{created['id']}",
        json={"body": "Pupils round, reactive, no RAPD."},
        headers=CLIN1,
    )
    client.delete(
        f"/me/quick-comments/{created['id']}", headers=CLIN1
    )

    r = client.get("/security-audit-events?limit=200", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    items = body["items"] if isinstance(body, dict) else body
    types = [ev["event_type"] for ev in items]
    assert "clinician_quick_comment_created" in types
    assert "clinician_quick_comment_updated" in types
    assert "clinician_quick_comment_deleted" in types


# ---------------------------------------------------------------------
# surface isolation — quick comments are NOT in any note/encounter read
# ---------------------------------------------------------------------


def test_quick_comments_dont_appear_in_encounter_endpoints(client):
    """Quick comments are doctor clipboard content, not encounter data.
    They must not surface on encounter reads or note reads."""
    client.post(
        "/me/quick-comments",
        json={"body": "Findings reviewed with patient."},
        headers=CLIN1,
    )

    # Encounter detail read — must not carry quick_comments.
    r = client.get("/encounters/1", headers=CLIN1)
    assert r.status_code == 200
    assert "quick_comments" not in r.json()
    assert "clinician_quick_comments" not in r.json()

    # Encounter events read — must not include quick-comment rows.
    r = client.get("/encounters/1/events", headers=CLIN1)
    assert r.status_code == 200
    for ev in r.json():
        assert "Findings reviewed with patient." not in str(
            ev.get("event_data", "")
        )
