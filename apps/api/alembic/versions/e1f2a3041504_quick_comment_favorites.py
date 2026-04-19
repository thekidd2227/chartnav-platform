"""per-clinician quick-comment favorites

Revision ID: e1f2a3041504
Revises: e1f2a3041503
Create Date: 2026-04-19 10:00:00.000000

Phase 28 — pin / favorite quick comments.

Creates `clinician_quick_comment_favorites` — a per-user, org-scoped
bag of "pinned" references. Exactly one of two refs populated per
row, enforced by a CHECK constraint:

- ``preloaded_ref`` — the stable string id from the preloaded pack
  (e.g. ``"post-44"``, ``"plan-50"``). Never a DB id, so if the
  preloaded list is reordered on the frontend nothing breaks.
- ``custom_comment_id`` — FK into ``clinician_quick_comments`` for
  the doctor's own custom comments.

The two unique constraints (one per ref type) fire ONLY when the
corresponding column is non-NULL — SQLite and Postgres both treat
NULLs as distinct in UNIQUE, which is exactly what we want: a
clinician cannot double-favorite the same ref, but can have one
preloaded favorite + one custom favorite that each live on
separate rows.

This table is deliberately narrower than the custom-comments
table — no `body`, no `is_active` (a favorite is removed by
deleting the row), no `updated_at` (the record either exists or
it doesn't). If a custom comment is soft-deleted, the favorite
row sticks around but the join for rendering filters it out.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041504"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041503"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinician_quick_comment_favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "user_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "preloaded_ref", sa.String(length=64), nullable=True,
            comment="stable string id from the preloaded pack; NULL "
            "for custom favorites",
        ),
        sa.Column(
            "custom_comment_id", sa.Integer(), nullable=True,
            comment="FK into clinician_quick_comments; NULL for "
            "preloaded favorites",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_qc_favorites_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_qc_favorites_user",
        ),
        sa.ForeignKeyConstraint(
            ["custom_comment_id"], ["clinician_quick_comments.id"],
            name="fk_qc_favorites_custom",
        ),
        sa.CheckConstraint(
            "(preloaded_ref IS NOT NULL AND custom_comment_id IS NULL) OR "
            "(preloaded_ref IS NULL AND custom_comment_id IS NOT NULL)",
            name="ck_qc_favorites_exactly_one_ref",
        ),
        sa.UniqueConstraint(
            "user_id", "preloaded_ref",
            name="uq_qc_favorites_user_preloaded",
        ),
        sa.UniqueConstraint(
            "user_id", "custom_comment_id",
            name="uq_qc_favorites_user_custom",
        ),
    )


def downgrade() -> None:
    op.drop_table("clinician_quick_comment_favorites")
