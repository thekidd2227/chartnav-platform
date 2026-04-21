"""front_desk role + clinician custom shortcuts

Revision ID: e1f2a3041506
Revises: d0e1f2a30415
Create Date: 2026-04-20 20:00:00.000000

Phase 38 — doctor & front-desk expansion.

Two concerns landing together because they both widen the "who can
do what" surface without touching the encounter state machine or the
adapter boundary:

1. **front_desk role.** Drops the existing `users.role` CHECK and
   recreates it with `front_desk` added to the allowed set. The
   backend authorization layer is where the fine-grained per-route
   permissions live — at the DB layer we only need the value to be a
   permitted literal. Alphabetical ordering is preserved in the
   literal list for grep legibility.

2. **clinician_custom_shortcuts.** The phase-29 Clinical Shortcuts
   catalog is static UI content; the phase-30
   `clinician_shortcut_favorites` table only pins catalog items.
   Doctors asked for their own *authored* shortcut fragments (a-la
   `clinician_quick_comments`). Same per-user, soft-delete,
   org-scoped shape as that table, keyed by a stable UUID-like ref
   the frontend can treat exactly like a catalog ref.

   Frontend still owns provenance — `prefix` ("my" vs catalog group
   name) — but the backend owns persistence and the audit stream.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041506"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041505"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_CHECK_OLD = "role IN ('admin', 'clinician', 'reviewer')"
ROLE_CHECK_NEW = "role IN ('admin', 'clinician', 'front_desk', 'reviewer')"


def upgrade() -> None:
    # ---- (1) widen users.role CHECK -----------------------------------
    #
    # batch_alter_table handles SQLite's lack of ALTER TABLE DROP
    # CONSTRAINT by rebuilding the table; Postgres applies the DDL
    # directly.
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint("ck_users_role_allowed", ROLE_CHECK_NEW)

    # ---- (2) clinician_custom_shortcuts ------------------------------
    op.create_table(
        "clinician_custom_shortcuts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
            index=True,
            comment="org scope; matches the owning user's org at creation",
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            index=True,
            comment="owning clinician; shortcuts are per-user not per-org",
        ),
        sa.Column(
            "shortcut_ref",
            sa.String(length=64),
            nullable=False,
            comment=(
                "stable string id the frontend uses as the provenance key "
                "in the usage-audit stream; prefixed with 'my-' to make "
                "the per-user namespace obvious alongside catalog refs "
                "like 'pvd-01'"
            ),
        ),
        sa.Column(
            "group_name",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'My patterns'"),
            comment="display grouping in the shortcut panel",
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
            comment="the shortcut fragment; inserted as-is into the draft",
        ),
        sa.Column(
            "tags",
            sa.Text(),
            nullable=True,
            comment=(
                "JSON-encoded list of search tags; null means no tags "
                "(search still matches body + group_name)"
            ),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="soft delete — false means hidden from the UI list",
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
            ["organization_id"],
            ["organizations.id"],
            name="fk_custom_shortcuts_org",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_custom_shortcuts_user",
        ),
        sa.UniqueConstraint(
            "user_id",
            "shortcut_ref",
            name="uq_custom_shortcuts_user_ref",
        ),
    )
    op.create_index(
        "ix_custom_shortcuts_user_active",
        "clinician_custom_shortcuts",
        ["organization_id", "user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_custom_shortcuts_user_active",
        table_name="clinician_custom_shortcuts",
    )
    op.drop_table("clinician_custom_shortcuts")

    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint("ck_users_role_allowed", ROLE_CHECK_OLD)
