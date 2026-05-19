"""Phase 21B — Ophthalmology imaging pipeline foundation.

Adds three tables that record device-derived imaging study metadata
and the provider-review workflow around it:

  * ``imaging_studies``       — one row per device-derived study
  * ``imaging_files``         — per-study file METADATA only (no binaries)
  * ``imaging_measurements``  — structured measurement metadata

Phase 21B is **metadata + review workflow only**. It does NOT:
  * store actual image binaries
  * claim integrations with any specific device or vendor
  * ingest DICOM
  * autonomously interpret images
  * autonomously diagnose, dose, order, refer, message patients, or
    grade severity

Modality labels are deliberately generic
(``oct_macula`` / ``fundus_photo`` / ``visual_field_24_2`` / ...).
Vendor-specific adapters are out of scope.

Every row is ``organization_id``-scoped. The route layer enforces
the standard ``ensure_same_org`` + 404-on-cross-org no-existence-leak
invariant; foreign keys here only enforce referential integrity
within the org.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- enum value sets (CHECK constraints; portable SQLite + Postgres) -

_MODALITIES = (
    "oct_macula",
    "oct_rnfl",
    "fundus_photo",
    "widefield_fundus",
    "visual_field_24_2",
    "visual_field_10_2",
    "biometry_packet",
    "external_pdf",
    "other",
)
_EYE_VALUES = ("OD", "OS", "OU", "NA")
_STUDY_STATUSES = (
    "pending_upload",
    "uploaded",
    "ready_for_review",
    "reviewed",
    "archived",
)
_FILE_KINDS = ("image", "report_pdf", "raw_export")
_MEASUREMENT_SOURCES = ("manual", "demo", "imported_metadata")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# --- upgrade ----------------------------------------------------------


def upgrade() -> None:
    # ----- imaging_studies -----
    op.create_table(
        "imaging_studies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending_upload",
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by_user_id", sa.Integer(), nullable=True
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
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
            name="fk_imaging_studies_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_imaging_studies_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_imaging_studies_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name="fk_imaging_studies_reviewer",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_imaging_studies_creator",
        ),
        sa.CheckConstraint(
            f"modality IN ({_csv(_MODALITIES)})",
            name="ck_imaging_studies_modality_allowed",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_VALUES)})",
            name="ck_imaging_studies_eye_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_STUDY_STATUSES)})",
            name="ck_imaging_studies_status_allowed",
        ),
    )
    op.create_index(
        "ix_imaging_studies_org_patient",
        "imaging_studies",
        ["organization_id", "patient_id"],
    )

    # ----- imaging_files -----
    op.create_table(
        "imaging_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("file_kind", sa.String(length=32), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=True),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_imaging_files_org",
        ),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["imaging_studies.id"],
            name="fk_imaging_files_study",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_imaging_files_creator",
        ),
        sa.CheckConstraint(
            f"file_kind IN ({_csv(_FILE_KINDS)})",
            name="ck_imaging_files_kind_allowed",
        ),
    )
    op.create_index(
        "ix_imaging_files_study",
        "imaging_files",
        ["study_id"],
    )

    # ----- imaging_measurements -----
    op.create_table(
        "imaging_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column(
            "measurement_type", sa.String(length=120), nullable=False
        ),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_imaging_measurements_org",
        ),
        sa.ForeignKeyConstraint(
            ["study_id"],
            ["imaging_studies.id"],
            name="fk_imaging_measurements_study",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_imaging_measurements_creator",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_VALUES)})",
            name="ck_imaging_measurements_eye_allowed",
        ),
        sa.CheckConstraint(
            f"source IN ({_csv(_MEASUREMENT_SOURCES)})",
            name="ck_imaging_measurements_source_allowed",
        ),
    )
    op.create_index(
        "ix_imaging_measurements_study",
        "imaging_measurements",
        ["study_id"],
    )


# --- downgrade --------------------------------------------------------


def downgrade() -> None:
    op.drop_index(
        "ix_imaging_measurements_study", table_name="imaging_measurements"
    )
    op.drop_table("imaging_measurements")
    op.drop_index("ix_imaging_files_study", table_name="imaging_files")
    op.drop_table("imaging_files")
    op.drop_index(
        "ix_imaging_studies_org_patient", table_name="imaging_studies"
    )
    op.drop_table("imaging_studies")
