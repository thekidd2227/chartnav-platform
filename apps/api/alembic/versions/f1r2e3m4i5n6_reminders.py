"""reminders — clinician follow-up + recall nudges

Revision ID: f1r2e3m4i5n6
Revises: e1f2a304150f
Create Date: 2026-04-22 21:00:00.000000

Adds a lightweight `reminders` table so the calendar surface has a
first-class "what still needs attention" feed distinct from
encounter scheduling. A reminder is a tiny work item that can, but
does not have to, attach to a specific encounter or patient — it
is org-scoped, has a due_at, a status, and a short title/body.

Design notes:
- Status is a string with values {pending, completed, cancelled}.
  We deliberately don't enum-type it so test fixtures can introduce
  new values without a schema migration.
- `encounter_id` and `patient_identifier` are both nullable so a
  reminder can be attached to (a) a specific encounter, (b) a
  specific patient without a booked encounter yet, or (c) nothing
  in particular (a free-floating operational nudge).
- Completion is tracked with both a boolean-ish status and the
  user_id of whoever completed it, mirroring the pattern we use on
  `note_versions.signed_by_user_id`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1r2e3m4i5n6"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
            comment="org-scoped; ensure_same_org is enforced at the route",
        ),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=True, index=True,
            comment="optional link to a specific encounter",
        ),
        sa.Column(
            "patient_identifier", sa.String(length=64), nullable=True,
            index=True,
            comment="optional local patient MRN — free-form string",
        ),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "due_at", sa.DateTime(timezone=False), nullable=False,
            index=True,
            comment="calendar-visible due date/time",
        ),
        sa.Column(
            "status", sa.String(length=24), nullable=False,
            server_default="pending",
            comment="'pending' | 'completed' | 'cancelled'",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "completed_by_user_id", sa.Integer(), nullable=True,
            comment="users.id of the clinician who completed it",
        ),
        sa.Column(
            "created_by_user_id", sa.Integer(), nullable=False,
            comment="users.id of the reminder author",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=False),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_reminders_org_due",
        "reminders", ["organization_id", "due_at"],
    )
    op.create_index(
        "ix_reminders_org_status_due",
        "reminders", ["organization_id", "status", "due_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reminders_org_status_due", table_name="reminders")
    op.drop_index("ix_reminders_org_due", table_name="reminders")
    op.drop_table("reminders")
