"""Phase 60 — visit_vitals_workups table

Structured technician + clinician vitals / workup intake row.
Encounter-scoped, org-scoped. Lifecycle: draft -> entered -> reviewed
-> signed, with `superseded` reserved for a future correction /
versioning flow.

Revision ID: b1c2d3e4f5a6
Revises: e1f2a3041508
Create Date: 2026-05-19
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041508"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visit_vitals_workups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
            server_default="technician_entry",
        ),
        # Blood pressure
        sa.Column("bp_systolic", sa.Integer(), nullable=True),
        sa.Column("bp_diastolic", sa.Integer(), nullable=True),
        sa.Column("bp_position", sa.String(length=16), nullable=True),
        sa.Column("bp_site", sa.String(length=16), nullable=True),
        # Temperature
        sa.Column("temperature_value", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "temperature_unit",
            sa.String(length=4),
            nullable=False,
            server_default="F",
        ),
        sa.Column("temperature_site", sa.String(length=16), nullable=True),
        # Other vitals
        sa.Column("pulse", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("oxygen_saturation", sa.Integer(), nullable=True),
        # Biometrics
        sa.Column("height_value", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "height_unit",
            sa.String(length=4),
            nullable=False,
            server_default="in",
        ),
        sa.Column("weight_value", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "weight_unit",
            sa.String(length=4),
            nullable=False,
            server_default="lb",
        ),
        sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
        # Pain
        sa.Column("pain_score", sa.Integer(), nullable=True),
        # Ophthalmology workup
        sa.Column("visual_acuity_od", sa.String(length=32), nullable=True),
        sa.Column("visual_acuity_os", sa.String(length=32), nullable=True),
        sa.Column("visual_acuity_ou", sa.String(length=32), nullable=True),
        sa.Column("iop_od", sa.Numeric(5, 2), nullable=True),
        sa.Column("iop_os", sa.Numeric(5, 2), nullable=True),
        sa.Column("iop_method", sa.String(length=16), nullable=True),
        sa.Column("dilation_status", sa.String(length=24), nullable=True),
        sa.Column("dilation_time", sa.DateTime(timezone=True), nullable=True),
        # Review checks
        sa.Column(
            "allergies_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "medications_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        # Free-text
        sa.Column("technician_notes", sa.Text(), nullable=True),
        # Warnings (metadata-only; the API audit detail still excludes
        # body text by convention, but warnings_json is part of the
        # response payload so the UI can render them).
        sa.Column("warnings_json", sa.Text(), nullable=True),
        # Provenance
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        # FKs
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_visit_vitals_workups_org",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_visit_vitals_workups_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_visit_vitals_workups_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"],
            ["users.id"],
            name="fk_visit_vitals_workups_signed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_visit_vitals_workups_created_by",
        ),
    )
    op.create_index(
        "ix_visit_vitals_workups_org",
        "visit_vitals_workups",
        ["organization_id"],
    )
    op.create_index(
        "ix_visit_vitals_workups_encounter",
        "visit_vitals_workups",
        ["encounter_id"],
    )
    op.create_index(
        "ix_visit_vitals_workups_patient",
        "visit_vitals_workups",
        ["patient_id"],
    )
    op.create_index(
        "ix_visit_vitals_workups_status",
        "visit_vitals_workups",
        ["status"],
    )
    op.create_index(
        "ix_visit_vitals_workups_signed_at",
        "visit_vitals_workups",
        ["signed_at"],
    )
    op.create_index(
        "ix_visit_vitals_workups_created_at",
        "visit_vitals_workups",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_visit_vitals_workups_created_at",
        table_name="visit_vitals_workups",
    )
    op.drop_index(
        "ix_visit_vitals_workups_signed_at",
        table_name="visit_vitals_workups",
    )
    op.drop_index(
        "ix_visit_vitals_workups_status",
        table_name="visit_vitals_workups",
    )
    op.drop_index(
        "ix_visit_vitals_workups_patient",
        table_name="visit_vitals_workups",
    )
    op.drop_index(
        "ix_visit_vitals_workups_encounter",
        table_name="visit_vitals_workups",
    )
    op.drop_index(
        "ix_visit_vitals_workups_org",
        table_name="visit_vitals_workups",
    )
    op.drop_table("visit_vitals_workups")
