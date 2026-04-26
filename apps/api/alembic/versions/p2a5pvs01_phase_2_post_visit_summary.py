"""phase 2 — post_visit_summaries

Revision ID: p2a5pvs01
Revises: p2a4msg01
Create Date: 2026-04-26 17:00:00.000000

Phase 2 item 5 of the closure plan:
docs/chartnav/closure/PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary.md

Adds a single table that closes the post-visit-summary acceptance
criteria:

  post_visit_summaries
    One row per signed note version. Carries the rendered PDF
    blob, a single-use unauth read-link token (HMAC-SHA256 hashed
    in storage), and an expires_at (30 days per spec §3). Re-
    generation against the same note_version_id is idempotent and
    returns the existing row.

Truth limitations preserved (spec §9):
  - This is NOT a HIPAA-conforming patient portal. It is a read-
    only view of a single visit behind a time-boxed token.
  - Token is not an identity binding. Anyone with the link can
    open the summary until it expires.
  - Plain-language assessment is rule-based, not LLM-generated.
  - We do not capture per-patient view audit beyond the first GET.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2a5pvs01"
down_revision: Union[str, Sequence[str], None] = "p2a4msg01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_visit_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "note_version_id", sa.Integer(), nullable=False, unique=True,
            comment="One summary per signed note version. Re-render "
                    "is idempotent.",
        ),
        sa.Column(
            "rendered_pdf_storage_ref", sa.String(length=255), nullable=False,
        ),
        sa.Column(
            "pdf_bytes", sa.LargeBinary(), nullable=False,
            comment="Rendered PDF blob; single page, plain-text body.",
        ),
        sa.Column(
            "read_link_token_hash", sa.String(length=128), nullable=False,
            unique=True,
            comment="HMAC-SHA256 of the raw token; raw is shown ONCE "
                    "to the staff member who generated it.",
        ),
        sa.Column(
            "expires_at", sa.DateTime(), nullable=False,
            comment="30-day expiry per spec §3.",
        ),
        sa.Column(
            "first_viewed_at", sa.DateTime(), nullable=True,
        ),
        sa.Column(
            "delivered_via", sa.String(length=32), nullable=True,
            comment="download | email_stub | sms_stub",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("post_visit_summaries")
