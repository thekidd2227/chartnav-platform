"""evidence sink retry disposition column

Revision ID: e1f2a304150f
Revises: e1f2a304150e
Create Date: 2026-04-22 10:00:00.000000

Phase 59 — evidence operations, trust, and retention closure.

Adds one column to `note_evidence_events`:

  sink_retry_disposition VARCHAR(24) NULL

Distinguishes operational retry noise from in-progress retries so
the operator can see what is still actionable:

  NULL                 → legacy (pre-phase-59); treat as pending
  'pending'            → transport failure; retry_sweep may pick up
  'permanent_failure'  → attempts crossed MAX_SINK_ATTEMPTS; no more
                         automatic retries; requires operator review
  'abandoned'          → operator-initiated give-up; audited

This column is NOT part of the canonical hash payload and never
feeds the evidence chain hashes — it governs retry classification
only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a304150f"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.add_column(
            sa.Column(
                "sink_retry_disposition",
                sa.String(length=24),
                nullable=True,
                comment=(
                    "'pending' | 'permanent_failure' | 'abandoned' | "
                    "NULL. Separates operator-actionable retry noise "
                    "from in-progress retries."
                ),
            )
        )
    op.create_index(
        "ix_note_evidence_events_retry_disposition",
        "note_evidence_events",
        ["organization_id", "sink_retry_disposition"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_note_evidence_events_retry_disposition",
        table_name="note_evidence_events",
    )
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.drop_column("sink_retry_disposition")
