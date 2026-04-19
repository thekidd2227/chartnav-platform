"""Adapter contract for external EHR/EMR clinical systems.

Everything ChartNav needs from a foreign clinical system goes through
this protocol. Core services (encounters, workflow events, coding,
documents) talk to the protocol — never directly to a vendor SDK, a
DB driver, or an HTTP client.

The protocol is deliberately small. It expresses the operations
ChartNav actually performs today. Growing it is cheap; shrinking it
is hard. Resist adding methods "just in case" — add them when a real
caller exists.

Capability flags (`supports_*`) are the honest seam: an adapter can
admit it cannot do something, and the service layer can surface a
clean error to callers instead of letting the request fall off a
cliff. This is how integrated modes stay honest before a full vendor
integration lands.

Source-of-truth enum: each domain object declares who owns it when
the adapter runs — ChartNav or the external system. The frontend
surfaces this to operators so the semantics of a given install are
never implicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SourceOfTruth(str, Enum):
    """Who owns the canonical copy of a given object."""

    CHARTNAV = "chartnav"
    EXTERNAL = "external"
    MIRRORED = "mirrored"   # read from external, cached in ChartNav
    NOT_SUPPORTED = "not_supported"


@dataclass(frozen=True)
class EncounterListResult:
    """Paged encounter list returned by `list_encounters`."""
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class AdapterInfo:
    """Metadata an adapter exposes about itself.

    Surfaced at `GET /platform` so operators can see exactly what the
    running deployment thinks it is. Intentionally tiny.
    """
    key: str                 # registry key, e.g. "native", "stub", "fhir"
    display_name: str        # human-readable label for the UI
    description: str         # one-paragraph operator-facing summary
    supports_patient_read: bool
    supports_patient_write: bool
    supports_encounter_read: bool
    supports_encounter_write: bool
    supports_document_write: bool
    # Phase 26 — write-path groundwork for signed notes.
    # `supports_document_transmit` means the adapter can accept a
    # fully-packaged FHIR DocumentReference (from
    # `app.services.note_artifact.render_fhir_document_reference`) and
    # deliver it to a real external system. This is orthogonal to the
    # older `supports_document_write` (which was the free-text
    # `write_note(body=...)` seam). New vendor adapters should
    # implement `transmit_artifact` rather than `write_note`.
    supports_document_transmit: bool = False
    source_of_truth: dict[str, SourceOfTruth] = None  # type: ignore[assignment]


@dataclass(frozen=True)
class TransmitResult:
    """Outcome of a single artifact-transmission attempt.

    Adapters return this from `transmit_artifact`. The service layer
    persists it into `note_transmissions` unchanged so the audit trail
    reflects exactly what the adapter saw. Not an exception path — a
    failed transmission is a normal, persisted business outcome.

    Fields:
    - ``status``: ``succeeded`` | ``failed`` | ``unsupported``.
      ``unsupported`` is allowed only when the adapter declined to
      attempt (e.g. a read-only adapter); prefer raising
      `AdapterNotSupported` at the protocol boundary when possible.
    - ``response_code``: HTTP status if the adapter is HTTP-based.
    - ``response_snippet``: up to 1024 chars of the response body for
      the audit trail. Adapters should truncate themselves; the
      service layer also truncates defensively.
    - ``remote_id``: whatever id the remote system echoed back. FHIR
      adapters surface `Location:` header or the resource's `id`.
    - ``error_code`` / ``error_reason``: populated on ``failed``.
    """

    status: str
    response_code: int | None = None
    response_snippet: str | None = None
    remote_id: str | None = None
    error_code: str | None = None
    error_reason: str | None = None


@runtime_checkable
class ClinicalSystemAdapter(Protocol):
    """Everything ChartNav's core services need from a clinical system.

    Methods return domain-shaped dicts (JSON-serialisable) rather than
    ORM rows. That keeps the adapter boundary clean: a vendor adapter
    never has to know about SQLAlchemy, and the native adapter never
    has to know about FHIR.

    Methods raise `AdapterNotSupported` when the adapter genuinely
    cannot perform the operation. They raise `AdapterError` for
    transport / auth / validation failures. Callers that want to
    degrade gracefully check `supports_*` first.
    """

    @property
    def info(self) -> AdapterInfo: ...

    # --- Patients ---------------------------------------------------
    def fetch_patient(self, patient_id: str) -> dict[str, Any]: ...
    def search_patients(
        self, *, query: str, limit: int = 25
    ) -> list[dict[str, Any]]: ...

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
    ) -> "EncounterListResult":
        """Org-scoped encounter list.

        Returns a paged result object the HTTP layer can emit as
        `X-Total-Count`/`X-Limit`/`X-Offset` headers. Every row is in
        ChartNav's internal encounter shape (`id`, `status`,
        `provider_name`, `patient_identifier`, `patient_name`, ...) plus
        a `_source` tag naming where the row came from (`chartnav` or
        the vendor key, e.g. `fhir`).
        """
        ...

    def fetch_encounter(self, encounter_id: str) -> dict[str, Any]: ...
    def update_encounter_status(
        self, encounter_id: str, new_status: str, *, changed_by: str
    ) -> dict[str, Any]: ...

    # --- Documents / notes ------------------------------------------
    def write_note(
        self,
        *,
        encounter_id: str,
        author_email: str,
        body: str,
        note_type: str = "progress",
    ) -> dict[str, Any]: ...

    # --- Signed-artifact transmission (phase 26) --------------------
    def transmit_artifact(
        self,
        *,
        artifact: dict[str, Any],
        document_reference: dict[str, Any],
        note_version_id: int,
        encounter_external_ref: str | None,
    ) -> "TransmitResult":
        """Hand a signed-note DocumentReference to the external system.

        Contract:
        - ``artifact`` is the canonical ChartNav envelope from phase 25
          (``chartnav.v1.json`` shape). Adapters that don't need the
          envelope can ignore it; provenance-aware adapters surface
          the content hash when logging.
        - ``document_reference`` is the FHIR R4 DocumentReference
          resource built by
          ``app.services.note_artifact.render_fhir_document_reference``.
          Vendor adapters that speak a different wire format MUST
          translate it themselves — this method does not re-serialize.
        - ``note_version_id`` is ChartNav's internal id; pass it
          through as metadata so the remote system can tie back.
        - ``encounter_external_ref`` is the remote encounter id if
          the encounter was externally sourced; ``None`` for native
          encounters. Vendor-specific adapters decide whether to
          accept transmission without one.

        Adapters that cannot transmit raise ``AdapterNotSupported``.
        Adapters that attempted and failed return a ``TransmitResult``
        with ``status='failed'`` and populated ``error_*`` fields.
        """
        ...

    # --- Provider / location references -----------------------------
    def sync_reference_data(self) -> dict[str, int]:
        """Refresh provider/location reference caches.

        Returns a summary dict `{"providers": N, "locations": M}` of
        how many rows were inspected/updated. Native adapter returns
        zeros because there's nothing to sync; a vendor adapter pulls
        from the external system.
        """
        ...


class AdapterError(RuntimeError):
    """Generic adapter-layer failure.

    Translated by the service layer into the standard error envelope
    `{error_code, reason}`.
    """

    def __init__(self, error_code: str, reason: str):
        super().__init__(f"{error_code}: {reason}")
        self.error_code = error_code
        self.reason = reason


class AdapterNotSupported(AdapterError):
    """The adapter deliberately cannot perform this operation.

    Surfaced with a specific error code so the UI can fall back to a
    documented alternative (e.g. "cannot write note through this
    connector; record it as a ChartNav-native workflow_event").
    """

    def __init__(self, reason: str):
        super().__init__("adapter_not_supported", reason)
