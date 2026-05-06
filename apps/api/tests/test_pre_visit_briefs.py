"""Phase 10 — pre-visit clinical brief tests.

Coverage groups:
  * generation against an empty patient (data_gaps populated)
  * generation with encounters / scribe sessions / retinal artifacts /
    patient summaries / workflow events
  * source priority: finalized patient summary, reviewed/finalized
    scribe session, signed retinal artifact
  * pending vs. suggested-review classification
  * source_counts shape
  * RBAC: admin/clinician POST + GET; reviewer GET only; cross-org 404
  * audit: pre_visit_brief_generated event exists and excludes
    sentinel tokens for every section body
  * no autonomous-diagnosis language ever appears in the response
"""

from __future__ import annotations

import json

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


# NB: anything that touches the DB must be imported INSIDE the test
# function — module-level imports of `app.db` (transitive via
# `app.services.pre_visit_briefs`) would bind to the dev DATABASE_URL
# before the per-test fixture sets the temp SQLite URL.


# --- helpers -----------------------------------------------------------


def _patient_id(identifier: str) -> int:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT id FROM patients WHERE patient_identifier = :p",
        {"p": identifier},
    )
    assert row, f"seed missing patient {identifier!r}"
    return int(row["id"])


def _patient_org(identifier: str) -> int:
    from app.db import fetch_one
    row = fetch_one(
        "SELECT organization_id FROM patients WHERE patient_identifier = :p",
        {"p": identifier},
    )
    assert row
    return int(row["organization_id"])


def _generate_route(client, headers, patient_id):
    return client.post(
        f"/patients/{patient_id}/pre-visit-briefs/generate",
        headers=headers,
    )


def _get_route(client, headers, patient_id):
    return client.get(
        f"/patients/{patient_id}/pre-visit-brief",
        headers=headers,
    )


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


def _review_scribe(client, headers, patient_id, session_id, **body):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/review",
        headers=headers,
        json=body,
    )


