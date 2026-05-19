"""Phase 25A / GH-006 — clinical safety eval harness.

Locked-in regression checks against fake fixtures. NOT a substitute
for clinician review. These tests fail loudly the moment the safety
contracts drift, so a future refactor cannot quietly let a banned
phrase or a laterality conflict through.

Three slices:
  1. Note quality linter (``app.services.note_quality``).
  2. Chart conflict surfacer (``app.services.chart_conflicts``).
  3. Audio consent gate (``app.services.consent``).

All inputs are synthetic. No PHI.
"""

from __future__ import annotations

import pytest

from app.services.note_quality import (
    QualityCheckContext,
    run_note_quality_checks,
)
from app.services.chart_context import (
    ChartContext,
    PatientAllergy,
    PatientMedication,
    reset_adapter_for_tests,
    set_adapter_for_tests,
)
from app.services.chart_conflicts import compare

from tests.evals.fixtures import note_drafts as ND


# ---------------------------------------------------------------
# Note-quality safety regressions.
# ---------------------------------------------------------------

def _codes(result) -> list[str]:
    return [f.code for f in result.flags]


def test_eval_clean_retina_OD_passes_safety():
    r = run_note_quality_checks(
        ND.CLEAN_RETINA_OD,
        QualityCheckContext(specialty="retina", encounter_laterality="OD"),
    )
    assert r.has_blocking_flags is False
    # No banned phrase, no laterality conflict.
    codes = _codes(r)
    assert "banned_phrase" not in codes
    assert "laterality_conflict" not in codes
    # Should be ≥ 80% complete on the clean fixture.
    assert r.completeness_percent >= 80


def test_eval_laterality_mismatch_blocks():
    r = run_note_quality_checks(
        ND.LATERALITY_CONFLICT_OS_IN_OD_VISIT,
        QualityCheckContext(specialty="retina", encounter_laterality="OD"),
    )
    assert r.has_blocking_flags is True
    assert "laterality_conflict" in _codes(r)


def test_eval_banned_phrase_warns():
    r = run_note_quality_checks(
        ND.BANNED_AUTODX,
        QualityCheckContext(specialty="retina", encounter_laterality="OD"),
    )
    assert "banned_phrase" in _codes(r)


def test_eval_duplicate_plan_warns():
    r = run_note_quality_checks(
        ND.DUPLICATE_PLAN,
        QualityCheckContext(),
    )
    assert "duplicate_critical_section" in _codes(r)


def test_eval_empty_draft_is_just_info_not_blocking():
    r = run_note_quality_checks(ND.EMPTY, QualityCheckContext())
    assert r.has_blocking_flags is False
    assert _codes(r) == ["draft_empty"]


def test_eval_contradiction_with_extracted_findings_warns():
    r = run_note_quality_checks(
        ND.CONTRADICTION_DRAFT,
        QualityCheckContext(
            specialty="retina",
            extracted_findings=ND.CONTRADICTION_EXTRACTED,
        ),
    )
    assert "contradiction_negation_then_assertion" in _codes(r)


# ---------------------------------------------------------------
# Chart-conflict safety regressions.
# ---------------------------------------------------------------

class _FakeAdapter:
    name = "fake"

    def __init__(self, ctx: ChartContext):
        self._ctx = ctx

    def get_context(self, *, patient_id, organization_id):
        return self._ctx


@pytest.fixture(autouse=True)
def _reset_adapter():
    yield
    reset_adapter_for_tests()


def test_eval_severe_chart_allergy_missing_in_dictation_is_high():
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                allergies=(
                    PatientAllergy(
                        substance="Sulfa",
                        reaction="anaphylaxis",
                        severity="severe",
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1, organization_id=1, dictated_allergies=[]
    )
    allergy = [c for c in report.conflicts if c.kind == "allergy"]
    assert len(allergy) == 1
    assert allergy[0].severity == "high"


def test_eval_med_only_in_dictation_is_low_severity():
    set_adapter_for_tests(
        _FakeAdapter(ChartContext(patient_id=1, organization_id=1))
    )
    report = compare(
        patient_id=1, organization_id=1,
        dictated_medications=["Brimonidine"],
    )
    med = [c for c in report.conflicts if c.kind == "medication"]
    assert len(med) == 1
    assert med[0].severity == "low"


def test_eval_med_match_clears_conflict():
    set_adapter_for_tests(
        _FakeAdapter(
            ChartContext(
                patient_id=1,
                organization_id=1,
                medications=(
                    PatientMedication(
                        name="Latanoprost",
                        dose="0.005%",
                        route="OU qhs",
                        is_active=True,
                    ),
                ),
            )
        )
    )
    report = compare(
        patient_id=1, organization_id=1,
        dictated_medications=["Latanoprost"],
    )
    assert not any(c.kind == "medication" for c in report.conflicts)


# ---------------------------------------------------------------
# Consent gate safety regressions.
# ---------------------------------------------------------------

def test_eval_consent_default_blocks_recording(client):
    # `client` is the seeded test fixture from tests/conftest.py.
    from app.services.consent import is_consent_granted
    assert is_consent_granted(encounter_id=1, organization_id=1) is False


def test_eval_consent_granted_then_revoked_blocks_again(client):
    from app.services.consent import set_consent, is_consent_granted

    set_consent(
        encounter_id=1,
        organization_id=1,
        status="granted",
        method="verbal",
        actor_user_id=2,
        actor_email="clin@chartnav.local",
    )
    assert is_consent_granted(1, 1) is True

    set_consent(
        encounter_id=1,
        organization_id=1,
        status="revoked",
        method="verbal",
        actor_user_id=2,
        actor_email="clin@chartnav.local",
    )
    assert is_consent_granted(1, 1) is False
