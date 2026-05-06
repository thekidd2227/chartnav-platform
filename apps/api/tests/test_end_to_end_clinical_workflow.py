"""Phase 12 — end-to-end clinical workflow integration tests.

Drives a realistic provider workflow across phases 6 / 8 / 9 / 10 / 11
in a single seeded org / patient / encounter so we catch wiring
defects between modules:

  patient context
    → scribe session
    → findings / proposals
    → retinal diagram
    → patient-friendly summary
    → pre-visit brief
    → provider action review queue

These tests do NOT introduce a new product surface — they exercise
existing routes end-to-end, assert audit safety across the full path,
and assert the safety language contract holds when all phases are
populated.

NB: anything that touches the DB must be imported INSIDE the test
function — module-level imports of `app.db` (transitive via the
service modules) bind to whatever `DATABASE_URL` is set at pytest
import time, BEFORE the per-test fixture swaps in the temp SQLite
URL. We follow the same deferred-import pattern used by
test_pre_visit_briefs.py and test_provider_action_items.py.
"""

from __future__ import annotations

import json

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _patient_id(identifier: str) -> int:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id FROM patients WHERE patient_identifier = :p",
        {"p": identifier},
    )
    assert row, f"seed missing patient {identifier!r}"
    return int(row["id"])


def _audit_rows(prefix: str = ""):
    from app.db import fetch_all
    if prefix:
        return fetch_all(
            "SELECT event_type, detail FROM security_audit_events "
            "WHERE event_type LIKE :p ORDER BY id",
            {"p": f"{prefix}%"},
        )
    return fetch_all(
        "SELECT event_type, detail FROM security_audit_events ORDER BY id"
    )


# Source-text sentinels — injected at every clinical-body field we
# can write to, then asserted absent from every audit row at the end.
SEN_SOURCE = "PHI_E2E_SOURCE_TOKEN_AAA"
SEN_FINDINGS = "PHI_E2E_FINDINGS_TOKEN_BBB"
SEN_SUMMARY = "PHI_E2E_SUMMARY_TOKEN_CCC"
SEN_REVIEW = "PHI_E2E_REVIEW_TOKEN_DDD"


# Realistic ophthalmology-flavored source text used to seed the
# scribe session. Includes language the Phase 11 generator should
# pick up (retinal tear) plus benign findings (drusen).
_SCRIBE_SOURCE = (
    "Chief complaint: blurry vision OD, two weeks.\n"
    "HPI: progressive blur OD, no flashes/floaters today.\n"
    "Exam: VA 20/40 OD, 20/20 OS. IOP 16/14. "
    "OD drusen at macula; possible retinal tear superior temporal OS.\n"
    "Assessment: drusen OD; suspected retinal tear OS pending review.\n"
    f"Plan: refraction next visit; monitor OS. ({SEN_SOURCE})"
)


def _seed_scribe_finalized(client) -> tuple[int, int]:
    """Walk a scribe session through draft → finalized for PT-1001.

    Returns `(patient_id, session_id)`.
    """
    pid = _patient_id("PT-1001")
    create = client.post(
        f"/patients/{pid}/scribe-sessions",
        headers=CLIN1,
        json={"input_mode": "pasted_text", "source_text": _SCRIBE_SOURCE},
    )
    assert create.status_code == 201, create.text
    sid = create.json()["id"]

    process = client.post(
        f"/patients/{pid}/scribe-sessions/{sid}/process",
        headers=CLIN1,
    )
    assert process.status_code == 200, process.text

    review = client.post(
        f"/patients/{pid}/scribe-sessions/{sid}/review",
        headers=CLIN1,
        json={},
    )
    assert review.status_code == 200, review.text

    finalize = client.post(
        f"/patients/{pid}/scribe-sessions/{sid}/finalize",
        headers=CLIN1,
    )
    assert finalize.status_code == 200, finalize.text
    return pid, sid


# ---------------------------------------------------------------------
# 1) Phase 12A live route smoke — every critical route is wired
# ---------------------------------------------------------------------


