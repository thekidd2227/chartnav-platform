"""evidence maturity columns — seals + sink retry + snapshot retention

Revision ID: e1f2a304150d
Revises: e1f2a304150c
Create Date: 2026-04-22 08:30:00.000000

Phase 57 — evidence maturity and compliance hardening.

Three additive migrations in one revision, all small:

1. `evidence_chain_seals` gains:
     - seal_hash_sha256       SHA-256 over the seal's canonical content
     - seal_signature_hex     optional HMAC over seal_hash_sha256
     - seal_signing_key_id    which keyring entry signed the seal
   These let seals be independently verified after they are written:
   a tampered seal row recomputes to a different hash, and a missing
   / wrong signature fails signature verification.

2. `note_evidence_events` gains:
     - sink_attempt_count     INTEGER NOT NULL DEFAULT 0
   Tracks how many times an operator has attempted external sink
   delivery for this row. Incremented ONLY on the retry endpoint;
   the initial append sets this to 1 on success and 1 on first
   failure so count reflects the number of physical attempts.

3. New column on `note_export_snapshots`:
     - artifact_purged_at     DATETIMEtz
     - artifact_purged_reason VARCHAR(500)
   A snapshot's heavy body (artifact_json) can be cleared on a
   retention sweep without dropping the row; the hash + linkage +
   issuer remain, and the purge stamp says when/why the body went
   away. This is the "soft-purge" path; a hard DELETE path is not
   added here because integrity references from evidence-chain
   events depend on the snapshot id existing.

No existing columns are dropped. Downgrade drops the new columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a304150d"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- (1) Seal integrity columns -----------------------------------
    with op.batch_alter_table("evidence_chain_seals") as batch:
        batch.add_column(
            sa.Column(
                "seal_hash_sha256",
                sa.String(length=64),
                nullable=True,
                comment=(
                    "SHA-256 over the seal's canonical payload "
                    "(org, tip_event_id, tip_event_hash, event_count, "
                    "sealed_at, sealed_by_*, note). Null on pre-Phase-57 "
                    "seals; always populated by the sealing route from "
                    "Phase 57 onward."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "seal_signature_hex",
                sa.String(length=128),
                nullable=True,
                comment=(
                    "Optional HMAC-SHA256 over seal_hash_sha256, emitted "
                    "when the org's signing mode is active."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "seal_signing_key_id",
                sa.String(length=64),
                nullable=True,
            )
        )

    # --- (2) Sink retry counter ---------------------------------------
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.add_column(
            sa.Column(
                "sink_attempt_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment=(
                    "Count of transport attempts against the external "
                    "evidence sink. The initial append sets this to 1; "
                    "the retry endpoint increments it."
                ),
            )
        )

    # --- (3) Snapshot soft-purge columns ------------------------------
    with op.batch_alter_table("note_export_snapshots") as batch:
        batch.add_column(
            sa.Column(
                "artifact_purged_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment=(
                    "When set, artifact_json has been cleared by a "
                    "retention sweep. The row itself is kept because "
                    "evidence-chain events may reference its id."
                ),
            )
        )
        batch.add_column(
            sa.Column(
                "artifact_purged_reason",
                sa.String(length=500),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("note_export_snapshots") as batch:
        batch.drop_column("artifact_purged_reason")
        batch.drop_column("artifact_purged_at")
    with op.batch_alter_table("note_evidence_events") as batch:
        batch.drop_column("sink_attempt_count")
    with op.batch_alter_table("evidence_chain_seals") as batch:
        batch.drop_column("seal_signing_key_id")
        batch.drop_column("seal_signature_hex")
        batch.drop_column("seal_hash_sha256")
