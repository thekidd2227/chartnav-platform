"""Tests for the Phase 6 findings -> retinal diagram proposal engine
and its `/propose-from-findings` route.

The proposal engine is **deterministic and rule-based**. It must never
write to the database; the route only emits an audit row whose detail
is metadata-only (no findings_text, no proposal bodies).
"""

from __future__ import annotations

from app.services.retinal_proposals import (
    coords_for,
    propose_from_findings,
)
from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# --- helpers -----------------------------------------------------------


def _patient_id_for(seeded_ids: dict, identifier: str) -> int:
    from app.db import fetch_one

    row = fetch_one(
        "SELECT id FROM patients WHERE patient_identifier = :pid",
        {"pid": identifier},
    )
    assert row, f"seed missing patient {identifier!r}"
    return int(row["id"])


# --- pure-logic engine --------------------------------------------------


class TestProposalEngine:
    def test_simple_od_drusen_at_macula(self):
        result = propose_from_findings("OD drusen at macula.")
        assert len(result.proposed_annotations) == 1
        p = result.proposed_annotations[0]
        assert p.symbol_type == "drusen"
        assert p.eye == "OD"
        assert p.zone == "macula"
        assert p.confidence_band == "high"
        assert p.source == "ai_proposed"
        assert "drusen" in p.reason
        assert "macula" in p.reason
        assert p.x == 0.5
        assert p.y == 0.5

    def test_os_flame_hemorrhage_superior(self):
        result = propose_from_findings("OS flame hemorrhage superior.")
        assert len(result.proposed_annotations) == 1
        p = result.proposed_annotations[0]
        assert p.eye == "OS"
        assert p.symbol_type == "flame_hemorrhage"
        assert p.zone == "superior"
        assert p.y == 0.25

    def test_ou_creates_od_and_os_proposals(self):
        result = propose_from_findings("OU drusen at macula.")
        eyes = sorted(p.eye for p in result.proposed_annotations)
        assert eyes == ["OD", "OS"]
        # Both proposals are stable but DISTINCT.
        ids = {p.proposal_id for p in result.proposed_annotations}
        assert len(ids) == 2

    def test_bilateral_word_creates_both_eyes(self):
        result = propose_from_findings("Bilateral retinal tear at periphery.")
        eyes = sorted(p.eye for p in result.proposed_annotations)
        assert eyes == ["OD", "OS"]

    def test_right_eye_left_eye_synonyms(self):
        result = propose_from_findings(
            "right eye drusen at macula. left eye microaneurysm at superior."
        )
        eyes = [(p.eye, p.symbol_type) for p in result.proposed_annotations]
        assert ("OD", "drusen") in eyes
        assert ("OS", "microaneurysm") in eyes

    def test_missing_laterality_yields_missing_flag_and_no_annotation(self):
        result = propose_from_findings("Drusen at macula.")
        assert result.proposed_annotations == []
        assert any(
            f.code == "missing_laterality" for f in result.missing_flags
        ), result.missing_flags

    def test_known_finding_without_zone_is_medium_confidence(self):
        result = propose_from_findings("OD drusen.")
        assert len(result.proposed_annotations) == 1
        p = result.proposed_annotations[0]
        assert p.confidence_band == "medium"
        assert p.zone is None
        # Drops at macula by default when zone unknown.
        assert p.x == 0.5 and p.y == 0.5
        assert "missing_zone" in p.missing_flags

    def test_chatter_is_ignored(self):
        result = propose_from_findings(
            "Good morning, doctor. OD drusen at macula. Thank you."
        )
        assert any("Good morning" in c for c in result.ignored_chatter)
        assert any("Thank you" in c for c in result.ignored_chatter)
        assert len(result.proposed_annotations) == 1

    def test_unknown_clinical_phrase_goes_to_uncertain(self):
        result = propose_from_findings(
            "Patient appears comfortable in clinic chair."
        )
        assert result.proposed_annotations == []
        assert "Patient appears comfortable in clinic chair" in (
            result.uncertain_phrases[0] if result.uncertain_phrases else ""
        )

    def test_stable_proposal_id_for_same_input(self):
        a = propose_from_findings("OD drusen at macula.")
        b = propose_from_findings("OD drusen at macula.")
        assert a.proposed_annotations[0].proposal_id == b.proposed_annotations[0].proposal_id

    def test_distinct_proposal_id_for_different_eye(self):
        a = propose_from_findings("OD drusen at macula.")
        b = propose_from_findings("OS drusen at macula.")
        assert a.proposed_annotations[0].proposal_id != b.proposed_annotations[0].proposal_id

    def test_distinct_proposal_id_for_different_zone(self):
        a = propose_from_findings("OD drusen at macula.")
        b = propose_from_findings("OD drusen at periphery.")
        assert a.proposed_annotations[0].proposal_id != b.proposed_annotations[0].proposal_id

    def test_confidence_summary_counts(self):
        result = propose_from_findings(
            "OD drusen at macula. OS flame hemorrhage. Drusen at macula."
        )
        s = result.confidence_summary
        # Two annotations placed: 1 high (full info) + 1 medium (no zone).
        # The third sentence has no laterality => missing_flag, no annotation.
        assert s["high"] == 1
        assert s["medium"] == 1
        assert s["needs_review"] is True

    def test_source_offsets_are_in_original_text(self):
        text = "Padding. OD drusen at macula. Trailing."
        result = propose_from_findings(text)
        p = result.proposed_annotations[0]
        assert text[p.source_start : p.source_end].strip().startswith(
            "OD drusen at macula"
        )

    def test_dot_blot_hemorrhage_compound_phrase(self):
        result = propose_from_findings("OS dot/blot hemorrhage at temporal.")
        assert len(result.proposed_annotations) == 1
        assert result.proposed_annotations[0].symbol_type == "dot_blot_hemorrhage"

    def test_compound_zone_superotemporal(self):
        result = propose_from_findings("OD lattice degeneration superotemporal.")
        p = result.proposed_annotations[0]
        assert p.zone == "superior_temporal"


