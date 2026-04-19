"""Phase 31 — shortcut usage summary admin report.

Thin read over the existing `clinician_shortcut_used` audit stream.
Covers:
- admin sees a ranked rollup for their own org only
- clinician/reviewer → 403 (admin-only route)
- per-ref counts + last_used_at are correct across mixed refs
- cross-org events don't leak into the summary
- out-of-window events don't leak into the summary
- the response envelope shape is stable
- `days` and `limit` query params validate + clamp
- PHI invariant: note_version_id / encounter_id never appear in any
  row of the response
"""

from __future__ import annotations


ADMIN1 = {"X-User-Email": "admin@chartnav.local"}
CLIN1 = {"X-User-Email": "clin@chartnav.local"}
REV1 = {"X-User-Email": "rev@chartnav.local"}
ADMIN2 = {"X-User-Email": "admin@northside.local"}
CLIN2 = {"X-User-Email": "clin@northside.local"}


def _fire_usage(client, headers, shortcut_id: str, note_version_id=None):
    body: dict = {"shortcut_id": shortcut_id}
    if note_version_id is not None:
        body["note_version_id"] = note_version_id
    r = client.post("/me/clinical-shortcuts/used", json=body, headers=headers)
    assert r.status_code == 202, r.text


# ---------------------------------------------------------------------
# Role gate
# ---------------------------------------------------------------------


def test_clinician_cannot_see_usage_summary(client):
    r = client.get("/admin/shortcut-usage-summary", headers=CLIN1)
    assert r.status_code == 403


def test_reviewer_cannot_see_usage_summary(client):
    r = client.get("/admin/shortcut-usage-summary", headers=REV1)
    assert r.status_code == 403


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


def test_admin_sees_ranked_rollup_of_own_org(client):
    # Clinician in org1 fires a few shortcut inserts.
    _fire_usage(client, CLIN1, "pvd-01", note_version_id=10)
    _fire_usage(client, CLIN1, "pvd-01")
    _fire_usage(client, CLIN1, "pvd-01")
    _fire_usage(client, CLIN1, "glc-05")
    _fire_usage(client, CLIN1, "glc-05")
    _fire_usage(client, CLIN1, "cor-03")

    r = client.get("/admin/shortcut-usage-summary", headers=ADMIN1)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["organization_id"] is not None
    assert body["window_days"] == 30
    assert body["total_events"] == 6
    assert body["distinct_refs"] == 3

    items = body["items"]
    # Ranked most-used first; ties broken by ref.
    refs_in_order = [i["shortcut_ref"] for i in items]
    assert refs_in_order[0] == "pvd-01"  # 3 events
    assert refs_in_order[1] == "glc-05"  # 2 events
    assert refs_in_order[2] == "cor-03"  # 1 event

    # Counts correct per ref.
    by_ref = {i["shortcut_ref"]: i for i in items}
    assert by_ref["pvd-01"]["count"] == 3
    assert by_ref["glc-05"]["count"] == 2
    assert by_ref["cor-03"]["count"] == 1

    # Every row carries a last_used_at timestamp.
    for i in items:
        assert i["last_used_at"] and isinstance(i["last_used_at"], str)


# ---------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------


def test_cross_org_events_do_not_leak(client):
    # Org1 doctor fires twice; org2 doctor fires three times.
    _fire_usage(client, CLIN1, "rd-04")
    _fire_usage(client, CLIN1, "rd-04")
    _fire_usage(client, CLIN2, "vasc-01")
    _fire_usage(client, CLIN2, "vasc-01")
    _fire_usage(client, CLIN2, "vasc-01")

    r1 = client.get("/admin/shortcut-usage-summary", headers=ADMIN1).json()
    r2 = client.get("/admin/shortcut-usage-summary", headers=ADMIN2).json()

    refs1 = {i["shortcut_ref"] for i in r1["items"]}
    refs2 = {i["shortcut_ref"] for i in r2["items"]}
    assert "rd-04" in refs1 and "vasc-01" not in refs1
    assert "vasc-01" in refs2 and "rd-04" not in refs2

    # Total events scoped per-org.
    assert r1["total_events"] == 2
    assert r2["total_events"] == 3


