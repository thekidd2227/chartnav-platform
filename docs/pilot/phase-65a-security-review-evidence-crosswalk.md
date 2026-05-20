# Phase 65A — Security Review Evidence Crosswalk

> **Status: docs-only crosswalk.** This document is an evidence
> index for the operator preparing a security-review packet for a
> specific prospective pilot practice. It does **not** modify any
> existing security or pilot doc, does **not** introduce new
> claims, does **not** approve real PHI, and does **not** flip any
> compliance status.
>
> Phase 65 (controlled pilot readiness plan, on
> `feature/phase-65-controlled-pilot-readiness-plan`) is the
> upstream planning artifact. Phase 65A is the first
> implementation increment from that plan's § 9 backlog: it maps
> the existing security + pilot evidence in the repo to the gates
> + blockers Phase 65 calls out, and it surfaces the per-practice
> blanks an operator must fill at engagement time.

## 1. How to use this crosswalk

Walk this document top-to-bottom **before** sending any
security-review packet to a prospective pilot practice:

1. § 3 maps every repo evidence doc to **what it proves** in the
   security review.
2. § 4 maps each Phase 65 plan § 4 "real-PHI blocker" to the
   repo doc(s) that address it, plus the per-practice evidence
   the operator still has to gather.
3. § 5 maps each Phase 65 plan § 7 "evidence packet checklist"
   row to the doc it points at, with one-line "what to send"
   summaries.
4. § 6 is a per-buyer-question quick-look: "buyer asks X → send
   doc Y → caveats Z."
5. § 7 lists the per-practice blanks that **never** live in this
   repo (BAA, contacts, retention period, environment validator
   output).
6. § 8 is the operator's "what to send first" decision tree.

This crosswalk does not replace any existing doc; it indexes
them.

## 2. Repo state anchor

| Item | Value |
|---|---|
| Branch | `feature/phase-65a-security-evidence-crosswalk` |
| Base | `main` at `1e5b368` (Phase 64 buyer outreach package) |
| Phase 65 plan | `feature/phase-65-controlled-pilot-readiness-plan` at `7b1ee3a` (not yet merged) |
| Phase 63C functional smoke | `BUYER-DEMO FUNCTIONAL GO: YES` (operator-side, port 8765) |
| Phase 63C smoke commit basis | `8d2b6dd` (Phase 63C-2 on `main`) |
| Real-PHI approval | **NOT GRANTED**. See `docs/security/chartnav-real-phi-readiness-status.md` § 1. |
| Compliance certifications | **None held.** Not HIPAA-certified. Not SOC 2-certified. Not FDA-cleared. Not HITRUST-certified. Not a certified EHR. |

## 3. Repo evidence inventory

Twenty-two security docs + eighteen pilot docs + one functional
smoke script make up the in-repo evidence base today. Each row
below names the doc, the audience it was written for, and the
specific question it answers in a security review.

### 3.1 Security docs (`docs/security/`)

| Doc | Primary audience | What it proves |
|---|---|---|
| `chartnav-access-control-policy.md` | Buyer security reviewer | RBAC roles, org isolation, reviewer read-only enforcement. |
| `chartnav-baa-vendor-readiness-checklist.md` | Buyer legal + security | What is required from each subprocessor before any real-PHI use. |
| `chartnav-backup-disaster-recovery-policy.md` | Buyer IT + security | Backup destination, cadence, restore-test expectations, DR posture. |
| `chartnav-customer-responsibility-matrix.md` | Buyer security + IT | Shared-responsibility split between ChartNav and the practice. |
| `chartnav-hipaa-readiness-control-matrix.md` | Buyer compliance | HIPAA control-by-control posture; not a certification claim. |
| `chartnav-ibm-watsonx-vendor-readiness.md` | Buyer security | Vendor-evaluation posture for IBM watsonx; not a shipped LLM capability. |
| `chartnav-incident-breach-response-runbook.md` | ChartNav on-call + buyer security | Step-by-step incident/breach response procedure. |
| `chartnav-incident-response-plan.md` | Buyer security + ChartNav owner | High-level incident-response policy and contacts model. |
| `chartnav-llm-fake-data-evaluation-plan.md` | Buyer security + ChartNav PM | Vendor-evaluation methodology for the fake-data adapter only. |
| `chartnav-llm-option-a-results.md` | Internal | Internal evaluation results; not a customer-facing claim. |
| `chartnav-llm-provider-decision-memo.md` | Internal | Internal decision memo on LLM provider posture. |
| `chartnav-llm-vendor-evaluation.md` | Buyer security | Vendor-evaluation posture; explicitly not a shipped capability. |
| `chartnav-monitoring-logging-readiness.md` | Buyer security + IT | Logging posture: metadata-only, PHI-safe by design. |
| `chartnav-openai-fake-data-adapter.md` | Buyer security | OpenAI adapter is a fake-data evaluation path, not a production capability. |
| `chartnav-phi-data-flow-map.md` | Buyer security | Where PHI does and does not flow in the system. |
| `chartnav-production-auth-readiness.md` | Buyer security + IT | Bearer-JWT auth posture for a controlled-pilot environment. |
| `chartnav-real-phi-go-live-gate.md` | Buyer security + ChartNav owner | Hard gates that must close before any real-PHI session. |
| `chartnav-real-phi-readiness-status.md` | Buyer security + executive | Bottom-line status: not approved by default; conditional path documented. |
| `chartnav-security-risk-analysis-template.md` | Buyer security | Template the practice fills in for its own risk analysis. |
| `chartnav-stt-vendor-readiness.md` | Buyer security | STT vendor posture; no live audio capture today. |
| `chartnav-subprocessor-inventory.md` | Buyer legal + security | Subprocessor inventory and BAA status field per vendor. |
| `chartnav-support-phi-handling-policy.md` | Buyer security + support | Support-channel PHI handling rules. |