class TestRouteSanity:
    """Confirm every critical route from phases 5B / 6 / 8 / 9 / 10 / 11
    is registered in the app router and answers within an
    org-scoped 200 / 201 (or returns a documented 4xx for invalid
    payload — never 404 due to missing route)."""

    def test_eye_diagrams_list_route_registered(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = client.get(f"/patients/{pid}/eye-diagrams", headers=CLIN1)
        assert r.status_code == 200, r.text

    def test_propose_from_findings_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/eye-diagrams/propose-from-findings",
            headers=CLIN1,
            json={"findings_text": ""},
        )
        assert r.status_code == 200, r.text

    def test_scribe_sessions_list_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.get(f"/patients/{pid}/scribe-sessions", headers=CLIN1)
        assert r.status_code == 200, r.text

    def test_patient_summaries_list_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.get(
            f"/patients/{pid}/patient-summaries", headers=CLIN1
        )
        assert r.status_code == 200, r.text

    def test_pre_visit_brief_get_route_registered(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = client.get(f"/patients/{pid}/pre-visit-brief", headers=CLIN1)
        assert r.status_code == 200, r.text

    def test_pre_visit_brief_generate_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/pre-visit-briefs/generate", headers=CLIN1
        )
        assert r.status_code == 200, r.text

    def test_provider_action_items_list_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.get(
            f"/patients/{pid}/provider-action-items", headers=CLIN1
        )
        assert r.status_code == 200, r.text

    def test_provider_action_items_generate_route_registered(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        )
        assert r.status_code == 200, r.text


# ---------------------------------------------------------------------
# 2) Backend end-to-end workflow
# ---------------------------------------------------------------------


class TestScribeToProposal:
    """Phase 8 → Phase 6 — finalize a scribe note and pull diagram
    proposals from its findings text. Confirms the propose endpoint
    is read-only on data and returns the expected proposal shape."""

    def test_finalize_scribe_then_propose_diagram_from_findings(
        self, client, seeded_ids
    ):
        pid, sid = _seed_scribe_finalized(client)

        # Pull the finalized note's structured findings — the route
        # just needs a text blob, so we feed it the source text plus
        # an explicit findings phrase the proposal engine can match.
        findings_text = (
            "OD drusen at macula. Possible retinal tear superior temporal OS. "
            f"({SEN_FINDINGS})"
        )
        r = client.post(
            f"/patients/{pid}/eye-diagrams/propose-from-findings",
            headers=CLIN1,
            json={"findings_text": findings_text},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Shape contract.
        for key in (
            "clinical_text",
            "ignored_chatter",
            "uncertain_phrases",
            "proposed_annotations",
            "confidence_summary",
            "missing_flags",
        ):
            assert key in body
        # Endpoint is read-only — no chart_artifact created.
        listed = client.get(
            f"/patients/{pid}/eye-diagrams", headers=CLIN1
        ).json()
        assert listed["total"] == 0


class TestRetinalArtifactLifecycle:
    """Phase 5B / 6 — create an unsigned retinal diagram, apply a
    proposal-shaped payload manually (simulating provider acceptance
    of a proposal), sign the artifact, and assert sign-immutability."""

    def test_create_apply_proposal_payload_and_sign(
        self, client, seeded_ids
    ):
        pid, _sid = _seed_scribe_finalized(client)

        # Create unsigned artifact.
        create = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={
                "title": "OD/OS retina drawing",
                "findings_text": (
                    f"Drusen OD; possible retinal tear OS. ({SEN_FINDINGS})"
                ),
                "drawing_json": {},
            },
        )
        assert create.status_code == 201, create.text
        aid = create.json()["id"]

        # Apply a proposal-shaped payload that includes one approved
        # annotation marked source=ai_approved. The payload mirrors
        # what the frontend sends after the provider explicitly
        # applies a proposal — Phase 6 contract.
        applied = {
            "od": {
                "annotations": [
                    {
                        "id": "ann-1",
                        "kind": "drusen",
                        "x": 0.5,
                        "y": 0.5,
                        "source": "ai_approved",
                        "confidence": "moderate",
                    }
                ]
            },
            "os": {"annotations": []},
        }
        update = client.patch(
            f"/patients/{pid}/eye-diagrams/{aid}",
            headers=CLIN1,
            json={"drawing_json": applied},
        )
        assert update.status_code == 200, update.text
        assert update.json()["drawing_json"]["od"]["annotations"][0][
            "source"
        ] == "ai_approved"

        # Sign it.
        sign = client.post(
            f"/patients/{pid}/eye-diagrams/{aid}/sign", headers=CLIN1
        )
        assert sign.status_code == 200, sign.text
        assert sign.json()["signed_at"] is not None

        # Signed artifact is immutable in place — non-fork PATCH gets
        # 409 artifact_signed_immutable.
        followup = client.patch(
            f"/patients/{pid}/eye-diagrams/{aid}",
            headers=CLIN1,
            json={"findings_text": "edit attempt"},
        )
        assert followup.status_code == 409, followup.text
        assert followup.json()["detail"]["error_code"] == "artifact_signed_immutable"


