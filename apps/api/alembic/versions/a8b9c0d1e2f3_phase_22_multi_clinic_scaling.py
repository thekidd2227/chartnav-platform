"""Phase 22 — Multi-clinic / multi-provider scaling foundation.

Adds four tables that turn ChartNav from a single-clinic demo into
a multi-location ophthalmology platform:

  * ``provider_location_assignments`` — which providers serve which
    locations (a provider may serve multiple locations; a location
    may have multiple providers).
  * ``location_rooms``               — exam / imaging / testing /
    procedure / admin / other rooms (lanes) per location.
  * ``provider_schedule_blocks``     — clinic / surgery / injection /
    testing / admin / unavailable / other blocks per provider per
    location per time window.
  * ``clinic_operating_hours``       — per-location, per-day-of-week
    open/close hours with explicit ``is_closed`` flag.

Every row is ``organization_id``-scoped. Foreign keys enforce
referential integrity within the org; the route layer enforces the
standard ``ensure_same_org`` + 404-on-cross-org no-existence-leak
invariant.

Phase 22 is metadata + scheduling foundation only. It does NOT
ingest external scheduling systems, automate appointment booking,
auto-assign rooms, or recommend providers for visits. It does NOT
introduce patient-facing surfaces, billing / claims / insurance,
HIPAA compliance controls, or device-vendor integrations.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- enum value sets (CHECK constraints; portable SQLite + Postgres) -

_ROOM_TYPES = (
    "exam",
    "imaging",
    "testing",
    "procedure",
    "admin",
    "other",
)
_BLOCK_TYPES = (
    "clinic",
    "surgery",
    "injection",
    "testing",
    "admin",
    "unavailable",
    "other",
)


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# --- upgrade ----------------------------------------------------------


def upgrade() -> None:
    # ----- provider_location_assignments -----
    op.create_table(
        "provider_location_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
            name="fk_pla_org",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["providers.id"], name="fk_pla_provider"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_pla_location"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "provider_id",
            "location_id",
            name="uq_pla_org_provider_location",
        ),
    )
    op.create_index(
        "ix_pla_org_provider",
        "provider_location_assignments",
        ["organization_id", "provider_id"],
    )
    op.create_index(
        "ix_pla_org_location",
        "provider_location_assignments",
        ["organization_id", "location_id"],
    )
    op.create_index(
        "ix_pla_org_active",
        "provider_location_assignments",
        ["organization_id", "is_active"],
    )

    # ----- location_rooms -----
    op.create_table(
        "location_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("room_type", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
            name="fk_rooms_org",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_rooms_location"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "location_id",
            "name",
            name="uq_rooms_org_location_name",
        ),
        sa.CheckConstraint(
            f"room_type IN ({_csv(_ROOM_TYPES)})",
            name="ck_rooms_type_allowed",
        ),
    )
    op.create_index(
        "ix_rooms_org_location",
        "location_rooms",
        ["organization_id", "location_id"],
    )
    op.create_index(
        "ix_rooms_org_type",
        "location_rooms",
        ["organization_id", "room_type"],
    )
    op.create_index(
        "ix_rooms_org_active",
        "location_rooms",
        ["organization_id", "is_active"],
    )

    # ----- provider_schedule_blocks -----
    op.create_table(
        "provider_schedule_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column(
            "start_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "end_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
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
            name="fk_psb_org",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["providers.id"], name="fk_psb_provider"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_psb_location"
        ),
        sa.CheckConstraint(
            f"block_type IN ({_csv(_BLOCK_TYPES)})",
            name="ck_psb_type_allowed",
        ),
        sa.CheckConstraint(
            "capacity IS NULL OR capacity >= 0",
            name="ck_psb_capacity_nonneg",
        ),
        sa.CheckConstraint(
            "start_at < end_at",
            name="ck_psb_time_range",
        ),
    )
    op.create_index(
        "ix_psb_org_provider",
        "provider_schedule_blocks",
        ["organization_id", "provider_id"],
    )
    op.create_index(
        "ix_psb_org_location",
        "provider_schedule_blocks",
        ["organization_id", "location_id"],
    )
    op.create_index(
        "ix_psb_org_start",
        "provider_schedule_blocks",
        ["organization_id", "start_at"],
    )
    op.create_index(
        "ix_psb_org_provider_start",
        "provider_schedule_blocks",
        ["organization_id", "provider_id", "start_at"],
    )
    op.create_index(
        "ix_psb_org_location_start",
        "provider_schedule_blocks",
        ["organization_id", "location_id", "start_at"],
    )
    op.create_index(
        "ix_psb_org_type",
        "provider_schedule_blocks",
        ["organization_id", "block_type"],
    )

    # ----- clinic_operating_hours -----
    op.create_table(
        "clinic_operating_hours",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.String(length=8), nullable=True),
        sa.Column("closes_at", sa.String(length=8), nullable=True),
        sa.Column(
            "is_closed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
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
            name="fk_hours_org",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_hours_location"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "location_id",
            "day_of_week",
            name="uq_hours_org_location_day",
        ),
        sa.CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_hours_day_range",
        ),
    )
    op.create_index(
        "ix_hours_org_location",
        "clinic_operating_hours",
        ["organization_id", "location_id"],
    )


# --- downgrade --------------------------------------------------------


def downgrade() -> None:
    op.drop_index(
        "ix_hours_org_location", table_name="clinic_operating_hours"
    )
    op.drop_table("clinic_operating_hours")
    op.drop_index("ix_psb_org_type", table_name="provider_schedule_blocks")
    op.drop_index(
        "ix_psb_org_location_start", table_name="provider_schedule_blocks"
    )
    op.drop_index(
        "ix_psb_org_provider_start", table_name="provider_schedule_blocks"
    )
    op.drop_index("ix_psb_org_start", table_name="provider_schedule_blocks")
    op.drop_index("ix_psb_org_location", table_name="provider_schedule_blocks")
    op.drop_index("ix_psb_org_provider", table_name="provider_schedule_blocks")
    op.drop_table("provider_schedule_blocks")
    op.drop_index("ix_rooms_org_active", table_name="location_rooms")
    op.drop_index("ix_rooms_org_type", table_name="location_rooms")
    op.drop_index("ix_rooms_org_location", table_name="location_rooms")
    op.drop_table("location_rooms")
    op.drop_index(
        "ix_pla_org_active", table_name="provider_location_assignments"
    )
    op.drop_index(
        "ix_pla_org_location", table_name="provider_location_assignments"
    )
    op.drop_index(
        "ix_pla_org_provider", table_name="provider_location_assignments"
    )
    op.drop_table("provider_location_assignments")
