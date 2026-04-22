"""Signed-note artifact builder (phase 25).

The **artifact** is ChartNav's canonical export shape for a signed
clinical note. It is not a write-back to any EHR and is not a
SMART-on-FHIR transaction — it is a **self-contained, inspectable,
provenance-bearing document package** that downstream systems
(humans, EHRs, audit reviewers) can consume in three shapes:

- ``chartnav.v1.json`` — canonical JSON, the source of truth for
  every other variant. Separates transcript → findings → generated
  draft → clinician-final in the payload itself so a reviewer can
  always see what the AI produced vs. what the human committed to.
- ``chartnav.v1.text`` — plain-text body with a metadata header
  block. The thing a clinician would paste into an EHR freeform
  note field today.
- ``fhir.DocumentReference.v1`` — minimal FHIR R4 DocumentReference
  resource with the clinician-final text inlined as a base64-encoded
  ``content.attachment``. This is the **packaging format**, not a
  transport: ChartNav does not currently POST this to any vendor
  FHIR endpoint. The point is that the shape is already correct the
  day someone does.

Integrity:
Every artifact carries a ``signature.content_hash_sha256`` computed
deterministically over ``<version_number>|<note_format>|<clinician_final>``
so consumers can verify the note body was not altered in transit.

This module is pure; it reads from SQLAlchemy rows and returns
JSON-serializable dicts. All DB access goes through ``fetch_one`` /
``fetch_all`` helpers exported by ``app.db`` — keep this file out of
the request handler path so tests can exercise it directly.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db import engine, fetch_one


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARTIFACT_VERSION = 1
ARTIFACT_TYPE = "chartnav.signed_note.v1"
JSON_MIME = "application/vnd.chartnav.signed-note+json"
TEXT_MIME = "text/plain; charset=utf-8"
FHIR_MIME = "application/fhir+json"

FORMAT_ALIASES = {
    "json": "chartnav.v1.json",
    "chartnav": "chartnav.v1.json",
    "chartnav.v1.json": "chartnav.v1.json",
    "text": "chartnav.v1.text",
    "txt": "chartnav.v1.text",
    "chartnav.v1.text": "chartnav.v1.text",
    "fhir": "fhir.DocumentReference.v1",
    "fhir.DocumentReference.v1": "fhir.DocumentReference.v1",
}

SUPPORTED_FORMATS = (
    "chartnav.v1.json",
    "chartnav.v1.text",
    "fhir.DocumentReference.v1",
)

# LOINC 34109-9 is "Note" broadly; 11506-3 is "Progress note".
# We use 11506-3 as the canonical type today because ChartNav notes
# cover the progress-note slot in a clinic workflow. Ophthalmology
# sub-specialty typing can layer on later via an additional coding.
LOINC_PROGRESS_NOTE = {
    "system": "http://loinc.org",
    "code": "11506-3",
    "display": "Progress note",
}

TRANSCRIPT_EXCERPT_MAX = 800  # chars — enough to give reviewers context


# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------

class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be built for a valid reason.

    The handler maps these to HTTP envelopes. ``error_code`` is the
    stable code clients key off of; ``status_code`` is the HTTP.
    """

    def __init__(self, error_code: str, reason: str, status_code: int):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def content_hash(
    *, version_number: int, note_format: str, clinician_final: str
) -> str:
    """Deterministic SHA-256 over the triad that uniquely identifies
    the body of a signed note. Not a signature (we do not own a
    signing key today); it is a tamper-evidence check for downstream
    consumers to notice if the body was altered after export."""
    payload = f"{version_number}|{note_format}|{clinician_final or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Row loading
# ---------------------------------------------------------------------------

def _excerpt(t: str | None, *, limit: int = TRANSCRIPT_EXCERPT_MAX) -> tuple[str, bool]:
    if not t:
        return "", False
    if len(t) <= limit:
        return t, False
    return t[:limit] + "…", True


