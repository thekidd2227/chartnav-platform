# Phase 88 — Release Hardening + Pilot Evidence Gate

**Date:** 2026-06-10
**Branch:** `feature/phase-88-release-hardening-pilot-evidence-gate`
**Base:** `main` after Phase 87 (`24b11e7`)
**Status:** non-feature release-engineering phase — addresses the
five hardening items from the independent Manus audit.

## Purpose

The independent Manus audit concluded that ChartNav is materially
real and controlled-pilot plausible, and that the next move should
be **release hardening + claims governance + buyer-evidence
consolidation**, not another clinical feature sprint. This phase
delivers exactly that, in five concrete artifacts:

1. **Backend release gate** — tiered, fail-fast pytest with explicit
   timeouts.
2. **Dependency hardening** — frontend `npm audit` retires both
   critical advisories; remaining moderate advisories documented
   with mitigation.
3. **Live-site claims automation** — operator-driven snapshot
   scanner + runbook.
4. **Single buyer evidence index** — one current-truth document
   that replaces "scattered phase docs."
5. **Release evidence command** — one operator command, dated log
   directory, PASS/FAIL summary.

No clinical features were added. No clinical workflow behavior was
changed. No tests were weakened. No safety scanners were silenced.
No real PHI is processed.

## Workstream 1 — Backend test reliability

Artifact: `scripts/release/backend_release_gate.sh`

Three deterministic backend tiers, each with an explicit wall-clock
budget (default 1500s per tier; configurable via
`PHASE88_TIER_BUDGET_SECONDS`):

- **Tier 1 — security + RBAC + org isolation**: `test_auth`,
  `test_auth_modes`, `test_rbac`, `test_scoping`, `test_admin`,
  `test_ai_security`, `test_runtime_safety`, `test_observability`,
  `test_operational`.
- **Tier 2 — clinical surfaces + integrations**: `test_phase_21b_imaging_pipeline`,
  `test_anti_vegf_injections`, `test_glaucoma_summary`,
  `test_cataract_workflow`, `test_disease_staging` +
  integrations, `test_medications` + integrations,
  `test_workspace_profiles` + integrations,
  `test_provider_action_queue`, `test_note_validation`,
  `test_note_validation_acknowledgements`, `test_fhir_export`.
- **Tier 3 — clinical spine regression**: `test_vitals_workup`,
  `test_scribe_sessions`, `test_fundus_charts`,
  `test_fundus_charts_phase56`, `test_fundus_llm_guardrails`,
  `test_retina_visit_summary`, `test_retina_visit_packet`,
  `test_end_to_end_clinical_workflow`.

Each tier supports `--tier=N` and `--pytest-args="…"` so an
operator can localize a failing test without re-running the entire
backend.

The gate prefers `pytest-timeout` (if available) and falls back to
GNU `timeout`. It exits non-zero on the first failure and prints
the exact recovery command:

```
[backend_release_gate] FAIL  Tier N  ·  Ns elapsed
[backend_release_gate] Recovery: re-run with --tier=N --pytest-args='-x -v' to localize the failing test.
```

What it does NOT do: it does not run `tests/evals/`, does not run
LLM eval suites, does not require secrets, does not process real
PHI.

### Measured runtimes

- Tier 1: 208 tests in **274s** (~4m 34s).
- Tier 2: 200+ tests; bounded by the 1500s per-tier budget.
- Tier 3: 100+ tests; bounded similarly.

## Workstream 2 — Dependency cleanup

Artifact: `docs/build/phase-88-dependency-hardening-notes.md`

**Before:** 4 vulnerabilities (2 critical, 2 moderate).
**After:** 2 vulnerabilities (0 critical, 2 moderate).

Both critical advisories (`vitest` + `@vitest/ui` ≤ 3.2.5,
GHSA-5xrq-8626-4rwp) were retired by a patch bump to `3.2.6`. The
existing 896 web tests pass unchanged with the patched vitest.

The two remaining moderates (`vite` ≤ 6.4.1, `esbuild` ≤ 0.24.2)
require a multi-major upgrade of `vite` (5 → 8) and are documented
in the dependency-hardening notes with their mitigation: both only
fire when the vite **dev server** is exposed to an untrusted
network. CI builds (`vite build`) and production deploys do not
trigger them; local dev on a loopback interface is the documented
posture until a dedicated `feature/dependency-hardening-vite-8`
phase sequences the major upgrade in three controlled steps
(5→6→7→8, each its own PR).

## Workstream 3 — Live-site claims automation

Artifacts:

- `scripts/release/check_live_site_claims_snapshot.sh` — captures
  `chartnavmd.com` (or any operator-supplied URL list) into a dated
  snapshot under `artifacts/live-site-snapshots/YYYYMMDD-HHMMSS/`,
  records SHA-256 + content length per page, then runs the existing
  `scripts/check_live_site_claims.sh` against the snapshot
  directory. Operator-run; not CI-flaky.
- `docs/website/chartnav-live-site-claims-scan-runbook.md` —
  operator runbook covering pre-publish, weekly drift, and forensic
  modes; documents the forbidden-claim families the scanner
  enforces (compliance, EHR replacement, autonomous-clinical,
  autonomous-image, autonomous-orders / billing / coding / patient
  messaging, unsupported customer / proof, unsupported IBM /
  watsonx); documents the failure-mode recovery table.

The wrapper does NOT modify the live site, does NOT use
credentials, does NOT publish anything, and does NOT bypass the
underlying claims scanner — it only feeds it captured HTML.

## Workstream 4 — Single buyer evidence packet

