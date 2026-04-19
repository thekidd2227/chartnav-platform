"""Note-generation orchestrator (phase 22).

Sits between the HTTP handler and the low-level
`note_generator.generate_draft(...)` seam. The orchestrator's job is
to enforce the **pipeline contract**:

    1. input must exist + be `completed`            (else NotReady)
    2. findings extracted via generate_draft(...)   (input-ready)
    3. note drafted with missing-flag metadata     (ready for review)
    4. provider review required                    (always, today)

Separating this layer from the generator lets us:
- drop in a real LLM (or a different extractor) by swapping
  `note_generator._run_generator` without touching the pipeline.
- add retries, streaming, or async background generation later
  without rewriting the HTTP handler.
- emit clean, stable error codes at every pipeline step.

The orchestrator is synchronous today (runs in the request path).
The contract survives a future move to background jobs — a worker
just calls the same function.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa

from app.db import engine, fetch_one, insert_returning_id, transaction
from app.services.note_generator import GenerationResult, generate_draft

log = logging.getLogger("chartnav.note_orchestrator")


class OrchestrationError(RuntimeError):
    def __init__(self, error_code: str, reason: str, status_code: int = 409):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason
        self.status_code = status_code


@dataclass(frozen=True)
class PipelineOutput:
    note_id: int
    findings_id: int
    version_number: int


def _resolve_source_input(conn, encounter_id: int, input_id: int | None) -> dict[str, Any]:
    if input_id is not None:
        row = conn.execute(
            sa.text(
                "SELECT id, encounter_id, input_type, processing_status, "
                "transcript_text FROM encounter_inputs "
                "WHERE id = :id AND encounter_id = :eid"
            ),
            {"id": input_id, "eid": encounter_id},
        ).mappings().first()
        if row is None:
            raise OrchestrationError(
                "input_not_found", "no such encounter input", 404
            )
    else:
        row = conn.execute(
            sa.text(
                "SELECT id, encounter_id, input_type, processing_status, "
                "transcript_text FROM encounter_inputs "
                "WHERE encounter_id = :eid AND processing_status = 'completed' "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"eid": encounter_id},
        ).mappings().first()
        if row is None:
            raise OrchestrationError(
                "no_completed_input",
                "encounter has no completed input to generate from; "
                "ingest first or retry a failed one",
            )

    if row["processing_status"] != "completed":
        raise OrchestrationError(
            "input_not_ready",
            f"input is {row['processing_status']!r}, expected 'completed' "
            "before generation",
        )
    return dict(row)


def run_note_generation(
    *,
    encounter_id: int,
    input_id: int | None,
    patient_display: str,
    provider_display: str,
    note_format: str = "soap",
) -> PipelineOutput:
    """End-to-end pipeline: input → findings → note_versions row.

    Every DB write happens inside a single transaction so partial
    output never ends up on disk. The deterministic generator today
    returns synchronously; a future LLM implementation can keep the
    same contract by returning a `GenerationResult` and letting this
    function persist it.
    """
    with engine.begin() as conn:
        source = _resolve_source_input(conn, encounter_id, input_id)

        try:
            result: GenerationResult = generate_draft(
                transcript_text=source.get("transcript_text") or "",
                patient_display=patient_display,
                provider_display=provider_display,
            )
        except Exception as e:
            log.exception(
                "note_generation_failed encounter_id=%s input_id=%s",
                encounter_id, source["id"],
            )
            raise OrchestrationError(
                "generation_failed",
                f"draft generator raised {type(e).__name__}: {e}",
                500,
            )

        findings_id = insert_returning_id(
            conn,
            "extracted_findings",
            {
                "encounter_id": encounter_id,
                "input_id": source["id"],
                "chief_complaint": result.findings.get("chief_complaint"),
                "hpi_summary": result.findings.get("hpi_summary"),
                "visual_acuity_od": result.findings.get("visual_acuity_od"),
                "visual_acuity_os": result.findings.get("visual_acuity_os"),
                "iop_od": result.findings.get("iop_od"),
                "iop_os": result.findings.get("iop_os"),
                "structured_json": json.dumps(
                    result.findings.get("structured_json", {}),
                    sort_keys=True,
                ),
                "extraction_confidence": result.findings.get(
                    "extraction_confidence"
                ),
            },
        )

        max_row = conn.execute(
            sa.text(
                "SELECT COALESCE(MAX(version_number), 0) AS n "
                "FROM note_versions WHERE encounter_id = :eid"
            ),
            {"eid": encounter_id},
        ).mappings().first()
        next_version = int(max_row["n"]) + 1 if max_row else 1

        note_id = insert_returning_id(
            conn,
            "note_versions",
            {
                "encounter_id": encounter_id,
                "version_number": next_version,
                "draft_status": "draft",
                "note_format": note_format,
                "note_text": result.note_text,
                "source_input_id": source["id"],
                "extracted_findings_id": findings_id,
                "generated_by": "system",
                "provider_review_required": True,
                "missing_data_flags": json.dumps(result.missing_flags),
            },
        )

    return PipelineOutput(
        note_id=note_id,
        findings_id=findings_id,
        version_number=next_version,
    )
