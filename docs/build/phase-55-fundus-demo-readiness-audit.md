# Phase 55 Fundus Demo-Readiness Audit

> Scope: demo-readiness audit only. No product UI features were
> implemented. No backend services were changed. No real PHI was
> processed. No media or marketing claims were created.
>
> Original starting point: `origin/main` at `c5959d7`, after Phase 54
> fundus LLM guardrail hardening and Phase 55 AI-assisted fundus
> charting.
>
> **Update (post Phase 55 UX polish, main at `07c4a71`):** the Phase 55
> UX polish PR (#59) landed after this audit was drafted and resolved
> the primary demo blocker called out in § 1 (`FundusChartPanel` not
> mounted in the encounter workspace) plus several "missing tests" and
> "missing docs" items below. Sections flagged with **[Resolved by
> Phase 55 #59]** are kept for historical traceability; the remaining
> findings are still actionable.

## 1. Current UX Summary

The dedicated fundus charting UI exists under `apps/web/src/features/fundus/`:

- `FundusChartPanel` lists saved charts, accepts clinician-entered findings,
  chooses laterality (`OD`, `OS`, `OU`), generates a chart, and loads the
  selected chart into the editor.
- `FundusChartEditor` shows status/laterality, warnings, SVG rendering,
  legend, review, render, and sign actions.
- `FundusChartRenderer` shows a 12-clock retinal diagram with posterior pole,
  equator, ora, labels, laterality, and overlays.
- `FundusChartLegend` summarizes finding types and colors.
- `fundusApi.ts` maps the expected generate, list, get, render, review, sign,
  create, and update endpoints.

**[Resolved by Phase 55 #59]** Original audit finding (now stale): the
panel was not mounted in the encounter workspace; the requested
`apps/web/src/pages/EncounterDetailPage.tsx` did not exist on current
`main`; the Imaging tab mounted only the older `EyeDiagramPanel`.

Current state on `main` at `07c4a71`:
`apps/web/src/ClinicalTabbedWorkspace.tsx:62` now imports
`FundusChartPanel`, and `:990` mounts it as a wide "Fundus charts" card
in the Imaging tab below the OD/OS retinal workbench. The panel is
reachable through the SPA without any URL trick.

## 2. Review/Sign Workflow Clarity

Backend tests cover draft generation, review, attestation-required signing,
and signed-chart update blocking. The UI also includes:

- status badge: `DRAFT`, `REVIEWED`, or `SIGNED`, plus laterality;
- copy for AI-generated charts: "AI-drafted - doctor review required";
- `Mark Reviewed` action while not reviewed and not signed;
- `Sign Chart` action with a browser confirmation attestation;
- signed timestamp display after signing.

Gaps:

- The UI allows `Sign Chart` directly from draft; backend accepts it as long
  as attestation is true. If the desired demo story is review first, then sign,
  the current UX does not force or strongly explain that sequence.
- **[Resolved by Phase 55 #59]** The sign confirmation said the chart
  reflects clinical findings but the screen did not visibly explain that
  signing locks the chart before the user clicks. Phase 55 replaced
  `window.confirm` with an inline purple attestation block whose text
  reads "I attest that I have reviewed this fundus chart and it
  accurately reflects my clinical findings. Signing will lock the chart
  — signed charts are immutable." The `Sign & Lock Chart` button is
  disabled until the checkbox is ticked. Also added a Draft → Reviewed
  → Signed status timeline pill row so the demo story is visible at all
  times.

## 3. Warning Visibility

Warnings are displayed in a yellow warning box above the chart when
`warnings_json` is present. That is demo-useful for missing laterality,
missing clock hour, and unrecognized findings.

Gaps:

- **[Resolved by Phase 55 #59]** Warnings were initialized from the
  first loaded `chart` prop with `useState(chart.warnings_json ?? [])`,
  so a different selected chart loaded into the same editor instance
  could leave the warnings panel stale. Phase 55 added a `useEffect` on
  `[chart.id, chart.warnings_json]` that refreshes the warnings on
  prop change and pinned the behaviour with the regression test
  `warnings refresh when the chart prop changes (bug fix regression)`
  in `apps/web/src/test/FundusChartPanel.test.tsx`.
- The generate response includes `warnings`, but the panel fetches the full
  chart after generation and relies on persisted warnings. That is acceptable
  if API persistence is correct, but a frontend test should pin warning display.
  Phase 55 added `renders warnings list when warnings_json is present` and
  `renders 'no warnings' message instead of hiding the panel when empty`,
  which partly covers this.

## 4. OD/OS and Laterality Clarity

The laterality selector is visible before generation and uses clear labels:

- `OD · Right`
- `OS · Left`
- `OU · Both`

**[Resolved by Phase 55 #59]** The original `<select>` dropdown was
replaced with a radio button group (`role="radiogroup"` with
`aria-checked` per option) so the selection is visible at a glance
rather than hidden behind a dropdown chevron. Test coverage:
`OD/OS/OU selector updates aria-checked state` in
`apps/web/src/test/FundusChartPanel.test.tsx`.

The saved chart list and status badge repeat laterality, and the SVG renders
the laterality in the upper-left of the diagram.

Gaps:

- The diagram does not explain OD/OS orientation or temporal/nasal meaning.
  The docs state the coordinate rule, but a demo operator may need narration.
- If findings text says one laterality and the dropdown says another, the demo
  behavior should be scripted carefully. Backend parser/tests preserve clear
  laterality from findings text, but the UX does not visibly warn about
  dropdown/text conflicts. **Still actionable.**

## 5. Signed Chart Lock/Immutability Clarity

Backend immutability is covered by `test_update_signed_chart_blocked`. The UI
hides render, review, and sign actions once `signed_at` is present and shows a
signed timestamp.

Gaps:

- **[Resolved by Phase 55 #59]** The signed-state message now reads
  "Chart signed · locked" inside a green banner with the explicit
  trailing sentence "Signed charts are immutable." The banner also
  surfaces `signed_at` plus `signed_by_user_id` ("clinician #N").
  Three vitest specs pin this: `signed chart renders a locked banner
  with timestamp + signer`, `signed chart disables edit controls
  (render/review/sign all gone)`, and the panel-level claim sweep
  rejects forbidden phrasings such as `auto-signed`.
- There is no visible "create new version/fork" path in the dedicated fundus
  panel. That may be fine for V1, but demo narration should not imply signed
  charts can be edited in place. **Still actionable.**

## 6. Demo-Safe Sample Findings

Use synthetic, non-patient examples only. Recommended samples:

- `horseshoe tear at 10:30 OD`
- `lattice from 5 to 7 OS near ora`
- `atrophic hole at 2 OD`
- `drusen at macula OU`
- `dot blot hemorrhage at 6 OS`
- `lattice degeneration at 6` - useful to demonstrate missing-laterality
  warning.
- `lattice OD near ora` - useful to demonstrate missing-clock-hour warning.
- `vision is 20/20` - useful to demonstrate no recognized fundus finding.

Avoid names, dates of birth, MRNs, real clinic identifiers, screenshots from
real charts, real fundus photos, or real patient history.

## 7. Claim-Risk Review

Existing public/demo scanners already block broad unsafe claims such as:

- HIPAA compliant/certified;
- OpenAI/GPT/Claude/LLM-powered clinical documentation;
- AI or LLM diagnosis;
- autonomous documentation or clinical reasoning;
- OCT auto-interpretation and autonomous imaging interpretation.

Gap found: current `main` did not directly name fundus-specific positive
overclaims. This branch adds claim checks for:

- fundus image interpretation;
- fundus photo interpretation;
- retinal image interpretation;
- AI interprets fundus;
- autonomous fundus interpretation;
- fundus diagnosis;
- AI-generated fundus diagnosis.

Demo-safe wording:

- "provider-reviewed retinal diagram drafting from clinician-entered findings"
- "structured fundus drawing support"
- "warnings for missing laterality or clock-hour details"

Do not say:

- "AI diagnoses retinal disease"
- "AI interprets fundus photos"
- "OpenAI fundus interpretation"
- "autonomous retinal charting"
- "production LLM fundus workflow"

## 8. Missing Tests

Recommended gaps:

- **[Resolved by Phase 55 #59]** Frontend test that `FundusChartPanel`
  is mounted in the intended encounter tab — covered by the Imaging
  tab's `ctw-card-fundus-charts` test hook in
  `ClinicalTabbedWorkspace.test.tsx` plus the dedicated
  `FundusChartPanel.test.tsx` (20 specs).
- **[Resolved by Phase 55 #59]** Frontend test for generate → warning
  box → select another chart with different warnings: regression test
  `warnings refresh when the chart prop changes (bug fix regression)`.
- **[Resolved by Phase 55 #59]** Frontend test for signed chart state:
  `signed chart renders a locked banner with timestamp + signer` and
  `signed chart disables edit controls (render/review/sign all gone)`.
- **[Resolved by Phase 55 #59]** Frontend test for sign confirmation
  text: `attestation block reads with the immutability + review
  language` plus `sign button is disabled until the attestation
  checkbox is ticked` and `clicking sign with attestation invokes
  signFundusChart`.
- **[Resolved by Phase 55 #59]** Frontend test for OD/OS/OU selector
  and saved-chart laterality display: `OD/OS/OU selector updates
  aria-checked state` plus chip-driven laterality alignment.
- Backend/API test for laterality conflict behavior if dropdown laterality and
  findings-text laterality disagree. **Still actionable.**
- Claim-scanner fixture test that fundus-specific positive claims fail while
  negative-context phrases remain allowed. **Still actionable** — this PR
  adds the forbidden phrases to the three scanners but does not add a
  fixture/golden test that proves the regex covers both positive-fail
  and negative-allowed cases. The vitest claim-safety sweep in
  `FundusChartPanel.test.tsx` partly mitigates this at the DOM level
  but is not a scanner-level fixture.

## 9. Missing Docs

Recommended gaps:

- `docs/build/phase-54-fundus-openai-safety-audit.md` was requested for
  inspection but is missing from current `main`. Treat that as a documentation
  traceability gap unless the Phase 54 audit PR is intentionally separate.
  **Still actionable** — Phase 55 did not add the requested artifact.
- `docs/workflow/fundus-charting.md` describes the safety posture, but a demo
  runbook should separately script what to say on screen. **Still partially
  actionable** — Phase 55 expanded the workflow doc with a "UI workflow
  (Phase 55 polish)" section, a demo-safe sample-findings catalogue,
  warning meanings table, review vs sign table, and a "What the AI does
  *not* do" section. A standalone demo *script* (per § 10 below) is
  still not written.
- Add explicit demo language explaining that signed charts are locked and new
  corrections require a new artifact/version path when available.
  **Still actionable** — Phase 55 added "Signed charts are immutable" UI
  copy but no corrections/version path is described.
- **[Resolved by Phase 55 #59]** "Where this appears in the app" note —
  `docs/workflow/fundus-charting.md` now opens its UI section with:
  "The Fundus Charts panel lives in the Imaging tab of the clinical
  workspace (`ClinicalTabbedWorkspace` → 'Fundus charts' card)."

## 10. Recommended Demo Script Notes

1. Open with scope: "This is fake demo data. ChartNav is drafting a structured
   retinal diagram from clinician-entered findings."
2. Use a clean finding first: `horseshoe tear at 10:30 OD`.
3. Point out OD/OS before generating: "OD is right eye, OS is left eye, OU is
   both."
4. Show warnings intentionally with a second example: `lattice degeneration at
   6`.
5. Say: "Warnings mean the clinician needs to clarify before review/sign."
6. After generation, say: "This is draft support, not a diagnosis."
7. Before signing, read the attestation out loud: provider has reviewed and
   confirms it reflects clinical findings.
8. After signing, say: "Signed charts are locked; corrections should not edit
   the signed artifact in place."
9. Do not mention OpenAI unless asked. If asked, say: "Production fundus
   charting uses the deterministic rule-based path. Any OpenAI assist is
   fake-data/demo-only behind guardrails and not for real PHI."

## 11. Explicit Safety Statements

- Fundus charting is not autonomous diagnosis.
- Fundus charting is not image interpretation.
- Fundus charting is not a production LLM workflow.
- No real PHI should be used in this demo.
- The safe demo posture is provider-reviewed diagram drafting from synthetic,
  clinician-entered findings.

## 12. PR Overlap Assessment

This audit branch should not overlap Claude's implementation PR at the product
code level. It does not edit backend services or fundus product components.
Changes are limited to a docs/build audit artifact and claim-scanner guardrails.

### Post-rebase overlap check (against `main` at `07c4a71`)

After the Phase 55 UX polish PR (#59) merged, this branch was rebased
onto `07c4a71`. The rebase applied cleanly (no conflicts) because:

- This PR only adds files (the audit doc) and appends to existing
  scanner lists; it touches no web source files.
- Phase 55 #59 only touched `apps/web/src/` files and
  `docs/workflow/fundus-charting.md`; it did not modify the three
  scanner scripts.

The seven fundus-specific phrases added here
(`fundus image interpretation`, `fundus photo interpretation`,
`retinal image interpretation`, `AI[- ]interprets? fundus`,
`autonomous fundus interpretation`, `fundus diagnosis`,
`AI[- ]generated fundus diagnosis`) plus the four Spanish phrases on the
website scanner do **not** appear anywhere in the three scanner files
on current `main`, so they are not duplicates and still add unique
coverage. (PR #56 — `[codex] docs: audit fundus and OpenAI safety
gaps` — is open but not yet merged at `07c4a71`; if it lands first,
overlap should be re-checked at that time.)
