"""per-clinician clinical-shortcut favorites

Revision ID: e1f2a3041505
Revises: e1f2a3041504
Create Date: 2026-04-19 12:00:00.000000

Phase 30 — pin Clinical Shortcuts.

The phase-29 Clinical Shortcuts catalog is static UI content shipped
with the frontend bundle; each entry has a stable string id
(`pvd-01`, `rd-02`, `dme-03`, …). Pinning is a per-user surface:
one row per (user, shortcut_ref).

Deliberately a separate table from the phase-28
`clinician_quick_comment_favorites`. Both share the same ergonomic
shape (pin / unpin / render strip above the main catalog), but
they key on different namespaces and survive independently — a
shortcut ref is stable across the frontend bundle, while a
custom quick-comment id is a DB row that can be soft-deleted. A
unified three-column `favorites` table with a three-way CHECK is
harder to evolve in SQLite than two small focused tables, so
keep them separate.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041505"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041504"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinician_shortcut_favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "user_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "shortcut_ref", sa.String(length=64), nullable=False,
            comment="stable string id from the Clinical Shortcuts "
            "catalog (e.g. 'pvd-01', 'dme-03')",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_shortcut_favorites_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_shortcut_favorites_user",
        ),
        sa.UniqueConstraint(
            "user_id", "shortcut_ref",
            name="uq_shortcut_favorites_user_ref",
        ),
    )


def downgrade() -> None:
    op.drop_table("clinician_shortcut_favorites")
