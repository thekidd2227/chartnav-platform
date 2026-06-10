"""Phase 88 — Imaging Metadata Review Linkage.

Extends the existing `imaging_studies` table (introduced in Phase
21B) with three optional device-and-source provenance columns:

  * ``device_manufacturer`` — provider-entered free-form text
                              (e.g. "Heidelberg", "Zeiss"). Optional.
  * ``device_model``        — provider-entered free-form text
                              (e.g. "Spectralis", "Cirrus 5000"). Optional.
  * ``source_system``       — provider-entered free-form text
                              (e.g. "OCT cart 1", "External PDF import").
                              Optional.

This phase is **metadata + review linkage only**. The table already
records modality, eye, status, captured_at, reviewed_by_user_id,
reviewed_at — Phase 88 reuses those columns and surfaces them through
new encounter-scoped read and PATCH endpoints.

Hard rules expressed by the schema:

  * All three new columns are nullable. Existing rows remain valid.
  * No CHECK enum on these columns — manufacturer/model/source_system
    are free-form provider-entered strings, not closed allowlists. The
    application layer caps length (128 chars) at validation time.
  * Org isolation is unchanged — every row already carries
    ``organization_id`` and the route layer enforces 404-on-cross-org.

This migration does NOT:

  * add image binary storage,
  * add DICOM / HL7 / live device interfaces,
  * add OCR or image interpretation,
  * autonomously classify modality or eye.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("imaging_studies") as batch:
        batch.add_column(
            sa.Column(
                "device_manufacturer", sa.String(length=128), nullable=True
            )
        )
        batch.add_column(
            sa.Column("device_model", sa.String(length=128), nullable=True)
        )
        batch.add_column(
            sa.Column("source_system", sa.String(length=128), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("imaging_studies") as batch:
        batch.drop_column("source_system")
        batch.drop_column("device_model")
        batch.drop_column("device_manufacturer")
