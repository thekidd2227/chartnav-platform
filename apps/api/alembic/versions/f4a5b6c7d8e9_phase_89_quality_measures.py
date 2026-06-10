"""Phase 89 — IRIS / MIPS Quality Intelligence.

Adds two tables for provider-reviewed quality documentation support:

  * ``quality_measure_specs``     — closed allowlist of measure
                                    specifications. Organization-
                                    scoped or global (NULL org).
  * ``quality_measure_responses`` — provider responses keyed to
                                    encounter + measure.

This phase is **quality workflow support**, NOT certified MIPS
submission, NOT IRIS Registry integration, and NOT a billing
automation surface. The application layer marks every spec
``verified_for_submission = false`` until a qualified operator
explicitly verifies it.

Hard rules expressed by the schema:

  * ``response_type`` is a closed allowlist (CHECK):
    met / exception / exclusion / not_applicable / incomplete.
  * ``measure_id`` is non-empty (CHECK) on both tables.
  * ``measure_name`` is non-empty (CHECK) on the spec table.
  * ``program_year`` is in a reasonable range (CHECK 2020-2030).
  * ``status`` on the spec is closed (CHECK): active / inactive.
  * (organization_id, encounter_id, measure_id) is UNIQUE on
    responses so each measure has exactly one current response per
    encounter.

No CHECK on ``exception_code`` — exception code semantics are
spec-driven and validated at the service layer against the spec's
``exception_codes`` JSON.

This migration does NOT:

  * submit anything to CMS / IRIS / payers / registries,
  * autonomously compute MIPS scoring,
  * autonomously decide whether a measure is met (the provider
    records the response),
  * autonomously interpret images or clinical artifacts.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "d2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RESPONSE_TYPES = (
    "met",
    "exception",
    "exclusion",
    "not_applicable",
    "incomplete",
)

_SPEC_STATUSES = ("active", "inactive")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "quality_measure_specs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("measure_id", sa.String(length=64), nullable=False),
        sa.Column("measure_name", sa.String(length=255), nullable=False),
        sa.Column("program_year", sa.Integer(), nullable=False),
        sa.Column(
            "applicable_icd10_prefixes", sa.Text(), nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "required_fields", sa.Text(), nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "exception_codes", sa.Text(), nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "status", sa.String(length=16), nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_quality_measure_specs_org",
        ),
        sa.CheckConstraint(
            "length(measure_id) > 0",
            name="ck_quality_measure_specs_measure_id_nonempty",
        ),
        sa.CheckConstraint(
            "length(measure_name) > 0",
            name="ck_quality_measure_specs_name_nonempty",
        ),
        sa.CheckConstraint(
            "program_year >= 2020 AND program_year <= 2030",
            name="ck_quality_measure_specs_program_year_range",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_SPEC_STATUSES)})",
            name="ck_quality_measure_specs_status_allowed",
        ),
        sa.UniqueConstraint(
            "organization_id", "measure_id", "program_year",
            name="uq_quality_measure_specs_org_measure_year",
        ),
    )
    op.create_index(
        "ix_quality_measure_specs_measure_year",
        "quality_measure_specs",
        ["measure_id", "program_year"],
    )

    op.create_table(
        "quality_measure_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=False),
        sa.Column("measure_id", sa.String(length=64), nullable=False),
        sa.Column("response_type", sa.String(length=24), nullable=False),
        sa.Column("exception_code", sa.String(length=64), nullable=True),
        sa.Column("responded_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "responded_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_quality_measure_responses_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_quality_measure_responses_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_quality_measure_responses_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["responded_by_user_id"], ["users.id"],
            name="fk_quality_measure_responses_responder",
        ),
        sa.CheckConstraint(
            "length(measure_id) > 0",
            name="ck_quality_measure_responses_measure_id_nonempty",
        ),
        sa.CheckConstraint(
            f"response_type IN ({_csv(_RESPONSE_TYPES)})",
            name="ck_quality_measure_responses_type_allowed",
        ),
        sa.UniqueConstraint(
            "organization_id", "encounter_id", "measure_id",
            name="uq_quality_measure_responses_org_encounter_measure",
        ),
    )
    op.create_index(
        "ix_quality_measure_responses_org_encounter",
        "quality_measure_responses",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_quality_measure_responses_org_patient",
        "quality_measure_responses",
        ["organization_id", "patient_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quality_measure_responses_org_patient",
        table_name="quality_measure_responses",
    )
    op.drop_index(
        "ix_quality_measure_responses_org_encounter",
        table_name="quality_measure_responses",
    )
    op.drop_table("quality_measure_responses")
    op.drop_index(
        "ix_quality_measure_specs_measure_year",
        table_name="quality_measure_specs",
    )
    op.drop_table("quality_measure_specs")
