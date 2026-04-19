"""transcript ingestion + extracted findings + note versions

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18 19:00:00.000000

Phase 19 — the ChartNav wedge becomes real.

Adds three tables:

- `encounter_inputs` — persistent record of anything fed into ChartNav
  (audio upload blob metadata, pasted text, manual operator entry,
  imported transcript). One encounter can have many inputs over time.
- `extracted_findings` — structured ophthalmology facts derived from
  an input. Separate from the note narrative so operators can inspect
  WHAT the generator saw before reading HOW it wrote it.
- `note_versions` — versioned note drafts. Every regeneration + every
  provider save creates a new row. Only one can be `signed`. Older
  versions are immutable for audit.

All tables are org-scoped indirectly via `encounters.organization_id`;
every API handler asserts that scope explicitly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # encounter_inputs
    # ------------------------------------------------------------------
    op.create_table(
        "encounter_inputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "input_type", sa.String(length=32), nullable=False,
            comment=(
                "audio_upload | text_paste | manual_entry | "
                "imported_transcript"
            ),
        ),
        sa.Column(
            "processing_status", sa.String(length=32), nullable=False,
            server_default=sa.text("'queued'"),
            comment="queued | processing | completed | failed | needs_review",
        ),
        sa.Column(
            "transcript_text", sa.Text(), nullable=True,
            comment="raw text for text/paste/manual; null until STT "
            "completes for audio uploads",
        ),
        sa.Column(
            "confidence_summary", sa.String(length=32), nullable=True,
            comment="high | medium | low | unknown — optional",
        ),
        sa.Column(
            "source_metadata", sa.Text(), nullable=True,
            comment="JSON-encoded metadata (filename, duration, vendor, "
            "language, stt engine, ...)",
        ),
        sa.Column(
            "created_by_user_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_encounter_inputs_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_encounter_inputs_created_by",
        ),
    )

    # ------------------------------------------------------------------
    # extracted_findings
    # ------------------------------------------------------------------
    op.create_table(
        "extracted_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "input_id", sa.Integer(), nullable=True,
            comment="source input; nullable because findings can also "
            "come from a manual provider edit without re-ingestion",
        ),
        sa.Column(
            "chief_complaint", sa.Text(), nullable=True,
        ),
        sa.Column(
            "hpi_summary", sa.Text(), nullable=True,
            comment="history of present illness — short plain-text",
        ),
        sa.Column(
            "visual_acuity_od", sa.String(length=32), nullable=True,
        ),
        sa.Column(
            "visual_acuity_os", sa.String(length=32), nullable=True,
        ),
        sa.Column(
            "iop_od", sa.String(length=32), nullable=True,
        ),
        sa.Column(
            "iop_os", sa.String(length=32), nullable=True,
        ),
        sa.Column(
            "structured_json", sa.Text(), nullable=False,
            server_default=sa.text("'{}'"),
            comment="full structured extraction: OD/OS/OU detail, "
            "diagnoses[], medications[], imaging[], assessment, plan, "
            "follow_up_interval, flags[], extraction_confidence, ...",
        ),
        sa.Column(
            "extraction_confidence", sa.String(length=32), nullable=True,
            comment="high | medium | low — top-level confidence",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_extracted_findings_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["input_id"], ["encounter_inputs.id"],
            name="fk_extracted_findings_input",
        ),
    )

    # ------------------------------------------------------------------
    # note_versions
    # ------------------------------------------------------------------
    op.create_table(
        "note_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "version_number", sa.Integer(), nullable=False,
            comment="1-based, monotonically increasing within encounter",
        ),
        sa.Column(
            "draft_status", sa.String(length=32), nullable=False,
            server_default=sa.text("'draft'"),
            comment=(
                "draft | provider_review | revised | signed | exported"
            ),
        ),
        sa.Column(
            "note_format", sa.String(length=32), nullable=False,
            server_default=sa.text("'soap'"),
            comment="soap | assessment_plan | consult_note | freeform",
        ),
        sa.Column(
            "note_text", sa.Text(), nullable=False,
            comment="narrative body, plain text (no markup coupling)",
        ),
        sa.Column(
            "source_input_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "extracted_findings_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "generated_by", sa.String(length=16), nullable=False,
            server_default=sa.text("'system'"),
            comment="system (auto-draft) | manual (operator-authored)",
        ),
        sa.Column(
            "provider_review_required", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "missing_data_flags", sa.Text(), nullable=True,
            comment="JSON array of string codes the provider should "
            "verify before signing (e.g. ['iop_missing', "
            "'follow_up_interval_missing'])",
        ),
        sa.Column(
            "signed_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "signed_by_user_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "exported_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_note_versions_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["source_input_id"], ["encounter_inputs.id"],
            name="fk_note_versions_source_input",
        ),
        sa.ForeignKeyConstraint(
            ["extracted_findings_id"], ["extracted_findings.id"],
            name="fk_note_versions_findings",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"], ["users.id"],
            name="fk_note_versions_signed_by",
        ),
        sa.UniqueConstraint(
            "encounter_id", "version_number",
            name="uq_note_versions_encounter_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("note_versions")
    op.drop_table("extracted_findings")
    op.drop_table("encounter_inputs")
