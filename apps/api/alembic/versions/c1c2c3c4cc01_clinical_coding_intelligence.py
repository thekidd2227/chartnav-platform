"""clinical coding intelligence — ICD-10-CM ingestion + versioning

Revision ID: c1c2c3c4cc01
Revises: f1r2e3m4i5n6
Create Date: 2026-04-22 23:30:00.000000

Creates six tables that back the Clinical Coding Intelligence feature:

  icd10cm_versions            — one row per official CDC/NCHS release,
                                 with checksum + effective window so
                                 we can resolve the valid code set for
                                 any date of service.
  icd10cm_codes               — normalized diagnosis codes (one row per
                                 (version_id, code)) with chapter and
                                 category relationships denormalized
                                 for search performance.
  icd10cm_code_relationships  — parent/child + chapter membership graph.
                                 Kept separate so the flat code table
                                 stays fast to scan.
  provider_favorite_codes     — per-clinician / per-org pinned codes
                                 and usage counters.
  coding_sync_jobs            — ingestion job audit trail: when,
                                 what files, bytes, parse result, error.
  ophthalmology_support_rules — advisory workflow hints by diagnosis
                                 pattern; maps to specificity prompts
                                 and claim-support reminders. NOT a
                                 coding or reimbursement rule engine.

The code column in both icd10cm_codes and ophthalmology_support_rules
is the decimal-pointed form (e.g. H40.1211). `normalized_code` strips
the dot (H401211) to make LIKE search fast for "what starts with".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c1c2c3c4cc01"
down_revision: Union[str, Sequence[str], None] = "f1r2e3m4i5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- icd10cm_versions ----------------------------------------
    op.create_table(
        "icd10cm_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_label", sa.String(length=64), nullable=False),
        sa.Column(
            "source_authority", sa.String(length=32), nullable=False,
            server_default="CDC/NCHS",
        ),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("effective_start_date", sa.Date(), nullable=False),
        sa.Column("effective_end_date", sa.Date(), nullable=True),
        sa.Column(
            "is_active", sa.Integer(), nullable=False, server_default="0",
            comment="1 = treated as the currently-preferred default version",
        ),
        sa.Column(
            "manifest_json", sa.Text(), nullable=False,
            comment="JSON array listing raw filenames + SHA-256 + byte size",
        ),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column(
            "parse_status", sa.String(length=32), nullable=False,
            server_default="downloaded",
            comment="downloaded | parsing | ready | failed | superseded",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_icd10cm_versions_effective",
        "icd10cm_versions", ["effective_start_date", "effective_end_date"],
    )
    op.create_index(
        "ix_icd10cm_versions_active",
        "icd10cm_versions", ["is_active"],
    )

    # ----- icd10cm_codes -------------------------------------------
    op.create_table(
        "icd10cm_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "code", sa.String(length=16), nullable=False,
            comment="decimal-pointed form, e.g. H40.1211",
        ),
        sa.Column(
            "normalized_code", sa.String(length=16), nullable=False,
            index=True,
            comment="dot stripped, e.g. H401211",
        ),
        sa.Column(
            "is_billable", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column("short_description", sa.String(length=256), nullable=False),
        sa.Column("long_description", sa.Text(), nullable=False),
        sa.Column(
            "chapter_code", sa.String(length=16), nullable=True,
            comment="e.g. 'VII' for eye + adnexa",
        ),
        sa.Column("chapter_title", sa.String(length=256), nullable=True),
        sa.Column(
            "category_code", sa.String(length=8), nullable=True,
            comment="3-char category, e.g. H40 for glaucoma",
        ),
        sa.Column(
            "parent_code", sa.String(length=16), nullable=True,
            comment="immediate parent in the tabular hierarchy",
        ),
        sa.Column(
            "specificity_flags", sa.String(length=128), nullable=True,
            comment="comma-separated tokens: laterality_required, severity_required, stage_required",
        ),
        sa.Column(
            "source_file", sa.String(length=256), nullable=True,
            comment="raw source file basename this record came from",
        ),
        sa.Column(
            "source_line_no", sa.Integer(), nullable=True,
        ),
        sa.UniqueConstraint(
            "version_id", "code",
            name="uq_icd10cm_codes_version_code",
        ),
    )
    op.create_index(
        "ix_icd10cm_codes_version_norm",
        "icd10cm_codes", ["version_id", "normalized_code"],
    )
    op.create_index(
        "ix_icd10cm_codes_version_category",
        "icd10cm_codes", ["version_id", "category_code"],
    )

    # ----- icd10cm_code_relationships ------------------------------
    op.create_table(
        "icd10cm_code_relationships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version_id", sa.Integer(), nullable=False, index=True),
        sa.Column("parent_code", sa.String(length=16), nullable=False),
        sa.Column("child_code", sa.String(length=16), nullable=False),
        sa.Column(
            "relationship_type", sa.String(length=32), nullable=False,
            server_default="parent_child",
            comment="parent_child | chapter | category",
        ),
    )
    op.create_index(
        "ix_icd10cm_rel_parent",
        "icd10cm_code_relationships",
        ["version_id", "parent_code"],
    )
    op.create_index(
        "ix_icd10cm_rel_child",
        "icd10cm_code_relationships",
        ["version_id", "child_code"],
    )

    # ----- provider_favorite_codes ---------------------------------
    op.create_table(
        "provider_favorite_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column(
            "specialty_tag", sa.String(length=32), nullable=True,
            comment="retina | glaucoma | cataract | cornea | oculoplastics | general",
        ),
        sa.Column(
            "usage_count", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column(
            "is_pinned", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "code",
            name="uq_provider_favorite_codes_user_code",
        ),
    )

    # ----- coding_sync_jobs ----------------------------------------
    op.create_table(
        "coding_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_type", sa.String(length=32), nullable=False,
            comment="scheduled | manual",
        ),
        sa.Column(
            "status", sa.String(length=32), nullable=False,
            server_default="queued",
            comment="queued | running | succeeded | failed",
        ),
        sa.Column("version_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "files_downloaded", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "records_parsed", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "bytes_downloaded", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_log", sa.Text(), nullable=True,
        ),
        sa.Column(
            "triggered_by_user_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )
    op.create_index(
        "ix_coding_sync_jobs_status",
        "coding_sync_jobs", ["status", "created_at"],
    )

    # ----- ophthalmology_support_rules -----------------------------
    op.create_table(
        "ophthalmology_support_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "specialty_tag", sa.String(length=32), nullable=False, index=True,
        ),
        sa.Column(
            "workflow_area", sa.String(length=64), nullable=False,
            comment="search | favorites | specificity_prompt | claim_support_hint",
        ),
        sa.Column(
            "diagnosis_code_pattern", sa.String(length=32), nullable=False,
            comment="ICD-10-CM LIKE-style pattern, e.g. H40.% or H25.%",
        ),
        sa.Column(
            "advisory_hint", sa.Text(), nullable=False,
            comment="short advisory text shown to the clinician",
        ),
        sa.Column(
            "specificity_prompt", sa.Text(), nullable=True,
            comment="bullet prompts: laterality, stage, severity, etc.",
        ),
        sa.Column(
            "source_reference", sa.String(length=256), nullable=True,
            comment="CDC/NCHS table, CMS policy doc, or clinical reference",
        ),
        sa.Column(
            "is_active", sa.Integer(), nullable=False, server_default="1",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ophthalmology_support_rules")
    op.drop_index("ix_coding_sync_jobs_status", table_name="coding_sync_jobs")
    op.drop_table("coding_sync_jobs")
    op.drop_table("provider_favorite_codes")
    op.drop_index("ix_icd10cm_rel_child", table_name="icd10cm_code_relationships")
    op.drop_index("ix_icd10cm_rel_parent", table_name="icd10cm_code_relationships")
    op.drop_table("icd10cm_code_relationships")
    op.drop_index("ix_icd10cm_codes_version_category", table_name="icd10cm_codes")
    op.drop_index("ix_icd10cm_codes_version_norm", table_name="icd10cm_codes")
    op.drop_table("icd10cm_codes")
    op.drop_index("ix_icd10cm_versions_active", table_name="icd10cm_versions")
    op.drop_index("ix_icd10cm_versions_effective", table_name="icd10cm_versions")
    op.drop_table("icd10cm_versions")
