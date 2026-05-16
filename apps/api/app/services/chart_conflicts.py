"""Phase 25A / GH-008 — chart-conflict surfacer.

Reads from `chart_context.get_context()` and the structured findings
emitted by the transcript-extraction pipeline; emits a list of
**heuristic** discrepancies between the chart of record and the
dictated visit. The result is informational — the doctor decides what
to do with each item.

Hard rules
----------
- Never calls the LLM.
- Never autonomously diagnoses, treats, orders, refers, codes, or
  bills. It only highlights "chart says X, dictation says Y".
- Read-only. No writes. No audit emissions. The conflict list is
  rendered to the doctor; the act of resolving a conflict is a
  separate human action.
- Heuristic only. False positives are expected and acceptable — the
  doctor reviews. False negatives are also possible; this is a
  hint surface, not a safety check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.services.chart_context import (
    ChartContext,
    PatientAllergy,
    PatientMedication,
    PatientProblem,
    resolve_adapter,
)


# ---------------------------------------------------------------
# Result model.
# ---------------------------------------------------------------

@dataclass(frozen=True)
class ChartConflict:
    kind: str        # "medication" / "allergy" / "problem" / "visit_freshness"
    severity: str    # "info" / "low" / "medium" / "high"
    message: str     # human-readable, no PHI beyond what the doctor dictated
    chart_value: str | None
    dictation_value: str | None


@dataclass(frozen=True)
class ConflictReport:
    patient_id: int
    organization_id: int
    conflicts: tuple[ChartConflict, ...] = field(default_factory=tuple)
    chart_was_empty: bool = False

    def to_dict(self) -> dict:
        return {
            "patient_id": self.patient_id,
            "organization_id": self.organization_id,
            "chart_was_empty": self.chart_was_empty,
            "conflicts": [
                {
                    "kind": c.kind,
                    "severity": c.severity,
                    "message": c.message,
                    "chart_value": c.chart_value,
                    "dictation_value": c.dictation_value,
                }
                for c in self.conflicts
            ],
        }


# ---------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------

def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _names_of(items: Iterable, attr: str) -> set[str]:
    return {_norm(getattr(i, attr, "")) for i in items if _norm(getattr(i, attr, ""))}


# ---------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------

def compare(
    *,
    patient_id: int,
    organization_id: int,
    dictated_medications: list[str] | None = None,
    dictated_allergies: list[str] | None = None,
    dictated_problems: list[str] | None = None,
) -> ConflictReport:
    """Return heuristic differences between the chart of record (via
    `chart_context.resolve_adapter()`) and the structured items the
    transcript extractor pulled out of this visit.

    All inputs default to empty. Missing data on either side surfaces
    as a "not on chart" / "not dictated" hint, never as an autonomous
    decision."""
    adapter = resolve_adapter()
    context = adapter.get_context(
        patient_id=patient_id, organization_id=organization_id
    )

    return _compare_with_context(
        context=context,
        dictated_medications=dictated_medications or [],
        dictated_allergies=dictated_allergies or [],
        dictated_problems=dictated_problems or [],
    )


def _compare_with_context(
    *,
    context: ChartContext,
    dictated_medications: list[str],
    dictated_allergies: list[str],
    dictated_problems: list[str],
) -> ConflictReport:
    conflicts: list[ChartConflict] = []

    chart_meds = {
        _norm(m.name): m for m in context.medications if m.is_active and m.name
    }
    chart_problems = {
        _norm(p.label): p for p in context.problems if p.is_active and p.label
    }
    chart_allergies = {
        _norm(a.substance): a for a in context.allergies if a.substance
    }

    dictated_med_set = {_norm(m) for m in dictated_medications if _norm(m)}
    dictated_prob_set = {_norm(p) for p in dictated_problems if _norm(p)}
    dictated_allergy_set = {_norm(a) for a in dictated_allergies if _norm(a)}

    # Medications.
    for missing in chart_meds.keys() - dictated_med_set:
        conflicts.append(
            ChartConflict(
                kind="medication",
                severity="medium",
                message=(
                    f"Chart lists active medication '{chart_meds[missing].name}'"
                    " but it was not mentioned in the dictation."
                ),
                chart_value=chart_meds[missing].name,
                dictation_value=None,
            )
        )
    for new in dictated_med_set - chart_meds.keys():
        conflicts.append(
            ChartConflict(
                kind="medication",
                severity="low",
                message=(
                    f"Dictation mentions medication '{new}' that is not on the"
                    " chart's active-meds list."
                ),
                chart_value=None,
                dictation_value=new,
            )
        )

    # Allergies — chart says yes, dictation didn't.
    for missing in chart_allergies.keys() - dictated_allergy_set:
        a = chart_allergies[missing]
        sev = (a.severity or "").lower()
        # High-severity chart allergy NOT mentioned in dictation is
        # the loudest "doctor please verify" signal we emit.
        severity = "high" if sev in {"severe", "anaphylaxis"} else "medium"
        conflicts.append(
            ChartConflict(
                kind="allergy",
                severity=severity,
                message=(
                    f"Chart documents allergy to '{a.substance}'"
                    f" (severity={a.severity or 'unknown'})"
                    " but dictation did not reference it."
                ),
                chart_value=a.substance,
                dictation_value=None,
            )
        )
    # Allergy reported in dictation but not on chart.
    for new in dictated_allergy_set - chart_allergies.keys():
        conflicts.append(
            ChartConflict(
                kind="allergy",
                severity="medium",
                message=(
                    f"Dictation references allergy to '{new}' that is not on"
                    " the chart. Confirm before signing."
                ),
                chart_value=None,
                dictation_value=new,
            )
        )

    # Active problems mentioned vs. chart.
    for missing in chart_problems.keys() - dictated_prob_set:
        p = chart_problems[missing]
        conflicts.append(
            ChartConflict(
                kind="problem",
                severity="info",
                message=(
                    f"Chart lists active problem '{p.label}'"
                    " not addressed in the dictation."
                ),
                chart_value=p.label,
                dictation_value=None,
            )
        )

    return ConflictReport(
        patient_id=context.patient_id,
        organization_id=context.organization_id,
        conflicts=tuple(conflicts),
        chart_was_empty=context.is_empty(),
    )