def _finalize_scribe(client, headers, patient_id, session_id):
    return client.post(
        f"/patients/{patient_id}/scribe-sessions/{session_id}/finalize",
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


def _seed_chart_artifact(
    *,
    organization_id: int,
    patient_id: int,
    title: str,
    findings_text: str = "",
    signed: bool = True,
) -> int:
    """Direct-DB insert of a chart_artifacts row for retinal-summary tests.

    We bypass the eye-diagrams API because it's outside the Phase 10
    scope. Phase 10 only reads chart_artifacts; it never writes.
    """
    from datetime import datetime, timezone
    from app.db import insert_returning_id, transaction
    from sqlalchemy import text

    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        # Find an admin user in the same org to use as created_by.
        u = conn.execute(
            text(
                "SELECT id FROM users WHERE organization_id = :org "
                "AND role IN ('admin','clinician') LIMIT 1"
            ),
            {"org": organization_id},
        ).mappings().first()
        assert u is not None, "no admin/clinician seeded for org"
        cols = (
            "organization_id, patient_id, encounter_id, "
            "created_by_user_id, artifact_type, title, findings_text, "
            "drawing_json, version_number, parent_artifact_id, "
            "signed_at, signed_by_user_id, created_at, updated_at"
        )
        sql = text(
            f"INSERT INTO chart_artifacts ({cols}) VALUES ("
            ":org, :pid, NULL, :cb, 'retinal_diagram', :title, "
            ":findings, '{}', 1, NULL, "
            ":signed_at, :signed_by, :now, :now"
            ")"
        )
        conn.execute(
            sql,
            {
                "org": organization_id,
                "pid": patient_id,
                "cb": int(u["id"]),
                "title": title,
                "findings": findings_text,
                "signed_at": now if signed else None,
                "signed_by": int(u["id"]) if signed else None,
                "now": now,
            },
        )
        last = conn.execute(
            text(
                "SELECT id FROM chart_artifacts "
                "WHERE organization_id = :org AND patient_id = :pid "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"org": organization_id, "pid": patient_id},
        ).mappings().first()
        return int(last["id"])


def _audit_rows():
    from app.db import fetch_all
    return fetch_all(
        "SELECT event_type, detail, organization_id, actor_email, path, method "
        "FROM security_audit_events "
        "WHERE event_type = 'pre_visit_brief_generated' "
        "ORDER BY id"
    )


# --- pure-service tests (no HTTP) --------------------------------------


class TestServiceEmpty:
    def test_no_data_brief_status_generated(self, client, seeded_ids):
        # Patient PT-1001 has the seeded encounter only — no scribe,
        # no retinal artifact, no patient summary.
        pid = _patient_id("PT-1001")
        r = _get_route(client, CLIN1, pid)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["brief_status"] == "generated"
        assert body["patient_id"] == pid
        assert isinstance(body["generated_at"], str) and body["generated_at"]
        assert "provider review required" in body["notice"]

    def test_data_gaps_lists_missing_sources(self, client, seeded_ids):
        # PT-2001 in the northside org has no scribe / retinal /
        # summaries (only an encounter). Use the northside admin so
        # the org-scoped lookup matches.
        pid = _patient_id("PT-2001")
        r = _get_route(client, ADMIN2, pid)
        assert r.status_code == 200, r.text
        body = r.json()
        gaps = " ".join(body["data_gaps"]).lower()
        assert "no scribe sessions" in gaps
        assert "no retinal artifacts" in gaps
        assert "no patient-friendly summaries" in gaps

    def test_source_counts_zero_when_only_encounters(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _get_route(client, CLIN1, pid)
        c = r.json()["source_counts"]
        assert c["scribe_sessions"] == 0
        assert c["retinal_artifacts"] == 0
        assert c["patient_summaries"] == 0
        assert c["encounters"] >= 1
        # workflow_events seeded against PT-1001's encounter
        assert c["workflow_events"] >= 1

    def test_cross_org_resolve_raises_404_at_route(self, client, seeded_ids):
        # PT-2001 belongs to northside; chartnav admin sees not_found.
        pid = _patient_id("PT-2001")
        r = _get_route(client, CLIN1, pid)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"


# --- service against richer source data --------------------------------


class TestServiceWithSources:
    def test_includes_recent_encounters_summary(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        body = _get_route(client, CLIN1, pid).json()
        assert body["last_visit_summary"]
        assert "Dr. Carter" in body["last_visit_summary"]

    def test_includes_signed_retinal_artifact(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            title="OD/OS macula drawing",
            signed=True,
        )
        body = _get_route(client, CLIN1, pid).json()
        r = body["retinal_artifact_summary"]
        assert r["total"] == 1
        assert r["signed_count"] == 1
        assert r["unsigned_count"] == 0
        assert r["latest_signed"] is not None
        assert r["latest_signed"]["title"] == "OD/OS macula drawing"
        assert body["source_counts"]["retinal_artifacts_signed"] == 1

    def test_unsigned_retinal_artifact_listed_as_gap(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            title="draft only",
            signed=False,
        )
        body = _get_route(client, CLIN1, pid).json()
        r = body["retinal_artifact_summary"]
        assert r["total"] == 1
        assert r["signed_count"] == 0
        assert r["unsigned_count"] == 1
        assert r["has_unsigned_drafts"] is True
        gaps = " ".join(body["data_gaps"]).lower()
        assert "no signed retinal artifacts" in gaps

    def test_includes_reviewed_scribe_session(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        sess = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        _review_scribe(client, CLIN1, pid, sess["id"])
        body = _get_route(client, CLIN1, pid).json()
        s = body["recent_scribe_session_summary"]
        assert s["session_id"] == sess["id"]
        assert s["status"] in ("reviewed", "finalized")
        # active_issues should pick up the assessment from the
        # processed scribe note.
        assert any("refractive" in i.lower() for i in body["active_issues"])
        assert body["source_counts"]["scribe_sessions"] >= 1
        assert body["source_counts"]["scribe_sessions_finalized"] >= 1

    def test_includes_finalized_patient_summary(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        sess = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        sm = _create_summary(
            client, CLIN1, pid, scribe_session_id=sess["id"]
        ).json()
        _review_summary(client, CLIN1, pid, sm["id"])
        _finalize_summary(client, CLIN1, pid, sm["id"])

        body = _get_route(client, CLIN1, pid).json()
        ctx = body["patient_summary_context"]
        assert ctx["summary_id"] == sm["id"]
        assert ctx["status"] == "finalized"
        assert ctx["source_kind"] == "finalized"
        assert ctx["plain_language_excerpt"]
        assert body["source_counts"]["patient_summaries_finalized"] == 1

    def test_prefers_finalized_summary_over_draft(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        # First summary: stays draft.
        _create_summary(client, CLIN1, pid).json()
        # Second summary: review then finalize.
        sess = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        sm2 = _create_summary(
            client, CLIN1, pid, scribe_session_id=sess["id"]
        ).json()
        _review_summary(client, CLIN1, pid, sm2["id"])
        _finalize_summary(client, CLIN1, pid, sm2["id"])

        body = _get_route(client, CLIN1, pid).json()
        # The brief picked the finalized one even though the draft is
        # the most recently updated.
        assert body["patient_summary_context"]["status"] == "finalized"
        assert body["patient_summary_context"]["summary_id"] == sm2["id"]

    def test_pending_items_list_open_work(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        sess = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        # Leave it ready_for_review.
        _create_summary(client, CLIN1, pid)  # draft

        body = _get_route(client, CLIN1, pid).json()
        kinds = sorted({p["kind"] for p in body["pending_items"]})
        assert "scribe_session" in kinds
        assert "patient_summary" in kinds

    def test_suggested_review_items_only_review_states(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        sess = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, sess["id"])
        # draft summary explicitly awaiting review
        _create_summary(client, CLIN1, pid)
        body = _get_route(client, CLIN1, pid).json()
        reasons = [s["reason"] for s in body["suggested_review_items"]]
        assert any("ready for provider review" in r for r in reasons)
        assert any("draft awaiting review" in r for r in reasons)

    def test_discarded_summary_excluded_from_context(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        sm = _create_summary(client, CLIN1, pid).json()
        client.post(
            f"/patients/{pid}/patient-summaries/{sm['id']}/discard",
            headers=CLIN1,
        )
        body = _get_route(client, CLIN1, pid).json()
        # Discarded != finalized && != reviewed → context falls back
        # to "none".
        assert body["patient_summary_context"]["status"] == "none"
        assert body["patient_summary_context"]["summary_id"] is None
        # And the discarded summary is not surfaced in pending or
        # suggested_review.
        kinds = {p["kind"] for p in body["pending_items"]}
        assert "patient_summary" not in kinds


# --- HTTP routes -------------------------------------------------------


class TestRoutes:
    def test_post_generate_returns_brief_and_audits(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = _generate_route(client, CLIN1, pid)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["brief_status"] == "generated"
        assert body["patient_id"] == pid
        assert "source_counts" in body
        assert "data_gaps" in body
        assert "notice" in body and "provider review required" in body["notice"]
        rows = _audit_rows()
        assert any(
            row["event_type"] == "pre_visit_brief_generated" for row in rows
        )

    def test_get_returns_brief_without_audit(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _get_route(client, CLIN1, pid)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["brief_status"] == "generated"
        # GET is read-only — no pre_visit_brief_generated row.
        rows = _audit_rows()
        assert not rows

    def test_cross_org_returns_404(self, client, seeded_ids):
        # PT-1001 belongs to chartnav; northside admin sees it as
        # not_found rather than getting access denied (no leak).
        pid = _patient_id("PT-1001")
        r = _generate_route(client, ADMIN2, pid)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_unknown_patient_returns_404(self, client, seeded_ids):
        r = _generate_route(client, CLIN1, 9_999_999)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_reviewer_can_get(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _get_route(client, REV1, pid)
        assert r.status_code == 200, r.text

    def test_reviewer_cannot_post(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _generate_route(client, REV1, pid)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_admin_can_post(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _generate_route(client, ADMIN1, pid)
        assert r.status_code == 200, r.text

    def test_no_autonomous_diagnosis_language_in_response(
        self, client, seeded_ids
    ):
        # Even when there are sources, the brief envelope itself never
        # uses autonomous-diagnosis or external-LLM phrasing. We can't
        # control what providers wrote into their own notes, but the
        # service-emitted prose (notice, last_visit_summary,
        # data_gaps, retinal/scribe envelope strings) must be safe.
        pid = _patient_id("PT-1001")
        r = _generate_route(client, CLIN1, pid)
        body = r.json()
        envelope_strings = [
            body.get("notice") or "",
            body.get("last_visit_summary") or "",
            *(body.get("data_gaps") or []),
            *(
                v
                for v in (body.get("retinal_artifact_summary") or {}).values()
                if isinstance(v, str)
            ),
        ]
        env = " | ".join(envelope_strings).lower()
        for forbidden in ("autonomous", "openai", "anthropic", " llm"):
            assert forbidden not in env, env

    def test_response_shape_keys(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _get_route(client, CLIN1, pid)
        body = r.json()
        for key in (
            "patient_id",
            "brief_status",
            "last_visit_summary",
            "active_issues",
            "retinal_artifact_summary",
            "recent_scribe_session_summary",
            "patient_summary_context",
            "pending_items",
            "suggested_review_items",
            "data_gaps",
            "source_counts",
            "generated_at",
            "notice",
        ):
            assert key in body, f"missing key {key!r} in response"


# --- audit redaction ---------------------------------------------------


# Sentinel tokens injected into each section's source-table row. If
# any of these reach the audit log, the redaction guarantee is broken.
SEN_LAST_VISIT = "PHI_LASTVISIT_TOKEN_AAA"  # patient_name on encounter
SEN_ACTIVE = "PHI_ACTIVE_TOKEN_BBB"          # key_findings entry
SEN_RETINAL = "PHI_RETINAL_TOKEN_CCC"        # chart_artifacts.title
SEN_SCRIBE = "PHI_SCRIBE_TOKEN_DDD"          # scribe source_text
SEN_SUMMARY = "PHI_SUMMARY_TOKEN_EEE"        # plain_language_summary
SEN_PENDING = "PHI_PENDING_TOKEN_FFF"        # patient_summary plain text
SEN_SUGGESTED = "PHI_SUGGESTED_TOKEN_GGG"    # scribe review_notes
SEN_GAPS = "PHI_GAPS_TOKEN_HHH"              # gap-trigger marker (n/a; we
#                                               assert the gap-string body
#                                               itself never appears in
#                                               audit detail)


def _seed_full_chart_with_sentinels(client, pid: int, org: int) -> None:
    """Seed a wide swath of chart data with sentinel tokens.

    Spread different tokens across different sections so we can assert
    each one independently against the audit log.
    """
    from app.db import transaction
    from sqlalchemy import text

    # last_visit_summary draws from encounter.patient_name + provider.
    # Patch the seeded encounter's patient_name to include our token.
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE encounters SET patient_name = :pn "
                "WHERE patient_id = :pid AND organization_id = :org"
            ),
            {"pn": f"Morgan Lee {SEN_LAST_VISIT}", "pid": pid, "org": org},
        )

    # scribe session with sentinel in source_text + draft note + plan
    sess = _create_scribe(
        client, CLIN1, pid,
        source_text=(
            f"Chief complaint: blurry vision OD ({SEN_SCRIBE}).\n"
            f"Plan: refraction next visit ({SEN_SUGGESTED})."
        ),
    ).json()
    _process_scribe(client, CLIN1, pid, sess["id"])
    _review_scribe(client, CLIN1, pid, sess["id"])

    # patient summary with sentinel content
    sm = _create_summary(
        client, CLIN1, pid, scribe_session_id=sess["id"]
    ).json()
    client.patch(
        f"/patients/{pid}/patient-summaries/{sm['id']}",
        headers=CLIN1,
        json={
            "plain_language_summary": f"Visit summary: {SEN_SUMMARY}.",
            "key_findings": [f"Active issue: {SEN_ACTIVE}"],
            "next_steps": [f"Pending step: {SEN_PENDING}"],
        },
    )
    _review_summary(client, CLIN1, pid, sm["id"])
    _finalize_summary(client, CLIN1, pid, sm["id"])

    # signed retinal artifact with sentinel in title
    _seed_chart_artifact(
        organization_id=org,
        patient_id=pid,
        title=f"Macula OD/OS — {SEN_RETINAL}",
        signed=True,
    )


class TestAuditRedaction:
    def test_audit_event_emitted_with_metadata_only(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = _generate_route(client, CLIN1, pid)
        assert r.status_code == 200
        rows = _audit_rows()
        assert rows, "no pre_visit_brief_generated row"
        detail = rows[-1]["detail"] or ""
        assert f"patient_id={pid}" in detail
        assert "generated_at=" in detail
        assert "counts[" in detail
        # Counts encoded as key=value tokens, alphabetically sorted.
        assert "scribe_sessions=" in detail
        assert "retinal_artifacts=" in detail

    def test_audit_excludes_last_visit_sentinel(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_LAST_VISIT not in (row["detail"] or "")

    def test_audit_excludes_active_issues_sentinel(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_ACTIVE not in (row["detail"] or "")

    def test_audit_excludes_retinal_sentinel(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_RETINAL not in (row["detail"] or "")

    def test_audit_excludes_scribe_sentinel(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_SCRIBE not in (row["detail"] or "")

    def test_audit_excludes_summary_sentinel(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_SUMMARY not in (row["detail"] or "")

    def test_audit_excludes_pending_items_sentinel(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_PENDING not in (row["detail"] or "")

    def test_audit_excludes_suggested_review_sentinel(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_full_chart_with_sentinels(client, pid, org)
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            assert SEN_SUGGESTED not in (row["detail"] or "")

    def test_audit_excludes_data_gap_strings(self, client, seeded_ids):
        # The brief's gap strings themselves are body content. We
        # assert no characteristic gap phrasing makes it into the
        # audit detail field.
        pid = _patient_id("PT-1001")
        _generate_route(client, CLIN1, pid)
        for row in _audit_rows():
            d = (row["detail"] or "").lower()
            assert "no scribe sessions on file" not in d
            assert "no patient-friendly summaries" not in d
            assert "no retinal artifacts on file" not in d
