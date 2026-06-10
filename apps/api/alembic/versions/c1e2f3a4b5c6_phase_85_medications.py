"""Phase 85 — Ophthalmic Medication Safety & Adherence Engine.

Adds three provider-entered tables:

  * ``medications``           — provider-entered drug list (eye drops,
                                oral systemic agents). Closed allowlist
                                on medication_class + route + laterality.
  * ``medication_refills``    — provider-entered refill events. Each row
                                carries a refill date and an
                                expected-days-supply count so a
                                deterministic refill-gap can be computed
                                without prescription writing.
  * ``medication_allergies``  — provider-entered allergy list, used only
                                for literal substance/class match
                                (NEVER an autonomous interaction check).

Hard rules expressed in the schema:

  * ``medication_class`` is a closed allowlist (CHECK). Ophthalmic
    classes (PGF2 analog, beta blocker, alpha agonist, CAI, rho-kinase,
    combination drop, steroid, NSAID, antibiotic, anti-VEGF
    intravitreal, lubricant) plus one explicit ``oral_systemic_other``
    catch-all. New classes require a migration + service change.
  * ``route`` ∈ {drops, oral, intravitreal}.
  * ``laterality`` ∈ {OD, OS, OU, NA}.
  * ``dose_per_day`` is a small non-negative integer (CHECK 0..24).
  * ``preservative_flag`` is provider-entered yes/no (Phase 85 does
    not autonomously categorize whether a drop contains BAK or other
    preservatives — that's a clinical knowledge call the provider
    makes when adding the row).
  * ``medication_allergies.severity`` ∈ {mild, moderate, severe} (CHECK).
  * ``medication_allergies.reaction_type`` ∈ closed allowlist (CHECK).

This is workflow infrastructure; it is NOT a prescription system.
ChartNav does NOT prescribe, does NOT refill, does NOT dose, does NOT
recommend medication changes, does NOT contact the pharmacy, and
does NOT perform autonomous drug interaction checking beyond a literal
substance/class match against the provider-entered allergy list.

Indexes:

  * medications: (organization_id, patient_id),
                 (patient_id, discontinued_on, started_on)
  * medication_refills: (organization_id, patient_id),
                        (medication_id, refill_date)
  * medication_allergies: (organization_id, patient_id)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "b0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_MED_CLASSES = (
    "pgf2_analog",
    "beta_blocker",
    "alpha_agonist",
    "carbonic_anhydrase_inhibitor",
    "rho_kinase_inhibitor",
    "combination_drop",
    "steroid_drop",
    "nsaid_drop",
    "antibiotic_drop",
    "anti_vegf_intravitreal",
    "lubricant",
    "oral_systemic_other",
)

_ROUTES = ("drops", "oral", "intravitreal")
_LATERALITIES = ("OD", "OS", "OU", "NA")

_REACTION_TYPES = (
    "rash",
    "swelling",
    "anaphylaxis",
    "gi_distress",
    "respiratory",
    "other",
)
_SEVERITIES = ("mild", "moderate", "severe")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "medications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("medication_name", sa.String(length=128), nullable=False),
        sa.Column("medication_class", sa.String(length=48), nullable=False),
        sa.Column("route", sa.String(length=16), nullable=False),
        sa.Column("laterality", sa.String(length=4), nullable=False),
        sa.Column("dose_per_day", sa.Integer(), nullable=False),
        sa.Column(
            "preservative_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("discontinued_on", sa.Date(), nullable=True),
        sa.Column("prescriber_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "prescriber_display_name", sa.String(length=128), nullable=True
        ),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
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
            name="fk_medications_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medications_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_medications_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name="fk_medications_recorded_by",
        ),
        sa.ForeignKeyConstraint(
            ["prescriber_user_id"],
            ["users.id"],
            name="fk_medications_prescriber",
        ),
        sa.CheckConstraint(
            f"medication_class IN ({_csv(_MED_CLASSES)})",
            name="ck_medications_class_allowed",
        ),
        sa.CheckConstraint(
            f"route IN ({_csv(_ROUTES)})",
            name="ck_medications_route_allowed",
        ),
        sa.CheckConstraint(
            f"laterality IN ({_csv(_LATERALITIES)})",
            name="ck_medications_laterality_allowed",
        ),
        sa.CheckConstraint(
            "dose_per_day >= 0 AND dose_per_day <= 24",
            name="ck_medications_dose_range",
        ),
        sa.CheckConstraint(
            "length(medication_name) > 0",
            name="ck_medications_name_nonempty",
        ),
    )
    op.create_index(
        "ix_medications_org_patient",
        "medications",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_medications_patient_active",
        "medications",
        ["patient_id", "discontinued_on", "started_on"],
    )

    op.create_table(
        "medication_refills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("medication_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("refill_date", sa.Date(), nullable=False),
        sa.Column("expected_days_supply", sa.Integer(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
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
            name="fk_medication_refills_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medication_refills_patient",
        ),
        sa.ForeignKeyConstraint(
            ["medication_id"],
            ["medications.id"],
            name="fk_medication_refills_medication",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_medication_refills_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name="fk_medication_refills_recorded_by",
        ),
        sa.CheckConstraint(
            "expected_days_supply >= 1 AND expected_days_supply <= 365",
            name="ck_medication_refills_supply_range",
        ),
    )
    op.create_index(
        "ix_medication_refills_org_patient",
        "medication_refills",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_medication_refills_medication_date",
        "medication_refills",
        ["medication_id", "refill_date"],
    )

    op.create_table(
        "medication_allergies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("substance", sa.String(length=128), nullable=False),
        sa.Column("reaction_type", sa.String(length=24), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
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
            name="fk_medication_allergies_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medication_allergies_patient",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            name="fk_medication_allergies_recorded_by",
        ),
        sa.CheckConstraint(
            f"reaction_type IN ({_csv(_REACTION_TYPES)})",
            name="ck_medication_allergies_reaction_allowed",
        ),
        sa.CheckConstraint(
            f"severity IN ({_csv(_SEVERITIES)})",
            name="ck_medication_allergies_severity_allowed",
        ),
        sa.CheckConstraint(
            "length(substance) > 0",
            name="ck_medication_allergies_substance_nonempty",
        ),
    )
    op.create_index(
        "ix_medication_allergies_org_patient",
        "medication_allergies",
        ["organization_id", "patient_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medication_allergies_org_patient",
        table_name="medication_allergies",
    )
    op.drop_table("medication_allergies")
    op.drop_index(
        "ix_medication_refills_medication_date",
        table_name="medication_refills",
    )
    op.drop_index(
        "ix_medication_refills_org_patient",
        table_name="medication_refills",
    )
    op.drop_table("medication_refills")
    op.drop_index(
        "ix_medications_patient_active", table_name="medications"
    )
    op.drop_index(
        "ix_medications_org_patient", table_name="medications"
    )
    op.drop_table("medications")
