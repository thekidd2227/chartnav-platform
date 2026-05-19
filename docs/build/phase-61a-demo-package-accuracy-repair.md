# Phase 61A — Controlled Demo Package Accuracy Repair

> Docs-only repair PR. No product code, no backend, no frontend, no
> migrations, no public marketing changes, no deploy.

## Why this exists

The Phase 61 controlled-buyer demo package (PR #70, merged at
`5a568e9`) shipped with several factual inaccuracies that a Codex
audit (PR #71) flagged as **P1** before any buyer demo:

1. Multiple Phase 61 docs claimed that **every signed artefact**
   carries a "What ChartNav did NOT do" panel. That is true for the
   Vitals (Phase 60) and Ambient Documentation (Phase 57) surfaces.
   It is **not** true for Fundus Charting V1.
2. The buyer Q&A sheet claimed `forbidden_actions.diagnosis=false`,
   `forbidden_actions.orders=false`, and similar **on every fundus
   response**. The fundus API does not return a `forbidden_actions`
   object in V1.
3. The runbook's Scene 2 Vitals warning-demo step said "Restore the
   sample." That instruction was ambiguous in the actual UI flow.
4. The runbook's fallback table referred to "API 500 / 404 / 403 on
   draft-ambient or similar" inside the **Vitals** row — `draft-ambient`
   is an Ambient endpoint, not a Vitals one.
5. The audit doc referred to "the three new Phase 61 docs" in the
   scanner FILES section; Phase 61 added **four** new demo docs.

If any of those wordings had reached a customer demo, ChartNav would
have been making a claim its product does not actually back. Phase
61A fixes the docs before that happens.

## What ChartNav actually ships, by surface

| Surface | Safety banner | Warnings panel | "What ChartNav did NOT do" card | `forbidden_actions` response field | Provider review/sign attestation | Signed-lock immutable state |
|---|---|---|---|---|---|---|
| Ambient Documentation Assist (Phase 57) | ✓ | ✓ | **✓** | **✓** (closed map, every key pinned `false` server-side) | ✓ | ✓ |
| Technician Workup & Structured Vitals (Phase 60) | ✓ | ✓ | **✓** (9 forbidden actions, each `(false)`) | **✓** (closed map, every key pinned `false` server-side) | ✓ | ✓ |
| Fundus Charting V1 (Phase 55 / 56) | ✓ | ✓ | **✗** | **✗** | ✓ (`{"attested": true}`) | ✓ (PATCH/sign-twice → 409) |

Fundus V1's safety posture is enforced through **different
mechanisms**:

- The deterministic `rule_based_v1` parser takes only clinician-typed
  findings as input — there is no image input at all, so image
  interpretation is structurally impossible.
- The output schema is drawing data only (`drawing_json`, `warnings`,
  `laterality`, `rendered_svg`). There is no `diagnosis` field, no
  `orders` field, no `referrals` field, no `billing` field, no
  `patient_message` field. The category-of-claim does not exist in
  the response shape.
- Warnings use review-prompt language only ("Please confirm before
  signing", "Please add OS or confirm intent before signing") — never
  diagnostic language. The Phase 56 test suite pins this.
- The provider review / sign / attestation flow + signed-lock state +
  PATCH-409 invariant matches the other two surfaces.
- The three claim scanners
  (`scripts/check_{commercial,website,demo}_claims.sh`) block every
  fundus-specific overclaim phrase (`fundus image interpretation`,
  `AI interprets fundus`, `autonomous fundus interpretation`,
  `fundus diagnosis`, `AI-generated fundus diagnosis`, etc.).

The Vitals + Ambient surfaces additionally **declare** the posture
on every response via the closed `forbidden_actions` map. Fundus
V1 declares the same posture through the surrounding controls,
not through a per-response field.

## Files corrected

1. `docs/build/phase-61-demo-package-audit.md`
   - § 5 Recommended demo order, scene 7 closing: scoped the "What
     ChartNav did NOT do" cards to Vitals + Ambient; explained that
     Fundus V1 enforces the same posture through warnings, provider
     review/sign, signed-lock, and the claim scanners.
   - § 7 Known limitations: "three new Phase 61 docs" → "four new
     Phase 61 demo docs (runbook + checklist + Q&A safe-answers +
     storyboard)".

2. `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
   - Scene 2 Vitals operator action: replaced the ambiguous "Restore
     the sample" with explicit recovery wording ("Manually re-enter
     the missing systolic value on the same selected workup, then
     click **Save** again to clear the warning. Or, if the workup
     has already advanced past `draft`, click 'New workup' and
     **Load fake demo vitals** to start a clean workup for the
     review/sign step.").
   - Scene 7 Closing operator action + narration: scoped the "What
     ChartNav did NOT do" card to Vitals + Ambient; added the
     explicit note that Fundus V1 uses warnings + provider review/
     sign + signed-lock + claim scanners instead. Updated the
     closing narrative to match.
   - § 11 Fallback table Vitals row: replaced "API 500 / 404 / 403
     on draft-ambient or similar" with "API 500 / 404 / 403 on the
     vitals-workups create / update / review / sign endpoints".

3. `docs/demo/phase-61-buyer-demo-checklist.md`
   - § 2 During demo: scoped the "What ChartNav did NOT do" card to
     Vitals or Ambient; explained the Fundus V1 difference.

4. `docs/demo/phase-61-buyer-qa-safe-answers.md`
   - Q7 (Does it diagnose?), Q8 (Does it interpret fundus photos
     or OCT?), Q9 (Does it recommend treatment?), Q10 (Does it
     place orders?), Q11 (Does it send referrals or patient
     messages?), Q12 (Does it bill or code?): rewrote each
     "What to say" / "Why" pair to scope the `forbidden_actions`
     claims to Vitals + Ambient and explain Fundus V1's
     alternate enforcement (parser shape, warnings vocabulary,
     review/sign flow, signed-lock, claim scanners).

5. `docs/demo/phase-61-demo-storyboard.md`
   - Closing narrative: same scoping as the runbook's Scene 7.
     "Every signed artefact" → Vitals + Ambient specifically;
     Fundus V1 fork explained.

## Files NOT changed by Phase 61A

- The Vitals scenes (Phase 60 runbook + storyboard Scene 1) and
  the Ambient scenes (Phase 57 runbook + storyboard Scene 2) are
  factually accurate as written. The fixes target only the parts
  that **over-generalised** to "every signed artefact".
- The Fundus Charting V1 scene (storyboard Scene 3) does **not**
  claim a "What ChartNav did NOT do" card — it already correctly
  references the safety banner, warnings, attestation, and signed
  lock. No change.
- `apps/web/src/features/fundus/*` — no change.
- `apps/api/app/api/fundus_charts.py` — no change.
- `apps/api/app/services/fundus_chart_ai.py` — no change. The
  `requires_provider_review` field on the OpenAI-assist response
  schema (line ~354) is the model contract, not a fundus API
  response field; it does not need to be reclassified.
- `docs/build/current-product-truth.md` — no change. The fundus
  row's "Claim posture" column already correctly says
  "Clinician-entered findings to structured drawing support; not
  diagnosis or image interpretation" without claiming a
  forbidden-actions object. No row update needed.
- `docs/workflow/fundus-charting.md` — no change. The doc
  describes warnings + provider review/sign + signed-lock
  accurately. It does not claim a forbidden-actions object.

## Validation

| Check | Result |
|---|---|
| `bash scripts/check_commercial_claims.sh` | PASSED |
| `bash scripts/check_website_claims.sh` | PASSED |
| `bash scripts/check_demo_claims.sh` | PASSED |
| `bash scripts/test_claim_policy_fixtures.sh` | PASS (sync + fixtures) |
| `python3 scripts/check_runtime_safety.py` | PASS |
| `bash scripts/check_alembic_safety.sh` | PASSED |
| `git diff --check` | clean |

No backend or frontend tests run — no code was changed.

## Confirmation: no product code changed

`git diff --stat` after this PR's changes touches only:
- `docs/build/phase-61-demo-package-audit.md`
- `docs/build/phase-61a-demo-package-accuracy-repair.md` (new, this file)
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-demo-storyboard.md`

No `apps/api/` change. No `apps/web/` change. No `alembic/` change.
No `scripts/` change. No `tests/` change. No public website /
deck / marketing path change. No deploy.

## Future follow-up (separate phase, not this PR)

A future phase may add a `forbidden_actions` response object to the
Fundus Charting API so its safety contract is **also** declared
per-response, matching Ambient and Vitals. That is a product-code
change, not a docs change, and is out of scope here. Until that
ships, the corrected wording in this repair PR is the authoritative
operator narration.

## Related documents

- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-61-demo-storyboard.md`
- `docs/build/phase-61-demo-package-audit.md`
- `docs/build/current-product-truth.md`
- `docs/commercial/claims-policy.json`
- `docs/workflow/fundus-charting.md`, `ambient-documentation-assist.md`, `structured-vitals-workup.md`