def _load_note_bundle(note_id: int) -> dict[str, Any]:
    """Pull the note, its encounter, the source input (if any), and
    the extracted findings (if any) in one go so the artifact builder
    has everything it needs without the handler doing extra queries."""
    # Phase 54 — pull every lifecycle/evidence column the artifact
    # must reason about in ONE query: Wave 3 attestation +
    # fingerprint + amendment/supersession fields, Wave 7 final
    # approval fields. Prior versions of this query selected a
    # narrower column set, which meant the artifact silently dropped
    # approval + supersession evidence.
    note = fetch_one(
        "SELECT id, encounter_id, version_number, draft_status, "
        "note_format, note_text, generated_note_text, source_input_id, "
        "extracted_findings_id, generated_by, missing_data_flags, "
        "signed_at, signed_by_user_id, exported_at, created_at, updated_at, "
        "attestation_text, content_fingerprint, "
        "reviewed_at, reviewed_by_user_id, "
        "amended_at, amended_by_user_id, amended_from_note_id, "
        "amendment_reason, superseded_at, superseded_by_note_id, "
        "final_approval_status, final_approved_at, "
        "final_approved_by_user_id, final_approval_signature_text, "
        "final_approval_invalidated_at, final_approval_invalidated_reason "
        "FROM note_versions WHERE id = :id",
        {"id": note_id},
    )
    if note is None:
        raise ArtifactError("note_not_found", "no such note version", 404)
    note = dict(note)

    encounter = fetch_one(
        "SELECT id, organization_id, status, patient_identifier, "
        "patient_name, provider_name, external_ref, external_source, "
        "created_at "
        "FROM encounters WHERE id = :id",
        {"id": note["encounter_id"]},
    )
    if encounter is None:
        # Shouldn't happen with FK, but guard cleanly.
        raise ArtifactError(
            "encounter_not_found",
            "note has no owning encounter",
            500,
        )
    encounter = dict(encounter)

    source_input = None
    if note.get("source_input_id"):
        row = fetch_one(
            "SELECT id, input_type, processing_status, transcript_text, "
            "confidence_summary, source_metadata, created_at "
            "FROM encounter_inputs WHERE id = :id",
            {"id": note["source_input_id"]},
        )
        if row is not None:
            source_input = dict(row)

    findings = None
    if note.get("extracted_findings_id"):
        row = fetch_one(
            "SELECT id, chief_complaint, hpi_summary, "
            "visual_acuity_od, visual_acuity_os, iop_od, iop_os, "
            "structured_json, extraction_confidence, created_at "
            "FROM extracted_findings WHERE id = :id",
            {"id": note["extracted_findings_id"]},
        )
        if row is not None:
            findings = dict(row)

    signer = None
    if note.get("signed_by_user_id"):
        row = fetch_one(
            "SELECT id, email, role FROM users WHERE id = :id",
            {"id": note["signed_by_user_id"]},
        )
        if row is not None:
            signer = dict(row)

    return {
        "note": note,
        "encounter": encounter,
        "source_input": source_input,
        "findings": findings,
        "signer": signer,
    }


def _platform_context() -> dict[str, Any]:
    """Platform-mode context from the process-level config.

    Phase 16 keeps platform mode + adapter in env-backed ``settings``
    (not DB rows), so this is a straight read. Wrapped in try/except
    so a config-less test harness still returns a renderable artifact.
    """
    try:
        from app.config import settings
        from app.integrations import resolve_adapter

        mode = settings.platform_mode
        try:
            adapter = resolve_adapter()
            adapter_display = adapter.display_name
        except Exception:
            adapter_display = settings.integration_adapter
    except Exception:
        mode = "standalone"
        adapter_display = None
    return {
        "platform_mode": mode or "standalone",
        "adapter_display_name": adapter_display,
    }


# ---------------------------------------------------------------------------
# Canonical JSON artifact
# ---------------------------------------------------------------------------

