"""Phase 21A — Retina + Glaucoma specialty tracking foundation.

Adds five tables that record longitudinal, provider-reviewed
ophthalmology specialty data:

  * ``retina_tracking``               — per-patient/per-eye review row
  * ``retina_injection_events``       — anti-VEGF / steroid history
  * ``glaucoma_tracking``             — per-patient/per-eye review row
  * ``glaucoma_iop_measurements``     — discrete IOP readings
  * ``glaucoma_visual_field_tests``   — VF test history

Every row is ``organization_id``-scoped. The route layer is
expected to enforce the same ``ensure_same_org`` + 404-on-cross-org
no-existence-leak invariant as the rest of the platform; foreign
keys here only enforce referential integrity within the org.

Phase 21A intentionally does NOT:
  * upload imaging files / DICOM (Phase 21B)
  * integrate vendor devices (Humphrey, Topcon OCT, etc.)
  * automate diagnosis, dosing, ordering, referral, messaging,
    or billing/coding
  * grade DR severity, determine cup/disc ratio, or recommend
    glaucoma medications

It only persists the structured findings a provider records during
or after an encounter, plus the discrete measurements (IOP, VF)
needed for trending in later phases.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- enum value sets (CHECK constraints; portable SQLite + Postgres) -

_EYE_OD_OS = ("OD", "OS")
_EYE_OD_OS_OU = ("OD", "OS", "OU")
_REVIEW_STATUSES = ("draft", "needs_review", "reviewed", "archived")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# --- upgrade ----------------------------------------------------------


def upgrade() -> None:
    # ----- retina_tracking -----
    op.create_table(
        "retina_tracking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("condition", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=True),
        sa.Column("last_oct_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fundus_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "injection_history_summary", sa.Text(), nullable=True
        ),
        sa.Column("follow_up_interval", sa.String(length=64), nullable=True),
        sa.Column("provider_assessment", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
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
            ["organization_id"], ["organizations.id"], name="fk_retina_org"
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_retina_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"], name="fk_retina_encounter"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_retina_creator"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"], name="fk_retina_updater"
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_OD_OS_OU)})",
            name="ck_retina_eye_allowed",
        ),
        sa.CheckConstraint(
            f"review_status IN ({_csv(_REVIEW_STATUSES)})",
            name="ck_retina_review_status_allowed",
        ),
    )
    op.create_index(
        "ix_retina_org_patient",
        "retina_tracking",
        ["organization_id", "patient_id"],
    )

    # ----- retina_injection_events -----
    op.create_table(
        "retina_injection_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("medication", sa.String(length=200), nullable=True),
        sa.Column(
            "procedure_date", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("laterality", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_retina_inj_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_retina_inj_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_retina_inj_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_retina_inj_creator",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_OD_OS_OU)})",
            name="ck_retina_inj_eye_allowed",
        ),
    )
    op.create_index(
        "ix_retina_inj_org_patient",
        "retina_injection_events",
        ["organization_id", "patient_id"],
    )

    # ----- glaucoma_tracking -----
    op.create_table(
        "glaucoma_tracking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("glaucoma_type", sa.String(length=120), nullable=True),
        sa.Column("target_iop", sa.Float(), nullable=True),
        sa.Column("latest_iop", sa.Float(), nullable=True),
        sa.Column("cup_to_disc_ratio", sa.Float(), nullable=True),
        sa.Column("rnfl_status", sa.String(length=120), nullable=True),
        sa.Column(
            "visual_field_status", sa.String(length=120), nullable=True
        ),
        sa.Column("medication_plan", sa.Text(), nullable=True),
        sa.Column(
            "progression_risk_label", sa.String(length=64), nullable=True
        ),
        sa.Column("provider_assessment", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
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
            ["organization_id"],
            ["organizations.id"],
            name="fk_glaucoma_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_glaucoma_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_glaucoma_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_glaucoma_creator",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_glaucoma_updater",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_OD_OS_OU)})",
            name="ck_glaucoma_eye_allowed",
        ),
        sa.CheckConstraint(
            f"review_status IN ({_csv(_REVIEW_STATUSES)})",
            name="ck_glaucoma_review_status_allowed",
        ),
    )
    op.create_index(
        "ix_glaucoma_org_patient",
        "glaucoma_tracking",
        ["organization_id", "patient_id"],
    )

    # ----- glaucoma_iop_measurements -----
    op.create_table(
        "glaucoma_iop_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("iop_value", sa.Float(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("method", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_iop_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_iop_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_iop_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_iop_creator",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_OD_OS)})",
            name="ck_iop_eye_allowed",
        ),
        sa.CheckConstraint(
            "iop_value >= 0 AND iop_value <= 80",
            name="ck_iop_value_range",
        ),
    )
    op.create_index(
        "ix_iop_org_patient",
        "glaucoma_iop_measurements",
        ["organization_id", "patient_id"],
    )

    # ----- glaucoma_visual_field_tests -----
    op.create_table(
        "glaucoma_visual_field_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("test_type", sa.String(length=120), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("reliability", sa.String(length=64), nullable=True),
        sa.Column("progression_flag", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_vf_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_vf_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_vf_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_vf_creator",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_OD_OS_OU)})",
            name="ck_vf_eye_allowed",
        ),
    )
    op.create_index(
        "ix_vf_org_patient",
        "glaucoma_visual_field_tests",
        ["organization_id", "patient_id"],
    )


# --- downgrade --------------------------------------------------------


def downgrade() -> None:
    op.drop_index("ix_vf_org_patient", table_name="glaucoma_visual_field_tests")
    op.drop_table("glaucoma_visual_field_tests")
    op.drop_index("ix_iop_org_patient", table_name="glaucoma_iop_measurements")
    op.drop_table("glaucoma_iop_measurements")
    op.drop_index("ix_glaucoma_org_patient", table_name="glaucoma_tracking")
    op.drop_table("glaucoma_tracking")
    op.drop_index(
        "ix_retina_inj_org_patient", table_name="retina_injection_events"
    )
    op.drop_table("retina_injection_events")
    op.drop_index("ix_retina_org_patient", table_name="retina_tracking")
    op.drop_table("retina_tracking")
