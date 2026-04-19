"""encounter_inputs job lifecycle: retry_count, last_error, timestamps

Revision ID: c9d0e1f2a304
Revises: b8c9d0e1f203
Create Date: 2026-04-18 22:45:00.000000

Phase 22 — turn `encounter_inputs` into a real async-job record
instead of just a status string. Adds:

- `retry_count`       INTEGER NOT NULL default 0
- `last_error`        TEXT nullable
- `last_error_code`   VARCHAR(100) nullable
- `started_at`        DATETIME nullable — when a worker first began
  processing this input
- `finished_at`       DATETIME nullable — when processing ended
  (completed OR failed OR needs_review)
- `worker_id`         VARCHAR(64) nullable — optional worker/tenant
  identifier so ops can attribute stuck jobs

Nothing about existing rows changes; the migration is purely
additive. Seed is unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a304"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("encounter_inputs") as batch:
        batch.add_column(
            sa.Column(
                "retry_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch.add_column(sa.Column("last_error", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("last_error_code", sa.String(length=100), nullable=True)
        )
        batch.add_column(
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("worker_id", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("encounter_inputs") as batch:
        batch.drop_column("worker_id")
        batch.drop_column("finished_at")
        batch.drop_column("started_at")
        batch.drop_column("last_error_code")
        batch.drop_column("last_error")
        batch.drop_column("retry_count")
