"""Phase 2 item 5 — post-visit summary contract tests.

Spec: docs/chartnav/closure/PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary.md §4.

Covers:
  - happy-path generation from a signed note;
  - 422 when the source note is unsigned;
  - cross-org access via token returns 404 (never reveal existence);
  - token expiry → 410;
  - PHI hygiene: unauth endpoint never echoes the token in the
    error body;
  - idempotent re-generation;
  - PDF download org scoping.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from .conftest import ADMIN1, ADMIN2, CLIN1, REV1


# -------- helpers ---------------------------------------------------

def _create_encounter(client, headers=ADMIN1, patient_id="PT-PVS") -> int:
    r = client.post(
        "/encounters",
        json={
            "organization_id": 1 if headers in (ADMIN1, CLIN1, REV1) else 2,
            "location_id": 1 if headers in (ADMIN1, CLIN1, REV1) else 2,
            "patient_identifier": patient_id,
            "patient_name": "Summary Patient",
            "provider_name": "Dr. Summary",
            "template_key": "retina",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _make_signed_note(encounter_id: int, *, signed: bool = True, note_text="VA OD 20/40, IOP 16. Plan: f/u 4/52.") -> int:
    from app.db import transaction
    with transaction() as conn:
        nv_row = conn.execute(
            text(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS v "
                "FROM note_versions WHERE encounter_id = :e"
            ),
            {"e": encounter_id},
        ).mappings().first()
        v = int(nv_row["v"])
        signed_at = "CURRENT_TIMESTAMP" if signed else "NULL"
        sql = (
            "INSERT INTO note_versions (encounter_id, version_number, "
            "  draft_status, note_format, note_text, generated_by, "
            "  provider_review_required, missing_data_flags, "
            f"  signed_at, signed_by_user_id) "
            f"VALUES (:e, :v, 'signed', 'soap', :t, 'manual', 0, '[]', "
            f"  {signed_at}, :uid) RETURNING id"
        )
        row = conn.execute(text(sql), {"e": encounter_id, "v": v, "t": note_text, "uid": 1 if signed else None}).mappings().first()
    return int(row["id"])


# -------- pure-function plain language mapper ----------------------

def test_plain_language_maps_common_ophthalmology_tokens():
    from app.services.post_visit_summary import to_plain_language
    out = to_plain_language("IOP OD 16, OS 18. Plan: f/u 4/52, RTC.")
    low = out.lower()
    assert "eye pressure" in low
    assert "right eye" in low
    assert "left eye" in low
    assert "follow up" in low
    assert "in 4 weeks" in low
    assert "return to clinic" in low


# -------- happy path -----------------------------------------------

def test_generate_summary_happy_path(client):
    enc = _create_encounter(client)
    nv = _make_signed_note(enc)
    r = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["note_version_id"] == nv
    # The raw token is shown in the response exactly once.
    assert isinstance(body["read_link_token"], str)
    assert len(body["read_link_token"]) >= 32
    # Authed PDF download works for the org.
    pdf = client.get(f"/post-visit-summaries/{body['id']}/pdf", headers=CLIN1)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-1.4")
    # Public unauth view via the magic-link token.
    pub = client.get(f"/summary/{body['read_link_token']}")
    assert pub.status_code == 200
    assert pub.headers["content-type"] == "application/pdf"


# -------- 422 unsigned ---------------------------------------------

def test_unsigned_note_returns_422(client):
    enc = _create_encounter(client, patient_id="PT-PVS-UNS")
    nv = _make_signed_note(enc, signed=False)
    r = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1)
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "note_not_signed"


# -------- idempotent re-generation ---------------------------------

def test_regenerate_returns_existing_row(client):
    enc = _create_encounter(client, patient_id="PT-PVS-ID")
    nv = _make_signed_note(enc)
    a = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1).json()
    b = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1).json()
    assert a["id"] == b["id"]
    # Second call does NOT regenerate the token (it's already in the row hash).
    assert b.get("read_link_token") is None
    assert b.get("_idempotent") is True


# -------- cross-org -------------------------------------------------

def test_cross_org_note_returns_404(client):
    enc = _create_encounter(client)
    nv = _make_signed_note(enc)
    r = client.post(f"/note-versions/{nv}/post-visit-summary", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "note_version_not_found"


def test_cross_org_pdf_download_returns_404(client):
    enc = _create_encounter(client)
    nv = _make_signed_note(enc)
    summary = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1).json()
    r = client.get(f"/post-visit-summaries/{summary['id']}/pdf", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "post_visit_summary_not_found"


# -------- public token: unknown / expired / PHI hygiene ------------

def test_public_summary_unknown_token_returns_404_and_no_phi(client):
    r = client.get("/summary/totally-bogus-token-32-chars-of-garbage")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["error_code"] == "post_visit_summary_not_found"
    # Reason must NOT echo the bogus token text.
    assert "totally-bogus" not in detail["reason"].lower()


def test_public_summary_expired_token_returns_410(client):
    enc = _create_encounter(client, patient_id="PT-PVS-EXP")
    nv = _make_signed_note(enc)
    summary = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1).json()
    raw = summary["read_link_token"]
    # Force the expires_at into the past.
    from app.db import transaction
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    with transaction() as conn:
        conn.execute(
            text("UPDATE post_visit_summaries SET expires_at = :p WHERE id = :id"),
            {"p": past, "id": summary["id"]},
        )
    r = client.get(f"/summary/{raw}")
    assert r.status_code == 410
    assert r.json()["detail"]["error_code"] == "post_visit_summary_expired"


# -------- role gating -----------------------------------------------

def test_reviewer_cannot_generate_summary(client):
    enc = _create_encounter(client, patient_id="PT-PVS-REV")
    nv = _make_signed_note(enc)
    r = client.post(f"/note-versions/{nv}/post-visit-summary", headers=REV1)
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_cannot_generate_summary"


# -------- first-view stamp ------------------------------------------

def test_first_view_is_stamped_on_public_get(client):
    enc = _create_encounter(client, patient_id="PT-PVS-FIRST")
    nv = _make_signed_note(enc)
    summary = client.post(f"/note-versions/{nv}/post-visit-summary", headers=CLIN1).json()
    # Before any view: no first_viewed_at.
    from app.db import fetch_one
    pre = fetch_one("SELECT first_viewed_at FROM post_visit_summaries WHERE id = :id", {"id": summary["id"]})
    assert pre.get("first_viewed_at") is None
    client.get(f"/summary/{summary['read_link_token']}")
    post = fetch_one("SELECT first_viewed_at FROM post_visit_summaries WHERE id = :id", {"id": summary["id"]})
    assert post.get("first_viewed_at") is not None
