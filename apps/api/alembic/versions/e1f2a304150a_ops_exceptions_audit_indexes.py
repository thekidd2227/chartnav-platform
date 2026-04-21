"""ops exceptions audit indexes (wave 8)

Revision ID: e1f2a304150a
Revises: e1f2a3041509
Create Date: 2026-04-21 07:00:00.000000

Phase 53 — enterprise operations & exceptions control plane.

The new /admin/operations/* surface aggregates the last N days of
`security_audit_events` by (organization_id, error_code, created_at)
to produce blocked-note, identity-failure, and signature-mismatch
queues. The existing indexes on that table are single-column
(event_type, actor_email, created_at) — none of them carry
organization_id. At org scale this is fine for hundreds of events,
but the ops queue is exactly the surface that will get called for
every admin panel load, so we index it correctly.

Two composite indexes:

  ix_security_audit_events_org_created
      (organization_id, created_at DESC)
      primary seek for every time-windowed admin query

  ix_security_audit_events_org_error_created
      (organization_id, error_code, created_at DESC)
      bucket queries that group by error_code within the window

Additive. No rows touched.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1f2a304150a"
down_revision: Union[str, Sequence[str], None] = "e1f2a3041509"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_security_audit_events_org_created",
        "security_audit_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_security_audit_events_org_error_created",
        "security_audit_events",
        ["organization_id", "error_code", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_audit_events_org_error_created",
        table_name="security_audit_events",
    )
    op.drop_index(
        "ix_security_audit_events_org_created",
        table_name="security_audit_events",
    )
