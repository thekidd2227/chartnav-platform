"""Idempotent seed for ChartNav. Cross-dialect (SQLite + Postgres).

Uses SQLAlchemy Core via `app.db` so the same seed runs against either
backend. All SQL uses portable constructs (`COALESCE`, named binds).
"""

from __future__ import annotations

import json
import os

from sqlalchemy import text

from app.db import insert_returning_id, transaction


def _wedge_enabled() -> bool:
    """Phase 24B wedge gate.

    Default ON for direct invocations (demo, Playwright e2e seed).
    Backend pytest fixtures set ``CHARTNAV_SEED_PHASE_24B_WEDGE=0`` so
    that Phase 20B / 20C count-based tests continue to see the empty
    baseline they were written against. The Phase 24B test file
    re-enables the wedge via its own ``test_db_with_wedge`` fixture.
    """
    return os.environ.get("CHARTNAV_SEED_PHASE_24B_WEDGE", "1") != "0"

ORGS = [
    {
        "slug": "demo-eye-clinic",
        "name": "Demo Eye Clinic",
        "location": "Main Clinic",
        "users": [
            ("admin@chartnav.local", "ChartNav Admin", "admin"),
            ("clin@chartnav.local", "Casey Clinician", "clinician"),
            ("rev@chartnav.local", "Riley Reviewer", "reviewer"),
            # Phase 20C — additive operational roles for the
            # role-based dashboards. Demo-local synthetic identities;
            # no real PHI.
            ("front@chartnav.local", "Frankie Front-Desk", "front_desk"),
            ("tech@chartnav.local", "Taylor Technician", "technician"),
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
            # Phase 20C — additive operational roles.
            ("front@northside.local", "Nora Front-Desk", "front_desk"),
            ("tech@northside.local", "Nash Technician", "technician"),
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


# =====================================================================
# Phase 24B — Morgan Lee retina follow-up wedge.
#
# Deterministic fake-data orchestration that exercises every clinic
# lane (front desk → tech workup → imaging review → MD encounter →
# documentation → sign-off → internal follow-up) for one patient.
# Every row is fake by construction; PT-1001 Morgan Lee is the same
# fake demo identity the rest of the seed uses.
#
# All text in this wedge is provider-reviewed workflow-coordination
# language. None of it claims autonomous diagnosis, automatic image
# interpretation, OCT/fundus/visual-field interpretation, treatment
# recommendation, medication selection, automatic orders / referrals
# / patient messaging / billing / coding / claims submission, EHR
# replacement, HIPAA certification, real device integration, or real
# PHI.
# =====================================================================


_WEDGE_QUEUE_LANE = (
    # (queue_type, status, assigned_role, title for payload, priority)
    ("check_in", "open", "front_desk", "Front desk readiness — confirm retina follow-up arrival.", "normal"),
    ("technician_workup", "open", "technician", "Technician workup — VA / IOP / refraction / dilation for retina follow-up.", "normal"),
    ("imaging_needed", "open", "technician", "Imaging metadata review — OCT macula + fundus photo captured upstream.", "normal"),
    ("ready_for_doctor", "open", "clinician", "Ready for MD — retina follow-up encounter.", "high"),
    ("documentation", "open", "clinician", "Provider-reviewed documentation — draft to final note for retina follow-up.", "normal"),
    ("signoff_needed", "open", "clinician", "Sign-off needed — retina follow-up note pending immutable sign.", "normal"),
    ("follow_up", "open", "front_desk", "Internal follow-up — confirm retina follow-up window after provider sign-off.", "normal"),
)


def _ensure_wedge_queue_item(
    conn,
    *,
    org_id: int,
    patient_id: int,
    encounter_id: int,
    provider_id: int,
    location_id: int,
    queue_type: str,
    status: str,
    assigned_role: str,
    payload_title: str,
    priority: str,
    assigned_user_id: int | None = None,
) -> int:
    """Idempotent insert keyed on (org, patient, encounter, queue_type)."""
    row = conn.execute(
        text(
            "SELECT id FROM work_queue_items "
            "WHERE organization_id = :org AND patient_id = :pid "
            "AND encounter_id = :eid AND queue_type = :qt"
        ),
        {"org": org_id, "pid": patient_id, "eid": encounter_id, "qt": queue_type},
    ).mappings().first()
    if row:
        return int(row["id"])
    # payload_json carries the role-facing title only — Phase 20C's
    # _compact_queue_item() strips this body before serializing to
    # the dashboard response. Buyer-visible UI shows the queue type
    # + status, not this payload.
    payload = json.dumps(
        {"title": payload_title, "source": "phase_24b_wedge", "demo": True},
        sort_keys=True,
    )
    return insert_returning_id(
        conn,
        "work_queue_items",
        {
            "organization_id": org_id,
            "location_id": location_id,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "provider_id": provider_id,
            "queue_type": queue_type,
            "priority": priority,
            "status": status,
            "assigned_role": assigned_role,
            "assigned_user_id": assigned_user_id,
            "source": "phase_24b_wedge",
            "payload_json": payload,
        },
    )


def _ensure_retina_tracking_for_wedge(
    conn, *, org_id: int, patient_id: int, encounter_id: int, user_id: int
) -> int:
    row = conn.execute(
        text(
            "SELECT id FROM retina_tracking "
            "WHERE organization_id = :org AND patient_id = :pid "
            "AND encounter_id = :eid AND condition = :cond"
        ),
        {
            "org": org_id,
            "pid": patient_id,
            "eid": encounter_id,
            "cond": "Diabetic retinopathy / macular edema monitoring",
        },
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "retina_tracking",
        {
            "organization_id": org_id,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "eye": "OU",
            "condition": "Diabetic retinopathy / macular edema monitoring",
            "severity": "moderate (provider-entered)",
            "follow_up_interval": "4 weeks",
            "injection_history_summary": "Prior anti-VEGF history captured by provider; no automation by ChartNav.",
            "provider_assessment": (
                "Provider-reviewed monitoring note. ChartNav records "
                "structured fields the provider enters; ChartNav does "
                "not diagnose, interpret OCTs, grade DR, or select "
                "anti-VEGF dosing."
            ),
            "review_status": "needs_review",
            "created_by_user_id": user_id,
        },
    )


def _ensure_imaging_study_for_wedge(
    conn,
    *,
    org_id: int,
    patient_id: int,
    encounter_id: int,
    user_id: int,
    modality: str,
    eye: str,
    notes: str,
) -> int:
    row = conn.execute(
        text(
            "SELECT id FROM imaging_studies "
            "WHERE organization_id = :org AND patient_id = :pid "
            "AND encounter_id = :eid AND modality = :m AND eye = :eye"
        ),
        {
            "org": org_id,
            "pid": patient_id,
            "eid": encounter_id,
            "m": modality,
            "eye": eye,
        },
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "imaging_studies",
        {
            "organization_id": org_id,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "modality": modality,
            "eye": eye,
            "status": "ready_for_review",
            "notes": notes,
            "created_by_user_id": user_id,
        },
    )


def _ensure_imaging_file_for_wedge(
    conn,
    *,
    org_id: int,
    study_id: int,
    user_id: int,
    file_kind: str,
    file_name: str,
    storage_uri: str,
) -> int:
    row = conn.execute(
        text(
            "SELECT id FROM imaging_files "
            "WHERE organization_id = :org AND study_id = :sid "
            "AND file_name = :fn"
        ),
        {"org": org_id, "sid": study_id, "fn": file_name},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "imaging_files",
        {
            "organization_id": org_id,
            "study_id": study_id,
            "file_kind": file_kind,
            "storage_uri": storage_uri,
            "file_name": file_name,
            "content_type": "application/octet-stream",
            "size_bytes": 0,
            "created_by_user_id": user_id,
        },
    )


def _ensure_action_item_for_wedge(
    conn, *, org_id: int, patient_id: int, encounter_id: int
) -> int:
    action_type = "review_retina_followup_window"
    row = conn.execute(
        text(
            "SELECT id FROM provider_action_items "
            "WHERE organization_id = :org AND patient_id = :pid "
            "AND encounter_id = :eid AND action_type = :at"
        ),
        {"org": org_id, "pid": patient_id, "eid": encounter_id, "at": action_type},
    ).mappings().first()
    if row:
        return int(row["id"])
    return insert_returning_id(
        conn,
        "provider_action_items",
        {
            "organization_id": org_id,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "source_type": "phase_24b_wedge",
            "action_type": action_type,
            "priority": "medium",
            "title": (
                "Internal follow-up — confirm retina follow-up window "
                "after provider sign-off. Review task only; internal "
                "staff coordination."
            ),
            "status": "suggested",
            "created_by_system": True,
            "generated_batch_id": "phase_24b_wedge",
        },
    )


def _seed_phase_24b_retina_wedge(
    conn,
    *,
    org_id: int,
    location_id: int,
    patient_id: int,
    encounter_id: int,
    provider_id: int,
    admin_user_id: int,
) -> dict[str, int]:
    """Seed the Morgan Lee retina follow-up wedge.

    Idempotent. Returns a summary dict.
    """
    counts: dict[str, int] = {"queue_items": 0, "imaging_files": 0}

    assignee_by_role = {
        "front_desk": _user_id_for_org_role(conn, org_id, "front_desk"),
        "technician": _user_id_for_org_role(conn, org_id, "technician"),
        "clinician": _user_id_for_org_role(conn, org_id, "clinician"),
    }

    for qt, st, role, title, prio in _WEDGE_QUEUE_LANE:
        _ensure_wedge_queue_item(
            conn,
            org_id=org_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            provider_id=provider_id,
            location_id=location_id,
            queue_type=qt,
            status=st,
            assigned_role=role,
            assigned_user_id=assignee_by_role.get(role),
            payload_title=title,
            priority=prio,
        )
        counts["queue_items"] += 1

    retina_id = _ensure_retina_tracking_for_wedge(
        conn,
        org_id=org_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        user_id=admin_user_id,
    )
    counts["retina_tracking_id"] = retina_id

    oct_study_id = _ensure_imaging_study_for_wedge(
        conn,
        org_id=org_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        user_id=admin_user_id,
        modality="oct_macula",
        eye="OU",
        notes=(
            "OCT macula captured upstream by the practice's existing "
            "imaging workflow. ChartNav stores metadata only. Provider "
            "interpretation stays with the clinician. ChartNav does "
            "not interpret OCT scans."
        ),
    )
    counts["oct_macula_study_id"] = oct_study_id
    _ensure_imaging_file_for_wedge(
        conn,
        org_id=org_id,
        study_id=oct_study_id,
        user_id=admin_user_id,
        file_kind="image",
        file_name="oct_macula_morgan_lee_demo.dcm",
        storage_uri="placeholder://demo/oct_macula_morgan_lee_demo.dcm",
    )
    counts["imaging_files"] += 1

    fundus_study_id = _ensure_imaging_study_for_wedge(
        conn,
        org_id=org_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        user_id=admin_user_id,
        modality="fundus_photo",
        eye="OU",
        notes=(
            "Fundus photograph captured upstream by the practice's "
            "existing imaging workflow. ChartNav stores metadata only. "
            "ChartNav does not interpret fundus photographs."
        ),
    )
    counts["fundus_photo_study_id"] = fundus_study_id
    _ensure_imaging_file_for_wedge(
        conn,
        org_id=org_id,
        study_id=fundus_study_id,
        user_id=admin_user_id,
        file_kind="image",
        file_name="fundus_photo_morgan_lee_demo.jpg",
        storage_uri="placeholder://demo/fundus_photo_morgan_lee_demo.jpg",
    )
    counts["imaging_files"] += 1

    counts["action_item_id"] = _ensure_action_item_for_wedge(
        conn,
        org_id=org_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
    )

    return counts


def _user_id_for_org_role(conn, org_id: int, role: str) -> int | None:
    row = conn.execute(
        text(
            "SELECT id FROM users WHERE organization_id = :org "
            "AND role = :role ORDER BY id LIMIT 1"
        ),
        {"org": org_id, "role": role},
    ).mappings().first()
    return int(row["id"]) if row else None


def _admin_user_id_for_org(conn, org_id: int) -> int | None:
    return _user_id_for_org_role(conn, org_id, "admin")


_PHASE_89_QUALITY_SPECS = (
    {
        "measure_id": "chartnav_demo_ophth_dr_communication",
        "measure_name": (
            "Diabetic Retinopathy: Communication with primary "
            "care physician (DEMO — internal placeholder, NOT verified for submission)"
        ),
        "program_year": 2026,
        "applicable_icd10_prefixes": ["E10.3", "E11.3"],
        "required_fields": [
            "visit_draft_signed",
            "disease_stage_documented",
        ],
        "exception_codes": ["patient_refused", "documentation_other"],
    },
    {
        "measure_id": "chartnav_demo_ophth_poag_iop_documentation",
        "measure_name": (
            "Primary Open-Angle Glaucoma: IOP documentation "
            "(DEMO — internal placeholder, NOT verified for submission)"
        ),
        "program_year": 2026,
        "applicable_icd10_prefixes": ["H40.1"],
        "required_fields": [
            "iop_documented",
            "visit_draft_signed",
        ],
        "exception_codes": ["patient_refused", "documentation_other"],
    },
    {
        "measure_id": "chartnav_demo_ophth_dr_screening",
        "measure_name": (
            "Diabetic Retinopathy: Documented screening within 12 months "
            "(DEMO — internal placeholder, NOT verified for submission)"
        ),
        "program_year": 2026,
        "applicable_icd10_prefixes": ["E10.3", "E11.3"],
        "required_fields": [
            "fundus_chart_signed",
            "imaging_reviewed",
        ],
        "exception_codes": ["patient_refused", "documentation_other"],
    },
)


def _ensure_phase_89_quality_specs(conn) -> int:
    """Phase 89 — idempotent seed of internal demo quality measure specs.

    Specs are global (organization_id IS NULL) and marked as DEMO in the
    measure_name so they are never confused with verified submission
    specs. The service layer treats every measure_id in the
    ``INTERNAL_DEMO_MEASURE_IDS`` set as ``verified_for_submission=false``.
    """
    import json as _json

    inserted = 0
    for spec in _PHASE_89_QUALITY_SPECS:
        existing = conn.execute(
            text(
                "SELECT id FROM quality_measure_specs "
                "WHERE organization_id IS NULL AND measure_id = :mid "
                "AND program_year = :py"
            ),
            {"mid": spec["measure_id"], "py": spec["program_year"]},
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            text(
                "INSERT INTO quality_measure_specs ("
                "organization_id, measure_id, measure_name, program_year, "
                "applicable_icd10_prefixes, required_fields, "
                "exception_codes, status"
                ") VALUES ("
                "NULL, :mid, :mname, :py, :icd, :req, :exc, 'active'"
                ")"
            ),
            {
                "mid": spec["measure_id"],
                "mname": spec["measure_name"],
                "py": spec["program_year"],
                "icd": _json.dumps(spec["applicable_icd10_prefixes"]),
                "req": _json.dumps(spec["required_fields"]),
                "exc": _json.dumps(spec["exception_codes"]),
            },
        )
        inserted += 1
    return inserted


_PHASE_90_MEDICATION_SAFETY_RULES = (
    {
        "rule_key": "ophth_preservative_burden_advisory",
        "rule_name": (
            "BAK preservative burden — provider review advisory "
            "(DEMO — internal placeholder, NOT verified for clinical use)"
        ),
        "medication_class": None,
        "trigger_context": "preservative_burden",
        "severity": "advisory",
        "message": (
            "Provider review advisory: 3+ active BAK-preserved drop(s) "
            "on file. ChartNav does not recommend a medication change."
        ),
        "requires_acknowledgement": False,
    },
    {
        "rule_key": "ophth_refill_gap_advisory",
        "rule_name": (
            "Refill gap — provider review advisory "
            "(DEMO — internal placeholder, NOT verified for clinical use)"
        ),
        "medication_class": None,
        "trigger_context": "refill_gap",
        "severity": "advisory",
        "message": (
            "Provider review advisory: last_fill_date + days_supply is "
            "past today by the configured threshold. Provider review "
            "required."
        ),
        "requires_acknowledgement": False,
    },
    {
        "rule_key": "ophth_cataract_alpha_blocker_review",
        "rule_name": (
            "Cataract workflow + active alpha-blocker — IFIS review reminder "
            "(DEMO — internal placeholder, NOT verified for clinical use)"
        ),
        "medication_class": "alpha_agonist",
        "trigger_context": "cataract_alpha_blocker",
        "severity": "advisory",
        "message": (
            "Provider review advisory: cataract workflow record on file "
            "with active alpha-blocker class medication. Provider review "
            "required; ChartNav does not recommend a medication change "
            "or surgical decision."
        ),
        "requires_acknowledgement": False,
    },
    {
        "rule_key": "ophth_duplicate_class_advisory",
        "rule_name": (
            "Duplicate ophthalmic drop class — provider review advisory "
            "(DEMO — internal placeholder, NOT verified for clinical use)"
        ),
        "medication_class": None,
        "trigger_context": "duplicate_class",
        "severity": "advisory",
        "message": (
            "Provider review advisory: two or more active drops in the "
            "same medication_class on file. Provider review required."
        ),
        "requires_acknowledgement": False,
    },
    {
        "rule_key": "ophth_medication_review_missing_advisory",
        "rule_name": (
            "Medication review missing — provider review advisory "
            "(DEMO — internal placeholder, NOT verified for clinical use)"
        ),
        "medication_class": None,
        "trigger_context": "review_missing",
        "severity": "advisory",
        "message": (
            "Provider review advisory: one or more active medications "
            "without a recorded review in the configured window. "
            "Provider review required."
        ),
        "requires_acknowledgement": False,
    },
)


def _ensure_phase_90_medication_safety_rules(conn) -> int:
    """Phase 90 — idempotent seed of internal DEMO medication safety
    rules. Global rows (organization_id IS NULL). The service layer
    flags every seeded rule_key as internal_demo_only=True."""
    inserted = 0
    for rule in _PHASE_90_MEDICATION_SAFETY_RULES:
        existing = conn.execute(
            text(
                "SELECT id FROM medication_safety_rules "
                "WHERE organization_id IS NULL AND rule_key = :key"
            ),
            {"key": rule["rule_key"]},
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            text(
                "INSERT INTO medication_safety_rules ("
                "organization_id, rule_key, rule_name, medication_class, "
                "trigger_context, severity, message, "
                "requires_acknowledgement, status"
                ") VALUES ("
                "NULL, :key, :name, :klass, :ctx, :sev, :msg, "
                ":ack, 'active'"
                ")"
            ),
            {
                "key": rule["rule_key"],
                "name": rule["rule_name"],
                "klass": rule["medication_class"],
                "ctx": rule["trigger_context"],
                "sev": rule["severity"],
                "msg": rule["message"],
                "ack": rule["requires_acknowledgement"],
            },
        )
        inserted += 1
    return inserted


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

            wedge_enc_id: int | None = None
            wedge_provider_id: int | None = None
            for enc_fx in org_fx["encounters"]:
                enc_id = _get_or_create_encounter(
                    conn, org_id, loc_id, enc_fx,
                    patient_id=patient_ids.get(enc_fx["patient_identifier"]),
                    provider_id=provider_ids.get(enc_fx["provider_name"]),
                )
                _ensure_events(conn, enc_id, enc_fx["events"])
                # Phase 24B — Morgan Lee retina follow-up wedge anchor.
                if (
                    org_fx["slug"] == "demo-eye-clinic"
                    and enc_fx.get("patient_identifier") == "PT-1001"
                ):
                    wedge_enc_id = enc_id
                    wedge_provider_id = provider_ids.get(enc_fx["provider_name"])

            # Phase 24B — seed the Morgan Lee retina follow-up wedge
            # (work queue items, retina tracking, OCT + fundus imaging
            # metadata, internal follow-up task). Idempotent. Gated
            # by `CHARTNAV_SEED_PHASE_24B_WEDGE` so backend tests can
            # opt out and keep their pre-wedge baseline.
            if (
                _wedge_enabled()
                and org_fx["slug"] == "demo-eye-clinic"
                and wedge_enc_id is not None
                and wedge_provider_id is not None
            ):
                admin_uid = _admin_user_id_for_org(conn, org_id)
                wedge_counts = _seed_phase_24b_retina_wedge(
                    conn,
                    org_id=org_id,
                    location_id=loc_id,
                    patient_id=patient_ids["PT-1001"],
                    encounter_id=wedge_enc_id,
                    provider_id=wedge_provider_id,
                    admin_user_id=admin_uid or 0,
                )
                summary.append(("phase_24b_wedge", org_id, wedge_counts))
            summary.append((org_fx["slug"], org_id, loc_id))

        # Phase 89 — idempotent seed of internal DEMO quality measure
        # specs. Global rows (organization_id IS NULL). Marked as DEMO
        # in measure_name; the service layer flags every internal-demo
        # measure_id as verified_for_submission=false.
        phase89_inserted = _ensure_phase_89_quality_specs(conn)
        summary.append(("phase_89_quality_specs", None, phase89_inserted))

        # Phase 90 — idempotent seed of internal DEMO medication safety
        # rules. Global rows (organization_id IS NULL). Every seeded
        # rule_key is flagged internal_demo_only=True at the service
        # layer; a qualified operator must verify before any real-
        # program use.
        phase90_inserted = _ensure_phase_90_medication_safety_rules(conn)
        summary.append(
            ("phase_90_medication_safety_rules", None, phase90_inserted)
        )

    print("Seed complete.")
    for item in summary:
        if item[0] == "phase_24b_wedge":
            print(f"  phase_24b_wedge: organization_id={item[1]} {item[2]}")
        elif item[0] == "phase_89_quality_specs":
            print(f"  phase_89_quality_specs: inserted={item[2]}")
        elif item[0] == "phase_90_medication_safety_rules":
            print(
                f"  phase_90_medication_safety_rules: inserted={item[2]}"
            )
        else:
            slug, org_id, loc_id = item
            print(f"  {slug}: organization_id={org_id} location_id={loc_id}")


if __name__ == "__main__":
    main()