### 3.2 Pilot docs (`docs/pilot/`)

| Doc | Primary audience | What it proves |
|---|---|---|
| `chartnav-admin-onboarding-checklist.md` | Practice admin | Steps to onboard a practice admin in a controlled-pilot deployment. |
| `chartnav-controlled-pilot-go-live-checklist.md` | Practice + ChartNav owner | The gating checklist before any controlled-pilot session opens. |
| `chartnav-demo-to-pilot-transition-plan.md` | Practice + ChartNav owner | How a buyer moves from fake-data demo to a controlled-pilot conversation. |
| `chartnav-known-limitations-and-non-goals.md` | Buyer security + clinical lead | Explicit list of what ChartNav does not do today and does not plan to do. |
| `chartnav-pilot-deployment-guide.md` | Practice IT + ChartNav owner | Pilot deployment topology and configuration guidance. |
| `chartnav-pilot-readiness-checklist.md` | Practice + ChartNav owner | Practice-side readiness checks before any pilot session. |
| `chartnav-pilot-success-metrics.md` | Practice + ChartNav owner | Operational metrics framework for pilot evaluation. |
| `chartnav-security-review-packet.md` | Buyer security reviewer | Conservative, non-overclaiming security-review packet entry. |
| `chartnav-support-runbook.md` | Practice + ChartNav support | Support cadence, escalation channels, S1/S2/S3 handling. |
| `phase-24d-*.md` (8 docs) | Outreach + commercial | Pilot discovery, selection criteria, scorecard, outreach bank — already covered by Phase 64. Not in scope for Phase 65A security review. |

### 3.3 Functional readiness

| Item | Path | What it proves |
|---|---|---|
| Phase 63C functional smoke | `scripts/demo/phase63c_functional_smoke.sh` | Live HTTP smoke against the local stack. Exercises Vitals + VisitDraft + Fundus + manual_note shape. Outcome: `BUYER-DEMO FUNCTIONAL GO: YES` for fake-data demo. **Does not** prove real-PHI readiness. |

## 4. Phase 65 plan § 4 blockers → repo evidence + per-practice gaps

For each real-PHI blocker named in the Phase 65 plan § 4, this
section names the in-repo doc(s) that address it and the
per-practice evidence the operator still has to gather. The
"per-practice" column is what the security-review owner provides
at engagement time — those items do not live in the repo.

