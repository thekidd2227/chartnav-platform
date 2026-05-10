"""Phase 20B — Structured data layer foundation.

Adds eight tables that underpin patient segmentation, lightweight
tagging, the patient problem list, clinic workflow templates +
stages, the cross-tab work-queue, and per-role saved view presets.

Every table is org-scoped via ``organization_id`` and follows the
existing ``ensure_same_org`` + 404-on-cross-org no-existence-leak
contract enforced by the route + service layer.

Designed to ship as the foundation for:
  - Phase 20C — role-based dashboards (consume ``work_queue_items``
    + ``role_view_presets``)
  - Phase 21A — specialty modules (extend ``patient_problem_list``
    with retina / glaucoma / cornea / etc.)
  - Phase 21B — imaging pipeline (writes back into work-queues)
  - Phase 22 — multi-clinic scaling (shares work-queue across
    locations)

Phase 20B itself does NOT add any role-based dashboards, retina /
glaucoma / cornea tracking, imaging studies, provider-location
assignments, schedule blocks, or operating hours. Those land in
their respective later phases per the Phase 20A roadmap.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- enum value sets (CHECK constraints; portable SQLite + Postgres) -

_PROBLEM_STATUSES = ("active", "monitoring", "inactive", "resolved")
_EYE_VALUES = ("OD", "OS", "OU")  # nullable; clinician may omit
_QUEUE_PRIORITIES = ("low", "normal", "high", "urgent")
_QUEUE_STATUSES = ("open", "in_progress", "blocked", "completed", "dismissed")
_VIEW_PRESET_ROLES = ("admin", "clinician", "reviewer", "front_desk", "technician")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# --- upgrade ----------------------------------------------------------


def upgrade() -> None:
    # ----- patient_segments -----
    op.create_table(
        "patient_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("segment_type", sa.String(length=64), nullable=False),
        sa.Column("criteria_json", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_segments_org"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_segments_creator"
        ),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_segments_org_name"
        ),
    )
    op.create_index("ix_segments_org", "patient_segments", ["organization_id"])
    op.create_index(
        "ix_segments_org_active",
        "patient_segments",
        ["organization_id", "is_active"],
    )

    # ----- patient_segment_memberships -----
    op.create_table(
        "patient_segment_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_memberships_org"
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_memberships_patient"
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["patient_segments.id"],
            name="fk_memberships_segment",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "patient_id",
            "segment_id",
            name="uq_memberships_org_patient_segment",
        ),
    )
    op.create_index(
        "ix_memberships_org", "patient_segment_memberships", ["organization_id"]
    )
    op.create_index(
        "ix_memberships_org_patient",
        "patient_segment_memberships",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_memberships_org_segment",
        "patient_segment_memberships",
        ["organization_id", "segment_id"],
    )

    # ----- patient_tags -----
    op.create_table(
        "patient_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_tags_org"
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_tags_patient"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_tags_creator"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "patient_id",
            "tag",
            name="uq_tags_org_patient_tag",
        ),
    )
    op.create_index("ix_tags_org", "patient_tags", ["organization_id"])
    op.create_index(
        "ix_tags_org_patient", "patient_tags", ["organization_id", "patient_id"]
    )
    op.create_index(
        "ix_tags_org_tag", "patient_tags", ["organization_id", "tag"]
    )

    # ----- patient_problem_list -----
    op.create_table(
        "patient_problem_list",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("condition_code", sa.String(length=64), nullable=True),
        sa.Column("condition_label", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=64), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column(
            "last_reviewed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_problem_org"
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_problem_patient"
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_PROBLEM_STATUSES)})",
            name="ck_problem_status",
        ),
        sa.CheckConstraint(
            f"eye IS NULL OR eye IN ({_csv(_EYE_VALUES)})",
            name="ck_problem_eye",
        ),
    )
    op.create_index("ix_problem_org", "patient_problem_list", ["organization_id"])
    op.create_index(
        "ix_problem_org_patient",
        "patient_problem_list",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_problem_org_specialty",
        "patient_problem_list",
        ["organization_id", "specialty"],
    )
    op.create_index(
        "ix_problem_org_status",
        "patient_problem_list",
        ["organization_id", "status"],
    )

    # ----- clinic_workflow_templates -----
    op.create_table(
        "clinic_workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("specialty", sa.String(length=64), nullable=True),
        sa.Column("role_owner", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_wftmpl_org"
        ),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_wftmpl_org_name"
        ),
    )
    op.create_index(
        "ix_wftmpl_org", "clinic_workflow_templates", ["organization_id"]
    )
    op.create_index(
        "ix_wftmpl_org_active",
        "clinic_workflow_templates",
        ["organization_id", "is_active"],
    )
    op.create_index(
        "ix_wftmpl_org_specialty",
        "clinic_workflow_templates",
        ["organization_id", "specialty"],
    )
    op.create_index(
        "ix_wftmpl_org_role",
        "clinic_workflow_templates",
        ["organization_id", "role_owner"],
    )

    # ----- clinic_workflow_stages -----
    op.create_table(
        "clinic_workflow_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("role_owner", sa.String(length=32), nullable=False),
        sa.Column("sla_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_wfstage_org"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["clinic_workflow_templates.id"],
            name="fk_wfstage_template",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "template_id",
            "stage_order",
            name="uq_wfstage_org_template_order",
        ),
    )
    op.create_index(
        "ix_wfstage_org", "clinic_workflow_stages", ["organization_id"]
    )
    op.create_index(
        "ix_wfstage_org_template",
        "clinic_workflow_stages",
        ["organization_id", "template_id"],
    )

    # ----- work_queue_items -----
    op.create_table(
        "work_queue_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("queue_type", sa.String(length=64), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=32),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="open",
        ),
        sa.Column("assigned_role", sa.String(length=32), nullable=True),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_wq_org"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_wq_location"
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name="fk_wq_patient"
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"], name="fk_wq_encounter"
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["providers.id"], name="fk_wq_provider"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["users.id"], name="fk_wq_assigned"
        ),
        sa.CheckConstraint(
            f"priority IN ({_csv(_QUEUE_PRIORITIES)})",
            name="ck_wq_priority",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_QUEUE_STATUSES)})", name="ck_wq_status"
        ),
    )
    op.create_index("ix_wq_org", "work_queue_items", ["organization_id"])
    op.create_index(
        "ix_wq_org_status", "work_queue_items", ["organization_id", "status"]
    )
    op.create_index(
        "ix_wq_org_type", "work_queue_items", ["organization_id", "queue_type"]
    )
    op.create_index(
        "ix_wq_org_priority",
        "work_queue_items",
        ["organization_id", "priority"],
    )
    op.create_index(
        "ix_wq_org_location",
        "work_queue_items",
        ["organization_id", "location_id"],
    )
    op.create_index(
        "ix_wq_org_assigned_role",
        "work_queue_items",
        ["organization_id", "assigned_role"],
    )
    op.create_index(
        "ix_wq_org_assigned_user",
        "work_queue_items",
        ["organization_id", "assigned_user_id"],
    )
    op.create_index(
        "ix_wq_org_due", "work_queue_items", ["organization_id", "due_at"]
    )

    # ----- role_view_presets -----
    op.create_table(
        "role_view_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("filters_json", sa.Text(), nullable=True),
        sa.Column("columns_json", sa.Text(), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_rvp_org"
        ),
        sa.CheckConstraint(
            f"role IN ({_csv(_VIEW_PRESET_ROLES)})", name="ck_rvp_role"
        ),
        sa.UniqueConstraint(
            "organization_id", "role", "name", name="uq_rvp_org_role_name"
        ),
    )
    op.create_index("ix_rvp_org", "role_view_presets", ["organization_id"])
    op.create_index(
        "ix_rvp_org_role", "role_view_presets", ["organization_id", "role"]
    )
    op.create_index(
        "ix_rvp_org_role_default",
        "role_view_presets",
        ["organization_id", "role", "is_default"],
    )


# --- downgrade --------------------------------------------------------


def downgrade() -> None:
    op.drop_index("ix_rvp_org_role_default", table_name="role_view_presets")
    op.drop_index("ix_rvp_org_role", table_name="role_view_presets")
    op.drop_index("ix_rvp_org", table_name="role_view_presets")
    op.drop_table("role_view_presets")

    op.drop_index("ix_wq_org_due", table_name="work_queue_items")
    op.drop_index("ix_wq_org_assigned_user", table_name="work_queue_items")
    op.drop_index("ix_wq_org_assigned_role", table_name="work_queue_items")
    op.drop_index("ix_wq_org_location", table_name="work_queue_items")
    op.drop_index("ix_wq_org_priority", table_name="work_queue_items")
    op.drop_index("ix_wq_org_type", table_name="work_queue_items")
    op.drop_index("ix_wq_org_status", table_name="work_queue_items")
    op.drop_index("ix_wq_org", table_name="work_queue_items")
    op.drop_table("work_queue_items")

    op.drop_index("ix_wfstage_org_template", table_name="clinic_workflow_stages")
    op.drop_index("ix_wfstage_org", table_name="clinic_workflow_stages")
    op.drop_table("clinic_workflow_stages")

    op.drop_index("ix_wftmpl_org_role", table_name="clinic_workflow_templates")
    op.drop_index(
        "ix_wftmpl_org_specialty", table_name="clinic_workflow_templates"
    )
    op.drop_index("ix_wftmpl_org_active", table_name="clinic_workflow_templates")
    op.drop_index("ix_wftmpl_org", table_name="clinic_workflow_templates")
    op.drop_table("clinic_workflow_templates")

    op.drop_index("ix_problem_org_status", table_name="patient_problem_list")
    op.drop_index("ix_problem_org_specialty", table_name="patient_problem_list")
    op.drop_index("ix_problem_org_patient", table_name="patient_problem_list")
    op.drop_index("ix_problem_org", table_name="patient_problem_list")
    op.drop_table("patient_problem_list")

    op.drop_index("ix_tags_org_tag", table_name="patient_tags")
    op.drop_index("ix_tags_org_patient", table_name="patient_tags")
    op.drop_index("ix_tags_org", table_name="patient_tags")
    op.drop_table("patient_tags")

    op.drop_index(
        "ix_memberships_org_segment", table_name="patient_segment_memberships"
    )
    op.drop_index(
        "ix_memberships_org_patient", table_name="patient_segment_memberships"
    )
    op.drop_index(
        "ix_memberships_org", table_name="patient_segment_memberships"
    )
    op.drop_table("patient_segment_memberships")

    op.drop_index("ix_segments_org_active", table_name="patient_segments")
    op.drop_index("ix_segments_org", table_name="patient_segments")
    op.drop_table("patient_segments")
