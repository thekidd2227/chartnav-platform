"""phase 2 — messaging hardening (messages + preferences)

Revision ID: p2a4msg01
Revises: p2a3int01
Create Date: 2026-04-26 15:00:00.000000

Phase 2 item 4 of the closure plan:
docs/chartnav/closure/PHASE_B_Reminders_and_Patient_Communication_Hardening.md

Adds two tables that close the messaging hardening acceptance
criteria:

  messages
    One row per outbound or inbound communication tied to a
    patient identifier within an organization. Status is constrained
    to a stable state machine (queued → sent → delivered |
    queued → sent → failed | queued → opt_out). Inbound rows are
    used to record STOP / HELP keyword arrivals.

  patient_communication_preferences
    Per-(org, patient_identifier, channel) opt-in/opt-out flag
    with source attribution ("staff-recorded", "inbound-stop",
    "intake-form-consent"). Inbound STOP flips the row, stamps
    opted_out_at, and the dispatcher refuses to enqueue.

Truth limitations preserved (spec §9):
  - No real SMS or email is sent in Phase B. The only provider
    actually wired is StubProvider; "delivered" produced by the
    stub means "stub recorded a synthetic delivery", never carrier
    delivery confirmation. The UI's MessageStatusLabel renders
    "Stub-delivered" while the stub is wired so no demo or audit
    log can mistakenly imply real transmission.
  - Inbound STOP parsing in Phase B is simulated via an admin
    action; there is no live carrier webhook.
  - No HIPAA Business Associate Agreement is in place with any
    messaging vendor because no vendor is wired.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2a4msg01"
down_revision: Union[str, Sequence[str], None] = "p2a3int01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "reminder_id", sa.Integer(), nullable=True, index=True,
        ),
        sa.Column(
            "patient_identifier", sa.String(length=255), nullable=False,
            index=True,
        ),
        sa.Column(
            "channel", sa.String(length=32), nullable=False,
            comment="Phase B: 'sms_stub' | 'email_stub' only. Real "
                    "channels (sms / email) land in Phase C.",
        ),
        sa.Column(
            "direction", sa.String(length=16), nullable=False,
            comment="'outbound' | 'inbound'",
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False,
            server_default=sa.text("'queued'"),
            comment="queued | sent | delivered | failed | opt_out | read",
        ),
        sa.Column(
            "provider_message_id", sa.String(length=128), nullable=True,
            comment="Synthetic for StubProvider; vendor-supplied for "
                    "real providers in Phase C.",
        ),
        sa.Column(
            "provider_kind", sa.String(length=32), nullable=False,
            server_default=sa.text("'stub'"),
            comment="'stub' (Phase B) or vendor key (Phase C)",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
    )

    op.create_table(
        "patient_communication_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), nullable=False, index=True,
        ),
        sa.Column(
            "patient_identifier", sa.String(length=255), nullable=False,
            index=True,
        ),
        sa.Column(
            "channel", sa.String(length=32), nullable=False,
        ),
        sa.Column(
            "opted_in", sa.Boolean(), nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("opted_out_at", sa.DateTime(), nullable=True),
        sa.Column(
            "opt_out_source", sa.String(length=64), nullable=True,
            comment="staff-recorded | inbound-stop | intake-form-consent",
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "patient_identifier", "channel",
            name="uq_pcp_org_patient_channel",
        ),
    )


def downgrade() -> None:
    op.drop_table("patient_communication_preferences")
    op.drop_table("messages")