class TestPatientSummaryFromFinalizedScribe:
    """Phase 9 — create a patient summary from a finalized scribe
    session, edit fields including a sentinel, review, finalize, and
    confirm the finalized summary is immutable."""

    def test_create_edit_review_finalize_summary_from_scribe(
        self, client, seeded_ids
    ):
        pid, sid = _seed_scribe_finalized(client)

        create = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        )
        assert create.status_code == 201, create.text
        smid = create.json()["id"]

        # Edit (provider-controlled fields). Inject a clinical sentinel
        # in the plain-language summary body and the review notes.
        edit = client.patch(
            f"/patients/{pid}/patient-summaries/{smid}",
            headers=CLIN1,
            json={
                "plain_language_summary": (
                    f"Visit recap including monitoring of OS. ({SEN_SUMMARY})"
                ),
                "key_findings": [
                    f"Drusen OD ({SEN_SUMMARY})",
                    "Possible retinal tear OS pending review",
                ],
                "next_steps": ["Refraction next visit", "Monitor OS"],
                "review_notes": f"Reviewer notes ({SEN_REVIEW})",
            },
        )
        assert edit.status_code == 200, edit.text

        # Review then finalize.
        review = client.post(
            f"/patients/{pid}/patient-summaries/{smid}/review",
            headers=CLIN1,
            json={"review_notes": f"Final reviewer notes ({SEN_REVIEW})"},
        )
        assert review.status_code == 200, review.text
        finalize = client.post(
            f"/patients/{pid}/patient-summaries/{smid}/finalize",
            headers=CLIN1,
        )
        assert finalize.status_code == 200, finalize.text
        assert finalize.json()["status"] == "finalized"

        # Finalized summary is immutable.
        retry = client.patch(
            f"/patients/{pid}/patient-summaries/{smid}",
            headers=CLIN1,
            json={"plain_language_summary": "edit attempt"},
        )
        assert retry.status_code == 409, retry.text
        assert (
            retry.json()["detail"]["error_code"] == "patient_summary_immutable"
        )


class TestPreVisitBriefIncludesAllSources:
    """Phase 10 — once scribe / artifact / summary all exist for a
    patient, the pre-visit brief surfaces them and reports
    source_counts > 0 for each. Asserts safety copy is present."""

    def test_brief_aggregates_all_phases(self, client, seeded_ids):
        # Seed scribe + summary.
        pid, sid = _seed_scribe_finalized(client)
        client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        # Walk that summary all the way through finalize.
        listed = client.get(
            f"/patients/{pid}/patient-summaries", headers=CLIN1
        ).json()
        assert listed["total"] >= 1
        smid = listed["items"][0]["id"]
        client.post(
            f"/patients/{pid}/patient-summaries/{smid}/review",
            headers=CLIN1,
            json={},
        )
        client.post(
            f"/patients/{pid}/patient-summaries/{smid}/finalize",
            headers=CLIN1,
        )
        # Seed + sign a retinal artifact.
        art = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={"title": "OD/OS macula", "drawing_json": {}},
        )
        aid = art.json()["id"]
        client.post(
            f"/patients/{pid}/eye-diagrams/{aid}/sign", headers=CLIN1
        )

        # Now pull the brief.
        brief = client.post(
            f"/patients/{pid}/pre-visit-briefs/generate", headers=CLIN1
        ).json()
        assert brief["brief_status"] == "generated"
        c = brief["source_counts"]
        assert c["scribe_sessions"] >= 1
        assert c["scribe_sessions_finalized"] >= 1
        assert c["retinal_artifacts"] >= 1
        assert c["retinal_artifacts_signed"] >= 1
        assert c["patient_summaries"] >= 1
        assert c["patient_summaries_finalized"] >= 1
        # Provider-review notice present and free of unsafe terms.
        assert "provider review required" in brief["notice"].lower()
        envelope = " | ".join([
            brief["notice"],
            brief["last_visit_summary"] or "",
            *(brief["data_gaps"] or []),
        ]).lower()
        for forbidden in (
            "autonomous", "external llm", "openai", "anthropic", "gpt",
            "place order", "send referral", "send to patient",
            "billing", "icd-10", "cpt code",
        ):
            assert forbidden not in envelope, envelope


