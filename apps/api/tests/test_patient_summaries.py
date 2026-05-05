"""Phase 9 — patient-friendly summary lifecycle tests.

Coverage groups:
  * lifecycle (create, list, detail, update, review, finalize, discard)
  * generator (structured note source, draft fallback, sparse limitations)
  * status rules (illegal transitions, immutability)
  * response shape (key_findings/next_steps/questions are arrays)
  * security (RBAC + cross-org)
  * audit redaction (sentinel tokens never leak)
"""

from __future__ import annotations

import json

from app.services.patient_summaries import (
    DEFAULT_LIMITATIONS_NOTICE,
    generate_summary,
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


def _create_scribe(client, headers, patient_id, **payload):
    body = {
        "input_mode": "pasted_text",
        "source_text": (
            "Chief complaint: blurry vision OD.\n"
            "HPI: 2 weeks of progressive blur.\n"
            "Exam: VA 20/40 OD, IOP 18 mmHg OU.\n"
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


def _process_scribe(client, headers, patient_id, session_id):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/process",
        headers=headers,
    )


def _create_summary(client, headers, patient_id, **payload):
    return client.post(
        f"/patients/{patient_id}/patient-summaries",
        headers=headers,
        json=payload,
    )


def _review_summary(client, headers, patient_id, summary_id, **body):
    return client.post(
        f"/patients/{patient_id}/patient-summaries/{summary_id}/review",
        headers=headers,
        json=body,
    )


def _finalize_summary(client, headers, patient_id, summary_id):
    return client.post(
        f"/patients/{patient_id}/patient-summaries/{summary_id}/finalize",
        headers=headers,
    )


def _discard_summary(client, headers, patient_id, summary_id):
    return client.post(
        f"/patients/{patient_id}/patient-summaries/{summary_id}/discard",
        headers=headers,
    )


def _summary_with_processed_scribe(client, headers, patient_id):
    """Helper: create a scribe session, process it, then create a
    summary from it. Returns the created summary JSON dict."""
    sess = _create_scribe(client, headers, patient_id).json()
    _process_scribe(client, headers, patient_id, sess["id"])
    return _create_summary(
        client, headers, patient_id, scribe_session_id=sess["id"]
    ).json()


# --- generator (pure-logic, no DB) -------------------------------------


class TestGenerator:
    def test_structured_note_drives_summary(self):
        result = generate_summary(
            structured_note={
                "chief_complaint": "blurry vision OD",
                "hpi": "2 weeks of progressive blur",
                "exam": "VA 20/40 OD",
                "assessment": "probable refractive change",
                "plan": "refraction next visit",
            },
            draft_note_text=None,
        )
        assert "blurry vision OD" in result.plain_language_summary
        assert any("VA 20/40 OD" in f for f in result.key_findings)
        assert any("refraction" in s for s in result.next_steps)
        assert result.limitations_notice == DEFAULT_LIMITATIONS_NOTICE

    def test_draft_note_fallback_with_extra_limitation(self):
        result = generate_summary(
            structured_note={},
            draft_note_text="Draft — provider review required\n\nProvider notes...",
        )
        assert "draft" in result.plain_language_summary.lower()
        # We do not parse the draft; details aren't extracted.
        assert result.key_findings == []
        # Limitations notice is augmented for draft fallback.
        assert "unprocessed draft" in result.limitations_notice

    def test_sparse_source_includes_limitation_notice(self):
        result = generate_summary(structured_note=None, draft_note_text=None)
        # Always returns a real notice.
        assert result.limitations_notice
        assert DEFAULT_LIMITATIONS_NOTICE.split(".")[0] in result.limitations_notice
        assert "No structured chart text" in result.limitations_notice
        # Plain summary still says something safe.
        assert result.plain_language_summary

    def test_no_diagnosis_invented(self):
        # Even if "assessment" is missing, the summary should not
        # invent a diagnosis claim.
        result = generate_summary(
            structured_note={"chief_complaint": "headache for 2 days"},
            draft_note_text=None,
        )
        assert "diagnos" not in result.plain_language_summary.lower()
        assert "treat" not in result.plain_language_summary.lower()
        assert "prescrib" not in result.plain_language_summary.lower()

    def test_provider_instructions_appended_verbatim(self):
        result = generate_summary(
            structured_note={"plan": "follow up in 2 weeks"},
            draft_note_text=None,
            provider_instructions="Mention that the office is closed Friday.",
        )
        assert "Note from your provider" in result.plain_language_summary
        assert "office is closed Friday" in result.plain_language_summary


# --- lifecycle ---------------------------------------------------------


class TestLifecycle:
    def test_create_summary(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        body = _summary_with_processed_scribe(client, CLIN1, pid)
        assert body["status"] == "draft"
        assert body["plain_language_summary"]
        assert isinstance(body["key_findings"], list)
        assert isinstance(body["next_steps"], list)
        assert isinstance(body["questions"], list)
        assert body["limitations_notice"]
        assert body["scribe_session_id"] is not None
        assert body["is_terminal"] is False

    def test_list_summaries(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        _create_summary(client, CLIN1, pid)
        _create_summary(client, CLIN1, pid)
        r = client.get(
            f"/patients/{pid}/patient-summaries", headers=CLIN1
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2

    def test_get_detail(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = client.get(
            f"/patients/{pid}/patient-summaries/{new['id']}", headers=CLIN1
        )
        assert r.status_code == 200
        assert r.json()["id"] == new["id"]

    def test_update_draft_summary(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={
                "plain_language_summary": "Provider edited summary.",
                "key_findings": ["Edited finding 1"],
                "next_steps": ["Schedule follow-up"],
                "questions": ["Q1"],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["plain_language_summary"] == "Provider edited summary."
        assert body["key_findings"] == ["Edited finding 1"]
        assert body["next_steps"] == ["Schedule follow-up"]
        assert body["questions"] == ["Q1"]

    def test_review_draft(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = _review_summary(client, CLIN1, pid, new["id"], review_notes="ok")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "reviewed"
        assert body["review_notes"] == "ok"
        assert body["reviewed_by_user_id"] is not None

    def test_finalize_reviewed(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, new["id"])
        r = _finalize_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "finalized"
        assert body["finalized_at"] is not None
        assert body["is_terminal"] is True

    def test_discard_draft(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = _discard_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "discarded"

    def test_discard_reviewed(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, new["id"])
        r = _discard_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "discarded"


# --- status rules ------------------------------------------------------


class TestStatusRules:
    def test_reject_direct_draft_to_finalize(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = _finalize_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_invalid_transition"

    def test_finalized_cannot_update(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, new["id"])
        _finalize_summary(client, CLIN1, pid, new["id"])
        r = client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"plain_language_summary": "after finalize"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"

    def test_finalized_cannot_review(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, new["id"])
        _finalize_summary(client, CLIN1, pid, new["id"])
        r = _review_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"

    def test_finalized_cannot_discard(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, new["id"])
        _finalize_summary(client, CLIN1, pid, new["id"])
        r = _discard_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"

    def test_discarded_cannot_update(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _discard_summary(client, CLIN1, pid, new["id"])
        r = client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"plain_language_summary": "after discard"},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"

    def test_discarded_cannot_review(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _discard_summary(client, CLIN1, pid, new["id"])
        r = _review_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"

    def test_discarded_cannot_finalize(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _discard_summary(client, CLIN1, pid, new["id"])
        r = _finalize_summary(client, CLIN1, pid, new["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "patient_summary_immutable"


# --- generator-via-route -----------------------------------------------


class TestGeneratorViaRoute:
    def test_generate_from_structured_note(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        body = _summary_with_processed_scribe(client, CLIN1, pid)
        # Source for the seed scribe text → these phrases should land
        # in the produced summary content.
        assert "blurry vision OD" in body["plain_language_summary"]
        assert any("VA 20/40 OD" in f for f in body["key_findings"])
        assert any("refraction" in s for s in body["next_steps"])
        assert body["limitations_notice"] == DEFAULT_LIMITATIONS_NOTICE

    def test_generate_from_draft_note_fallback(self, client, seeded_ids):
        # Create a scribe session WITHOUT structured headings so process
        # produces no structured fields → generator falls back to draft.
        pid = _patient_id(seeded_ids, "PT-1001")
        sess = _create_scribe(
            client, CLIN1, pid,
            source_text="Just some narrative without headings.",
        ).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        body = _create_summary(
            client, CLIN1, pid, scribe_session_id=sess["id"]
        ).json()
        assert "draft" in body["plain_language_summary"].lower()
        assert "unprocessed draft" in body["limitations_notice"]

    def test_sparse_source_includes_limitation(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        body = _create_summary(client, CLIN1, pid).json()
        assert body["limitations_notice"]
        assert "No structured chart text" in body["limitations_notice"]


# --- response shape: lists are real lists, not strings -----------------


class TestResponseShape:
    def test_create_response_lists_are_arrays(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        body = _summary_with_processed_scribe(client, CLIN1, pid)
        for key in ("key_findings", "next_steps", "questions"):
            assert isinstance(body[key], list)
            for item in body[key]:
                assert isinstance(item, str)

    def test_list_response_lists_are_arrays(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        _create_summary(client, CLIN1, pid)
        r = client.get(
            f"/patients/{pid}/patient-summaries", headers=CLIN1
        )
        assert isinstance(r.json()["items"][0]["key_findings"], list)


# --- security ---------------------------------------------------------


class TestSecurity:
    def test_admin_can_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create_summary(client, ADMIN1, pid)
        assert r.status_code == 201

    def test_clinician_can_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create_summary(client, CLIN1, pid)
        assert r.status_code == 201

    def test_reviewer_cannot_write(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create_summary(client, REV1, pid)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_unauthenticated_blocked(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = client.post(f"/patients/{pid}/patient-summaries", json={})
        assert r.status_code == 401

    def test_cross_org_patient_returns_404(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        r = _create_summary(client, ADMIN2, pid)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_cross_org_summary_returns_404(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        r = client.get(
            f"/patients/{pid}/patient-summaries/{new['id']}", headers=ADMIN2
        )
        assert r.status_code == 404

    def test_source_scribe_org_mismatch_rejected(self, client, seeded_ids):
        # Create a scribe session for an Org B patient, then try to use
        # it as the source for an Org A summary. Should be rejected as
        # scribe_session_not_found (org isolation).
        pid_b = _patient_id(seeded_ids, "PT-2001")  # Northside patient
        sess_b = _create_scribe(client, ADMIN2, pid_b).json()

        pid_a = _patient_id(seeded_ids, "PT-1001")  # Demo patient
        r = _create_summary(
            client, CLIN1, pid_a, scribe_session_id=sess_b["id"]
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "scribe_session_not_found"

    def test_source_scribe_patient_mismatch_rejected(self, client, seeded_ids):
        # Both patients in the same org. Scribe session belongs to
        # PT-1002; summary requested under PT-1001. Should reject.
        pid_a = _patient_id(seeded_ids, "PT-1001")
        pid_b = _patient_id(seeded_ids, "PT-1002")
        sess_b = _create_scribe(client, CLIN1, pid_b).json()

        r = _create_summary(
            client, CLIN1, pid_a, scribe_session_id=sess_b["id"]
        )
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "scribe_session_not_found"


# --- audit redaction --------------------------------------------------


SENTINEL_SUMMARY = "PHI_PLS_TOKEN_AAA"
SENTINEL_KF = "PHI_KF_TOKEN_BBB"
SENTINEL_NS = "PHI_NS_TOKEN_CCC"
SENTINEL_Q = "PHI_Q_TOKEN_DDD"
SENTINEL_NOTES = "PHI_NOTES_TOKEN_EEE"


class TestAuditRedaction:
    def _audit_rows(self):
        from app.db import fetch_all
        return fetch_all(
            "SELECT event_type, detail FROM security_audit_events "
            "WHERE event_type LIKE 'patient_summary_%' ORDER BY id"
        )

    def test_audit_events_exist(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"plain_language_summary": "edit"},
        )
        _review_summary(client, CLIN1, pid, new["id"])
        _finalize_summary(client, CLIN1, pid, new["id"])

        events = {r["event_type"] for r in self._audit_rows()}
        assert "patient_summary_created" in events
        assert "patient_summary_updated" in events
        assert "patient_summary_reviewed" in events
        assert "patient_summary_finalized" in events

    def test_audit_excludes_sentinel_summary_body(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"plain_language_summary": SENTINEL_SUMMARY},
        )
        for row in self._audit_rows():
            assert SENTINEL_SUMMARY not in (row["detail"] or "")

    def test_audit_excludes_sentinel_key_findings(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"key_findings": [SENTINEL_KF]},
        )
        for row in self._audit_rows():
            assert SENTINEL_KF not in (row["detail"] or "")

    def test_audit_excludes_sentinel_next_steps(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"next_steps": [SENTINEL_NS]},
        )
        for row in self._audit_rows():
            assert SENTINEL_NS not in (row["detail"] or "")

    def test_audit_excludes_sentinel_questions(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{new['id']}",
            headers=CLIN1,
            json={"questions": [SENTINEL_Q]},
        )
        for row in self._audit_rows():
            assert SENTINEL_Q not in (row["detail"] or "")

    def test_audit_excludes_sentinel_review_notes(self, client, seeded_ids):
        pid = _patient_id(seeded_ids, "PT-1001")
        new = _create_summary(client, CLIN1, pid).json()
        _review_summary(
            client, CLIN1, pid, new["id"], review_notes=SENTINEL_NOTES
        )
        for row in self._audit_rows():
            assert SENTINEL_NOTES not in (row["detail"] or "")
