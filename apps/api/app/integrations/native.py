"""Native ChartNav adapter.

Used when ChartNav is the system of record (`platform_mode=standalone`
or an integrated deployment that explicitly keeps operational data in
the ChartNav DB).

This adapter is thin. The real persistence layer is `app.db` +
`app.api.routes`; this module reuses the same query surface the HTTP
routes use, so behavior stays consistent across both entry points.
No parallel ORM, no duplicated SQL.

Patient/provider objects live in the ChartNav DB as lightweight
records (org-scoped users + locations + encounters today; a
`patients` table is the obvious next addition when standalone mode
grows). The adapter is honest about current capabilities via the
`supports_*` flags in `info`.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from app.db import engine
from app.integrations.base import (
    AdapterError,
    AdapterInfo,
    AdapterNotSupported,
    EncounterListResult,
    SourceOfTruth,
)


_INFO = AdapterInfo(
    key="native",
    display_name="ChartNav native",
    description=(
        "ChartNav persists clinical and operational data — including "
        "patients and providers — to its own database. Use in "
        "standalone deployments where ChartNav is the system of record."
    ),
    supports_patient_read=True,
    supports_patient_write=True,
    supports_encounter_read=True,
    supports_encounter_write=True,
    supports_document_write=True,  # stored as workflow_events today
    source_of_truth={
        "organization": SourceOfTruth.CHARTNAV,
        "location": SourceOfTruth.CHARTNAV,
        "user": SourceOfTruth.CHARTNAV,
        "encounter": SourceOfTruth.CHARTNAV,
        "workflow_event": SourceOfTruth.CHARTNAV,
        "patient": SourceOfTruth.CHARTNAV,
        "provider": SourceOfTruth.CHARTNAV,
        "document": SourceOfTruth.CHARTNAV,
    },
)


class NativeChartNavAdapter:
    """ChartNav-as-system-of-record adapter."""

    @property
    def info(self) -> AdapterInfo:
        return _INFO

    # --- Patients ---------------------------------------------------
    def fetch_patient(self, patient_id: str) -> dict[str, Any]:
        """Fetch a native patient by PK or `patient_identifier`.

        Callers use PKs; adapters accept either because integrations
        typically carry their own reference. Returns a canonicalized
        dict, not a DB row.
        """
        if not patient_id:
            raise AdapterError("invalid_argument", "patient_id is required")
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT id, organization_id, external_ref, "
                    "patient_identifier, first_name, last_name, "
                    "date_of_birth, sex_at_birth, is_active, created_at "
                    "FROM patients WHERE "
                    "CAST(id AS VARCHAR) = :id OR patient_identifier = :id"
                ),
                {"id": str(patient_id)},
            ).mappings().first()
        if row is None:
            raise AdapterError("patient_not_found", f"id={patient_id}")
        return {**dict(row), "source": "native"}

    def search_patients(
        self, *, query: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        if not query:
            return []
        q = f"%{query}%"
        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT id, organization_id, external_ref, "
                    "patient_identifier, first_name, last_name, "
                    "date_of_birth, sex_at_birth, is_active, created_at "
                    "FROM patients WHERE is_active = 1 AND ("
                    "patient_identifier LIKE :q OR first_name LIKE :q OR last_name LIKE :q"
                    ") ORDER BY id LIMIT :lim"
                ),
                {"q": q, "lim": int(limit)},
            ).mappings().all()
        return [{**dict(r), "source": "native"} for r in rows]

    # --- Encounters -------------------------------------------------
    def list_encounters(
        self,
        *,
        organization_id: int,
        location_id: int | None = None,
        status: str | None = None,
        provider_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EncounterListResult:
        clauses = ["organization_id = :org"]
        params: dict[str, Any] = {"org": organization_id}
        if location_id is not None:
            clauses.append("location_id = :loc")
            params["loc"] = location_id
        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        if provider_name is not None:
            clauses.append("provider_name = :pname")
            params["pname"] = provider_name
        where = " WHERE " + " AND ".join(clauses)

        with engine.connect() as conn:
            total_row = conn.execute(
                sa.text(f"SELECT COUNT(*) AS n FROM encounters{where}"),
                params,
            ).mappings().first()
            rows = conn.execute(
                sa.text(
                    "SELECT id, organization_id, location_id, "
                    "patient_identifier, patient_name, provider_name, "
                    "status, patient_id, provider_id, "
                    "external_ref, external_source, "
                    "scheduled_at, started_at, completed_at, created_at "
                    f"FROM encounters{where} "
                    "ORDER BY id DESC LIMIT :limit OFFSET :offset"
                ),
                {**params, "limit": int(limit), "offset": int(offset)},
            ).mappings().all()
        items = [
            {**dict(r), "_source": "chartnav"} for r in rows
        ]
        return EncounterListResult(
            items=items,
            total=int(total_row["n"]) if total_row else 0,
            limit=int(limit),
            offset=int(offset),
        )

    def fetch_encounter(self, encounter_id: str) -> dict[str, Any]:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT id, organization_id, location_id, "
                    "patient_identifier, patient_name, provider_name, "
                    "status, patient_id, provider_id, "
                    "external_ref, external_source, "
                    "scheduled_at, started_at, completed_at, created_at "
                    "FROM encounters WHERE id = :id"
                ),
                {"id": int(encounter_id)},
            ).mappings().first()
        if row is None:
            raise AdapterError("encounter_not_found", f"id={encounter_id}")
        return {**dict(row), "_source": "chartnav"}

    def update_encounter_status(
        self, encounter_id: str, new_status: str, *, changed_by: str
    ) -> dict[str, Any]:
        # The HTTP route at POST /encounters/{id}/status is the
        # blessed path — it enforces RBAC + edge validation + audit.
        # The adapter doesn't duplicate that logic; callers reach
        # the adapter path only when the service layer decided to
        # bypass the HTTP surface (e.g. batch tools, scheduled jobs).
        with engine.begin() as conn:
            row = conn.execute(
                sa.text(
                    "UPDATE encounters SET status = :s "
                    "WHERE id = :id RETURNING id, status"
                ),
                {"s": new_status, "id": int(encounter_id)},
            ).mappings().first()
            if row is None:
                raise AdapterError("encounter_not_found", f"id={encounter_id}")
            conn.execute(
                sa.text(
                    "INSERT INTO workflow_events "
                    "(encounter_id, event_type, event_data) "
                    "VALUES (:eid, 'status_changed', :payload)"
                ),
                {
                    "eid": int(encounter_id),
                    "payload": (
                        '{"new_status": "' + new_status + '", '
                        '"changed_by": "' + changed_by + '"}'
                    ),
                },
            )
        return dict(row)

    # --- Documents / notes ------------------------------------------
    def write_note(
        self,
        *,
        encounter_id: str,
        author_email: str,
        body: str,
        note_type: str = "progress",
    ) -> dict[str, Any]:
        # Notes land in workflow_events until a dedicated documents
        # table exists. Keeps the data model compact; still queryable.
        import json

        with engine.begin() as conn:
            row = conn.execute(
                sa.text(
                    "INSERT INTO workflow_events "
                    "(encounter_id, event_type, event_data) "
                    "VALUES (:eid, :etype, :payload) "
                    "RETURNING id"
                ),
                {
                    "eid": int(encounter_id),
                    "etype": f"note_{note_type}",
                    "payload": json.dumps(
                        {"author": author_email, "body": body}
                    ),
                },
            ).mappings().first()
        return {"id": row["id"], "encounter_id": encounter_id}

    # --- Reference data ---------------------------------------------
    def sync_reference_data(self) -> dict[str, int]:
        # No external system to pull from; native reference data is
        # whatever's already in ChartNav's locations + users tables.
        return {"providers": 0, "locations": 0}
