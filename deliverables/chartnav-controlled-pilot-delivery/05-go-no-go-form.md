# Controlled Pilot Launch GO / NO-GO Form

**Audience:** Practice clinical owner, administrator, security
owner; ARCG ops + commercial + legal
**Source of truth:** mirrors
`docs/pilot/phase-100-controlled-pilot-launch-gate.md` (in repo)
**Posture:** This form alone does **not** approve real PHI.

## Launch scope — pick exactly one

- [ ] **Scope A — Controlled fake-data pilot.** Synthetic seed
  data only. No real patients, no production identity provider.
  Phase 18 + Phase 93 + Phase 100 real-PHI gates may remain open.
- [ ] **Scope B — Controlled real-PHI pilot.** Real patients.
  Every Phase 18 + Phase 93 + Phase 100 gate must close. The
  signed real-PHI readiness review and the signed Phase 18
  go-live checklist must be on file before this box can be
  checked.

## Required approvals

| # | Approver | Scope A | Scope B |
|---|---|---|---|
| 1 | Practice clinical owner | required | required |
| 2 | Practice administrator | required | required |
| 3 | Practice security owner / CISO | not required | **required** |
| 4 | ARCG ops owner | required | required |
| 5 | ARCG commercial owner | required | required |
| 6 | ARCG legal | not required | **required** |

A missing required signature is automatically NO-GO.

## A. Build + release evidence

| # | Criterion | Evidence | Status |
|---|---|---|---|
| A1 | Latest `main` builds clean; `git status` + `git diff --check` clean on the launch SHA | shell output | ☐ |
| A2 | Phase 88 release evidence gate PASS on the launch SHA | `artifacts/release-evidence/<latest>/summary.txt` | ☐ |
| A3 | Phase 100 controlled-pilot launch gate PASS on the launch SHA | `artifacts/phase-100-controlled-pilot-launch/<latest>/summary.txt` + `go-no-go.txt` | ☐ |
| A4 | Phase 101 buyer-demo evidence capture PASS on the launch SHA | `artifacts/buyer-demo/<latest>/summary.txt` | ☐ |
| A5 | All claim scanners PASS | commercial, website, demo, pilot readiness, claim policy fixtures | ☐ |
| A6 | Backend tiered release gate PASS (Tier 1 + 2 + 3) | gate log | ☐ |
| A7 | Frontend `tsc --noEmit` clean + full vitest green | gate log | ☐ |

## B. Functional surfaces

| # | Criterion | Evidence | Status |
|---|---|---|---|
| B1 | Phase 1 clinical spine signs vitals → draft → fundus on encounter #1 | `02-buyer-demo-runbook.md` Section 3 + audit-log spot-check | ☐ |
| B2 | Phase 2 intelligence panels render with no forbidden language | gate log + manual spot-check | ☐ |
| B3 | Phase 87 FHIR export pinned to `submission_status: not_submitted` / `transport: none` | gate log | ☐ |
| B4 | Phase 91 + Phase 92 panels mount with five safety boundaries asserted | gate log + UI spot-check | ☐ |
| B5 | Phase 63C functional smoke PASS against the launch stack (required for Scope B; recommended for Scope A) | `O1-phase63c-smoke.log` (in the Phase 101 bundle) | ☐ |

## C. Buyer evidence assets

| # | Criterion | Evidence | Status |
|---|---|---|---|
| C1 | Buyer demo rehearsed end-to-end on the launch SHA (15-min and/or 30-min) | rehearsal stopwatch + notes | ☐ |
| C2 | No forbidden narration during the rehearsal | rehearsal notes | ☐ |
| C3 | (Scope A) Captured screenshots / videos, if any, display "demo mode — no real PHI" in every frame | spot-check | ☐ |

## D. Security + access readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| D1 | `06-no-real-phi-attestation.md` walked end-to-end (Scope A: informational; Scope B: countersigned) | this folder | ☐ |
| D2 | Phase 93 real-PHI readiness review walked end-to-end (Scope B only) | `docs/security/phase-93-real-phi-readiness-review.md` (in repo) | ☐ |
| D3 | Phase 18 controlled-pilot go-live checklist walked end-to-end (Scope B only) | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` (in repo) | ☐ |
| D4 | Named-user roster + role assignments approved (Scope A: lightweight; Scope B: practice administrator on record) | roster export | ☐ |
| D5 | Production OIDC issuer + audience locked (Scope B only) | identity provider config | ☐ |

## E. Ops + monitoring readiness (Scope B)

| # | Criterion | Evidence | Status |
|---|---|---|---|
| E1 | Backup + DR rehearsal within 90 days | rehearsal log | ☐ |
| E2 | Monitoring + alerting destinations confirmed live | alerting config screenshot | ☐ |
| E3 | Incident response on-call rotation locked for the pilot window | rotation export | ☐ |
| E4 | First-week monitoring cadence locked | monitoring schedule | ☐ |

## F. Commercial + contract readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| F1 | Pilot agreement signed | signed PDF | ☐ |
| F2 | Pricing acknowledged in writing | email thread | ☐ |
| F3 | Pilot success metrics agreed | countersigned doc | ☐ |
| F4 | Pilot exit criteria + decision date locked | decision memo | ☐ |

## NO-GO triggers (any one → NO-GO)

- Any required signature missing.
- Any Phase 88 / 100 / 101 gate row FAIL.
- Any claim scanner FAIL (silenced or allowlisted → NO-GO).
- Forbidden narration during the rehearsal.
- Any Scope B security row open with real PHI in scope.

## Decision

| Outcome | Meaning |
|---|---|
| **GO** | Every required row GREEN; every required signature present; launch date locked. |
| **CONDITIONAL GO** | At most two non-signature, non-security rows open with named owner + closure date within 14 days. |
| **NO-GO** | Any signature missing, any security row open (Scope B), any required-build row open, or 3+ rows open. |

## Sign-off

| Role | Name | Outcome | Signature | Date |
|---|---|---|---|---|
| Practice clinical owner | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |
| Practice administrator | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |
| Practice security owner / CISO (Scope B) | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |
| ARCG ops owner | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |
| ARCG commercial owner | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |
| ARCG legal (Scope B) | ___________________ | GO / CONDITIONAL / NO-GO | ___________________ | __________ |

**Locked launch date:** __________
**Locked scope:** Scope A (fake-data) / Scope B (real PHI)
**Launch SHA:** __________
**Phase 100 launch gate artifact dir:** __________
**Phase 101 capture artifact dir:** __________
**Next-review date:** __________ (no later than 30 days after launch)
