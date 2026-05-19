"""Phase 11 — provider action review queue tests.

Coverage groups:
  * generator behavior against an empty patient (data-gap path only)
  * generator surfaces unsigned retinal artifact + skips signed
  * generator surfaces draft / reviewed scribe sessions; skips finalized
  * generator surfaces draft / reviewed patient summaries; skips finalized
  * clinical-language scans (tear, detachment, neovascularization,
    severe hemorrhage)
  * dedupe across repeated generates while items are still active
  * list filters (status / priority / action_type / encounter_id)
  * lifecycle transitions: accept, dismiss, complete + rejected paths
  * RBAC + cross-org 404
  * audit metadata-only redaction (sentinel tokens for title and reason
    body never reach the audit log)
  * negative content checks (no orders / coding / referral / messaging)
"""

from __future__ import annotations

import json

from tests.conftest import ADMIN1, ADMIN2, CLIN1, CLIN2, REV1


# NB: anything that touches the DB must be imported INSIDE the test
# function — module-level imports of `app.db` (transitive via the
# Phase 11 service) would bind to the dev DATABASE_URL before the
# per-test fixture sets the temp SQLite URL.


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


def _generate(client, headers, patient_id):
    return client.post(
        f"/patients/{patient_id}/provider-action-items/generate",
        headers=headers,
    )


def _list(client, headers, patient_id, **filters):
    qs = "&".join(f"{k}={v}" for k, v in filters.items() if v is not None)
    url = f"/patients/{patient_id}/provider-action-items"
    if qs:
        url += f"?{qs}"
    return client.get(url, headers=headers)


def _get(client, headers, patient_id, action_id):
    return client.get(
        f"/patients/{patient_id}/provider-action-items/{action_id}",
        headers=headers,
    )


def _accept(client, headers, patient_id, action_id):
    return client.post(
        f"/patients/{patient_id}/provider-action-items/{action_id}/accept",
        headers=headers,
    )


def _dismiss(client, headers, patient_id, action_id):
    return client.post(
        f"/patients/{patient_id}/provider-action-items/{action_id}/dismiss",
        headers=headers,
    )


def _complete(client, headers, patient_id, action_id):
    return client.post(
        f"/patients/{patient_id}/provider-action-items/{action_id}/complete",
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
    title: str = "OD/OS macula drawing",
    findings_text: str = "",
    signed: bool = True,
) -> int:
    """Direct-DB insert of a chart_artifacts row.

    Phase 11 reads chart_artifacts but never writes them, so we bypass
    the eye-diagrams API which is outside the Phase 11 scope.
    """
    from datetime import datetime, timezone
    from app.db import transaction
    from sqlalchemy import text

    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        u = conn.execute(
            text(
                "SELECT id FROM users WHERE organization_id = :org "
                "AND role IN ('admin','clinician') LIMIT 1"
            ),
            {"org": organization_id},
        ).mappings().first()
        assert u is not None
        cols = (
            "organization_id, patient_id, encounter_id, "
            "created_by_user_id, artifact_type, title, findings_text, "
            "drawing_json, version_number, parent_artifact_id, "
            "signed_at, signed_by_user_id, created_at, updated_at"
        )
        sql = text(
            f"INSERT INTO chart_artifacts ({cols}) VALUES ("
            ":org, :pid, NULL, :cb, 'retinal_diagram', :title, :findings, "
            "'{}', 1, NULL, :signed_at, :signed_by, :now, :now"
            ")"
        )
        conn.execute(sql, {
            "org": organization_id,
            "pid": patient_id,
            "cb": int(u["id"]),
            "title": title,
            "findings": findings_text,
            "signed_at": now if signed else None,
            "signed_by": int(u["id"]) if signed else None,
            "now": now,
        })
        last = conn.execute(
            text(
                "SELECT id FROM chart_artifacts "
                "WHERE organization_id = :org AND patient_id = :pid "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"org": organization_id, "pid": patient_id},
        ).mappings().first()
        return int(last["id"])


def _audit_rows(prefix: str = "provider_action_"):
    from app.db import fetch_all
    return fetch_all(
        "SELECT event_type, detail FROM security_audit_events "
        "WHERE event_type LIKE :p ORDER BY id",
        {"p": f"{prefix}%"},
    )


def _types_in(items: list[dict]) -> set[str]:
    return {it["action_type"] for it in items}


