"""phase A — encounter templates: add encounters.template_key

Revision ID: f1g2t3p4q5r6
Revises: f1r2e3m4i5n6
Create Date: 2026-04-24 12:00:00.000000

Phase A item 1 of the closure plan:
docs/chartnav/closure/PHASE_A_Ophthalmology_Encounter_Templates.md

Adds a `template_key` column to the encounters table so every encounter
is anchored to one of the four ChartNav-curated ophthalmology templates
(retina, glaucoma, anterior_segment_cataract, general_ophthalmology).

Default value is `general_ophthalmology` so legacy rows are preserved
without forcing a backfill or a NULL-handling branch in the orchestrator.

Truth limitation preserved verbatim from the spec:
  Templates are NOT clinically validated until the practicing-
  ophthalmologist advisor sign-off is recorded under
  docs/chartnav/clinical/template_review.md. Code surfaces an
  advisor-review banner until that signature exists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1g2t3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "f1r2e3m4i5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "encounters",
        sa.Column(
            "template_key",
            sa.String(length=64),
            nullable=False,
            server_default="general_ophthalmology",
            comment=(
                "ChartNav-curated ophthalmology template key. One of: "
                "'retina', 'glaucoma', 'anterior_segment_cataract', "
                "'general_ophthalmology'. Drives section order and "
                "required-findings flags in the SOAP draft. NOT a "
                "clinical-validation marker."
            ),
        ),
    )
    op.create_index(
        "ix_encounters_template_key",
        "encounters",
        ["template_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_encounters_template_key", table_name="encounters")
    with op.batch_alter_table("encounters") as batch:
        batch.drop_column("template_key")
