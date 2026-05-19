"""ChartNav deployment / observability telemetry (phase 37).

Single read-only aggregator that powers every "control plane" lens
on a ChartNav deployment:

- ChartNav itself (admin section in the doctor app)
- LCC (fleet-level rollup across many deployments)
- SourceDeck (deployment-readiness view inside the implementation
  catalog)

The model is deliberately narrow: one capability surfaced through
multiple lenses, not three forks of the same data.

Source-of-truth for everything in here:
- `organizations` / `locations`            (org + site identity)
- `users`                                  (clinician / reviewer counts)
- `encounters`                             (workload signal)
- `encounter_inputs`                       (audio + transcript queue)
- `note_versions`                          (signed-note signal)
- `security_audit_events`                  (alerts + recent activity)
- `app.config.settings`                    (release/runtime config)
- `app.services.audio_storage` / `stt_provider`
                                           (storage + STT health)

PHI minimisation: aggregates and counts only. Individual transcript
text never crosses this surface; the deepest a control-plane reader
gets is `(input_id, status, last_error_code)`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.config import settings
from app.db import fetch_all, fetch_one


# ---------------------------------------------------------------------------
# Release manifest
# ---------------------------------------------------------------------------

DEPLOYMENT_API_VERSION = "v1"
CHARTNAV_RELEASE_VERSION = "0.1.0"
# Each control-plane lens reads this string as the API contract
# version. Bump when the response shape changes in a non-additive
# way; LCC + SourceDeck pin to a major.


@dataclass(frozen=True)
class ReleaseManifest:
    """Stable identity of a deployment's running build + config."""
    release_version: str
    api_version: str
    platform_mode: str
    integration_adapter: str
    audio_ingest_mode: str
    stt_provider: str
    storage_scheme: str
    capture_modes: tuple[str, ...]   # audio capture sources allowed today


def _release_manifest() -> ReleaseManifest:
    # Storage scheme is whatever the resolver picks; we don't import
    # the resolver eagerly so a bootstrap-time error in
    # audio_storage doesn't break this module.
    try:
        from app.services.audio_storage import resolve_storage
        scheme = resolve_storage().scheme
    except Exception:
        scheme = "unknown"
    return ReleaseManifest(
        release_version=CHARTNAV_RELEASE_VERSION,
        api_version=DEPLOYMENT_API_VERSION,
        platform_mode=settings.platform_mode,
        integration_adapter=settings.integration_adapter,
        audio_ingest_mode=settings.audio_ingest_mode,
        stt_provider=settings.stt_provider,
        storage_scheme=scheme,
        capture_modes=("file-upload", "browser-mic"),
    )


# ---------------------------------------------------------------------------
# Health rollups
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _count(sql: str, params: dict[str, Any]) -> int:
    row = fetch_one(sql, params)
    if row is None:
        return 0
    # Different drivers spell the count column differently; grab whatever's there.
    for v in row.values():
        return int(v or 0)
    return 0


def _input_queue_health(organization_id: int, *, hours: int) -> dict[str, Any]:
    cutoff = _now() - timedelta(hours=hours)
    queued = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org AND ei.processing_status = 'queued'",
        {"org": organization_id},
    )
    processing = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org AND ei.processing_status = 'processing'",
        {"org": organization_id},
    )
    completed_window = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND ei.processing_status = 'completed' "
        "AND ei.finished_at >= :since",
        {"org": organization_id, "since": cutoff},
    )
    failed_window = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND ei.processing_status = 'failed' "
        "AND ei.updated_at >= :since",
        {"org": organization_id, "since": cutoff},
    )
    needs_review_window = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND ei.processing_status = 'needs_review' "
        "AND ei.updated_at >= :since",
        {"org": organization_id, "since": cutoff},
    )

    # Oldest queued row: if non-zero, ops cares — STT may be down.
    oldest_row = fetch_one(
        "SELECT MIN(ei.created_at) AS oldest "
        "FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org AND ei.processing_status = 'queued'",
        {"org": organization_id},
    )
    oldest_queued_at = (oldest_row or {}).get("oldest")
    oldest_queued_age_seconds: Optional[int] = None
    if oldest_queued_at is not None:
        try:
            if isinstance(oldest_queued_at, str):
                # SQLite returns ISO strings.
                oldest_dt = datetime.fromisoformat(
                    oldest_queued_at.replace(" ", "T")
                )
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
            else:
                oldest_dt = oldest_queued_at
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
            oldest_queued_age_seconds = max(
                0, int((_now() - oldest_dt).total_seconds())
            )
        except Exception:
            oldest_queued_age_seconds = None

    return {
        "queued": queued,
        "processing": processing,
        "completed_window": completed_window,
        "failed_window": failed_window,
        "needs_review_window": needs_review_window,
        "oldest_queued_age_seconds": oldest_queued_age_seconds,
    }


