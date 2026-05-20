# Phase 64 — Buyer Outreach Package Implementation Report

> **Status: docs-only commercial-readiness package committed.**
> Phase 64 ships the 11 buyer-outreach deliverables defined by
> the merged Phase 64 plan (`docs/build/phase-64-buyer-outreach-
> package-plan.md`). No product code, no website edit, no
> migration, no claim-policy change, no deploy.

## 1. Scope

Pure commercial documentation. Eleven new files under
`docs/commercial/phase-64-*.md`, plus one extension to
`scripts/check_commercial_claims.sh` so the scanner covers the
new files, plus this short implementation report.

## 2. Files created

| Path | Purpose |
|---|---|
| `docs/commercial/phase-64-one-page-buyer-brief.md` | Internal / shareable brief for early outreach. |
| `docs/commercial/phase-64-outreach-email-v1.md` | Cold-or-warm outreach email v1. |
| `docs/commercial/phase-64-follow-up-email-v1.md` | Polite follow-up email v1. |
| `docs/commercial/phase-64-linkedin-dm-script.md` | LinkedIn DM script + short follow-up. |
| `docs/commercial/phase-64-call-opener.md` | 60-second operator call opener + hard-stop topics table. |
| `docs/commercial/phase-64-buyer-qualification-checklist.md` | Qualifying signals + disqualifier list + fit-score guide. |
| `docs/commercial/phase-64-paid-pilot-positioning.md` | Pilot framing hypotheses (30/60/90-day) + objection table + what-it-does-not-include. |
| `docs/commercial/phase-64-pilot-success-metrics.md` | 7 manually-measurable workflow metrics + explicit out-of-scope list. |
| `docs/commercial/phase-64-security-review-packet-index.md` | Index of evidence we can share with a buyer's security team before any real-PHI use. |
| `docs/commercial/phase-64-demo-asset-index.md` | Pointer index for buyer-demo media + the Phase 63C functional readiness gate. |
| `docs/commercial/phase-64-outreach-tracker-schema.md` | Markdown table schema for the internal outreach tracker (no CRM integration). |
| `docs/build/phase-64-buyer-outreach-package-implementation-report.md` | This report. |

## 3. Source-of-truth docs used

Read and referenced in the 11 deliverables:

- `docs/build/phase-64-buyer-outreach-package-plan.md` (planning
  source of truth)
- `docs/build/current-product-truth.md`
- `docs/build/phase-63c-demo-critical-functional-repair-report.md`
- `docs/build/phase-63c1-functional-smoke-500-repair-report.md`
- `docs/build/phase-63c2-vitals-smoke-transition-repair-report.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `docs/release/release-evidence-checklist.md`
- `docs/commercial/chartnav-approved-claims-language.md`
- `docs/commercial/claims-policy.json`

## 4. Safe positioning (per the plan § 4)

Every deliverable frames ChartNav as:

- a provider-reviewed ophthalmology workflow layer that runs
  alongside the practice's existing EHR (not a replacement);
- four narrow workflows: Technician Workup & Vitals,
  Provider-Reviewed VisitDraft Assist (transcript-to-draft;
  not ambient capture), Provider-Reviewed Fundus Drawing Assist
  (clinician-entered findings to structured diagram; not image
  interpretation), and doctor review / attestation / signed lock;
- available as a **controlled fake-data demo** today;
- a candidate for **paid pilot** conversations after a successful
  demo, conditional on security review before any real-PHI use.

## 5. Forbidden positioning (per the plan § 5) — explicitly NOT used

The deliverables do not claim ChartNav is or does any of the
following, except when explicitly negating the claim:

- ChartNav is not an AI scribe, does not provide hands-free scribing,
  does not perform ambient listening, does not listen to the exam
  room, does not capture exam-room audio, does not ignore small
  talk while capturing findings, does not provide autonomous
  documentation, does not auto-write notes, is not a diagnostic
  AI, does not perform fundus image interpretation, does not
  perform OCT interpretation, is not an EHR replacement, is not
  HIPAA-compliant or HIPAA-certified, is not a production LLM
  product, and is not OpenAI / Anthropic / IBM-powered clinical
  documentation. ChartNav does not provide automatic coding,
  billing, orders, referrals, or patient messaging. ChartNav does
  not integrate with medical devices and does not provide remote
  patient monitoring.

The commercial-claims scanner (extended in this PR to cover all
11 new files) verifies these negations stay negations. After the
final pass: **0 fail / 0 warn across 17 docs scanned for
forbidden phrases (was 6 → now 17)**.

## 6. Checks run

| Check | Result |
|---|---|
| `scripts/check_runtime_safety.py` | PASS |
| `scripts/check_commercial_claims.sh` | PASS (0 fail / 0 warn). Covers the 17 docs (the original 6 Phase 17 commercial support docs + the 11 Phase 64 files). |
| `scripts/check_website_claims.sh` | PASS (0 fail / 0 warn) |
| `scripts/check_demo_claims.sh` | PASS (0 hits across 34 demo files) |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_alembic_safety.sh` | PASS |
| `git diff --check` | clean |

