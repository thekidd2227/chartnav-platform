"""Clinical Coding Intelligence — ICD-10-CM ingestion service.

Public entrypoints:
    run_sync(version_label=None, triggered_by_user_id=None)  — download,
        parse, and store an official CDC/NCHS release. Idempotent.
        If a version with the same version_label already has
        parse_status='ready', the job short-circuits and returns the
        existing version row.
    list_sync_jobs(limit)  — audit trail for admin UI.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, date
from pathlib import Path

from sqlalchemy import text

from app.db import transaction, fetch_one, fetch_all, insert_returning_id
from app.lib.icd10cm import (
    CDC_NCHS_RELEASE_SOURCES,
    fetch_release,
    parse_order_file,
)
from .specialty import seed_support_rules


# Raw artifact directory lives next to the API package so it is
# easy to inspect during a pilot. Operators can change this via
# env (see README + deployment docs).
import os
RAW_ROOT = Path(
    os.environ.get(
        "CHARTNAV_ICD10CM_RAW_DIR",
        str(Path(__file__).resolve().parents[3] / "data" / "icd10cm" / "raw"),
    )
).resolve()
RAW_ROOT.mkdir(parents=True, exist_ok=True)


def _find_source(version_label: str | None) -> dict:
    """Pick the source to ingest. If no label is given, we pick the
    release whose effective window contains today; otherwise we fall
    back to the newest release in the list."""
    if version_label:
        for s in CDC_NCHS_RELEASE_SOURCES:
            if s["version_label"] == version_label:
                return s
        raise ValueError(f"unknown version_label: {version_label}")
    today = date.today().isoformat()
    # Prefer the release whose [effective_start, effective_end) wraps today.
    for s in CDC_NCHS_RELEASE_SOURCES:
        start = s["effective_start"]
        end = s.get("effective_end") or "9999-12-31"
        if start <= today <= end:
            return s
    # Fallback: newest by effective_start.
    return sorted(CDC_NCHS_RELEASE_SOURCES,
                  key=lambda s: s["effective_start"])[-1]


def _fixture_for(source: dict) -> Path | None:
    """Return the local fixture path for this source if one exists.
    Fixtures live under `tests/fixtures/icd10cm/`."""
    name = source["primary_order_file"]
    candidate = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "icd10cm" / name
    return candidate if candidate.exists() else None


def run_sync(
    version_label: str | None = None,
    *,
    triggered_by_user_id: int | None = None,
    allow_network: bool = True,
) -> dict:
    """Run one full ingestion. Returns a dict describing the result.

    Ingestion sequence:
      1. Record a new coding_sync_jobs row (status=running).
      2. Resolve the source entry (by label or date window).
      3. Call fetch_release → raw artifacts land in RAW_ROOT.
      4. If a matching icd10cm_versions row already has parse_status
         = 'ready' and the same checksum, skip re-parsing and return.
      5. Otherwise, INSERT a new icd10cm_versions row, parse the
         order file, bulk-insert icd10cm_codes + relationships,
         flip parse_status='ready', and seed support rules.
      6. Update coding_sync_jobs with the stats.
    """
    source = _find_source(version_label)
    started_at = datetime.utcnow()

    # Step 1 — audit row
    with transaction() as conn:
        job_id = insert_returning_id(
            conn, "coding_sync_jobs",
            {
                "job_type": "manual" if triggered_by_user_id else "scheduled",
                "status": "running",
                "started_at": started_at,
                "triggered_by_user_id": triggered_by_user_id,
            },
        )

    try:
        # Step 2+3 — fetch (with fixture fallback)
        manifest = fetch_release(
            source,
            raw_root=RAW_ROOT,
            network=allow_network,
            fallback_fixture=_fixture_for(source),
        )

        # Step 4 — idempotency check
        existing = fetch_one(
            "SELECT id, parse_status, checksum_sha256 FROM icd10cm_versions "
            "WHERE version_label = :v",
            {"v": manifest.version_label},
        )
        if existing and existing["parse_status"] == "ready" \
                and existing["checksum_sha256"] == manifest.checksum_sha256:
            _finish_job(
                job_id, status="succeeded",
                files_downloaded=len(manifest.files),
                records_parsed=_count_codes(existing["id"]),
                bytes_downloaded=manifest.bytes_total,
                version_id=existing["id"],
            )
            return {
                "version_id": existing["id"],
                "version_label": manifest.version_label,
                "status": "skipped_already_ready",
                "records_parsed": _count_codes(existing["id"]),
                "raw_dir": str(manifest.raw_dir),
                "checksum_sha256": manifest.checksum_sha256,
                "job_id": job_id,
            }

        # Step 5 — version row (or reuse if we had a stale one)
        if existing:
            with transaction() as conn:
                conn.execute(
                    text(
                        "UPDATE icd10cm_versions SET "
                        "parse_status = 'parsing', "
                        "downloaded_at = :now, "
                        "checksum_sha256 = :cs, "
                        "manifest_json = :mf, "
                        "source_url = :src "
                        "WHERE id = :id"
                    ),
                    {
                        "now": datetime.utcnow(),
                        "cs": manifest.checksum_sha256,
                        "mf": manifest.to_json(),
                        "src": manifest.source_url,
                        "id": existing["id"],
                    },
                )
            version_id = existing["id"]
            # Wipe prior codes for this version before reinserting.
            with transaction() as conn:
                conn.execute(
                    text("DELETE FROM icd10cm_codes WHERE version_id = :v"),
                    {"v": version_id},
                )
                conn.execute(
                    text("DELETE FROM icd10cm_code_relationships WHERE version_id = :v"),
                    {"v": version_id},
                )
        else:
            with transaction() as conn:
                version_id = insert_returning_id(
                    conn, "icd10cm_versions",
                    {
                        "version_label": manifest.version_label,
                        "source_authority": manifest.source_authority,
                        "source_url": manifest.source_url,
                        "release_date": manifest.release_date,
                        "effective_start_date": manifest.effective_start,
                        "effective_end_date": manifest.effective_end,
                        "is_active": 0,
                        "manifest_json": manifest.to_json(),
                        "checksum_sha256": manifest.checksum_sha256,
                        "downloaded_at": datetime.utcnow(),
                        "parse_status": "parsing",
                    },
                )

        # Parse + bulk insert
        parsed = 0
        batch: list[dict] = []
        rel_batch: list[dict] = []
        BATCH_SIZE = 500
        for rec in parse_order_file(str(manifest.primary_order_path)):
            batch.append({
                "version_id": version_id,
                "code": rec.code,
                "normalized_code": rec.normalized_code,
                "is_billable": 1 if rec.is_billable else 0,
                "short_description": rec.short_description,
                "long_description": rec.long_description,
                "chapter_code": rec.chapter_code,
                "chapter_title": rec.chapter_title,
                "category_code": rec.category_code,
                "parent_code": rec.parent_code,
                "specificity_flags": rec.specificity_flags,
                "source_file": rec.source_file,
                "source_line_no": rec.source_line_no,
            })
            if rec.parent_code:
                rel_batch.append({
                    "version_id": version_id,
                    "parent_code": rec.parent_code,
                    "child_code": rec.code,
                    "relationship_type": "parent_child",
                })
            if len(batch) >= BATCH_SIZE:
                _flush_batches(batch, rel_batch)
                parsed += len(batch); batch = []; rel_batch = []
        if batch:
            _flush_batches(batch, rel_batch)
            parsed += len(batch)

        # Flip status + activate (first successful version becomes
        # active automatically; subsequent releases don't displace
        # without explicit admin toggle).
        with transaction() as conn:
            conn.execute(
                text(
                    "UPDATE icd10cm_versions SET "
                    "parse_status = 'ready', "
                    "parsed_at = :now "
                    "WHERE id = :id"
                ),
                {"now": datetime.utcnow(), "id": version_id},
            )
            # Activate if no other version is active.
            active = conn.execute(
                text("SELECT COUNT(*) FROM icd10cm_versions WHERE is_active = 1")
            ).scalar() or 0
            if active == 0:
                conn.execute(
                    text(
                        "UPDATE icd10cm_versions SET "
                        "is_active = 1, activated_at = :now "
                        "WHERE id = :id"
                    ),
                    {"now": datetime.utcnow(), "id": version_id},
                )
            # Seed support rules (idempotent)
            seed_support_rules(conn)

        _finish_job(
            job_id, status="succeeded",
            files_downloaded=len(manifest.files),
            records_parsed=parsed,
            bytes_downloaded=manifest.bytes_total,
            version_id=version_id,
        )
        return {
            "version_id": version_id,
            "version_label": manifest.version_label,
            "status": "ready",
            "records_parsed": parsed,
            "raw_dir": str(manifest.raw_dir),
            "checksum_sha256": manifest.checksum_sha256,
            "job_id": job_id,
        }
    except Exception as e:
        _finish_job(job_id, status="failed", error_log=f"{type(e).__name__}: {e}")
        raise


def _flush_batches(code_batch: list[dict], rel_batch: list[dict]) -> None:
    if not code_batch and not rel_batch:
        return
    with transaction() as conn:
        if code_batch:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO icd10cm_codes "
                    "(version_id, code, normalized_code, is_billable, "
                    "short_description, long_description, chapter_code, "
                    "chapter_title, category_code, parent_code, "
                    "specificity_flags, source_file, source_line_no) "
                    "VALUES (:version_id, :code, :normalized_code, :is_billable, "
                    ":short_description, :long_description, :chapter_code, "
                    ":chapter_title, :category_code, :parent_code, "
                    ":specificity_flags, :source_file, :source_line_no)"
                ),
                code_batch,
            )
        if rel_batch:
            conn.execute(
                text(
                    "INSERT INTO icd10cm_code_relationships "
                    "(version_id, parent_code, child_code, relationship_type) "
                    "VALUES (:version_id, :parent_code, :child_code, :relationship_type)"
                ),
                rel_batch,
            )


def _count_codes(version_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS n FROM icd10cm_codes WHERE version_id = :v",
        {"v": version_id},
    )
    return int(row["n"]) if row else 0


def _finish_job(
    job_id: int, *,
    status: str,
    files_downloaded: int = 0,
    records_parsed: int = 0,
    bytes_downloaded: int = 0,
    version_id: int | None = None,
    error_log: str | None = None,
) -> None:
    with transaction() as conn:
        conn.execute(
            text(
                "UPDATE coding_sync_jobs SET "
                "status = :s, completed_at = :ts, "
                "files_downloaded = :f, records_parsed = :r, "
                "bytes_downloaded = :b, version_id = :v, "
                "error_log = COALESCE(:e, error_log) "
                "WHERE id = :id"
            ),
            {
                "s": status, "ts": datetime.utcnow(),
                "f": files_downloaded, "r": records_parsed,
                "b": bytes_downloaded, "v": version_id,
                "e": error_log, "id": job_id,
            },
        )


def list_sync_jobs(limit: int = 25) -> list[dict]:
    return fetch_all(
        "SELECT id, job_type, status, version_id, started_at, completed_at, "
        "files_downloaded, records_parsed, bytes_downloaded, error_log, "
        "triggered_by_user_id, created_at "
        "FROM coding_sync_jobs ORDER BY id DESC LIMIT :n",
        {"n": limit},
    )
