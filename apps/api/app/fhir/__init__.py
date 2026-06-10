"""Phase 87 — FHIR R4 Export Layer.

ChartNav exposes a narrow, read-only FHIR R4 projection of the
structured provider-entered artifacts it already aggregates:

  * Patient            — projected from `patients`
  * Encounter          — projected from `encounters` (+ workflow_events)
  * DocumentReference  — projected from Phase 77 retina visit packet

These adapters never write to FHIR servers, never sync state, never
push to upstream EHRs, and never submit claims. The endpoints are
read-only export surfaces; this is interoperability, not workflow
mutation. ChartNav is not a certified EHR and does not bill or code.
"""

__all__ = []
