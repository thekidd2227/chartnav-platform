"""Phase 78 — Anti-VEGF retina operating rail.

Adds one table that records structured anti-VEGF injection workflow
metadata. Phase 78 is **workflow intelligence**, not clinical
intelligence. The table is metadata + provider-review workflow only.

The ``anti_vegf_injections`` table records, per (encounter, eye):

  * which drug class label was injected (generic label only — no
    specific brand-name dosing protocol);
  * the date the injection was administered;
  * the planned next-due interval in weeks (provider-entered);
  * the next due date (provider-entered);
  * the authorization status (per-payer prior-auth state) tracked
    discretely so the work-queue surface can flag pending /
    expired auths without ChartNav making any payer decisions;
  * the lot number captured at administration (for provider-side
    inventory + recall tracking).

What this phase explicitly does NOT do:

  * recommend a drug, dose, or treatment plan;
  * decide whether an injection is medically appropriate;
  * interpret OCT / fundus / VF imagery to drive injection cadence;
  * autonomously submit a prior-auth or insurance claim;
  * order, refer, message patients, bill, or code;
  * autonomously sign anything.

Every action that mutates a row in this table requires explicit
provider review and a recorded ``created_by_user_id``. There is no
auto-create path.

Every row is ``organization_id``-scoped. The route layer enforces
the standard ``ensure_same_org`` + 404-on-cross-org invariant; the
foreign keys here only enforce referential integrity within the org.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EYE_VALUES = ("OD", "OS")

# Drug class labels are deliberately generic. The product does not
# choose between brand names or dosing regimens — the provider records
# what they administered. Vendor / brand-specific dosing decisions are
# out of scope for ChartNav.
_DRUG_LABELS = (
    "anti_vegf_generic",
    "anti_vegf_biosimilar",
    "anti_vegf_branded",
    "other",
)

_AUTH_STATUSES = (
    "not_required",
    "pending",
    "approved",
    "denied",
    "expired",
    "unknown",
)


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "anti_vegf_injections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("eye", sa.String(length=2), nullable=False),
        sa.Column(
            "drug_label",
            sa.String(length=64),
            nullable=False,
            server_default="anti_vegf_generic",
        ),
        sa.Column(
            "injection_date", sa.Date(), nullable=False
        ),
        sa.Column(
            "interval_weeks", sa.Integer(), nullable=True
        ),
        sa.Column(
            "next_due_date", sa.Date(), nullable=True
        ),
        sa.Column(
            "authorization_status",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "authorization_expires_on", sa.Date(), nullable=True
        ),
        sa.Column(
            "lot_number", sa.String(length=64), nullable=True
        ),
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
            name="fk_anti_vegf_injections_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_anti_vegf_injections_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_anti_vegf_injections_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_anti_vegf_injections_creator",
        ),
        sa.CheckConstraint(
            f"eye IN ({_csv(_EYE_VALUES)})",
            name="ck_anti_vegf_injections_eye_allowed",
        ),
        sa.CheckConstraint(
            f"drug_label IN ({_csv(_DRUG_LABELS)})",
            name="ck_anti_vegf_injections_drug_allowed",
        ),
        sa.CheckConstraint(
            f"authorization_status IN ({_csv(_AUTH_STATUSES)})",
            name="ck_anti_vegf_injections_auth_status_allowed",
        ),
        sa.CheckConstraint(
            "interval_weeks IS NULL OR (interval_weeks >= 1 AND interval_weeks <= 52)",
            name="ck_anti_vegf_injections_interval_range",
        ),
    )
    op.create_index(
        "ix_anti_vegf_injections_org_patient",
        "anti_vegf_injections",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_anti_vegf_injections_patient_eye_date",
        "anti_vegf_injections",
        ["patient_id", "eye", "injection_date"],
    )
    op.create_index(
        "ix_anti_vegf_injections_org_next_due",
        "anti_vegf_injections",
        ["organization_id", "next_due_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_anti_vegf_injections_org_next_due", table_name="anti_vegf_injections"
    )
    op.drop_index(
        "ix_anti_vegf_injections_patient_eye_date",
        table_name="anti_vegf_injections",
    )
    op.drop_index(
        "ix_anti_vegf_injections_org_patient",
        table_name="anti_vegf_injections",
    )
    op.drop_table("anti_vegf_injections")
