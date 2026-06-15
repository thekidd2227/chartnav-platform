# Phase 100 — Controlled Pilot Launch Gate

**Status:** decision document — final launch gate
**Date:** 2026-06-15
**Audience:** ChartNav operator, ARCG ops lead, ARCG commercial
owner, prospective pilot practice's clinical + security +
administrative owners
**Branch:** `feature/phase-100-controlled-pilot-launch-gate`
**Base:** `main` after Phase 93 (`fead0ae`)

## Executive status

ChartNav is **feature-complete** for a controlled fake-data
ophthalmology pilot:

- Phase 1 Clinical Spine — vitals → visit draft → fundus chart →
  provider-reviewed signed lock with metadata-only audit trail.
- Phase 2 Clinical Intelligence — 78 through 92 (anti-VEGF rail,
  glaucoma cockpit, cataract workflow, action queue, validation
  rail, acknowledgement persistence, disease staging, medication
  safety, FHIR export, imaging metadata, quality intelligence,
  ophthalmic medication safety, advanced clinical intelligence).
- Phase 86 subspecialty adaptive workspace + Phase 91 unified
  workspace engine + Phase 92 advanced clinical intelligence
  panel — all mounted, all surface insufficient_data states, all
  enforce safety boundaries.
- Phase 87 FHIR export — read-only DocumentReference; pinned to
  `submission_status: not_submitted`, `transport: none`.
- Phase 88 release hardening + pilot evidence gate — single
  operator command, dated artifact bundle, PASS/FAIL summary.
- Phase 93 pilot launch readiness program — dry-run runbook,
  end-to-end validation checklist, real-PHI readiness review,
  generic GO/NO-GO form, launch gate script, status index.

Phase 100 is the **decision step**: a named practice signs the
launch decision in this document and the operator either kicks off
the controlled pilot or returns to fake-data demo while gates close.

This document does **not** approve real PHI on its own. Real PHI
requires every gate in
`docs/security/phase-93-real-phi-readiness-review.md` and
`docs/security/phase-100-no-real-phi-attestation.md` and
`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` to
close with written, dated, attributable evidence.

## Launch scope

The launch is one of two scopes — pick exactly one for this form
and check the matching box:

- [ ] **Scope A — Controlled fake-data pilot.** A named practice
  uses ChartNav against synthetic seed data only. No real
  patients, no real PHI, no production identity provider. Phase 18
  + Phase 93 + Phase 100 real-PHI gates may remain open. Outcome
  on this form gates the start.
- [ ] **Scope B — Controlled real-PHI pilot.** A named practice
  uses ChartNav against real patients. Every Phase 18 + Phase 93
  + Phase 100 gate must close. The signed real-PHI readiness
  review and the signed Phase 18 go-live checklist must be on
  file before the box can be checked.

## Demo-only vs real-PHI boundary

| Item | Scope A (fake-data) | Scope B (real PHI) |
|---|---|---|
| Patient data | seeded synthetic only | live PHI from practice EHR or direct entry |
| Identity provider | demo `chartnav.local` allowed | production OIDC issuer, demo identities disabled |
| Database | local SQLite or staging Postgres with fake seed | production Postgres + PITR + practice-approved region |
| Audit log destination | local file | practice-approved log destination with retention agreement |
| Backup | not required for scope A | rehearsed, verified, RTO/RPO signed |
| Incident response | informal | runbook walked, on-call rotation locked |
| BAA | not required for scope A | executed before any session starts |
| Practice sign-off | clinical + administrative | clinical + administrative + security/CISO |

## Required approvals

Every named role below must sign the bottom of this form for the
launch to be GO. A missing signature is automatically NO-GO.

| # | Approver | Scope A | Scope B |
|---|---|---|---|
| 1 | Practice clinical owner | required | required |
| 2 | Practice administrator | required | required |
| 3 | Practice security owner / CISO | not required | required |
| 4 | ARCG ops owner (Jean-Max / ARCG Systems) | required | required |
| 5 | ARCG commercial owner | required | required |
| 6 | ARCG legal | not required | required |

## Technical readiness

Every row must be GREEN before the launch is recommended.

| # | Criterion | Evidence | Status |
|---|---|---|---|
| T1 | Phase 100 controlled pilot launch gate PASS on the launch SHA | `artifacts/phase-100-controlled-pilot-launch/<latest>/summary.txt` | ☐ |
| T2 | Phase 93 pilot launch gate PASS on the launch SHA | `artifacts/phase-93-pilot-launch/<latest>/summary.txt` | ☐ |
| T3 | Phase 88 release evidence gate PASS on the launch SHA | `artifacts/release-evidence/<latest>/summary.txt` | ☐ |
| T4 | `tsc --noEmit` clean | gate log | ☐ |
| T5 | vitest full suite green | gate log | ☐ |
| T6 | Backend tiered release gate green (Tier 1 + 2 + 3) | gate log | ☐ |
| T7 | All claim scanners green (commercial, website, demo, pilot readiness, claim policy fixtures) | gate logs | ☐ |
| T8 | `check_runtime_safety.py` PASS | gate log | ☐ |
| T9 | `git diff --check` clean | gate log | ☐ |