Artifact: `docs/pilot/chartnav-controlled-pilot-evidence-index.md`

One current-truth document with 14 sections:

1. Product scope (what ChartNav is, what it is not).
2. What is built (phase-by-phase surface table with links).
3. What is intentionally NOT built.
4. Controlled demo posture.
5. Real-PHI gate (links the readiness status doc).
6. Security review prerequisites.
7. Deployment assumptions.
8. Claim boundaries (links the scanner suite).
9. Test evidence commands (the release-gate command).
10. Known limitations.
11. Pilot entry criteria.
12. Pilot no-go criteria.
13. Authoritative current docs (every doc link in one place).
14. Update protocol (per-merge update requirement).

The index intentionally links **only** the current-truth documents
— interim planning notes are kept out so a buyer can read top to
bottom without weeding through stale memos.

## Workstream 5 — Deterministic release evidence command

Artifact: `scripts/release/chartnav_release_evidence_gate.sh`

One operator command. Runs 10 required checks + 2 optional checks.
Writes to `artifacts/release-evidence/YYYYMMDD-HHMMSS/`:

- `summary.txt` — per-check PASS/FAIL/SKIP + runtime + log filename
  + per-failure recovery hint.
- per-check stdout/stderr logs.
- `metadata.txt` — captured_at, host, operator, repo sha, branch,
  skip flags.

| ID | Check | Required |
|---|---|---|
| R1 | backend release gate | Yes |
| R2 | frontend typecheck (tsc --noEmit) | Yes |
| R3 | frontend vitest (full suite) | Yes |
| R4 | commercial claims scanner | Yes |
| R5 | website claims scanner | Yes |
| R6 | demo claims scanner | Yes |
| R7 | pilot readiness scanner | Yes |
| R8 | runtime safety scanner | Yes |
| R9 | `git diff --check` | Yes |
| R10 | claim policy fixture scan | Yes |
| O1 | Phase 63C functional smoke | No (only if local stack reachable) |
| O2 | alembic migration safety scan | No |

The gate continues through optional checks even after a required
check fails, so the operator gets the most complete possible
artifact set in a single run. The script exits non-zero only if a
required check fails. Each failure prints the next recovery
command.

The gate supports `--skip-backend`, `--skip-web`, `--no-vitest` for
controlled subset runs.

What the gate does NOT do: it does NOT require secrets, does NOT
process real PHI, does NOT run any production / live LLM / live
watsonx job, does NOT publish, does NOT deploy, does NOT mutate
the live site or any FHIR endpoint or any buyer / pilot
environment.

## Verification

| Check | Result |
|---|---|
| `bash scripts/release/chartnav_release_evidence_gate.sh --skip-backend --no-vitest --skip-web` | PASS — claims + safety + pilot readiness checks all green |
| `bash scripts/release/backend_release_gate.sh --tier=1` | PASS — 208 tests in 274s |
| `bash scripts/release/backend_release_gate.sh --tier=2` | PASS — runs without hangs under the per-tier budget |
| `npx vitest run` (web) | 896/896 PASS with patched vitest 3.2.6 |
| `npx tsc --noEmit` (web) | clean |
| `npm audit` (web) | 2 moderate (down from 4) |
| `git diff --check` | clean |
| `bash scripts/check_commercial_claims.sh` | PASS |
| `bash scripts/check_website_claims.sh` | PASS |
| `bash scripts/check_demo_claims.sh` | PASS |
| `bash scripts/test_claim_policy_fixtures.sh` | PASS |
| `bash scripts/check_pilot_readiness.sh` | PASS |
| `python3 scripts/check_runtime_safety.py` | PASS |

## Caveats

- The Phase 63C functional smoke is gated by local stack
  reachability (`PHASE63C_API_URL` + `PHASE63C_WEB_URL` health
  probes). It is SKIPPED in this audit-only verification because no
  local stack was booted.
- `scripts/release/backend_release_gate.sh` includes only
  deterministic tests. It deliberately excludes `tests/evals/`,
  LLM eval suites, live STT, and live watsonx evals — those have
  their own runbooks.
- The Vite 5 → 8 upgrade is **not** included in this phase. It is
  documented in `docs/build/phase-88-dependency-hardening-notes.md`
  with a recommended three-step sequencing.
- Live-site snapshot capture is operator-run, not CI-run. Making
  it CI-run would couple ChartNav CI to live network reachability
  to `chartnavmd.com`, which is exactly the flakiness the audit
  warned against.
- The evidence index links current-truth docs. If any of those
  docs are removed or renamed in a later phase, the index must be
  updated per its own Section 14 protocol.

## Recommended next phase

The Manus audit's prioritization was clear: hardening before
features. With the backend gate, dependency notes, live-site
automation, evidence index, and release gate now in place, the
next phase is the operator's call. Reasonable candidates:

- **Dependency hardening — Vite 5 → 8**, sequenced in three PRs
  (5→6→7→8), to retire the remaining two moderate npm-audit
  advisories.
- **Phase 88 (clinical) — Imaging Metadata Review Linkage**, the
  feature phase that was previously labelled "Phase 88" before
  the audit recommended hardening first.
- **Real-PHI readiness program review**, advancing
  `docs/security/chartnav-real-phi-readiness-status.md` against
  the buyer evidence index Section 5 + 11.
- **Pilot dry-run rehearsal**, exercising the new
  release-evidence gate + the new buyer evidence index end-to-end
  against a friendly practice.

None of these is a default; the operator should pick based on
which buyer conversation is most credible next quarter.