class TestProviderActionLifecycleOverFullChart:
    """Phase 11 — once scribe / artifact / summary all exist, the
    provider action queue surfaces a mix of workflow + clinical
    review prompts. Drive the lifecycle: accept → complete on one,
    dismiss on another."""

    def test_full_chart_drives_action_lifecycle(
        self, client, seeded_ids
    ):
        # Seed full chart (signed artifact w/ retinal-tear language so
        # the clinical-language scan also fires).
        pid, sid = _seed_scribe_finalized(client)
        # Create + sign a retinal artifact whose findings include
        # retinal-tear language.
        art = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={
                "title": "OD/OS retina",
                "findings_text": (
                    "Possible retinal tear superior temporal OS."
                ),
                "drawing_json": {},
            },
        ).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{art['id']}/sign",
            headers=CLIN1,
        )
        # Reviewed (not yet finalized) summary so the queue surfaces
        # finalize_patient_summary too.
        sm = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        client.post(
            f"/patients/{pid}/patient-summaries/{sm['id']}/review",
            headers=CLIN1,
            json={},
        )

        # Generate.
        gen = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        ).json()
        assert gen["created_count"] >= 2, gen
        kinds = {it["action_type"] for it in gen["items"]}
        assert "review_retinal_tear_language" in kinds
        assert "finalize_patient_summary" in kinds

        # Walk lifecycle: accept + complete one; dismiss another.
        first = gen["items"][0]
        second = gen["items"][1]
        a = client.post(
            f"/patients/{pid}/provider-action-items/{first['id']}/accept",
            headers=CLIN1,
        )
        assert a.status_code == 200, a.text
        c = client.post(
            f"/patients/{pid}/provider-action-items/{first['id']}/complete",
            headers=CLIN1,
        )
        assert c.status_code == 200, c.text
        d = client.post(
            f"/patients/{pid}/provider-action-items/{second['id']}/dismiss",
            headers=CLIN1,
        )
        assert d.status_code == 200, d.text

        # Direct suggested → completed is rejected.
        third = gen["items"][2] if len(gen["items"]) > 2 else None
        if third is not None:
            r = client.post(
                f"/patients/{pid}/provider-action-items/{third['id']}/complete",
                headers=CLIN1,
            )
            assert r.status_code == 409, r.text


class TestEndToEndAuditRedaction:
    """Walk the entire workflow with sentinel tokens injected at every
    clinical-body field, then assert NONE of them appear in any
    `security_audit_events.detail` row across any phase."""

    def test_no_sentinel_leaks_into_audit_after_full_workflow(
        self, client, seeded_ids
    ):
        # 1) scribe session with sentinel.
        pid, sid = _seed_scribe_finalized(client)

        # 2) signed retinal artifact with sentinel in title + findings.
        art = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={
                "title": f"OD/OS retina ({SEN_FINDINGS})",
                "findings_text": (
                    f"Drusen OD; retinal tear OS pending review. "
                    f"({SEN_FINDINGS})"
                ),
                "drawing_json": {},
            },
        ).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{art['id']}/sign",
            headers=CLIN1,
        )

        # 3) patient summary with sentinel in body + review notes.
        sm = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        client.patch(
            f"/patients/{pid}/patient-summaries/{sm['id']}",
            headers=CLIN1,
            json={
                "plain_language_summary": f"Visit recap. ({SEN_SUMMARY})",
                "key_findings": [f"Drusen OD ({SEN_SUMMARY})"],
                "review_notes": f"Reviewer ({SEN_REVIEW})",
            },
        )
        client.post(
            f"/patients/{pid}/patient-summaries/{sm['id']}/review",
            headers=CLIN1,
            json={"review_notes": f"Reviewer final ({SEN_REVIEW})"},
        )
        client.post(
            f"/patients/{pid}/patient-summaries/{sm['id']}/finalize",
            headers=CLIN1,
        )

        # 4) pre-visit brief generated (POST audited).
        client.post(
            f"/patients/{pid}/pre-visit-briefs/generate", headers=CLIN1
        )

        # 5) action items generated + walked.
        gen = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        ).json()
        if gen["items"]:
            iid = gen["items"][0]["id"]
            client.post(
                f"/patients/{pid}/provider-action-items/{iid}/accept",
                headers=CLIN1,
            )
            client.post(
                f"/patients/{pid}/provider-action-items/{iid}/complete",
                headers=CLIN1,
            )

        # Assert: NO sentinel string appears in any audit detail row.
        rows = _audit_rows()
        assert rows, "expected at least one audit row across the workflow"
        for row in rows:
            detail = row["detail"] or ""
            assert SEN_SOURCE not in detail, (row["event_type"], detail)
            assert SEN_FINDINGS not in detail, (row["event_type"], detail)
            assert SEN_SUMMARY not in detail, (row["event_type"], detail)
            assert SEN_REVIEW not in detail, (row["event_type"], detail)


