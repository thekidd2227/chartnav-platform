"""ai_governance_log — append-only audit trail for AI calls

Revision ID: e1f2a3041506
Revises: e1f2a3041505
Create Date: 2026-04-29 10:00:00.000000

Every AI provider call writes one row here. Prompt and output text are
never stored — only SHA-256 hashes. `security_events` is a JSON-encoded
list of {event_id, type, detail, severity, timestamp} appended over the
record's lifetime.

Org-scoped: every row carries `organization_id`. Routes filter by it;
cross-org reads are blocked at the query layer. Human-review fields are
the only mutable surface after insert.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041506"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041505"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_governance_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column("organization_id", sa.Integer(), nullable=False, index=True),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="ibm_watsonx"),
        sa.Column("model_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("use_case", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("output_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "phi_redaction_status", sa.String(length=32),
            nullable=False, server_default="not_checked",
        ),
        sa.Column(
            "human_review_required", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "human_review_status", sa.String(length=32),
            nullable=False, server_default="pending",
        ),
        sa.Column("human_reviewer_id", sa.Integer(), nullable=True),
        sa.Column("human_review_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("human_review_notes", sa.Text(), nullable=True),
        sa.Column(
            "security_events", sa.Text(),
            nullable=False, server_default="[]",
            comment="JSON-encoded list of security event dicts",
        ),
        sa.Column("workflow_id", sa.Integer(), nullable=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("patient_identifier", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_ai_governance_log_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_ai_governance_log_user",
        ),
        sa.ForeignKeyConstraint(
            ["human_reviewer_id"], ["users.id"],
            name="fk_ai_governance_log_reviewer",
        ),
    )
    op.create_index(
        "ix_ai_governance_log_created_at",
        "ai_governance_log",
        ["created_at"],
    )
    op.create_index(
        "ix_ai_governance_log_org_created",
        "ai_governance_log",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_ai_governance_log_review_status",
        "ai_governance_log",
        ["human_review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_governance_log_review_status", table_name="ai_governance_log")
    op.drop_index("ix_ai_governance_log_org_created", table_name="ai_governance_log")
    op.drop_index("ix_ai_governance_log_created_at", table_name="ai_governance_log")
    op.drop_table("ai_governance_log")
