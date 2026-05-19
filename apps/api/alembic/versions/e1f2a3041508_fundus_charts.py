"""fundus_charts table

Revision ID: e1f2a3041508
Revises: a8b9c0d1e2f3
Create Date: 2026-05-19
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3041508"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fundus_charts",
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
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("note_version_id", sa.Integer(), nullable=True),
        sa.Column(
            "laterality", sa.String(length=8),
            nullable=False, server_default="OD",
        ),
        sa.Column(
            "status", sa.String(length=32),
            nullable=False, server_default="draft",
        ),
        sa.Column(
            "source_type", sa.String(length=32),
            nullable=False, server_default="ai_generated",
        ),
        sa.Column("findings_json", sa.Text(), nullable=True),
        sa.Column(
            "drawing_json", sa.Text(),
            nullable=False, server_default="{}",
        ),
        sa.Column("rendered_svg", sa.Text(), nullable=True),
        sa.Column("ai_model_name", sa.String(length=128), nullable=True),
        sa.Column("ai_confidence_json", sa.Text(), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_fundus_charts_org",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_fundus_charts_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"],
            name="fk_fundus_charts_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"], ["users.id"],
            name="fk_fundus_charts_signed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_fundus_charts_created_by",
        ),
    )
    op.create_index("ix_fundus_charts_org", "fundus_charts", ["organization_id"])
    op.create_index("ix_fundus_charts_encounter", "fundus_charts", ["encounter_id"])
    op.create_index("ix_fundus_charts_status", "fundus_charts", ["status"])
    op.create_index("ix_fundus_charts_laterality", "fundus_charts", ["laterality"])
    op.create_index("ix_fundus_charts_signed_at", "fundus_charts", ["signed_at"])


def downgrade() -> None:
    op.drop_index("ix_fundus_charts_signed_at", table_name="fundus_charts")
    op.drop_index("ix_fundus_charts_laterality", table_name="fundus_charts")
    op.drop_index("ix_fundus_charts_status", table_name="fundus_charts")
    op.drop_index("ix_fundus_charts_encounter", table_name="fundus_charts")
    op.drop_index("ix_fundus_charts_org", table_name="fundus_charts")
    op.drop_table("fundus_charts")
