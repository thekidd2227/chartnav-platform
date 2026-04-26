"""Phase A item 4 — PM/RCM continuity handoff export.

Spec: docs/chartnav/closure/PHASE_A_PM_RCM_Continuity_and_Integration_Path.md

This module produces the canonical encounter handoff payload (JSON +
CSV summary) and a textual rendering of the signed note (used as the
PDF body). The payload schema is the v1.0 contract defined in §5.1
of the spec.

Truth limitations preserved verbatim from the spec:
- NO PM/RCM integration ships in Phase A. Nothing in the pilot sends
  a claim. This is a manual export bundle the biller imports by hand.
- CPT codes are provider-entered, not auto-generated. There is no
  E/M level scoring engine.
- The canonical payload is designed to map cleanly to NextGen and
  AdvancedMD, but no vendor-certification work has been done.
  "Integration-ready" is not the same as "integrated."
- HIPAA 5010 compliance of the eventual X12 output depends on Phase B
  work with a clearinghouse partner.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_one, transaction


SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------
def build_handoff_payload(encounter_id: int) -> dict:
    """Build the canonical handoff payload for a signed encounter.

    Raises ValueError if the encounter is not signed yet (no
    encounter_attestations row exists). The route layer translates
    that into HTTP 409.
    """
    encounter = fetch_one(
        "SELECT id, organization_id, location_id, patient_identifier, "
        "patient_name, provider_name, status, scheduled_at, started_at, "
        "completed_at, created_at, template_key "
        "FROM encounters WHERE id = :id",
        {"id": encounter_id},
    )
    if not encounter:
        raise ValueError(f"encounter {encounter_id} not found")

    attestation = fetch_one(
        "SELECT id, attested_by_user_id, typed_name, attestation_text, "
        "encounter_snapshot_hash, attested_at "
        "FROM encounter_attestations WHERE encounter_id = :eid",
        {"eid": encounter_id},
    )
    if not attestation:
        raise ValueError(f"encounter {encounter_id} has no attestation; cannot export")

    org = fetch_one(
        "SELECT id, name FROM organizations WHERE id = :id",
        {"id": encounter["organization_id"]},
    ) or {}
    location = fetch_one(
        "SELECT id, name FROM locations WHERE id = :id",
        {"id": encounter["location_id"]},
    ) or {}

    # Pull the signed note for fingerprint + signed_at.
    signed_note = fetch_one(
        "SELECT id, version_number, signed_at, signed_by_user_id, "
        "content_fingerprint, attestation_text, note_text "
        "FROM note_versions "
        "WHERE encounter_id = :eid AND signed_at IS NOT NULL "
        "ORDER BY signed_at DESC, id DESC LIMIT 1",
        {"eid": encounter_id},
    ) or {}

    # Provider row, for NPI + display name. Falls back to encounter's
    # denormalized provider_name when no provider_id is set.
    provider_row = None
    if encounter.get("provider_id"):
        provider_row = fetch_one(
            "SELECT id, display_name, npi FROM providers WHERE id = :id",
            {"id": encounter["provider_id"]},
        )
    provider_name = (
        (provider_row or {}).get("display_name")
        or encounter.get("provider_name")
        or "Unassigned"
    )
    provider_npi = (provider_row or {}).get("npi") or ""

    template = (encounter.get("template_key") or "general_ophthalmology")

    payload: dict = {
        "schema_version": SCHEMA_VERSION,
        "encounter_id": str(encounter["id"]),
        "encounter_date": _date_part(
            encounter.get("scheduled_at") or encounter.get("created_at")
        ),
        "org": {
            "id": f"org_{org.get('id', '')}",
            "name": org.get("name", "") or "",
            "npi_group": "",
            "tax_id_last4": "",
        },
        "provider": {
            "user_id": f"usr_{(provider_row or {}).get('id', '')}",
            "full_name": provider_name,
            "npi_individual": provider_npi,
            "taxonomy_code": "207W00000X",  # Ophthalmology taxonomy
        },
        "patient": {
            "mrn": encounter.get("patient_identifier") or "",
            "display_name": encounter.get("patient_name") or "",
            "dob": "",
            "sex_at_birth": "",
            "insurance_id_last4": "",
        },
        "visit": {
            "chief_complaint": "",  # provider-entered; not auto-extracted
            "template_key": template,
            "place_of_service": str(location.get("id") or "11"),
            "location_name": location.get("name", "") or "",
        },
        "codes": {
            "cpt": [],     # provider-entered in v1
            "icd10": [],   # provider-entered in v1
        },
        "note": {
            "pdf_url": "",  # caller supplies a signed download URL
            "signed_at": (
                str(signed_note.get("signed_at"))
                if signed_note.get("signed_at")
                else None
            ),
            "attestation_hash": attestation["encounter_snapshot_hash"],
            "content_fingerprint": signed_note.get("content_fingerprint") or "",
        },
        "_truth": {
            "advisory_only": True,
            "no_pm_rcm_integration": True,
            "codes_provider_entered": True,
            "schema_version": SCHEMA_VERSION,
        },
    }
    return payload


# ---------------------------------------------------------------------
# CSV emitter (single-row superbill format)
# ---------------------------------------------------------------------
CSV_FIELDS = [
    "schema_version",
    "encounter_id",
    "encounter_date",
    "org_name",
    "org_npi_group",
    "provider_full_name",
    "provider_npi_individual",
    "patient_mrn",
    "patient_display_name",
    "visit_chief_complaint",
    "visit_template_key",
    "place_of_service",
    "cpt_codes",
    "icd10_codes",
    "signed_at",
    "attestation_hash",
    "content_fingerprint",
]


def render_csv(payload: dict) -> str:
    """Render the canonical payload as a single-row superbill CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow({
        "schema_version": payload.get("schema_version", ""),
        "encounter_id": payload.get("encounter_id", ""),
        "encounter_date": payload.get("encounter_date", ""),
        "org_name": payload.get("org", {}).get("name", ""),
        "org_npi_group": payload.get("org", {}).get("npi_group", ""),
        "provider_full_name": payload.get("provider", {}).get("full_name", ""),
        "provider_npi_individual": payload.get("provider", {}).get("npi_individual", ""),
        "patient_mrn": payload.get("patient", {}).get("mrn", ""),
        "patient_display_name": payload.get("patient", {}).get("display_name", ""),
        "visit_chief_complaint": payload.get("visit", {}).get("chief_complaint", ""),
        "visit_template_key": payload.get("visit", {}).get("template_key", ""),
        "place_of_service": payload.get("visit", {}).get("place_of_service", ""),
        "cpt_codes": ";".join(
            f"{c.get('code', '')}"
            + (":" + ",".join(c.get("modifiers", [])) if c.get("modifiers") else "")
            for c in payload.get("codes", {}).get("cpt", [])
        ),
        "icd10_codes": ";".join(
            c.get("code", "") for c in payload.get("codes", {}).get("icd10", [])
        ),
        "signed_at": payload.get("note", {}).get("signed_at") or "",
        "attestation_hash": payload.get("note", {}).get("attestation_hash", ""),
        "content_fingerprint": payload.get("note", {}).get("content_fingerprint", ""),
    })
    return buf.getvalue()


