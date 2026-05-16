"""Phase 25A / GH-007 + GH-008 — chart context & conflict surfacer.

Coverage:
- Local-DB adapter returns the right org + skeleton fields.
- Cross-org patient lookup returns an empty context, no error.
- Compare flags chart→dictation gaps (missing meds / allergies).
- Severe chart-allergy NOT mentioned in dictation → severity=high.
- New dictated medication not on chart → severity=low.
- `chart_was_empty` is True when the adapter has nothing.
"""

from __future__ import annotations

import pytest

from app.services.chart_context import (
    ChartContext,
    LocalDBChartContextAdapter,
    PatientAllergy,
    PatientMedication,
    PatientProblem,
    reset_adapter_for_tests,
    set_adapter_for_tests,
)
from app.services.chart_conflicts import compare


# ---------------------------------------------------------------
# Local-DB adapter.
# ---------------------------------------------------------------

def test_local_adapter_returns_empty_for_unknown_patient(client):
    adapter = LocalDBChartContextAdapter()
    ctx = adapter.get_context(patient_id=999_999, organization_id=1)
    assert ctx.patient_id == 999_999
    assert ctx.organization_id == 1
    assert ctx.is_empty()


def test_local_adapter_is_org_scoped(client):
    """A patient in org 1 must be invisible to an adapter call from org 2."""
    # Seeded patients live in org 1.
    adapter = LocalDBChartContextAdapter()
    ctx_org2 = adapter.get_context(patient_id=1, organization_id=2)
    # Even if the patient exists in org 1, asking from org 2 must
    # return an empty context (no existence leak).
    assert ctx_org2.is_empty()


def test_local_adapter_surfaces_recent_visits(client):
    """Seeded encounters in org 1 are visible to the org-1 adapter."""
    adapter = LocalDBChartContextAdapter()
    # The seed script links encounters to patient_id 1 in org 1.
    ctx = adapter.get_context(patient_id=1, organization_id=1)
    # Recent visits is the populated field on the stub.
    assert len(ctx.recent_visits) >= 1
    for v in ctx.recent_visits:
        assert v.encounter_id > 0
        assert v.visited_at is not None


# ---------------------------------------------------------------
# Conflict surfacer.
# ---------------------------------------------------------------

class _FakeAdapter:
    name = "fake"

    def __init__(self, context: ChartContext):
        self._ctx = context

    def get_context(self, *, patient_id: int, organization_id: int) -> ChartContext:
        return self._ctx


@pytest.fixture(autouse=True)
def _reset_adapter():
    yield
    reset_adapter_for_tests()


def test_compare_flags_chart_med_not_dictated(client):
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                medications=(
                    PatientMedication(
                        name="Metformin",
                        dose="500 mg",
                        route="PO",
                        is_active=True,
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1,
        organization_id=1,
        dictated_medications=[],  # doctor didn't mention any meds
    )
    kinds = {c.kind for c in report.conflicts}
    assert "medication" in kinds
    msg = next(c for c in report.conflicts if c.kind == "medication").message
    assert "Metformin" in msg


def test_compare_flags_new_dictated_med_not_on_chart(client):
    set_adapter_for_tests(_FakeAdapter(ChartContext(patient_id=1, organization_id=1)))
    report = compare(
        patient_id=1,
        organization_id=1,
        dictated_medications=["Latanoprost"],
    )
    new = [c for c in report.conflicts if c.kind == "medication"]
    assert len(new) == 1
    assert new[0].severity == "low"
    assert new[0].dictation_value == "latanoprost"


def test_compare_severe_chart_allergy_missing_in_dictation_is_high(client):
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                allergies=(
                    PatientAllergy(
                        substance="Penicillin",
                        reaction="anaphylaxis",
                        severity="severe",
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1,
        organization_id=1,
        dictated_allergies=[],
    )
    allergy_conflicts = [c for c in report.conflicts if c.kind == "allergy"]
    assert len(allergy_conflicts) == 1
    assert allergy_conflicts[0].severity == "high"
    assert "Penicillin" in allergy_conflicts[0].message


def test_compare_problem_only_on_chart_is_info_severity(client):
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                problems=(
                    PatientProblem(
                        code=None,
                        label="Type 2 diabetes",
                        onset_date=None,
                        is_active=True,
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1,
        organization_id=1,
        dictated_problems=[],
    )
    prob_conflicts = [c for c in report.conflicts if c.kind == "problem"]
    assert len(prob_conflicts) == 1
    assert prob_conflicts[0].severity == "info"


def test_compare_returns_empty_when_chart_and_dictation_match(client):
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                medications=(
                    PatientMedication(
                        name="Metformin", dose=None, route=None, is_active=True
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1,
        organization_id=1,
        dictated_medications=["Metformin"],
    )
    assert all(c.kind != "medication" for c in report.conflicts)


def test_compare_chart_was_empty_flag(client):
    set_adapter_for_tests(_FakeAdapter(ChartContext(patient_id=1, organization_id=1)))
    report = compare(patient_id=1, organization_id=1)
    assert report.chart_was_empty is True


def test_compare_serializes_to_dict_safely(client):
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                problems=(
                    PatientProblem(
                        code="E11.9",
                        label="Type 2 diabetes",
                        onset_date=None,
                        is_active=True,
                    ),
                ),
            )
        )
    )
    payload = compare(
        patient_id=1, organization_id=1, dictated_problems=[]
    ).to_dict()
    assert payload["patient_id"] == 1
    assert isinstance(payload["conflicts"], list)
    assert payload["conflicts"][0]["chart_value"] == "Type 2 diabetes"
    assert payload["conflicts"][0]["dictation_value"] is None
