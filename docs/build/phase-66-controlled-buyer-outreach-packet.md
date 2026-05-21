# Phase 66 — Controlled Buyer Outreach Packet (Build Report)

> **Status: docs-only commercial increment. Buyer-outreach-
> readiness GO for first-pilot prospecting** (subject to the
> existing safety frame). No product code, no backend, no
> frontend, no API, no migration, no demo-script change, no
> public website change, no deploy, no real PHI, no production
> LLM, no new claims.

## 1. What Phase 66 adds on top of Phase 64 / 65

Phase 64 shipped 11 commercial docs in operator voice. Phase 65A
shipped a security evidence crosswalk. Phase 65B shipped the
plan + 6 pilot operator artefacts. Phase 66 is a **founder-led,
specialty-targeted overlay** on those — narrower, more concrete,
and focused on what to do **this week** to find the first paid
pilot.

Phase 66 does not duplicate Phase 64 / 65. The differentiators:

| Phase 66 deliverable | What's genuinely new vs Phase 64 / 65 |
|---|---|
| `phase-66-prospect-targeting-brief.md` | Specialty-tiered priority ranking (retina vs glaucoma vs general ophth) with EHR-signal cues + outreach-source ranking + pilot-ready-signal table. Phase 64's `buyer-qualification-checklist.md` is the general qualifier universe; this brief narrows it. |
| `phase-66-founder-led-outreach-templates.md` | Founder-voice email + LinkedIn DM (Phase 64 is operator-voice) **plus two genuinely new templates**: calendar invite copy (NEW — not in Phase 64) and post-demo follow-up email (NEW — Phase 64's follow-up is for non-response, not post-demo). |
| `phase-66-buyer-discovery-questions.md` | 15-question deeper list organized by workflow stage (Phase 64's call-opener has 5 questions to pick three from). Includes "questions operators must NOT ask" sub-section. |
| `phase-66-what-not-to-promise-cheat-sheet.md` | Single-page consolidated cheat sheet of the safety-frame negations scattered across Phase 64 / 65 docs. Includes three "emergency phrases" the operator memorises. Same shape as `chartnav-approved-claims-language.md`; added to the scanner's catalog-skip list. |

## 2. Files changed

| Path | Lines | Kind |
|---|---:|---|
| `docs/commercial/phase-66-prospect-targeting-brief.md` | 154 | New |
| `docs/commercial/phase-66-founder-led-outreach-templates.md` | 282 | New |
| `docs/commercial/phase-66-buyer-discovery-questions.md` | 154 | New |
| `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md` | 169 | New |
| `docs/build/phase-66-controlled-buyer-outreach-packet.md` | (this) | New |
| `scripts/check_commercial_claims.sh` | +6 / -2 | Extend SUPPORT FILES list to scan 4 new Phase 66 docs + add Phase 66 cheat sheet to catalog-skip list |

## 3. Scanner extension rationale

Two scanner edits:

1. **SUPPORT FILES list** extended from 17 docs (Phase 17 + Phase 64) to 21 docs (Phase 17 + Phase 64 + Phase 66 prospect brief + Phase 66 outreach templates + Phase 66 discovery questions). The cheat sheet is in the catalog-skip list (next item).
2. **Catalog-skip list** extended to include `phase-66-what-not-to-promise-cheat-sheet.md`. The cheat sheet is structurally identical to the already-skipped `chartnav-approved-claims-language.md` and the language-guide: it exists to enumerate banned phrases with safe replacements. Skipping it from positive-claim scanning is consistent with how Phase 17 catalog docs are handled.

This is **not** a weakening of the scanner. The cheat sheet is a catalog, not a positive-claim surface. All other Phase 66 docs are scanned and PASS 0 fail / 0 warn.

## 4. Hard rules honored

- **No product functionality change.** No file under `apps/api/` or `apps/web/`.
- **No fake customer claims.** Every Phase 66 doc states ChartNav is pre-pilot, no public customer references, no traction claim.
- **No claim of certified EHR / EHR replacement.** All four Phase 66 docs negate this explicitly.
- **No claim of billing / autonomous diagnosis / AI scribe / HIPAA certification.** All negated explicitly across the 4 docs.
- **No overbuilt support or incident workflows.** Phase 66 uses Phase 65's templates by reference (`phase-65-issue-incident-triage-template.md`); does not duplicate or deepen them. Per the brief, that work waits for a real prospect.
- **Buyer-safe language only.** All scanners PASS.

## 5. Scanners run

| Check | Result |
|---|---|
| `scripts/check_commercial_claims.sh` | **PASS** (0 fail / 0 warn across 21 docs scanned for forbidden phrases — was 17, now 21) |
| `scripts/check_demo_claims.sh` | PASS (0 hits across 34 demo files) |
| `scripts/check_website_claims.sh` | PASS (0 fail / 0 warn) |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_runtime_safety.py` | PASS |
| `scripts/check_alembic_safety.sh` | PASS |
| `git diff --check` | clean |

## 6. Phase 63C buyer-demo smoke

**Not run from this sandbox** (no live API/web stack). Behavior
preserved by construction — this PR touches no API route, no
Pydantic schema, no service module, no migration, no scanner
FILES list semantics affecting demo paths, no claim policy, and
no demo / capture / smoke script.

Last operator-side outcome at `75608ad`:
```
Phase 63C functional smoke: 20 pass / 0 fail
BUYER-DEMO FUNCTIONAL GO: YES
```

## 7. Buyer-outreach-readiness GO/NO-GO

**Repo-side: GO for first-pilot outreach.** Phase 66 adds the
founder-led, specialty-targeted overlay on top of the existing
Phase 64 commercial package, with full safety-frame coverage.

**Operator-side: GO when the operator has:**

1. Read `docs/commercial/phase-66-prospect-targeting-brief.md`
   and identified specific Rank 1 prospects from the personal
   network.
2. Read `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
   and committed the three emergency phrases to memory.
3. Initialised the outreach tracker
   (`docs/commercial/phase-64-outreach-tracker-schema.md`) with
   the first 12 Rank 1 prospects.
4. Verified the Phase 63C functional smoke is still green on
   the iMac stack
   (`bash scripts/demo/phase63c_functional_smoke.sh` →
   `BUYER-DEMO FUNCTIONAL GO: YES`).

When those four are done, Phase 66 Cycle 1 outreach can begin.

## 8. Exact next commands for Jean-Max

After Phase 66 merges:

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
```

Expected HEAD: `<merge sha> docs(commercial): add controlled buyer outreach packet (#NN)`.

Re-confirm the smoke (should remain green):

```bash
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

Then read the Phase 66 packet top-to-bottom:

```bash
open docs/commercial/phase-66-prospect-targeting-brief.md
open docs/commercial/phase-66-founder-led-outreach-templates.md
open docs/commercial/phase-66-buyer-discovery-questions.md
open docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md
open docs/build/phase-66-controlled-buyer-outreach-packet.md
```

Identify the first 12 Rank 1 prospects. Initialise the outreach
tracker. Begin Cycle 1 founder-led emails. Use the cheat sheet
in a side pane on every call.

## 9. What's NOT in scope for Phase 66 (deferred)

- Phase 65D Pilot Support / Incident Workflow deepening — waits
  for a specific prospective pilot practice (per the Phase 65B
  reconciliation report § 10).
- Phase 65C Limited Pilot Instrumentation deepening — same.
- Phase 65E Pilot Exit Criteria deepening — same.
- Any rename of VisitDraft Assist, Fundus Drawing Assist,
  Technician Workup, Doctor Review / Attestation, or Signed
  Lock.
- Any public website edit, marketing-site change, or external
  press / launch material.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/build/phase-64-buyer-outreach-package-implementation-report.md`
- `docs/build/phase-65b-pilot-operations-runbook-reconciliation.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md`
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