# ---------------------------------------------------------------------
# PDF body (text). The route layer wraps this in a minimal PDF.
# ---------------------------------------------------------------------
def render_pdf_body(payload: dict, note_text: str | None = None) -> str:
    """Plain-text body for the note PDF. Kept text-only so we don't
    pull a heavy PDF dependency into Phase A. The route layer wraps
    this in a minimal valid PDF; consumers needing rich layout pull
    the JSON instead and render in their own pipeline."""
    lines: list[str] = []
    lines.append("ChartNav — Signed Encounter Note (Phase A handoff bundle)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Encounter ID:        {payload.get('encounter_id', '')}")
    lines.append(f"Encounter date:      {payload.get('encounter_date', '')}")
    lines.append(f"Provider:            {payload['provider']['full_name']} "
                 f"(NPI {payload['provider']['npi_individual']})")
    lines.append(f"Organization:        {payload['org']['name']}")
    lines.append(f"Location of service: {payload['visit']['location_name']} "
                 f"(POS {payload['visit']['place_of_service']})")
    lines.append(f"Patient MRN:         {payload['patient']['mrn']}")
    lines.append(f"Patient name:        {payload['patient']['display_name']}")
    lines.append(f"Template:            {payload['visit']['template_key']}")
    lines.append("")
    lines.append("--- Note body --------------------------------------------")
    lines.append(note_text or "(note body not supplied)")
    lines.append("")
    lines.append("--- Attestation ------------------------------------------")
    lines.append(f"Signed at:        {payload['note'].get('signed_at') or ''}")
    lines.append(f"Snapshot hash:    {payload['note'].get('attestation_hash', '')}")
    lines.append(f"Content fingerprint: {payload['note'].get('content_fingerprint', '')}")
    lines.append("")
    lines.append("Truth statement: this is a manual handoff bundle. ChartNav")
    lines.append("does not transmit claims, does not generate CPT/ICD codes,")
    lines.append("and does not guarantee reimbursement.")
    return "\n".join(lines)


