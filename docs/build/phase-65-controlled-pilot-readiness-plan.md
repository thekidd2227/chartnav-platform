# Phase 65 Controlled Pilot Readiness Plan

Date: 2026-05-20
Status: planning artifact only
Scope: docs-only pilot-readiness plan after Phase 63C buyer-demo functional smoke repair

## 1. Executive Summary

Phase 65 is **not a launch**.

Phase 65 is a controlled pilot readiness plan: it defines what must be true before any paid pilot touches real PHI or live clinical operations. It is intentionally separate from Phase 64 buyer outreach materials.

Phase 64 outreach may continue with fake-data demo positioning, because Phase 63C establishes buyer-demo functional readiness for the controlled fake-data path. Real-PHI pilot use remains gated behind security review, legal approval, environment validation, access-control review, backup/restore posture, incident-response readiness, and explicit written approval.

Current recommendation:

- Fake-data buyer-demo conversations may proceed when the Phase 63C smoke is green.
- Paid pilot conversations may proceed as discovery and qualification.
- Real-PHI pilot operation must not start until every Gate 2 and Gate 3 requirement in this plan is closed with evidence.
- No production LLM should be enabled as part of Phase 65.

## 2. Readiness Basis

Phase 63C status on current `main`:

- `main` includes `8d2b6dd fix(demo): repair vitals transition in functional smoke (#83)`.
- Phase 63C functional smoke is expected to finish with `BUYER-DEMO FUNCTIONAL GO: YES`.
- The stated smoke result is **20 pass / 0 fail** after the Phase 63C-2 vitals transition repair.

What Phase 63C proves:

- The controlled fake-data demo stack can reach the API and frontend.
- The local demo DB can be migrated to Alembic head and contain required tables.
- The seeded fake clinician and Morgan Lee encounter can be validated.
- The fake-data Vitals workflow can create, advance to entered, review, and sign.
- The fake-data VisitDraft workflow can create, draft, review, and finalize.
- The fake-data Fundus workflow can generate, review, and sign.
- Manual-note validation rejects invalid string payloads and accepts shaped object payloads.
- Feature API routes are no longer landing on the Vite origin during the smoke.

What Phase 63C does **not** prove:

- It does not approve real PHI.
- It does not approve live clinical operations.
- It does not prove a practice security review has passed.
- It does not prove legal agreements, BAA, DPA, or subprocessor approvals are complete.
- It does not prove production authentication, monitoring, backup/restore, incident contacts, audit retention, or environment separation are configured for a specific practice.
- It does not approve a production LLM, STT vendor, OpenAI, Anthropic, IBM watsonx, device integration, EHR writeback, remote patient monitoring, orders, referrals, messages, billing, or coding.

## 3. Pilot Gate Taxonomy

| Gate | Entry criteria | Allowed activities | Forbidden activities | Evidence required | Owner | Exit criteria |
| --- | --- | --- | --- | --- | --- | --- |
| Gate 0: fake-data demo only | Current `main` synced; Phase 63C smoke green; runtime safety and claim scanners pass; demo uses synthetic Morgan Lee data or other clearly synthetic records | Controlled fake-data demo, internal dry run, screenshot/video review, buyer discovery with safe boundaries | Real PHI, live clinical use, production LLM, real vendor API keys, public compliance claims, EHR replacement claims | `scripts/demo/phase63c_functional_smoke.sh` output; release/safety checks; Phase 61/62 runbooks | Demo operator / QA owner | Buyer can understand product truth and qualifies for Gate 1 conversation |
| Gate 1: paid pilot conversation | Gate 0 passed; buyer understands fake-data-only demo; buyer fits target profile; no immediate demand for certified EHR replacement or autonomous workflow | Paid pilot discovery, workflow fit review, user/role mapping, security-review scheduling, pilot-scope hypothesis | Processing real PHI, promising deployment dates, promising compliance certification, enabling live vendors, making ROI guarantees | Phase 64 qualification checklist when merged; Phase 61 Q&A; current product truth | Commercial owner with QA/safety support | Buyer requests security review and agrees no real PHI before Gate 3 |
| Gate 2: security review | Buyer identifies clinical champion, security/compliance owner, IT owner; security packet is shared; pilot scope is narrow | Review security packet, access model, hosting, backup, incident response, retention, vendor/subprocessor posture, workflow boundaries | Real PHI ingestion, production deployment, external LLM/STT PHI egress, unapproved integrations | `docs/pilot/chartnav-security-review-packet.md`; `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`; relevant security docs; gaps list | Practice security/compliance owner + ChartNav security owner | Security owner gives written conditional approval or names blockers |
| Gate 3: limited real-PHI pilot approval | Gate 2 closed; BAA/legal review complete if applicable; controlled-pilot environment approved; auth, RBAC, audit, backup, logging, incident contacts validated | Limited real-PHI pilot with named users, named workflows, defined dates, limited locations, support cadence, stop criteria | Demo/fake-data adapters with real PHI, production LLM unless separately approved, broad rollout, unsupervised use, unapproved vendor egress | Signed legal/security approval; environment validator output; access review; backup/restore evidence; incident contact sheet stored out-of-repo | Practice approver + ChartNav pilot owner | First real-PHI session authorized in writing |
| Gate 4: monitored pilot operation | Gate 3 approval; users onboarded; support route active; success metrics defined; rollback path approved | Monitored limited pilot, daily/weekly check-ins, issue triage, manual metrics collection, safety-boundary review | Scope expansion, new locations, new vendors, new LLM/STT path, unattended clinical automation, public claims from pilot results | Pilot issue log; weekly metric summary; safety exceptions log; support/incident records | Pilot operations owner + practice champion | Pilot period completes without unresolved S1/S2 blockers or is stopped safely |
| Gate 5: expansion decision | Gate 4 complete; metrics reviewed; safety issues closed; practice gives feedback | Expansion/no-expansion decision, revised scope, renewal/next pilot planning, security delta review | Assuming success from demo metrics, publishing claims without approval, expanding before unresolved safety gaps close | Exit memo; success metrics; open risks; practice decision; updated security review if scope changes | Business owner + practice decision maker | Go/no-go decision for next contract, renewal, or stop |