def _parse_json_field(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def _iso(dt: Any) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        # Normalize to ISO 8601 UTC. Tests assert on prefix only.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt)


def build_artifact(
    *,
    note_id: int,
    caller_email: str | None,
    caller_user_id: int | None,
    caller_organization_id: int | None,
    require_signed: bool = True,
) -> dict[str, Any]:
    """Assemble the canonical JSON artifact.

    Enforces org scoping + signed-only gating so the handler stays a
    thin wrapper. Format conversion (text / FHIR) builds on top of
    the dict this returns — canonical JSON is the single source of
    truth for every variant.
    """
    bundle = _load_note_bundle(note_id)
    note = bundle["note"]
    encounter = bundle["encounter"]

    # Org scoping: artifact is a read of the note, same rules as the
    # note GET — cross-org → 404.
    if caller_organization_id is None or encounter["organization_id"] != caller_organization_id:
        raise ArtifactError("note_not_found", "no such note version", 404)

    # Phase 54 — canonical "is this record of care" gate.
    # Reuses the lifecycle service rather than inlining a set.
    # An amended row is itself a signed record of care (the amendment
    # service stamps it signed), so it must be artifactable. Legacy
    # code rejected `amended` which meant the new record of care
    # could not produce an artifact — that was a drift site.
    from app.services.note_lifecycle import LIFECYCLE_STATES
    SIGNED_LIKE = {"signed", "exported", "amended"}
    assert SIGNED_LIKE.issubset(LIFECYCLE_STATES), (
        "artifact gate must reference canonical lifecycle states"
    )
    if require_signed and note["draft_status"] not in SIGNED_LIKE:
        # An unsigned artifact is meaningless — the clinician has not
        # attested. Refuse rather than emit a confusing half-artifact.
        raise ArtifactError(
            "note_not_signed",
            "only signed, amended, or exported notes can produce an export artifact",
            409,
        )

    clinician_final = note["note_text"] or ""
    generated_draft = note.get("generated_note_text") or clinician_final
    edit_applied = generated_draft != clinician_final

    missing_flags = _parse_json_field(note.get("missing_data_flags"), [])
    structured = _parse_json_field(
        (bundle["findings"] or {}).get("structured_json"), {}
    )

    platform = _platform_context()
    source_input = bundle["source_input"]
    excerpt, truncated = ("", False)
    if source_input:
        excerpt, truncated = _excerpt(source_input.get("transcript_text"))

    findings = bundle["findings"] or {}
    signer = bundle["signer"] or {}

    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "chartnav": {
            "platform_mode": platform["platform_mode"],
            "adapter_display_name": platform["adapter_display_name"],
            "organization_id": encounter["organization_id"],
        },
        "encounter": {
            "id": encounter["id"],
            "status": encounter.get("status"),
            "patient_display": (
                encounter.get("patient_name")
                or encounter.get("patient_identifier")
                or None
            ),
            "provider_display": encounter.get("provider_name"),
            "source": (
                "fhir"
                if (encounter.get("external_source") or "").lower() == "fhir"
                else "chartnav_native"
            ),
            "external_ref": encounter.get("external_ref"),
        },
        "transcript_source": (
            None
            if source_input is None
            else {
                "input_id": source_input["id"],
                "input_type": source_input.get("input_type"),
                "processing_status": source_input.get("processing_status"),
                "confidence_summary": source_input.get("confidence_summary"),
                "transcript_excerpt": excerpt,
                "transcript_truncated": truncated,
                "transcript_chars": len(source_input.get("transcript_text") or ""),
            }
        ),
        "extracted_findings": (
            None
            if not findings
            else {
                "chief_complaint": findings.get("chief_complaint"),
                "hpi_summary": findings.get("hpi_summary"),
                "visual_acuity": {
                    "od": findings.get("visual_acuity_od"),
                    "os": findings.get("visual_acuity_os"),
                },
                "iop": {
                    "od": findings.get("iop_od"),
                    "os": findings.get("iop_os"),
                },
                "structured": structured,
                "extraction_confidence": findings.get("extraction_confidence"),
            }
        ),
        "note": {
            "id": note["id"],
            "version_number": note["version_number"],
            "format": note["note_format"],
            "draft_status": note["draft_status"],
            "generated_by": note.get("generated_by"),
            "generated_draft": generated_draft,
            "clinician_final": clinician_final,
            "edit_applied": edit_applied,
        },
        "missing_data_flags": missing_flags,
        "signature": {
            "signed_at": _iso(note.get("signed_at")),
            "signed_by_email": signer.get("email") if signer else None,
            "signed_by_user_id": note.get("signed_by_user_id"),
            "attestation_text": note.get("attestation_text"),
            "content_hash_sha256": content_hash(
                version_number=note["version_number"],
                note_format=note["note_format"],
                clinician_final=clinician_final,
            ),
            # Phase 54 — surface the Wave 3 frozen content fingerprint
            # alongside the live content hash. Different purposes:
            #   * content_hash_sha256 — canonical deterministic hash
            #     over (version, format, text) for downstream integrity.
            #   * content_fingerprint — the SHA-256 frozen at sign time
            #     over the normalized note body. Drift detection.
            "content_fingerprint_sha256": note.get("content_fingerprint"),
            "hash_inputs": "version_number|note_format|clinician_final",
        },
        # Phase 54 — final physician approval evidence. NULL on
        # pre-Wave-7 rows; `pending`/`approved`/`invalidated` for rows
        # that entered the Wave 7 flow. Downstream systems that consume
        # the artifact (EHR, audit, reviewers) read THIS block, not
        # `note.draft_status`, to determine whether the record has
        # been physician-approved.
        "final_approval": {
            "status": note.get("final_approval_status"),
            "approved_at": _iso(note.get("final_approved_at")),
            "approved_by_user_id": note.get("final_approved_by_user_id"),
            "signature_text": note.get("final_approval_signature_text"),
            "invalidated_at": _iso(note.get("final_approval_invalidated_at")),
            "invalidated_reason": note.get("final_approval_invalidated_reason"),
        },
        # Phase 54 — supersession / amendment evidence. The fields
        # collectively describe where this row sits in the record-
        # of-care chain. Consumers that need the full chain should
        # call GET /note-versions/{id}/amendment-chain; this block
        # carries the immediate links so point-in-time artifacts
        # remain evidentiary on their own.
        "lifecycle": {
            "state": note["draft_status"],
            "reviewed_at": _iso(note.get("reviewed_at")),
            "reviewed_by_user_id": note.get("reviewed_by_user_id"),
            "amended_at": _iso(note.get("amended_at")),
            "amended_by_user_id": note.get("amended_by_user_id"),
            "amended_from_note_id": note.get("amended_from_note_id"),
            "amendment_reason": note.get("amendment_reason"),
            "superseded_at": _iso(note.get("superseded_at")),
            "superseded_by_note_id": note.get("superseded_by_note_id"),
            "is_current_record_of_care": note.get("superseded_at") is None,
        },
        "export_envelope": {
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "issued_by_email": caller_email,
            "issued_by_user_id": caller_user_id,
            "format_variant": "chartnav.v1.json",
            "mime_type": JSON_MIME,
        },
    }
    return artifact


