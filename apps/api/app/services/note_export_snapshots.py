"""Phase 56 — export snapshot service.

Captures a deterministic byte-exact record of what ChartNav actually
handed off when a note is exported. Artifacts are re-buildable from
the note row on demand, but after an amendment the source row may
no longer reflect the exported state — the snapshot is the only
way to reconstruct "what was shipped at export time".

One snapshot row per export. Linked to the `note_exported` evidence
chain event for forensic cross-reference.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import text

from app.db import fetch_all, fetch_one, transaction


@dataclass(frozen=True)
class ExportSnapshot:
    id: int
    note_version_id: int
    encounter_id: int
    evidence_chain_event_id: Optional[int]
    artifact_hash_sha256: str
    content_fingerprint: Optional[str]
    issued_at: str
    issued_by_user_id: Optional[int]
    issued_by_email: Optional[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "note_version_id": self.note_version_id,
            "encounter_id": self.encounter_id,
            "evidence_chain_event_id": self.evidence_chain_event_id,
            "artifact_hash_sha256": self.artifact_hash_sha256,
            "content_fingerprint": self.content_fingerprint,
            "issued_at": self.issued_at,
            "issued_by_user_id": self.issued_by_user_id,
            "issued_by_email": self.issued_by_email,
        }


def _canonical_artifact_bytes(artifact: dict[str, Any]) -> bytes:
    """Deterministic serialization: sorted keys, compact separators,
    UTF-8. Same policy as the evidence chain so the hash is
    reproducible from stored bytes."""
    return json.dumps(
        artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def persist_snapshot(
    *,
    organization_id: int,
    note_row: dict[str, Any],
    artifact: dict[str, Any],
    evidence_chain_event_id: Optional[int],
    issued_by_user_id: Optional[int],
    issued_by_email: Optional[str],
) -> ExportSnapshot:
    """Write one export snapshot row. Computes and stores the
    canonical byte hash so re-verification is deterministic."""
    raw = _canonical_artifact_bytes(artifact)
    digest = hashlib.sha256(raw).hexdigest()

    with transaction() as conn:
        new_row = conn.execute(
            text(
                "INSERT INTO note_export_snapshots ("
                " organization_id, note_version_id, encounter_id, "
                " evidence_chain_event_id, artifact_json, "
                " artifact_hash_sha256, content_fingerprint, "
                " issued_by_user_id, issued_by_email"
                ") VALUES ("
                " :org, :nvid, :enc, :evt, :art, :h, :fp, :uid, :email"
                ") RETURNING id, issued_at"
            ),
            {
                "org": int(organization_id),
                "nvid": int(note_row["id"]),
                "enc": int(note_row["encounter_id"]),
                "evt": (
                    int(evidence_chain_event_id)
                    if evidence_chain_event_id is not None else None
                ),
                "art": raw.decode("utf-8"),
                "h": digest,
                "fp": note_row.get("content_fingerprint"),
                "uid": issued_by_user_id,
                "email": issued_by_email,
            },
        ).mappings().first()

    issued_at = new_row.get("issued_at")
    if hasattr(issued_at, "isoformat"):
        issued_at_iso = issued_at.isoformat()
    else:
        issued_at_iso = str(issued_at) if issued_at else ""

    return ExportSnapshot(
        id=int(new_row["id"]),
        note_version_id=int(note_row["id"]),
        encounter_id=int(note_row["encounter_id"]),
        evidence_chain_event_id=evidence_chain_event_id,
        artifact_hash_sha256=digest,
        content_fingerprint=note_row.get("content_fingerprint"),
        issued_at=issued_at_iso,
        issued_by_user_id=issued_by_user_id,
        issued_by_email=issued_by_email,
    )


def list_snapshots_for_note(note_version_id: int) -> list[dict[str, Any]]:
    """Most-recent first."""
    return fetch_all(
        "SELECT id, organization_id, note_version_id, encounter_id, "
        "evidence_chain_event_id, artifact_hash_sha256, "
        "content_fingerprint, issued_at, issued_by_user_id, "
        "issued_by_email, artifact_purged_at, artifact_purged_reason "
        "FROM note_export_snapshots WHERE note_version_id = :nvid "
        "ORDER BY id DESC",
        {"nvid": int(note_version_id)},
    )


def get_snapshot(snapshot_id: int) -> Optional[dict[str, Any]]:
    row = fetch_one(
        "SELECT id, organization_id, note_version_id, encounter_id, "
        "evidence_chain_event_id, artifact_json, artifact_hash_sha256, "
        "content_fingerprint, issued_at, issued_by_user_id, "
        "issued_by_email, artifact_purged_at, artifact_purged_reason "
        "FROM note_export_snapshots WHERE id = :id",
        {"id": int(snapshot_id)},
    )
    return dict(row) if row else None


# ---------------------------------------------------------------------
# Phase 57 — retention / soft-purge sweep
# ---------------------------------------------------------------------

from dataclasses import dataclass as _dataclass
from datetime import datetime, timedelta, timezone


@_dataclass(frozen=True)
class RetentionSweepResult:
    dry_run: bool
    organization_id: int
    retention_days: Optional[int]
    candidates_found: int
    purged: int
    candidate_ids: list[int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "organization_id": self.organization_id,
            "retention_days": self.retention_days,
            "candidates_found": self.candidates_found,
            "purged": self.purged,
            "candidate_ids": self.candidate_ids,
        }


def sweep_retention(
    organization_id: int,
    *,
    dry_run: bool = False,
) -> RetentionSweepResult:
    """Apply the org's retention policy to its export snapshots.

    Policy: when the org's `export_snapshot_retention_days` is set,
    soft-purge (clear artifact_json + stamp purge metadata) all
    snapshots whose `issued_at < now() - retention_days` AND whose
    artifact_json is still present.

    SAFETY — what this function never does:
      * never deletes a snapshot row (the id is referenced by
        evidence chain events; the row must remain resolvable)
      * never purges when the org has no retention configured
      * never purges rows already purged (idempotent)
      * never touches artifact_hash_sha256 or linkage columns, so
        integrity checks against the chain still hold

    When `dry_run=True`, returns the candidate ids without mutating
    anything. Operators are expected to dry-run first.
    """
    from app.security_policy import resolve_security_policy

    policy = resolve_security_policy(organization_id)
    days = getattr(policy, "export_snapshot_retention_days", None)
    if not days:
        return RetentionSweepResult(
            dry_run=dry_run,
            organization_id=organization_id,
            retention_days=None,
            candidates_found=0,
            purged=0,
            candidate_ids=[],
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
    candidates = fetch_all(
        "SELECT id FROM note_export_snapshots "
        "WHERE organization_id = :org "
        "AND artifact_purged_at IS NULL "
        "AND issued_at < :cutoff "
        "ORDER BY id ASC LIMIT 1000",
        {"org": int(organization_id), "cutoff": cutoff.isoformat()},
    )
    ids = [int(r["id"]) for r in candidates]
    if dry_run or not ids:
        return RetentionSweepResult(
            dry_run=True if dry_run else False,
            organization_id=organization_id,
            retention_days=int(days),
            candidates_found=len(ids),
            purged=0,
            candidate_ids=ids,
        )

    purged = 0
    reason = (
        f"retention_sweep:days={days};retained_hash_only"
    )
    from sqlalchemy import text as _sql
    with transaction() as conn:
        for sid in ids:
            conn.execute(
                _sql(
                    "UPDATE note_export_snapshots SET "
                    "artifact_json = '', "
                    "artifact_purged_at = CURRENT_TIMESTAMP, "
                    "artifact_purged_reason = :r "
                    "WHERE id = :id "
                    "AND organization_id = :org "
                    "AND artifact_purged_at IS NULL"
                ),
                {"id": sid, "org": int(organization_id), "r": reason},
            )
            purged += 1

    return RetentionSweepResult(
        dry_run=False,
        organization_id=organization_id,
        retention_days=int(days),
        candidates_found=len(ids),
        purged=purged,
        candidate_ids=ids,
    )


__all__ = [
    "ExportSnapshot",
    "persist_snapshot",
    "list_snapshots_for_note",
    "get_snapshot",
    "RetentionSweepResult",
    "sweep_retention",
]