# ---------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------


def test_days_query_param_clamps(client):
    r = client.get(
        "/admin/shortcut-usage-summary?days=0", headers=ADMIN1
    )
    assert r.status_code == 422  # ge=1
    r = client.get(
        "/admin/shortcut-usage-summary?days=400", headers=ADMIN1
    )
    assert r.status_code == 422  # le=365
    r = client.get(
        "/admin/shortcut-usage-summary?days=90", headers=ADMIN1
    )
    assert r.status_code == 200
    assert r.json()["window_days"] == 90


def test_limit_caps_the_returned_rows(client):
    # Fire 5 refs.
    for ref in ("pvd-01", "rd-01", "amd-01", "dm-01", "cor-01"):
        _fire_usage(client, CLIN1, ref)
    r = client.get(
        "/admin/shortcut-usage-summary?limit=2", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["distinct_refs"] == 5
    assert len(body["items"]) == 2


# ---------------------------------------------------------------------
# PHI invariant
# ---------------------------------------------------------------------


def test_summary_does_not_leak_note_or_encounter_ids(client):
    _fire_usage(client, CLIN1, "cor-05", note_version_id=999)
    r = client.get("/admin/shortcut-usage-summary", headers=ADMIN1)
    body = r.json()
    # The summary should expose only ref + count + last_used_at.
    for row in body["items"]:
        assert set(row.keys()) == {"shortcut_ref", "count", "last_used_at"}
    # Key-level PHI invariant: check row-serialized text, not the
    # whole envelope (the top-level `generated_at` timestamp can
    # coincidentally contain a "999" in its microseconds suffix).
    flat_rows = str(body["items"])
    assert "note_version_id" not in flat_rows
    assert "encounter_id" not in flat_rows
    assert "999" not in flat_rows


# ---------------------------------------------------------------------
# Quick-comment usage events are NOT conflated into the shortcut summary
# ---------------------------------------------------------------------


def test_quick_comment_events_are_not_rolled_into_shortcut_summary(client):
    # Fire one quick-comment use + one shortcut use.
    r = client.post(
        "/me/quick-comments/used",
        json={"preloaded_ref": "sx-01"},
        headers=CLIN1,
    )
    assert r.status_code == 202
    _fire_usage(client, CLIN1, "pvd-02")

    r = client.get("/admin/shortcut-usage-summary", headers=ADMIN1)
    body = r.json()
    # Only the shortcut event should have landed.
    assert body["total_events"] == 1
    assert body["items"][0]["shortcut_ref"] == "pvd-02"
    # And the preloaded quick-comment ref must not appear.
    refs = {i["shortcut_ref"] for i in body["items"]}
    assert "sx-01" not in refs


# ---------------------------------------------------------------------
# Phase 32 — per-user breakdown
# ---------------------------------------------------------------------


def test_by_user_groups_by_user_email_and_ref(client):
    _fire_usage(client, CLIN1, "glc-01")
    _fire_usage(client, CLIN1, "glc-01")
    _fire_usage(client, CLIN1, "cor-03")
    _fire_usage(client, ADMIN1, "glc-01")

    r = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=ADMIN1
    )
    assert r.status_code == 200
    body = r.json()
    assert body["by_user"] is True
    assert body["total_events"] == 4
    assert body["distinct_refs"] == 2
    assert body["distinct_users"] == 2

    by_key = {
        (i["user_email"], i["shortcut_ref"]): i for i in body["items"]
    }
    assert by_key[("clin@chartnav.local", "glc-01")]["count"] == 2
    assert by_key[("clin@chartnav.local", "cor-03")]["count"] == 1
    assert by_key[("admin@chartnav.local", "glc-01")]["count"] == 1

    # Each row carries a last_used_at.
    for row in body["items"]:
        assert row["last_used_at"]

    # Ranking: highest-count row first; ties broken by (email, ref).
    counts_order = [i["count"] for i in body["items"]]
    assert counts_order == sorted(counts_order, reverse=True)