| Blocker (Phase 65 § 4) | Repo evidence | Per-practice evidence required |
|---|---|---|
| Security review | `docs/pilot/chartnav-security-review-packet.md`; `docs/security/chartnav-hipaa-readiness-control-matrix.md`; `docs/security/chartnav-customer-responsibility-matrix.md`. | Security owner's review notes + gaps list; written conditional approval or named blockers. |
| Access controls | `docs/security/chartnav-access-control-policy.md`; `docs/security/chartnav-production-auth-readiness.md`; backend RBAC tests in `apps/api/tests/test_rbac.py`. | Practice user roster with role mapping; reviewer/technician restrictions validated in the target environment. |
| Audit logging review | `docs/security/chartnav-monitoring-logging-readiness.md`; `docs/security/chartnav-phi-data-flow-map.md`; sentinel-redaction tests in `apps/api/tests/test_end_to_end_clinical_workflow.py::TestEndToEndAuditRedaction`. | Practice-agreed audit retention period; target-environment log review for sensitive-content exposure. |
| Data retention policy | `docs/security/chartnav-monitoring-logging-readiness.md`; `docs/security/chartnav-real-phi-go-live-gate.md`; `docs/security/chartnav-backup-disaster-recovery-policy.md`. | Practice-specific retention period; deletion / export expectations in writing. |
| BAA / legal review | `docs/security/chartnav-baa-vendor-readiness-checklist.md`; `docs/security/chartnav-subprocessor-inventory.md`; `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`. | Executed BAA stored out-of-repo; subprocessor BAA chain reviewed for the specific deployment path. |
| Incident response | `docs/security/chartnav-incident-response-plan.md`; `docs/security/chartnav-incident-breach-response-runbook.md`. | Practice contacts; escalation timing; evidence-preservation owner; notification-workflow sign-off. |
| Environment separation | `docs/security/chartnav-real-phi-readiness-status.md`; `docs/pilot/chartnav-demo-to-pilot-transition-plan.md`; bundle wrappers under `artifacts/phase-62/desktop-bundle/`. | Operator-visible environment label; separate startup / config path validated end-to-end. |
| Backup / restore | `docs/security/chartnav-backup-disaster-recovery-policy.md`. | Practice-approved backup destination; backup cadence; restore-test evidence; monitoring evidence. |
| Vendor / API key policy | `docs/security/chartnav-llm-vendor-evaluation.md`; `docs/security/chartnav-ibm-watsonx-vendor-readiness.md`; `docs/security/chartnav-stt-vendor-readiness.md`; `docs/security/chartnav-openai-fake-data-adapter.md`; `scripts/check_runtime_safety.py`. | Confirmation no live vendor egress is enabled for the pilot deployment; no secrets printed or committed. |
| LLM disabled / separately approved | `docs/security/chartnav-real-phi-readiness-status.md`; `docs/security/chartnav-llm-provider-decision-memo.md`; runtime safety validator. | Written confirmation `CHARTNAV_LLM_ENABLED=0` for the pilot environment; separate approval path if LLM is enabled later. |
| Role-based access validation | `docs/security/chartnav-access-control-policy.md`; backend RBAC tests. | Target-environment RBAC smoke for admin / clinician / technician / reviewer roles. |
| Sensitive content logging | `docs/security/chartnav-monitoring-logging-readiness.md`; metadata-only audit tests. | Practice-side review confirming request bodies, Authorization headers, transcript text, vitals values, fundus findings, and note bodies are absent from the deployment's logs. |
| Demo / fake-data mode separation | `docs/security/chartnav-real-phi-readiness-status.md`; bundle wrapper `start-api.sh` (refuses production / staging / controlled-pilot `CHARTNAV_ENV`). | Operator's visible environment label + separate startup script for the pilot environment vs the demo environment. |

## 5. Phase 65 plan § 7 evidence checklist → "what to send" summaries

The Phase 65 plan § 7 lists fourteen evidence paths. This section
gives the operator a one-line "what this doc tells the buyer"
summary for each.

| Phase 65 § 7 evidence | What to tell the buyer when sending it |
|---|---|
| `docs/build/current-product-truth.md` | The single source of truth for what ChartNav is and is not. Send this first. |
| `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md` | The gating checklist that must close before any controlled-pilot session opens. |
| `docs/pilot/chartnav-pilot-readiness-checklist.md` | Practice-side readiness checks before any pilot session. |
| `docs/pilot/chartnav-security-review-packet.md` | Conservative, non-overclaiming entry packet for the security reviewer. |
| `docs/pilot/chartnav-demo-to-pilot-transition-plan.md` | How a buyer moves from fake-data demo to controlled-pilot conversation. |
| `docs/release/release-evidence-checklist.md` | The release-side evidence required for any external claim. |
| `docs/security/chartnav-incident-response-plan.md` | High-level incident-response policy and contact model. |
| `docs/security/chartnav-incident-breach-response-runbook.md` | Operational runbook for an incident / breach event. |
| `docs/security/chartnav-backup-disaster-recovery-policy.md` | Backup + DR policy; practice supplies destination + cadence + restore-test evidence. |
| `docs/security/chartnav-security-risk-analysis-template.md` | Template the practice fills in for its own risk analysis. |
| `docs/security/chartnav-hipaa-readiness-control-matrix.md` | Control-by-control HIPAA posture; not a HIPAA-certification claim. |
| `docs/security/chartnav-baa-vendor-readiness-checklist.md` | What is required from each subprocessor before real-PHI use. |
| `docs/security/chartnav-real-phi-readiness-status.md` | The "bottom line — not approved by default" status doc. Include in every packet. |
| `docs/demo/phase-61-controlled-buyer-demo-runbook.md` | The buyer-demo operating runbook. |
| `docs/demo/phase-61-buyer-qa-safe-answers.md` | 20-question buyer Q&A bank; safe answers only. |
| `scripts/demo/phase63c_functional_smoke.sh` | The fake-data demo functional-readiness gate. Latest outcome: `BUYER-DEMO FUNCTIONAL GO: YES` at `8d2b6dd`. |

