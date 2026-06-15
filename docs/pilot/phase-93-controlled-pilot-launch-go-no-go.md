# Phase 93 — Controlled Pilot Launch GO / NO-GO

**Status:** decision document
**Date:** 2026-06-11
**Audience:** ChartNav operator, ARCG ops lead, prospective pilot
practice's clinical + security + administrative owners
**Branch:** `feature/phase-93-pilot-launch-readiness-program`

## Purpose

Turn the Phase 93 readiness program into a single, attributable
GO / NO-GO decision for a named controlled pilot. This document
collapses the Phase 88 release-evidence gate, the Phase 91 +
Phase 92 functional readiness, the Phase 93 real-PHI readiness
review, and the buyer-evidence asset inventory into one form.

This document does **not** approve real PHI by itself — the
Phase 93 real-PHI readiness review
(`docs/security/phase-93-real-phi-readiness-review.md`) and the
Phase 18 controlled-pilot go-live checklist
(`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`)
remain authoritative for that decision. This form captures
controlled-pilot launch readiness (which may or may not include
real PHI depending on the prior two sign-offs).

## Decision states

| State | Meaning | Allowed next action |
|---|---|---|
| **GO** | Every required gate below is closed with evidence. Practice may move from fake-data demo to controlled pilot at the signed start date. | Sign Phase 18 + Phase 93 real-PHI gates if a real-PHI pilot is desired, then schedule kick-off. |
| **Conditional GO** | At most two non-blocker gates remain open with a named owner and a closure date within 14 days. | Close the named gates, then re-run this form. |
| **NO-GO** | Any blocker gate is open, OR more than two non-blocker gates are open, OR any safety scanner failed on the latest build. | Stop. Record blocker + owner + remediation plan. Do not announce a pilot start date. |

## GO criteria

Every row below must be GREEN before the practice is recommended
to proceed.

### A — Build + release evidence

| # | Criterion | Evidence | Status |
|---|---|---|---|
| A1 | Latest `main` builds clean (`git status` clean, `git diff --check` clean) | shell output | ☐ |
| A2 | Phase 88 release evidence gate PASS on the launch SHA | `artifacts/release-evidence/<latest>/summary.txt` | ☐ |
| A3 | Phase 93 pilot launch gate PASS on the launch SHA | `artifacts/phase-93-pilot-launch/<latest>/summary.txt` | ☐ |
| A4 | All five claim scanners PASS (commercial, website, demo, pilot readiness, runtime safety) | gate logs | ☐ |
| A5 | Backend tiered release gate PASS (Tier 1 + 2 + 3) | gate log | ☐ |
| A6 | Frontend `tsc --noEmit` clean, full vitest suite green | gate log | ☐ |

### B — Functional surfaces (Phase 1 + Phase 2)

| # | Criterion | Evidence | Status |
|---|---|---|---|
| B1 | Phase 93 end-to-end validation checklist green | `docs/pilot/phase-93-end-to-end-validation-checklist.md` countersigned | ☐ |
| B2 | Phase 1 clinical spine signs every artifact (vitals, draft, fundus) | gate Section C–F | ☐ |
| B3 | Phase 2 intelligence panels render with no forbidden language | gate Section G–R | ☐ |
| B4 | Phase 87 FHIR export pinned to `not_submitted` / `transport: none` | gate Section S | ☐ |
| B5 | Phase 91 unified workspace + Phase 92 advanced clinical intelligence panel mount correctly | gate Section R | ☐ |
| B6 | Phase 63C functional smoke PASS against the launch stack (if reachable) | smoke log | ☐ |

### C — Buyer evidence assets

| # | Criterion | Evidence | Status |
|---|---|---|---|
| C1 | Phase 93 pilot dry-run runbook walked end-to-end at least once on the launch SHA | dry-run report | ☐ |
| C2 | Screenshot + video clip evidence captured per existing shot lists; every frame labelled "demo mode — no real PHI" | shot-list deliverables | ☐ |
| C3 | Demo and pilot narration audited against the forbidden-narration list | dry-run report | ☐ |
| C4 | Phase 88 controlled-pilot evidence index reviewed | `docs/pilot/chartnav-controlled-pilot-evidence-index.md` updated stamp | ☐ |

