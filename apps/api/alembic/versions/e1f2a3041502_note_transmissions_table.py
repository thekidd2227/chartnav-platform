"""note transmission log — signed-artifact dispatch attempts to external systems

Revision ID: e1f2a3041502
Revises: e1f2a3041501
Create Date: 2026-04-19 08:00:00.000000

Phase 26 — FHIR write-path groundwork.

Adds `note_transmissions` — an append-only log of every attempt to
hand a signed note artifact to an external clinical system (via any
adapter). One note-version can have many transmissions (retries,
force-resends, different targets), but at most one is allowed to be
``succeeded`` at any moment unless the caller explicitly forces a
re-transmission.

Columns:

- ``note_version_id`` — FK to the signed note being dispatched.
- ``encounter_id``    — denormalized for fast filter + scoping.
- ``organization_id`` — denormalized for org scoping without a join.
- ``adapter_key``     — which adapter handled the transmission
                         (``fhir`` / ``stub`` / vendor-specific).
- ``target_system``   — the adapter's human-readable target identifier
                         (base URL for FHIR, "stub" for stub, etc.).
- ``transport_status``— ``queued`` | ``dispatching`` | ``succeeded``
                         | ``failed`` | ``unsupported``.
- ``request_body_hash`` — sha256 of the serialized request body, so
                         downstream reconciliation can match against
                         the exported artifact hash.
- ``response_code``   — HTTP status (nullable — stub adapter has none).
- ``response_snippet``— capped text (max 1024 chars) for audit trail.
- ``remote_id``       — whatever id the remote system echoed back,
                         if any (e.g. the vendor's DocumentReference id).
- ``last_error_code`` / ``last_error`` — populated on failure.
- ``attempt_number``  — monotonically increasing per (note_version).
- ``attempted_at`` / ``completed_at``
- ``created_by_user_id`` — who initiated the transmission.
- ``created_at`` / ``updated_at``.

Unique constraint on ``(note_version_id, attempt_number)`` so the
worker/retry path can insert row N+1 safely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3041502"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_transmissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "note_version_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "encounter_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "adapter_key", sa.String(length=64), nullable=False,
            comment="'fhir' | 'stub' | vendor-specific",
        ),
        sa.Column(
            "target_system", sa.String(length=512), nullable=True,
            comment="base URL for FHIR, adapter-specific label otherwise",
        ),
        sa.Column(
            "transport_status", sa.String(length=32), nullable=False,
            server_default=sa.text("'queued'"),
            comment=(
                "queued | dispatching | succeeded | failed | unsupported"
            ),
        ),
        sa.Column(
            "request_body_hash", sa.String(length=64), nullable=True,
            comment="sha256 hex of the serialized request body",
        ),
        sa.Column(
            "response_code", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "response_snippet", sa.Text(), nullable=True,
            comment="capped (<=1024 chars) response body excerpt for audit",
        ),
        sa.Column(
            "remote_id", sa.String(length=256), nullable=True,
            comment="id echoed back by the remote system (vendor DocRef id)",
        ),
        sa.Column(
            "last_error_code", sa.String(length=64), nullable=True,
        ),
        sa.Column(
            "last_error", sa.Text(), nullable=True,
        ),
        sa.Column(
            "attempt_number", sa.Integer(), nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "attempted_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_by_user_id", sa.Integer(), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["note_version_id"], ["note_versions.id"],
            name="fk_note_transmissions_note_version",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"], ["encounters.id"],
            name="fk_note_transmissions_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_note_transmissions_created_by",
        ),
        sa.UniqueConstraint(
            "note_version_id", "attempt_number",
            name="uq_note_transmissions_version_attempt",
        ),
    )


def downgrade() -> None:
    op.drop_table("note_transmissions")
