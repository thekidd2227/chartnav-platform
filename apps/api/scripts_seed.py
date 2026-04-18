"""Idempotent seed for ChartNav local SQLite.

Seeds:
  - one demo organization (demo-eye-clinic)
  - one demo location (Main Clinic)
  - one demo admin user (admin@chartnav.local)
  - one demo encounter (patient PT-1001 / Morgan Lee)
  - two workflow events for that encounter

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

DEMO_PATIENT_ID = "PT-1001"
DEMO_PATIENT_NAME = "Morgan Lee"
DEMO_PROVIDER = "Dr. Carter"
DEMO_STATUS = "in_progress"

DEMO_EVENTS = [
    ("encounter_created", {"source": "seed"}),
    (
        "note_draft_requested",
        {"requested_by": DEMO_ADMIN_EMAIL, "template": "cataract-followup"},
    ),
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
        (
            org_id,
            DEMO_ADMIN_EMAIL,
            DEMO_ADMIN_NAME,
            "admin",
            DEMO_ADMIN_EMAIL,
        ),
    )


def _get_or_create_encounter(
    cur: sqlite3.Cursor, org_id: int, location_id: int
) -> int:
    cur.execute(
        """
        INSERT INTO encounters (
            organization_id, location_id,
            patient_identifier, patient_name,
            provider_name, status, started_at
        )
        SELECT ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
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
            DEMO_PATIENT_ID,
            DEMO_PATIENT_NAME,
            DEMO_PROVIDER,
            DEMO_STATUS,
            org_id,
            location_id,
            DEMO_PATIENT_ID,
            DEMO_PROVIDER,
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
        (org_id, location_id, DEMO_PATIENT_ID, DEMO_PROVIDER),
    )
    return cur.fetchone()[0]


def _ensure_events(cur: sqlite3.Cursor, encounter_id: int) -> None:
    for event_type, data in DEMO_EVENTS:
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
        encounter_id = _get_or_create_encounter(cur, org_id, location_id)
        _ensure_events(cur, encounter_id)

        conn.commit()

        print("Seed complete.")
        print(
            f"organization_id={org_id} location_id={location_id} encounter_id={encounter_id}"
        )

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
