"""evidence sink delivery + export snapshots + chain seals

Revision ID: e1f2a304150c
Revises: e1f2a304150b
Create Date: 2026-04-22 07:00:00.000000

Phase 56 — external evidence integrity + immutable audit sink.

Adds three things, all additive:

1. Per-event sink delivery columns on `note_evidence_events`:
     - sink_status        "sent" | "failed" | "skipped" | NULL
     - sink_attempted_at  DATETIMEtz
     - sink_error         short reason on failure

   NULL `sink_status` means the row predates Phase 56 or the sink
   was disabled when the event fired — both are legitimate and
   distinguishable from an actual failure.

2. A new `note_export_snapshots` table.

   When an export succeeds, the platform persists the canonical
   artifact bytes + SHA-256 hash + a link back to the evidence
   chain event that recorded the export. This gives a point-in-time
   snapshot of what was actually handed off — independent of any
   later amendment or fingerprint drift on the source row.

3. A new `evidence_chain_seals` table.

   A manual checkpointing mechanism: a security admin can "seal"
   the current tip of the evidence chain, persisting the tip
   event_hash + event count + a sealed_at timestamp. Subsequent
   chain verification can compare the current tip to the most
   recent seal and confirm the chain has not been rewound.

Downgrade drops the tables and the columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a304150c"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- (1) Per-event sink delivery state -----------------------------
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.add_column(
            sa.Column(
                "sink_status",
                sa.String(length=16),
                nullable=True,
                comment=(
                    "External evidence-sink delivery status for this "
                    "event: 'sent' | 'failed' | 'skipped' | NULL. "
                    "NULL when sink was disabled / row predates Phase 56."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "sink_attempted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "sink_error",
                sa.String(length=500),
                nullable=True,
                comment="Short error reason on sink_status='failed'.",
            )
        )
    op.create_index(
        "ix_note_evidence_events_sink_status",
        "note_evidence_events",
        ["organization_id", "sink_status"],
    )

    # --- (2) Export snapshot table -------------------------------------
    op.create_table(
        "note_export_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "note_version_id",
            sa.Integer(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "encounter_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "evidence_chain_event_id",
            sa.Integer(),
            nullable=True,
            comment=(
                "FK to note_evidence_events.id — the note_exported "
                "event that this snapshot corresponds to. NULL only if "
                "the chain write failed (best-effort)."
            ),
        ),
        sa.Column(
            "artifact_json",
            sa.Text(),
            nullable=False,
            comment=(
                "Canonical JSON artifact bytes captured at export time. "
                "Stored compact (sorted keys) so the hash is "
                "reproducible."
            ),
        ),
        sa.Column(
            "artifact_hash_sha256",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of the canonical artifact bytes.",
        ),
        sa.Column(
            "content_fingerprint",
            sa.String(length=64),
            nullable=True,
            comment=(
                "Note body fingerprint at export time. Denormalized "
                "from the note row so the snapshot is self-contained."
            ),
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "issued_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "issued_by_email",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_note_export_snapshots_note",
        "note_export_snapshots",
        ["note_version_id", "id"],
    )

    # --- (3) Chain seals -----------------------------------------------
    op.create_table(
        "evidence_chain_seals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tip_event_id",
            sa.Integer(),
            nullable=False,
            comment="note_evidence_events.id of the chain tip at seal time.",
        ),
        sa.Column(
            "tip_event_hash",
            sa.String(length=64),
            nullable=False,
            comment="event_hash of the tip at seal time.",
        ),
        sa.Column(
            "event_count",
            sa.Integer(),
            nullable=False,
            comment=(
                "Total events in this org at seal time. Consumers use "
                "this to detect backward rewinds."
            ),
        ),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "sealed_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "sealed_by_email",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.String(length=500),
            nullable=True,
            comment="Optional human-readable note on what was being sealed.",
        ),
    )
    op.create_index(
        "ix_evidence_chain_seals_org_id",
        "evidence_chain_seals",
        ["organization_id", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_chain_seals_org_id", table_name="evidence_chain_seals",
    )
    op.drop_table("evidence_chain_seals")
    op.drop_index(
        "ix_note_export_snapshots_note", table_name="note_export_snapshots",
    )
    op.drop_table("note_export_snapshots")
    op.drop_index(
        "ix_note_evidence_events_sink_status",
        table_name="note_evidence_events",
    )
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.drop_column("sink_error")
        batch.drop_column("sink_attempted_at")
        batch.drop_column("sink_status")
