"""note lifecycle governance (wave 3)

Revision ID: e1f2a3041508
Revises: e1f2a3041507
Create Date: 2026-04-21 05:00:00.000000

Phase 49 — clinical governance wave 3.

Adds the columns required to turn the existing note lifecycle
into an enterprise-defensible audit trail:

  - reviewed_at / reviewed_by_user_id
      distinct signals from provider_review (the *workflow stage*).
      A reviewer who opens the note and explicitly attests review
      lands these columns. Sign is still the final act; review is
      an auditable gate in front of it.

  - content_fingerprint  (SHA-256 hex of note_text at sign time)
      Detects silent post-sign mutation of a "signed" row by
      anyone with DB access. Computed + written atomically on
      sign; compared on every read.

  - attestation_text
      The CMS-style provider attestation statement frozen at sign
      time. Not re-evaluated at read time — the text the signer
      actually attested to is what the record shows.

  - amended_at / amended_by_user_id / amended_from_note_id /
    amendment_reason
      When a signed note requires correction, the amendment
      service creates a NEW note_version linked back to the
      original via `amended_from_note_id`. The amendment row
      carries its own signing/attestation state.

  - superseded_at / superseded_by_note_id
      The original signed row is marked superseded the moment
      the amendment is itself signed. Both rows remain
      inspectable; exported systems see the supersession chain.

No existing columns are dropped. Existing pilot flow remains
unchanged for orgs that never exercise review / amendment paths
(the columns default to NULL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041508"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("note_versions") as batch:
        batch.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "content_fingerprint",
                sa.String(length=64),
                nullable=True,
                comment=(
                    "SHA-256 hex of note_text at sign time. Detects "
                    "silent post-sign mutation by anyone with DB access."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "attestation_text",
                sa.Text(),
                nullable=True,
                comment=(
                    "CMS-style provider attestation statement frozen at "
                    "sign time. Not re-evaluated at read time."
                ),
            )
        )
        batch.add_column(
            sa.Column("amended_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("amended_by_user_id", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "amended_from_note_id",
                sa.Integer(),
                nullable=True,
                comment=(
                    "When set, this row is an amendment — "
                    "`amended_from_note_id` points at the previous "
                    "signed note_versions.id."
                ),
            )
        )
        batch.add_column(
            sa.Column("amendment_reason", sa.String(length=500), nullable=True)
        )
        batch.add_column(
            sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "superseded_by_note_id",
                sa.Integer(),
                nullable=True,
                comment=(
                    "When set, this row was superseded by a newer "
                    "amendment. Value points at the amendment's "
                    "note_versions.id."
                ),
            )
        )

    # Lookup indexes — the amendment chain is walked on every note
    # read for the workspace UI, so the FK-style lookup should be
    # cheap.
    op.create_index(
        "ix_note_versions_amended_from",
        "note_versions",
        ["amended_from_note_id"],
    )
    op.create_index(
        "ix_note_versions_superseded_by",
        "note_versions",
        ["superseded_by_note_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_note_versions_superseded_by", table_name="note_versions")
    op.drop_index("ix_note_versions_amended_from", table_name="note_versions")
    with op.batch_alter_table("note_versions") as batch:
        batch.drop_column("superseded_by_note_id")
        batch.drop_column("superseded_at")
        batch.drop_column("amendment_reason")
        batch.drop_column("amended_from_note_id")
        batch.drop_column("amended_by_user_id")
        batch.drop_column("amended_at")
        batch.drop_column("attestation_text")
        batch.drop_column("content_fingerprint")
        batch.drop_column("reviewed_by_user_id")
        batch.drop_column("reviewed_at")
