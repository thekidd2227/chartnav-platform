"""final physician approval governance (wave 7)

Revision ID: e1f2a3041509
Revises: e1f2a3041508
Create Date: 2026-04-21 06:00:00.000000

Phase 52 — clinical approval + record finalization wave 7.

Adds the smallest authoritative model needed for real, server-side
physician final-approval of a signed note:

On `users`:

  - is_authorized_final_signer BOOLEAN NOT NULL DEFAULT FALSE
      A coarse role ("clinician") is not sufficient to authorize
      final approval; an org must explicitly designate which
      clinicians may perform final approval. Defaults to FALSE so
      no existing user silently gains the privilege on upgrade.
      Admins MAY also be flagged — the flag is independent of role.

On `note_versions`:

  - final_approval_status VARCHAR(16) NULL
      One of "pending", "approved", "invalidated". NULL on rows
      that predate Wave 7 or do not require final approval.
      Populated lazily: when a note transitions into `signed` the
      route sets it to "pending" (so the UI can show the pending
      state); when final approval succeeds it flips to "approved";
      when an amendment supersedes the signed row the approval is
      flipped to "invalidated".

  - final_approved_at DATETIME(tz) NULL
      Set when the authorized doctor types their name and the
      server confirms a case-sensitive exact match.

  - final_approved_by_user_id INTEGER NULL
      FK to users.id. Frozen at final-approval time; does not
      drift if the user is later deactivated or renamed.

  - final_approval_signature_text VARCHAR(255) NULL
      The EXACT string the doctor typed at approval time. Stored
      verbatim for audit; a later rename of `users.full_name`
      cannot rewrite what the doctor actually typed.

  - final_approval_invalidated_at DATETIME(tz) NULL
  - final_approval_invalidated_reason VARCHAR(500) NULL
      Populated when an amendment (or other governed path)
      invalidates a prior approval. The `final_approved_at` stamp
      is NOT cleared — the invalidation is additive so the audit
      trail still shows that approval once existed.

No existing columns are dropped. No CHECK is added on the new
status column at this revision — the application enforces the
allowed set. Adding a DB-level CHECK is a Wave 8+ concern once the
status vocabulary has stabilised in production.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041509"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041508"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ----------------------------------------------------
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "is_authorized_final_signer",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment=(
                    "When true, this user may perform final physician "
                    "approval on signed notes in their org. Independent "
                    "of role; defaults to false so no user is silently "
                    "granted the privilege on upgrade."
                ),
            )
        )

    # --- note_versions --------------------------------------------
    with op.batch_alter_table("note_versions") as batch:
        batch.add_column(
            sa.Column(
                "final_approval_status",
                sa.String(length=16),
                nullable=True,
                comment=(
                    "One of 'pending', 'approved', 'invalidated'. "
                    "NULL on rows that predate wave 7 or do not "
                    "require final approval."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "final_approved_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "final_approved_by_user_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "final_approval_signature_text",
                sa.String(length=255),
                nullable=True,
                comment=(
                    "The exact string the doctor typed at approval "
                    "time, case-preserved and verbatim. Independent "
                    "of users.full_name drift."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "final_approval_invalidated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "final_approval_invalidated_reason",
                sa.String(length=500),
                nullable=True,
            )
        )

    op.create_index(
        "ix_note_versions_final_approval_status",
        "note_versions",
        ["final_approval_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_note_versions_final_approval_status",
        table_name="note_versions",
    )
    with op.batch_alter_table("note_versions") as batch:
        batch.drop_column("final_approval_invalidated_reason")
        batch.drop_column("final_approval_invalidated_at")
        batch.drop_column("final_approval_signature_text")
        batch.drop_column("final_approved_by_user_id")
        batch.drop_column("final_approved_at")
        batch.drop_column("final_approval_status")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_authorized_final_signer")
