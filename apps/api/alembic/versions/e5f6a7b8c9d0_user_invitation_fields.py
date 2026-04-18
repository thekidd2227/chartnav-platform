"""user invitation token/state fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-18 14:00:00.000000

Adds:
  users.invitation_token_hash   — sha256 hex of the invite token (raw token never stored)
  users.invitation_expires_at   — DATETIME; after this, /invites/accept rejects
  users.invitation_accepted_at  — DATETIME; set on successful accept

The raw token is returned once by POST /users/{id}/invite and never
again. Hashes are indexed for O(1) lookup by /invites/accept.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("invitation_token_hash", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("invitation_expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("invitation_accepted_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_users_invitation_token_hash",
        "users",
        ["invitation_token_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_invitation_token_hash", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("invitation_accepted_at")
        batch.drop_column("invitation_expires_at")
        batch.drop_column("invitation_token_hash")
