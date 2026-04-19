"""encounter external linkage for integrated-mode bridge

Revision ID: b8c9d0e1f203
Revises: a7b8c9d0e1f2
Create Date: 2026-04-18 21:30:00.000000

Phase 21: native encounters grow an `external_ref` + `external_source`
pair so ChartNav can mirror an externally-sourced encounter shell
into its own table and hang the full workflow (transcript → findings
→ notes → signoff) off of that native row.

Rules:
- `external_ref` is the vendor's encounter id (FHIR `Encounter.id`,
  Epic contact id, etc.). Nullable — pure standalone encounters
  never set it.
- `external_source` is the adapter key (`fhir`, `stub`, vendor). Nullable.
- `(organization_id, external_ref, external_source)` is UNIQUE when
  `external_ref` is set — this is what makes the bridge idempotent.
- Locations / patient-display / provider-display continue to live in
  the existing columns; the bridge service mirrors whatever the
  adapter returns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f203"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.add_column(
            sa.Column("external_ref", sa.String(length=128), nullable=True)
        )
        batch.add_column(
            sa.Column("external_source", sa.String(length=64), nullable=True)
        )
        batch.create_unique_constraint(
            "uq_encounters_org_external",
            ["organization_id", "external_ref", "external_source"],
        )
        batch.create_index(
            "ix_encounters_external_ref", ["external_ref"]
        )


def downgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.drop_index("ix_encounters_external_ref")
        batch.drop_constraint("uq_encounters_org_external", type_="unique")
        batch.drop_column("external_source")
        batch.drop_column("external_ref")