def test_by_user_stays_org_scoped(client):
    _fire_usage(client, CLIN1, "ocp-01")
    _fire_usage(client, CLIN2, "ocp-01")
    r1 = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=ADMIN1
    ).json()
    r2 = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=ADMIN2
    ).json()
    r1_emails = {i["user_email"] for i in r1["items"]}
    r2_emails = {i["user_email"] for i in r2["items"]}
    assert "clin@chartnav.local" in r1_emails
    assert "clin@northside.local" not in r1_emails
    assert "clin@northside.local" in r2_emails
    assert "clin@chartnav.local" not in r2_emails


def test_by_user_rejects_non_admins(client):
    r = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=CLIN1
    )
    assert r.status_code == 403
    r = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=REV1
    )
    assert r.status_code == 403


def test_by_user_response_does_not_leak_ids(client):
    _fire_usage(client, CLIN1, "ocp-03", note_version_id=77)
    r = client.get(
        "/admin/shortcut-usage-summary?by_user=true", headers=ADMIN1
    )
    body = r.json()
    for row in body["items"]:
        assert set(row.keys()) == {
            "user_email", "shortcut_ref", "count", "last_used_at",
        }
    # Check row-serialized text, not the envelope, so a coincidental
    # microsecond-suffix digit in `generated_at` never flakes the
    # invariant.
    flat_rows = str(body["items"])
    assert "note_version_id" not in flat_rows
    assert "encounter_id" not in flat_rows
    assert "77" not in flat_rows


# ---------------------------------------------------------------------
# Phase 32 — CSV export
# ---------------------------------------------------------------------


def test_csv_export_aggregate_shape(client):
    _fire_usage(client, CLIN1, "glc-02")
    _fire_usage(client, CLIN1, "glc-02")
    _fire_usage(client, CLIN1, "ocp-04")

    r = client.get(
        "/admin/shortcut-usage-summary/export", headers=ADMIN1
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert "chartnav-shortcut-usage-" in r.headers["content-disposition"]
    assert "-by-user" not in r.headers["content-disposition"]

    body = r.text.strip().splitlines()
    # Header + 2 distinct refs.
    assert body[0] == "shortcut_ref,count,last_used_at"
    assert len(body) == 3
    # glc-02 (count 2) ranks above ocp-04 (count 1).
    assert body[1].startswith("glc-02,2,")
    assert body[2].startswith("ocp-04,1,")


def test_csv_export_by_user_shape(client):
    _fire_usage(client, CLIN1, "cor-05")
    _fire_usage(client, CLIN1, "cor-05")
    _fire_usage(client, ADMIN1, "cor-05")

    r = client.get(
        "/admin/shortcut-usage-summary/export?by_user=true",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    assert "-by-user" in r.headers.get("content-disposition", "")

    lines = r.text.strip().splitlines()
    assert lines[0] == "user_email,shortcut_ref,count,last_used_at"
    # Two distinct (email, ref) buckets.
    assert len(lines) == 3
    # Highest count bucket comes first.
    assert lines[1].startswith("clin@chartnav.local,cor-05,2,")
    assert lines[2].startswith("admin@chartnav.local,cor-05,1,")


def test_csv_export_rejects_non_admins(client):
    r = client.get(
        "/admin/shortcut-usage-summary/export", headers=CLIN1
    )
    assert r.status_code == 403
    r = client.get(
        "/admin/shortcut-usage-summary/export", headers=REV1
    )
    assert r.status_code == 403


def test_csv_export_respects_org_and_window(client):
    _fire_usage(client, CLIN1, "ocp-02")
    _fire_usage(client, CLIN2, "ocp-02")

    r = client.get(
        "/admin/shortcut-usage-summary/export", headers=ADMIN1
    )
    # Org1 only sees their own ocp-02 usage.
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("shortcut_ref,count")
    assert lines[1].startswith("ocp-02,1,")
    # Out-of-range window rejected cleanly.
    r = client.get(
        "/admin/shortcut-usage-summary/export?days=0", headers=ADMIN1
    )
    assert r.status_code == 422
