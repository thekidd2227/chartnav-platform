"""Phase 2 item 1 — consult-letter generation contract.

Spec: docs/chartnav/closure/PHASE_B_Referring_Provider_Communication.md §4.

Covers:
  - happy-path PDF generation from a signed note;
  - cross-org access denied (404, never 403, so existence is not
    revealed);
  - 422 when the source note version is not signed;
  - idempotent re-render returns the same row;
  - delivery-channel branch (download produces a real PDF; email
    + fax_stub record intent without transmission);
  - PDF download endpoint enforces org scoping.
"""
from __future__ import annotations

from sqlalchemy import text

from .conftest import ADMIN1, CLIN1, REV1, ADMIN2

VALID_NPI_A = "1234567893"


def _create_encounter(client, headers=ADMIN1, patient_id="PT-CONSULT") -> int:
    r = client.post(
        "/encounters",
        json={
            "organization_id": 1,
            "location_id": 1,
            "patient_identifier": patient_id,
            "patient_name": "Consult Patient",
            "provider_name": "Dr. Carter",
            "template_key": "retina",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _make_signed_note(encounter_id: int, note_text: str = "Assessment: stable. Plan: follow up in 4 weeks.") -> int:
    """Insert a signed note_versions row directly so the consult-letter
    test does not have to drive the entire transcript→draft→sign
    pipeline. Returns the new note_version_id."""
    from app.db import transaction
    with transaction() as conn:
        next_ver_row = conn.execute(
            text(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS v "
                "FROM note_versions WHERE encounter_id = :enc"
            ),
            {"enc": encounter_id},
        ).mappings().first()
        next_ver = int(next_ver_row["v"])
        row = conn.execute(
            text(
                "INSERT INTO note_versions ("
                "  encounter_id, version_number, draft_status, "
                "  note_format, note_text, generated_by, "
                "  provider_review_required, missing_data_flags, "
                "  signed_at, signed_by_user_id) "
                "VALUES ("
                "  :enc, :ver, 'signed', 'soap', :text, 'manual', "
                "  0, '[]', CURRENT_TIMESTAMP, 1) "
                "RETURNING id"
            ),
            {"enc": encounter_id, "ver": next_ver, "text": note_text},
        ).mappings().first()
    return int(row["id"])


def _create_referring_provider(client, headers=ADMIN1, npi: str = VALID_NPI_A) -> int:
    r = client.post(
        "/referring-providers",
        json={"name": "Dr. Olive Optometrist", "npi_10": npi, "email": "olive@example.com"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# -------- happy path -------------------------------------------------

def test_consult_letter_happy_path(client):
    enc = _create_encounter(client)
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp, "delivery_channel": "download"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["delivery_status"] == "rendered"
    assert body["delivered_via"] == "download"
    # PDF download works.
    pdf = client.get(f"/consult-letters/{body['id']}/pdf", headers=CLIN1)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-1.4")
    assert pdf.content.rstrip().endswith(b"%%EOF")


# -------- 422 unsigned ------------------------------------------------

def test_consult_letter_unsigned_returns_422(client):
    enc = _create_encounter(client, patient_id="PT-UNSIGNED")
    # Insert an UNSIGNED note version (signed_at NULL).
    from app.db import transaction
    with transaction() as conn:
        next_ver_row = conn.execute(
            text(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS v "
                "FROM note_versions WHERE encounter_id = :enc"
            ),
            {"enc": enc},
        ).mappings().first()
        nv_ver = int(next_ver_row["v"])
        row = conn.execute(
            text(
                "INSERT INTO note_versions ("
                "  encounter_id, version_number, draft_status, "
                "  note_format, note_text, generated_by, "
                "  provider_review_required, missing_data_flags) "
                "VALUES (:enc, :ver, 'draft', 'soap', 'wip', 'manual', 1, '[]') "
                "RETURNING id"
            ),
            {"enc": enc, "ver": nv_ver},
        ).mappings().first()
    nv = int(row["id"])
    rp = _create_referring_provider(client)
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp},
        headers=CLIN1,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error_code"] == "note_not_signed"


# -------- cross-org 404 ----------------------------------------------

def test_consult_letter_cross_org_404(client):
    enc = _create_encounter(client)
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)  # org1 RP
    # Org-2 admin tries to render a letter against an org-1 note.
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp},
        headers=ADMIN2,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "note_version_not_found"


# -------- idempotent re-render ---------------------------------------

def test_consult_letter_re_render_is_idempotent(client):
    enc = _create_encounter(client, patient_id="PT-IDEMPOT")
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    first = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp},
        headers=CLIN1,
    )
    second = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp},
        headers=CLIN1,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json().get("_idempotent") is True


# -------- delivery channel: email records intent only ----------------

def test_consult_letter_email_channel_records_intent(client):
    enc = _create_encounter(client, patient_id="PT-EMAIL")
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp, "delivery_channel": "email"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["delivered_via"] == "email"
    assert body["delivery_status"] == "stub_logged"
    assert "intent only" in body["advisory"].lower()


def test_consult_letter_fax_stub_carries_truth_label(client):
    enc = _create_encounter(client, patient_id="PT-FAX")
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp, "delivery_channel": "fax_stub"},
        headers=CLIN1,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["delivered_via"] == "fax_stub"
    # Spec §9: UI must label this as "Fax queued (stub — no transmission in pilot)."
    assert "stub" in body["advisory"].lower()
    assert "no transmission" in body["advisory"].lower()


# -------- delivery channel validation --------------------------------

def test_consult_letter_invalid_channel_400(client):
    enc = _create_encounter(client, patient_id="PT-BADCH")
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    r = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp, "delivery_channel": "carrier_pigeon"},
        headers=CLIN1,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "invalid_delivery_channel"


# -------- PDF download org scoping ----------------------------------

def test_pdf_download_cross_org_404(client):
    enc = _create_encounter(client, patient_id="PT-PDFCROSS")
    nv = _make_signed_note(enc)
    rp = _create_referring_provider(client)
    created = client.post(
        f"/note-versions/{nv}/consult-letter",
        json={"referring_provider_id": rp},
        headers=CLIN1,
    ).json()
    r = client.get(f"/consult-letters/{created['id']}/pdf", headers=ADMIN2)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "consult_letter_not_found"


# -------- FHIR DocumentReference truth boundary ----------------------

def test_fhir_document_reference_skipped_in_standalone_mode():
    from app.services.consult_letters import post_document_reference
    out = post_document_reference(
        consult_letter={"id": 1},
        deployment_mode="standalone",
    )
    assert out["fhir_posted"] is False
    assert "intentionally skipped" in out["skipped_reason"]


def test_fhir_document_reference_phase_b_does_not_post_even_in_writethrough():
    """Spec §9: FHIR write is intentionally NOT wired in Phase B."""
    from app.services.consult_letters import post_document_reference
    out = post_document_reference(
        consult_letter={"id": 1},
        deployment_mode="integrated_writethrough",
    )
    assert out["fhir_posted"] is False
    assert "Phase B" in out["skipped_reason"]
    assert "Phase C" in out["skipped_reason"]
