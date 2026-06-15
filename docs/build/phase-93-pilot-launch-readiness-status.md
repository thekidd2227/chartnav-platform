# Phase 93 — Pilot Launch Readiness Status

**Date:** 2026-06-11
**Branch:** `feature/phase-93-pilot-launch-readiness-program`
**Base:** `main` after Phase 92 (`78cb395`)
**Status:** non-feature pilot-launch readiness phase — merges the
old Phase 98–99 workstreams (dry-run package, end-to-end demo
validation, security evidence review, real-PHI readiness review,
release evidence package, controlled pilot onboarding assets,
environment validation, production runbooks, disaster-recovery
validation, final smoke certification) into one operator program.

## Purpose

Phase 1 (Clinical Spine, complete) + Phase 2 (Clinical
Intelligence, substantially complete through Phase 92) + Phase 88
(Release Hardening + Pilot Evidence Gate, merged) gave ChartNav
every functional surface needed to run a controlled fake-data
buyer demo and prepare a named practice for a controlled pilot.

Phase 93 collapses the launch readiness program into one
operator-visible bundle:

1. A single dry-run runbook for the operator.
2. A single end-to-end validation checklist for the build.
3. A single real-PHI readiness review form for the security
   conversation.
4. A single GO / NO-GO form for the controlled-pilot launch
   decision.
5. A single command (`scripts/release/phase93_pilot_launch_gate.sh`)
   that produces one dated artifact bundle the ops lead can attach
   to the GO/NO-GO form.
6. This status index — the single document the operator opens
   when asked "what's pilot-ready, what isn't, and what's next?"

No clinical features were added. No clinical workflow behavior was
changed. No tests were weakened. No safety scanners were silenced.
No real PHI is processed by anything in this phase.

## Hard rules upheld

- No new clinical features.
- No new autonomous decision-making.
- No diagnosis, image interpretation, treatment / surgery /
  medication / IOL recommendation.
- No submission to registries, payers, CMS, IRIS, or EHRs.
- No production LLM. No live vendor scripts. No secrets touched.
- No real PHI in any environment produced by this phase.
- No HIPAA / SOC 2 / HITRUST / FDA / "certified EHR" /
  "EHR replacement" claims.

## What is feature-complete

| Layer | Status | Authoritative doc |
|---|---|---|
| Phase 1 Clinical Spine | complete | `docs/build/phase-75-completion-gate-core-closeout.md` |
| Phase 2 Clinical Intelligence (78–92) | complete through Phase 92 | `docs/build/phase-92-advanced-clinical-intelligence-layer.md` |
| Phase 77 Retina Visit Packet export | complete | `docs/build/phase-77-retina-visit-packet-export.md` |
| Phase 86 Subspecialty Adaptive Workspace | complete | `docs/build/phase-86-subspecialty-adaptive-workspace.md` |
| Phase 87 FHIR Export (read-only, `not_submitted`) | complete | `docs/build/phase-87-fhir-export-layer.md` |
| Phase 88 Release Hardening + Pilot Evidence Gate | complete | `docs/build/phase-88-release-hardening-pilot-evidence-gate.md` |
| Phase 91 Unified Workspace Engine | complete | `docs/build/phase-91-unified-workspace-engine.md` |
| Phase 92 Advanced Clinical Intelligence Layer | complete | `docs/build/phase-92-advanced-clinical-intelligence-layer.md` |
| Backend tiered release gate | complete | `scripts/release/backend_release_gate.sh` |
| Release evidence gate | complete | `scripts/release/chartnav_release_evidence_gate.sh` |
| Phase 93 pilot launch gate | new | `scripts/release/phase93_pilot_launch_gate.sh` |

## What is pilot-ready

| Capability | Status | Notes |
|---|---|---|
| Controlled fake-data buyer demo | **Pilot-ready** | Phase 93 dry-run runbook + end-to-end validation checklist gate the operator pre-flight. |
| Controlled-pilot kick-off conversation | **Pilot-ready** | Phase 93 GO/NO-GO doc collapses the launch decision into one signed form. |
| Provider-reviewed structured documentation | **Pilot-ready** | Phase 1 spine, immutable signed lock, metadata-only audit. |
| Phase 91 unified workspace + Phase 92 advanced intelligence panel | **Pilot-ready** | Both panels mount, both surface insufficient-data states, both enforce the safety boundaries. |
| FHIR R4 read-only export (DocumentReference) | **Pilot-ready** | Phase 87; pinned to `submission_status: not_submitted`, `transport: none`. |
| Operator release evidence capture | **Pilot-ready** | One command, one dated bundle, PASS/FAIL summary. |
| Documented hard non-claims | **Pilot-ready** | Enforced by claim scanners + runtime safety scanner + claim policy fixtures. |

## What is NOT approved