### D — Security + access readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| D1 | Phase 93 real-PHI readiness review walked end-to-end (regardless of go-live outcome) | `docs/security/phase-93-real-phi-readiness-review.md` countersigned | ☐ |
| D2 | Phase 18 controlled-pilot go-live checklist walked end-to-end (if real PHI is in scope) | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` countersigned | ☐ |
| D3 | Named-user roster + role assignment approved by the practice administrator | roster export | ☐ |
| D4 | Practice security review packet accepted (or conditionally accepted) | `docs/pilot/chartnav-security-review-packet.md` signed cover letter | ☐ |

### E — Ops + monitoring readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| E1 | Backup + DR rehearsal complete within 90 days | rehearsal log | ☐ |
| E2 | Monitoring + alerting destinations confirmed live | alerting config screenshot | ☐ |
| E3 | Incident response on-call rotation locked for the pilot window | rotation export | ☐ |
| E4 | Support runbook (`docs/pilot/chartnav-support-runbook.md`) walked through with both sides | walkthrough notes | ☐ |
| E5 | First-week monitoring cadence locked | monitoring schedule | ☐ |

### F — Commercial + contract readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| F1 | Pilot agreement signed | signed PDF | ☐ |
| F2 | Pricing acknowledged in writing | email thread | ☐ |
| F3 | Pilot success metrics agreed (`docs/pilot/chartnav-pilot-success-metrics.md`) | countersigned doc | ☐ |
| F4 | Pilot exit criteria + decision date locked | decision memo | ☐ |

## NO-GO criteria

The launch is **NO-GO** if any of these are true on the launch
SHA — independent of how green the GO criteria appear:

### Build / release blockers

- The Phase 88 release evidence gate returns FAIL on any required
  check.
- The Phase 93 pilot launch gate returns FAIL on any required
  check.
- Any of the five claim scanners is silenced, allowlisted around,
  or returns FAIL.
- `git diff --check` reports whitespace damage on the launch SHA.
- The backend tiered release gate FAILS at any tier.
- `tsc --noEmit` reports an error or the vitest suite has any
  failing test.

### Functional blockers

- Phase 1 clinical spine cannot complete vitals → draft → fundus →
  signed-lock on encounter #1.
- Any Phase 2 panel renders forbidden-language content.
- FHIR export readiness reports anything other than
  `submission_status: not_submitted`.
- The Phase 92 advanced clinical intelligence panel fails to
  surface the five safety boundaries.

### Demo blockers

- Buyer narration contains any phrase on the Phase 93 dry-run
  forbidden-narration list.
- Captured screenshots or videos display anything other than
  synthetic seeded patient identifiers.
- "Demo mode — no real PHI" label is absent from any captured
  frame that displays clinical data.

### Security blockers

- Any Section 2 (BAA + vendor), Section 5 (logging + audit), or
  Section 6 (backup + DR) gate in the Phase 93 real-PHI readiness
  review is open AND real PHI is in scope.
- Production identity provider (OIDC issuer / audience) is not
  locked AND real PHI is in scope.
- Named-user roster is not approved by the practice administrator.

### Evidence blockers

- Phase 88 controlled-pilot evidence index is stale (older than
  30 days) relative to the launch SHA.
- Phase 93 dry-run runbook has not been walked through on the
  launch SHA.

## Out-of-scope (still forbidden, even at GO)

- **Production LLM.** Every LLM-shaped surface remains
  deterministic / fake adapter / disabled.
- **Real vendor scripts.** Do not run `dev_live_watsonx_eval.py`,
  do not enable a live STT vendor, do not pin a production
  embedding provider.
- **Patient messaging.** ChartNav does not text, email, post, or
  call patients at any tier.
- **Billing / coding / claims submission.** ChartNav does not
  bill, code, submit, or transmit any claim at any tier.
- **EHR writeback.** ChartNav does not write back to the
  practice's EHR at any tier.
- **Autonomous diagnosis / treatment / image interpretation /
  surgery / medication recommendations / IOL recommendations.**
  Never. Including under real PHI.

## Sign-off

The launch is approved when every signer marks GO and the launch
date is locked in writing.

| Role | Name | Outcome | Signature | Date |
|---|---|---|---|---|
| Practice clinical owner | ___________________ | GO / Conditional / NO-GO | ___________________ | __________ |
| Practice security owner / CISO | ___________________ | GO / Conditional / NO-GO | ___________________ | __________ |
| Practice administrator | ___________________ | GO / Conditional / NO-GO | ___________________ | __________ |
| ARCG ops owner | ___________________ | GO / Conditional / NO-GO | ___________________ | __________ |
| ARCG commercial owner | ___________________ | GO / Conditional / NO-GO | ___________________ | __________ |

**Locked launch date:** __________
**Next-review date:** __________ (no later than 30 days after launch)
**Phase 93 launch gate SHA:** __________
**Phase 93 launch gate artifact dir:** __________
