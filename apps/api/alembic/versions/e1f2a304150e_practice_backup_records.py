"""practice backup records

Revision ID: e1f2a304150e
Revises: e1f2a304150d
Create Date: 2026-04-22 09:00:00.000000

Phase 58 — practice backup / restore / reinstall recovery.

Adds a small audit table recording WHEN a backup bundle was issued
and WHO issued it. The bundle bytes themselves are NOT persisted to
the server — the operator downloads them via the browser to a
location outside the app so a data-loss event cannot destroy both
live data AND the backup. This table holds the metadata only:

  - organization_id
  - created_by_user_id + email
  - created_at
  - schema_version  (alembic head at issuance time)
  - bundle_version  (backup-format version)
  - artifact_bytes_size
  - artifact_hash_sha256
  - summary counts (encounters, note_versions, users)
  - optional operator note

Restore operations are also recorded here with event_type='restore'
so the history surfaces both sides of the lifecycle.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a304150e"
down_revision: Union[str, Sequence[str], None] = "e1f2a304150d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "practice_backup_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "event_type",
            sa.String(length=24),
            nullable=False,
            comment="'backup_created' | 'restore_applied'.",
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_by_email",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "bundle_version",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=32),
            nullable=False,
            comment="Alembic head at the time the record was written.",
        ),
        sa.Column(
            "artifact_bytes_size",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "artifact_hash_sha256",
            sa.String(length=64),
            nullable=True,
            comment=(
                "SHA-256 of the canonical backup bundle. For "
                "restore_applied rows this is the hash of the bundle "
                "that was applied."
            ),
        ),
        sa.Column(
            "encounter_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "note_version_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "user_count",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.String(length=500),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_practice_backup_records_org_id",
        "practice_backup_records",
        ["organization_id", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_practice_backup_records_org_id",
        table_name="practice_backup_records",
    )
    op.drop_table("practice_backup_records")
