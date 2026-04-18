"""admin governance: role CHECK + soft-delete flags

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-18 10:00:00.000000

- Adds a DB-level CHECK constraint on `users.role` to reject anything
  outside {admin, clinician, reviewer}. The seed already matches; this
  just hardens what the app layer enforces.
- Adds `is_active` boolean flags on `users` and `locations` for safe
  soft-delete (preserves foreign-key integrity of historical rows like
  encounters, workflow_events, and audit rows).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_CHECK = "role IN ('admin', 'clinician', 'reviewer')"


def upgrade() -> None:
    # Soft-delete flags. NOT NULL + default true so existing rows stay
    # active without backfill work.
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),  # portable: SQLite bool = int; Postgres coerces
            )
        )
        # DB-level role enforcement. batch_alter_table handles SQLite's
        # lack of ALTER TABLE ADD CONSTRAINT by rebuilding the table.
        batch.create_check_constraint("ck_users_role_allowed", ROLE_CHECK)

    with op.batch_alter_table("locations") as batch:
        batch.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("locations") as batch:
        batch.drop_column("is_active")

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.drop_column("is_active")
