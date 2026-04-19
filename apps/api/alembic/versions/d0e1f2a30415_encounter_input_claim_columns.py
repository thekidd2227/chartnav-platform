"""encounter_inputs claim columns for background worker pickup

Revision ID: d0e1f2a30415
Revises: c9d0e1f2a304
Create Date: 2026-04-18 23:45:00.000000

Phase 23 — give the async-job lifecycle real background-worker
semantics. Claim-based pickup prevents double-processing when
multiple workers poll the same queue.

Adds two nullable columns to `encounter_inputs`:

- `claimed_by`   VARCHAR(64) — worker id that currently owns the row.
- `claimed_at`   DATETIME     — when the claim was taken. Enables
  stale-claim recovery (`claimed_at < now - CHARTNAV_WORKER_CLAIM_TTL`).

Plus an index on `(processing_status, claimed_by)` so the
"give me one queued row that nobody has claimed" query is cheap.

Pure additive migration; existing rows unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a30415"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("encounter_inputs") as batch:
        batch.add_column(
            sa.Column("claimed_by", sa.String(length=64), nullable=True)
        )
        batch.add_column(
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_index(
            "ix_encounter_inputs_queue",
            ["processing_status", "claimed_by"],
        )


def downgrade() -> None:
    with op.batch_alter_table("encounter_inputs") as batch:
        batch.drop_index("ix_encounter_inputs_queue")
        batch.drop_column("claimed_at")
        batch.drop_column("claimed_by")