## 6. Buyer-question crosswalk

When a buyer's security reviewer asks one of these, send the named
doc(s) and use the caveat in the third column.

| Buyer question | Send | Caveat |
|---|---|---|
| "Are you HIPAA-certified?" | `docs/security/chartnav-real-phi-readiness-status.md`; `docs/security/chartnav-hipaa-readiness-control-matrix.md`. | ChartNav is **not** HIPAA-certified. Certification is operational and not vendor-conferred. The matrix shows control-by-control posture; the bottom-line status doc names what is and is not approved today. |
| "Where does PHI flow?" | `docs/security/chartnav-phi-data-flow-map.md`; `docs/security/chartnav-monitoring-logging-readiness.md`. | The flow map and logging posture together show that metadata-only audit logging is the design intent; the practice-side log review at deployment time confirms no sensitive content leaks. |
| "What's your incident-response posture?" | `docs/security/chartnav-incident-response-plan.md`; `docs/security/chartnav-incident-breach-response-runbook.md`. | Practice supplies its own contacts + escalation timing + notification workflow; ChartNav supplies the policy + the runbook. |
| "What's your backup and restore posture?" | `docs/security/chartnav-backup-disaster-recovery-policy.md`. | The policy defines expected backup cadence and restore-test discipline. Per-practice destination, cadence, restore-test evidence, and monitoring evidence are required at engagement time. |
| "Who are your subprocessors?" | `docs/security/chartnav-subprocessor-inventory.md`; `docs/security/chartnav-baa-vendor-readiness-checklist.md`. | The inventory enumerates current candidates with their BAA-readiness state. The BAA chain is closed per deployment, not per repo state. |
| "Do you have a production LLM?" | `docs/security/chartnav-llm-provider-decision-memo.md`; `docs/security/chartnav-llm-vendor-evaluation.md`; `docs/security/chartnav-real-phi-readiness-status.md`. | No production LLM is approved today. The vendor-evaluation work is explicitly evaluation, not a shipped capability. `CHARTNAV_LLM_ENABLED=0` in every demo + pilot default. |
| "Do you process exam-room audio?" | `docs/security/chartnav-stt-vendor-readiness.md`; `docs/build/current-product-truth.md`. | ChartNav does not capture exam-room audio. The VisitDraft Assist works from a transcript the clinician types or pastes. |
| "Do you interpret fundus or OCT images?" | `docs/build/current-product-truth.md`; `docs/pilot/chartnav-known-limitations-and-non-goals.md`. | ChartNav does not interpret fundus photos or OCT images. The Fundus Drawing Assist works from clinician-entered findings text only. |
| "Will ChartNav replace our EHR?" | `docs/build/current-product-truth.md`; `docs/pilot/chartnav-known-limitations-and-non-goals.md`. | ChartNav is not a certified EHR and does not replace any EHR. It runs alongside the practice's existing chart system. |
| "Can we start on real PHI next Monday?" | `docs/security/chartnav-real-phi-readiness-status.md`; `docs/security/chartnav-real-phi-go-live-gate.md`; `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`. | Real-PHI use is gated. The bottom-line status doc plus the go-live gate plus the controlled-pilot checklist describe the gates that must close in writing before the first real-PHI session. |
| "What does your access-control model look like?" | `docs/security/chartnav-access-control-policy.md`; `docs/security/chartnav-production-auth-readiness.md`; `docs/security/chartnav-customer-responsibility-matrix.md`. | RBAC roles + org isolation + reviewer read-only enforcement are tested in the backend. The customer responsibility matrix names what the practice owns vs what ChartNav owns. |
| "What metrics will you measure during the pilot?" | `docs/pilot/chartnav-pilot-success-metrics.md`; `docs/commercial/phase-64-pilot-success-metrics.md`. | Operational metrics only; no clinical outcome claims. Pick one or two with the buyer; do not commit to all of them. |

## 7. Per-practice blanks (never live in this repo)

These items are practice-specific and must be filled at engagement
time. They live out-of-repo (signed PDFs, contact spreadsheets,
configuration files in the deployment environment).

