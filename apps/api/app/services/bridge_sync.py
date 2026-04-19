"""Bridged-encounter refresh foundation (phase 23).

When ChartNav bridges an external encounter (phase 21), the native
row mirrors the external shell at bridge-time and never re-syncs.
This module is the minimum honest re-fetch foundation:

- Given a bridged native encounter (`external_ref` + `external_source`
  populated), re-call the adapter's `fetch_encounter` and reconcile
  only the **allowed mirror fields** onto the native row.
- Preserves the phase-20 + phase-21 source-of-truth boundary: we
  never write back to the external EHR, we never stomp on ChartNav-
  native workflow columns, and we never bridge an encounter that
  wasn't already bridged.

Not included in this phase (by design):
- Continuous background sync. A cron or scheduled job can call
  `refresh_bridged_encounter(id)` on a cadence; the service has no
  opinion about scheduling.
- Audit-level diffing of every mirrored field — we record the fact
  of the refresh in the audit trail via the HTTP handler.
- Transactional consistency with a vendor write-back (there is no
  write-back in ChartNav's wedge today — that's honest).
"""

from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa

from app.db import engine, fetch_one

log = logging.getLogger("chartnav.bridge_sync")


# Fields the refresh is allowed to update on the native row. Anything
# not in this list is never touched by the sync — in particular,
# `patient_id`, `provider_id`, `location_id`, `external_ref`, and
# `external_source` are preserved; and all ChartNav-native workflow
# rows (workflow_events, encounter_inputs, extracted_findings,
# note_versions) live on separate tables and are untouched.
MIRRORED_FIELDS = (
    "patient_identifier",
    "patient_name",
    "provider_name",
    "status",
)


class BridgeRefreshError(RuntimeError):
    def __init__(self, error_code: str, reason: str, status_code: int = 400):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason
        self.status_code = status_code


def refresh_bridged_encounter(
    *,
    native_id: int,
    organization_id: int,
) -> dict[str, Any]:
    """Re-fetch external shell + reconcile allowed fields.

    Returns:
        {
            "id": <native_id>,
            "refreshed": True/False,
            "mirrored": {field: new_value, ...} | {},
            "skipped_unchanged": [field, ...],
        }

    `refreshed=True` when at least one mirror field changed.
    `mirrored` is the exact set of fields that were updated. The
    caller (HTTP handler) logs the audit event.
    """
    row = fetch_one(
        "SELECT id, organization_id, external_ref, external_source, "
        "patient_identifier, patient_name, provider_name, status "
        "FROM encounters WHERE id = :id",
        {"id": native_id},
    )
    if row is None or row["organization_id"] != organization_id:
        raise BridgeRefreshError(
            "encounter_not_found",
            "no such encounter in your organization",
            404,
        )
    if not row["external_ref"] or not row["external_source"]:
        raise BridgeRefreshError(
            "not_bridged",
            "encounter has no external_ref/external_source to refresh; "
            "only bridged encounters can be synced",
            409,
        )

    # Ask the adapter for the fresh shell.
    from app.integrations import resolve_adapter
    from app.integrations.base import AdapterError

    adapter = resolve_adapter()
    # The adapter returned for a deployment may not match the
    # `external_source` on the native row (e.g. the deployment is
    # now in standalone mode but historical rows were bridged from
    # FHIR). We refuse honestly rather than fetching from the wrong
    # adapter.
    if adapter.info.key != row["external_source"]:
        raise BridgeRefreshError(
            "external_source_mismatch",
            f"native row was bridged from {row['external_source']!r} but "
            f"current adapter is {adapter.info.key!r}; refresh is refused "
            "to preserve source-of-truth",
            409,
        )

    try:
        fresh = adapter.fetch_encounter(str(row["external_ref"]))
    except AdapterError as e:
        raise BridgeRefreshError(
            e.error_code, e.reason, 502 if e.error_code != "encounter_not_found" else 404,
        )

    updates: dict[str, Any] = {}
    skipped: list[str] = []
    for field in MIRRORED_FIELDS:
        new_value = fresh.get(field)
        current = row[field]
        if new_value is None or new_value == "":
            skipped.append(field)
            continue
        if current == new_value:
            skipped.append(field)
            continue
        updates[field] = new_value

    if not updates:
        return {
            "id": native_id,
            "refreshed": False,
            "mirrored": {},
            "skipped_unchanged": list(MIRRORED_FIELDS),
        }

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                f"UPDATE encounters SET {set_clauses}, "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :id AND organization_id = :org"
            ) if False else sa.text(  # no updated_at on encounters
                f"UPDATE encounters SET {set_clauses} "
                "WHERE id = :id AND organization_id = :org"
            ),
            {**updates, "id": native_id, "org": organization_id},
        )

    log.info(
        "bridge_refresh id=%s mirrored=%s skipped=%s",
        native_id, list(updates.keys()), skipped,
    )
    return {
        "id": native_id,
        "refreshed": True,
        "mirrored": updates,
        "skipped_unchanged": skipped,
    }
