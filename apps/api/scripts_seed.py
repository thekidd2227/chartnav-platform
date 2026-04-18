"""Idempotent seed for ChartNav local SQLite.

Provisions two tenants with full role coverage so auth + RBAC + scoping
can be tested end-to-end.

  org #1 — demo-eye-clinic
    location:   Main Clinic
    users:
      admin@chartnav.local    (admin)
      clin@chartnav.local     (clinician)
      rev@chartnav.local      (reviewer)
    encounters:
      PT-1001 Morgan Lee    / Dr. Carter / in_progress   (3 events)
      PT-1002 Jordan Rivera / Dr. Patel  / review_needed (5 events)

  org #2 — northside-retina
    location:   Northside HQ
    users:
      admin@northside.local   (admin)
      clin@northside.local    (clinician)
    encounters:
      PT-2001 Priya Shah    / Dr. Ahmed  / scheduled     (1 event)
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chartnav.db"


ORGS = [
    {
        "slug": "demo-eye-clinic",
        "name": "Demo Eye Clinic",
        "location": "Main Clinic",
        "users": [
            ("admin@chartnav.local", "ChartNav Admin", "admin"),
            ("clin@chartnav.local", "Casey Clinician", "clinician"),
            ("rev@chartnav.local", "Riley Reviewer", "reviewer"),
        ],
        "encounters": [
            {
                "patient_identifier": "PT-1001",
                "patient_name": "Morgan Lee",
                "provider_name": "Dr. Carter",
                "status": "in_progress",
                "events": [
                    ("encounter_created", {"source": "seed", "status": "scheduled"}),
                    ("status_changed", {"old_status": "scheduled", "new_status": "in_progress"}),
                    (
                        "note_draft_requested",
                        {"requested_by": "admin@chartnav.local", "template": "cataract-followup"},
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
                    ("status_changed", {"old_status": "scheduled", "new_status": "in_progress"}),
                    ("status_changed", {"old_status": "in_progress", "new_status": "draft_ready"}),
                    ("status_changed", {"old_status": "draft_ready", "new_status": "review_needed"}),
                    (
                        "note_draft_completed",
                        {"template": "glaucoma-initial", "length_words": 184},
                    ),
                ],
            },
        ],
    },
    {
        "slug": "northside-retina",
        "name": "Northside Retina Center",
        "location": "Northside HQ",
        "users": [
            ("admin@northside.local", "Northside Admin", "admin"),
            ("clin@northside.local", "Noa Clinician", "clinician"),
        ],
        "encounters": [
            {
                "patient_identifier": "PT-2001",
                "patient_name": "Priya Shah",
                "provider_name": "Dr. Ahmed",
                "status": "scheduled",
                "events": [
                    ("encounter_created", {"source": "seed", "status": "scheduled"}),
                ],
            },
        ],
    },
]


def _get_or_create_org(cur, slug, name):
    cur.execute(
        "INSERT INTO organizations (name, slug) "
        "SELECT ?, ? WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = ?)",
        (name, slug, slug),
    )
    cur.execute("SELECT id FROM organizations WHERE slug = ?", (slug,))
    return cur.fetchone()[0]


def _get_or_create_location(cur, org_id, name):
    cur.execute(
        "INSERT INTO locations (organization_id, name) "
        "SELECT ?, ? WHERE NOT EXISTS ("
        "SELECT 1 FROM locations WHERE organization_id = ? AND name = ?)",
        (org_id, name, org_id, name),
    )
    cur.execute(
        "SELECT id FROM locations WHERE organization_id = ? AND name = ?",
        (org_id, name),
    )
    return cur.fetchone()[0]


def _ensure_user(cur, org_id, email, full_name, role):
    # If the user exists, keep the role in sync with what the seed declares
    # so a re-seed after schema/role changes converges deterministically.
    cur.execute(
        "INSERT INTO users (organization_id, email, full_name, role) "
        "SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = ?)",
        (org_id, email, full_name, role, email),
    )
    cur.execute(
        "UPDATE users SET role = ?, organization_id = ?, full_name = ? "
        "WHERE email = ?",
        (role, org_id, full_name, email),
    )


def _get_or_create_encounter(cur, org_id, location_id, fx):
    if fx["status"] in {"in_progress", "draft_ready", "review_needed", "completed"}:
        started_expr = "CURRENT_TIMESTAMP"
    else:
        started_expr = "NULL"
    completed_expr = "CURRENT_TIMESTAMP" if fx["status"] == "completed" else "NULL"

    cur.execute(
        f"""
        INSERT INTO encounters (
            organization_id, location_id,
            patient_identifier, patient_name,
            provider_name, status,
            started_at, completed_at
        )
        SELECT ?, ?, ?, ?, ?, ?, {started_expr}, {completed_expr}
        WHERE NOT EXISTS (
            SELECT 1 FROM encounters
            WHERE organization_id = ?
              AND location_id = ?
              AND patient_identifier = ?
              AND provider_name = ?
        )
        """,
        (
            org_id, location_id,
            fx["patient_identifier"], fx["patient_name"],
            fx["provider_name"], fx["status"],
            org_id, location_id,
            fx["patient_identifier"], fx["provider_name"],
        ),
    )
    cur.execute(
        "SELECT id FROM encounters WHERE organization_id = ? AND location_id = ? "
        "AND patient_identifier = ? AND provider_name = ?",
        (org_id, location_id, fx["patient_identifier"], fx["provider_name"]),
    )
    return cur.fetchone()[0]


def _ensure_events(cur, encounter_id, events):
    for event_type, data in events:
        payload = json.dumps(data, sort_keys=True)
        cur.execute(
            "INSERT INTO workflow_events (encounter_id, event_type, event_data) "
            "SELECT ?, ?, ? WHERE NOT EXISTS ("
            "SELECT 1 FROM workflow_events WHERE encounter_id = ? "
            "AND event_type = ? AND IFNULL(event_data, '') = ?)",
            (encounter_id, event_type, payload, encounter_id, event_type, payload),
        )


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()

        summary = []
        for org_fx in ORGS:
            org_id = _get_or_create_org(cur, org_fx["slug"], org_fx["name"])
            loc_id = _get_or_create_location(cur, org_id, org_fx["location"])
            for email, full_name, role in org_fx["users"]:
                _ensure_user(cur, org_id, email, full_name, role)
            for enc_fx in org_fx["encounters"]:
                enc_id = _get_or_create_encounter(cur, org_id, loc_id, enc_fx)
                _ensure_events(cur, enc_id, enc_fx["events"])
            summary.append((org_fx["slug"], org_id, loc_id))

        conn.commit()

        print("Seed complete.")
        for slug, org_id, loc_id in summary:
            print(f"  {slug}: organization_id={org_id} location_id={loc_id}")
        rows = cur.execute(
            "SELECT o.slug, u.email, u.role FROM users u "
            "JOIN organizations o ON o.id = u.organization_id ORDER BY o.id, u.id"
        ).fetchall()
        print("users:", rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
