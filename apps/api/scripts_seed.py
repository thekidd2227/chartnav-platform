"""Idempotent seed for ChartNav. Cross-dialect (SQLite + Postgres).

Uses SQLAlchemy Core via `app.db` so the same seed runs against either
backend. All SQL uses portable constructs (`COALESCE`, named binds).
"""

from __future__ import annotations

import json

from sqlalchemy import text

from app.db import insert_returning_id, transaction

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
        "patients": [
            {
                "patient_identifier": "PT-1001",
                "first_name": "Morgan",
                "last_name": "Lee",
                "date_of_birth": "1962-03-14",
                "sex_at_birth": "female",
            },
            {
                "patient_identifier": "PT-1002",
                "first_name": "Jordan",
                "last_name": "Rivera",
                "date_of_birth": "1954-11-02",
                "sex_at_birth": "male",
            },
        ],
        "providers": [
            {"display_name": "Dr. Carter", "npi": "1234567893", "specialty": "Ophthalmology"},
            {"display_name": "Dr. Patel", "npi": "1932456321", "specialty": "Ophthalmology"},
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
        "patients": [
            {
                "patient_identifier": "PT-2001",
                "first_name": "Priya",
                "last_name": "Shah",
                "date_of_birth": "1948-07-20",
                "sex_at_birth": "female",
            },
        ],
        "providers": [
            {"display_name": "Dr. Ahmed", "npi": "1609995340", "specialty": "Retina"},
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


def _get_or_create_org(conn, slug: str, name: str) -> int:
    row = conn.execute(
        text("SELECT id FROM organizations WHERE slug = :slug"),
        {"slug": slug},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn, "organizations", {"name": name, "slug": slug}
    )


def _get_or_create_location(conn, org_id: int, name: str) -> int:
    row = conn.execute(
        text(
            "SELECT id FROM locations "
            "WHERE organization_id = :org AND name = :name"
        ),
        {"org": org_id, "name": name},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn, "locations", {"organization_id": org_id, "name": name}
    )


def _ensure_user(conn, org_id: int, email: str, full_name: str, role: str) -> None:
    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).mappings().first()
    if not row:
        insert_returning_id(
            conn,
            "users",
            {
                "organization_id": org_id,
                "email": email,
                "full_name": full_name,
                "role": role,
            },
        )
    else:
        conn.execute(
            text(
                "UPDATE users SET role = :role, organization_id = :org, "
                "full_name = :full_name WHERE email = :email"
            ),
            {"role": role, "org": org_id, "full_name": full_name, "email": email},
        )


def _ensure_patient(conn, org_id: int, fx: dict) -> int:
    """Idempotent patient upsert keyed on (org_id, patient_identifier)."""
    row = conn.execute(
        text(
            "SELECT id FROM patients WHERE organization_id = :org "
            "AND patient_identifier = :pid"
        ),
        {"org": org_id, "pid": fx["patient_identifier"]},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "patients",
        {
            "organization_id": org_id,
            "patient_identifier": fx["patient_identifier"],
            "first_name": fx["first_name"],
            "last_name": fx["last_name"],
            "date_of_birth": fx.get("date_of_birth"),
            "sex_at_birth": fx.get("sex_at_birth"),
        },
    )


def _ensure_provider(conn, org_id: int, fx: dict) -> int:
    """Idempotent provider upsert keyed on (org_id, display_name).

    NPI is unique-per-org when non-null; display_name is used as the
    dedupe key so re-seeding across NPI changes stays idempotent.
    """
    row = conn.execute(
        text(
            "SELECT id FROM providers WHERE organization_id = :org "
            "AND display_name = :name"
        ),
        {"org": org_id, "name": fx["display_name"]},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "providers",
        {
            "organization_id": org_id,
            "display_name": fx["display_name"],
            "npi": fx.get("npi"),
            "specialty": fx.get("specialty"),
        },
    )


def _get_or_create_encounter(
    conn, org_id: int, location_id: int, fx: dict,
    patient_id: int | None = None, provider_id: int | None = None,
) -> int:
    row = conn.execute(
        text(
            "SELECT id FROM encounters WHERE organization_id = :org AND "
            "location_id = :loc AND patient_identifier = :pid AND provider_name = :provider"
        ),
        {
            "org": org_id,
            "loc": location_id,
            "pid": fx["patient_identifier"],
            "provider": fx["provider_name"],
        },
    ).mappings().first()
    if row:
        # Backfill native linkage on re-seed even if row already exists.
        if patient_id or provider_id:
            conn.execute(
                text(
                    "UPDATE encounters SET patient_id = COALESCE(:pid_fk, patient_id), "
                    "provider_id = COALESCE(:prov_fk, provider_id) WHERE id = :id"
                ),
                {"pid_fk": patient_id, "prov_fk": provider_id, "id": int(row["id"])},
            )
        return int(row["id"])

    started = fx["status"] in {"in_progress", "draft_ready", "review_needed", "completed"}
    completed = fx["status"] == "completed"

    # Use DB-side CURRENT_TIMESTAMP for the timestamps so seed output is
    # consistent on both SQLite and Postgres.
    conn.execute(
        text(
            "INSERT INTO encounters ("
            "organization_id, location_id, patient_identifier, patient_name, "
            "provider_name, status, patient_id, provider_id, "
            "started_at, completed_at"
            ") VALUES ("
            ":org, :loc, :pid, :pname, :provider, :status, "
            ":pid_fk, :prov_fk, "
            + ("CURRENT_TIMESTAMP" if started else "NULL")
            + ", "
            + ("CURRENT_TIMESTAMP" if completed else "NULL")
            + ")"
        ),
        {
            "org": org_id,
            "loc": location_id,
            "pid": fx["patient_identifier"],
            "pname": fx["patient_name"],
            "provider": fx["provider_name"],
            "status": fx["status"],
            "pid_fk": patient_id,
            "prov_fk": provider_id,
        },
    )
    row = conn.execute(
        text(
            "SELECT id FROM encounters WHERE organization_id = :org AND "
            "location_id = :loc AND patient_identifier = :pid AND provider_name = :provider"
        ),
        {
            "org": org_id,
            "loc": location_id,
            "pid": fx["patient_identifier"],
            "provider": fx["provider_name"],
        },
    ).mappings().first()
    return int(row["id"])


def _ensure_events(conn, encounter_id: int, events: list) -> None:
    for event_type, data in events:
        payload = json.dumps(data, sort_keys=True)
        existing = conn.execute(
            text(
                "SELECT id FROM workflow_events WHERE encounter_id = :enc AND "
                "event_type = :type AND COALESCE(event_data, '') = :data"
            ),
            {"enc": encounter_id, "type": event_type, "data": payload},
        ).mappings().first()
        if existing:
            continue
        insert_returning_id(
            conn,
            "workflow_events",
            {
                "encounter_id": encounter_id,
                "event_type": event_type,
                "event_data": payload,
            },
        )


def main() -> None:
    summary = []
    with transaction() as conn:
        for org_fx in ORGS:
            org_id = _get_or_create_org(conn, org_fx["slug"], org_fx["name"])
            loc_id = _get_or_create_location(conn, org_id, org_fx["location"])
            for email, full_name, role in org_fx["users"]:
                _ensure_user(conn, org_id, email, full_name, role)

            # Native clinical objects (phase 18).
            patient_ids: dict[str, int] = {}
            for pat_fx in org_fx.get("patients", []):
                pid = _ensure_patient(conn, org_id, pat_fx)
                patient_ids[pat_fx["patient_identifier"]] = pid
            provider_ids: dict[str, int] = {}
            for prov_fx in org_fx.get("providers", []):
                pvid = _ensure_provider(conn, org_id, prov_fx)
                provider_ids[prov_fx["display_name"]] = pvid

            for enc_fx in org_fx["encounters"]:
                enc_id = _get_or_create_encounter(
                    conn, org_id, loc_id, enc_fx,
                    patient_id=patient_ids.get(enc_fx["patient_identifier"]),
                    provider_id=provider_ids.get(enc_fx["provider_name"]),
                )
                _ensure_events(conn, enc_id, enc_fx["events"])
            summary.append((org_fx["slug"], org_id, loc_id))

    print("Seed complete.")
    for slug, org_id, loc_id in summary:
        print(f"  {slug}: organization_id={org_id} location_id={loc_id}")


if __name__ == "__main__":
    main()