## Clinical workflow readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| C1 | Phase 93 end-to-end validation checklist green on the launch SHA | `docs/pilot/phase-93-end-to-end-validation-checklist.md` countersigned | ☐ |
| C2 | Phase 1 spine signs every artifact (vitals, draft, fundus) on encounter #1 | gate Section C–F | ☐ |
| C3 | Phase 2 intelligence panels render with no forbidden language | gate Section G–R | ☐ |
| C4 | Phase 87 FHIR export pinned to `not_submitted`/`transport: none` | gate Section S | ☐ |
| C5 | Phase 91 + Phase 92 panels mount with five safety boundaries asserted | gate Section R | ☐ |
| C6 | Phase 63C functional smoke PASS against the launch stack (Scope B only; Scope A may rely on the validation checklist alone) | smoke log | ☐ |

## Security readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| S1 | Phase 100 no-real-PHI attestation reviewed and acknowledged | `docs/security/phase-100-no-real-phi-attestation.md` countersigned | ☐ |
| S2 | Phase 93 real-PHI readiness review walked end-to-end (Scope B = required; Scope A = informational) | `docs/security/phase-93-real-phi-readiness-review.md` countersigned | ☐ |
| S3 | Phase 18 controlled-pilot go-live checklist walked end-to-end (Scope B only) | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` countersigned | ☐ |
| S4 | Named-user roster + role assignments approved by the practice administrator | roster export | ☐ |
| S5 | Practice security review packet accepted or conditionally accepted | `docs/pilot/chartnav-security-review-packet.md` signed cover letter | ☐ |
| S6 | Production OIDC issuer + audience locked (Scope B only) | identity provider config | ☐ |

## Evidence readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| E1 | Phase 100 final pilot evidence index reviewed and current | `docs/pilot/phase-100-final-pilot-evidence-index.md` | ☐ |
| E2 | Controlled-pilot evidence index (Phase 88) current within 30 days | `docs/pilot/chartnav-controlled-pilot-evidence-index.md` updated stamp | ☐ |
| E3 | Phase 93 dry-run runbook walked end-to-end on the launch SHA | dry-run report | ☐ |
| E4 | Screenshot + video clip evidence captured per the existing shot lists (Scope A controlled demos) | shot-list deliverables | ☐ |
| E5 | Every captured frame displays "demo mode — no real PHI" indicator | spot-check | ☐ |

## Buyer-demo readiness

| # | Criterion | Evidence | Status |
|---|---|---|---|
| B1 | Phase 100 controlled-pilot buyer demo script rehearsed at least once on the launch SHA | rehearsal notes | ☐ |
| B2 | Operator narration audited against the Phase 93 forbidden-narration list | rehearsal notes | ☐ |
| B3 | 15-minute walkthrough has been timed; 30-minute walkthrough has been timed | rehearsal stopwatch | ☐ |
| B4 | Demo patient reset works cleanly on the launch SHA | `scripts/reset_demo_state.sh` exit log | ☐ |
| B5 | Recovery steps tested for at least one mid-demo failure | rehearsal notes | ☐ |

## Open blockers

If any row above is RED, list it here with the named owner and the
target closure date. A row with an open blocker cannot be marked
GREEN.

| Row | Blocker | Owner | Target closure |
|---|---|---|---|
| | | | |

## Final GO / CONDITIONAL GO / NO-GO

| Outcome | Meaning |
|---|---|
| **GO** | Every required row is GREEN, every required signature present, the locked launch date is recorded. Practice may proceed at the locked date. |
| **CONDITIONAL GO** | At most two non-signature, non-security rows are open with named owner + closure date within 14 days. Practice may begin onboarding tasks; launch holds until rows close and the form is re-signed. |
| **NO-GO** | Any signature missing, any security row open (Scope B), any technical-readiness row open, or three or more rows open of any kind. Practice does not proceed; record blockers and remediation plan. |

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
**Locked launch scope:** Scope A (fake-data) / Scope B (real PHI)
**Phase 100 launch gate SHA:** __________
**Phase 100 launch gate artifact dir:** __________
**Next-review date:** __________ (no later than 30 days after launch)
