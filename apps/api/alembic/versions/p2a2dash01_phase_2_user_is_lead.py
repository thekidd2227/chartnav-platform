"""phase 2 — users.is_lead column for clinician-lead admin access

Revision ID: p2a2dash01
Revises: p2c1l3t4r5p6
Create Date: 2026-04-26 11:00:00.000000

Phase 2 item 2 (Admin Dashboard + Operational Metrics):
docs/chartnav/closure/PHASE_B_Admin_Dashboard_and_Operational_Metrics.md

Adds an `is_lead` boolean to the users table so a clinician can be
explicitly designated a clinician-lead. The dashboard route uses
this attribute to allow `clinician AND is_lead = TRUE` callers
through, while keeping general clinicians, reviewers, technicians,
biller-coders, and front-desk users out (per spec §3 and §4
role-gating tests).

Truth limitation: the attribute is operator-controlled and lives
on the user row. We do NOT introduce a separate roles table or a
per-permission ACL system in Phase B. An admin grants the lead
attribute the same way they grant other user fields.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2a2dash01"
down_revision: Union[str, Sequence[str], None] = "p2c1l3t4r5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "is_lead", sa.Boolean(),
                server_default=sa.text("0"), nullable=False,
                comment="If True for a clinician, this user is a "
                        "clinician-lead and may view the admin dashboard.",
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_lead")
