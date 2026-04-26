"""phase A — RBAC role expansion: technician + biller_coder

Revision ID: r2b3a4c5e6f7
Revises: f1g2t3p4q5r6
Create Date: 2026-04-24 12:30:00.000000

Phase A item 2 of the closure plan:
docs/chartnav/closure/PHASE_A_RBAC_and_Audit_Trail_Spec.md

Widens the `users.role` CHECK constraint to allow `technician` and
`biller_coder`, alongside the previously-allowed
{admin, clinician, reviewer, front_desk}. Same SQLite batch-rebuild
pattern as e1f2a3041506; Postgres applies the DDL directly.

Truth limitations preserved (verbatim from the spec):
- Roles are coarse-grained. We are NOT claiming row-level security
  inside Postgres or per-field attribute-based access control.
- Audit trail is at the application layer. We do NOT ship a WORM
  store or SIEM integration in Phase A.
- `reviewer` remains in the schema as a legacy/QA role. It is not
  part of the five-role clinic matrix and should not be assigned
  to clinical staff.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "r2b3a4c5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1g2t3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Alphabetical-by-grep ordering inside each side, same convention as
# the prior front_desk migration.
ROLE_CHECK_PREV = (
    "role IN ('admin', 'clinician', 'front_desk', 'reviewer')"
)
ROLE_CHECK_NEXT = (
    "role IN ('admin', 'biller_coder', 'clinician', "
    "'front_desk', 'reviewer', 'technician')"
)


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint("ck_users_role_allowed", ROLE_CHECK_NEXT)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint("ck_users_role_allowed", ROLE_CHECK_PREV)
