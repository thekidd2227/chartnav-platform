"""provider_action_items — provider action review queue

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-05-05 19:00:00.000000

Phase 11. One row per provider-reviewable action suggestion.
ChartNav generates suggestions deterministically from existing chart
records; the provider explicitly Accepts, Dismisses, or Completes
them. This table never creates orders, sends referrals, messages
patients, or takes any clinical action. Lifecycle:

    suggested -> accepted -> completed
    suggested -> dismissed
    accepted  -> dismissed
    dismissed and completed are immutable terminal states.
    suggested -> completed is rejected (must accept first).

Audit metadata only — `title` and `reason` may contain clinical
context for provider display and are NEVER written to the audit log.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUSES = ("suggested", "accepted", "dismissed", "completed")
_PRIORITIES = ("low", "medium", "high")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "provider_action_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column(
            "source_type", sa.String(length=64), nullable=True,
            comment=(
                "Logical source category — e.g. 'scribe_session', "
                "'patient_summary', 'chart_artifact', 'pre_visit_brief'. "
                "Free-form by design (no FK)."
            ),
        ),
        sa.Column(
            "source_id", sa.Integer(), nullable=True,
            comment="Source row id (when applicable). No FK — sources span tables.",
        ),
        sa.Column(
            "action_type", sa.String(length=64), nullable=False,
            comment=(
                "e.g. review_retinal_tear_language, "
                "sign_unsigned_retinal_diagram, finalize_scribe_session. "
                "Always a review/consider/check task — never an order."
            ),
        ),
        sa.Column(
            "priority", sa.String(length=16),
            nullable=False, server_default="medium",
        ),
        sa.Column(
            "title", sa.String(length=255),
            nullable=False, server_default="",
            comment=(
                "Provider-facing short title. NEVER written to audit logs."
            ),
        ),
        sa.Column(
            "reason", sa.Text(),
            nullable=False, server_default="",
            comment=(
                "Provider-facing rationale. May reference clinical "
                "context. NEVER written to audit logs."
            ),
        ),
        sa.Column(
            "status", sa.String(length=16),
            nullable=False, server_default="suggested",
        ),
        sa.Column(
            "created_by_system", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "generated_batch_id", sa.String(length=64), nullable=True,
            comment="Stable id for items emitted by a single generate call.",
        ),
        sa.Column("accepted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("dismissed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_provider_action_items_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"],
            name="fk_provider_action_items_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_provider_action_items_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"], ["users.id"],
            name="fk_provider_action_items_accepted_by",
        ),
        sa.ForeignKeyConstraint(
            ["dismissed_by_user_id"], ["users.id"],
            name="fk_provider_action_items_dismissed_by",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_user_id"], ["users.id"],
            name="fk_provider_action_items_completed_by",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_STATUSES)})",
            name="ck_provider_action_items_status",
        ),
        sa.CheckConstraint(
            f"priority IN ({_csv(_PRIORITIES)})",
            name="ck_provider_action_items_priority",
        ),
    )
    op.create_index(
        "ix_provider_action_items_org_patient",
        "provider_action_items",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_provider_action_items_org_encounter",
        "provider_action_items",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_provider_action_items_org_status",
        "provider_action_items",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_provider_action_items_org_action_type",
        "provider_action_items",
        ["organization_id", "action_type"],
    )
    op.create_index(
        "ix_provider_action_items_org_priority",
        "provider_action_items",
        ["organization_id", "priority"],
    )
    op.create_index(
        "ix_provider_action_items_generated_batch_id",
        "provider_action_items",
        ["generated_batch_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_action_items_generated_batch_id",
        table_name="provider_action_items",
    )
    op.drop_index(
        "ix_provider_action_items_org_priority",
        table_name="provider_action_items",
    )
    op.drop_index(
        "ix_provider_action_items_org_action_type",
        table_name="provider_action_items",
    )
    op.drop_index(
        "ix_provider_action_items_org_status",
        table_name="provider_action_items",
    )
    op.drop_index(
        "ix_provider_action_items_org_encounter",
        table_name="provider_action_items",
    )
    op.drop_index(
        "ix_provider_action_items_org_patient",
        table_name="provider_action_items",
    )
    op.drop_table("provider_action_items")
