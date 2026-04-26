"""phase A — encounter revisions + attestations

Revision ID: s3c4h5g6a7b8
Revises: r2b3a4c5e6f7
Create Date: 2026-04-24 13:00:00.000000

Phase A item 3 of the closure plan:
docs/chartnav/closure/PHASE_A_Structured_Charting_and_Attestation.md

Adds two tables that close the structured-charting + attestation
acceptance criteria:

  encounter_revisions     — append-only field-level edit history.
                             One row per (encounter_id, field_path)
                             mutation, with before/after JSON and
                             actor identity.

  encounter_attestations  — first-class attestation row written at
                             sign time. Carries the typed name, the
                             attestation text, and a deterministic
                             snapshot hash of the canonicalized
                             encounter JSON so the attestation is
                             auditable independently of the note body.

Truth limitations preserved verbatim from the spec:
- Immutability is enforced at the application layer, not at the
  database layer. A direct DB write bypasses it. This is standard
  for SQLite-backed pilots; production Postgres deployments should
  add row-level security or a deny-by-default trigger — tracked
  separately.
- `encounter_snapshot_hash` is a tamper-evidence signal, not a legal
  trusted timestamp. We do not (yet) anchor it to an external TSA.
- Edit history is ChartNav-internal. It does not retroactively apply
  to edits made in an external EHR in `integrated_readthrough` mode.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s3c4h5g6a7b8"
down_revision: Union[str, Sequence[str], None] = "r2b3a4c5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounter_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
            comment="encounters.id this revision applies to",
        ),
        sa.Column(
            "actor_user_id", sa.Integer(), nullable=False,
            comment="users.id of the actor who made the change",
        ),
        sa.Column(
            "field_path", sa.String(length=128), nullable=False,
            comment="dotted field path, e.g. 'template_key' or "
                    "'assessment_struct.plan'",
        ),
        sa.Column(
            "before_json", sa.Text(), nullable=True,
            comment="JSON snapshot of the value before the change",
        ),
        sa.Column(
            "after_json", sa.Text(), nullable=True,
            comment="JSON snapshot of the value after the change",
        ),
        sa.Column(
            "reason", sa.Text(), nullable=True,
            comment="optional free-text (e.g. 'reviewer correction')",
        ),
        sa.Column(
            "changed_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_encounter_revisions_changed_at",
        "encounter_revisions",
        ["encounter_id", "changed_at"],
    )

    op.create_table(
        "encounter_attestations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False,
            comment="encounters.id this attestation belongs to; one "
                    "per encounter, enforced by UNIQUE",
        ),
        sa.Column(
            "attested_by_user_id", sa.Integer(), nullable=False,
            comment="users.id of the signer",
        ),
        sa.Column(
            "typed_name", sa.String(length=255), nullable=False,
            comment="exact name typed by the signer at sign time",
        ),
        sa.Column(
            "attestation_text", sa.Text(), nullable=False,
            comment="canonical attestation language presented at sign",
        ),
        sa.Column(
            "encounter_snapshot_hash", sa.String(length=128), nullable=False,
            comment="sha256 of canonicalized encounter JSON at sign time; "
                    "tamper-evidence, NOT a legal trusted timestamp",
        ),
        sa.Column(
            "attested_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.UniqueConstraint(
            "encounter_id",
            name="uq_encounter_attestations_encounter_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("encounter_attestations")
    op.drop_index(
        "ix_encounter_revisions_changed_at",
        table_name="encounter_revisions",
    )
    op.drop_table("encounter_revisions")
