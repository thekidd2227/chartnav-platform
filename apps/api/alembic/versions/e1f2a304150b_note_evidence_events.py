"""note evidence events (wave-evidence)

Revision ID: e1f2a304150b
Revises: e1f2a304150a
Create Date: 2026-04-22 05:00:00.000000

Phase 55 — immutable audit and external evidence hardening.

Adds a dedicated, append-only evidence log that sits alongside the
general-purpose `security_audit_events` table. The general table is
append-only-by-convention and records everything the platform does;
this new table is narrower — it records ONLY the governance
transitions that need to be reconstructible in a compliance or
dispute scenario:

  - note signed
  - note final-approved
  - note exported
  - note amended (both sides: original invalidated, amendment born)
  - note final-approval invalidated (separate event from amendment so
    programmatic invalidations remain visible)

Each row is hash-chained to the previous row in the same organization.
Tampering with any row's canonical fields breaks the chain from that
row forward and can be detected by re-computing `event_hash` from
`prev_event_hash` + the canonical content.

The chain is org-scoped (not global) so multi-tenant isolation is
preserved: one org's chain can be inspected / re-verified without
decrypting another org's rows.

Downgrade drops the table. No other table is touched.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a304150b"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_evidence_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
            comment=(
                "Owning org. Chain is scoped per-org so cross-tenant "
                "isolation holds when auditing."
            ),
        ),
        sa.Column(
            "note_version_id",
            sa.Integer(),
            nullable=False,
            index=True,
            comment="Target note_versions.id at the time of the event.",
        ),
        sa.Column(
            "encounter_id",
            sa.Integer(),
            nullable=False,
            comment="Denormalized for fast per-encounter evidence queries.",
        ),
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
            index=True,
            comment=(
                "One of 'note_signed', 'note_final_approved', "
                "'note_exported', 'note_amended_source', "
                "'note_amended_new', 'note_final_approval_invalidated'."
            ),
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            nullable=True,
            comment="User that caused the event. Null only for system events.",
        ),
        sa.Column(
            "actor_email",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "draft_status",
            sa.String(length=32),
            nullable=True,
            comment="Canonical lifecycle state at event time.",
        ),
        sa.Column(
            "final_approval_status",
            sa.String(length=16),
            nullable=True,
            comment="Final-approval status at event time.",
        ),
        sa.Column(
            "content_fingerprint",
            sa.String(length=64),
            nullable=True,
            comment=(
                "SHA-256 of the note body frozen at sign time. Null when "
                "the event fires before a fingerprint exists."
            ),
        ),
        sa.Column(
            "detail_json",
            sa.Text(),
            nullable=True,
            comment=(
                "Additional event-specific context as JSON. e.g. amendment "
                "reason, invalidation cause, related note ids."
            ),
        ),
        sa.Column(
            "prev_event_hash",
            sa.String(length=64),
            nullable=True,
            comment=(
                "SHA-256 hex of the previous event_hash in this org's "
                "chain. Null only for the org's very first event."
            ),
        ),
        sa.Column(
            "event_hash",
            sa.String(length=64),
            nullable=False,
            comment=(
                "SHA-256 hex over the row's canonical fields plus "
                "prev_event_hash. Tampering with canonical fields breaks "
                "the chain from this row forward."
            ),
        ),
    )
    # Primary seek path for chain verification: (org, id) in order.
    op.create_index(
        "ix_note_evidence_events_org_id",
        "note_evidence_events",
        ["organization_id", "id"],
    )
    # Per-note evidence lookup.
    op.create_index(
        "ix_note_evidence_events_note_id",
        "note_evidence_events",
        ["note_version_id", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_note_evidence_events_note_id",
        table_name="note_evidence_events",
    )
    op.drop_index(
        "ix_note_evidence_events_org_id",
        table_name="note_evidence_events",
    )
    op.drop_table("note_evidence_events")
