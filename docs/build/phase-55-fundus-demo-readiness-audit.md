# Phase 55 Fundus Demo-Readiness Audit

> Scope: demo-readiness audit only. No product UI features were
> implemented. No backend services were changed. No real PHI was
> processed. No media or marketing claims were created.
>
> Starting point: `origin/main` at `c5959d7`, after Phase 54 fundus LLM
> guardrail hardening and Phase 55 AI-assisted fundus charting.

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

Demo blocker: the panel appears unmounted in the actual encounter workspace.
`rg` found no imports/usages of `FundusChartPanel` outside the fundus feature
folder, and the requested `apps/web/src/pages/EncounterDetailPage.tsx` does
not exist on current `main`. The current encounter body is rendered by
`App.tsx` -> `ClinicalTabbedWorkspace.tsx`; the Imaging tab still mounts the
older `EyeDiagramPanel`, not `FundusChartPanel`.

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
- The sign confirmation says the chart reflects clinical findings, which is
  good, but the screen does not visibly explain that signing locks the chart
  before the user clicks.

## 3. Warning Visibility

Warnings are displayed in a yellow warning box above the chart when
`warnings_json` is present. That is demo-useful for missing laterality,
missing clock hour, and unrecognized findings.

Gaps:

- Warnings are initialized from the first loaded `chart` prop with
  `useState(chart.warnings_json ?? [])`; if a different selected chart is
  loaded into the same editor instance, warnings may not refresh unless React
  remounts the component. This is a UX regression risk to test.
- The generate response includes `warnings`, but the panel fetches the full
  chart after generation and relies on persisted warnings. That is acceptable
  if API persistence is correct, but a frontend test should pin warning display.

## 4. OD/OS and Laterality Clarity

The laterality selector is visible before generation and uses clear labels:

- `OD (Right)`
- `OS (Left)`
- `OU (Both)`

The saved chart list and status badge repeat laterality, and the SVG renders
the laterality in the upper-left of the diagram.

Gaps:

- The diagram does not explain OD/OS orientation or temporal/nasal meaning.
  The docs state the coordinate rule, but a demo operator may need narration.
- If findings text says one laterality and the dropdown says another, the demo
  behavior should be scripted carefully. Backend parser/tests preserve clear
  laterality from findings text, but the UX does not visibly warn about
  dropdown/text conflicts.

## 5. Signed Chart Lock/Immutability Clarity

Backend immutability is covered by `test_update_signed_chart_blocked`. The UI
hides render, review, and sign actions once `signed_at` is present and shows a
signed timestamp.

Gaps:

- The signed-state message does not explicitly say "locked" or "immutable".
- There is no visible "create new version/fork" path in the dedicated fundus
  panel. That may be fine for V1, but demo narration should not imply signed
  charts can be edited in place.

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

- Frontend test that `FundusChartPanel` is mounted in the intended encounter
  tab once product scope approves it.
- Frontend test for generate -> warning box -> select another chart with
  different warnings, to catch stale warning state.
- Frontend test for signed chart state: action buttons hidden and locked copy
  displayed.
- Frontend test for sign confirmation text.
- Frontend test for OD/OS/OU selector and saved-chart laterality display.
- Backend/API test for laterality conflict behavior if dropdown laterality and
  findings-text laterality disagree.
- Claim-scanner fixture test that fundus-specific positive claims fail while
  negative-context phrases remain allowed.

## 9. Missing Docs

Recommended gaps:

- `docs/build/phase-54-fundus-openai-safety-audit.md` was requested for
  inspection but is missing from current `main`. Treat that as a documentation
  traceability gap unless the Phase 54 audit PR is intentionally separate.
- `docs/workflow/fundus-charting.md` describes the safety posture, but a demo
  runbook should separately script what to say on screen.
- Add explicit demo language explaining that signed charts are locked and new
  corrections require a new artifact/version path when available.
- Add a short "where this appears in the app" note after the panel is mounted,
  because the current encounter tabbed workspace does not appear to expose the
  dedicated fundus charting panel.

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
