"""Phase 80 — Cataract surgical workflow records.

Adds one table that records structured cataract pre-op / post-op
workflow metadata per (patient, surgery_eye). Phase 80 is
**workflow intelligence**, not clinical intelligence. ChartNav does
NOT select an IOL power, does NOT recommend a surgical technique,
does NOT recommend a surgery date, does NOT infer complications,
does NOT order tests, refer, message patients, or bill / code.

Every row stores what the provider entered. Free-text fields
(``target_refraction``, ``lens_plan_label``, ``complication_note``,
``notes``) are explicitly labeled as ``provider-entered`` on the UI
and are never aggregated into deterministic queue projections.

Pre-op signals:

  * ``planned_surgery_date``       — provider-entered date (nullable)
  * ``biometry_study_id``          — optional FK to ``imaging_studies``
                                     where the biometry packet lives
  * ``biometry_reviewed``          — provider attests biometry reviewed
  * ``topography_reviewed``        — provider attests topography reviewed
  * ``consent_status``             — discrete enum
  * ``target_refraction``          — provider-entered free text
  * ``lens_plan_label``            — provider-entered free text

Post-op cadence signals:

  * ``postop_day_1_status``        — discrete enum (not_scheduled /
                                     scheduled / completed / missed /
                                     unknown)
  * ``postop_week_1_status``       — same enum
  * ``postop_month_1_status``      — same enum

Provider-entered complications:

  * ``complications_flag``         — provider-entered boolean
  * ``complication_note``          — provider-entered free text

Every row is ``organization_id``-scoped; cross-org reads return 404.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "f8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SURGERY_EYE_VALUES = ("OD", "OS")
_CONSENT_STATUSES = (
    "not_obtained",
    "in_progress",
    "signed",
    "declined",
    "unknown",
)
_POSTOP_STATUSES = (
    "not_scheduled",
    "scheduled",
    "completed",
    "missed",
    "unknown",
)


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "cataract_workflow_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("surgery_eye", sa.String(length=2), nullable=False),
        sa.Column("planned_surgery_date", sa.Date(), nullable=True),
        sa.Column("biometry_study_id", sa.Integer(), nullable=True),
        sa.Column(
            "biometry_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "topography_reviewed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "consent_status",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("target_refraction", sa.String(length=64), nullable=True),
        sa.Column("lens_plan_label", sa.String(length=160), nullable=True),
        sa.Column(
            "postop_day_1_status",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "postop_week_1_status",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "postop_month_1_status",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "complications_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("complication_note", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["organization_id"],
            ["organizations.id"],
            name="fk_cataract_workflow_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_cataract_workflow_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_cataract_workflow_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["biometry_study_id"],
            ["imaging_studies.id"],
            name="fk_cataract_workflow_biometry",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_cataract_workflow_creator",
        ),
        sa.CheckConstraint(
            f"surgery_eye IN ({_csv(_SURGERY_EYE_VALUES)})",
            name="ck_cataract_workflow_eye_allowed",
        ),
        sa.CheckConstraint(
            f"consent_status IN ({_csv(_CONSENT_STATUSES)})",
            name="ck_cataract_workflow_consent_allowed",
        ),
        sa.CheckConstraint(
            f"postop_day_1_status IN ({_csv(_POSTOP_STATUSES)})",
            name="ck_cataract_workflow_postop_day_1_allowed",
        ),
        sa.CheckConstraint(
            f"postop_week_1_status IN ({_csv(_POSTOP_STATUSES)})",
            name="ck_cataract_workflow_postop_week_1_allowed",
        ),
        sa.CheckConstraint(
            f"postop_month_1_status IN ({_csv(_POSTOP_STATUSES)})",
            name="ck_cataract_workflow_postop_month_1_allowed",
        ),
    )
    op.create_index(
        "ix_cataract_workflow_org_patient",
        "cataract_workflow_records",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_cataract_workflow_patient_eye",
        "cataract_workflow_records",
        ["patient_id", "surgery_eye"],
    )
    op.create_index(
        "ix_cataract_workflow_org_surgery_date",
        "cataract_workflow_records",
        ["organization_id", "planned_surgery_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cataract_workflow_org_surgery_date",
        table_name="cataract_workflow_records",
    )
    op.drop_index(
        "ix_cataract_workflow_patient_eye",
        table_name="cataract_workflow_records",
    )
    op.drop_index(
        "ix_cataract_workflow_org_patient",
        table_name="cataract_workflow_records",
    )
    op.drop_table("cataract_workflow_records")
