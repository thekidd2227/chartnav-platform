"""Phase 25A / GH-004 — backend mirror of noteQualityChecks tests.

Mirrors the most important assertions from
``apps/web/src/test/noteQualityChecks.test.ts`` so server-side gates
behave the same way as the in-browser linter.

Specifically covers:
- empty draft → ``draft_empty`` info flag, completeness 0
- missing critical sections → ``missing_critical_element`` warns
- laterality conflict → ``laterality_conflict`` block
- banned phrase → ``banned_phrase`` warn
- duplicate section header → ``duplicate_critical_section`` warn
- contradiction (extracted vs draft) → ``contradiction_*`` warn
- completeness scoring climbs as sections are added
- specialty-aware section list
"""

from __future__ import annotations

from app.services.note_quality import (
    QualityCheckContext,
    run_note_quality_checks,
    severity_counts,
)


def _codes(result):
    return [f.code for f in result.flags]


def test_empty_draft_flags_draft_empty_only():
    r = run_note_quality_checks("", QualityCheckContext())
    assert r.completeness_percent == 0
    assert r.has_blocking_flags is False
    codes = _codes(r)
    assert codes == ["draft_empty"]


def test_blank_whitespace_draft_counts_as_empty():
    r = run_note_quality_checks("   \n   \n", QualityCheckContext())
    assert _codes(r) == ["draft_empty"]


def test_missing_sections_emit_warn_flags():
    # Generic specialty requires CC / History / Exam / Assessment / Plan.
    r = run_note_quality_checks(
        "Chief complaint: blurry vision OS.\n", QualityCheckContext()
    )
    codes = _codes(r)
    # 4 of 5 sections missing.
    missing = [c for c in codes if c == "missing_critical_element"]
    assert len(missing) >= 3
    assert r.completeness_percent < 100


def test_full_general_note_hits_high_completeness():
    text = (
        "Chief complaint: blurry vision OS x 3 days.\n"
        "History: 65yo F.\n"
        "Exam: VA OS 20/40.\n"
        "Assessment: posterior vitreous detachment OS.\n"
        "Plan: 30-day follow-up; return precautions reviewed.\n"
    )
    r = run_note_quality_checks(text, QualityCheckContext(specialty="general"))
    assert r.completeness_percent == 100
    # No missing-section warns.
    assert "missing_critical_element" not in _codes(r)


def test_laterality_conflict_blocks_when_encounter_is_OD_but_draft_says_OS():
    text = (
        "Chief complaint: redness OS\n"
        "History: started this morning\n"
        "Exam: OS injection\n"
        "Assessment: conjunctivitis\n"
        "Plan: drops\n"
    )
    r = run_note_quality_checks(
        text, QualityCheckContext(encounter_laterality="OD")
    )
    assert r.has_blocking_flags is True
    assert "laterality_conflict" in _codes(r)


def test_laterality_OU_anchor_clears_conflict():
    text = (
        "Chief complaint: itch OU\n"
        "History: 2 days\n"
        "Exam: lids clear bilateral\n"
        "Assessment: allergic conjunctivitis\n"
        "Plan: artificial tears\n"
    )
    r = run_note_quality_checks(
        text, QualityCheckContext(encounter_laterality="OD")
    )
    # OU / bilateral anchor present — no laterality_conflict.
    assert "laterality_conflict" not in _codes(r)


def test_banned_phrase_flag():
    text = (
        "Chief complaint: visual decline OD\n"
        "History: 1 week\n"
        "Exam: OCT consistent\n"
        "Assessment: autonomous diagnosis pending\n"
        "Plan: follow up\n"
    )
    r = run_note_quality_checks(text, QualityCheckContext())
    codes = _codes(r)
    assert "banned_phrase" in codes


def test_duplicate_section_header_flag():
    text = (
        "Chief complaint: redness\n"
        "History: 2 days\n"
        "Exam: ok\n"
        "Assessment: viral conjunctivitis\n"
        "Plan: drops\n"
        "Plan: f/u 1 week\n"  # duplicate header
    )
    r = run_note_quality_checks(text, QualityCheckContext())
    codes = _codes(r)
    assert "duplicate_critical_section" in codes


def test_contradiction_extracted_negates_draft_asserts():
    text = (
        "Chief complaint: floaters OS\n"
        "History: 3 days\n"
        "Exam: peripheral retinal detachment noted\n"
        "Assessment: retinal detachment OS\n"
        "Plan: urgent retina referral\n"
    )
    extracted = "No retinal detachment on exam."
    r = run_note_quality_checks(
        text,
        QualityCheckContext(extracted_findings=extracted, specialty="retina"),
    )
    codes = _codes(r)
    assert "contradiction_negation_then_assertion" in codes


def test_specialty_retina_requires_imaging_review():
    """Retina specialty's required-sections list adds "Imaging review";
    a draft missing that section should surface the warn flag."""
    text = (
        "Chief complaint: floaters OS\n"
        "History: 3 days\n"
        "Exam: PVD OS\n"
        "Assessment: PVD\n"
        "Plan: re-exam in 2 weeks\n"
    )
    r = run_note_quality_checks(
        text, QualityCheckContext(specialty="retina")
    )
    codes = _codes(r)
    assert "missing_critical_element" in codes


def test_severity_counts_helper_returns_dict_of_three_keys():
    r = run_note_quality_checks("", QualityCheckContext())
    counts = severity_counts(r)
    assert set(counts.keys()) == {"block", "warn", "info"}
    assert counts["info"] >= 1
    assert counts["block"] == 0


def test_result_serialises_to_dict_safely():
    r = run_note_quality_checks(
        "Plan: keep going\n",
        QualityCheckContext(),
    )
    payload = r.to_dict()
    assert isinstance(payload["flags"], list)
    assert "completeness_percent" in payload
    assert "has_blocking_flags" in payload
