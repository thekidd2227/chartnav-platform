"""native patients + providers + encounter linkage

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-18 18:00:00.000000

Phase 18: the first real native clinical-object layer.

Adds:
- `patients`  (org-scoped, soft-active, optional external_ref for
  integrated-mode mirroring)
- `providers` (org-scoped, soft-active, optional NPI + external_ref)
- `encounters.patient_id`  (nullable FK — backward compatible)
- `encounters.provider_id` (nullable FK — backward compatible)

`patient_identifier` and `provider_name` remain on `encounters` as
denormalized display fields so existing reads keep working. Native
linkage becomes the preferred source of truth going forward; external
integrations carry `external_ref` for canonical mapping back to the
vendor system.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # patients — native clinical identity
    # ------------------------------------------------------------------
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False,
            index=True,
        ),
        sa.Column(
            "external_ref", sa.String(length=128), nullable=True,
            comment="vendor id (FHIR Patient.id, Epic MRN, etc.)",
        ),
        sa.Column(
            "patient_identifier", sa.String(length=64), nullable=False,
            comment="local MRN-equivalent; unique per org",
        ),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column(
            "sex_at_birth", sa.String(length=16), nullable=True,
            comment="clinically relevant for many specialties; free-form to "
            "avoid imposing a vocabulary we don't own",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_patients_organization",
        ),
        sa.UniqueConstraint(
            "organization_id", "patient_identifier",
            name="uq_patients_org_identifier",
        ),
        sa.UniqueConstraint(
            "organization_id", "external_ref",
            name="uq_patients_org_external_ref",
        ),
    )

    # ------------------------------------------------------------------
    # providers — native provider directory
    # ------------------------------------------------------------------
    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False,
            index=True,
        ),
        sa.Column(
            "external_ref", sa.String(length=128), nullable=True,
            comment="vendor id (FHIR Practitioner.id, etc.)",
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "npi", sa.String(length=16), nullable=True,
            comment="10-digit National Provider Identifier; "
            "format validated at the API layer, not at the DB layer",
        ),
        sa.Column("specialty", sa.String(length=128), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_providers_organization",
        ),
        sa.UniqueConstraint(
            "organization_id", "npi",
            name="uq_providers_org_npi",
        ),
        sa.UniqueConstraint(
            "organization_id", "external_ref",
            name="uq_providers_org_external_ref",
        ),
    )

    # ------------------------------------------------------------------
    # encounters.patient_id / encounters.provider_id
    # ------------------------------------------------------------------
    # SQLite can't ALTER TABLE ADD CONSTRAINT — batch rewrite.
    with op.batch_alter_table("encounters") as batch:
        batch.add_column(
            sa.Column("patient_id", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column("provider_id", sa.Integer(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_encounters_patient", "patients",
            ["patient_id"], ["id"],
        )
        batch.create_foreign_key(
            "fk_encounters_provider", "providers",
            ["provider_id"], ["id"],
        )
        batch.create_index(
            "ix_encounters_patient_id", ["patient_id"]
        )
        batch.create_index(
            "ix_encounters_provider_id", ["provider_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.drop_index("ix_encounters_provider_id")
        batch.drop_index("ix_encounters_patient_id")
        batch.drop_constraint("fk_encounters_provider", type_="foreignkey")
        batch.drop_constraint("fk_encounters_patient", type_="foreignkey")
        batch.drop_column("provider_id")
        batch.drop_column("patient_id")

    op.drop_table("providers")
    op.drop_table("patients")
