# Phase 56 Next QA Backlog

> Scope: read-only style QA backlog after recent fundus charting,
> OpenAI fake-data adapter, and Phase 55 UX polish work.
>
> Constraints honored: no product features implemented, no backend
> services edited, no frontend product components edited, no API routes
> edited, no deployment, no real PHI, and no active Claude branch touched.

## 1. Current Product State Summary

ChartNav main is at `07c4a71` with Phase 55 UX polish merged.

- Fundus charting is mounted in the clinical workspace Imaging tab under a
  "Fundus charts" card.
- The default fundus generation path remains `rule_based_v1`, a deterministic
  parser over clinician-entered findings text.
- The UI now includes a safety banner, OD/OS/OU selector, fake-data demo chips,
  saved-chart list, preview column, warning panel, status timeline, review
  action, explicit sign attestation, and signed/locked state.
- Backend tests cover basic parse warnings, SVG render, list/generate/retrieve,
  manual create, update, render, review, attestation-required signing,
  signed-chart update blocking, and cross-org access denial.
- The OpenAI adapter remains fake-data/demo-only, never default, guarded by env
  checks, per-request fake-data and provider-review checks, mocked transport
  tests, and key-leak regression tests.
- Phase 54 added a narrow fundus OpenAI assist seam, but docs state the
  production default is still `rule_based_v1` and real PHI must not use the
  assist path.
- `docs/build/phase-55-fundus-demo-readiness-audit.md` is not present on the
  current main branch; treat that as traceability context, not a runtime issue.

## 2. Highest-Risk Regression Areas

1. **Fundus UI mounted but not route-level pinned**
   - `FundusChartPanel` is mounted in `ClinicalTabbedWorkspace`, but the tests
     inspected mostly exercise the panel in isolation.
   - A future workspace refactor could accidentally remove or hide the card.

2. **Laterality mismatch handling**
   - Docs mention a `Laterality mismatch` warning.
   - Existing backend tests cover missing laterality and normal OD/OS parsing,
     but not dropdown-vs-text mismatch behavior through the API.

3. **Signed-lock completeness**
   - Backend blocks signed chart PATCH and UI removes action controls.
   - Additional coverage should verify render/review/sign endpoints cannot
     mutate or re-promote an already signed chart in surprising ways.

4. **OpenAI/fundus seam confusion**
   - Docs correctly say fake-data/demo only.
   - Operators could still misread the presence of an OpenAI fundus assist seam
     as approval for production LLM or real PHI if runbooks drift.

5. **Claim scanner coverage gap**
   - Current scanners block broad unsafe claims like AI diagnosis, autonomous
     imaging interpretation, and LLM-powered clinical documentation.
   - They do not yet explicitly block fundus-specific phrases such as "fundus
     image interpretation" or "AI-generated fundus diagnosis" on main.

6. **Audit minimization proof**
   - Docs say audit events store chart id, laterality, and warning count only.
   - Tests inspected do not directly assert findings text and drawing JSON stay
     out of audit event payloads.

## 3. Recommended Frontend Tests

Highest value frontend tests:

1. Add a `ClinicalTabbedWorkspace` integration test that switches to Imaging
   and asserts the "Fundus charts" card renders `FundusChartPanel`.
2. Add a route/workspace smoke test so `App` encounter detail loads the fundus
   card for a native encounter with numeric encounter id.
3. Add a test that API list failure shows a visible error while keeping the
   panel usable for retry or navigation.
4. Add a test for generate failure that confirms the typed findings remain in
   the textarea so the clinician does not lose work.
5. Add renderer tests for empty `drawing_json`, malformed elements, long labels,
   and clock ranges crossing 12 o'clock.
6. Add accessibility checks for the OD/OS/OU radio group, signed-lock banner,
   warnings panel, and attestation checkbox.
7. Add a claim-safety fixture for the fundus UI that specifically rejects
   positive "fundus interpretation" and "fundus diagnosis" wording.

## 4. Recommended Backend Tests

Highest value backend tests:

1. API-level laterality mismatch test:
   - selected `laterality="OD"` with findings text naming `OS`;
   - assert warning is persisted and returned.
2. Audit minimization test:
   - generate a chart with a distinctive fake finding string;
   - assert audit events do not store findings text or drawing JSON.
3. Signed chart endpoint hardening:
   - after signing, assert PATCH fails;
   - verify review/render behavior is either explicitly allowed or blocked per
     product policy and documented.
4. Role matrix tests:
   - admin and clinician can create/review/sign;
   - reviewer/front-desk equivalents cannot mutate if those roles exist in the
     auth fixture.
5. Parser edge cases:
   - ambiguous clock hours;
   - "temporal" / "nasal" text;
   - multiple findings across OD and OS in one input;
   - unknown finding with known laterality and known clock hour.
6. OpenAI fundus assist dispatcher tests in the API path once
   `fundus_charts.py` adopts `generate_chart()` instead of calling the
   deterministic parser directly.
