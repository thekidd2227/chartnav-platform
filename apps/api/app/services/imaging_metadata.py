"""Phase 88 — Imaging Metadata Review Linkage service.

Read + review projection over the existing `imaging_studies` table.
This phase makes structured imaging metadata visible to clinicians
on a per-encounter basis and surfaces "metadata exists / has been
reviewed" signals to the cross-phase aggregators (Phase 76 summary,
Phase 77 packet, Phase 79 glaucoma cockpit, Phase 80 cataract
workflow, Phase 81 provider action queue, Phase 87 FHIR
DocumentReference).

Hard rules:

  * ChartNav does NOT interpret images. The metadata here is
    structured metadata only — modality, eye, captured_at,
    device manufacturer/model, source system, and the provider's
    own review state.
  * ChartNav does NOT autonomously classify modality or eye.
  * ChartNav does NOT generate findings or diagnoses.
  * Review state is a deterministic projection of the
    ``status`` + ``reviewed_at`` + ``reviewed_by_user_id`` columns
    that Phase 21B already records.
  * Only admin / clinician may PATCH the review state. Reviewer /
    technician / front_desk are denied.
  * Cross-org access returns 404 (no existence leak).

The ``metadata_hash`` field is a deterministic SHA-256 hex digest
of the projected fields. It lets a downstream consumer
(notably Phase 87 FHIR DocumentReference) prove that the
imaging-metadata projection referenced by a packet has not
shifted since the packet was issued.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from sqlalchemy import text as sa_text

from app.auth import Caller
from app.db import engine


# ---------------------------------------------------------------------------
# Allowlists — mirror Phase 21B + a Phase-88-friendly bucket grouping.
# ---------------------------------------------------------------------------

# Phase 88 surface taxonomy. Every modality recorded in
# ``imaging_studies`` is bucketed into one of these workflow-facing
# groups so the panels (glaucoma cockpit, cataract workflow, retina
# summary) can ask "is OCT metadata on file?" without hard-coding
# the underlying enum.
MODALITY_GROUPS: dict[str, tuple[str, ...]] = {
    "oct": ("oct_macula", "oct_rnfl"),
    "fundus": ("fundus_photo", "widefield_fundus"),
    "visual_field": ("visual_field_24_2", "visual_field_10_2"),
    "biometry": ("biometry_packet",),
    "topography": (),
    "external_record": ("external_pdf",),
    "other": ("other",),
}

# Reverse map: each modality code → its group.
MODALITY_TO_GROUP: dict[str, str] = {}
for _group, _members in MODALITY_GROUPS.items():
    for _m in _members:
        MODALITY_TO_GROUP[_m] = _group

VALID_REVIEW_STATUSES = frozenset(
    {"pending_upload", "uploaded", "ready_for_review", "reviewed", "archived"}
)


# ---------------------------------------------------------------------------
# Service errors
# ---------------------------------------------------------------------------


@dataclass
class ImagingMetadataError(Exception):
    error_code: str
    reason: str
    status_code: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _assert_review_role(caller: Caller) -> None:
    if caller.role not in {"admin", "clinician"}:
        raise ImagingMetadataError(
            "forbidden",
            "only admin or clinician can change imaging review state",
            403,
        )


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------


def _resolve_encounter_or_404(
    conn, encounter_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            "SELECT id, organization_id, patient_id, patient_identifier, "
            "patient_name FROM encounters "
            "WHERE id = :eid AND organization_id = :oid"
        ),
        {"eid": encounter_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise ImagingMetadataError(
            "encounter_not_found",
            "encounter not found in your organization",
            404,
        )
    return {
        "id": int(row[0]),
        "organization_id": int(row[1]),
        "patient_id": int(row[2]) if row[2] is not None else None,
        "patient_identifier": row[3],
        "patient_name": row[4],
    }


def _resolve_study_or_404(
    conn, study_id: int, organization_id: int
) -> dict[str, Any]:
    row = conn.execute(
        sa_text(
            f"SELECT {', '.join(_STUDY_COLS)} FROM imaging_studies "
            "WHERE id = :sid AND organization_id = :oid"
        ),
        {"sid": study_id, "oid": organization_id},
    ).fetchone()
    if row is None:
        raise ImagingMetadataError(
            "imaging_metadata_not_found",
            "imaging metadata not found in your organization",
            404,
        )
    return dict(zip(_STUDY_COLS, row))


# ---------------------------------------------------------------------------
# Row schema
# ---------------------------------------------------------------------------

_STUDY_COLS = (
    "id",
    "organization_id",
    "patient_id",
    "encounter_id",
    "modality",
    "eye",
    "status",
    "captured_at",
    "reviewed_by_user_id",
    "reviewed_at",
    "device_manufacturer",
    "device_model",
    "source_system",
    "created_by_user_id",
    "created_at",
    "updated_at",
)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _compute_metadata_hash(projection: dict[str, Any]) -> str:
    """Deterministic SHA-256 hex digest over the projected fields.

    Excludes ``metadata_hash`` itself + display-name resolution so
    actor-name churn doesn't shift the hash.
    """
    canonical_fields = {
        "id": projection["id"],
        "organization_id": projection["organization_id"],
        "patient_id": projection["patient_id"],
        "encounter_id": projection["encounter_id"],
        "modality": projection["modality"],
        "laterality": projection["laterality"],
        "acquisition_date": projection["acquisition_date"],
        "device_manufacturer": projection["device_manufacturer"],
        "device_model": projection["device_model"],
        "source_system": projection["source_system"],
        "review_status": projection["review_status"],
        "reviewed_at": projection["reviewed_at"],
    }
    blob = json.dumps(canonical_fields, sort_keys=True, default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def _actor_cache(
    conn, user_ids: Iterable[int]
) -> dict[int, dict[str, str | None]]:
    ids = sorted({int(u) for u in user_ids if u is not None})
    out: dict[int, dict[str, str | None]] = {}
    if not ids:
        return out
    placeholders = ", ".join(f":u{i}" for i in range(len(ids)))
    params = {f"u{i}": uid for i, uid in enumerate(ids)}
    rows = conn.execute(
        sa_text(
            "SELECT id, full_name, email, role FROM users "
            f"WHERE id IN ({placeholders})"
        ),
        params,
    ).fetchall()
    for uid, full_name, email, role in rows:
        out[int(uid)] = {
            "display_name": full_name or email,
            "role": role,
        }
    return out


def _serialize(
    record: dict[str, Any],
    *,
    reviewer_display_name: str | None = None,
    reviewer_role: str | None = None,
) -> dict[str, Any]:
    projection = {
        "id": int(record["id"]),
        "organization_id": int(record["organization_id"]),
        "patient_id": int(record["patient_id"]),
        "encounter_id": int(record["encounter_id"])
        if record.get("encounter_id") is not None
        else None,
        "modality": record["modality"],
        "modality_group": MODALITY_TO_GROUP.get(
            record["modality"], "other"
        ),
        "laterality": record["eye"],
        "acquisition_date": _iso(record.get("captured_at")),
        "device_manufacturer": record.get("device_manufacturer"),
        "device_model": record.get("device_model"),
        "source_system": record.get("source_system"),
        "review_status": record["status"],
        "reviewed_by_user_id": int(record["reviewed_by_user_id"])
        if record.get("reviewed_by_user_id") is not None
        else None,
        "reviewed_by_display": reviewer_display_name,
        "reviewed_by_role": reviewer_role,
        "reviewed_at": _iso(record.get("reviewed_at")),
        "created_at": _iso(record.get("created_at")),
        "updated_at": _iso(record.get("updated_at")),
    }
    projection["metadata_hash"] = _compute_metadata_hash(projection)
    return projection


_DISCLOSURE = (
    "Imaging metadata only. ChartNav does not interpret images, does not "
    "infer findings from imaging, does not autonomously classify modality "
    "or laterality, and does not recommend treatment, surgery, injections, "
    "or medication based on imaging. Review status is provider-driven."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_for_encounter(encounter_id: int, caller: Caller) -> dict[str, Any]:
    """Return the encounter-scoped imaging metadata projection.

    Newest-first by captured_at, then id. Each row is a metadata-only
    projection — no image binary, no findings text, no interpretation.
    """
    with engine.connect() as conn:
        encounter = _resolve_encounter_or_404(
            conn, encounter_id, caller.organization_id
        )
        patient_id = encounter["patient_id"]
        rows: list[dict[str, Any]] = []
        if patient_id is not None:
            raw = conn.execute(
                sa_text(
                    f"SELECT {', '.join(_STUDY_COLS)} FROM imaging_studies "
                    "WHERE organization_id = :oid AND patient_id = :pid "
                    "ORDER BY CASE WHEN captured_at IS NULL THEN 1 ELSE 0 END, "
                    "captured_at DESC, id DESC"
                ),
                {"oid": caller.organization_id, "pid": patient_id},
            ).fetchall()
            rows = [dict(zip(_STUDY_COLS, r)) for r in raw]
        actor_ids = {
            int(r["reviewed_by_user_id"]) for r in rows
            if r.get("reviewed_by_user_id") is not None
        }
        actors = _actor_cache(conn, actor_ids)

    items: list[dict[str, Any]] = []
    for rec in rows:
        reviewer = (
            actors.get(int(rec["reviewed_by_user_id"]))
            if rec.get("reviewed_by_user_id") is not None
            else None
        )
        items.append(
            _serialize(
                rec,
                reviewer_display_name=(
                    reviewer["display_name"] if reviewer else None
                ),
                reviewer_role=reviewer["role"] if reviewer else None,
            )
        )

    by_group: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_group.setdefault(it["modality_group"], []).append(it)

    unreviewed = [
        it for it in items if it["review_status"] != "reviewed"
    ]

    return {
        "encounter_id": encounter["id"],
        "patient_id": patient_id,
        "patient_identifier": encounter["patient_identifier"],
        "patient_name": encounter["patient_name"],
        "organization_id": caller.organization_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True,
        "items": items,
        "by_modality_group": by_group,
        "counts": {
            "total": len(items),
            "reviewed": sum(1 for it in items if it["review_status"] == "reviewed"),
            "unreviewed": len(unreviewed),
        },
        "modality_groups_present": sorted(by_group.keys()),
        "disclosure": _DISCLOSURE,
    }


def mark_reviewed(
    metadata_id: int, caller: Caller
) -> dict[str, Any]:
    """Set the imaging study's review state to ``reviewed`` and stamp
    the actor. Idempotent — re-reviewing updates the timestamp.
    """
    _assert_review_role(caller)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        existing = _resolve_study_or_404(
            conn, metadata_id, caller.organization_id
        )
        conn.execute(
            sa_text(
                "UPDATE imaging_studies SET status = 'reviewed', "
                "reviewed_by_user_id = :uid, reviewed_at = :ts, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"uid": caller.user_id, "ts": now, "id": metadata_id},
        )
        row = conn.execute(
            sa_text(
                f"SELECT {', '.join(_STUDY_COLS)} FROM imaging_studies "
                "WHERE id = :id"
            ),
            {"id": metadata_id},
        ).fetchone()
        record = dict(zip(_STUDY_COLS, row))
        actors = _actor_cache(conn, [caller.user_id])

    reviewer = actors.get(caller.user_id)
    return _serialize(
        record,
        reviewer_display_name=reviewer["display_name"] if reviewer else None,
        reviewer_role=reviewer["role"] if reviewer else None,
    )


# ---------------------------------------------------------------------------
# Cross-phase projections
# ---------------------------------------------------------------------------


def summary_for_encounter(
    encounter_id: int, organization_id: int
) -> dict[str, Any]:
    """Lightweight metadata-only projection used by Phase 76 summary,
    Phase 77 packet, and Phase 87 FHIR DocumentReference.

    Counts only — no clinical free text, no findings.
    """
    with engine.connect() as conn:
        row = conn.execute(
            sa_text(
                "SELECT id, patient_id FROM encounters "
                "WHERE id = :eid AND organization_id = :oid"
            ),
            {"eid": encounter_id, "oid": organization_id},
        ).fetchone()
        if row is None:
            return _empty_summary()
        patient_id = row[1]
        if patient_id is None:
            return _empty_summary()
        raw = conn.execute(
            sa_text(
                f"SELECT {', '.join(_STUDY_COLS)} FROM imaging_studies "
                "WHERE organization_id = :oid AND patient_id = :pid"
            ),
            {"oid": organization_id, "pid": int(patient_id)},
        ).fetchall()

    items = [dict(zip(_STUDY_COLS, r)) for r in raw]
    total = len(items)
    reviewed = sum(1 for it in items if it["status"] == "reviewed")
    unreviewed = total - reviewed
    by_group: dict[str, dict[str, int]] = {}
    for it in items:
        g = MODALITY_TO_GROUP.get(it["modality"], "other")
        bucket = by_group.setdefault(
            g, {"total": 0, "reviewed": 0, "unreviewed": 0}
        )
        bucket["total"] += 1
        if it["status"] == "reviewed":
            bucket["reviewed"] += 1
        else:
            bucket["unreviewed"] += 1
    # Deterministic group-level hash so packet integrity envelopes can
    # detect metadata shifts without enumerating every row.
    hash_blob = json.dumps(
        {
            "total": total,
            "reviewed": reviewed,
            "by_group": by_group,
            "ids": sorted(int(it["id"]) for it in items),
            "statuses": sorted(
                (int(it["id"]), it["status"]) for it in items
            ),
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    summary_hash = hashlib.sha256(hash_blob).hexdigest()
    return {
        "total_count": total,
        "reviewed_count": reviewed,
        "unreviewed_count": unreviewed,
        "by_modality_group": by_group,
        "modality_groups_present": sorted(by_group.keys()),
        "summary_hash": summary_hash,
        "insufficient_data": total == 0,
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "total_count": 0,
        "reviewed_count": 0,
        "unreviewed_count": 0,
        "by_modality_group": {},
        "modality_groups_present": [],
        "summary_hash": hashlib.sha256(b"empty").hexdigest(),
        "insufficient_data": True,
    }


def patients_with_unreviewed_imaging(
    organization_id: int,
) -> list[dict[str, Any]]:
    """Phase 81 hook — patients with at least one imaging row that
    has not reached ``reviewed`` status. Informational only; never
    Tier 1.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            sa_text(
                "SELECT DISTINCT patient_id FROM imaging_studies "
                "WHERE organization_id = :oid AND status != 'reviewed' "
                "AND patient_id IS NOT NULL"
            ),
            {"oid": organization_id},
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            pid = int(row[0])
            counts = conn.execute(
                sa_text(
                    "SELECT COUNT(*) FROM imaging_studies "
                    "WHERE organization_id = :oid AND patient_id = :pid "
                    "AND status != 'reviewed'"
                ),
                {"oid": organization_id, "pid": pid},
            ).fetchone()
            out.append(
                {
                    "patient_id": pid,
                    "unreviewed_count": int(counts[0]) if counts else 0,
                }
            )
    out.sort(key=lambda r: (-r["unreviewed_count"], r["patient_id"]))
    return out


__all__ = [
    "ImagingMetadataError",
    "MODALITY_GROUPS",
    "MODALITY_TO_GROUP",
    "VALID_REVIEW_STATUSES",
    "list_for_encounter",
    "mark_reviewed",
    "summary_for_encounter",
    "patients_with_unreviewed_imaging",
]
