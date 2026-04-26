"""phase 2 — referring_providers + consult_letters

Revision ID: p2c1l3t4r5p6
Revises: s3c4h5g6a7b8
Create Date: 2026-04-26 09:00:00.000000

Phase 2 item 1 of the closure plan:
docs/chartnav/closure/PHASE_B_Referring_Provider_Communication.md

Adds two tables that close the referring-provider communication
acceptance criteria:

  referring_providers   — operator-managed directory of referring
                          optometrists / PCPs / other ophthalmologists
                          per organization. Unique per org by NPI-10.

  consult_letters       — one row per (encounter, signed note version,
                          referring provider) pair. Carries delivery
                          channel + status. Once `sent_at` is set, the
                          row is treated as immutable by the route
                          layer (re-render returns the existing row).

Truth limitations preserved verbatim from the spec §9:
- Fax is a stub. No bytes leave the process.
- Email delivery is operator-SMTP-dependent; ChartNav does not run
  a shared outbound relay.
- FHIR `DocumentReference` write-back is only exercised in
  `integrated_writethrough` mode; in standalone / read-through it is
  explicitly skipped and logged.
- The letter is not a billable encounter document; it does not
  replace the signed note in the EHR of record.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2c1l3t4r5p6"
down_revision: Union[str, Sequence[str], None] = "s3c4h5g6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referring_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
            comment="organizations.id; cross-org access is forbidden",
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("practice", sa.String(length=255), nullable=True),
        sa.Column(
            "npi_10", sa.String(length=10), nullable=False,
            comment="10-digit NPI; Luhn-checked at the application "
                    "layer (CMS LUHN_10 with 80840 prefix)",
        ),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("fax", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "npi_10",
            name="uq_referring_providers_org_npi",
        ),
    )

    op.create_table(
        "consult_letters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
            comment="denormalized for org-scoping joins",
        ),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "note_version_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "referring_provider_id", sa.Integer(), nullable=False,
            index=True,
        ),
        sa.Column(
            "rendered_pdf_storage_ref", sa.String(length=255),
            nullable=False,
            comment="content-addressed key into the PDF blob store; "
                    "phase 2 stores inline in pdf_bytes for SQLite "
                    "pilot ergonomics",
        ),
        sa.Column(
            "pdf_bytes", sa.LargeBinary(), nullable=False,
            comment="rendered PDF blob; small (single-page text PDF)",
        ),
        sa.Column(
            "delivery_status", sa.String(length=32), nullable=False,
            server_default=sa.text("'rendered'"),
            comment="rendered | queued | sent | failed | stub_logged",
        ),
        sa.Column(
            "delivered_via", sa.String(length=16), nullable=False,
            server_default=sa.text("'download'"),
            comment="download | email | fax_stub",
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.UniqueConstraint(
            "note_version_id", "referring_provider_id",
            name="uq_consult_letters_version_provider",
        ),
    )


def downgrade() -> None:
    op.drop_table("consult_letters")
    op.drop_table("referring_providers")
