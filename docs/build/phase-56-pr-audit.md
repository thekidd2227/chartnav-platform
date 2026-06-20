# Phase 56 PR Audit

> Scope: audit of merged PR #61 / branch
> `feature/phase-56-fundus-qa-demo-runbook`.
>
> Constraints honored: no backend services edited by this audit, no frontend
> product components edited, no API routes edited, no deployment, and no real
> PHI processed.

## Executive Conclusion

PR #61 is merge-safe in its current merged form. It materially improves the
fundus charting QA posture with focused frontend tests, backend edge-case tests,
demo runbook coverage, workflow doc updates, and claim-scanner additions.

The PR is not purely test/docs because it modifies
`apps/api/app/services/fundus_chart_ai.py` to add a laterality-mismatch warning.
That implementation change is narrow, documented, and directly supports the
Phase 55 audit gap. I do not consider it unnecessary, but it should be treated
as a small behavior change rather than "tests only."

## 1. Route-Level Fundus Mounting

Coverage: **mostly covered, with one follow-up.**

What is covered:

- `apps/web/src/test/ClinicalTabbedWorkspace.test.tsx` now stubs the fundus API
  and verifies the Imaging tab renders the `Fundus charts` card.
- It asserts the mounted card contains `fundus-chart-panel`,
  `fundus-safety-banner`, and the OD/OS/OU laterality controls.
- `ClinicalTabbedWorkspace.tsx` mounts `<FundusChartPanel encounterId={encounterId} />`
  below the OD/OS retinal workbench.

Remaining gap:

- This is workspace-level mount coverage, not full `App` encounter-detail route
  coverage. A future test should open an encounter through `App` and assert the
  Imaging tab exposes the Fundus charts card for a native encounter.

## 2. Laterality Mismatch

Coverage: **covered.**

The PR adds:

- unit coverage that request hint `OD` plus findings text `OS` emits a
  `Laterality mismatch` warning;
- coverage that findings text wins;
- no-warning coverage when request/text agree;
- no-warning coverage for `OU` as a broad hint;
- API coverage proving the warning is returned by generate and persisted on GET.

The small service change is aligned with the documented behavior.

## 3. Audit Minimization

Coverage: **covered at a useful regression level.**

`test_audit_detail_contains_no_raw_findings_text_or_drawing` creates a canary
finding, triggers generate/render/review/sign, then inspects
`security_audit_events` for forbidden substrings:

- raw findings text;
- canary token;
- drawing JSON keys;
- SVG fragments;
- rendered SVG prefix.

It also verifies `chart_id` remains available for traceability. This is the
right balance: metadata remains useful without leaking clinical payloads.

## 4. Signed Chart Policy

Coverage: **covered.**

The PR pins:

- review on signed chart returns `409`;
- second sign returns `409` and does not re-stamp `signed_at`;
- PATCH on signed chart returns `409`;
- render on signed chart is intentionally allowed and idempotent, preserving
  `signed_at`, signer id, and status.

The render policy is explicitly documented in the test name/body. That reduces
future ambiguity.

## 5. Demo Runbook Safety and Usefulness

Assessment: **safe and useful.**

Strengths:

- opens with fake-data/no-PHI warning;
- explicitly says no image interpretation, no diagnosis, and no autonomous sign;
- states default fundus path is deterministic `rule_based_v1`;
- warns not to set real OpenAI/fundus assist env vars for the demo;
- gives exact click path, safe samples, approved phrases, forbidden phrases,
  warning narration, review-vs-sign language, signed-lock explanation, Q&A, and
  troubleshooting.

Non-blocking polish:

- Section 4 step 6 tells the operator to click the `Lattice 5 to 7 OS` chip,
  generate, then replace the text with `lattice degeneration at 6` and generate
  again. That works, but it creates an extra clean lattice chart before the
  warning example. A later docs-only polish pass could simplify this by editing
  the text before the first warning-demo generate.

## 6. Public/Vendor Overclaims

Assessment: **no positive overclaims introduced.**

The runbook lists forbidden phrases, but frames them as "do not say" and pairs
them with safe alternatives. The docs repeatedly state:

- not OpenAI-powered;
- no production LLM;
- no real PHI;
- no diagnosis;
- no image interpretation;
- no HIPAA-compliance claim.

Claim scanner additions improve coverage for:

- `OpenAI fundus interpretation`;
- `OpenAI-powered fundus charting`;
- `production LLM fundus workflow`;
- `autonomous retinal charting`;
- `AI detects retinal disease`;
- `real PHI ready` in commercial/website scanners.

The demo scanner does not add `real PHI ready` in this PR because that phrase
already existed earlier in its compliance overclaim list.

## 7. Implementation Files Modified

Assessment: **one implementation file modified, but justified.**

Modified implementation file:

- `apps/api/app/services/fundus_chart_ai.py`

Change:

- Adds a warning when `laterality_hint` is `OD`/`OS`, parsed findings laterality
  is `OD`/`OS`, and they disagree.
- Keeps findings text as source of truth.

This is not an unnecessary product expansion. It is a targeted safety/QA fix
for a Phase 55 audit gap and is covered by unit/API tests. No frontend product
component or API route implementation was modified.

## 8. Test Sufficiency

Assessment: **sufficient for merge; strong next-layer coverage remains.**

Strong coverage added:

- route/workspace mounting of fundus card;
- panel failure modes;
- laterality mismatch;
- audit minimization;
- signed chart policy;
- renderer edge cases;
- role matrix;
- cross-org access;
- claim scanners.

Recommended follow-up tests:

- full `App` encounter-detail path test for fundus card reachability;
- role matrix coverage for review/render/update endpoints, not only generate,
  read, and sign;
- scanner fixture tests proving positive fundus overclaims fail while catalog
  sections and negative-context phrasing pass;
- API test for exact warning payload shape when text includes multiple eyes.

## 9. Merge-Safety Recommendation

Recommendation: **merge-safe / no blockers.**

Rationale:

- Required claim scanners pass.
- Targeted fundus backend suite passes.
- New behavior is narrow and tested.
- Demo runbook is safe for customer-facing rehearsal if the operator follows it.
- No public/vendor overclaim is introduced.
- No real-PHI path or production LLM activation is added.

## Blockers

None.

## Residual Risks

- Workspace-level route coverage is good, but full `App` route coverage is still
  worth adding.
- The runbook warning-demo sequence can be made cleaner.
- The service file change means this PR should not be described as docs/tests
  only; it includes a small, intentional behavior fix.