def _note_health(organization_id: int, *, hours: int) -> dict[str, Any]:
    cutoff = _now() - timedelta(hours=hours)
    drafts = _count(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.draft_status IN ('draft','provider_review','revised')",
        {"org": organization_id},
    )
    signed_window = _count(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.draft_status IN ('signed','exported') "
        "AND nv.signed_at >= :since",
        {"org": organization_id, "since": cutoff},
    )
    exported_window = _count(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.draft_status = 'exported' "
        "AND nv.exported_at >= :since",
        {"org": organization_id, "since": cutoff},
    )
    return {
        "open_drafts": drafts,
        "signed_window": signed_window,
        "exported_window": exported_window,
    }


def _audit_alert_counts(organization_id: int, *, hours: int) -> dict[str, Any]:
    """Recent alert-class events grouped by event_type.

    The alert "class" is anything ending in _failed / _denied or
    carrying an `error_code`. We don't try to be smart — the caller
    decides which event types are interesting; we just hand back the
    count + most-recent timestamp.
    """
    cutoff = _now() - timedelta(hours=hours)
    rows = fetch_all(
        "SELECT event_type, error_code, COUNT(*) AS n, "
        "MAX(created_at) AS last_at "
        "FROM security_audit_events "
        "WHERE organization_id = :org AND created_at >= :since "
        "AND (error_code IS NOT NULL OR event_type LIKE '%failed%' "
        "     OR event_type LIKE '%denied%') "
        "GROUP BY event_type, error_code "
        "ORDER BY n DESC",
        {"org": organization_id, "since": cutoff},
    )
    items = [
        {
            "event_type": r["event_type"],
            "error_code": r["error_code"],
            "count": int(r["n"] or 0),
            "last_at": (
                r["last_at"].isoformat()
                if hasattr(r["last_at"], "isoformat")
                else (r["last_at"] or None)
            ),
        }
        for r in rows
    ]
    total = sum(it["count"] for it in items)
    return {"total": total, "items": items}


def _location_rollup(organization_id: int, *, hours: int) -> list[dict[str, Any]]:
    """Per-location counts so a fleet rollup can drill into "which
    site has the queue backed up?"."""
    cutoff = _now() - timedelta(hours=hours)
    rows = fetch_all(
        "SELECT l.id AS location_id, l.name AS location_name, "
        "  COUNT(DISTINCT e.id) AS encounters_window, "
        "  SUM(CASE WHEN ei.processing_status='queued' THEN 1 ELSE 0 END) AS queued, "
        "  SUM(CASE WHEN ei.processing_status='processing' THEN 1 ELSE 0 END) AS processing, "
        "  SUM(CASE WHEN ei.processing_status='failed' AND ei.updated_at >= :since THEN 1 ELSE 0 END) AS failed_window "
        "FROM locations l "
        "LEFT JOIN encounters e ON e.location_id = l.id "
        "  AND (e.created_at >= :since OR e.id IN (SELECT encounter_id FROM encounter_inputs)) "
        "LEFT JOIN encounter_inputs ei ON ei.encounter_id = e.id "
        "WHERE l.organization_id = :org "
        "GROUP BY l.id, l.name "
        "ORDER BY l.id ASC",
        {"org": organization_id, "since": cutoff},
    )
    return [
        {
            "location_id": int(r["location_id"]),
            "location_name": r["location_name"],
            "encounters_window": int(r["encounters_window"] or 0),
            "queued": int(r["queued"] or 0),
            "processing": int(r["processing"] or 0),
            "failed_window": int(r["failed_window"] or 0),
        }
        for r in rows
    ]


