"""patient extended demographics

Revision ID: b2d4f6a80a01
Revises: e1f2a3041508
Create Date: 2026-06-25 00:00:00.000000

Reconciliation migration (mainline-wins).

Background: an earlier stash carried `f7b9c1d2e301_patient_chart_foundation`
which (a) extended `patients` with EMR demographics AND (b) re-created the
`chart_artifacts` table. Mainline has since shipped `chart_artifacts`
(e1f2a3041507, `drawing_json`) and `fundus_charts` (e1f2a3041508) on its own
line of history, so the stash migration collided (duplicate table) and forked
the Alembic graph into two heads. That stash migration was never committed to
main; it has been dropped.

This migration keeps ONLY the part mainline lacks — the extended `patients`
demographics columns required by the patient-detail endpoint — and chains
cleanly after the current mainline head (e1f2a3041508), leaving a single head.
It does NOT touch `chart_artifacts`.

Everything added here is nullable, so existing rows keep working unchanged.
Insurance is stored as freeform JSON TEXT so the UI can iterate without a new
migration per field; `column kept TEXT for SQLite/Postgres parity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d4f6a80a01"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041508"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columns mainline's `patients` table (f6a7b8c9d0e1) does not already have.
# (id, organization_id, external_ref, patient_identifier, first_name,
#  last_name, date_of_birth, sex_at_birth, is_active, created_at already exist.)
_ADDED_COLUMNS = (
    ("middle_name", sa.String(length=128)),
    ("preferred_name", sa.String(length=128)),
    ("display_name", sa.String(length=255)),
    ("pronouns", sa.String(length=64)),
    ("gender_identity", sa.String(length=64)),
    ("preferred_language", sa.String(length=64)),
    ("race", sa.String(length=128)),
    ("ethnicity", sa.String(length=128)),
    ("email", sa.String(length=255)),
    ("phone", sa.String(length=64)),
    ("address_line1", sa.String(length=255)),
    ("address_line2", sa.String(length=255)),
    ("address_city", sa.String(length=128)),
    ("address_state", sa.String(length=64)),
    ("address_postal_code", sa.String(length=32)),
    ("address_country", sa.String(length=64)),
    ("emergency_contact_name", sa.String(length=255)),
    ("emergency_contact_phone", sa.String(length=64)),
    ("emergency_contact_relationship", sa.String(length=64)),
    ("insurance_metadata", sa.Text()),
    ("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        for name, type_ in _ADDED_COLUMNS:
            batch.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        for name, _type in reversed(_ADDED_COLUMNS):
            batch.drop_column(name)
