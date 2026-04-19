"""per-clinician custom quick-comment pad

Revision ID: e1f2a3041503
Revises: e1f2a3041502
Create Date: 2026-04-19 09:00:00.000000

Phase 27 — doctor quick-comment pad.

Creates `clinician_quick_comments` — a per-user, org-scoped bag of
short reusable clinician-authored comment snippets. The 50 preloaded
ophthalmology picks are UI content (shipped with the frontend); this
table only stores doctor-*authored* custom comments, so each user
curates their own short-list without polluting a global library or
mixing with transcript-derived / AI-generated content.

Design notes:
- Soft delete via `is_active=false`. Nothing is permanently removed
  so audit queries can still resolve references.
- No encounter / note linkage — these are a clinician's personal
  snippets, independent of any one encounter. Insertion into a
  specific note's draft happens on the client; that action is
  recorded via the existing note-edit audit path.
- `(organization_id, user_id, is_active)` index supports the
  "give me this clinician's current list" query cheaply.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041503"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinician_quick_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
            comment="org scope; matches the owning user's org at creation",
        ),
        sa.Column(
            "user_id", sa.Integer(), nullable=False, index=True,
            comment="owning clinician; comments are per-user not per-org",
        ),
        sa.Column(
            "body", sa.Text(), nullable=False,
            comment="the comment text; inserted as-is into the draft",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
            comment="soft delete — false means hidden from the UI list",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_clinician_quick_comments_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_clinician_quick_comments_user",
        ),
    )
    with op.batch_alter_table("clinician_quick_comments") as batch:
        batch.create_index(
            "ix_clinician_quick_comments_owner_active",
            ["organization_id", "user_id", "is_active"],
        )


def downgrade() -> None:
    with op.batch_alter_table("clinician_quick_comments") as batch:
        batch.drop_index("ix_clinician_quick_comments_owner_active")
    op.drop_table("clinician_quick_comments")
