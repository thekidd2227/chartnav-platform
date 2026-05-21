# Phase 65B — Pilot Operations Runbook Reconciliation

> **Status: reconciliation complete. Phase 65 plan + Phase 65
> execution artifacts are now ready to land on main without
> reverting Phase 64 or Phase 65A.**
>
> Phase 65B is a **reconciliation increment**, not new operator
> content. The Phase 65 plan and its six pilot operator artifacts
> already exist on a separate branch (`feature/phase-65-controlled-
> pilot-readiness-plan`), but that branch was forked from a stale
> base — its merge-into-main diff would have silently deleted all
> 11 Phase 64 commercial docs + the Phase 65A security crosswalk
> + the Phase 64 implementation report + the Phase 64
> `scripts/check_commercial_claims.sh` FILES-list extension.
>
> This PR ships **only the additive Phase 65 docs** (1 plan + 1
> execution handoff + 6 pilot operator artifacts + 1 README
> insert) on a branch that is rebased off current main, so Phase
> 64 + Phase 65A survive. After this PR merges, the original
> `feature/phase-65-controlled-pilot-readiness-plan` branch can
> be closed without merging.

## 1. The stale-branch problem

The Phase 65 planning + execution branch was created on
2026-05-20 at base `8d2b6dd` (Phase 63C-2). Phase 64 and Phase
65A merged after that base. Running `git diff --name-status
main..origin/feature/phase-65-controlled-pilot-readiness-plan`
today returns:

| Kind | Count | Detail |
|---|---|---|
| Added (intended) | 9 | 1 plan + 1 execution handoff + 6 pilot operator artifacts + 1 README edit |
| Deleted (NOT intended — stale base) | 13 | All `docs/commercial/phase-64-*.md` + `docs/build/phase-64-buyer-outreach-package-implementation-report.md` + `docs/pilot/phase-65a-security-review-evidence-crosswalk.md` |
| Modified (NOT intended — stale base) | 1 | `scripts/check_commercial_claims.sh` reverted to pre-Phase-64 FILES list |

Merging that branch via `git merge` would have **silently
reverted Phase 64 + Phase 65A**. This PR avoids that by
cherry-picking only the additive files onto a fresh branch off
current main.

## 2. What this PR brings in (9 files)

| Path | Origin | Lines | Purpose |
|---|---|---:|---|
| `docs/build/phase-65-controlled-pilot-readiness-plan.md` | Phase 65 branch | 303 | The original Phase 65 plan (Gate taxonomy, real-PHI blockers, evidence packet, success metrics, buyer-facing boundaries). |
| `docs/build/phase-65-controlled-pilot-execution-handoff.md` | Phase 65 branch | 85 | Handoff from plan to execution; names what an operator does after Phase 65A. |
| `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md` | Phase 65 branch | 241 | Gate 0-5 decision tool from fake-data demo through to expansion decision. |
| `docs/pilot/phase-65-security-review-handoff-checklist.md` | Phase 65 branch | 123 | Buyer security-review handoff checklist + evidence map. |
| `docs/pilot/phase-65-pilot-operator-runbook.md` | Phase 65 branch | 125 | Operator runbook for limited monitored pilot after Gate 3 approval. |
| `docs/pilot/phase-65-issue-incident-triage-template.md` | Phase 65 branch | 106 | S1-S4 issue template + escalation rules. |
| `docs/pilot/phase-65-success-metric-tracker-schema.md` | Phase 65 branch | 70 | Operational metric tracker schema; no clinical outcome claims. |
| `docs/pilot/phase-65-pilot-exit-criteria-decision-memo-template.md` | Phase 65 branch | 91 | End-of-pilot decision template. |
| `docs/pilot/README.md` (insert only) | Phase 65 branch | +16 | Phase 65 index section in the pilot README; existing content untouched. |
| `docs/build/phase-65b-pilot-operations-runbook-reconciliation.md` | New (this PR) | (self) | This reconciliation memo. |

## 3. What this PR does NOT do

- **Does not delete any Phase 64 file.** All 11
  `docs/commercial/phase-64-*.md` files survive.
