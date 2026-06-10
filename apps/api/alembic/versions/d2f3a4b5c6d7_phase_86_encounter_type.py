"""Phase 86 — Subspecialty Adaptive Workspace.

Adds a closed-allowlist ``encounter_type`` column to the ``encounters``
table so the Workspace Profile Resolver can deterministically pick
the right Overview-tab profile (panel ordering + collapse state).

Hard rules expressed in the schema:

  * ``encounter_type`` is a closed allowlist (CHECK):
    ``retina`` / ``glaucoma`` / ``cataract`` / ``comprehensive``.
  * Default value is ``comprehensive`` (server default) so existing
    encounters land on the balanced profile without inference.

This phase does NOT autonomously classify encounters. Subspecialty
selection is provider-driven: the value either rides in on the
external bridge payload or is patched via the Phase 86 endpoint.
ChartNav does NOT infer subspecialty from imaging, vitals, or any
clinical artifact — the column is purely workflow metadata used to
reorder existing surfaces.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "c1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ENCOUNTER_TYPES = ("retina", "glaucoma", "cataract", "comprehensive")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.add_column(
            sa.Column(
                "encounter_type",
                sa.String(length=24),
                nullable=False,
                server_default="comprehensive",
            )
        )
        batch.create_check_constraint(
            "ck_encounters_type_allowed",
            f"encounter_type IN ({_csv(_ENCOUNTER_TYPES)})",
        )
        batch.create_index(
            "ix_encounters_type", ["encounter_type"]
        )


def downgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.drop_index("ix_encounters_type")
        batch.drop_constraint(
            "ck_encounters_type_allowed", type_="check"
        )
        batch.drop_column("encounter_type")
