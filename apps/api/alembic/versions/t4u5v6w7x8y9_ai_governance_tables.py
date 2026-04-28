"""AI governance tables — watsonx + Guardium scaffold

Revision ID: t4u5v6w7x8y9
Revises: s3c4h5g6a7b8
Create Date: 2026-04-27 21:00:00.000000

Adds six tables for ChartNav's internal AI governance layer:

  ai_use_cases          — inventory of every AI capability
  ai_model_registry     — model/provider version tracking
  ai_prompt_templates   — versioned prompt template registry
  ai_output_audit       — one row per AI output (hashes only, no raw PHI)
  ai_human_reviews      — human review decisions on AI outputs
  ai_security_events    — prompt injection, jailbreak, policy events

All tables:
  - are org-scoped (org_id) where applicable
  - include created_at
  - never store raw PHI (hashes/references only)
  - use TEXT UUIDs as primary keys for SQLite + Postgres portability

See docs/security/ai-governance-architecture.md for field-level docs.
"""

from alembic import op
import sqlalchemy as sa

revision = "t4u5v6w7x8y9"
down_revision = "s3c4h5g6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_use_cases",
        sa.Column("use_case_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("model_provider", sa.Text, nullable=False),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("phi_exposure", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("output_type", sa.Text, nullable=False, server_default="text"),
        sa.Column("requires_human_review", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("clinical_disclaimer_required", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text, nullable=False),
    )

    op.create_table(
        "ai_model_registry",
        sa.Column("model_id", sa.Text, primary_key=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("version_tag", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("deprecated_at", sa.Text, nullable=True),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("provider", "model_name", "version_tag",
                            name="uq_ai_model_registry_provider_name_version"),
    )

    op.create_table(
        "ai_prompt_templates",
        sa.Column("template_id", sa.Text, primary_key=True),
        sa.Column("use_case_id", sa.Text,
                  sa.ForeignKey("ai_use_cases.use_case_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("template_hash", sa.Text, nullable=False),
        sa.Column("template_preview", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index(
        "ix_ai_prompt_templates_use_case",
        "ai_prompt_templates", ["use_case_id"]
    )

    op.create_table(
        "ai_output_audit",
        sa.Column("audit_id", sa.Text, primary_key=True),
        sa.Column("org_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("encounter_id", sa.Text, nullable=True),
        sa.Column("use_case_id", sa.Text,
                  sa.ForeignKey("ai_use_cases.use_case_id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("model_provider", sa.Text, nullable=False),
        sa.Column("model_name", sa.Text, nullable=False),
        sa.Column("prompt_template_id", sa.Text,
                  sa.ForeignKey("ai_prompt_templates.template_id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("input_hash", sa.Text, nullable=False),    # SHA-256 only
        sa.Column("output_hash", sa.Text, nullable=False),   # SHA-256 only
        sa.Column("output_preview", sa.Text, nullable=False, server_default=""),
        sa.Column("phi_redacted", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("clinical_disclaimer_shown", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count_prompt", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count_completion", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_ai_output_audit_org", "ai_output_audit", ["org_id"])
    op.create_index("ix_ai_output_audit_user", "ai_output_audit", ["user_id"])
    op.create_index("ix_ai_output_audit_encounter", "ai_output_audit", ["encounter_id"])

    op.create_table(
        "ai_human_reviews",
        sa.Column("review_id", sa.Text, primary_key=True),
        sa.Column("audit_id", sa.Text,
                  sa.ForeignKey("ai_output_audit.audit_id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("org_id", sa.Text, nullable=False),
        sa.Column("reviewer_user_id", sa.Text, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.Text, nullable=False),
    )
    op.create_index("ix_ai_human_reviews_org", "ai_human_reviews", ["org_id"])
    op.create_index("ix_ai_human_reviews_audit", "ai_human_reviews", ["audit_id"])

    op.create_table(
        "ai_security_events",
        sa.Column("event_id", sa.Text, primary_key=True),
        sa.Column("org_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("payload_hash", sa.Text, nullable=False),  # SHA-256 only
        sa.Column("details", sa.Text, nullable=False, server_default="{}"),  # JSON blob
        sa.Column("detected_by", sa.Text, nullable=False, server_default="chartnav_internal"),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_index("ix_ai_security_events_org", "ai_security_events", ["org_id"])
    op.create_index("ix_ai_security_events_type", "ai_security_events", ["event_type"])
    op.create_index("ix_ai_security_events_severity", "ai_security_events", ["severity"])


def downgrade() -> None:
    op.drop_table("ai_security_events")
    op.drop_table("ai_human_reviews")
    op.drop_table("ai_output_audit")
    op.drop_table("ai_prompt_templates")
    op.drop_table("ai_model_registry")
    op.drop_table("ai_use_cases")
