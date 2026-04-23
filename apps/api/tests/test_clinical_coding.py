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


@pytest.fixture()
def ingested(client, monkeypatch):
    """Run the real ingestion pipeline against the bundled fixture
    file so tests exercise the full code path end-to-end."""
    import app.services.clinical_coding.ingest as ingest
    # Point the ingest service at the test fixture regardless of the
    # source_url in the release table.
    monkeypatch.setattr(
        ingest, "_fixture_for", lambda source: FIXTURE,
    )
    from app.services.clinical_coding import run_sync
    result = run_sync(
        version_label="ICD-10-CM FY2026", allow_network=False,
    )
    assert result["status"] == "ready"
    assert result["records_parsed"] > 30
    return result


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
    again = run_sync(version_label="ICD-10-CM FY2026", allow_network=False)
    assert again["status"] in {"ready", "skipped_already_ready"}
    v = active_version()
    assert v["is_active"] == 1
    assert v["parse_status"] == "ready"


# -------- public routes --------------------------------------------

def test_active_version_route(client, ingested):
    r = client.get("/clinical-coding/version/active", headers=CLIN1)
    assert r.status_code == 200
    body = r.json()
    assert body["version_label"] == "ICD-10-CM FY2026"
    assert body["source_authority"].startswith("CMS")
    assert body["is_active"] == 1


def test_version_by_date(client, ingested):
    r = client.get(
        "/clinical-coding/version/by-date?dateOfService=2026-04-01",
        headers=CLIN1,
    )
    assert r.status_code == 200
    assert r.json()["version_label"] == "ICD-10-CM FY2026"


def test_search_by_description(client, ingested):
    r = client.get(
        "/clinical-coding/search?q=glaucoma&limit=5",
        headers=CLIN1,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["result_count"] > 0
    assert any("glaucoma" in x["long_description"].lower() for x in body["results"])
    assert body["version"]["version_label"] == "ICD-10-CM FY2026"


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
        json={"version_label": "ICD-10-CM FY2026", "allow_network": False},
        headers=CLIN1,
    )
    assert r.status_code == 403


def test_admin_sync_as_admin(client, ingested, monkeypatch):
    import app.services.clinical_coding.ingest as ingest
    monkeypatch.setattr(ingest, "_fixture_for", lambda source: FIXTURE)
    r = client.post(
        "/admin/clinical-coding/sync",
        json={"version_label": "ICD-10-CM FY2026", "allow_network": False},
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
    assert body["active_version"]["version_label"] == "ICD-10-CM FY2026"
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
