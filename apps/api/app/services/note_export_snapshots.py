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
        "issued_by_email "
        "FROM note_export_snapshots WHERE note_version_id = :nvid "
        "ORDER BY id DESC",
        {"nvid": int(note_version_id)},
    )


def get_snapshot(snapshot_id: int) -> Optional[dict[str, Any]]:
    row = fetch_one(
        "SELECT id, organization_id, note_version_id, encounter_id, "
        "evidence_chain_event_id, artifact_json, artifact_hash_sha256, "
        "content_fingerprint, issued_at, issued_by_user_id, "
        "issued_by_email "
        "FROM note_export_snapshots WHERE id = :id",
        {"id": int(snapshot_id)},
    )
    return dict(row) if row else None


__all__ = [
    "ExportSnapshot",
    "persist_snapshot",
    "list_snapshots_for_note",
    "get_snapshot",
]