def render_pdf_bytes(text_body: str) -> bytes:
    """Wrap a plain-text body in a minimal single-page PDF. No external
    PDF library required. The output is parseable by any PDF reader.

    Choice rationale: the spec calls for a PDF deliverable; we honor
    that without taking on a heavy reportlab/weasyprint dependency in
    Phase A. The text content is the single source of truth — clinics
    that need styled output should render the JSON in their PM tool."""
    # Encode each line as a separate Tx instruction. PDF requires us
    # to escape (, ), and \ in the text strings.
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = text_body.splitlines()
    # Compose the content stream — Helvetica 9pt, top-down at 750.
    stream = ["BT", "/F1 9 Tf", "1 0 0 1 36 770 Tm", "11 TL"]
    first = True
    for ln in lines:
        if first:
            stream.append(f"({_esc(ln)}) Tj")
            first = False
        else:
            stream.append("T*")
            stream.append(f"({_esc(ln)}) Tj")
    stream.append("ET")
    content_stream = "\n".join(stream).encode("latin-1", "replace")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] "
        b"/Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>"
    )
    objects.append(
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\n"
        b"stream\n" + content_stream + b"\nendstream"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = b"%PDF-1.4\n"
    offsets: list[int] = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n"
    pdf += f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_offset}\n".encode()
    pdf += b"%%EOF\n"
    return pdf


# ---------------------------------------------------------------------
# Vendor mapping (Phase A: documented; Phase B: real adapters)
# ---------------------------------------------------------------------
def map_to_nextgen(payload: dict) -> dict:
    """Documented field-by-field mapping from the canonical payload to
    NextGen Practice Management's encounter+claim shape.

    Phase A only: this is a pure function with no network I/O. The
    output is the shape a NextGen integration would POST when one is
    built in Phase B / C.
    """
    return {
        "EncounterID": payload["encounter_id"],
        "EncounterDate": payload["encounter_date"],
        "PracticeName": payload["org"]["name"],
        "PracticeNPI": payload["org"]["npi_group"],
        "RenderingProvider": {
            "FullName": payload["provider"]["full_name"],
            "NPI": payload["provider"]["npi_individual"],
        },
        "PatientMRN": payload["patient"]["mrn"],
        "PatientName": payload["patient"]["display_name"],
        "PlaceOfService": payload["visit"]["place_of_service"],
        "ServiceLines": [
            {
                "CPT": c.get("code"),
                "Modifiers": c.get("modifiers", []),
                "Units": c.get("units", 1),
            }
            for c in payload["codes"]["cpt"]
        ],
        "Diagnoses": [
            {"ICD10": c.get("code"), "Rank": c.get("rank")}
            for c in payload["codes"]["icd10"]
        ],
        "Attestation": {
            "SignedAt": payload["note"].get("signed_at"),
            "Hash": payload["note"].get("attestation_hash"),
        },
        "_advisory_only": True,
    }


def map_to_advancedmd(payload: dict) -> dict:
    """Documented field-by-field mapping to AdvancedMD's encounter
    shape. Same Phase-A advisory-only semantics as map_to_nextgen."""
    return {
        "encounter_external_id": payload["encounter_id"],
        "service_date": payload["encounter_date"],
        "practice": {
            "name": payload["org"]["name"],
            "npi": payload["org"]["npi_group"],
        },
        "rendering_provider": {
            "name": payload["provider"]["full_name"],
            "npi": payload["provider"]["npi_individual"],
        },
        "patient": {
            "chart_number": payload["patient"]["mrn"],
            "name": payload["patient"]["display_name"],
        },
        "place_of_service": payload["visit"]["place_of_service"],
        "procedures": [
            {
                "cpt": c.get("code"),
                "modifiers": c.get("modifiers", []),
                "units": c.get("units", 1),
            }
            for c in payload["codes"]["cpt"]
        ],
        "diagnoses": [c.get("code") for c in payload["codes"]["icd10"]],
        "attestation": {
            "signed_at": payload["note"].get("signed_at"),
            "snapshot_hash": payload["note"].get("attestation_hash"),
        },
        "_advisory_only": True,
    }


# ---------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------
def _date_part(value: Any) -> str:
    """Return YYYY-MM-DD from a datetime or ISO string. Empty when
    the input is None."""
    if not value:
        return ""
    s = str(value)
    return s[:10]


def get_signed_note_text(encounter_id: int) -> Optional[str]:
    """Return the body of the most-recent signed note, or None."""
    row = fetch_one(
        "SELECT note_text FROM note_versions "
        "WHERE encounter_id = :eid AND signed_at IS NOT NULL "
        "ORDER BY signed_at DESC, id DESC LIMIT 1",
        {"eid": encounter_id},
    )
    return row["note_text"] if row else None