def _user_summary(organization_id: int) -> dict[str, Any]:
    rows = fetch_all(
        "SELECT role, COUNT(*) AS n FROM users "
        "WHERE organization_id = :org AND is_active = 1 "
        "GROUP BY role",
        {"org": organization_id},
    )
    by_role: dict[str, int] = {}
    for r in rows:
        by_role[r["role"]] = int(r["n"] or 0)
    return {
        "active_total": sum(by_role.values()),
        "by_role": by_role,
    }


def _recent_jobs(organization_id: int, *, limit: int) -> list[dict[str, Any]]:
    """Most recent ingestion outcomes, terminal states only.

    Carries `last_error_code` (a stable token) but never the
    transcript body or the raw error message — keep this control-
    plane-safe for SourceDeck's live preview as well as LCC's
    alert wall.
    """
    rows = fetch_all(
        "SELECT ei.id, ei.encounter_id, ei.input_type, ei.processing_status, "
        "       ei.last_error_code, ei.retry_count, ei.finished_at, ei.updated_at "
        "FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "ORDER BY COALESCE(ei.finished_at, ei.updated_at) DESC, ei.id DESC "
        "LIMIT :n",
        {"org": organization_id, "n": int(limit)},
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append({
            "input_id": r["id"],
            "encounter_id": r["encounter_id"],
            "input_type": r["input_type"],
            "processing_status": r["processing_status"],
            "last_error_code": r["last_error_code"],
            "retry_count": int(r["retry_count"] or 0),
            "finished_at": (
                r["finished_at"].isoformat()
                if hasattr(r["finished_at"], "isoformat")
                else r["finished_at"]
            ),
            "updated_at": (
                r["updated_at"].isoformat()
                if hasattr(r["updated_at"], "isoformat")
                else r["updated_at"]
            ),
        })
    return out


def _qa_summary(organization_id: int) -> dict[str, Any]:
    """Counts that drive a QA reviewer's intake queue.

    No transcript bodies, no patient identifiers — just queue
    cardinality. An admin who needs the full text uses the existing
    note + transcript reads, which are PHI-aware.
    """
    needs_review_inputs = _count(
        "SELECT COUNT(*) AS n FROM encounter_inputs ei "
        "JOIN encounters e ON e.id = ei.encounter_id "
        "WHERE e.organization_id = :org "
        "AND ei.processing_status IN ('failed','needs_review')",
        {"org": organization_id},
    )
    awaiting_signoff = _count(
        "SELECT COUNT(*) AS n FROM note_versions nv "
        "JOIN encounters e ON e.id = nv.encounter_id "
        "WHERE e.organization_id = :org "
        "AND nv.draft_status = 'provider_review'",
        {"org": organization_id},
    )
    return {
        "inputs_needing_review": needs_review_inputs,
        "notes_awaiting_signoff": awaiting_signoff,
    }


# ---------------------------------------------------------------------------
# Public aggregates
# ---------------------------------------------------------------------------

# Stable schema ids for the public deployment contracts. SourceDeck and
# any other consumer key off these so we can publish vN+1 without
# silently breaking vN readers. Bump the integer suffix only when an
# existing field is renamed, removed, or has its type changed. Adding a
# new field is *not* a bump.
DEPLOYMENT_OVERVIEW_SCHEMA_VERSION = "deployment_overview/v1"
DEPLOYMENT_MANIFEST_SCHEMA_VERSION = "deployment_manifest/v1"


def deployment_overview(*, organization_id: int, hours: int = 24) -> dict[str, Any]:
    """Top-level rollup. The default lens for the ChartNav admin
    section + LCC's per-deployment card + SourceDeck's
    deployment-readiness panel."""
    inputs = _input_queue_health(organization_id, hours=hours)
    notes = _note_health(organization_id, hours=hours)
    alerts = _audit_alert_counts(organization_id, hours=hours)
    users = _user_summary(organization_id)
    qa = _qa_summary(organization_id)
    locations = _location_rollup(organization_id, hours=hours)
    manifest = _release_manifest()

    return {
        "schema_version": DEPLOYMENT_OVERVIEW_SCHEMA_VERSION,
        "deployment_id": organization_id,  # one deployment ↔ one org today
        "window_hours": int(hours),
        "generated_at": _now().isoformat(),
        "release": {
            "release_version": manifest.release_version,
            "api_version": manifest.api_version,
            "platform_mode": manifest.platform_mode,
            "integration_adapter": manifest.integration_adapter,
            "audio_ingest_mode": manifest.audio_ingest_mode,
            "stt_provider": manifest.stt_provider,
            "storage_scheme": manifest.storage_scheme,
            "capture_modes": list(manifest.capture_modes),
        },
        "inputs": inputs,
        "notes": notes,
        "alerts": alerts,
        "users": users,
        "qa": qa,
        "locations": locations,
        # Cheap rolled-up health dot for LCC's fleet table — green/
        # amber/red. Computed from input + alert signals only.
        "health": _summary_health(inputs, alerts),
    }


def _summary_health(inputs: dict[str, Any], alerts: dict[str, Any]) -> str:
    if alerts["total"] >= 5:
        return "red"
    if (inputs["failed_window"] or 0) >= 3:
        return "red"
    if (inputs["oldest_queued_age_seconds"] or 0) >= 600:  # 10 minutes
        return "amber"
    if alerts["total"] >= 1 or inputs["failed_window"] >= 1:
        return "amber"
    return "green"


def deployment_locations(*, organization_id: int, hours: int = 24) -> dict[str, Any]:
    return {
        "deployment_id": organization_id,
        "window_hours": int(hours),
        "generated_at": _now().isoformat(),
        "items": _location_rollup(organization_id, hours=hours),
    }


def deployment_alerts(*, organization_id: int, hours: int = 24) -> dict[str, Any]:
    payload = _audit_alert_counts(organization_id, hours=hours)
    return {
        "deployment_id": organization_id,
        "window_hours": int(hours),
        "generated_at": _now().isoformat(),
        **payload,
    }


def deployment_jobs(*, organization_id: int, limit: int = 50) -> dict[str, Any]:
    return {
        "deployment_id": organization_id,
        "limit": int(limit),
        "generated_at": _now().isoformat(),
        "items": _recent_jobs(organization_id, limit=limit),
    }


def deployment_qa(*, organization_id: int) -> dict[str, Any]:
    return {
        "deployment_id": organization_id,
        "generated_at": _now().isoformat(),
        **_qa_summary(organization_id),
    }


def deployment_manifest() -> dict[str, Any]:
    """Public, deployment-wide release manifest. No org filter — this
    is the build/runtime fingerprint, not a tenant view. Used by
    SourceDeck to confirm a deployed instance matches the catalog
    capability version it expects."""
    m = _release_manifest()
    return {
        "schema_version": DEPLOYMENT_MANIFEST_SCHEMA_VERSION,
        "release_version": m.release_version,
        "api_version": m.api_version,
        "platform_mode": m.platform_mode,
        "integration_adapter": m.integration_adapter,
        "audio_ingest_mode": m.audio_ingest_mode,
        "stt_provider": m.stt_provider,
        "storage_scheme": m.storage_scheme,
        "capture_modes": list(m.capture_modes),
    }