## 4. Real-PHI Blockers

The following must be resolved before any real PHI is processed. Do not treat these as complete unless evidence exists for the specific practice and environment.

| Blocker | Current evidence / source | Required before real PHI |
| --- | --- | --- |
| Security review | Security-review packet exists in `docs/pilot/chartnav-security-review-packet.md` | Practice security owner reviews and accepts it, with gaps tracked |
| Access controls | Product truth and pilot docs describe RBAC/org isolation | Practice users provisioned; roles reviewed; reviewer/technician restrictions validated in target environment |
| Audit logging review | Docs state metadata-only audit posture and sentinel tests | Practice agrees audit retention; target environment logging reviewed for sensitive content exposure |
| Data retention policy | Retention questions exist in pilot docs | Practice-specific retention period and deletion/export expectations documented |
| BAA / legal review if applicable | Controlled-pilot checklist requires BAA and pilot agreement | Executed agreement(s) stored out-of-repo; subprocessor obligations reviewed |
| Incident response contact/process | `docs/security/chartnav-incident-response-plan.md` exists | Practice contacts, escalation timing, evidence preservation, and notification workflow confirmed |
| Environment separation | Product truth separates demo and controlled-pilot modes | Demo/fake-data environment cannot be mistaken for real-PHI pilot environment |
| Backup/restore posture | Backup/DR policy exists; scripts are referenced | Practice-approved destination, backup cadence, restore test, and monitoring evidence complete |
| Vendor/API key policy | Runtime safety validator and vendor docs gate LLM/STT | No live vendor egress unless separately approved; no secrets printed or committed |
| LLM disabled or separately approved | Current product truth says no production LLM is approved | Keep LLM disabled for pilot unless separate security/legal/vendor path is approved |
| Role-based access validation | Tests and docs exist | Run target-environment RBAC smoke for admin/clinician/technician/reviewer if applicable |
| Logging does not expose sensitive content | Security docs describe PHI-safe logging | Confirm request bodies, Authorization headers, transcript text, vitals values, fundus findings, and notes are absent from logs |
| Demo/fake-data mode separated from pilot mode | Demo runbooks and product truth require fake data | Operator must have a clear visible environment label and separate startup/config path |

## 5. Pilot Operating Model

Who can use it:

- Named users only.
- Pilot clinician(s), technician(s), and a practice admin/security contact.
- No broad practice-wide rollout during initial pilot operation.
- Reviewer/front-desk roles only if the final pilot scope explicitly needs them and RBAC is validated.

Allowed use cases:

- Structured technician intake and vitals for provider review.
- Provider-reviewed VisitDraft assist from approved transcript inputs.
- Provider-reviewed fundus drawing assist from clinician-entered findings.
- Doctor review, attestation, and signed lock.
- Manual operational metric collection.

Prohibited use cases:

- Real-PHI use before Gate 3 approval.
- Autonomous documentation or unattended note finalization.
- Diagnosis, image interpretation, OCT interpretation, treatment recommendation, orders, referrals, patient messages, billing, coding, device integration, or remote patient monitoring.
- Production LLM or external STT vendor processing without separate approval.
- Public claims based on pilot anecdotes before review and approval.

Fake-data demo vs real-PHI pilot distinction:

- Fake-data demo: synthetic patient data, local/demo environment, Phase 63C smoke, buyer demonstration only.
- Real-PHI pilot: controlled-pilot environment, signed legal/security approval, named users, monitored operation, documented stop criteria.

Support escalation path:

- S1: suspected data-safety incident, cross-org leak, sensitive content in logs, wrong environment, token compromise. Stop use immediately; preserve evidence; notify practice contacts per incident plan.
- S2: core workflow failure for multiple users or repeated 5xx/auth failures. Pause affected workflow; triage within agreed support window.
- S3: single-user issue, UI confusion, training gap, isolated nonblocking bug. Track and resolve in weekly cadence unless it worsens.

Cadence:

- Daily check-in during first week of any real-PHI pilot.
- Weekly check-in after first week if no S1/S2 issues remain open.
- End-of-pilot review at 30/60/90 days depending on agreed pilot length.

Rollback/stop criteria:

- Any S1 incident.
- Runtime safety validator fails.
- Audit/log review finds sensitive content where it should not be.
- User roles or org mappings are incorrect.
- Backup/restore evidence is missing after the agreed deadline.
- Practice asks to pause.
- Workflow failure rate makes clinician review unsafe or impractical.

## 6. Pilot Success Criteria

Use operational metrics only. Do not make clinical outcome claims.

| Metric | How to measure | Success signal |
| --- | --- | --- |
| Documentation turnaround time | Manual before/after timestamp review | Shorter or more predictable completion time, without skipping review |
| Technician intake completeness | Count missing required intake fields before provider review | Fewer missing fields or clearer review prompts |
| Provider review burden | Provider self-report and number of edits per artifact | Lower perceived review friction; no reduction in attestation rigor |
| Draft usefulness | Provider rating of VisitDraft output on a simple scale | More drafts marked useful than not useful |
| Fundus drawing completeness | Count required laterality/finding/detail corrections | Fewer incomplete drawing drafts after training |
| Workflow handoff clarity | Staff survey and observed handoff issues | Fewer "who owns this next?" moments |
| Safety-boundary adherence | Count boundary near-misses and stopped actions | Zero real-PHI/demo mixups; zero forbidden workflow attempts |
| Operator interventions | Count support/operator assists per session | Downward trend after onboarding |
| Failed workflow attempts | Count failed saves/generates/sign attempts | Low and falling; no repeated blocker |
| User-reported friction | Weekly notes from clinicians/technicians | Clear top frictions identified and prioritized |

## 7. Security-Review Evidence Packet Checklist

Existing evidence paths to reference:

| Evidence | Existing path |
| --- | --- |
| Current product truth | `docs/build/current-product-truth.md` |
| Controlled pilot go-live checklist | `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` |
| Pilot readiness checklist | `docs/pilot/chartnav-pilot-readiness-checklist.md` |
| Security review packet | `docs/pilot/chartnav-security-review-packet.md` |
| Demo-to-pilot transition plan | `docs/pilot/chartnav-demo-to-pilot-transition-plan.md` |
| Release evidence checklist | `docs/release/release-evidence-checklist.md` |
| Incident response plan | `docs/security/chartnav-incident-response-plan.md` |
| Incident/breach runbook | `docs/security/chartnav-incident-breach-response-runbook.md` |
| Backup / disaster recovery policy | `docs/security/chartnav-backup-disaster-recovery-policy.md` |
| Security risk analysis template | `docs/security/chartnav-security-risk-analysis-template.md` |
| HIPAA-readiness control matrix | `docs/security/chartnav-hipaa-readiness-control-matrix.md` |
| BAA / vendor readiness checklist | `docs/security/chartnav-baa-vendor-readiness-checklist.md` |
| Real-PHI readiness status | `docs/security/chartnav-real-phi-readiness-status.md` |
| Buyer demo runbook | `docs/demo/phase-61-controlled-buyer-demo-runbook.md` |
| Buyer Q&A safe answers | `docs/demo/phase-61-buyer-qa-safe-answers.md` |
| Phase 63C smoke | `scripts/demo/phase63c_functional_smoke.sh` |

Missing or practice-specific artifacts:

- Executed BAA or legal agreement.
- Practice-specific security-review sign-off.
- Practice-approved hosting choice, region, and network egress policy.
- Practice-approved backup destination and restore-test evidence.
- Practice-specific audit retention period.
- Practice incident contacts and escalation channel, stored out-of-repo.
- Pilot user roster with role mapping.
- Pilot success-metric baseline and measurement owner.
- Written real-PHI start authorization.
- Vendor/subprocessor BAA execution status for the specific deployment path.

## 8. Buyer-Facing Boundaries

Internal guide for pilot conversations:

Allowed to say:

