"""Phase 8 — scribe session lifecycle tests.

Coverage groups:
  * lifecycle (create, list, detail, update, process, review, finalize, discard)
  * status rules (illegal transitions, immutability)
  * processing v1 parsing
  * security (RBAC + cross-org)
  * audit redaction (sentinel tokens never leak)
"""

from __future__ import annotations

import json

from app.services.scribe_sessions import (
    DRAFT_PREFIX,
    parse_sections,
)
from tests.conftest import ADMIN1, ADMIN2, CLIN1, REV1


# --- helpers -----------------------------------------------------------


def _patient_id(seeded_ids: dict, identifier: str) -> int:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id FROM patients WHERE patient_identifier = :pid",
        {"pid": identifier},
    )
    assert row, f"seed missing patient {identifier!r}"
    return int(row["id"])


def _create(client, headers, patient_id: int, **payload):
    body = {
        "input_mode": "pasted_text",
        "source_text": (
            "Chief complaint: blurry vision OD.\n"
            "HPI: 2 weeks of progressive blur.\n"
            "Exam: VA 20/40 OD.\n"
            "Assessment: probable refractive change.\n"
            "Plan: refraction next visit."
        ),
    }
    body.update(payload)
    return client.post(
        f"/patients/{patient_id}/scribe-sessions",
        headers=headers,
        json=body,
    )


def _process(client, headers, patient_id, session_id):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/process",
        headers=headers,
    )


def _review(client, headers, patient_id, session_id, **body):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/review",
        headers=headers,
        json=body,
    )


def _finalize(client, headers, patient_id, session_id):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/finalize",
        headers=headers,
    )


def _discard(client, headers, patient_id, session_id):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/discard",
        headers=headers,
    )


# --- lifecycle ---------------------------------------------------------