class TestEndToEndOrgIsolation:
    """Build the same workflow as PT-1001 in chartnav org, then
    confirm a caller from the northside org sees 404 patient_not_found
    on every Phase 6/8/9/10/11 surface."""

    def test_cross_org_workflow_is_isolated(self, client, seeded_ids):
        pid, sid = _seed_scribe_finalized(client)
        # Build a summary so we have a non-trivial chart.
        sm = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        # Sign a retinal artifact so we have a Phase 5B+6 source row.
        art = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={"title": "OD/OS macula", "drawing_json": {}},
        ).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{art['id']}/sign",
            headers=CLIN1,
        )
        # Generate a pre-visit brief and an action item for clinid1.
        client.post(
            f"/patients/{pid}/pre-visit-briefs/generate", headers=CLIN1
        )
        gen = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        ).json()

        # ADMIN2 is in northside — cross-org must return 404 on every
        # patient-id-bearing route.
        cross_calls = [
            ("GET", f"/patients/{pid}/eye-diagrams", None),
            (
                "POST",
                f"/patients/{pid}/eye-diagrams/propose-from-findings",
                {"findings_text": ""},
            ),
            ("GET", f"/patients/{pid}/eye-diagrams/{art['id']}", None),
            ("GET", f"/patients/{pid}/scribe-sessions", None),
            ("GET", f"/patients/{pid}/scribe-sessions/{sid}", None),
            ("GET", f"/patients/{pid}/patient-summaries", None),
            ("GET", f"/patients/{pid}/patient-summaries/{sm['id']}", None),
            ("GET", f"/patients/{pid}/pre-visit-brief", None),
            ("POST", f"/patients/{pid}/pre-visit-briefs/generate", None),
            ("GET", f"/patients/{pid}/provider-action-items", None),
            ("POST", f"/patients/{pid}/provider-action-items/generate", None),
        ]
        for method, path, body in cross_calls:
            if method == "GET":
                r = client.get(path, headers=ADMIN2)
            else:
                r = client.post(path, headers=ADMIN2, json=body or {})
            assert r.status_code == 404, (method, path, r.status_code, r.text)
            assert r.json()["detail"]["error_code"] == "patient_not_found", (
                method, path, r.json()
            )

        # If at least one action was generated, also confirm cross-org
        # action_id lookup is 404 too.
        if gen["items"]:
            iid = gen["items"][0]["id"]
            r = client.get(
                f"/patients/{pid}/provider-action-items/{iid}",
                headers=ADMIN2,
            )
            assert r.status_code == 404
            assert r.json()["detail"]["error_code"] == "patient_not_found"


