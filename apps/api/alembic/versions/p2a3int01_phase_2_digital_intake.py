"""phase 2 — digital intake (intake_tokens + intake_submissions)

Revision ID: p2a3int01
Revises: p2a2dash01
Create Date: 2026-04-26 13:00:00.000000

Phase 2 item 3 of the closure plan:
docs/chartnav/closure/PHASE_B_Digital_Intake.md

Adds two tables that close the digital-intake acceptance criteria:

  intake_tokens       — staff-issued, single-use, time-boxed tokens
                         the patient redeems on the unauthenticated
                         /intake/{token} surface. We store ONLY the
                         token hash; the raw token is shown to staff
                         exactly once at issuance time.

  intake_submissions  — patient-submitted JSON payload bound to a
                         token; staff reviews and either accepts
                         (creates a draft patient + draft encounter)
                         or rejects with an optional reason.

Truth limitations preserved verbatim from the spec §9:
- This is NOT a portal. Patients cannot log in, view past
  submissions, or edit a submitted form.
- No identity verification beyond possession of the token. A
  shared link is a shared capability; operators must treat tokens
  as semi-sensitive.
- No HIPAA audit-level identity binding occurs at the patient side;
  the accepting staff member remains the accountable party in
  workflow_events.
- Accepted data is treated as patient self-report until the
  clinician confirms during the visit.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2a3int01"
down_revision: Union[str, Sequence[str], None] = "p2a2dash01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intake_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "token_hash", sa.String(length=128), nullable=False,
            unique=True,
            comment="HMAC-SHA256 of the raw token. The raw token is "
                    "shown to staff exactly once at issuance.",
        ),
        sa.Column(
            "patient_identifier_candidate", sa.String(length=255),
            nullable=True,
            comment="Optional staff hint (e.g. PT-1234) so the staff "
                    "queue can group submissions; NOT echoed in any "
                    "public-route error response.",
        ),
        sa.Column(
            "expires_at", sa.DateTime(), nullable=False,
            comment="Tokens expire after 72 hours per spec §3.",
        ),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_by_user_id", sa.Integer(), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )

    op.create_table(
        "intake_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "token_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "payload_json", sa.Text(), nullable=False,
            comment="JSON body of the submitted intake form. NEVER "
                    "echoed in error responses.",
        ),
        sa.Column(
            "submitted_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=32), nullable=False,
            server_default=sa.text("'pending_review'"),
            comment="pending_review | accepted | rejected",
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "accepted_patient_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "accepted_encounter_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "reviewed_by_user_id", sa.Integer(), nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["token_id"], ["intake_tokens.id"],
            name="fk_intake_submissions_token",
        ),
    )


def downgrade() -> None:
    op.drop_table("intake_submissions")
    op.drop_table("intake_tokens")