- **Does not delete the Phase 65A crosswalk.**
  `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
  survives.
- **Does not revert the Phase 64 scanner extension.**
  `scripts/check_commercial_claims.sh` keeps the 17-doc FILES
  list it gained in Phase 64.
- **Does not duplicate Phase 65A.** Phase 65A is a security-
  evidence crosswalk index. The Phase 65 pilot operator
  artefacts in this PR are operational templates the operator
  fills in at engagement time. Different shape, different
  purpose, no content overlap.
- **Does not edit product code.** No file under `apps/api/` or
  `apps/web/` is touched.
- **Does not edit any API route, schema, migration, claim
  policy, scanner, or demo script.** Phase 63C functional smoke
  behavior is preserved by construction.
- **Does not introduce a new claim.** All 9 incoming files come
  from the Phase 65 branch verbatim; they already passed the
  Phase 65 author's safety review and pass all six gates on this
  branch unchanged.

## 4. State table

| Item | Pre-this-PR | Post-this-PR |
|---|---|---|
| Phase 64 commercial package on main | ✓ merged at `1e5b368` | ✓ untouched |
| Phase 65A security crosswalk on main | ✓ merged at `124d669` | ✓ untouched |
| Phase 65 plan on main | ✗ branch-only | ✓ merged |
| Phase 65 execution handoff on main | ✗ branch-only | ✓ merged |
| 6 Phase 65 pilot operator artefacts on main | ✗ branch-only | ✓ merged |
| `feature/phase-65-controlled-pilot-readiness-plan` branch | open, stale base | should be closed without merging after this PR lands |
| Phase 63C functional smoke gate | green (last operator-side: 20 pass / 0 fail at `8d2b6dd`) | green (no code paths touched) |

## 5. Where the new docs fit in the Phase 65 § 9 backlog

The Phase 65 plan's § 9 listed: 65A → 65B → 65D → 65C → 65E. With
this PR, the in-main state is:

| Backlog item | What it requires | In-main? |
|---|---|---|
| 65A — Security Review Packet Completion | Evidence crosswalk index | ✓ merged at `124d669` |
| **65B — Pilot Operations Runbook** | **Plan + execution handoff + 6 pilot operator artefacts** | **lands with this PR (reconciliation)** |
| 65D — Pilot Support / Incident Workflow | Formalized support channels, S1/S2/S3 handling | Partially covered by `phase-65-issue-incident-triage-template.md` in this PR; full Phase 65D may want a dedicated PR if more depth is needed. |
| 65C — Limited Pilot Instrumentation | Metric collection plan | Partially covered by `phase-65-success-metric-tracker-schema.md` in this PR; a dedicated Phase 65C may want richer metric definitions. |
| 65E — Pilot Exit Criteria and Expansion Decision Memo | Go/no-go renewal template | Covered by `phase-65-pilot-exit-criteria-decision-memo-template.md` in this PR. |

Phase 65B as defined by the operator brief is satisfied by this
PR. Phase 65C and Phase 65D can be opened later if additional
depth is needed beyond the templates this PR brings in.

## 6. Commands run on this branch

```bash
git checkout main && git pull --ff-only origin main
git checkout -b feature/phase-65b-pilot-operations-runbook-reconciliation

# Cherry-pick additive files only — no deletions.
git checkout origin/feature/phase-65-controlled-pilot-readiness-plan -- \
  docs/build/phase-65-controlled-pilot-readiness-plan.md \
  docs/build/phase-65-controlled-pilot-execution-handoff.md \
  docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md \
  docs/pilot/phase-65-security-review-handoff-checklist.md \
  docs/pilot/phase-65-pilot-operator-runbook.md \
  docs/pilot/phase-65-issue-incident-triage-template.md \
  docs/pilot/phase-65-success-metric-tracker-schema.md \
  docs/pilot/phase-65-pilot-exit-criteria-decision-memo-template.md \
  docs/pilot/README.md

# Validation gates — all pass.
python3 scripts/check_runtime_safety.py
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
bash scripts/check_alembic_safety.sh
git diff --check
```

## 7. Validation results

| Check | Result |
|---|---|
| `scripts/check_runtime_safety.py` | PASS |
| `scripts/check_commercial_claims.sh` | PASS (0 fail / 0 warn across 17 commercial docs) |
| `scripts/check_website_claims.sh` | PASS (0 fail / 0 warn) |
| `scripts/check_demo_claims.sh` | PASS (0 hits across 34 demo files) |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_alembic_safety.sh` | PASS |
| `git diff --check` | clean |
| Phase 63C functional smoke | NOT RUN from sandbox (no live API/web stack). Behavior preserved by construction — no API route, no schema, no service module, no migration, no scanner FILES list, no claim policy, no demo / capture / smoke script touched. Last operator-side outcome: `BUYER-DEMO FUNCTIONAL GO: YES` (20 pass / 0 fail) at `8d2b6dd`. |

## 8. After this PR merges

1. Close `feature/phase-65-controlled-pilot-readiness-plan`
   without merging it. Its content (minus the accidental
   deletions) is now on main via this PR. Closing it prevents a
   future contributor from merging the stale branch and
   reverting Phase 64 + Phase 65A.
2. The Phase 65A crosswalk's "Phase 65 plan lives on
   `feature/phase-65-controlled-pilot-readiness-plan`" reference
   becomes obsolete — the plan is now on main. A future small
   doc-update PR can drop that branch qualifier from the
   crosswalk's § 2 anchor table. Not blocking this PR.

## 9. Hard constraints honored

- No real PHI.
- No HIPAA-compliance claim, no certified-EHR claim, no
  autonomous-diagnosis / orders / coding / billing claim.
- ChartNav positioned only as a provider-reviewed ophthalmology
  workflow / documentation support layer.
- No rename of VisitDraft Assist, Fundus Drawing Assist,
  Technician Workup, Doctor Review / Attestation, or Signed Lock.
- No backend code, frontend code, API route, migration, deploy,
  production LLM, or vendor API key.
- No duplication of Phase 65A security evidence crosswalk.
- No duplication of existing Phase 65 operator docs (those did
  not yet exist on main; this PR brings them in for the first
  time).

## 10. Exact next phase recommendation

**Phase 65D** — Pilot Support / Incident Workflow.

Rationale: Phase 65B (this PR) ships the operator artefacts; the
next pilot-readiness priority per the Phase 65 plan's § 9
recommended order is Phase 65D ("Pilot Support / Incident
Workflow"), specifically deepening
`phase-65-issue-incident-triage-template.md` into a full
support/incident workflow with named owners, escalation
channels, evidence preservation, and S1/S2/S3 + breach
procedures. Phase 65C (Limited Pilot Instrumentation) and Phase
65E (Pilot Exit Criteria) follow.

Phase 65D can be opened as a small follow-on PR once a real
prospective pilot practice surfaces (no need to over-engineer it
before there's a specific engagement to anchor against).

## Related documents

- `docs/build/phase-65-controlled-pilot-readiness-plan.md` (now
  in-main via this PR)
- `docs/build/phase-65-controlled-pilot-execution-handoff.md`
  (now in-main via this PR)
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
  (already merged at `124d669`)
- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
