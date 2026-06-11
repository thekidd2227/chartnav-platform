"""Phase 91 — Unified Ophthalmology Workspace Engine.

Adds two closed-allowlist columns to ``encounters`` so the unified
workspace state engine can deterministically project visit-mode and
eye-linked laterality without inferring either signal.

  * ``visit_mode`` — closed allowlist (CHECK):
      intake / surgical_pre_op / post_op / follow_up / lab_review /
      unscheduled. Default ``unscheduled`` so existing encounters
      stay safe.
  * ``active_laterality`` — closed allowlist (CHECK):
      OD / OS / OU / NA. Default ``NA``.

This phase is workflow orchestration only. ChartNav does NOT
auto-classify the visit mode, does NOT autonomously select an eye,
does NOT add clinical intelligence, and does NOT generate diagnoses.
Both columns are provider-driven via PATCH endpoints.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "g5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VISIT_MODES = (
    "intake",
    "surgical_pre_op",
    "post_op",
    "follow_up",
    "lab_review",
    "unscheduled",
)
_ACTIVE_LATERALITIES = ("OD", "OS", "OU", "NA")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.add_column(
            sa.Column(
                "visit_mode",
                sa.String(length=24),
                nullable=False,
                server_default="unscheduled",
            )
        )
        batch.add_column(
            sa.Column(
                "active_laterality",
                sa.String(length=4),
                nullable=False,
                server_default="NA",
            )
        )
        batch.create_check_constraint(
            "ck_encounters_visit_mode_allowed",
            f"visit_mode IN ({_csv(_VISIT_MODES)})",
        )
        batch.create_check_constraint(
            "ck_encounters_active_laterality_allowed",
            f"active_laterality IN ({_csv(_ACTIVE_LATERALITIES)})",
        )
        batch.create_index(
            "ix_encounters_visit_mode", ["visit_mode"]
        )


def downgrade() -> None:
    with op.batch_alter_table("encounters") as batch:
        batch.drop_index("ix_encounters_visit_mode")
        batch.drop_constraint(
            "ck_encounters_active_laterality_allowed", type_="check"
        )
        batch.drop_constraint(
            "ck_encounters_visit_mode_allowed", type_="check"
        )
        batch.drop_column("active_laterality")
        batch.drop_column("visit_mode")
