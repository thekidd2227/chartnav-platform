"""org settings JSON + user invited_at

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-18 12:00:00.000000

- `organizations.settings`: TEXT, nullable. Free-form JSON for tenant
  preferences (the admin UI edits a small whitelisted subset). Stored
  as TEXT so the same column works on SQLite + Postgres without extra
  extensions.
- `users.invited_at`: DATETIME, nullable. Server sets it when an admin
  creates a user. The frontend uses it to render a "Invited" badge in
  the admin panel. Email delivery is intentionally out of scope.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("settings", sa.Text(), nullable=True))

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("invited_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("invited_at")

    with op.batch_alter_table("organizations") as batch:
        batch.drop_column("settings")
