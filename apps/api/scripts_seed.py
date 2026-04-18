"""Idempotent seed for ChartNav local SQLite.

Seeds:
  - one demo organization (demo-eye-clinic)
  - one demo location (Main Clinic)
  - one demo admin user (admin@chartnav.local)
  - two demo encounters covering the workflow state machine:
      * PT-1001 Morgan Lee    / Dr. Carter / status = in_progress
      * PT-1002 Jordan Rivera / Dr. Patel  / status = review_needed
  - workflow events that model the lifecycle history of each encounter

Running the script repeatedly is safe: each insert is guarded by a
uniqueness check so no duplicate rows are created.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chartnav.db"

DEMO_ORG_SLUG = "demo-eye-clinic"
DEMO_ORG_NAME = "Demo Eye Clinic"
DEMO_LOCATION_NAME = "Main Clinic"
DEMO_ADMIN_EMAIL = "admin@chartnav.local"
DEMO_ADMIN_NAME = "ChartNav Admin"

# encounter fixtures: (patient_id, patient_name, provider, final_status, events)
# events use status_changed rows to reconstruct a realistic lifecycle so the
# demo UI / docs can show a filled-in history.
DEMO_ENCOUNTERS = [
    {
        "patient_identifier": "PT-1001",
        "patient_name": "Morgan Lee",
        "provider_name": "Dr. Carter",
        "status": "in_progress",
        "events": [
            ("encounter_created", {"source": "seed", "status": "scheduled"}),
            (
                "status_changed",
                {"old_status": "scheduled", "new_status": "in_progress"},
            ),
            (
                "note_draft_requested",
                {
                    "requested_by": DEMO_ADMIN_EMAIL,
                    "template": "cataract-followup",
                },
            ),
        ],
    },
    {
        "patient_identifier": "PT-1002",
        "patient_name": "Jordan Rivera",
        "provider_name": "Dr. Patel",
        "status": "review_needed",
        "events": [
            ("encounter_created", {"source": "seed", "status": "scheduled"}),
            (
                "status_changed",
                {"old_status": "scheduled", "new_status": "in_progress"},
            ),
            (
                "status_changed",
                {"old_status": "in_progress", "new_status": "draft_ready"},
            ),
            (
                "status_changed",
                {"old_status": "draft_ready", "new_status": "review_needed"},
            ),
            (
                "note_draft_completed",
                {"template": "glaucoma-initial", "length_words": 184},
            ),
        ],
    },
]


def _get_or_create_org(cur: sqlite3.Cursor) -> int:
    cur.execute(
        """
        INSERT INTO organizations (name, slug)
        SELECT ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = ?)
        """,
        (DEMO_ORG_NAME, DEMO_ORG_SLUG, DEMO_ORG_SLUG),
    )
    cur.execute("SELECT id FROM organizations WHERE slug = ?", (DEMO_ORG_SLUG,))
    return cur.fetchone()[0]


def _get_or_create_location(cur: sqlite3.Cursor, org_id: int) -> int:
    cur.execute(
        """
        INSERT INTO locations (organization_id, name)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM locations WHERE organization_id = ? AND name = ?
        )
        """,
        (org_id, DEMO_LOCATION_NAME, org_id, DEMO_LOCATION_NAME),
    )
    cur.execute(
        "SELECT id FROM locations WHERE organization_id = ? AND name = ?",
        (org_id, DEMO_LOCATION_NAME),
    )
    return cur.fetchone()[0]


def _ensure_admin_user(cur: sqlite3.Cursor, org_id: int) -> None:
    cur.execute(
        """
        INSERT INTO users (organization_id, email, full_name, role)
        SELECT ?, ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = ?)
        """,
        (org_id, DEMO_ADMIN_EMAIL, DEMO_ADMIN_NAME, "admin", DEMO_ADMIN_EMAIL),
    )


def _get_or_create_encounter(
    cur: sqlite3.Cursor, org_id: int, location_id: int, fixture: dict
) -> int:
    # started_at / completed_at are stamped based on fixture final status so
    # the seeded row stays consistent with the state machine's invariants.
    started_at = None
    completed_at = None
    if fixture["status"] in {
        "in_progress",
        "draft_ready",
        "review_needed",
        "completed",
    }:
        started_at_expr = "CURRENT_TIMESTAMP"
    else:
        started_at_expr = "NULL"
    completed_expr = (
        "CURRENT_TIMESTAMP" if fixture["status"] == "completed" else "NULL"
    )

    cur.execute(
        f"""
        INSERT INTO encounters (
            organization_id, location_id,
            patient_identifier, patient_name,
            provider_name, status,
            started_at, completed_at
        )
        SELECT ?, ?, ?, ?, ?, ?, {started_at_expr}, {completed_expr}
        WHERE NOT EXISTS (
            SELECT 1 FROM encounters
            WHERE organization_id = ?
              AND location_id = ?
              AND patient_identifier = ?
              AND provider_name = ?
        )
        """,
        (
            org_id,
            location_id,
            fixture["patient_identifier"],
            fixture["patient_name"],
            fixture["provider_name"],
            fixture["status"],
            org_id,
            location_id,
            fixture["patient_identifier"],
            fixture["provider_name"],
        ),
    )
    cur.execute(
        """
        SELECT id FROM encounters
        WHERE organization_id = ?
          AND location_id = ?
          AND patient_identifier = ?
          AND provider_name = ?
        """,
        (
            org_id,
            location_id,
            fixture["patient_identifier"],
            fixture["provider_name"],
        ),
    )
    return cur.fetchone()[0]


def _ensure_events(cur: sqlite3.Cursor, encounter_id: int, events: list) -> None:
    for event_type, data in events:
        payload = json.dumps(data, sort_keys=True)
        cur.execute(
            """
            INSERT INTO workflow_events (encounter_id, event_type, event_data)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM workflow_events
                WHERE encounter_id = ?
                  AND event_type = ?
                  AND IFNULL(event_data, '') = ?
            )
            """,
            (encounter_id, event_type, payload, encounter_id, event_type, payload),
        )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()

        org_id = _get_or_create_org(cur)
        location_id = _get_or_create_location(cur, org_id)
        _ensure_admin_user(cur, org_id)

        for fixture in DEMO_ENCOUNTERS:
            enc_id = _get_or_create_encounter(cur, org_id, location_id, fixture)
            _ensure_events(cur, enc_id, fixture["events"])

        conn.commit()

        print("Seed complete.")
        print(f"organization_id={org_id} location_id={location_id}")

        rows = cur.execute(
            """
            SELECT e.id, e.patient_identifier, e.provider_name, e.status,
                   (SELECT COUNT(*) FROM workflow_events w WHERE w.encounter_id = e.id) AS event_count
            FROM encounters e
            WHERE e.organization_id = ?
            ORDER BY e.id
            """,
            (org_id,),
        ).fetchall()
        print("encounters:", rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
