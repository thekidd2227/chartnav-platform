"""Phase 2 item 6 — demo seed contract tests.

Spec: docs/chartnav/closure/PHASE_B_Demo_Environment_and_Pilot_Scope.md §4.

Acceptance criteria:
  - Seed against an already-seeded DB produces the documented row
    counts in the demo org.
  - Running twice is idempotent (no duplicate rows, no conflicts).
  - All seeded records are scoped to the demo org.
"""
from __future__ import annotations

from sqlalchemy import text


DEMO_SLUG = "pilot-demo-eye-clinic"


def _demo_org_id() -> int:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id FROM organizations WHERE slug = :s", {"s": DEMO_SLUG},
    )
    return int(row["id"]) if row else -1


def _count(table: str, where: str = "", params: dict | None = None) -> int:
    from app.db import fetch_one
    sql = f"SELECT COUNT(*) AS n FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return int(fetch_one(sql, params or {})["n"])


def test_demo_seed_runs_against_seeded_db_and_idempotent(client):
    # `client` fixture has already run scripts_seed.main(). Now run
    # the demo seed twice and confirm idempotency + row counts.
    import scripts_seed_demo
    out1 = scripts_seed_demo.main()
    out2 = scripts_seed_demo.main()
    assert out1 == out2  # function-level idempotency

    org_id = _demo_org_id()
    assert org_id > 0

    # Spec §3 row counts inside the demo org.
    assert _count("users", "organization_id = :o", {"o": org_id}) == 6
    assert _count("encounters", "organization_id = :o", {"o": org_id}) == 20
    assert _count("reminders", "organization_id = :o", {"o": org_id}) == 12
    assert _count("intake_tokens", "organization_id = :o", {"o": org_id}) == 4
    # Pending vs accepted vs expired (the 1 accepted is the only
    # submission row).
    assert _count(
        "intake_submissions",
        "organization_id = :o AND status = 'accepted'", {"o": org_id},
    ) == 1
    # Exactly 1 fully-signed encounter in the demo org.
    assert _count(
        "note_versions nv JOIN encounters e ON e.id = nv.encounter_id",
        "e.organization_id = :o AND nv.signed_at IS NOT NULL",
        {"o": org_id},
    ) == 1
    # Linked post-visit summary + linked consult letter.
    assert _count(
        "post_visit_summaries", "organization_id = :o", {"o": org_id},
    ) == 1
    assert _count(
        "consult_letters", "organization_id = :o", {"o": org_id},
    ) == 1


def test_demo_seed_does_not_pollute_other_orgs(client):
    """Seeded rows must NOT show up under the standard demo-eye-clinic
    org; the demo seed lives in its own pilot-demo-eye-clinic org."""
    import scripts_seed_demo
    scripts_seed_demo.main()
    from app.db import fetch_one
    standard = fetch_one(
        "SELECT id FROM organizations WHERE slug = :s",
        {"s": "demo-eye-clinic"},
    )
    assert standard is not None
    sid = int(standard["id"])
    # Standard demo org row counts unchanged by the pilot demo seed.
    # We don't assert exact numbers (those depend on the standard
    # seed's own evolution), but no PT-DEMO-* identifier should be
    # in the standard org.
    leak = fetch_one(
        "SELECT COUNT(*) AS n FROM patients "
        "WHERE organization_id = :o AND patient_identifier LIKE 'PT-DEMO-%'",
        {"o": sid},
    )
    assert int(leak["n"]) == 0
