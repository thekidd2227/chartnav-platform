"""External encounter → native workflow bridge (phase 21).

Integrated modes surface encounter *shells* from an external EHR
(via `FHIRAdapter`, stub, or a vendor adapter). ChartNav's core wedge
— transcript ingestion, findings extraction, note drafting, provider
signoff — lives in native tables (`encounter_inputs`,
`extracted_findings`, `note_versions`, `workflow_events`).

The bridge is the minimal honest glue: given an external encounter
identifier, get-or-create a **native** `encounters` row that carries
the vendor reference (`external_ref` + `external_source`) and the
mirrored shell fields (`patient_identifier`, `patient_name`,
`provider_name`, `status`). Once that native row exists, every
ChartNav workflow endpoint (inputs / generate / sign / export) works
against it identically to a standalone-native encounter.

Design invariants:
- Idempotent. `(organization_id, external_ref, external_source)` is
  UNIQUE in the DB; repeat calls return the existing row.
- Source-of-truth preserved. The external system remains authoritative
  for the encounter shell; ChartNav does not write back.
  `update_encounter_status` in integrated mode still routes through
  the adapter (phase 20) and fails honestly when unsupported.
- No schema duplication. Mirrored fields (patient/provider display)
  live on the existing `encounters` columns; we don't build a parallel
  `external_encounters` table.
- `external_source` in {`fhir`, `stub`, or any vendor adapter key}.

Used by:
- `POST /encounters/bridge` HTTP handler.
- Frontend workflow — "Bridge to ChartNav" action on integrated
  encounter detail.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from app.db import engine, fetch_one, insert_returning_id, transaction


def _pick_default_location(conn, organization_id: int) -> int:
    """Pick the caller's first active location for bridge shells.

    Bridged encounters don't reliably know their location from the
    external system without vendor-specific mapping; rather than
    introduce a NULL-location path that breaks existing queries,
    attach the shell to the org's first seeded active location.
    Operators can re-assign later if the external system carries
    usable location metadata.
    """
    row = conn.execute(
        sa.text(
            "SELECT id FROM locations "
            "WHERE organization_id = :org AND is_active = 1 "
            "ORDER BY id LIMIT 1"
        ),
        {"org": organization_id},
    ).mappings().first()
    if row is None:
        raise RuntimeError(
            f"organization {organization_id} has no active location; "
            "cannot create bridged encounter shell"
        )
    return int(row["id"])


def resolve_or_create_bridged_encounter(
    *,
    organization_id: int,
    external_ref: str,
    external_source: str,
    patient_identifier: str | None = None,
    patient_name: str | None = None,
    provider_name: str | None = None,
    status: str | None = None,
    location_id: int | None = None,
) -> dict[str, Any]:
    """Idempotent get-or-create for a bridged native encounter.

    Returns the full native row (same shape the existing `/encounters`
    surface emits) with an additional `_bridged` flag on freshly
    created rows so callers can surface a one-shot "bridged now"
    banner if desired. Existing rows return `_bridged=False`.
    """
    if not external_ref:
        raise ValueError("external_ref is required")
    if not external_source:
        raise ValueError("external_source is required")

    with transaction() as conn:
        existing = conn.execute(
            sa.text(
                "SELECT id FROM encounters WHERE organization_id = :org "
                "AND external_ref = :ref AND external_source = :src"
            ),
            {"org": organization_id, "ref": external_ref, "src": external_source},
        ).mappings().first()

        if existing is not None:
            native_id = int(existing["id"])
            bridged_now = False
        else:
            loc = location_id or _pick_default_location(conn, organization_id)
            native_id = insert_returning_id(
                conn,
                "encounters",
                {
                    "organization_id": organization_id,
                    "location_id": loc,
                    "patient_identifier": (
                        patient_identifier or f"EXT-{external_ref}"
                    ),
                    "patient_name": patient_name,
                    "provider_name": provider_name or "<external>",
                    # External encounters enter ChartNav in whatever
                    # status the adapter reported; default `scheduled`
                    # so the state machine has a valid starting point
                    # the provider can drive from within ChartNav
                    # (workflow events + signoff are ChartNav-side).
                    "status": status or "scheduled",
                    "external_ref": external_ref,
                    "external_source": external_source,
                },
            )
            bridged_now = True

    row = fetch_one(
        "SELECT id, organization_id, location_id, patient_identifier, "
        "patient_name, provider_name, status, patient_id, provider_id, "
        "external_ref, external_source, "
        "scheduled_at, started_at, completed_at, created_at "
        "FROM encounters WHERE id = :id",
        {"id": native_id},
    )
    if row is None:  # pragma: no cover — defensive
        raise RuntimeError(
            f"bridge failed to read back native encounter id={native_id}"
        )
    return {
        **row,
        "_source": "chartnav",
        "_bridged": bridged_now,
        "_external_ref": row.get("external_ref"),
        "_external_source": row.get("external_source"),
    }
