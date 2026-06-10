"""Phase 87 — FHIR R4 DocumentReference adapter.

Projects the Phase 77 retina visit packet as a FHIR DocumentReference
resource. The packet body itself is delivered as a base64-encoded
inline attachment so the DocumentReference is self-contained — no
binary fetch step is required and ChartNav does not need to host an
external bucket for this read-only export surface.

Hard rules:

  * Org isolation enforced; cross-org → 404 (no existence leak).
  * Read-only. No write-back, no upload, no submission to upstream
    EHRs, no SMART-on-FHIR launch, no bulk export.
  * The packet body is the same metadata-only projection Phase 77
    already returns — no new clinical free text is introduced.
  * Integrity metadata (sha256 of the canonical packet JSON) is
    embedded so a consumer can verify the attachment matches the
    DocumentReference's `meta` hash.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine
from app.fhir.patient_adapter import FhirExportError


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")


def _sha256_hex(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _confirm_encounter_exists(
    encounter_id: int, organization_id: int
) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, patient_id, status FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
    if row is None:
        return None
    return {
        "id": int(row[0]),
        "patient_id": int(row[1]) if row[1] is not None else None,
        "status": row[2],
    }


def build_document_reference_resource(
    encounter_id: int, caller: Caller
) -> dict[str, Any]:
    """Return a FHIR R4 DocumentReference resource for the given
    encounter's retina visit packet.

    Raises ``FhirExportError`` 404 when the encounter is not in the
    caller's organization.
    """
    from app.services.retina_visit_packet import (
        PACKET_SCHEMA_VERSION,
        build_packet,
    )
    from app.services.retina_visit_summary import SummaryError

    encounter = _confirm_encounter_exists(
        encounter_id, caller.organization_id
    )
    if encounter is None:
        raise FhirExportError(
            "encounter_not_found", "encounter not found", 404
        )

    try:
        packet = build_packet(encounter_id, caller)
    except SummaryError as exc:
        # Surface as a 404 to avoid leaking which encounters lack
        # buildable packets.
        raise FhirExportError("packet_not_available", str(exc), 404)

    packet_bytes = _canonical_json(packet)
    packet_hash = _sha256_hex(packet_bytes)
    packet_b64 = base64.b64encode(packet_bytes).decode("ascii")
    packet_size = len(packet_bytes)

    generated_at = packet.get("generated_at") or datetime.now(
        timezone.utc
    ).isoformat()

    review = packet.get("review_sign_lock", {})
    all_signed = bool(review.get("all_signed"))
    imaging_block = packet.get("imaging_metadata_summary", {}) or {}
    imaging_total = int(imaging_block.get("total_count", 0))
    imaging_reviewed = int(imaging_block.get("reviewed_count", 0))
    imaging_hash = imaging_block.get("summary_hash") or ""

    resource: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": f"retina-visit-packet-{encounter_id}",
        "meta": {
            "source": (
                f"urn:chartnav:organization:{caller.organization_id}"
            ),
            "versionId": PACKET_SCHEMA_VERSION,
        },
        "status": "current",
        "docStatus": "final" if all_signed else "preliminary",
        "identifier": [
            {
                "use": "official",
                "system": "urn:chartnav:retina-visit-packet",
                "value": f"encounter:{encounter_id}",
            },
            {
                "use": "secondary",
                "system": "urn:chartnav:packet-hash:sha256",
                "value": packet_hash,
            },
        ],
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11506-3",
                    "display": "Progress note",
                },
                {
                    "system": (
                        "https://chartnav.local/fhir/CodeSystem/document-type"
                    ),
                    "code": "retina-visit-packet",
                    "display": "Retina visit packet",
                },
            ],
            "text": "ChartNav retina visit packet (metadata-only)",
        },
        "subject": {
            "reference": (
                f"Patient/{encounter['patient_id']}"
                if encounter["patient_id"] is not None
                else None
            ),
        },
        "date": generated_at,
        "context": {
            "encounter": [{"reference": f"Encounter/{encounter_id}"}],
        },
        "content": [
            {
                "attachment": {
                    "contentType": "application/fhir+json",
                    "data": packet_b64,
                    "title": "retina-visit-packet.json",
                    "creation": generated_at,
                    "size": packet_size,
                    "hash": base64.b64encode(
                        bytes.fromhex(packet_hash)
                    ).decode("ascii"),
                },
                "format": {
                    "system": (
                        "https://chartnav.local/fhir/CodeSystem/document-format"
                    ),
                    "code": PACKET_SCHEMA_VERSION,
                    "display": "ChartNav retina visit packet 1.0",
                },
            }
        ],
        "extension": [
            {
                "url": (
                    "https://chartnav.local/fhir/StructureDefinition/packet-integrity"
                ),
                "extension": [
                    {
                        "url": "algorithm",
                        "valueCode": "sha256",
                    },
                    {
                        "url": "packet-hash-hex",
                        "valueString": packet_hash,
                    },
                    {
                        "url": "packet-bytes",
                        "valueInteger": packet_size,
                    },
                    {
                        "url": "packet-generated-at",
                        "valueDateTime": generated_at,
                    },
                    {
                        "url": "all-signed",
                        "valueBoolean": all_signed,
                    },
                ],
            },
            {
                "url": (
                    "https://chartnav.local/fhir/StructureDefinition/imaging-metadata-summary"
                ),
                "extension": [
                    {
                        "url": "total-count",
                        "valueInteger": imaging_total,
                    },
                    {
                        "url": "reviewed-count",
                        "valueInteger": imaging_reviewed,
                    },
                    {
                        "url": "unreviewed-count",
                        "valueInteger": imaging_total - imaging_reviewed,
                    },
                    {
                        "url": "summary-hash",
                        "valueString": imaging_hash,
                    },
                ],
            },
        ],
    }

    if resource["subject"]["reference"] is None:
        del resource["subject"]

    return resource


__all__ = ["build_document_reference_resource"]
