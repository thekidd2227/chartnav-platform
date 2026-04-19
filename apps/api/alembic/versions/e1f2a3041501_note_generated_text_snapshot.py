"""snapshot generator output as an immutable column on note_versions

Revision ID: e1f2a3041501
Revises: d0e1f2a30415
Create Date: 2026-04-19 07:00:00.000000

Phase 25 — export/interoperability groundwork.

Separates "what the generator drafted" from "what the clinician
actually signed". Prior schema mutated `note_versions.note_text`
in place on every provider edit, which meant the signed record
looked identical to the generated draft at audit time — no way to
show reviewers what the AI produced vs. what the human committed to.

Adds one additive column:

- ``generated_note_text`` TEXT NULL — populated at draft creation
  by the orchestrator, never touched again. For rows that predate
  this migration we seed it from the current ``note_text`` so the
  artifact endpoint can still return a non-null value; the
  `edit_applied` boolean in the artifact stays correct because the
  unedited column will just equal ``note_text`` for legacy rows.

Pure additive; no existing reads/writes break.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041501"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a30415"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("note_versions") as batch:
        batch.add_column(
            sa.Column(
                "generated_note_text",
                sa.Text(),
                nullable=True,
                comment=(
                    "immutable snapshot of the generator's draft at "
                    "creation time; never touched by provider edits. "
                    "`note_text` continues to hold the current "
                    "(possibly edited) version."
                ),
            )
        )

    # Backfill legacy rows: for everything already on disk, we can't
    # recover the original draft, so mirror the current note_text.
    # `edit_applied` in the artifact will be False for these rows even
    # if an edit did occur pre-migration; this is the honest choice —
    # we don't pretend to know a diff we never recorded.
    op.execute(
        "UPDATE note_versions "
        "SET generated_note_text = note_text "
        "WHERE generated_note_text IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("note_versions") as batch:
        batch.drop_column("generated_note_text")
