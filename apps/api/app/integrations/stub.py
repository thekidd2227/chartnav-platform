"""Stub clinical-system adapter for integrated modes without a vendor.

Honest placeholder: boots, exposes the protocol, and behaves
predictably so the service layer can be exercised end-to-end without
a real Epic/Cerner/FHIR back-end wired up.

- `writes_allowed=False` (integrated_readthrough): all write methods
  raise `AdapterNotSupported` with a clear reason. Read methods
  return canned rows so the UI can render an integrated deployment.
- `writes_allowed=True` (integrated_writethrough): writes are
  recorded in an in-process list (inspectable in tests) but not
  persisted anywhere durable. The stub never pretends the write
  reached a real external system.

A real vendor adapter replaces this by registering under its own key
in `app/integrations/__init__.py::_VENDOR_ADAPTERS`.
"""

from __future__ import annotations

from typing import Any

from app.integrations.base import (
    AdapterError,
    AdapterInfo,
    AdapterNotSupported,
    SourceOfTruth,
)


def _info(writes_allowed: bool) -> AdapterInfo:
    return AdapterInfo(
        key="stub",
        display_name="Stub (integrated)",
        description=(
            "Honest placeholder adapter for integrated deployments "
            "before a vendor connector is wired. Reads return canned "
            "shape; writes are " + (
                "recorded in-process but not persisted externally."
                if writes_allowed
                else "rejected until a real adapter is installed."
            )
        ),
        supports_patient_read=True,
        supports_patient_write=writes_allowed,
        supports_encounter_read=True,
        supports_encounter_write=writes_allowed,
        supports_document_write=writes_allowed,
        source_of_truth={
            "organization": SourceOfTruth.MIRRORED,
            "location": SourceOfTruth.MIRRORED,
            "user": SourceOfTruth.CHARTNAV,
            "encounter": SourceOfTruth.EXTERNAL,
            "workflow_event": SourceOfTruth.CHARTNAV,
            "patient": SourceOfTruth.EXTERNAL,
            "document": SourceOfTruth.EXTERNAL,
        },
    )


class StubClinicalSystemAdapter:
    """Placeholder adapter for integrated modes."""

    def __init__(self, *, writes_allowed: bool) -> None:
        self._writes_allowed = writes_allowed
        self._info = _info(writes_allowed)
        # Inspectable write log for tests / debugging.
        self.recorded_writes: list[dict[str, Any]] = []

    @property
    def info(self) -> AdapterInfo:
        return self._info

    # --- Patients ---------------------------------------------------
    def fetch_patient(self, patient_id: str) -> dict[str, Any]:
        if not patient_id:
            raise AdapterError("invalid_argument", "patient_id is required")
        return {
            "id": patient_id,
            "source": "stub",
            "display_name": f"Stub Patient {patient_id}",
        }

    def search_patients(
        self, *, query: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        if not query:
            return []
        return [
            {
                "id": f"stub-{query}-{i}",
                "source": "stub",
                "display_name": f"Stub match {i} for {query!r}",
            }
            for i in range(min(limit, 3))
        ]

    # --- Encounters -------------------------------------------------
    def fetch_encounter(self, encounter_id: str) -> dict[str, Any]:
        return {
            "id": encounter_id,
            "source": "stub",
            "status": "in_progress",
            "provider_name": "Stub Provider",
        }

    def update_encounter_status(
        self, encounter_id: str, new_status: str, *, changed_by: str
    ) -> dict[str, Any]:
        if not self._writes_allowed:
            raise AdapterNotSupported(
                "stub adapter in read-through mode cannot update "
                "encounter status; wire a vendor adapter or switch to "
                "integrated_writethrough"
            )
        record = {
            "op": "update_encounter_status",
            "encounter_id": encounter_id,
            "new_status": new_status,
            "changed_by": changed_by,
        }
        self.recorded_writes.append(record)
        return {"id": encounter_id, "status": new_status, "source": "stub"}

    # --- Documents / notes ------------------------------------------
    def write_note(
        self,
        *,
        encounter_id: str,
        author_email: str,
        body: str,
        note_type: str = "progress",
    ) -> dict[str, Any]:
        if not self._writes_allowed:
            raise AdapterNotSupported(
                "stub adapter in read-through mode cannot write notes"
            )
        record = {
            "op": "write_note",
            "encounter_id": encounter_id,
            "author_email": author_email,
            "body": body,
            "note_type": note_type,
        }
        self.recorded_writes.append(record)
        return {
            "id": f"stub-note-{len(self.recorded_writes)}",
            "encounter_id": encounter_id,
        }

    # --- Reference data ---------------------------------------------
    def sync_reference_data(self) -> dict[str, int]:
        # Honest: no real external system to sync from.
        return {"providers": 0, "locations": 0}