class TestEndToEndSafetyLanguage:
    """Walk the workflow and assert every text field returned by every
    user-facing route is free of order / coding / referral / patient-
    messaging / autonomous-diagnosis / external-LLM language."""

    def test_no_unsafe_language_anywhere_in_workflow_payloads(
        self, client, seeded_ids
    ):
        pid, sid = _seed_scribe_finalized(client)
        # Seed full chart.
        client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={
                "title": "OD/OS retina",
                "findings_text": (
                    "Drusen OD; possible retinal tear OS pending review."
                ),
                "drawing_json": {},
            },
        )
        sm = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        client.post(
            f"/patients/{pid}/patient-summaries/{sm['id']}/review",
            headers=CLIN1,
            json={},
        )

        # Pull every key payload.
        brief = client.post(
            f"/patients/{pid}/pre-visit-briefs/generate", headers=CLIN1
        ).json()
        actions = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        ).json()

        # Forbidden phrases. The negative-assertion safety copy
        # ("ChartNav does not …") is allowed only on the panel — not
        # in service-emitted strings — but the brief notice and
        # action items don't include negative-assertion copy, so any
        # match here is a true positive.
        forbidden = (
            "place order", "order oct", "order an mri",
            "send referral", "submit referral", "refer to",
            "send to patient", "email patient", "sms patient",
            "portal push", "billing", "icd-10", "cpt code",
            "autonomous", "openai", "anthropic", "gpt-", "external llm",
        )
        # 1) Pre-visit brief envelope.
        envelope = " | ".join([
            brief.get("notice") or "",
            brief.get("last_visit_summary") or "",
            *(brief.get("data_gaps") or []),
        ]).lower()
        for needle in forbidden:
            assert needle not in envelope, (needle, envelope)
        # 2) Each action item.
        for it in actions.get("items", []):
            blob = (
                f"{it['action_type']} {it['title']} {it['reason']}"
            ).lower()
            for needle in forbidden:
                assert needle not in blob, (needle, blob)


class TestReviewerReadOnlyAcrossWorkflow:
    """RBAC sanity — a reviewer in the same org can read the workflow
    artifacts they're allowed to read, and is rejected from every
    write-side route across all phases."""

    def test_reviewer_can_read_and_cannot_write(self, client, seeded_ids):
        pid, sid = _seed_scribe_finalized(client)
        # Seed a summary + sign an artifact with admin/clinician.
        sm = client.post(
            f"/patients/{pid}/patient-summaries",
            headers=CLIN1,
            json={"scribe_session_id": sid},
        ).json()
        art = client.post(
            f"/patients/{pid}/eye-diagrams",
            headers=CLIN1,
            json={"title": "OD/OS retina", "drawing_json": {}},
        ).json()
        client.post(
            f"/patients/{pid}/eye-diagrams/{art['id']}/sign",
            headers=CLIN1,
        )
        gen = client.post(
            f"/patients/{pid}/provider-action-items/generate",
            headers=CLIN1,
        ).json()
        action_id = gen["items"][0]["id"] if gen["items"] else None

        # Reviewer reads — should succeed.
        for path in (
            f"/patients/{pid}/eye-diagrams",
            f"/patients/{pid}/scribe-sessions",
            f"/patients/{pid}/patient-summaries",
            f"/patients/{pid}/pre-visit-brief",
            f"/patients/{pid}/provider-action-items",
        ):
            r = client.get(path, headers=REV1)
            assert r.status_code == 200, (path, r.text)

        # Reviewer writes — every one should be 403 role_forbidden.
        write_attempts = [
            (
                "POST",
                f"/patients/{pid}/eye-diagrams",
                {"title": "x", "drawing_json": {}},
            ),
            (
                "POST",
                f"/patients/{pid}/eye-diagrams/propose-from-findings",
                {"findings_text": "x"},
            ),
            (
                "POST",
                f"/patients/{pid}/scribe-sessions",
                {"input_mode": "pasted_text", "source_text": "x"},
            ),
            (
                "POST",
                f"/patients/{pid}/patient-summaries",
                {},
            ),
            (
                "POST",
                f"/patients/{pid}/patient-summaries/{sm['id']}/review",
                {},
            ),
            (
                "POST",
                f"/patients/{pid}/pre-visit-briefs/generate",
                None,
            ),
            (
                "POST",
                f"/patients/{pid}/provider-action-items/generate",
                None,
            ),
        ]
        for method, path, body in write_attempts:
            r = client.post(path, headers=REV1, json=body or {})
            assert r.status_code == 403, (method, path, r.status_code, r.text)
            assert r.json()["detail"]["error_code"] == "role_forbidden", (
                method, path, r.json()
            )
        if action_id is not None:
            for op in ("accept", "dismiss", "complete"):
                r = client.post(
                    f"/patients/{pid}/provider-action-items/{action_id}/{op}",
                    headers=REV1,
                )
                assert r.status_code == 403, (op, r.text)