# ---------------------------------------------------------------------------
# Plain-text variant
# ---------------------------------------------------------------------------

def render_text(artifact: dict[str, Any]) -> str:
    """Clinician-ready text block: metadata header + note body + audit
    footer. Deliberately plain text with no markup — the target is a
    freeform EHR note field or a paste into a PDF template.
    """
    n = artifact["note"]
    sig = artifact["signature"]
    env = artifact["export_envelope"]
    enc = artifact["encounter"]
    missing = artifact.get("missing_data_flags") or []
    missing_line = ", ".join(missing) if missing else "none"

    # Phase 54 — include final-approval + supersession lines in the
    # text artifact so the plain-text variant is evidentiarily
    # equivalent to the JSON and FHIR variants.
    final_approval = artifact.get("final_approval") or {}
    lifecycle = artifact.get("lifecycle") or {}

    fa_status = final_approval.get("status")
    if fa_status == "approved":
        fa_line = (
            f"Final physician approval: approved at "
            f"{final_approval.get('approved_at') or '<unknown>'} "
            f"(user #{final_approval.get('approved_by_user_id') or '—'})\n"
        )
    elif fa_status == "pending":
        fa_line = "Final physician approval: PENDING\n"
    elif fa_status == "invalidated":
        fa_line = (
            f"Final physician approval: INVALIDATED at "
            f"{final_approval.get('invalidated_at') or '<unknown>'} — "
            f"{final_approval.get('invalidated_reason') or 'no reason recorded'}\n"
        )
    else:
        # NULL on pre-Wave-7 rows — omit the line rather than invent one.
        fa_line = ""

    if lifecycle.get("superseded_at"):
        supersession_line = (
            f"Record-of-care status: SUPERSEDED by note_version "
            f"#{lifecycle.get('superseded_by_note_id')} at "
            f"{lifecycle.get('superseded_at')}\n"
        )
    elif lifecycle.get("amended_from_note_id"):
        supersession_line = (
            f"Record-of-care status: amendment of note_version "
            f"#{lifecycle.get('amended_from_note_id')}\n"
        )
    else:
        supersession_line = ""

    header = (
        f"ChartNav Signed Note (v{n['version_number']}, {n['format']})\n"
        f"Patient: {enc.get('patient_display') or '<unknown>'}\n"
        f"Provider: {enc.get('provider_display') or '<unknown>'}\n"
        f"Encounter: {enc['id']} "
        f"({enc.get('source')}"
        + (f"; external_ref={enc['external_ref']}" if enc.get('external_ref') else "")
        + ")\n"
        f"Signed at: {sig.get('signed_at') or '<unsigned>'}\n"
        f"Signed by: {sig.get('signed_by_email') or '<unknown>'}\n"
        f"Content hash (sha256): {sig['content_hash_sha256']}\n"
        + (
            f"Content fingerprint (sha256, sign-time): "
            f"{sig.get('content_fingerprint_sha256')}\n"
            if sig.get('content_fingerprint_sha256') else ""
        )
        + fa_line
        + supersession_line
        + f"Missing-data flags: {missing_line}\n"
        + f"Generator edit applied: {'yes' if n['edit_applied'] else 'no'}\n"
    )
    body = n["clinician_final"] or ""
    footer = (
        "\n"
        "— end of note body —\n"
        f"Exported by: {env.get('issued_by_email') or '<unknown>'} at {env['issued_at']}\n"
        f"Format variant: {env['format_variant']}\n"
        "This document was generated by ChartNav. The clinician of "
        "record has attested to the body above; the content hash "
        "fingerprints it for downstream tamper detection.\n"
    )
    return f"{header}\n{body}\n{footer}"