| Blank | Owner | Storage |
|---|---|---|
| Executed BAA / pilot legal agreement | Practice legal + ChartNav owner | Out-of-repo signed PDF + a placeholder row in the outreach tracker referencing it by name. |
| Practice-specific security-review sign-off | Practice security reviewer | Written email or letter referencing the security packet that was reviewed. |
| Practice-approved hosting choice, region, network egress policy | Practice IT | Deployment configuration; documented in the practice's deployment runbook. |
| Practice-approved backup destination + restore-test evidence | Practice IT | Backup-system console output + dated restore-test log. |
| Practice-specific audit retention period | Practice security | Written agreement; configured via `CHARTNAV_AUDIT_RETENTION_DAYS`. |
| Practice incident contacts + escalation channel | Practice security + ChartNav owner | Out-of-repo contact sheet; not committed to git. |
| Pilot user roster + role mapping | Practice admin + ChartNav owner | Out-of-repo spreadsheet (no real PHI); roles validated in the target environment. |
| Pilot success-metric baseline + measurement owner | Practice operations lead | Out-of-repo measurement log; owner named in the outreach tracker. |
| Written real-PHI start authorization | Practice approver | Out-of-repo email or letter. **No real-PHI session may start before this exists.** |
| Vendor / subprocessor BAA execution status for the specific deployment path | ChartNav legal + Practice legal | Signed agreements referenced by the BAA-readiness checklist. |

## 8. Operator's "what to send first" decision tree

When a qualified buyer asks for evidence, send in this order:

1. **First — the bottom line.** `docs/build/current-product-truth.md`
   + `docs/security/chartnav-real-phi-readiness-status.md`. These
   set expectations honestly. Sending these first prevents the
   conversation from drifting into compliance overclaim territory.
2. **Second — the entry packet.** `docs/pilot/chartnav-security-review-packet.md`
   + `docs/pilot/chartnav-known-limitations-and-non-goals.md`. The
   security packet is the buyer-facing entry doc; the
   limitations + non-goals doc is the boundaries.
3. **Third — control-level evidence**, by the buyer's specific
   questions (§ 6 above). Send only what they ask for.
4. **Fourth — the gating discipline.** `docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`
   + `docs/security/chartnav-real-phi-go-live-gate.md`. These show
   the buyer how disciplined the path from demo to real-PHI is.
5. **Fifth — the functional readiness signal.** Mention the
   Phase 63C smoke result + commit basis. Offer to walk the
   buyer's technical reviewer through running it themselves
   against the inspection bundle.
6. **Last — operational evidence.** `docs/pilot/chartnav-pilot-success-metrics.md`
   + `docs/pilot/chartnav-support-runbook.md`. These are how the
   pilot will be operated, not how it will be approved.

Anything outside this list, decline politely. If the buyer asks
for a HIPAA certification document or a SOC 2 attestation,
ChartNav does not hold those today and saying so honestly is the
safe answer.

## 9. What Phase 65A is NOT

- **Not a new claim.** Every statement in this crosswalk is
  already true in the existing security + pilot docs. This file
  is an index, not a contract.
- **Not a real-PHI approval.** Real-PHI use remains gated by
  Phase 65 § 4 blockers + the controlled-pilot go-live checklist.
- **Not a HIPAA / SOC 2 / HITRUST / FDA certification.** ChartNav
  holds none of those.
- **Not an EHR replacement positioning.** ChartNav is not a
  certified EHR and does not replace any EHR.
- **Not a product code change.** No file under `apps/api/` or
  `apps/web/` is touched.
- **Not a migration change.** No new migration.
- **Not a claim policy change.** No claim scanner change. No
  scanner FILES list extension.
- **Not a buyer-demo smoke change.** Phase 63C smoke behavior is
  preserved by construction (no code touched, no scanner
  changed, no migration added).

## 10. Validation

Run the standard six gates plus the demo smoke. All must remain
green for this PR to land.

```bash
python3 scripts/check_runtime_safety.py
bash scripts/check_commercial_claims.sh
bash scripts/check_website_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/test_claim_policy_fixtures.sh
PYTHON=apps/api/.venv/bin/python bash scripts/check_alembic_safety.sh
git diff --check
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

Expected smoke result: `BUYER-DEMO FUNCTIONAL GO: YES` (20 pass /
0 fail).

## 11. Related documents

- `docs/build/phase-65-controlled-pilot-readiness-plan.md` (on
  `feature/phase-65-controlled-pilot-readiness-plan`; the
  upstream planning artifact that names Phase 65A → 65E in § 9).
- `docs/build/current-product-truth.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/pilot/chartnav-security-review-packet.md`
- `docs/security/chartnav-real-phi-readiness-status.md`
