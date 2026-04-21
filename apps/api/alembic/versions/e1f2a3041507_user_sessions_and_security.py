"""user_sessions table for real session governance

Revision ID: e1f2a3041507
Revises: e1f2a3041506
Create Date: 2026-04-21 02:00:00.000000

Phase 48 — enterprise control plane, wave 2.

Adds a single new table, `user_sessions`, to track authenticated
sessions so the platform can enforce idle + absolute timeouts and
admin-driven revocation. Extended security policy values
(`audit_sink_mode`, `audit_sink_target`, `security_admin_emails`)
land in the existing `organizations.settings` JSON blob — no
schema change needed for those.

Design rules:

- Tracking is a strict no-op at the middleware layer when the org
  has not configured `idle_timeout_minutes` / `absolute_timeout_minutes`.
  That keeps local dev + every existing pytest path zero-cost.
- `session_key` is a deterministic fingerprint of the auth transport
  (header mode → email slug; bearer mode → first 32 hex chars of a
  SHA-256 of the token). The raw token is NEVER persisted.
- Revocation stores `revoked_at` + `revoked_reason` + `revoked_by_user_id`
  so the audit surface can show a full revocation history, not just
  "disappeared."
- `last_activity_at` is advanced on every authenticated request
  (rate-limited to at most once per 30 seconds — enforced in the
  runtime path, not the schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041507"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
            comment="org scope; matches users.organization_id at session open",
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_key",
            sa.String(length=128),
            nullable=False,
            comment=(
                "deterministic fingerprint of the auth transport — "
                "NEVER the raw bearer token. Header-mode: a slug of the "
                "user's email. Bearer-mode: first 32 hex chars of a "
                "SHA-256 of the token payload."
            ),
        ),
        sa.Column(
            "auth_mode",
            sa.String(length=16),
            nullable=False,
            comment="'header' or 'bearer' — the transport that created this row",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_reason",
            sa.String(length=64),
            nullable=True,
            comment=(
                "one of: 'admin_terminated', 'idle_timeout', "
                "'absolute_timeout', 'user_logout', 'mfa_revoked'"
            ),
        ),
        sa.Column(
            "revoked_by_user_id",
            sa.Integer(),
            nullable=True,
            comment="user_id of the admin who revoked, when applicable",
        ),
        sa.Column(
            "remote_addr",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.String(length=512),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_user_sessions_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_sessions_user",
        ),
        sa.UniqueConstraint(
            "user_id",
            "session_key",
            name="uq_user_sessions_user_key",
        ),
    )
    op.create_index(
        "ix_user_sessions_org_active",
        "user_sessions",
        ["organization_id", "revoked_at", "last_activity_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_sessions_org_active", table_name="user_sessions")
    op.drop_table("user_sessions")
