"""fundus_charts table

Revision ID: e1f2a3041508
Revises: e1f2a3041507
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op

revision = "e1f2a3041508"
down_revision = "e1f2a3041507"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE fundus_charts (
            id                  INTEGER      PRIMARY KEY AUTOINCREMENT,
            created_at          DATETIME     NOT NULL DEFAULT (datetime('now')),
            updated_at          DATETIME     NOT NULL DEFAULT (datetime('now')),
            organization_id     INTEGER      NOT NULL REFERENCES organizations(id),
            encounter_id        INTEGER      NOT NULL REFERENCES encounters(id),
            patient_id          INTEGER      NOT NULL,
            note_version_id     INTEGER,
            laterality          VARCHAR(8)   NOT NULL DEFAULT 'OD',
            status              VARCHAR(32)  NOT NULL DEFAULT 'draft',
            source_type         VARCHAR(32)  NOT NULL DEFAULT 'ai_generated',
            findings_json       TEXT,
            drawing_json        TEXT         NOT NULL DEFAULT '{}',
            rendered_svg        TEXT,
            ai_model_name       VARCHAR(128),
            ai_confidence_json  TEXT,
            warnings_json       TEXT,
            reviewed_by_user_id INTEGER      REFERENCES users(id),
            reviewed_at         DATETIME,
            signed_by_user_id   INTEGER      REFERENCES users(id),
            signed_at           DATETIME,
            created_by_user_id  INTEGER      NOT NULL REFERENCES users(id)
        )
        """
    )
    op.execute("CREATE INDEX ix_fundus_charts_org ON fundus_charts (organization_id)")
    op.execute("CREATE INDEX ix_fundus_charts_encounter ON fundus_charts (encounter_id)")
    op.execute("CREATE INDEX ix_fundus_charts_status ON fundus_charts (status)")
    op.execute("CREATE INDEX ix_fundus_charts_laterality ON fundus_charts (laterality)")
    op.execute("CREATE INDEX ix_fundus_charts_signed_at ON fundus_charts (signed_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fundus_charts")