- ChartNav is a provider-reviewed ophthalmology workflow layer.
- The fake-data buyer demo is functionally green after the Phase 63C smoke.
- ChartNav supports structured technician intake, provider-reviewed VisitDraft assist, provider-reviewed fundus drawing assist, doctor attestation, and signed lock.
- Any real-PHI pilot requires security review, legal approval if applicable, environment validation, named users, and written approval.
- Pilot success metrics should be operational and manually reviewed first.
- No production LLM is approved today.

Forbidden positive claims:

- AI scribe.
- hands-free scribing.
- ambient listening.
- listens to the room.
- autonomous documentation.
- AI writes the note.
- diagnostic AI.
- fundus image interpretation.
- OCT interpretation.
- certified EHR.
- EHR replacement.
- HIPAA compliant/certified.
- production LLM.
- OpenAI/Anthropic/IBM-powered clinical documentation.
- automatic billing, coding, orders, referrals, or patient messages.
- device integration or remote patient monitoring.
- guaranteed ROI, clinical outcome improvement, or customer traction.

Safe answer when a buyer asks about real PHI:

> "The demo is fake data only. A real-PHI pilot is a separate controlled process. We would first complete security review, legal/BAA review if applicable, environment validation, role/access review, backup/restore evidence, incident contacts, and written approval. Until those gates close, ChartNav stays in fake-data demo mode."

## 9. Implementation Backlog for Future Phases

Planning labels only. Do not implement these in this Phase 65 artifact.

| Candidate phase | Purpose | Business value |
| --- | --- | --- |
| Phase 65A Security Review Packet Completion | Close missing or stale security-review evidence, map each artifact to buyer security questions, and identify practice-specific blanks | Highest: reduces friction after Phase 64 outreach creates qualified interest |
| Phase 65B Pilot Operations Runbook | Define day-by-day pilot operations, onboarding, support cadence, issue triage, rollback, and stop rules | High: prevents paid pilot chaos |
| Phase 65C Limited Pilot Instrumentation | Add or plan minimal operational metrics collection without clinical outcome claims | High: makes pilot success measurable |
| Phase 65D Pilot Support / Incident Workflow | Formalize support channels, S1/S2/S3 handling, evidence preservation, and owner responsibilities | Medium-high: protects trust during early live use |
| Phase 65E Pilot Exit Criteria and Expansion Decision Memo | Create a go/no-go template for renewal, expansion, pause, or stop after pilot | Medium: keeps business decisions disciplined |

Recommended order: 65A, 65B, 65D, 65C, then 65E. Security evidence and operating discipline should come before instrumentation.

## 10. Non-Overlap With Phase 64

This doc does not replace Phase 64 buyer outreach assets.

This doc should inform qualification and security-review answers, but it is not the buyer brief, outreach email, follow-up email, LinkedIn DM script, call opener, qualification checklist, paid pilot positioning memo, success metrics draft, security-review packet index, demo asset index, or tracker schema.

Claude's Phase 64 files remain the commercial package.

Codex did not modify:

- `docs/commercial/`
- any `docs/commercial/phase-64-*` file
- `docs/build/phase-64-buyer-outreach-package-plan.md`
- public website files
- frontend product code
- backend product code
- API routes
- migrations
- demo media scripts
- capture artifacts

Unrelated local untracked files were present at branch start and intentionally left untouched:

```text
?? .agents/
?? .vercel/
?? apps/web/.gitignore
?? apps/web/chartnavmd-site/
?? apps/web/playwright.capture.config.ts
?? apps/web/tests/e2e/phase62_capture.spec.ts
?? docs/build/phases-1-55-comprehensive-audit.md
?? scripts/demo/capture_phase62_screenshots.mjs
?? scripts/demo/capture_phase62_video_clips.mjs
```

## 11. Validation Commands

Run:

```bash
python3 scripts/check_runtime_safety.py
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
bash scripts/check_alembic_safety.sh
git diff --check
```

If Alembic fails with system Python:

```bash
PYTHON=apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh
```

## 12. Recommendation

This plan is safe to merge as a docs-only planning artifact if the validation commands pass and the PR diff contains only `docs/build/phase-65-controlled-pilot-readiness-plan.md`.

Phase 64 can continue in parallel because this plan does not modify commercial deliverables, public website files, or buyer outreach copy. Phase 64 should continue to frame ChartNav as fake-data-demo-ready and paid-pilot-conversation-ready, with real-PHI pilot use gated.

After Phase 64 lands:

1. Compare Phase 64 buyer qualification and security-review answers against this Phase 65 gate taxonomy.
2. Start Phase 65A to complete or update the security review packet and evidence index.
3. Do not start any real-PHI pilot until Gate 3 has written approval and all blockers in Section 4 are closed with practice-specific evidence.

