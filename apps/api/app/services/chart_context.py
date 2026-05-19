"""Phase 25A / GH-007 — chart-context interface + stub adapter.

Background
----------
The transcript-to-note pipeline and the conflict surfacer
(`chart_conflicts.py`, GH-008) both need a read-only view of "what
ChartNav already knows about this patient" — chronic problems,
active medications, allergies, recent visits, etc. — so they can
flag inconsistencies between the dictated note and the chart of
record.

This module defines the **read-only protocol** the rest of the
system depends on, plus a default stub adapter that pulls from the
local ChartNav tables. A future EHR-integrated build can ship a
different adapter (Athena, eClinicalWorks, Epic) that satisfies the
same protocol without changing call sites.

Hard rules
----------
- Read-only. No writes. No side effects. No emit_audit_event.
- Org-scoped at every entry. Cross-org always returns empty.
- Never reads transcripts or note bodies — only structured chart
  data already extracted into ChartNav's tables.
- Never calls the LLM. The conflict surfacer compares strings/values
  the doctor said vs. what the chart says. Heuristics only.
- Never autonomously diagnoses, treats, codes, bills, refers, or
  acts. This module surfaces facts; the doctor decides.

Phase 25A ships the **interface + a local-DB stub**. A real EHR
adapter is intentionally deferred to Phase 25B/26.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PatientProblem:
    """A chronic condition / active problem on the chart of record."""
    code: str | None       # ICD-10 or local identifier (optional)
    label: str             # human-readable, e.g. "Type 2 diabetes"
    onset_date: str | None # ISO date or None if unknown
    is_active: bool


@dataclass(frozen=True)
class PatientMedication:
    """An active medication on the chart of record."""
    name: str              # drug name, e.g. "Metformin"
    dose: str | None       # "500 mg", may be None
    route: str | None      # "PO", "topical", etc.
    is_active: bool


@dataclass(frozen=True)
class PatientAllergy:
    substance: str
    reaction: str | None
    severity: str | None   # "mild" / "moderate" / "severe" / None


@dataclass(frozen=True)
class PatientVisitSnapshot:
    encounter_id: int
    visited_at: _dt.datetime
    summary: str | None    # short, no PHI in body


@dataclass(frozen=True)
class ChartContext:
    """The aggregate view returned by an adapter."""
    patient_id: int
    organization_id: int
    problems: tuple[PatientProblem, ...] = field(default_factory=tuple)
    medications: tuple[PatientMedication, ...] = field(default_factory=tuple)
    allergies: tuple[PatientAllergy, ...] = field(default_factory=tuple)
    recent_visits: tuple[PatientVisitSnapshot, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return (
            not self.problems
            and not self.medications
            and not self.allergies
            and not self.recent_visits
        )


class ChartContextAdapter(Protocol):
    """Adapters wired by `app.integrations` implement this Protocol.
    Implementations MUST be read-only and org-scoped."""

    name: str

    def get_context(
        self,
        *,
        patient_id: int,
        organization_id: int,
    ) -> ChartContext: ...


# ---------------------------------------------------------------
# Default stub adapter — local DB only.
# ---------------------------------------------------------------

class LocalDBChartContextAdapter:
    """Reads from ChartNav's own tables only.

    Today the ChartNav schema does not carry a problem list / med
    list / allergy list / chronic conditions table. The fields below
    return empty tuples until those tables land. The Phase 22 patient
    table does carry basic demographics; we expose only the recent-
    visits snapshot for now.

    The point of shipping this stub is the **interface**: callers can
    integrate against `ChartContextAdapter` now, and the day the
    structured-problem-list table ships, only this adapter changes.
    """

    name = "local_db_stub"

    def get_context(
        self,
        *,
        patient_id: int,
        organization_id: int,
    ) -> ChartContext:
        from sqlalchemy import text
        from app.db import transaction

        # Verify the patient is in the caller's org. Cross-org returns
        # an empty context — never an existence-leaking error.
        with transaction() as conn:
            owner = conn.execute(
                text(
                    "SELECT organization_id FROM patients WHERE id = :pid"
                ),
                {"pid": patient_id},
            ).mappings().first()
            if owner is None or owner["organization_id"] != organization_id:
                return ChartContext(
                    patient_id=patient_id,
                    organization_id=organization_id,
                )

            # Recent visits — last 5 encounters for this patient.
            rows = conn.execute(
                text(
                    "SELECT id, created_at, status "
                    "FROM encounters "
                    "WHERE patient_id = :pid AND organization_id = :oid "
                    "ORDER BY created_at DESC LIMIT 5"
                ),
                {"pid": patient_id, "oid": organization_id},
            ).mappings().all()

        visits: list[PatientVisitSnapshot] = []
        for r in rows:
            ts = r["created_at"]
            if isinstance(ts, str):
                try:
                    parsed = _dt.datetime.fromisoformat(
                        ts.replace("Z", "+00:00")
                    )
                except ValueError:
                    try:
                        parsed = _dt.datetime.strptime(
                            ts.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        continue
            else:
                parsed = ts
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=_dt.timezone.utc)
            visits.append(
                PatientVisitSnapshot(
                    encounter_id=int(r["id"]),
                    visited_at=parsed,
                    summary=f"status={r['status']}",
                )
            )

        return ChartContext(
            patient_id=patient_id,
            organization_id=organization_id,
            problems=tuple(),
            medications=tuple(),
            allergies=tuple(),
            recent_visits=tuple(visits),
        )


# ---------------------------------------------------------------
# Module-level resolver.
# ---------------------------------------------------------------
# Kept intentionally simple. The conflict surfacer + future EHR
# adapter call `resolve_adapter()` and never reach for a concrete
# class directly.

_ADAPTER: ChartContextAdapter = LocalDBChartContextAdapter()


def resolve_adapter() -> ChartContextAdapter:
    return _ADAPTER


def set_adapter_for_tests(adapter: ChartContextAdapter) -> None:
    """Test seam — swap the adapter in unit tests without touching
    module-level state from a fixture file."""
    global _ADAPTER
    _ADAPTER = adapter


def reset_adapter_for_tests() -> None:
    global _ADAPTER
    _ADAPTER = LocalDBChartContextAdapter()
