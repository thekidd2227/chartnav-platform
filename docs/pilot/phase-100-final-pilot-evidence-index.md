# Phase 100 — Final Pilot Evidence Index

**Status:** living index — updated per controlled-pilot decision
**Date:** 2026-06-15
**Repo SHA at writing:** `main` after Phase 93 (`fead0ae`)
**Phase context:** Phase 100 — Controlled Pilot Launch Gate

## Purpose

A single, dated index of every authoritative artifact a buyer,
practice security owner, or pilot reviewer needs to evaluate
ChartNav for a controlled pilot. Each section is one short
description plus a link to the in-repo source of truth.

This index does not duplicate content from the Phase 88 controlled-
pilot evidence index (`docs/pilot/chartnav-controlled-pilot-
evidence-index.md`); it adds the Phase 91 + Phase 92 + Phase 93 +
Phase 100 deltas and re-cross-references the underlying Phase 88
catalog.

## 1. Launch decision documents

| Document | Path |
|---|---|
| Phase 100 controlled pilot launch gate (this signature form) | `docs/pilot/phase-100-controlled-pilot-launch-gate.md` |
| Phase 100 no-real-PHI attestation | `docs/security/phase-100-no-real-phi-attestation.md` |
| Phase 100 controlled-pilot launch status | `docs/build/phase-100-controlled-pilot-launch-status.md` |
| Phase 93 controlled pilot launch GO/NO-GO (generic) | `docs/pilot/phase-93-controlled-pilot-launch-go-no-go.md` |
| Phase 93 real-PHI readiness review | `docs/security/phase-93-real-phi-readiness-review.md` |
| Phase 18 controlled-pilot go-live checklist | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` |
| Phase 65 controlled pilot go/no-go gate | `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md` |

## 2. Release evidence gates

| Command | Purpose | Path |
|---|---|---|
| `bash scripts/release/phase100_controlled_pilot_launch_gate.sh` | Final controlled-pilot launch gate. Delegates to Phase 93 + writes one dated bundle. | `scripts/release/phase100_controlled_pilot_launch_gate.sh` |
| `bash scripts/release/phase93_pilot_launch_gate.sh` | Pilot-launch evidence gate; delegates to Phase 88. | `scripts/release/phase93_pilot_launch_gate.sh` |
| `bash scripts/release/chartnav_release_evidence_gate.sh` | Tiered release evidence: backend gate, frontend typecheck, vitest, 5 claim scanners, runtime safety, git diff --check, claim policy fixtures. | `scripts/release/chartnav_release_evidence_gate.sh` |
| `bash scripts/release/backend_release_gate.sh` | Tiered backend pytest (1500s/tier budget). | `scripts/release/backend_release_gate.sh` |

## 3. Pilot dry-run + validation

| Document | Path |
|---|---|
| Phase 93 pilot dry-run runbook | `docs/pilot/phase-93-pilot-dry-run-runbook.md` |
| Phase 93 end-to-end validation checklist | `docs/pilot/phase-93-end-to-end-validation-checklist.md` |
| Phase 93 pilot launch readiness status | `docs/build/phase-93-pilot-launch-readiness-status.md` |
| Phase 65 pilot operator runbook | `docs/pilot/phase-65-pilot-operator-runbook.md` |
| Phase 65 issue + incident triage template | `docs/pilot/phase-65-issue-incident-triage-template.md` |
| Phase 65 success metric tracker schema | `docs/pilot/phase-65-success-metric-tracker-schema.md` |

## 4. Buyer demo + commercial readiness

| Document | Path |
|---|---|
| Phase 100 controlled-pilot buyer demo script (15min + 30min) | `docs/demo/phase-100-controlled-pilot-buyer-demo-script.md` |
| ChartNav demo operator guide | `docs/demo/chartnav-demo-operator-guide.md` |
| ChartNav demo environment doc | `docs/demo/chartnav-demo-environment.md` |
| ChartNav demo click path | `docs/demo/chartnav-demo-click-path.md` |
| Phase 24c retina demo runbook | `docs/demo/phase-24c-retina-demo-runbook.md` |
| Phase 61 controlled buyer demo runbook | `docs/demo/phase-61-controlled-buyer-demo-runbook.md` |
| Phase 61 buyer Q&A safe answers | `docs/demo/phase-61-buyer-qa-safe-answers.md` |
| Phase 62 end-to-end demo visit script | `docs/demo/phase-62-end-to-end-demo-visit-script.md` |
| Phase 62 controlled buyer demo evidence packet | `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` |
| Phase 62a buyer demo GO/NO-GO status | `docs/demo/phase-62a-buyer-demo-go-no-go-status.md` |

## 5. Smoke + functional verification

| Command | Purpose | Path |
|---|---|---|
| `bash scripts/demo/phase63c_functional_smoke.sh --reset` | End-to-end demo smoke (optional in launch gate; required when stack is local) | `scripts/demo/phase63c_functional_smoke.sh` |
| `bash scripts/reset_demo_state.sh` | Reset seeded state. Refuses non-local `DATABASE_URL`. | `scripts/reset_demo_state.sh` |

## 6. Safety scanners

| Command | Purpose | Path |
|---|---|---|
| `bash scripts/check_commercial_claims.sh` | Commercial-claim guardrail | `scripts/check_commercial_claims.sh` |
| `bash scripts/check_demo_claims.sh` | Demo-claim guardrail | `scripts/check_demo_claims.sh` |
| `bash scripts/check_website_claims.sh` | Public-site claim guardrail | `scripts/check_website_claims.sh` |
| `bash scripts/check_pilot_readiness.sh` | Pilot-readiness claim guardrail | `scripts/check_pilot_readiness.sh` |
| `bash scripts/test_claim_policy_fixtures.sh` | Claim policy fixture suite | `scripts/test_claim_policy_fixtures.sh` |
| `python3 scripts/check_runtime_safety.py` | Runtime safety scanner (no unsafe combinations) | `scripts/check_runtime_safety.py` |

## 7. Security artifacts

| Document | Path |
|---|---|
| Real-PHI readiness status | `docs/security/chartnav-real-phi-readiness-status.md` |
| Real-PHI go-live gate | `docs/security/chartnav-real-phi-go-live-gate.md` |
| HIPAA readiness control matrix | `docs/security/chartnav-hipaa-readiness-control-matrix.md` |
| BAA + vendor readiness checklist | `docs/security/chartnav-baa-vendor-readiness-checklist.md` |
| Access control policy | `docs/security/chartnav-access-control-policy.md` |
| Backup + DR policy | `docs/security/chartnav-backup-disaster-recovery-policy.md` |
| Customer responsibility matrix | `docs/security/chartnav-customer-responsibility-matrix.md` |
| Incident + breach response runbook | `docs/security/chartnav-incident-breach-response-runbook.md` |
| Incident response plan | `docs/security/chartnav-incident-response-plan.md` |
| Monitoring + logging readiness | `docs/security/chartnav-monitoring-logging-readiness.md` |
| Production auth readiness | `docs/security/chartnav-production-auth-readiness.md` |
| Subprocessor inventory | `docs/security/chartnav-subprocessor-inventory.md` |
| Support PHI handling policy | `docs/security/chartnav-support-phi-handling-policy.md` |
| PHI data flow map | `docs/security/chartnav-phi-data-flow-map.md` |
| LLM provider decision memo | `docs/security/chartnav-llm-provider-decision-memo.md` |
| LLM vendor evaluation | `docs/security/chartnav-llm-vendor-evaluation.md` |
| STT vendor readiness | `docs/security/chartnav-stt-vendor-readiness.md` |

## 8. Known limitations + non-goals

| Document | Path |
|---|---|
| ChartNav known limitations and non-goals | `docs/pilot/chartnav-known-limitations-and-non-goals.md` |
| Security review packet | `docs/pilot/chartnav-security-review-packet.md` |
| Phase 66 — what not to promise cheat sheet | `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md` |
| Phase 64 — paid pilot positioning | `docs/commercial/phase-64-paid-pilot-positioning.md` |

## 9. Buyer evidence packet (Phase 88 consolidated)

| Document | Path |
|---|---|
| Phase 88 controlled-pilot evidence index | `docs/pilot/chartnav-controlled-pilot-evidence-index.md` |
| Phase 64 security review packet index | `docs/commercial/phase-64-security-review-packet-index.md` |
| Phase 64 buyer qualification checklist | `docs/commercial/phase-64-buyer-qualification-checklist.md` |
| Phase 64 one-page buyer brief | `docs/commercial/phase-64-one-page-buyer-brief.md` |
| Phase 64 demo asset index | `docs/commercial/phase-64-demo-asset-index.md` |
| Phase 64 pilot success metrics | `docs/commercial/phase-64-pilot-success-metrics.md` |
| Approved claims language | `docs/commercial/chartnav-approved-claims-language.md` |
| Ophthalmology positioning language guide | `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md` |

## 10. Phase build docs (Phase 1 spine + Phase 2 intelligence)

| Phase | Doc |
|---|---|
| Phase 75 completion gate (core closeout) | `docs/build/phase-75-completion-gate-core-closeout.md` |
| Phase 76 retina visit summary | `docs/build/phase-76-retina-visit-summary-aggregator.md` |
| Phase 77 retina visit packet | `docs/build/phase-77-retina-visit-packet-export.md` |
| Phase 78 anti-VEGF rail | `docs/build/phase-78-anti-vegf-retina-operating-rail.md` |
| Phase 79 glaucoma cockpit | `docs/build/phase-79-glaucoma-progression-cockpit.md` |
| Phase 80 cataract workflow | `docs/build/phase-80-cataract-surgical-workflow.md` |
| Phase 81 provider action queue | `docs/build/phase-81-provider-action-item-queue.md` |
| Phase 82 note validation rail | `docs/build/phase-82-note-validation-rail.md` |
| Phase 83 acknowledgement persistence | `docs/build/phase-83-pre-sign-acknowledgement-persistence.md` |
| Phase 84 disease staging | `docs/build/phase-84-disease-staging-protocol-engine.md` |
| Phase 85 medication safety | `docs/build/phase-85-medication-safety-adherence-engine.md` |
| Phase 86 subspecialty adaptive workspace | `docs/build/phase-86-subspecialty-adaptive-workspace.md` |
| Phase 87 FHIR export | `docs/build/phase-87-fhir-export-layer.md` |
| Phase 88 release hardening + pilot evidence gate | `docs/build/phase-88-release-hardening-pilot-evidence-gate.md` |
| Phase 88 imaging metadata review linkage | `docs/build/phase-88-imaging-metadata-review-linkage.md` |
| Phase 89 quality intelligence | `docs/build/phase-89-quality-intelligence.md` |
| Phase 90 ophthalmic medication safety | `docs/build/phase-90-ophthalmic-medication-safety-adherence-engine.md` |
| Phase 91 unified workspace engine | `docs/build/phase-91-unified-workspace-engine.md` |
| Phase 92 advanced clinical intelligence | `docs/build/phase-92-advanced-clinical-intelligence-layer.md` |
| Phase 93 pilot launch readiness status | `docs/build/phase-93-pilot-launch-readiness-status.md` |
| Phase 100 controlled-pilot launch status | `docs/build/phase-100-controlled-pilot-launch-status.md` |

## How to use this index

1. Before a launch decision, open this file and confirm every link
   resolves to a current artifact.
2. Run `bash scripts/release/phase100_controlled_pilot_launch_gate.sh`
   and attach the dated artifact bundle path to the launch GO/NO-GO
   form.
3. Hand a copy of this index plus the Phase 88 controlled-pilot
   evidence index to the practice's security reviewer.
4. Keep the launch SHA + artifact dir + signed Phase 100 launch
   gate form in the practice's pilot folder (out-of-repo).
