"""Merge: post_visit_summaries + ai_governance_tables

Revision ID: u5v6w7x8y9z0
Revises: p2a5pvs01, t4u5v6w7x8y9
Create Date: 2026-04-27 21:10:00.000000

Merges two independent head branches:
  p2a5pvs01 — Phase 2 post-visit summaries (main line)
  t4u5v6w7x8y9 — AI governance scaffold (new branch)

No schema changes — merge only.
"""

from alembic import op

revision = "u5v6w7x8y9z0"
down_revision = ("p2a5pvs01", "t4u5v6w7x8y9")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
