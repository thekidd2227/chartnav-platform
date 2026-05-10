"""Phase 20C — extend users.role CHECK constraint with front_desk + technician.

Phase 20C ships role-based dashboards. Two additive operational roles
join the existing {admin, clinician, reviewer} set:

  * front_desk — schedule / check-in / checkout / follow-up lane
  * technician — workup / VA / IOP / refraction / dilation / testing /
                 imaging-needed / ready-for-doctor lane

Both roles are read-mostly. They do NOT inherit clinician write
privileges on existing surfaces (note signing, scribe sessions, eye
diagrams, etc.). Their write access is scoped to operational queue
items via the Phase 20B work_queue_items endpoints.

The Phase 20B schema already accepts these role enums in
``role_view_presets.role`` and ``clinic_workflow_*.role_owner`` —
this migration extends the matching ``users.role`` CHECK constraint
so seeded + invited users can carry these roles too.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Old constraint (Phase 11 governance) — kept here only for the
# downgrade path.
_OLD_ROLE_CHECK = "role IN ('admin', 'clinician', 'reviewer')"
_NEW_ROLE_CHECK = (
    "role IN ('admin', 'clinician', 'reviewer', "
    "'front_desk', 'technician')"
)


def upgrade() -> None:
    # batch_alter_table handles SQLite's lack of ALTER TABLE DROP
    # CONSTRAINT by rebuilding the table; same pattern Phase 11 used
    # to add the original constraint.
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint(
            "ck_users_role_allowed", _NEW_ROLE_CHECK
        )


def downgrade() -> None:
    # Reverting to the Phase 11 enum will fail loudly if any seeded /
    # invited user is currently carrying front_desk or technician —
    # that's intentional. Operators must reassign those users to
    # clinician (closest legacy role) before downgrading.
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role_allowed", type_="check")
        batch.create_check_constraint(
            "ck_users_role_allowed", _OLD_ROLE_CHECK
        )