class TestCoordsForEye:
    """Coordinate convention must match `RetinalDrawingCanvas.tsx`.

    OD: optic disc on the RIGHT (x > 0.5), nasal=right, temporal=left.
    OS: optic disc on the LEFT (x < 0.5), nasal=left, temporal=right.
    Superior is y < 0.5; inferior is y > 0.5; eye-independent.
    """

    def test_macula_center(self):
        for eye in ("OD", "OS"):
            assert coords_for(eye, "macula") == (0.5, 0.5)

    def test_optic_disc_nasal_per_eye(self):
        x_od, y_od = coords_for("OD", "optic_disc")
        x_os, y_os = coords_for("OS", "optic_disc")
        assert x_od > 0.5  # right side of OD pane = nasal
        assert x_os < 0.5  # left side of OS pane = nasal
        assert y_od == 0.5 and y_os == 0.5

    def test_nasal_temporal_swap_per_eye(self):
        nasal_od_x, _ = coords_for("OD", "nasal")
        temporal_od_x, _ = coords_for("OD", "temporal")
        nasal_os_x, _ = coords_for("OS", "nasal")
        temporal_os_x, _ = coords_for("OS", "temporal")
        assert nasal_od_x > 0.5 and temporal_od_x < 0.5
        assert nasal_os_x < 0.5 and temporal_os_x > 0.5

    def test_superior_inferior_eye_independent(self):
        for eye in ("OD", "OS"):
            _, y_sup = coords_for(eye, "superior")
            _, y_inf = coords_for(eye, "inferior")
            assert y_sup < 0.5 and y_inf > 0.5


# --- /propose-from-findings endpoint -----------------------------------


SECRET_PHRASE = "PRIVATE_FINDINGS_TOKEN_QQQ"


def _post_proposal(client, headers, patient_id: int, text: str):
    return client.post(
        f"/patients/{patient_id}/eye-diagrams/propose-from-findings",
        headers=headers,
        json={"findings_text": text},
    )


class TestProposeRoute:
    def test_admin_and_clinician_can_propose(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        for headers in (ADMIN1, CLIN1):
            r = _post_proposal(client, headers, pid, "OD drusen at macula.")
            assert r.status_code == 200, r.json()
            body = r.json()
            assert len(body["proposed_annotations"]) == 1
            assert body["proposed_annotations"][0]["symbol_type"] == "drusen"

    def test_reviewer_cannot_propose(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _post_proposal(client, REV1, pid, "OD drusen at macula.")
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_unauthenticated_blocked(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = client.post(
            f"/patients/{pid}/eye-diagrams/propose-from-findings",
            json={"findings_text": "OD drusen at macula."},
        )
        assert r.status_code == 401

    def test_cross_org_returns_404_patient_not_found(self, client, seeded_ids):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        r = _post_proposal(client, ADMIN2, pid, "OD drusen at macula.")
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_does_not_persist_chart_artifacts_row(self, client, seeded_ids):
        from app.db import fetch_one

        pid = _patient_id_for(seeded_ids, "PT-1001")
        before = fetch_one(
            "SELECT COUNT(*) AS n FROM chart_artifacts "
            "WHERE patient_id = :pid",
            {"pid": pid},
        )
        r = _post_proposal(
            client, CLIN1, pid, "OD drusen at macula. OS flame hemorrhage."
        )
        assert r.status_code == 200
        after = fetch_one(
            "SELECT COUNT(*) AS n FROM chart_artifacts "
            "WHERE patient_id = :pid",
            {"pid": pid},
        )
        assert after["n"] == before["n"]

    def test_audit_records_metadata_only(self, client, seeded_ids):
        from app.db import fetch_all

        pid = _patient_id_for(seeded_ids, "PT-1001")
        # Plant a sentinel token in findings_text + a finding so the
        # audit row is generated.
        text = f"OD drusen at macula. {SECRET_PHRASE}."
        r = _post_proposal(client, CLIN1, pid, text)
        assert r.status_code == 200

        rows = fetch_all(
            "SELECT event_type, detail FROM security_audit_events "
            "WHERE event_type = 'eye_diagram_proposed' ORDER BY id"
        )
        assert rows, "expected at least one eye_diagram_proposed audit row"
        last = rows[-1]
        assert last["event_type"] == "eye_diagram_proposed"
        assert SECRET_PHRASE not in (last["detail"] or "")
        assert "drusen" not in (last["detail"] or "")
        assert "proposal_count=" in (last["detail"] or "")
        assert "uncertain_count=" in (last["detail"] or "")
        assert "missing_flag_count=" in (last["detail"] or "")

    def test_proposal_response_includes_uncertain_and_missing(
        self, client, seeded_ids
    ):
        pid = _patient_id_for(seeded_ids, "PT-1001")
        text = (
            "Drusen at macula. "  # missing laterality
            "Patient seemed cheerful today. "  # uncertain
            "OS flame hemorrhage superior."
        )
        r = _post_proposal(client, CLIN1, pid, text)
        body = r.json()
        assert body["missing_flags"], "expected a missing_laterality flag"
        assert any(
            "cheerful" in u.lower() for u in body["uncertain_phrases"]
        )
        assert any(
            p["symbol_type"] == "flame_hemorrhage" for p in body["proposed_annotations"]
        )
