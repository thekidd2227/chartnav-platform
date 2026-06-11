"""Phase 90 — Ophthalmic Medication Safety & Adherence Engine.

Extends the existing ``medications`` table (Phase 85) with adherence
+ review columns, and adds two new tables that together encode the
deterministic medication-safety rule engine:

  * ``medication_safety_rules``   — closed allowlist of rules
                                    (preservative-burden advisory,
                                    refill-gap advisory, etc.). The
                                    application seeds five demo
                                    rules; new rules require a
                                    migration + service change.
  * ``medication_safety_events``  — provider-reviewable events
                                    surfaced by the rule engine.

New medication columns:

  * ``preservative_type``  — BAK / preservative_free / other / unknown
                              (CHECK enum). Coexists with the Phase 85
                              ``preservative_flag`` boolean — both
                              update together at the service layer.
  * ``last_fill_date``      — date of the most recent provider-entered
                              refill, denormalized so the adherence
                              projection doesn't re-walk the
                              medication_refills table on every read.
  * ``days_supply``         — provider-entered nominal days-supply
                              for the active fill (1-365 CHECK).
  * ``reviewed_by_user_id`` — provider who reviewed the medication
                              entry (admin / clinician).
  * ``reviewed_at``         — timestamp of the most recent provider
                              review.

Hard rules expressed by the schema:

  * ``preservative_type`` is a closed allowlist (CHECK).
  * ``severity`` on rules and events is closed: hard_stop / alert /
    advisory. Phase 90's seeded rules use advisory only; hard_stop is
    reserved for a future qualified-operator extension.
  * ``status`` on events is closed: active / acknowledged / resolved.
  * ``laterality`` on events: OD / OS / OU / none.
  * (organization_id, rule_key) is UNIQUE on rules (or NULL/global
    when org-scoped).
  * Indexes: per-patient + per-encounter on events.

This phase is **provider-reviewed workflow safety support**.
ChartNav does NOT prescribe, does NOT recommend medication changes,
does NOT diagnose, does NOT interpret images, does NOT recommend
treatment / surgery, does NOT submit to pharmacies, payers, or
EHRs.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PRESERVATIVE_TYPES = ("BAK", "preservative_free", "other", "unknown")
_RULE_SEVERITIES = ("hard_stop", "alert", "advisory")
_EVENT_SEVERITIES = ("hard_stop", "alert", "advisory")
_EVENT_STATUSES = ("active", "acknowledged", "resolved")
_EVENT_LATERALITIES = ("OD", "OS", "OU", "none")
_RULE_STATUSES = ("active", "inactive")


def _csv(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # --- extend medications ----------------------------------------
    with op.batch_alter_table("medications") as batch:
        batch.add_column(
            sa.Column(
                "preservative_type",
                sa.String(length=24),
                nullable=False,
                server_default="unknown",
            )
        )
        batch.add_column(
            sa.Column("last_fill_date", sa.Date(), nullable=True)
        )
        batch.add_column(
            sa.Column("days_supply", sa.Integer(), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "reviewed_by_user_id", sa.Integer(), nullable=True
            )
        )
        batch.add_column(
            sa.Column(
                "reviewed_at", sa.DateTime(timezone=True), nullable=True
            )
        )
        batch.create_check_constraint(
            "ck_medications_preservative_type_allowed",
            f"preservative_type IN ({_csv(_PRESERVATIVE_TYPES)})",
        )
        batch.create_check_constraint(
            "ck_medications_days_supply_range",
            "days_supply IS NULL OR (days_supply >= 1 AND days_supply <= 365)",
        )
        batch.create_foreign_key(
            "fk_medications_reviewed_by",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
        )

    # --- medication_safety_rules ---------------------------------
    op.create_table(
        "medication_safety_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column(
            "medication_class", sa.String(length=48), nullable=True
        ),
        sa.Column(
            "trigger_context", sa.String(length=64), nullable=False
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column(
            "requires_acknowledgement",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
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
            name="fk_medication_safety_rules_org",
        ),
        sa.CheckConstraint(
            "length(rule_key) > 0",
            name="ck_medication_safety_rules_key_nonempty",
        ),
        sa.CheckConstraint(
            "length(rule_name) > 0",
            name="ck_medication_safety_rules_name_nonempty",
        ),
        sa.CheckConstraint(
            f"severity IN ({_csv(_RULE_SEVERITIES)})",
            name="ck_medication_safety_rules_severity_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_RULE_STATUSES)})",
            name="ck_medication_safety_rules_status_allowed",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "rule_key",
            name="uq_medication_safety_rules_org_key",
        ),
    )
    op.create_index(
        "ix_medication_safety_rules_active",
        "medication_safety_rules",
        ["status", "trigger_context"],
    )

    # --- medication_safety_events --------------------------------
    op.create_table(
        "medication_safety_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("medication_id", sa.Integer(), nullable=True),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column(
            "laterality",
            sa.String(length=8),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "message", sa.String(length=512), nullable=False
        ),
        sa.Column(
            "acknowledged_by_user_id", sa.Integer(), nullable=True
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            name="fk_medication_safety_events_org",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medication_safety_events_patient",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_medication_safety_events_encounter",
        ),
        sa.ForeignKeyConstraint(
            ["medication_id"],
            ["medications.id"],
            name="fk_medication_safety_events_medication",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_user_id"],
            ["users.id"],
            name="fk_medication_safety_events_ack_by",
        ),
        sa.CheckConstraint(
            "length(rule_key) > 0",
            name="ck_medication_safety_events_rule_key_nonempty",
        ),
        sa.CheckConstraint(
            f"severity IN ({_csv(_EVENT_SEVERITIES)})",
            name="ck_medication_safety_events_severity_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_csv(_EVENT_STATUSES)})",
            name="ck_medication_safety_events_status_allowed",
        ),
        sa.CheckConstraint(
            f"laterality IN ({_csv(_EVENT_LATERALITIES)})",
            name="ck_medication_safety_events_laterality_allowed",
        ),
    )
    op.create_index(
        "ix_medication_safety_events_org_patient",
        "medication_safety_events",
        ["organization_id", "patient_id"],
    )
    op.create_index(
        "ix_medication_safety_events_org_encounter",
        "medication_safety_events",
        ["organization_id", "encounter_id"],
    )
    op.create_index(
        "ix_medication_safety_events_status",
        "medication_safety_events",
        ["status", "severity"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_medication_safety_events_status",
        table_name="medication_safety_events",
    )
    op.drop_index(
        "ix_medication_safety_events_org_encounter",
        table_name="medication_safety_events",
    )
    op.drop_index(
        "ix_medication_safety_events_org_patient",
        table_name="medication_safety_events",
    )
    op.drop_table("medication_safety_events")
    op.drop_index(
        "ix_medication_safety_rules_active",
        table_name="medication_safety_rules",
    )
    op.drop_table("medication_safety_rules")
    with op.batch_alter_table("medications") as batch:
        batch.drop_constraint(
            "fk_medications_reviewed_by", type_="foreignkey"
        )
        batch.drop_constraint(
            "ck_medications_days_supply_range", type_="check"
        )
        batch.drop_constraint(
            "ck_medications_preservative_type_allowed", type_="check"
        )
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by_user_id")
        batch.drop_column("days_supply")
        batch.drop_column("last_fill_date")
        batch.drop_column("preservative_type")
