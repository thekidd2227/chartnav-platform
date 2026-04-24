"""Phase 64 — Clinical Coding Intelligence (ICD-10-CM) contract tests.

Drives the ingestion pipeline against the committed fixture so the
test suite runs without network. Then exercises the public + admin
routes to verify versioning, search, code detail, favorites, and
the admin sync trigger + audit surfaces.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import ADMIN1, CLIN1, REV1


FIXTURE = (
    Path(__file__).parent / "fixtures" / "icd10cm" / "icd10cm-order-2026.txt"
)
FIXTURE_APRIL = (
    Path(__file__).parent / "fixtures" / "icd10cm" / "icd10cm-order-2026-april.txt"
)


OCTOBER_LABEL = "ICD-10-CM FY2026 (October 2025)"
APRIL_LABEL = "ICD-10-CM FY2026 (April 2026 Update)"


def _pick_fixture(source):
    # Route each source to the fixture whose filename matches the
    # source's primary_order_file, so the October-vs-April split
    # produces two distinct DB rows.
    name = source["primary_order_file"]
    if "april" in name.lower():
        return FIXTURE_APRIL
    return FIXTURE


@pytest.fixture()
def ingested(client, monkeypatch):
    """Ingest the October FY2026 release against the bundled fixture."""
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(ingest, "_fixture_for", _pick_fixture)
    from app.services.clinical_coding import run_sync
    result = run_sync(version_label=OCTOBER_LABEL, allow_network=False)
    assert result["status"] == "ready"
    assert result["records_parsed"] > 30
    return result


@pytest.fixture()
def ingested_both(client, monkeypatch):
    """Ingest BOTH FY2026 slices (October + April update)."""
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(ingest, "_fixture_for", _pick_fixture)
    from app.services.clinical_coding import run_sync
    first = run_sync(version_label=OCTOBER_LABEL, allow_network=False)
    second = run_sync(version_label=APRIL_LABEL, allow_network=False)
    assert first["status"] == "ready"
    assert second["status"] == "ready"
    return {"october": first, "april": second}


# -------- parser unit sanity ---------------------------------------

def test_parser_extracts_expected_fields():
    from app.lib.icd10cm import parse_order_file, chapter_for_code
    rows = list(parse_order_file(str(FIXTURE)))
    # Pick the billable H40.1110 record (glaucoma RE mild).
    glauc = [r for r in rows if r.code == "H40.1110"]
    assert glauc, "expected H40.1110 in fixture"
    g = glauc[0]
    assert g.is_billable is True
    assert "glaucoma" in g.long_description.lower()
    assert g.chapter_code == "VII"
    assert g.category_code == "H40"
    # chapter_for_code is deterministic and version-independent
    assert chapter_for_code("H40.11") == ("VII", "Diseases of the eye and adnexa")


# -------- ingestion ------------------------------------------------

def test_ingest_sync_idempotent(client, ingested, monkeypatch):
    from app.services.clinical_coding import run_sync, active_version
    # Second call against same fixture should short-circuit.
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(
        ingest, "_fixture_for", lambda source: FIXTURE,
    )
    again = run_sync(version_label=OCTOBER_LABEL, allow_network=False)
    assert again["status"] in {"ready", "skipped_already_ready"}
    v = active_version()
    assert v["is_active"] == 1
    assert v["parse_status"] == "ready"


# -------- public routes --------------------------------------------

def test_active_version_route(client, ingested):
    r = client.get("/clinical-coding/version/active", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["version_label"] == OCTOBER_LABEL
    assert body["source_authority"].startswith("CMS")
    assert body["is_active"] == 1


def test_version_by_date(client, ingested):
    # DOS inside the October FY2026 window resolves cleanly.
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-01-15",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["version_label"] == OCTOBER_LABEL


def test_search_by_description(client, ingested):
    r = client.get(
        "/clinical-coding/search?q=glaucoma&limit=5",
        headers=CLIN1,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["result_count"] > 0
    assert any("glaucoma" in x["long_description"].lower() for x in body["results"])
    assert body["version"]["version_label"] == OCTOBER_LABEL


def test_search_by_code_prefix(client, ingested):
    r = client.get(
        "/clinical-coding/search?q=H40.11&limit=5",
        headers=CLIN1,
    )
    assert r.status_code == 200
    body = r.json()
    for row in body["results"]:
        assert row["normalized_code"].startswith("H4011")


def test_code_detail_includes_support_hints(client, ingested):
    # Search first so we land on a real code
    r = client.get("/clinical-coding/code/H40.1110", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["code"]["code"] == "H40.1110"
    # Support hints come from the ophthalmology_support_rules table;
    # at least the H40.%  claim_support_hint and H40.11% specificity
    # prompt match this code.
    hints = body["code"]["support_hints"]
    assert any(h["workflow_area"] == "specificity_prompt" for h in hints)


def test_code_detail_404_on_unknown(client, ingested):
    r = client.get("/clinical-coding/code/ZZZ.ZZZ", headers=CLIN1)
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "code_not_found"


def test_specialties_route(client, ingested):
    r = client.get("/clinical-coding/specialties", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert {"retina", "glaucoma", "cataract", "cornea", "oculoplastics", "general"} \
        <= set(body["specialties"])


def test_specialty_bundle_codes(client, ingested):
    r = client.get("/clinical-coding/specialty/glaucoma/codes", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["specialty_tag"] == "glaucoma"
    # Pattern H40.11% expands to the billable stage codes we seeded
    # (H40.1110 / H40.1111 / H40.1112 …). The fixture contains three.
    poag = next(b for b in body["bundles"] if "Primary open-angle" in b["label"])
    assert len(poag["codes"]) >= 1


# -------- favorites -----------------------------------------------

def test_favorites_crud(client, ingested):
    r = client.post(
        "/clinical-coding/favorites",
        json={"code": "H40.1110", "specialty_tag": "glaucoma", "is_pinned": True, "bump_usage": True},
        headers=CLIN1,
    )
    assert r.status_code == 201
    fav = r.json()
    assert fav["code"] == "H40.1110"
    assert fav["is_pinned"] == 1
    assert fav["usage_count"] == 1
    # List
    r = client.get("/clinical-coding/favorites", headers=CLIN1)
    assert r.status_code == 200
    assert any(x["id"] == fav["id"] for x in r.json())
    # Bump usage by re-upsert
    r = client.post(
        "/clinical-coding/favorites",
        json={"code": "H40.1110", "bump_usage": True},
        headers=CLIN1,
    )
    assert r.status_code == 201
    # Delete
    r = client.delete(f"/clinical-coding/favorites/{fav['id']}", headers=CLIN1)
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_favorites_reviewer_forbidden(client, ingested):
    r = client.post(
        "/clinical-coding/favorites",
        json={"code": "H40.1110"},
        headers=REV1,
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "role_forbidden"


# -------- admin --------------------------------------------------

def test_admin_sync_requires_admin(client, ingested):
    r = client.post(
        "/admin/clinical-coding/sync",
        json={"version_label": OCTOBER_LABEL, "allow_network": False},
        headers=CLIN1,
    )
    assert r.status_code == 403


def test_admin_sync_as_admin(client, ingested, monkeypatch):
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(ingest, "_fixture_for", lambda source: FIXTURE)
    r = client.post(
        "/admin/clinical-coding/sync",
        json={"version_label": OCTOBER_LABEL, "allow_network": False},
        headers=ADMIN1,
    )
    assert r.status_code == 202
    assert r.json()["status"] in {"ready", "skipped_already_ready"}


def test_admin_sync_status(client, ingested):
    r = client.get(
        "/admin/clinical-coding/sync/status",
        headers=ADMIN1,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["active_version"]["version_label"] == OCTOBER_LABEL
    assert isinstance(body["recent_jobs"], list)
    assert len(body["recent_jobs"]) >= 1


def test_admin_audit_includes_version_and_checksum(client, ingested):
    r = client.get("/admin/clinical-coding/audit", headers=ADMIN1)
    assert r.status_code == 200
    body = r.json()
    assert len(body["versions"]) == 1
    v = body["versions"][0]
    assert v["source_authority"].startswith("CMS") or v["source_authority"].startswith("CDC")
    assert v["checksum_sha256"] and len(v["checksum_sha256"]) == 64
    # Source URL is always present (even when a fixture was the
    # effective source, we keep the documented upstream URL)
    assert v["source_url"].startswith("http")


# ==================================================================
# Effective-date verification (October / April FY2026 split)
# ==================================================================

def test_fy2026_october_release_has_bounded_effective_end(client, ingested_both):
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-02-15",
        headers=CLIN1,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version_label"] == OCTOBER_LABEL
    assert body["effective_start_date"] == "2026-10-01" or body["effective_start_date"] == "2025-10-01"
    # The fix: end is NOT None. It is 2026-03-31.
    assert body["effective_end_date"] == "2026-03-31"


def test_fy2026_april_update_has_bounded_window(client, ingested_both):
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-05-10",
        headers=CLIN1,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version_label"] == APRIL_LABEL
    assert body["effective_start_date"] == "2026-04-01"
    assert body["effective_end_date"] == "2026-09-30"


def test_dos_march_15_resolves_october_release(client, ingested_both):
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-03-15",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["version_label"] == OCTOBER_LABEL


def test_dos_april_15_resolves_april_release(client, ingested_both):
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-04-15",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["version_label"] == APRIL_LABEL


def test_search_uses_the_dos_resolved_version(client, ingested_both):
    """Search should run against the code set valid on the DOS, NOT
    against whichever version happens to be active. The April
    release contains an addendum code that is absent from the October
    release; we use that as the oracle."""
    # April 15 → April release → addendum code is present
    r_april = client.get(
        "/clinical-coding/search?q=H35.8A&dateOfService=2026-04-15",
        headers=CLIN1,
    )
    assert r_april.status_code == 200
    april_body = r_april.json()
    assert april_body["version"]["version_label"] == APRIL_LABEL
    assert any(x["code"].startswith("H35.8A") for x in april_body["results"])

    # March 15 → October release → addendum code is absent
    r_march = client.get(
        "/clinical-coding/search?q=H35.8A&dateOfService=2026-03-15",
        headers=CLIN1,
    )
    assert r_march.status_code == 200
    march_body = r_march.json()
    assert march_body["version"]["version_label"] == OCTOBER_LABEL
    assert march_body["result_count"] == 0


def test_october_release_not_openended_once_april_loaded(client, ingested_both):
    """Once both slices are loaded, the audit surface must show a
    bounded end date on the October release."""
    r = client.get("/admin/clinical-coding/audit", headers=ADMIN1)
    assert r.status_code == 200
    versions = {v["version_label"]: v for v in r.json()["versions"]}
    assert OCTOBER_LABEL in versions
    assert APRIL_LABEL in versions
    oct_v = versions[OCTOBER_LABEL]
    apr_v = versions[APRIL_LABEL]
    assert oct_v["effective_end_date"] == "2026-03-31", (
        f"October release should end 2026-03-31, got {oct_v['effective_end_date']!r}"
    )
    assert apr_v["effective_end_date"] == "2026-09-30"
    # No overlap: October ends before April starts
    assert oct_v["effective_end_date"] < apr_v["effective_start_date"]


def test_legacy_label_migrates_to_october(client, monkeypatch):
    """A pre-correction deployment stored the October release with
    the legacy label 'ICD-10-CM FY2026' and effective_end=None. The
    next sync must rename that row in place and set a bounded end
    date — not create a duplicate."""
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(ingest, "_fixture_for", _pick_fixture)
    from app.services.clinical_coding import run_sync

    # 1. Simulate the legacy state: insert a row with the old label
    #    + open-ended effective_end via the service's current writer.
    import sqlalchemy as _sa
    from app.db import engine, transaction
    with transaction() as conn:
        conn.execute(
            _sa.text(
                "INSERT INTO icd10cm_versions "
                "(version_label, source_authority, source_url, release_date, "
                "effective_start_date, effective_end_date, is_active, "
                "manifest_json, checksum_sha256, downloaded_at, parse_status) "
                "VALUES ('ICD-10-CM FY2026', 'CMS', 'http://legacy/', "
                "'2025-06-20', '2025-10-01', NULL, 1, '[]', "
                "'deadbeef00000000000000000000000000000000000000000000000000000000', "
                "CURRENT_TIMESTAMP, 'ready')"
            )
        )

    # 2. Run sync for the corrected October label. The pre-step should
    #    rename the legacy row and drop the open-ended window.
    result = run_sync(version_label=OCTOBER_LABEL, allow_network=False)
    assert result["status"] in {"ready", "skipped_already_ready"}

    # 3. There must be exactly one row with either label, and it must
    #    carry the corrected window.
    r = client.get("/admin/clinical-coding/audit", headers=ADMIN1)
    assert r.status_code == 200
    labels = [v["version_label"] for v in r.json()["versions"]]
    assert "ICD-10-CM FY2026" not in labels, (
        "legacy label must not survive after sync"
    )
    oct_row = next(
        v for v in r.json()["versions"] if v["version_label"] == OCTOBER_LABEL
    )
    assert oct_row["effective_end_date"] == "2026-03-31"