| Item | Status | Why |
|---|---|---|
| Real PHI in any environment | **Not approved** | Every Phase 93 real-PHI readiness review gate must be closed first. ChartNav alone cannot approve real PHI; the practice's BAA, security review, hosting, identity, logging, backup, DR, and incident-response approvals are joint prerequisites. |
| HIPAA / SOC 2 / HITRUST / FDA certification | **Not pursued in this build** | ChartNav supports the practice's HIPAA obligations contractually via BAA. SOC 2 / HITRUST / FDA are not in scope. |
| Certified EHR claim | **Never** | ChartNav is documentation + review support, not a certified EHR. |
| EHR replacement claim | **Never** | ChartNav lives alongside the practice's existing EHR. |
| Autonomous diagnosis / image interpretation / treatment / surgery / medication / IOL recommendation | **Never** | Enforced by the claim scanners. |
| Patient messaging / automated outreach | **Not built** | No patient-send surface exists. |
| Billing / coding / claims submission / EHR writeback | **Not built** | No write paths exist. |
| Production LLM | **Not enabled** | Every LLM-shaped surface is deterministic / fake adapter / disabled. |
| Live vendor scripts | **Not enabled** | `dev_live_watsonx_eval.py` and any live STT / live FHIR-write integration are gated and not part of any release. |

## What remains before real PHI

These items are the union of the Phase 18 controlled-pilot go-live
checklist (`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`)
and the Phase 93 real-PHI readiness review
(`docs/security/phase-93-real-phi-readiness-review.md`). They
cannot be solved by ChartNav alone:

1. **BAA executed.** Practice (covered entity) + ARCG Systems
   (business associate).
2. **Practice security review accepted.**
   `docs/pilot/chartnav-security-review-packet.md`.
3. **Production bearer JWT issuer + audience.** Practice-controlled
   identity provider; demo identities disabled.
4. **Production-grade Postgres + backups + PITR.** Practice-approved
   region.
5. **Audit log destination + retention.** Practice-approved; no PHI
   in logs.
6. **Backup + DR rehearsed within 90 days.** Verified restore.
7. **Incident + breach response runbook walked.**
   `docs/security/chartnav-incident-breach-response-runbook.md`.
8. **Named-user roster approved.** Practice administrator on
   record.
9. **Practice clinical + security + administrative sign-off in
   writing.** Section 12 of the real-PHI readiness review.
10. **Locked go-live date.** Recorded in writing on the GO/NO-GO
    form.

## Which command proves release readiness

```
bash scripts/release/phase93_pilot_launch_gate.sh
```

Output:

- `artifacts/phase-93-pilot-launch/<YYYYMMDD-HHMMSS>/summary.txt`
  with `OVERALL: PASS` on success.
- `artifacts/phase-93-pilot-launch/<YYYYMMDD-HHMMSS>/release-evidence/`
  pointing at the Phase 88 evidence bundle the gate produced as
  part of R1.
- `artifacts/phase-93-pilot-launch/<YYYYMMDD-HHMMSS>/01-release-evidence-gate.log`
  with the full Phase 88 gate output (backend tiered release gate,
  frontend typecheck, vitest, all five claim scanners, runtime
  safety, git diff --check, claim policy fixtures).

If the optional Phase 63C smoke is reachable (`PHASE63C_API_URL`
and `PHASE63C_WEB_URL` answer), `O1-phase63c-smoke.log` is also
written.

## Exact next-phase recommendation

**Recommendation:** Phase 100 — Controlled Pilot Launch Gate.

Phase 100 is the **named-practice launch decision**. It takes the
generic Phase 93 GO/NO-GO form and instantiates it for a specific
prospective pilot site, with the practice's clinical, security,
administrative, and commercial owners on the signature page. It is
not a software phase — it is the operator + practice signing the
form, locking the date, and either starting the controlled pilot
or going back to fake-data demo while gates close.

Phase 100 requires:

- This Phase 93 status doc, current within 30 days of the launch
  decision.
- The Phase 93 pilot launch gate PASS on the launch SHA.
- The Phase 93 real-PHI readiness review fully signed (if real PHI
  is in scope) **or** an explicit "fake-data controlled pilot only"
  scope locked in writing.
- The Phase 18 controlled-pilot go-live checklist fully signed (if
  real PHI is in scope).
- A named practice with a named clinical owner, security owner,
  and administrator.
- A locked go-live date.

Until Phase 100 is signed, ChartNav remains a fake-data product
for that practice — regardless of how many gates are green here.

## Files

### New (Phase 93)

- `docs/pilot/phase-93-pilot-dry-run-runbook.md`
- `docs/pilot/phase-93-end-to-end-validation-checklist.md`
- `docs/pilot/phase-93-controlled-pilot-launch-go-no-go.md`
- `docs/security/phase-93-real-phi-readiness-review.md`
- `docs/build/phase-93-pilot-launch-readiness-status.md`
- `scripts/release/phase93_pilot_launch_gate.sh`

### Modified

- none. Phase 93 is doc + script only; no source changes.

## Risks closed

- **Scattered launch readiness evidence.** Phase 93 collapses the
  dry-run runbook, the end-to-end validation checklist, the
  real-PHI readiness review, and the GO/NO-GO form into one
  cross-referenced bundle.
- **Ad-hoc release commands.** Phase 93 ships one operator command
  (`phase93_pilot_launch_gate.sh`) that produces one dated bundle,
  delegating to the Phase 88 release evidence gate so the
  underlying checks remain authoritative and don't drift.
- **Implicit real-PHI assumption.** Phase 93 ships an explicit
  non-approval statement and a full sign-off matrix; the operator
  cannot accidentally treat "all gates green" as "real-PHI
  approved" — the matrix forces the question to its named owners.
- **Demo narration drift.** Phase 93 ships a forbidden-narration
  list inside the dry-run runbook that mirrors the claim scanner
  surface so an operator walks into a buyer demo with the same
  language enforced both verbally and in the repo.