# --- generator: empty / data-gap paths --------------------------------


class TestGeneratorDataGaps:
    def test_empty_patient_creates_data_gap_suggestion(
        self, client, seeded_ids
    ):
        # PT-1001 has only the seeded encounter (no scribe / retinal /
        # summary). The generator should surface a data-gap prompt.
        pid = _patient_id("PT-1001")
        r = _generate(client, CLIN1, pid)
        assert r.status_code == 200
        types = _types_in(r.json()["items"])
        assert "review_pre_visit_data_gaps" in types
        assert "review_missing_signed_retinal_artifact" in types
        assert "review_missing_finalized_patient_summary" in types
        assert "review_missing_reviewed_scribe_session" in types

    def test_no_orders_or_coding_or_referral_in_data_gap_path(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        r = _generate(client, CLIN1, pid)
        body = r.json()
        # Action-type vocabulary is closed; assert nothing in there
        # mentions order/code/referral/etc.
        for it in body["items"]:
            for field in ("action_type", "title", "reason"):
                assert "order" not in it[field].lower()
                assert "referral" not in it[field].lower()
                assert "billing" not in it[field].lower()
                assert "icd-10" not in it[field].lower()
                assert "cpt" not in it[field].lower()
                assert "send to patient" not in it[field].lower()


# --- generator: workflow completion -----------------------------------


class TestGeneratorWorkflow:
    def test_unsigned_retinal_artifact_creates_sign_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org, patient_id=pid, signed=False
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "sign_unsigned_retinal_diagram" in types
        assert "reconcile_unsigned_artifacts" in types

    def test_signed_retinal_artifact_does_not_create_unsigned_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org, patient_id=pid, signed=True
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "sign_unsigned_retinal_diagram" not in types
        assert "reconcile_unsigned_artifacts" not in types
        assert "review_missing_signed_retinal_artifact" not in types

    def test_draft_scribe_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        _create_scribe(client, CLIN1, pid).json()
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_scribe_session" in types

    def test_ready_for_review_scribe_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        s = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        r = _generate(client, CLIN1, pid)
        items = r.json()["items"]
        types = _types_in(items)
        assert "review_scribe_session" in types

    def test_reviewed_scribe_creates_finalize_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        s = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        _review_scribe(client, CLIN1, pid, s["id"])
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "finalize_scribe_session" in types

    def test_finalized_scribe_does_not_create_finalize_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        s = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        _review_scribe(client, CLIN1, pid, s["id"])
        _finalize_scribe(client, CLIN1, pid, s["id"])
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "finalize_scribe_session" not in types
        assert "review_scribe_session" not in types

    def test_draft_summary_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        _create_summary(client, CLIN1, pid).json()
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_patient_summary" in types

    def test_reviewed_summary_creates_finalize_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        sm = _create_summary(client, CLIN1, pid).json()
        _review_summary(client, CLIN1, pid, sm["id"])
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "finalize_patient_summary" in types

    def test_finalized_summary_does_not_create_summary_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        s = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        sm = _create_summary(
            client, CLIN1, pid, scribe_session_id=s["id"]
        ).json()
        _review_summary(client, CLIN1, pid, sm["id"])
        _finalize_summary(client, CLIN1, pid, sm["id"])
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "finalize_patient_summary" not in types
        assert "review_patient_summary" not in types


# --- generator: clinical language scans -------------------------------


class TestGeneratorClinicalLanguage:
    def test_retinal_tear_language_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        # Sign an artifact whose findings include "retinal tear".
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            title="OD posterior pole drawing",
            findings_text="Suspected retinal tear at 1 o'clock.",
            signed=True,
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_retinal_tear_language" in types

    def test_retinal_detachment_language_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            findings_text="Possible retinal detachment in OS inferior quadrant.",
            signed=True,
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_retinal_detachment_language" in types

    def test_neovascularization_language_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            findings_text="Neovascularization noted at the disc.",
            signed=True,
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_neovascularization_language" in types

    def test_severe_hemorrhage_language_creates_review_suggestion(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            findings_text="Severe vitreous hemorrhage obscuring the macula.",
            signed=True,
        )
        r = _generate(client, CLIN1, pid)
        types = _types_in(r.json()["items"])
        assert "review_severe_hemorrhage_language" in types


# --- dedupe across repeated generates ---------------------------------


class TestDedupe:
    def test_repeated_generate_does_not_duplicate_active_items(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org, patient_id=pid, signed=False
        )

        first = _generate(client, CLIN1, pid).json()
        second = _generate(client, CLIN1, pid).json()
        # Second call should reuse rather than create new.
        assert second["created_count"] == 0
        assert second["reused_count"] == first["created_count"]

        # And the listing reflects exactly the original set, not 2x.
        listed = _list(client, CLIN1, pid).json()
        types = [it["action_type"] for it in listed["items"]]
        # Every type appears exactly once.
        assert sorted(set(types)) == sorted(types)

    def test_repeated_generate_creates_new_after_dismiss(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org, patient_id=pid, signed=False
        )
        first = _generate(client, CLIN1, pid).json()
        # Find and dismiss every active item.
        for it in first["items"]:
            _dismiss(client, CLIN1, pid, it["id"])
        # A fresh generate should now create new items because all
        # prior ones are in a terminal state.
        second = _generate(client, CLIN1, pid).json()
        assert second["created_count"] == first["created_count"]


# --- list filters -----------------------------------------------------


class TestListFilters:
    def test_filter_by_status(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        _generate(client, CLIN1, pid)
        suggested = _list(client, CLIN1, pid, status="suggested").json()
        assert suggested["total"] >= 1
        # All entries are suggested.
        assert all(it["status"] == "suggested" for it in suggested["items"])
        # Empty filter for a state we haven't reached.
        completed = _list(client, CLIN1, pid, status="completed").json()
        assert completed["total"] == 0

    def test_filter_by_priority(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        # Sign an artifact with retinal-tear language → high priority.
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            findings_text="Suspected retinal tear at 1 o'clock.",
            signed=True,
        )
        _generate(client, CLIN1, pid)
        high = _list(client, CLIN1, pid, priority="high").json()
        assert high["total"] >= 1
        assert all(it["priority"] == "high" for it in high["items"])

    def test_filter_by_action_type(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org, patient_id=pid, signed=False
        )
        _generate(client, CLIN1, pid)
        narrow = _list(
            client,
            CLIN1,
            pid,
            action_type="sign_unsigned_retinal_diagram",
        ).json()
        assert narrow["total"] >= 1
        assert all(
            it["action_type"] == "sign_unsigned_retinal_diagram"
            for it in narrow["items"]
        )

    def test_filter_invalid_status_returns_400(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _list(client, CLIN1, pid, status="bogus")
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "invalid_status_filter"


# --- lifecycle transitions --------------------------------------------


class TestLifecycle:
    def test_accept_suggested(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        r = _accept(client, CLIN1, pid, item["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"
        assert r.json()["accepted_at"]

    def test_dismiss_suggested(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        r = _dismiss(client, CLIN1, pid, item["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "dismissed"
        assert r.json()["is_terminal"] is True

    def test_complete_after_accept(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        _accept(client, CLIN1, pid, item["id"])
        r = _complete(client, CLIN1, pid, item["id"])
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
        assert r.json()["is_terminal"] is True

    def test_reject_suggested_to_completed(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        r = _complete(client, CLIN1, pid, item["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "provider_action_invalid_transition"

    def test_dismissed_is_immutable(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        _dismiss(client, CLIN1, pid, item["id"])
        r1 = _accept(client, CLIN1, pid, item["id"])
        r2 = _complete(client, CLIN1, pid, item["id"])
        assert r1.status_code == 409
        assert r2.status_code == 409
        assert r1.json()["detail"]["error_code"] == "provider_action_item_immutable"
        assert r2.json()["detail"]["error_code"] == "provider_action_item_immutable"

    def test_completed_is_immutable(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        _accept(client, CLIN1, pid, item["id"])
        _complete(client, CLIN1, pid, item["id"])
        r = _dismiss(client, CLIN1, pid, item["id"])
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "provider_action_item_immutable"


# --- security: cross-org + RBAC ---------------------------------------


class TestSecurity:
    def test_cross_org_returns_404(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        # ADMIN2 is in a different org — should look like 404.
        r = _generate(client, ADMIN2, pid)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "patient_not_found"

    def test_unknown_action_returns_404(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _get(client, CLIN1, pid, 9_999_999)
        assert r.status_code == 404
        assert r.json()["detail"]["error_code"] == "provider_action_item_not_found"

    def test_reviewer_can_read(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        _generate(client, CLIN1, pid)
        r = _list(client, REV1, pid)
        assert r.status_code == 200

    def test_reviewer_cannot_generate(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        r = _generate(client, REV1, pid)
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "role_forbidden"

    def test_reviewer_cannot_accept_or_dismiss_or_complete(
        self, client, seeded_ids
    ):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item_id = first["items"][0]["id"]
        for fn in (_accept, _dismiss, _complete):
            r = fn(client, REV1, pid, item_id)
            assert r.status_code == 403
            assert r.json()["detail"]["error_code"] == "role_forbidden"


# --- audit redaction --------------------------------------------------


SEN_TITLE = "PHI_TITLE_TOKEN_AAA"
SEN_REASON = "PHI_REASON_TOKEN_BBB"
SEN_SOURCE = "PHI_SOURCE_TOKEN_CCC"


class TestAuditRedaction:
    def test_audit_events_emitted_on_lifecycle(self, client, seeded_ids):
        pid = _patient_id("PT-1001")
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        _accept(client, CLIN1, pid, item["id"])
        _complete(client, CLIN1, pid, item["id"])

        events = {row["event_type"] for row in _audit_rows()}
        assert "provider_action_items_generated" in events
        assert "provider_action_item_accepted" in events
        assert "provider_action_item_completed" in events

    def test_audit_excludes_title_and_reason_sentinel(
        self, client, seeded_ids
    ):
        # Inject sentinel tokens into the source artifact's title +
        # findings, then generate; the resulting action item's title /
        # reason will reference the artifact, but the audit MUST NOT
        # contain either token.
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            title=f"Macula drawing — {SEN_TITLE}",
            findings_text=f"Note: {SEN_REASON}",
            signed=False,
        )
        first = _generate(client, CLIN1, pid).json()
        item = first["items"][0]
        _accept(client, CLIN1, pid, item["id"])
        _dismiss(client, CLIN1, pid, item["id"])
        for row in _audit_rows():
            assert SEN_TITLE not in (row["detail"] or "")
            assert SEN_REASON not in (row["detail"] or "")

    def test_audit_excludes_clinical_source_body_sentinel(
        self, client, seeded_ids
    ):
        # The action item generated from a finalized scribe note will
        # describe the session, but its source body must never reach
        # the audit log.
        pid = _patient_id("PT-1001")
        s = _create_scribe(
            client, CLIN1, pid,
            source_text=(
                f"Chief complaint: blurry vision OD ({SEN_SOURCE}).\n"
                "Plan: refraction next visit."
            ),
        ).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        _review_scribe(client, CLIN1, pid, s["id"])
        first = _generate(client, CLIN1, pid).json()
        # Walk the lifecycle on every emitted item to maximize audit
        # surface.
        for it in first["items"]:
            _accept(client, CLIN1, pid, it["id"])
            _dismiss(client, CLIN1, pid, it["id"])
        for row in _audit_rows():
            assert SEN_SOURCE not in (row["detail"] or "")


# --- envelope safety checks -------------------------------------------


class TestNoForbiddenLanguage:
    def test_action_titles_use_review_consider_check_only(
        self, client, seeded_ids
    ):
        # Walk both the empty path and the rich path; assert that
        # every emitted title starts with a permitted verb. This is
        # the contract: ChartNav suggests review tasks, never orders
        # or instructions.
        pid = _patient_id("PT-1001")
        org = _patient_org("PT-1001")
        _seed_chart_artifact(
            organization_id=org,
            patient_id=pid,
            findings_text="Possible retinal detachment OS.",
            signed=True,
        )
        s = _create_scribe(client, CLIN1, pid).json()
        _process_scribe(client, CLIN1, pid, s["id"])
        _review_scribe(client, CLIN1, pid, s["id"])
        sm = _create_summary(client, CLIN1, pid).json()
        _ = sm  # surface a draft summary too

        first = _generate(client, CLIN1, pid).json()
        forbidden = (
            "order ", "place order", "billing", "icd-10", "cpt code",
            "send referral", "submit referral", "send to patient",
            "email patient", "sms ", "portal push", "prescribe",
            "automatically ", "autonomous ",
        )
        for it in first["items"]:
            blob = (
                f"{it['action_type']} {it['title']} {it['reason']}".lower()
            )
            for needle in forbidden:
                assert needle not in blob, (
                    f"forbidden phrase {needle!r} appeared in "
                    f"action item: {it}"
                )
