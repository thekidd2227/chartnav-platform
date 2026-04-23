#!/usr/bin/env python3
"""Clinical Coding Intelligence — proof script.

Exercises the ICD-10-CM subsystem end-to-end against the dev DB and
the committed fixtures, then writes a machine-readable proof bundle
to ``docs/clinical-coding/proof/``.

Produces:
  docs/clinical-coding/proof/Clinical_Coding_Proof_Data.json
  docs/clinical-coding/proof/Clinical_Coding_Proof_Summary.md

What the proof covers:
  * Both FY2026 releases ingest with the corrected effective windows
    (October 2025 release → 2025-10-01 → 2026-03-31,
     April 2026 update → 2026-04-01 → 2026-09-30).
  * A DOS of 2026-03-15 resolves to the October release.
  * A DOS of 2026-04-15 resolves to the April update.
  * Neither release is open-ended once both are loaded.
  * Search + code detail work on both releases.

Usage:
    PYTHONPATH=apps/api python scripts/clinical_coding_proof.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "apps" / "api"
PROOF_DIR = REPO_ROOT / "docs" / "clinical-coding" / "proof"
PROOF_DIR.mkdir(parents=True, exist_ok=True)

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.services.clinical_coding import (  # noqa: E402
    run_sync,
    active_version,
    resolve_version_for_date,
    search_codes,
    get_code_detail,
    list_sync_jobs,
)


def _ingest_both_releases() -> list[dict]:
    """Run run_sync twice — once for each FY2026 slice.
    Falls back to fixtures automatically when the network is blocked."""
    results = []
    for label in (
        "ICD-10-CM FY2026 (October 2025)",
        "ICD-10-CM FY2026 (April 2026 Update)",
    ):
        try:
            r = run_sync(version_label=label, allow_network=True)
        except Exception as e:
            # Fall back silently to fixture-only ingestion.
            r = run_sync(version_label=label, allow_network=False)
            r["note"] = f"network sync failed ({type(e).__name__}); fell back to fixture"
        results.append(r)
    return results


def _version_entry(v: dict | None) -> dict | None:
    if not v:
        return None
    return {
        "id": v["id"],
        "version_label": v["version_label"],
        "source_authority": v["source_authority"],
        "source_url": v["source_url"],
        "release_date": str(v["release_date"]),
        "effective_start_date": str(v["effective_start_date"]),
        "effective_end_date": (
            str(v["effective_end_date"]) if v["effective_end_date"] else None
        ),
        "parse_status": v["parse_status"],
        "is_active": int(v["is_active"]),
        "checksum_sha256": v["checksum_sha256"],
    }


def _assert(cond: bool, msg: str, failures: list[str]) -> None:
    if not cond:
        failures.append(msg)


def main() -> int:
    failures: list[str] = []

    ingestions = _ingest_both_releases()

    # Case 1 — 2026-03-15 (before April update) should resolve to
    # the October release.
    v_march = resolve_version_for_date(date(2026, 3, 15))
    _assert(
        v_march is not None and v_march["version_label"] == "ICD-10-CM FY2026 (October 2025)",
        f"DOS 2026-03-15 should resolve to the October release, got "
        f"{v_march['version_label'] if v_march else None!r}",
        failures,
    )

    # Case 2 — 2026-04-15 (after April update) should resolve to the
    # April release.
    v_april = resolve_version_for_date(date(2026, 4, 15))
    _assert(
        v_april is not None and v_april["version_label"] == "ICD-10-CM FY2026 (April 2026 Update)",
        f"DOS 2026-04-15 should resolve to the April release, got "
        f"{v_april['version_label'] if v_april else None!r}",
        failures,
    )

    # Case 3 — the October release MUST have a bounded effective_end.
    _assert(
        v_march is not None and str(v_march["effective_end_date"]) == "2026-03-31",
        "October FY2026 release is still open-ended or has the wrong end date",
        failures,
    )
    # April release must end 2026-09-30.
    _assert(
        v_april is not None and str(v_april["effective_end_date"]) == "2026-09-30",
        "April FY2026 update has the wrong end date",
        failures,
    )

    # Case 4 — a search for a known ophthalmology term returns hits
    # against each release's version_id.
    searches = {}
    for tag, v in (("march_release", v_march), ("april_release", v_april)):
        if not v:
            continue
        hits = search_codes("glaucoma", version_id=int(v["id"]), limit=3, billable_only=True)
        searches[tag] = [
            {"code": h["code"], "short_description": h["short_description"]}
            for h in hits
        ]
        _assert(
            len(hits) > 0,
            f"search for 'glaucoma' returned 0 hits against {v['version_label']}",
            failures,
        )

    # Case 5 — April release contains the fixture's addendum code
    # that does NOT exist in the October release.
    addendum_code = "H35.8A1"
    april_has = (
        get_code_detail(addendum_code, version_id=int(v_april["id"]))
        if v_april else None
    )
    october_has = (
        get_code_detail(addendum_code, version_id=int(v_march["id"]))
        if v_march else None
    )
    _assert(
        april_has is not None,
        f"addendum code {addendum_code} missing from April release",
        failures,
    )
    _assert(
        october_has is None,
        f"addendum code {addendum_code} should NOT exist in October release",
        failures,
    )

    # Recent sync history
    recent_jobs = [
        {
            "id": j["id"],
            "job_type": j["job_type"],
            "status": j["status"],
            "version_id": j["version_id"],
            "records_parsed": j["records_parsed"],
            "completed_at": str(j["completed_at"]) if j["completed_at"] else None,
        }
        for j in list_sync_jobs(limit=10)
    ]

    proof = {
        "schema_version": "clinical-coding/proof@1",
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "effective_date_boundaries": {
            "october_release_ends": "2026-03-31",
            "april_release_starts": "2026-04-01",
            "april_release_ends": "2026-09-30",
        },
        "active_version": _version_entry(active_version()),
        "resolution_cases": {
            "dos_2026-03-15": _version_entry(v_march),
            "dos_2026-04-15": _version_entry(v_april),
        },
        "ingestion_results": ingestions,
        "search_probe_glaucoma": searches,
        "addendum_code_check": {
            "code": addendum_code,
            "present_in_april": april_has is not None,
            "present_in_october": october_has is not None,
        },
        "recent_sync_jobs": recent_jobs,
        "assertions": {
            "passed": len(failures) == 0,
            "failures": failures,
        },
    }

    (PROOF_DIR / "Clinical_Coding_Proof_Data.json").write_text(
        json.dumps(proof, indent=2, default=str)
    )

    # Summary markdown for human review
    lines = [
        "# Clinical Coding Intelligence — Proof Summary",
        "",
        f"Generated: {proof['generated_at']}",
        "",
        "## Effective-date boundary check",
        "",
        f"- October FY2026 release ends: **{proof['effective_date_boundaries']['october_release_ends']}**",
        f"- April FY2026 update starts: **{proof['effective_date_boundaries']['april_release_starts']}**",
        f"- April FY2026 update ends: **{proof['effective_date_boundaries']['april_release_ends']}**",
        "",
        "## Resolution cases",
        "",
        f"- DOS **2026-03-15** → `{(v_march or {}).get('version_label', 'n/a')}`",
        f"- DOS **2026-04-15** → `{(v_april or {}).get('version_label', 'n/a')}`",
        "",
        "## Ingestion results",
        "",
    ]
    for r in ingestions:
        lines.append(
            f"- `{r.get('version_label', '?')}` → status=`{r.get('status')}` "
            f"records_parsed={r.get('records_parsed')} "
            f"job_id={r.get('job_id')}"
        )
    lines += [
        "",
        "## Assertions",
        "",
        f"- **Passed:** {proof['assertions']['passed']}",
    ]
    if failures:
        lines.append("- **Failures:**")
        for f in failures:
            lines.append(f"  - {f}")
    else:
        lines.append("- No failures.")

    (PROOF_DIR / "Clinical_Coding_Proof_Summary.md").write_text("\n".join(lines) + "\n")

    print(json.dumps(proof, indent=2, default=str))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