# ---------------------------------------------------------------------------
# FHIR DocumentReference variant
# ---------------------------------------------------------------------------

def render_fhir_document_reference(artifact: dict[str, Any]) -> dict[str, Any]:
    """Minimal FHIR R4 ``DocumentReference`` that wraps the signed note.

    Deliberately does not claim to be a SMART-on-FHIR transaction or a
    vendor write-back — ChartNav does not transmit this anywhere today.
    It is the **packaging format** so the shape is correct the moment
    someone wires transport.
    """
    n = artifact["note"]
    sig = artifact["signature"]
    enc = artifact["encounter"]
    env = artifact["export_envelope"]

    clinician_final: str = n["clinician_final"] or ""
    data_b64 = base64.b64encode(clinician_final.encode("utf-8")).decode("ascii")

    lifecycle = artifact.get("lifecycle") or {}
    final_approval = artifact.get("final_approval") or {}

    # Phase 54 — FHIR docStatus semantics:
    #   * amended  → FHIR "amended" (R4 distinct from "final")
    #   * signed / exported + not superseded → "final"
    #   * anything else → "preliminary"
    # Legacy code sent `amended` rows down the `preliminary` branch,
    # which misrepresented the record of care.
    draft_state = n["draft_status"]
    if draft_state == "amended":
        doc_status = "amended"
    elif draft_state in {"signed", "exported"} and not lifecycle.get("superseded_at"):
        doc_status = "final"
    elif draft_state in {"signed", "exported"} and lifecycle.get("superseded_at"):
        # A signed row that has been superseded by an amendment is no
        # longer the record of care; mark as "superseded" (R4 value).
        doc_status = "superseded"
    else:
        doc_status = "preliminary"

    # Entered-in-error maps to FHIR `entered-in-error`; ChartNav
    # never emits this today. If/when we add a retract flow, add
    # a branch here.

    resource: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "identifier": [
            {
                "system": "urn:chartnav:note",
                "value": f"{n['id']}:v{n['version_number']}",
            }
        ],
        "status": "current",
        "docStatus": doc_status,
        "type": {"coding": [LOINC_PROGRESS_NOTE]},
        "date": sig.get("signed_at") or env["issued_at"],
        "author": [
            {"display": sig.get("signed_by_email") or "<unknown>"},
        ],
        "description": (
            f"ChartNav signed progress note, v{n['version_number']}, "
            f"format={n['format']}, edit_applied={n['edit_applied']}"
        ),
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain; charset=utf-8",
                    "language": "en",
                    "data": data_b64,
                    "title": f"ChartNav note v{n['version_number']}",
                    "creation": sig.get("signed_at") or env["issued_at"],
                    "hash": sig["content_hash_sha256"],
                }
            }
        ],
        "context": {
            "encounter": [
                {
                    "identifier": (
                        {
                            "system": "urn:chartnav:encounter",
                            "value": str(enc["id"]),
                        }
                    ),
                    "display": (
                        enc.get("patient_display") or "<patient>"
                    ),
                }
            ],
        },
        "meta": {
            "source": "chartnav.v1",
            "tag": [
                {
                    "system": "urn:chartnav:artifact",
                    "code": ARTIFACT_TYPE,
                }
            ],
        },
    }

    # If the encounter is externally sourced (already from FHIR), surface
    # the external reference as an additional encounter identifier so a
    # downstream integrator can tie the document back to their own
    # Encounter resource without a second round-trip.
    if enc.get("source") == "fhir" and enc.get("external_ref"):
        resource["context"]["encounter"][0]["identifier"] = {
            "system": "urn:fhir:Encounter",
            "value": enc["external_ref"],
        }

    return resource


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def resolve_format(raw: str | None) -> str:
    """Translate a user-facing format string into a canonical variant."""
    if raw is None:
        return "chartnav.v1.json"
    key = raw.strip().lower()
    canonical = FORMAT_ALIASES.get(key)
    if canonical is None:
        raise ArtifactError(
            "unsupported_artifact_format",
            f"format must be one of {sorted(set(FORMAT_ALIASES.values()))}",
            400,
        )
    return canonical


def build_for_format(
    *,
    note_id: int,
    format_variant: str,
    caller_email: str | None,
    caller_user_id: int | None,
    caller_organization_id: int | None,
) -> tuple[Any, str, str]:
    """Entry point used by the HTTP handler.

    Returns ``(body, mime_type, format_variant)`` where ``body`` is a
    dict for json/fhir and a str for text — FastAPI can return either
    directly via a typed response.
    """
    artifact = build_artifact(
        note_id=note_id,
        caller_email=caller_email,
        caller_user_id=caller_user_id,
        caller_organization_id=caller_organization_id,
    )
    canonical = resolve_format(format_variant)

    if canonical == "chartnav.v1.json":
        return artifact, JSON_MIME, canonical
    if canonical == "chartnav.v1.text":
        return render_text(artifact), TEXT_MIME, canonical
    if canonical == "fhir.DocumentReference.v1":
        return render_fhir_document_reference(artifact), FHIR_MIME, canonical

    # resolve_format already raised for anything unknown; guard regardless.
    raise ArtifactError(
        "unsupported_artifact_format",
        f"unknown canonical format {canonical!r}",
        400,
    )