7. LLM output schema hardening:
   - malformed laterality;
   - missing `requires_provider_review`;
   - unsafe text in labels/warnings;
   - overlong label truncation or rejection policy.

## 5. Recommended Docs Improvements

1. Add a short Phase 55 traceability note or merge the Phase 55 demo-readiness
   audit artifact if it is intended to be part of main.
2. Add a one-page demo operator runbook for the fundus card:
   - sample script;
   - safe phrases;
   - what not to say;
   - troubleshooting if API generation fails.
3. Add a plain-English role matrix for fundus charts.
4. Add a correction workflow note:
   - what to do when a signed chart is wrong;
   - whether future work should fork/version rather than edit in place.
5. Add a diagram of default deterministic path vs fake-data OpenAI assist path.
6. Add approved claim language to commercial docs:
   - "provider-reviewed retinal diagram drafting from clinician-entered
     findings";
   - "not diagnosis";
   - "not image interpretation";
   - "not production LLM".

## 6. Recommended Demo Improvements

1. Use only built-in fake-data demo chips.
2. Start with `horseshoe tear at 10:30 OD` to show a clean chart.
3. Use `lattice from 5 to 7 OS near ora` to show clock range and OS clarity.
4. Intentionally demonstrate one warning case, then narrate that warnings are
   provider clarification prompts, not clinical conclusions.
5. Narrate the workflow as Draft -> Reviewed -> Signed/Locked.
6. Read the attestation before signing so the buyer sees human accountability.
7. Do not mention OpenAI unless asked.
8. If asked about OpenAI, say:
   - production fundus charting is deterministic;
   - OpenAI assist is fake-data/demo-only behind guardrails;
   - no real PHI should use that path.
9. Avoid fundus photos during the demo unless the screen is clearly showing
   metadata/read-only placeholders, not interpretation.

## 7. Claim-Safety Watchlist

Watch for and block these phrases in public/demo copy:

- "fundus image interpretation"
- "fundus photo interpretation"
- "retinal image interpretation"
- "AI interprets fundus"
- "autonomous fundus interpretation"
- "fundus diagnosis"
- "AI-generated fundus diagnosis"
- "OpenAI fundus interpretation"
- "OpenAI-powered fundus charting"
- "production LLM fundus workflow"
- "real PHI ready"
- "autonomous retinal charting"
- "AI detects retinal disease"

Preferred safe wording:

- "provider-reviewed retinal diagram drafting"
- "from clinician-entered findings"
- "structured fundus chart support"
- "warnings for missing laterality or clock-hour detail"
- "not diagnosis"
- "not image interpretation"

## 8. Security/Compliance Watchlist

1. Do not process real PHI through the fake-data OpenAI adapter or fundus assist.
2. Do not set `CHARTNAV_LLM_REAL_PHI_APPROVED=1` expecting it to enable OpenAI;
   the fake-data adapter must refuse.
3. Do not set `CHARTNAV_PILOT_ALLOW_LLM_OPENAI=1` for fake-data mode; it must
   refuse under the Phase 52B semantic flip.
4. Do not log API keys, findings text, drawing JSON, or full model payloads.
5. Do not let model labels/warnings become orders, diagnoses, billing, coding,
   referrals, or patient messages.
6. Do not treat an LLM output as the source of truth for chart-of-record changes.
7. Keep organization scoping tests active for every fundus endpoint.
8. Keep signed artifacts immutable and version/fork future corrections.

## 9. What NOT To Build Next

Do not build these next:

- production LLM fundus charting;
- real-PHI OpenAI fundus assist;
- fundus photo/OCT image interpretation;
- autonomous diagnosis or disease grading;
- automated treatment recommendations;
- automatic orders, referrals, coding, billing, or patient messages;
- public marketing around OpenAI-powered clinical workflow;
- broad UI redesign before route-level and backend edge-case coverage is pinned.

## 10. Recommended Phase 56 Options Ranked By Business Value

1. **Fundus QA hardening and demo runbook** - highest value.
   - Add route-level frontend tests, API laterality/audit tests, signed-lock
     endpoint policy tests, and a concise operator runbook.
   - Best business value because it protects the newest demo surface without
     expanding clinical risk.

2. **Claim-safety scanner expansion for fundus-specific overclaims**.
   - Add explicit fundus interpretation/diagnosis phrases to commercial,
     website, and demo scanners, plus a small fixture test if practical.
   - High value because it reduces buyer-facing claim risk before outreach.

3. **Correction/versioning design note for signed fundus charts**.
   - Document how corrections should work after signing before building any
     product change.
   - Medium value because it clarifies operations and compliance without
     adding product complexity.

Recommendation: choose Option 1 first. It preserves quality and control around
the shipped workflow, keeps the demo honest, and avoids prematurely expanding
into higher-risk LLM or image-interpretation territory.
