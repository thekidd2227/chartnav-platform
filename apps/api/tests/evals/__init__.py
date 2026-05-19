"""Phase 25A / GH-006 — clinical safety eval harness.

These tests are NOT a substitute for clinician review. They are
deterministic regression checks against synthetic fake fixtures
(``tests/evals/fixtures/``) that lock in the safety contracts ChartNav
relies on:

  - The note-quality linter (``app.services.note_quality``) keeps
    flagging the cases we care about (banned phrases, contradictions,
    laterality conflicts).
  - The chart-conflict surfacer (``app.services.chart_conflicts``)
    keeps flagging chart-vs-dictation gaps with the expected severity.
  - The audio-consent gate (``app.services.consent``) keeps refusing
    recording for non-granted states.

No PHI lives here. Every fixture is invented, every name is fictional,
every condition is generic.
"""
