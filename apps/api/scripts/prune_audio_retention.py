"""Phase 25A / GH-003 — audio retention pruner.

Background
----------
ChartNav persists doctor audio uploads under
``settings.audio_upload_dir`` so the ingestion worker can re-read the
bytes for retry / forensic replay. The blob is referenced by the
``source_metadata.storage_ref`` JSON on the matching
``encounter_inputs`` row. A clinic that has finished using a recording
(transcript generated, draft signed, encounter closed) typically wants
the bytes deleted after N days — both to limit storage and to limit
the blast radius of any future incident.

This script implements that retention policy. It is intentionally
**operator-driven**: there is no daemon, no cron, no embedded
scheduler. Ops triggers it from their own scheduler (cron, k8s
CronJob, etc.) and reviews the report.

Modes
-----
- ``--dry-run`` (default): scan only. Reports what *would* be
  deleted but writes nothing and does not touch any file. Safe to
  run on production.
- ``--delete``: scan + delete the matching audio files, clear the
  ``source_metadata.storage_ref`` value, and emit an
  ``audio_retention_pruned`` security audit event per encounter
  input. The ``encounter_inputs`` row itself is preserved so the
  transcript + audit trail remain intact.

Eligibility
-----------
A row is eligible when:
- ``input_type = 'audio_upload'``
- ``finished_at`` is non-NULL AND older than ``--days`` ago
- ``source_metadata.storage_ref`` (or ``source_metadata.stored_path``)
  points to an existing file we can actually delete

PHI / audit policy
------------------
- The script never reads, transcribes, or copies audio bytes — it
  just unlinks the file.
- The audit row carries the encounter_input_id, encounter_id,
  organization_id, and a ``deleted_size_bytes`` metric. Filename and
  storage uri are **NOT** persisted into the audit detail (storage
  paths can be sensitive in some deployments).

Usage
-----
    python -m scripts.prune_audio_retention --days 30 --dry-run
    python -m scripts.prune_audio_retention --days 30 --delete
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


@dataclasses.dataclass
class PruneCandidate:
    input_id: int
    encounter_id: int
    organization_id: int
    finished_at: str
    storage_uri: Optional[str]
    size_on_disk: int  # 0 when missing / unreadable


@dataclasses.dataclass
class PruneReport:
    scanned: int
    eligible: int
    deleted: int
    bytes_freed: int
    missing_files: int
    errors: list[str]
    candidates: list[PruneCandidate]

    def to_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "eligible": self.eligible,
            "deleted": self.deleted,
            "bytes_freed": self.bytes_freed,
            "missing_files": self.missing_files,
            "errors": list(self.errors),
            "candidates": [dataclasses.asdict(c) for c in self.candidates],
        }


def _parse_finished_at(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(str(value).split(".")[0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_local_path(source_metadata_json: Optional[str]) -> Optional[str]:
    """Return the on-disk path encoded in source_metadata.
    Falls back from `storage_ref.uri` to legacy `stored_path`."""
    if not source_metadata_json:
        return None
    try:
        md = json.loads(source_metadata_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(md, dict):
        return None
    ref = md.get("storage_ref")
    if isinstance(ref, dict) and ref.get("scheme") == "file":
        uri = ref.get("uri")
        if isinstance(uri, str) and uri:
            return uri
    legacy = md.get("stored_path")
    if isinstance(legacy, str) and legacy:
        return legacy
    return None


def collect_candidates(*, cutoff: datetime) -> list[PruneCandidate]:
    """Scan ``encounter_inputs`` for completed audio uploads older
    than ``cutoff``. Read-only; never mutates rows."""
    from sqlalchemy import text
    from app.db import transaction

    out: list[PruneCandidate] = []
    with transaction() as conn:
        rows = conn.execute(
            text(
                "SELECT ei.id AS input_id, "
                "       ei.encounter_id AS encounter_id, "
                "       e.organization_id AS organization_id, "
                "       ei.finished_at AS finished_at, "
                "       ei.source_metadata AS source_metadata "
                "FROM encounter_inputs ei "
                "JOIN encounters e ON e.id = ei.encounter_id "
                "WHERE ei.input_type = 'audio_upload' "
                "  AND ei.finished_at IS NOT NULL"
            )
        ).mappings().all()

    for row in rows:
        finished = _parse_finished_at(row["finished_at"])
        if finished is None or finished > cutoff:
            continue
        uri = _extract_local_path(row["source_metadata"])
        size = 0
        if uri:
            try:
                size = Path(uri).stat().st_size
            except OSError:
                size = 0
        out.append(
            PruneCandidate(
                input_id=int(row["input_id"]),
                encounter_id=int(row["encounter_id"]),
                organization_id=int(row["organization_id"]),
                finished_at=str(row["finished_at"]),
                storage_uri=uri,
                size_on_disk=size,
            )
        )
    return out


def _clear_storage_ref_on_row(input_id: int) -> None:
    """After deleting the on-disk blob, null out
    `source_metadata.storage_ref` and `stored_path` so future readers
    don't try to re-open a non-existent file. Preserve every other
    metadata field."""
    from sqlalchemy import text
    from app.db import transaction

    with transaction() as conn:
        row = conn.execute(
            text("SELECT source_metadata FROM encounter_inputs WHERE id = :id"),
            {"id": input_id},
        ).mappings().first()
        if row is None:
            return
        raw = row["source_metadata"]
        try:
            md = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            md = {}
        if not isinstance(md, dict):
            md = {}
        md.pop("storage_ref", None)
        md.pop("stored_path", None)
        md["retention_pruned_at"] = datetime.now(timezone.utc).isoformat()
        conn.execute(
            text(
                "UPDATE encounter_inputs SET source_metadata = :md "
                "WHERE id = :id"
            ),
            {"md": json.dumps(md), "id": input_id},
        )


def _emit_audit(*, candidate: PruneCandidate, deleted_bytes: int) -> None:
    from app.audit import record

    record(
        event_type="audio_retention_pruned",
        request_id=None,
        actor_email="system:prune_audio_retention",
        actor_user_id=None,
        organization_id=candidate.organization_id,
        path=f"/encounter-inputs/{candidate.input_id}/audio-blob",
        method="DELETE",
        error_code=None,
        # Detail intentionally carries only metadata-grade numbers.
        # Storage uris can be sensitive depending on backend.
        detail=(
            f"encounter_input_id={candidate.input_id} "
            f"encounter_id={candidate.encounter_id} "
            f"deleted_bytes={deleted_bytes}"
        ),
        remote_addr=None,
    )


def run(*, days: int, do_delete: bool) -> PruneReport:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    candidates = collect_candidates(cutoff=cutoff)

    eligible = sum(1 for c in candidates if c.storage_uri and c.size_on_disk > 0)
    deleted = 0
    bytes_freed = 0
    missing = sum(1 for c in candidates if c.storage_uri and c.size_on_disk == 0)
    errors: list[str] = []

    if not do_delete:
        return PruneReport(
            scanned=len(candidates),
            eligible=eligible,
            deleted=0,
            bytes_freed=0,
            missing_files=missing,
            errors=errors,
            candidates=candidates,
        )

    for cand in candidates:
        if not cand.storage_uri or cand.size_on_disk <= 0:
            continue
        path = Path(cand.storage_uri)
        try:
            path.unlink()
        except OSError as e:
            errors.append(f"input_id={cand.input_id} unlink failed: {e}")
            continue
        deleted += 1
        bytes_freed += cand.size_on_disk
        try:
            _clear_storage_ref_on_row(cand.input_id)
        except Exception as e:  # pragma: no cover — defensive
            errors.append(f"input_id={cand.input_id} clear_ref failed: {e}")
        try:
            _emit_audit(candidate=cand, deleted_bytes=cand.size_on_disk)
        except Exception as e:  # pragma: no cover — defensive
            errors.append(f"input_id={cand.input_id} audit failed: {e}")

    return PruneReport(
        scanned=len(candidates),
        eligible=eligible,
        deleted=deleted,
        bytes_freed=bytes_freed,
        missing_files=missing,
        errors=errors,
        candidates=candidates,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prune_audio_retention",
        description=(
            "Delete completed audio uploads older than N days. "
            "Default mode is --dry-run; pass --delete to actually "
            "remove files."
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        required=True,
        help="Retention window in days. Audio files for completed "
        "uploads finished MORE than this many days ago are eligible.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Scan only; do not delete (default).",
    )
    mode.add_argument(
        "--delete",
        dest="do_delete",
        action="store_true",
        help="Delete eligible audio blobs and clear storage_ref.",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Emit the full report as JSON to stdout.",
    )
    args = parser.parse_args(argv)

    if args.days < 1:
        print("error: --days must be >= 1", file=sys.stderr)
        return 2

    do_delete = bool(args.do_delete) and not args.dry_run
    report = run(days=args.days, do_delete=do_delete)

    if args.json_out:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        mode_label = "DELETE" if do_delete else "DRY-RUN"
        print(f"[{mode_label}] retention_days={args.days}")
        print(f"  scanned       = {report.scanned}")
        print(f"  eligible      = {report.eligible}")
        print(f"  deleted       = {report.deleted}")
        print(f"  bytes_freed   = {report.bytes_freed}")
        print(f"  missing_files = {report.missing_files}")
        if report.errors:
            print("  errors:")
            for err in report.errors:
                print(f"    - {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
