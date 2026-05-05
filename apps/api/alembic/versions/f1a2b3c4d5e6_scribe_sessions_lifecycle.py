"""scribe_sessions_lifecycle — AI scribe session table

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3041507
Create Date: 2026-05-04 23:30:00.000000

Phase 8. One row per AI scribe session — the unit of work between a
provider's source/transcript text and a finalized clinical artifact.

Lifecycle: draft → processing → ready_for_review → reviewed → finalized
(plus discarded, reachable from any non-terminal state).
finalized and discarded are immutable.

Org-scoped via FK to organizations. Patient-scoped via FK to patients.
Optional encounter linkage. Optional linked artifact (e.g., when a
session is the source for a chart artifact). Audit metadata only —
source/transcript/draft/structured/review_notes are never written into
the audit log.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Status + input_mode enums are enforced at the DB level via CHECK
# constraints (portable across SQLite + Postgres) instead of native
# ENUM types so the migration runs on both backends without dialect
# branches.

_STATUSES = (
    "draft",
    "processing",
    "ready_for_review",
    "reviewed",
    "finalized",
    "discarded",
)
_INPUT_MODES = (
    "pasted_text",
    "transcript",
    "audio_placeholder",
)


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "scribe_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=32),
            nullable=False, server_default="draft",
        ),
        sa.Column(
            "input_mode", sa.String(length=32),
            nullable=False, server_default="pasted_text",
        ),
        sa.Column(
            "source_text", sa.Text(), nullable=True,
            comment="Raw provider input. NEVER written to audit logs.",
        ),
        sa.Column(
            "transcript_text", sa.Text(), nullable=True,
            comment="Optional dictation transcript. NEVER written to audit logs.",
        ),
        sa.Column(
            "draft_note_text", sa.Text(), nullable=True,
            comment="Engine-produced draft. NEVER written to audit logs.",
        ),
        sa.Column(
            "structured_note_json", sa.Text(), nullable=True,
            comment=(
                "JSON-encoded sections (chief_complaint, hpi, exam, "
                "assessment, plan, unassigned_text). NEVER written to "
                "audit logs."
            ),
        ),
        sa.Column("linked_artifact_id", sa.Integer(), nullable=True),
        sa.Column(
            "review_notes", sa.Text(), nullable=True,
            comment="Reviewer notes. NEVER written to audit logs.",
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_scribe_sessions_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_scribe_sessions_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_scribe_sessions_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_scribe_sessions_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"],
            name="fk_scribe_sessions_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["linked_artifact_id"], ["chart_artifacts.id"],
            name="fk_scribe_sessions_linked_artifact",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_STATUSES)})",
            name="ck_scribe_sessions_status",
        ),
        sa.CheckConstraint(
            f"input_mode IN ({_csv(_INPUT_MODES)})",
            name="ck_scribe_sessions_input_mode",
        ),
    )
    op.create_index(
        "ix_scribe_sessions_org_encounter",
        "scribe_sessions",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_scribe_sessions_org_patient",
        "scribe_sessions",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_scribe_sessions_org_status",
        "scribe_sessions",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_scribe_sessions_created_by_user_id",
        "scribe_sessions",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_scribe_sessions_linked_artifact_id",
        "scribe_sessions",
        ["linked_artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scribe_sessions_linked_artifact_id",
        table_name="scribe_sessions",
    )
    op.drop_index(
        "ix_scribe_sessions_created_by_user_id",
        table_name="scribe_sessions",
    )
    op.drop_index("ix_scribe_sessions_org_status", table_name="scribe_sessions")
    op.drop_index("ix_scribe_sessions_org_patient", table_name="scribe_sessions")
    op.drop_index("ix_scribe_sessions_org_encounter", table_name="scribe_sessions")
    op.drop_table("scribe_sessions")
