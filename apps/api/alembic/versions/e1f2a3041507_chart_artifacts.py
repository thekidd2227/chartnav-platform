"""chart_artifacts table — retinal diagram persistence shell

Revision ID: e1f2a3041507
Revises: e1f2a3041506
Create Date: 2026-05-04 11:00:00.000000

Persistence shell for retinal diagram artifacts. Each row is one version
of one artifact for a given patient (and optionally an encounter). Once
signed, a row is immutable; an "edit" produces a new row whose
parent_artifact_id points at the previous version, and version_number is
the parent's version_number + 1.

This migration deliberately does NOT add a drawing canvas, AI proposal
pipeline, or apply/reject workflow. It is the storage and identity
foundation only.

`drawing_json` is a TEXT column with JSON content. The application
serializes/deserializes via json.dumps/loads. This matches the
ai_governance_log pattern and stays portable across SQLite + Postgres.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041507"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chart_artifacts",
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
            "artifact_type", sa.String(length=64),
            nullable=False, server_default="retinal_diagram",
            comment="kept extensible; this PR ships only retinal_diagram",
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column(
            "findings_text", sa.Text(),
            nullable=False, server_default="",
            comment="provider-authored clinical note; NEVER logged in audit",
        ),
        sa.Column(
            "drawing_json", sa.Text(),
            nullable=False, server_default="{}",
            comment="JSON-encoded drawing payload; NEVER logged in audit",
        ),
        sa.Column(
            "version_number", sa.Integer(),
            nullable=False, server_default="1",
        ),
        sa.Column(
            "parent_artifact_id", sa.Integer(), nullable=True,
            comment="set on forks created when a signed artifact is edited",
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_chart_artifacts_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_chart_artifacts_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_chart_artifacts_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_chart_artifacts_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"], ["users.id"],
            name="fk_chart_artifacts_signed_by",
        ),
        sa.ForeignKeyConstraint(
            ["parent_artifact_id"], ["chart_artifacts.id"],
            name="fk_chart_artifacts_parent",
        ),
    )
    op.create_index(
        "ix_chart_artifacts_org_patient",
        "chart_artifacts",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_chart_artifacts_org_encounter",
        "chart_artifacts",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_chart_artifacts_parent",
        "chart_artifacts",
        ["parent_artifact_id"],
    )
    op.create_index(
        "ix_chart_artifacts_org_type_created",
        "chart_artifacts",
        ["organization_id", "artifact_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chart_artifacts_org_type_created", table_name="chart_artifacts")
    op.drop_index("ix_chart_artifacts_parent", table_name="chart_artifacts")
    op.drop_index("ix_chart_artifacts_org_encounter", table_name="chart_artifacts")
    op.drop_index("ix_chart_artifacts_org_patient", table_name="chart_artifacts")
    op.drop_table("chart_artifacts")
