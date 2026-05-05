"""patient_summaries — provider-reviewed patient-friendly summaries

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-05 11:30:00.000000

Phase 9. One row per patient-friendly summary draft. Generated from
provider-reviewed clinical sources (preferred: a reviewed/finalized
scribe_sessions row), then explicitly reviewed and finalized by a
provider before it is considered ready to share. This table never
sends anything to a patient — patient delivery is deferred.

Lifecycle: draft → reviewed → finalized; discarded reachable from
draft or reviewed. finalized and discarded are immutable.

Audit metadata only — plain_language_summary / key_findings /
next_steps / questions / limitations_notice / review_notes are
never written to the audit log.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUSES = ("draft", "reviewed", "finalized", "discarded")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "patient_summaries",
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
        sa.Column("scribe_session_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=32),
            nullable=False, server_default="draft",
        ),
        sa.Column(
            "plain_language_summary", sa.Text(),
            nullable=False, server_default="",
            comment="Provider-facing draft. NEVER written to audit logs.",
        ),
        sa.Column(
            "key_findings_json", sa.Text(),
            nullable=False, server_default="[]",
            comment="JSON-encoded list. NEVER written to audit logs.",
        ),
        sa.Column(
            "next_steps_json", sa.Text(),
            nullable=False, server_default="[]",
            comment="JSON-encoded list. NEVER written to audit logs.",
        ),
        sa.Column(
            "questions_json", sa.Text(),
            nullable=False, server_default="[]",
            comment="JSON-encoded list. NEVER written to audit logs.",
        ),
        sa.Column(
            "limitations_notice", sa.Text(),
            nullable=False, server_default="",
            comment="Provider-facing limitations notice. NEVER written to audit logs.",
        ),
        sa.Column(
            "review_notes", sa.Text(), nullable=True,
            comment="Reviewer notes. NEVER written to audit logs.",
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_patient_summaries_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_patient_summaries_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_patient_summaries_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["scribe_session_id"], ["scribe_sessions.id"],
            name="fk_patient_summaries_scribe_session",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_patient_summaries_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"],
            name="fk_patient_summaries_reviewed_by",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_STATUSES)})",
            name="ck_patient_summaries_status",
        ),
    )
    op.create_index(
        "ix_patient_summaries_org_patient",
        "patient_summaries",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_patient_summaries_org_encounter",
        "patient_summaries",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_patient_summaries_org_scribe_session",
        "patient_summaries",
        ["organization_id", "scribe_session_id"],
    )
    op.create_index(
        "ix_patient_summaries_org_status",
        "patient_summaries",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_patient_summaries_created_by_user_id",
        "patient_summaries",
        ["created_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patient_summaries_created_by_user_id",
        table_name="patient_summaries",
    )
    op.drop_index("ix_patient_summaries_org_status", table_name="patient_summaries")
    op.drop_index(
        "ix_patient_summaries_org_scribe_session",
        table_name="patient_summaries",
    )
    op.drop_index("ix_patient_summaries_org_encounter", table_name="patient_summaries")
    op.drop_index("ix_patient_summaries_org_patient", table_name="patient_summaries")
    op.drop_table("patient_summaries")
