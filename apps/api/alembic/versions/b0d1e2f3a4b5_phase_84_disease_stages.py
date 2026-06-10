"""Phase 84 — Disease Staging Protocol Engine.

Adds a single table that stores provider-entered disease staging
records keyed to a patient + encounter pair. This is **workflow
intelligence**, not clinical intelligence: ChartNav does not stage
disease, does not interpret imaging to derive a stage, does not
infer progression, does not recommend treatment / surgery /
escalation. Every row is what the provider chose to record.

Supported staging systems (deliberately constrained to a closed
allowlist; new systems require a migration + service change):

  * AMD AREDS         : Category 1 / 2 / 3 / 4
  * Diabetic ETDRS    : Mild NPDR / Moderate NPDR / Severe NPDR /
                        Non-high-risk PDR / High-risk PDR / Advanced
  * Glaucoma POAG     : Mild / Moderate / Severe
  * Keratoconus AK    : Stage I / II / III / IV
  * Dry Eye DEWS      : Severity 1 / 2 / 3 / 4

Hard rules expressed in the schema:

  * ``staging_system`` is a closed allowlist (CHECK).
  * ``stage_value`` is non-empty (CHECK).
  * ``(staging_system, stage_value)`` allowed combinations are
    enforced at the service layer (cannot be expressed portably in a
    cross-dialect CHECK clause without bloat).
  * ``prior_stage`` is provider-entered; ChartNav does NOT auto-fill
    it from the previous row. The service may surface the previous
    row to the UI, but a POST without an explicit ``prior_stage``
    saves NULL.
  * ``progression_detected`` is computed in the service as a
    deterministic equality check (``prior_stage != stage_value`` when
    both are present) — not persisted as a column to avoid drift.
  * ``elapsed_days_since_prior`` is computed in the service at read
    time from ``staged_at`` against the most recent prior row.

Indexes:

  * (organization_id, patient_id) — list-by-patient
  * (patient_id, diagnosis_code, staged_at) — per-disease history
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "a9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STAGING_SYSTEMS = (
    "amd_areds",
    "diabetic_etdrs",
    "glaucoma_poag",
    "keratoconus_amsler_krumeich",
    "dry_eye_dews",
)


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "disease_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("diagnosis_code", sa.String(length=64), nullable=False),
        sa.Column("staging_system", sa.String(length=48), nullable=False),
        sa.Column("stage_value", sa.String(length=64), nullable=False),
        sa.Column("prior_stage", sa.String(length=64), nullable=True),
        sa.Column(
            "staged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("staged_by_user_id", sa.Integer(), nullable=False),
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
            name="fk_disease_stages_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_disease_stages_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_disease_stages_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["staged_by_user_id"],
            ["users.id"],
            name="fk_disease_stages_staged_by",
        ),
        sa.CheckConstraint(
            f"staging_system IN ({_csv(_STAGING_SYSTEMS)})",
            name="ck_disease_stages_system_allowed",
        ),
        sa.CheckConstraint(
            "length(stage_value) > 0",
            name="ck_disease_stages_stage_nonempty",
        ),
        sa.CheckConstraint(
            "length(diagnosis_code) > 0",
            name="ck_disease_stages_diagnosis_nonempty",
        ),
    )
    op.create_index(
        "ix_disease_stages_org_patient",
        "disease_stages",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_disease_stages_patient_diagnosis_date",
        "disease_stages",
        ["patient_id", "diagnosis_code", "staged_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_disease_stages_patient_diagnosis_date",
        table_name="disease_stages",
    )
    op.drop_index(
        "ix_disease_stages_org_patient",
        table_name="disease_stages",
    )
    op.drop_table("disease_stages")
