"""Post-visit summary — generation + plain-language mapper + read-link.

Spec: docs/chartnav/closure/PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary.md

What this module does:
  - Renders a single-page, plain-text PDF summary from a signed
    note_versions row (the same minimal-PDF writer the consult-
    letter and handoff-export modules use; no WeasyPrint dep).
  - Generates a 30-day-expiry read-link token. Raw token is shown
    to staff exactly once; we store HMAC-SHA256(per-process salt,
    token) in the row.
  - Maps assessment text to plain-language English using a small
    deterministic substitution table — NO LLM call (spec §9).
  - Idempotent re-render: a second POST against the same signed
    note version returns the existing row.

Truth limitations (§9):
  - Not a HIPAA-conforming patient portal.
  - Token is possession-only; copy-paste forwarded link produces
    indistinguishable views.
  - Plain-language mapper is rule-based and intentionally minimal.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import fetch_one, insert_returning_id, transaction
from app.services.handoff_export import render_pdf_bytes
from app.services.intake import generate_token, hash_token


SUMMARY_TTL_DAYS = 30


# ---------- Plain-language substitution table -------------------------

# Conservative ophthalmology-leaning mapping. We do NOT change
# clinically loaded statements; we just substitute commonly opaque
# tokens with plain English. Spec §9: deterministic, no LLM.
_PLAIN_LANGUAGE_RULES: list[tuple[str, str]] = [
    (r"\bIOP\b", "eye pressure"),
    (r"\bOD\b", "right eye"),
    (r"\bOS\b", "left eye"),
    (r"\bOU\b", "both eyes"),
    (r"\bVA\b", "vision"),
    (r"\bq\.?d\.?\b", "once daily"),
    (r"\bb\.?i\.?d\.?\b", "twice daily"),
    (r"\bt\.?i\.?d\.?\b", "three times daily"),
    (r"\bq\.?i\.?d\.?\b", "four times daily"),
    (r"\bqhs\b", "at bedtime"),
    (r"\bp\.?o\.?\b", "by mouth"),
    (r"\bf/u\b", "follow up"),
    (r"\bRTC\b", "return to clinic"),
    # Slot intervals like "4/52" → "in 4 weeks"
    (r"\b(\d+)/52\b", r"in \1 weeks"),
    (r"\b(\d+)/12\b", r"in \1 months"),
]


def to_plain_language(text: str) -> str:
    if not text:
        return ""
    out = text
    for pat, repl in _PLAIN_LANGUAGE_RULES:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


# ---------- Renderer --------------------------------------------------

def _render_summary_body(
    *,
    encounter: dict,
    note_text: str,
    org_name: str,
    visit_date: str,
) -> str:
    plain = to_plain_language(note_text or "")
    lines: list[str] = []
    lines.append(f"{org_name} — Post-visit summary")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"For: {encounter.get('patient_name') or encounter.get('patient_identifier','')}")
    lines.append(f"Date of visit: {visit_date}")
    lines.append(f"Provider: {encounter.get('provider_name','')}")
    lines.append("")
    lines.append("--- Your visit ---")
    lines.append(plain or "(no narrative on file)")
    lines.append("")
    lines.append("--- Important ---")
    lines.append("This is a plain-English summary of your visit. It is")
    lines.append("not a HIPAA-conforming patient portal — please call our")
    lines.append("office for billing or scheduling questions.")
    lines.append("")
    lines.append("--- Contact us ---")
    lines.append("If you have an urgent eye problem, call our office or")
    lines.append("go to the nearest emergency department.")
    return "\n".join(lines)


# ---------- Generation -----------------------------------------------

class PostVisitSummaryError(Exception):
    def __init__(self, code: str, http_status: int):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def generate_for_note_version(
    *,
    note_version_id: int,
    organization_id: int,
) -> dict[str, Any]:
    """Render and persist the summary. Idempotent on note_version_id.

    Returns {id, read_link_token, expires_at}. The raw token is in
    the response exactly once; subsequent reads of the row only see
    the hash.
    """
    note = fetch_one(
        "SELECT nv.id, nv.encounter_id, nv.signed_at, nv.note_text, "
        "       e.organization_id, e.patient_identifier, e.patient_name, "
        "       e.provider_name, e.scheduled_at, e.completed_at "
        "FROM note_versions nv JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE nv.id = :id",
        {"id": note_version_id},
    )
    if not note or note["organization_id"] != organization_id:
        raise PostVisitSummaryError("note_version_not_found", 404)
    if not note.get("signed_at"):
        raise PostVisitSummaryError("note_not_signed", 422)

    existing = fetch_one(
        "SELECT id, organization_id, encounter_id, note_version_id, "
        "       expires_at, first_viewed_at, delivered_via, created_at "
        "FROM post_visit_summaries WHERE note_version_id = :nv",
        {"nv": note_version_id},
    )
    if existing:
        return {
            **dict(existing),
            "read_link_token": None,  # not regenerated
            "_idempotent": True,
        }

    org_row = fetch_one(
        "SELECT name FROM organizations WHERE id = :id",
        {"id": organization_id},
    ) or {"name": "ChartNav"}
    visit_date = (
        str(note.get("completed_at") or note.get("scheduled_at") or "")[:10]
    )
    body = _render_summary_body(
        encounter=dict(note),
        note_text=note.get("note_text") or "",
        org_name=org_row.get("name") or "ChartNav",
        visit_date=visit_date,
    )
    pdf_bytes = render_pdf_bytes(body)

    raw_token = generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SUMMARY_TTL_DAYS)
    storage_ref = f"post-visit-summaries/{note_version_id}.pdf"

    with transaction() as conn:
        new_id = insert_returning_id(
            conn,
            "post_visit_summaries",
            {
                "organization_id": organization_id,
                "encounter_id": note["encounter_id"],
                "note_version_id": note_version_id,
                "rendered_pdf_storage_ref": storage_ref,
                "pdf_bytes": pdf_bytes,
                "read_link_token_hash": hash_token(raw_token),
                "expires_at": expires.isoformat(timespec="seconds"),
            },
        )
    return {
        "id": new_id,
        "encounter_id": note["encounter_id"],
        "note_version_id": note_version_id,
        "expires_at": expires.isoformat(timespec="seconds"),
        "read_link_token": raw_token,
        "_idempotent": False,
    }


def lookup_by_token(raw_token: str) -> dict[str, Any]:
    """Public-route lookup. Raises on unknown / expired."""
    if not isinstance(raw_token, str) or len(raw_token) < 16:
        raise PostVisitSummaryError("post_visit_summary_not_found", 404)
    h = hash_token(raw_token)
    row = fetch_one(
        "SELECT id, organization_id, encounter_id, note_version_id, "
        "       expires_at, pdf_bytes, first_viewed_at "
        "FROM post_visit_summaries WHERE read_link_token_hash = :h",
        {"h": h},
    )
    if not row:
        raise PostVisitSummaryError("post_visit_summary_not_found", 404)
    expires_at = row.get("expires_at")
    if isinstance(expires_at, str):
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            exp = None
    else:
        exp = expires_at
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise PostVisitSummaryError("post_visit_summary_expired", 410)
    return dict(row)


def stamp_first_view(summary_id: int) -> None:
    from sqlalchemy import text
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE post_visit_summaries "
                "SET first_viewed_at = COALESCE(first_viewed_at, CURRENT_TIMESTAMP) "
                "WHERE id = :id"
            ),
            {"id": summary_id},
        )
