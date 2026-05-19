"""visit vitals workups

Revision ID: e1f2a3041509
Revises: e1f2a3041508
Create Date: 2026-05-19

Structured technician workup and vitals intake. This table stores
provider-reviewable clinical intake values entered by staff or
clinicians. It does not store device integration payloads, diagnoses,
treatment recommendations, orders, referrals, patient messages, billing
codes, or automated coding outputs.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041509"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041508"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUSES = ("draft", "entered", "reviewed", "signed", "superseded")
_SOURCE_TYPES = ("technician_entry", "clinician_entry", "imported", "demo")
_BP_POSITIONS = ("sitting", "standing", "supine", "unknown")
_BP_SITES = ("left_arm", "right_arm", "wrist", "other", "unknown")
_TEMP_UNITS = ("F", "C")
_TEMP_SITES = ("oral", "temporal", "tympanic", "axillary", "other", "unknown")
_HEIGHT_UNITS = ("in", "cm")
_WEIGHT_UNITS = ("lb", "kg")
_IOP_METHODS = ("applanation", "tonopen", "icare", "other", "unknown")
_DILATION_STATUSES = ("not_dilated", "dilated", "declined", "contraindicated", "unknown")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "visit_vitals_workups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
            server_default="technician_entry",
        ),
        sa.Column("bp_systolic", sa.Integer(), nullable=True),
        sa.Column("bp_diastolic", sa.Integer(), nullable=True),
        sa.Column("bp_position", sa.String(length=32), nullable=True),
        sa.Column("bp_site", sa.String(length=32), nullable=True),
        sa.Column("temperature_value", sa.Numeric(6, 2), nullable=True),
        sa.Column("temperature_unit", sa.String(length=8), nullable=False, server_default="F"),
        sa.Column("temperature_site", sa.String(length=32), nullable=True),
        sa.Column("pulse", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("oxygen_saturation", sa.Integer(), nullable=True),
        sa.Column("height_value", sa.Numeric(7, 2), nullable=True),
        sa.Column("height_unit", sa.String(length=8), nullable=False, server_default="in"),
        sa.Column("weight_value", sa.Numeric(7, 2), nullable=True),
        sa.Column("weight_unit", sa.String(length=8), nullable=False, server_default="lb"),
        sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("visual_acuity_od", sa.String(length=64), nullable=True),
        sa.Column("visual_acuity_os", sa.String(length=64), nullable=True),
        sa.Column("visual_acuity_ou", sa.String(length=64), nullable=True),
        sa.Column("iop_od", sa.Numeric(5, 2), nullable=True),
        sa.Column("iop_os", sa.Numeric(5, 2), nullable=True),
        sa.Column("iop_method", sa.String(length=32), nullable=True),
        sa.Column("dilation_status", sa.String(length=32), nullable=True),
        sa.Column("dilation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "allergies_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "medications_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "technician_notes",
            sa.Text(),
            nullable=True,
            comment="Clinical free text. NEVER written to audit logs.",
        ),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_visit_vitals_workups_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_visit_vitals_workups_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_visit_vitals_workups_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"],
            name="fk_visit_vitals_workups_reviewed_by",
        ),
        sa.ForeignKeyConstraint(
            ["signed_by_user_id"], ["users.id"],
            name="fk_visit_vitals_workups_signed_by",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_visit_vitals_workups_created_by",
        ),
        sa.CheckConstraint(f"status IN ({_csv(_STATUSES)})", name="ck_visit_vitals_workups_status"),
        sa.CheckConstraint(
            f"source_type IN ({_csv(_SOURCE_TYPES)})",
            name="ck_visit_vitals_workups_source_type",
        ),
        sa.CheckConstraint(
            f"bp_position IS NULL OR bp_position IN ({_csv(_BP_POSITIONS)})",
            name="ck_visit_vitals_workups_bp_position",
        ),
        sa.CheckConstraint(
            f"bp_site IS NULL OR bp_site IN ({_csv(_BP_SITES)})",
            name="ck_visit_vitals_workups_bp_site",
        ),
        sa.CheckConstraint(
            f"temperature_unit IN ({_csv(_TEMP_UNITS)})",
            name="ck_visit_vitals_workups_temperature_unit",
        ),
        sa.CheckConstraint(
            f"temperature_site IS NULL OR temperature_site IN ({_csv(_TEMP_SITES)})",
            name="ck_visit_vitals_workups_temperature_site",
        ),
        sa.CheckConstraint(
            f"height_unit IN ({_csv(_HEIGHT_UNITS)})",
            name="ck_visit_vitals_workups_height_unit",
        ),
        sa.CheckConstraint(
            f"weight_unit IN ({_csv(_WEIGHT_UNITS)})",
            name="ck_visit_vitals_workups_weight_unit",
        ),
        sa.CheckConstraint(
            f"iop_method IS NULL OR iop_method IN ({_csv(_IOP_METHODS)})",
            name="ck_visit_vitals_workups_iop_method",
        ),
        sa.CheckConstraint(
            f"dilation_status IS NULL OR dilation_status IN ({_csv(_DILATION_STATUSES)})",
            name="ck_visit_vitals_workups_dilation_status",
        ),
    )
    op.create_index("ix_visit_vitals_workups_org", "visit_vitals_workups", ["organization_id"])
    op.create_index("ix_visit_vitals_workups_patient", "visit_vitals_workups", ["patient_id"])
    op.create_index("ix_visit_vitals_workups_encounter", "visit_vitals_workups", ["encounter_id"])
    op.create_index("ix_visit_vitals_workups_status", "visit_vitals_workups", ["status"])
    op.create_index("ix_visit_vitals_workups_signed_at", "visit_vitals_workups", ["signed_at"])
    op.create_index("ix_visit_vitals_workups_created_at", "visit_vitals_workups", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_visit_vitals_workups_created_at", table_name="visit_vitals_workups")
    op.drop_index("ix_visit_vitals_workups_signed_at", table_name="visit_vitals_workups")
    op.drop_index("ix_visit_vitals_workups_status", table_name="visit_vitals_workups")
    op.drop_index("ix_visit_vitals_workups_encounter", table_name="visit_vitals_workups")
    op.drop_index("ix_visit_vitals_workups_patient", table_name="visit_vitals_workups")
    op.drop_index("ix_visit_vitals_workups_org", table_name="visit_vitals_workups")
    op.drop_table("visit_vitals_workups")