## 7. Functional smoke status

Phase 63C-2 merged at `8d2b6dd` (commit immediately before this
branch). The Phase 63C functional smoke last reported
`BUYER-DEMO FUNCTIONAL GO: YES` on the operator's iMac stack
after the Phase 63C-2 transition fix.

This sandbox cannot run the live functional smoke (no live API
or web stack). **Local rerun: not run.** Smoke status quoted from
the prior operator-side execution on `8d2b6dd`. Phase 64
deliverables that reference the smoke do so verbatim (commit
SHA and outcome string).

## 8. No product code

No file under `apps/api/` or `apps/web/` was touched.

## 9. No backend / frontend changes

No backend service, route, schema, migration, or test changed.
No frontend component, test, or i18n entry changed.

## 10. No public website changes

`apps/web/src/LandingPage.tsx`, `apps/web/src/i18n/landing.en.ts`,
and `apps/web/src/i18n/landing.es.ts` are untouched. The public
landing page is out of Phase 64 scope.

## 11. No real PHI

No deliverable references real patient information, real
practice names, real provider names, or real contact details.
The single example row in `phase-64-outreach-tracker-schema.md`
is explicitly labelled "Synthetic Eye Center (fake)" with a "No
real practice. No real patient information." caveat directly
beneath.

## 12. No production LLM

No deliverable promises a production LLM activation. Vendor
evaluation paths (OpenAI / Anthropic / IBM watsonx) appear only
in the context of the Phase 64 paid-pilot positioning memo,
explicitly as "vendor evaluation, never advertised as a shipped
production capability."

## 13. No deploy

`apps/web/public/` untouched. No production config changed.

## 14. Buyer-demo readiness basis

Phase 64 deliverables that reference demo readiness are anchored
to `8d2b6dd` (Phase 63C-2 merge) and the most recent operator-
side `BUYER-DEMO FUNCTIONAL GO: YES`. The `phase-64-demo-asset-
index.md` explicitly distinguishes:

- **Media presence** (Phase 63A file-presence gate): 30
  screenshots + 12 video clips exist.
- **Buyer-demo functional GO** (Phase 63C/63C-2 smoke):
  exercises actual HTTP API for all three workflows; the
  authoritative readiness signal.

Both must be green for outreach conversations to lean on demo
evidence.

## 15. Exact next command for Jean-Max

After Phase 64 merges:

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
```

Expected HEAD: `<merge sha> docs(commercial): add phase 64 buyer outreach package (#NN)`.

Then open the package and read top-to-bottom:

```bash
open docs/commercial/phase-64-one-page-buyer-brief.md
open docs/commercial/phase-64-outreach-email-v1.md
open docs/commercial/phase-64-call-opener.md
open docs/commercial/phase-64-buyer-qualification-checklist.md
open docs/commercial/phase-64-paid-pilot-positioning.md
open docs/commercial/phase-64-pilot-success-metrics.md
open docs/commercial/phase-64-security-review-packet-index.md
open docs/commercial/phase-64-demo-asset-index.md
open docs/commercial/phase-64-outreach-tracker-schema.md
```

Phase 64 outreach should not start until:

- the buyer-demo functional smoke is green on the iMac
  (`bash scripts/demo/phase63c_functional_smoke.sh`);
- the operator has personally read all 11 deliverables and is
  comfortable with the safe positioning;
- the outreach tracker is initialized.

## Related documents

- `docs/build/phase-64-buyer-outreach-package-plan.md`
- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
