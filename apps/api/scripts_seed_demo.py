"""Phase 2 item 6 — deterministic demo seed.

Spec: docs/chartnav/closure/PHASE_B_Demo_Environment_and_Pilot_Scope.md

What this script does:
  - Adds a SECOND seeded organization ("Pilot Demo Eye Clinic" /
    slug "pilot-demo-eye-clinic") on top of whatever the standard
    scripts_seed.py already produced. The standard seed remains the
    test fixture; this one is the leave-behind demo profile that
    Sales / SE drives during pilot calls.
  - Produces the exact row counts called out in spec §3:
      * 6 staff identities (2 general-ophth clinicians + 1 retina
        clinician + 1 admin + 1 front_desk + 1 reviewer);
      * 20 encounters distributed across the four Phase A
        templates (general, glaucoma, cataract, retina);
      * 1 fully-signed encounter with a linked post-visit summary
        + a linked consult letter (full end-to-end);
      * Reminders spanning 14 days: 3 overdue, 5 complete, 4
        upcoming;
      * Intake tokens: 2 pending, 1 accepted, 1 expired.
  - Idempotent. Running twice (or running on top of the standard
    seed) produces no duplicate rows. Identifiers are natural-key
    (e.g. PT-DEMO-1001) so screenshots stay stable across runs.

Truth limitations preserved (spec §9):
  - Synthetic data only. We never demo real patient records.
  - Numbers are seeded — operators must not present them as live
    pilot metrics.
  - The clip-pack regeneration is documented but not regenerated
    by this script (the clip pack is a recording artifact, not
    deterministic seed data).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import text


def _insert_returning_id(conn, table: str, values: dict) -> int:
    """Lazy resolver — always pulls the live `app.db.insert_returning_id`
    so test fixtures that reload `app.*` modules per-test never see a
    stale-module reference (same trick the test_consult_letters
    helpers use)."""
    import app.db
    return app.db.insert_returning_id(conn, table, values)


def _transaction():
    import app.db
    return app.db.transaction()


DEMO_ORG_SLUG = "pilot-demo-eye-clinic"
DEMO_ORG_NAME = "Pilot Demo Eye Clinic"
DEMO_LOCATION_NAME = "Demo Main Clinic"


# ---- Required staff identities -------------------------------------

DEMO_USERS = [
    # (email, full_name, role, is_authorized_final_signer, is_lead)
    ("admin@pilot-demo.local",   "Pilot Demo Admin",      "admin",       False, False),
    ("front@pilot-demo.local",   "Pilot Demo Front Desk", "front_desk",  False, False),
    ("rev@pilot-demo.local",     "Pilot Demo Reviewer",   "reviewer",    False, False),
    ("dr.smith@pilot-demo.local","Dr. Smith (Gen Ophth)", "clinician",   True,  True),
    ("dr.jones@pilot-demo.local","Dr. Jones (Gen Ophth)", "clinician",   True,  False),
    ("dr.lee@pilot-demo.local",  "Dr. Lee (Retina)",      "clinician",   True,  False),
]


# ---- 20 encounters across the four Phase A templates ---------------

# 5 per template × 4 templates = 20 encounters.
TEMPLATE_DISTRIBUTION = [
    "general_ophthalmology",
    "glaucoma",
    "anterior_segment_cataract",
    "retina",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_org(conn, slug: str, name: str) -> int:
    r = conn.execute(
        text("SELECT id FROM organizations WHERE slug = :s"), {"s": slug}
    ).mappings().first()
    if r:
        return int(r["id"])
    return _insert_returning_id(
        conn, "organizations", {"slug": slug, "name": name}
    )


def _get_or_create_location(conn, org_id: int, name: str) -> int:
    r = conn.execute(
        text(
            "SELECT id FROM locations WHERE organization_id = :o AND name = :n"
        ),
        {"o": org_id, "n": name},
    ).mappings().first()
    if r:
        return int(r["id"])
    return _insert_returning_id(
        conn, "locations", {"organization_id": org_id, "name": name}
    )


def _ensure_user(conn, org_id: int, email: str, full_name: str, role: str,
                 final_signer: bool, is_lead: bool) -> int:
    r = conn.execute(
        text("SELECT id FROM users WHERE email = :e"), {"e": email}
    ).mappings().first()
    if r:
        # Keep attributes in sync but don't bounce the row id.
        conn.execute(
            text(
                "UPDATE users SET organization_id = :o, full_name = :fn, "
                "  role = :r, is_authorized_final_signer = :fs, is_lead = :il "
                "WHERE email = :e"
            ),
            {"o": org_id, "fn": full_name, "r": role,
             "fs": int(bool(final_signer)), "il": int(bool(is_lead)), "e": email},
        )
        return int(r["id"])
    return _insert_returning_id(
        conn, "users",
        {
            "organization_id": org_id, "email": email, "full_name": full_name,
            "role": role,
            "is_authorized_final_signer": int(bool(final_signer)),
            "is_lead": int(bool(is_lead)),
        },
    )


def _ensure_patient(conn, org_id: int, identifier: str, name: str) -> int:
    r = conn.execute(
        text(
            "SELECT id FROM patients WHERE organization_id = :o "
            "AND patient_identifier = :p"
        ),
        {"o": org_id, "p": identifier},
    ).mappings().first()
    if r:
        return int(r["id"])
    parts = name.split(" ", 1)
    return _insert_returning_id(
        conn, "patients",
        {
            "organization_id": org_id,
            "patient_identifier": identifier,
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else "",
        },
    )


def _ensure_encounter(
    conn, *, org_id: int, location_id: int, patient_id: int,
    patient_identifier: str, patient_name: str, provider_name: str,
    template_key: str, status: str = "scheduled",
    completed_at: datetime | None = None,
) -> int:
    """Natural-key idempotent: (org_id, patient_identifier, template_key)."""
    r = conn.execute(
        text(
            "SELECT id FROM encounters "
            "WHERE organization_id = :o AND patient_identifier = :p "
            "AND template_key = :t"
        ),
        {"o": org_id, "p": patient_identifier, "t": template_key},
    ).mappings().first()
    if r:
        return int(r["id"])
    return _insert_returning_id(
        conn, "encounters",
        {
            "organization_id": org_id,
            "location_id": location_id,
            "patient_identifier": patient_identifier,
            "patient_name": patient_name,
            "provider_name": provider_name,
            "template_key": template_key,
            "status": status,
            "patient_id": patient_id,
            "completed_at": completed_at.isoformat(timespec="seconds") if completed_at else None,
        },
    )


def _ensure_signed_note(conn, *, encounter_id: int, note_text: str) -> int:
    r = conn.execute(
        text(
            "SELECT id FROM note_versions WHERE encounter_id = :e "
            "ORDER BY version_number DESC LIMIT 1"
        ),
        {"e": encounter_id},
    ).mappings().first()
    if r:
        return int(r["id"])
    return _insert_returning_id(
        conn, "note_versions",
        {
            "encounter_id": encounter_id,
            "version_number": 1,
            "draft_status": "signed",
            "note_format": "soap",
            "note_text": note_text,
            "generated_by": "manual",
            "provider_review_required": 0,
            "missing_data_flags": "[]",
            "signed_at": _now().isoformat(timespec="seconds"),
            "signed_by_user_id": 1,
        },
    )


def _ensure_reminder(
    conn, *, org_id: int, title: str, due_at: datetime, status: str,
    created_by: int,
) -> None:
    r = conn.execute(
        text(
            "SELECT id FROM reminders WHERE organization_id = :o AND title = :t"
        ),
        {"o": org_id, "t": title},
    ).mappings().first()
    if r:
        return
    _insert_returning_id(
        conn, "reminders",
        {
            "organization_id": org_id,
            "title": title,
            "body": "Pilot demo seed reminder.",
            "due_at": due_at.isoformat(timespec="seconds"),
            "status": status,
            "completed_at": _now().isoformat(timespec="seconds") if status == "completed" else None,
            "completed_by_user_id": created_by if status == "completed" else None,
            "created_by_user_id": created_by,
        },
    )


def _ensure_intake_token(
    conn, *, org_id: int, candidate: str, used: bool, expired: bool,
    created_by: int,
) -> int:
    """Token rows for the demo. Natural key = candidate identifier
    (NOT a real token; demo only)."""
    r = conn.execute(
        text(
            "SELECT id FROM intake_tokens "
            "WHERE organization_id = :o AND patient_identifier_candidate = :p"
        ),
        {"o": org_id, "p": candidate},
    ).mappings().first()
    if r:
        return int(r["id"])
    expires_at = _now() + (timedelta(hours=-1) if expired else timedelta(hours=72))
    used_at = _now().isoformat(timespec="seconds") if used else None
    # Hash a deterministic dummy so the row exists; the raw token is
    # never recoverable for the demo seed (operators issue real tokens
    # via the UI during a live pilot).
    import hashlib
    tok_hash = hashlib.sha256(f"demo:{candidate}".encode()).hexdigest()
    return _insert_returning_id(
        conn, "intake_tokens",
        {
            "organization_id": org_id,
            "token_hash": tok_hash,
            "patient_identifier_candidate": candidate,
            "expires_at": expires_at.isoformat(timespec="seconds"),
            "used_at": used_at,
            "created_by_user_id": created_by,
        },
    )


def _ensure_intake_submission(conn, *, org_id: int, token_id: int, status: str) -> None:
    r = conn.execute(
        text("SELECT id FROM intake_submissions WHERE token_id = :t"),
        {"t": token_id},
    ).mappings().first()
    if r:
        return
    payload = {"patient_name": "Demo Submission", "consent": True}
    _insert_returning_id(
        conn, "intake_submissions",
        {
            "organization_id": org_id,
            "token_id": token_id,
            "payload_json": json.dumps(payload, sort_keys=True),
            "status": status,
        },
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> dict[str, int]:
    counts = {
        "users": 0,
        "encounters": 0,
        "signed_encounters": 0,
        "reminders": 0,
        "intake_tokens": 0,
        "intake_submissions": 0,
    }

    with _transaction() as conn:
        org_id = _get_or_create_org(conn, DEMO_ORG_SLUG, DEMO_ORG_NAME)
        loc_id = _get_or_create_location(conn, org_id, DEMO_LOCATION_NAME)

        # --- Staff identities ------------------------------------------
        staff_ids: dict[str, int] = {}
        for email, full_name, role, fs, lead in DEMO_USERS:
            uid = _ensure_user(conn, org_id, email, full_name, role, fs, lead)
            staff_ids[role] = uid
            counts["users"] += 1
        admin_id = staff_ids["admin"]

        # --- 20 encounters (5 per template) ----------------------------
        clinician_emails = [
            "dr.smith@pilot-demo.local",
            "dr.jones@pilot-demo.local",
            "dr.lee@pilot-demo.local",
        ]
        encounter_ids: list[int] = []
        idx = 0
        for tpl in TEMPLATE_DISTRIBUTION:
            for k in range(5):
                idx += 1
                pid = f"PT-DEMO-{1000 + idx:04d}"
                pname = f"Demo Patient {idx:02d}"
                provider_email = clinician_emails[idx % 3]
                provider_name = next(
                    fn for em, fn, *_ in DEMO_USERS if em == provider_email
                )
                patient_id = _ensure_patient(conn, org_id, pid, pname)
                eid = _ensure_encounter(
                    conn,
                    org_id=org_id, location_id=loc_id,
                    patient_id=patient_id,
                    patient_identifier=pid, patient_name=pname,
                    provider_name=provider_name, template_key=tpl,
                    status="completed" if idx == 1 else "scheduled",
                    completed_at=_now() - timedelta(days=1) if idx == 1 else None,
                )
                encounter_ids.append(eid)
                counts["encounters"] += 1

        # --- Full end-to-end signed encounter (the first one) ---------
        signed_enc = encounter_ids[0]
        nv_id = _ensure_signed_note(
            conn,
            encounter_id=signed_enc,
            note_text="VA OD 20/40, OS 20/30. IOP 16/14. Plan: f/u 4/52.",
        )
        counts["signed_encounters"] = 1

        # Linked consult letter — needs a referring provider row.
        rp_row = conn.execute(
            text(
                "SELECT id FROM referring_providers "
                "WHERE organization_id = :o AND npi_10 = :n"
            ),
            {"o": org_id, "n": "1234567893"},
        ).mappings().first()
        if not rp_row:
            rp_id = _insert_returning_id(
                conn, "referring_providers",
                {
                    "organization_id": org_id,
                    "name": "Dr. Demo Optometrist",
                    "practice": "Demo Optometry",
                    "npi_10": "1234567893",
                    "email": "demo@demo-optometry.example",
                },
            )
        else:
            rp_id = int(rp_row["id"])

    # End first transaction. Now invoke service-layer helpers that
    # open their own transactions.

    # Linked post-visit summary (idempotent at the service layer).
    from app.services.post_visit_summary import generate_for_note_version
    generate_for_note_version(
        note_version_id=nv_id, organization_id=org_id,
    )
    from app.services.consult_letters import (
        dispatch_delivery, render_letter_pdf,
    )
    from app.db import fetch_one as _fo
    cl_existing = _fo(
        "SELECT id FROM consult_letters "
        "WHERE note_version_id = :nv AND referring_provider_id = :rp",
        {"nv": nv_id, "rp": rp_id},
    )
    if not cl_existing:
        # Build payload via the service helpers.
        note = _fo(
            "SELECT nv.id, nv.encounter_id, nv.note_text, "
            "       e.organization_id, e.patient_identifier, e.patient_name, "
            "       e.provider_name, e.scheduled_at, e.completed_at "
            "FROM note_versions nv JOIN encounters e ON e.id = nv.encounter_id "
            "WHERE nv.id = :id",
            {"id": nv_id},
        )
        rp = _fo(
            "SELECT id, organization_id, name, practice, npi_10, phone, "
            "       fax, email, created_at "
            "FROM referring_providers WHERE id = :id",
            {"id": rp_id},
        )
        org = _fo(
            "SELECT name FROM organizations WHERE id = :id",
            {"id": org_id},
        ) or {"name": ""}
        pdf_bytes = render_letter_pdf(
            encounter=dict(note), note_text=note["note_text"] or "",
            referring_provider=dict(rp), org_name=org.get("name") or "",
        )
        delivery = dispatch_delivery(channel="download",
                                      referring_provider=dict(rp))
        with _transaction() as conn:
            _insert_returning_id(
                conn, "consult_letters",
                {
                    "organization_id": org_id,
                    "encounter_id": note["encounter_id"],
                    "note_version_id": nv_id,
                    "referring_provider_id": rp_id,
                    "rendered_pdf_storage_ref": (
                        f"consult-letters/{nv_id}/{rp_id}.pdf"
                    ),
                    "pdf_bytes": pdf_bytes,
                    "delivery_status": delivery["delivery_status"],
                    "delivered_via": delivery["delivered_via"],
                    "sent_at": delivery["sent_at"],
                },
            )

    # --- Reminders: 3 overdue, 5 complete, 4 upcoming = 12 total -------
    with _transaction() as conn:
        # Overdue
        for i in range(1, 4):
            _ensure_reminder(
                conn, org_id=org_id,
                title=f"Pilot demo overdue #{i}",
                due_at=_now() - timedelta(days=i),
                status="pending", created_by=admin_id,
            )
        # Completed
        for i in range(1, 6):
            _ensure_reminder(
                conn, org_id=org_id,
                title=f"Pilot demo completed #{i}",
                due_at=_now() - timedelta(days=i + 5),
                status="completed", created_by=admin_id,
            )
        # Upcoming
        for i in range(1, 5):
            _ensure_reminder(
                conn, org_id=org_id,
                title=f"Pilot demo upcoming #{i}",
                due_at=_now() + timedelta(days=i),
                status="pending", created_by=admin_id,
            )
        counts["reminders"] = 12

        # --- Intake tokens: 2 pending, 1 accepted, 1 expired -----------
        # 2 pending (no submission yet)
        _ensure_intake_token(
            conn, org_id=org_id, candidate="PT-DEMO-INTAKE-PENDING-A",
            used=False, expired=False, created_by=admin_id,
        )
        _ensure_intake_token(
            conn, org_id=org_id, candidate="PT-DEMO-INTAKE-PENDING-B",
            used=False, expired=False, created_by=admin_id,
        )
        # 1 accepted (token used + submission row + accepted)
        accepted_token = _ensure_intake_token(
            conn, org_id=org_id, candidate="PT-DEMO-INTAKE-ACCEPTED",
            used=True, expired=False, created_by=admin_id,
        )
        _ensure_intake_submission(
            conn, org_id=org_id, token_id=accepted_token, status="accepted",
        )
        # 1 expired (no submission)
        _ensure_intake_token(
            conn, org_id=org_id, candidate="PT-DEMO-INTAKE-EXPIRED",
            used=False, expired=True, created_by=admin_id,
        )
        counts["intake_tokens"] = 4
        counts["intake_submissions"] = 1

    return counts


if __name__ == "__main__":
    out = main()
    print("Pilot demo seed complete:")
    for k, v in out.items():
        print(f"  {k}: {v}")
