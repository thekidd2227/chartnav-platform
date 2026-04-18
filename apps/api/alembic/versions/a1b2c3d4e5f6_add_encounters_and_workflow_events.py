"""add encounters and workflow_events

Revision ID: a1b2c3d4e5f6
Revises: 43ccbf363a8f
Create Date: 2026-04-17 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "43ccbf363a8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id"),
            nullable=False,
        ),
        sa.Column("patient_identifier", sa.String(length=255), nullable=False),
        sa.Column("patient_name", sa.String(length=255), nullable=True),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_encounters_organization_id", "encounters", ["organization_id"]
    )
    op.create_index("ix_encounters_location_id", "encounters", ["location_id"])
    op.create_index(
        "ix_encounters_patient_identifier",
        "encounters",
        ["patient_identifier"],
    )
    op.create_index("ix_encounters_status", "encounters", ["status"])

    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id",
            sa.Integer(),
            sa.ForeignKey("encounters.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_data", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_workflow_events_encounter_id",
        "workflow_events",
        ["encounter_id"],
    )
    op.create_index(
        "ix_workflow_events_event_type", "workflow_events", ["event_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_events_event_type", table_name="workflow_events")
    op.drop_index("ix_workflow_events_encounter_id", table_name="workflow_events")
    op.drop_table("workflow_events")

    op.drop_index("ix_encounters_status", table_name="encounters")
    op.drop_index("ix_encounters_patient_identifier", table_name="encounters")
    op.drop_index("ix_encounters_location_id", table_name="encounters")
    op.drop_index("ix_encounters_organization_id", table_name="encounters")
    op.drop_table("encounters")