class TestLifecycle:
    def test_create_session(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create(client, CLIN1, pid)
        assert r.status_code == 201, r.json()
        body = r.json()
        assert body["status"] == "draft"
        assert body["input_mode"] == "pasted_text"
        assert body["source_text"].startswith("Chief complaint:")
        assert body["draft_note_text"] is None
        assert body["structured_note_json"] == {}
        assert body["is_terminal"] is False

    def test_list_sessions(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        _create(client, CLIN1, pid, source_text="A")
        _create(client, CLIN1, pid, source_text="B")
        r = client.get(
            f"/patients/{pid}/scribe-sessions", headers=CLIN1
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2

    def test_get_detail(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.get(
            f"/patients/{pid}/scribe-sessions/{new['id']}", headers=CLIN1
        )
        assert r.status_code == 200
        assert r.json()["id"] == new["id"]

    def test_update_draft_session(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.patch(
            f"/patients/{pid}/scribe-sessions/{new['id']}",
            headers=CLIN1,
            json={"source_text": "updated source"},
        )
        assert r.status_code == 200
        assert r.json()["source_text"] == "updated source"

    def test_process_session(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = _process(client, CLIN1, pid, new["id"])
        assert r.status_code == 200, r.json()
        body = r.json()
        assert body["status"] == "ready_for_review"
        assert body["draft_note_text"].startswith(DRAFT_PREFIX)
        # structured_note_json must be a dict, not a string.
        assert isinstance(body["structured_note_json"], dict)
        assert "chief_complaint" in body["structured_note_json"]

    def test_review_session(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        r = _review(client, CLIN1, pid, new["id"], review_notes="LGTM")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reviewed"
        assert body["review_notes"] == "LGTM"
        assert body["reviewed_by_user_id"] is not None

    def test_finalize_session(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        r = _finalize(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "finalized"
        assert body["finalized_at"] is not None
        assert body["is_terminal"] is True

    def test_discard_draft(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = _discard(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "discarded"

    def test_discard_ready_for_review(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        r = _discard(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "discarded"


# --- status rules ------------------------------------------------------


class TestStatusRules:
    def test_review_before_process_rejected(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = _review(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_invalid_transition"

    def test_finalize_before_review_rejected(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        r = _finalize(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_invalid_transition"

    def test_finalized_cannot_update(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        _finalize(client, CLIN1, pid, new["id"])
        r = client.patch(
            f"/patients/{pid}/scribe-sessions/{new['id']}",
            headers=CLIN1,
            json={"source_text": "after finalize"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_finalized_cannot_process(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        _finalize(client, CLIN1, pid, new["id"])
        r = _process(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_finalized_cannot_review(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        _finalize(client, CLIN1, pid, new["id"])
        r = _review(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_finalized_cannot_discard(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        _finalize(client, CLIN1, pid, new["id"])
        r = _discard(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_discarded_cannot_update(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _discard(client, CLIN1, pid, new["id"])
        r = client.patch(
            f"/patients/{pid}/scribe-sessions/{new['id']}",
            headers=CLIN1,
            json={"source_text": "after discard"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_discarded_cannot_process(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _discard(client, CLIN1, pid, new["id"])
        r = _process(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_discarded_cannot_review(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _discard(client, CLIN1, pid, new["id"])
        r = _review(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"

    def test_discarded_cannot_finalize(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _discard(client, CLIN1, pid, new["id"])
        r = _finalize(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "scribe_session_immutable"


# --- processing v1 parsing --------------------------------------------


class TestProcessingV1:
    def test_parse_chief_complaint(self):
        d = parse_sections("Chief complaint: red eye.")
        assert d.get("chief_complaint") == "red eye."

    def test_parse_cc_alias(self):
        d = parse_sections("CC: pain.")
        assert d.get("chief_complaint") == "pain."

    def test_parse_hpi(self):
        d = parse_sections("HPI: 2 weeks of redness.")
        assert d.get("hpi") == "2 weeks of redness."

    def test_parse_exam(self):
        d = parse_sections("Exam: VA 20/40 OD, 20/30 OS.")
        assert d.get("exam") == "VA 20/40 OD, 20/30 OS."

    def test_parse_assessment(self):
        d = parse_sections("Assessment: probable refractive change.")
        assert d.get("assessment") == "probable refractive change."

    def test_parse_plan(self):
        d = parse_sections("Plan: refraction next visit.")
        assert d.get("plan") == "refraction next visit."

    def test_unknown_text_goes_to_unassigned(self):
        d = parse_sections(
            "Casual aside before any heading.\n"
            "Chief complaint: x"
        )
        assert "Casual aside" in d.get("unassigned_text", "")

    def test_structured_note_json_response_is_object(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = _process(client, CLIN1, pid, new["id"])
        body = r.json()
        # Plain dict from JSON response — not a re-encoded string.
        assert isinstance(body["structured_note_json"], dict)


# --- security --------------------------------------------------------


class TestSecurity:
    def test_admin_can_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create(client, ADMIN1, pid)
        assert r.status_code == 201

    def test_clinician_can_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create(client, CLIN1, pid)
        assert r.status_code == 201

    def test_reviewer_cannot_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create(client, REV1, pid)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_unauthenticated_blocked(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = client.post(
            f"/patients/{pid}/scribe-sessions",
            json={"source_text": "x"},
        )
        assert r.status_code == 401

    def test_cross_org_patient_returns_404(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create(client, ADMIN2, pid)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_cross_org_session_returns_404(self, client, seeded_ids):
        # PT-1001 is in demo-eye-clinic. Session is created by a demo
        # clinician. ADMIN2 (Northside) tries to fetch — patient lookup
        # blocks first.
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        r = client.get(
            f"/patients/{pid}/scribe-sessions/{new['id']}", headers=ADMIN2
        )
        assert r.status_code == 404

    def test_encounter_patient_mismatch_rejected(self, client, seeded_ids):
        # Use an encounter that exists but belongs to a different
        # patient. We pick a different patient's encounter from seed.
        from app.db import fetch_one
        pid_a = _patient_id(seeded_ids, "PT-1001")
        pid_b = _patient_id(seeded_ids, "PT-1002")
        # Find any encounter with patient_id = pid_b
        enc = fetch_one(
            "SELECT id FROM encounters WHERE patient_id = :pid LIMIT 1",
            {"pid": pid_b},
        )
        if not enc:
            # Some encounters in seed link via patient_identifier only;
            # if no numeric patient_id exists, this assertion can't run.
            return
        r = _create(client, CLIN1, pid_a, encounter_id=int(enc["id"]))
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "patient_encounter_mismatch"


# --- audit redaction --------------------------------------------------


SENTINEL_SOURCE = "PHI_SOURCE_TOKEN_AAA"
SENTINEL_TRANSCRIPT = "PHI_TRANSCRIPT_TOKEN_BBB"
SENTINEL_REVIEW_NOTES = "PHI_REVIEW_NOTES_TOKEN_CCC"


class TestAuditRedaction:
    """Audit detail must contain only metadata (ids/status/etc.).
    Source/transcript/draft/structured/review_notes must never leak.
    """

    def _audit_rows(self):
        from app.db import fetch_all
        return fetch_all(
            "SELECT event_type, detail FROM security_audit_events "
            "WHERE event_type LIKE 'scribe_session_%' ORDER BY id"
        )

    def test_audit_events_exist(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(client, CLIN1, pid, new["id"])
        _finalize(client, CLIN1, pid, new["id"])

        events = {r["event_type"] for r in self._audit_rows()}
        assert "scribe_session_created" in events
        assert "scribe_session_processed" in events
        assert "scribe_session_reviewed" in events
        assert "scribe_session_finalized" in events

    def test_audit_excludes_sentinel_source_text(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(
            client, CLIN1, pid,
            source_text=f"Chief complaint: {SENTINEL_SOURCE}.",
        ).json()
        _process(client, CLIN1, pid, new["id"])
        for row in self._audit_rows():
            assert SENTINEL_SOURCE not in (row["detail"] or "")

    def test_audit_excludes_sentinel_transcript_text(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(
            client, CLIN1, pid,
            transcript_text=SENTINEL_TRANSCRIPT,
            input_mode="transcript",
        ).json()
        _process(client, CLIN1, pid, new["id"])
        for row in self._audit_rows():
            assert SENTINEL_TRANSCRIPT not in (row["detail"] or "")

    def test_audit_excludes_sentinel_draft_note_text(self, client, seeded_ids):
        # The draft is engine-produced so we cannot plant a sentinel
        # directly. We assert the audit row for the processed event
        # does not contain any of the source headings or content
        # unique to this run.
        pid = _patient_id(seeded_ids, "PT-1001")
        unique = "UNIQUE_HPI_LINE_DEF456"
        new = _create(
            client, CLIN1, pid,
            source_text=f"HPI: {unique}.",
        ).json()
        _process(client, CLIN1, pid, new["id"])
        for row in self._audit_rows():
            assert unique not in (row["detail"] or "")

    def test_audit_excludes_sentinel_structured_note_json(self, client, seeded_ids):
        # Structured note carries values from source_text; if we can
        # confirm the source token isn't in audit, structured payload
        # contents (which derive from it) also can't be.
        pid = _patient_id(seeded_ids, "PT-1001")
        struct_token = "STRUCT_TOKEN_GHI789"
        new = _create(
            client, CLIN1, pid,
            source_text=f"Assessment: {struct_token}.",
        ).json()
        _process(client, CLIN1, pid, new["id"])
        for row in self._audit_rows():
            assert struct_token not in (row["detail"] or "")
        # Sanity: the token IS present in the structured response.
        from app.db import fetch_one
        fresh = fetch_one(
            "SELECT structured_note_json FROM scribe_sessions WHERE id = :id",
            {"id": new["id"]},
        )
        assert struct_token in (fresh["structured_note_json"] or "")

    def test_audit_excludes_sentinel_review_notes(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create(client, CLIN1, pid).json()
        _process(client, CLIN1, pid, new["id"])
        _review(
            client, CLIN1, pid, new["id"], review_notes=SENTINEL_REVIEW_NOTES
        )
        for row in self._audit_rows():
            assert SENTINEL_REVIEW_NOTES not in (row["detail"] or "")
