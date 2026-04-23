# ChartNav — Critical + High Severity Gap Closure · Master Plan

Scope: close the CRITICAL and HIGH items identified in the approved
ChartNav competitive-gap brief. Phased so pilot-readiness is
sequenced, and so every artifact separates `current state` from
`required state` and from `roadmap`. Nothing in this plan asserts
traction, certifications, or integrations that do not exist.

Controlling positioning: ChartNav is an **ophthalmology-first clinical
workflow and documentation platform**. It is not an Epic replacement
and is not advertised as one. Deployment modes are `standalone`,
`integrated_readthrough` (FHIR R4 read, no EHR mutation), and
`integrated_writethrough` (vendor-adapter writes; `501
adapter_write_not_supported` when the adapter cannot write).

---

## How to use this plan

1. Every closure item lives in its own file under
   `docs/chartnav/closure/PHASE_X_*.md`.
2. Each file follows the same 10-section structure:
   problem, current state, required state, acceptance criteria,
   Codex implementation scope, out-of-scope / process-only, demoable
   now vs later, dependencies, truth limitations, risks if incomplete.
3. This master plan is the index. Codex reads the individual files
   to implement; the commercial team reads the buyer-facing sections.

---

## Phase A — Foundation Integrity (pre-pilot)

Gates access to any pilot commitment. Each item must land before a
discovery call turns into a signed pilot. Files:

| File | Purpose |
|---|---|
| `PHASE_A_Ophthalmology_Encounter_Templates.md` | Four specialty templates (retina, glaucoma, anterior segment / cataract, general ophthalmology) with section structure, findings groups, CPT/ICD relevance fields, and a JSON schema sketch. |
| `PHASE_A_Structured_Charting_and_Attestation.md` | Immutability guarantees extended to encounter rows, per-field edit history, attestation workflow hardened against post-sign mutation. |
| `PHASE_A_RBAC_and_Audit_Trail_Spec.md` | Five-role matrix (front desk, technician, clinician, biller/coder, admin) with route-level access, missing role additions (`technician`, `biller_coder`), seeded identities, audit coverage. |
| `PHASE_A_PM_RCM_Continuity_and_Integration_Path.md` | Honest interim manual/export handoff now; target API integration plan later. Explicit first PM/RCM target recommendation and field-level handoff payload schema. |
| `PHASE_A_Tablet_Charting_Requirements.md` | iPad-first charting surface requirements (touch targets, keyboard behavior, orientation, safe area, mic capture via browser `getUserMedia`). |
| `PHASE_A_Implementation_Methodology.md` | Go-live sequence (T-30 / T-14 / T-7 / T-0 / T+7 / T+30), training matrix per role, support window, escalation, rollback, coexistence logic with the customer EHR. |

**Exit gate for Phase A:** all six files' acceptance criteria are met
in code, and the demo environment can run the four templates through
a signed + attested flow on tablet without manual back-stops.

---

## Phase B — Pilot Threshold (pilot ready)

A pilot clinic can operate end-to-end once Phase B lands. Files:

| File | Purpose |
|---|---|
| `PHASE_B_Referring_Provider_Communication.md` | Consult-letter template engine, PDF + secure link delivery, `referring_providers` + `consult_letters` tables, post-sign letter workflow. |
| `PHASE_B_Admin_Dashboard_and_Operational_Metrics.md` | First-class admin dashboard: encounter throughput, sign-to-export lag, missing-flag resolution rate, reminder completion %, 14-day trend. |
| `PHASE_B_Digital_Intake.md` | Token-based pre-visit intake form (unauthenticated, time-boxed), staff review + accept into the real patient record. |
| `PHASE_B_Reminders_and_Patient_Communication_Hardening.md` | Messages table + opt-out model + provider seam (stub + Twilio skeleton). Still no real SMS in Phase B; the rails are laid and tested. |
| `PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary.md` | Post-visit summary PDF + optional magic-link read-only page. No full portal, no login system, no messaging. |
| `PHASE_B_Demo_Environment_and_Pilot_Scope.md` | Dockerized standalone demo, deterministic seed, pilot scope template with exit criteria signed up-front. |
| `PHASE_B_Onboarding_Training_and_Support.md` | Training matrix per role, 30/60/90 runbook, support tier honestly described (business-hours email in pilot). |

**Exit gate for Phase B:** a pilot clinic can run intake → encounter →
signed note → consult letter → post-visit summary → admin dashboard
on the same deployment, with reminders opt-out and message-status
model functioning against the stub provider.

---

## Phase C — Sales Readiness (pre-broader-rollout)

Conversations with buyers beyond the initial pilot require these.
Files:

| File | Purpose |
|---|---|
| `PHASE_C_CPT_and_Charge_Capture_Logic.md` | Deterministic CPT suggestion layer over signed notes (92xxx series v1), rationale per suggestion, biller/coder capture UI. Explicitly not a coding engine; reviewer-assist only. |
| `PHASE_C_AI_Governance.md` | Publishable governance policy. Deterministic extractor first; LLM seam second. Data residency, logging, opt-out, human-verify. Buyer-safe RFP wording. |
| `PHASE_C_Security_Posture_and_BAA_Readiness.md` | Publishable security posture doc, BAA template, release-compliance checklist. HIPAA posture documented; no certification claims. |
| `PHASE_C_Reporting_and_Exports.md` | Operational + compliance + clinical + billing-handoff + full-data exports. Honest labels: "handoff", not "claim submission". |
| `PHASE_C_Buyer_Objection_Map.md` | 12–16 top objections across physician owners, clinic operators, admin leaders, revenue-cycle stakeholders, investors — each with honest answer + proof pointer. |
| `PHASE_C_Sales_Readiness_Gates.md` | Hard checklist: Gate A (discovery call), Gate B (accept a pilot), Gate C (scale beyond pilot). |

**Exit gate for Phase C:** a qualified buyer can sign a BAA, review a
security posture package, read an AI governance policy, see a CPT
suggestion demo, and leave the conversation without us having
overstated anything.

---

## Cross-cutting truth limitations

These apply to every artifact in this plan and should appear
verbatim in any buyer-facing version of the same content:

- No signed pilots have closed; everything in Phase A/B is
  pilot-ready engineering, not commercial proof.
- Production STT and LLM providers are seams, not wirings. The
  shipping extractor is deterministic regex-based and emits a
  `[stub-transcript]` placeholder when audio arrives without a
  production transcriber configured.
- ChartNav ships no outbound notifier (SMS, email, push) yet. Phase B
  lays the messages table + opt-out model + provider seam. Real
  delivery is a deployment-time provider binding.
- No SOC 2, HITRUST, or ISO 27001 certification. HIPAA posture is
  built (encryption, RBAC, audit, retention) and not independently
  audited.
- The CPT suggestion engine in Phase C is a deterministic
  reviewer-assist, not a coding certification. It never auto-bills.
  No NCCI edits, no modifier logic, no payor-specific rules in v1.
- ChartNav is not a full Epic replacement and is not positioned as
  one in any buyer-facing artifact.

---

## Codex implementation order (what to build first)

Do not interleave. Land one item at a time, merged behind the existing
release gate, then take the next.

1. **Encounter templates** (PHASE_A_Ophthalmology_Encounter_Templates)
   — unblocks every subsequent UI surface; touches the encounter
   schema via a `template_key` column; new service
   `apps/api/app/services/encounter_templates.py`.
2. **RBAC expansion + audit coverage** (PHASE_A_RBAC_and_Audit_Trail_Spec)
   — add `technician` and `biller_coder` roles, migrate the CHECK
   constraint, seed identities, extend `test_security_wave2.py`.
3. **Structured charting attestation** (PHASE_A_Structured_Charting_and_Attestation)
   — harden immutability on encounter rows, add revisions table,
   extend audit coverage.
4. **PM/RCM handoff export** (PHASE_A_PM_RCM_Continuity_and_Integration_Path)
   — CSV/JSON export bundle per signed note; no integration work yet.
5. **Tablet charting hardening** (PHASE_A_Tablet_Charting_Requirements)
   — iPad Pro viewport tests, numeric keypad, safe-area fixes.
6. **Implementation methodology doc** (PHASE_A_Implementation_Methodology)
   — documentation only; Codex writes it but no code changes.
7. **Admin dashboard** (PHASE_B_Admin_Dashboard_and_Operational_Metrics)
   — single new route + React surface + axe-AA pass.
8. **Messages + opt-out + provider seam**
   (PHASE_B_Reminders_and_Patient_Communication_Hardening)
   — table + routes + stub provider; the Twilio skeleton is an
   interface, not wired.
9. **Digital intake** (PHASE_B_Digital_Intake) — token table, two
   unauthenticated routes (time-boxed), staff accept flow.
10. **Post-visit summary** (PHASE_B_Minimum_Patient_Portal_and_Post_Visit_Summary)
    — post-sign summary PDF + magic-link read-only view.
11. **Referring-provider consult letter** (PHASE_B_Referring_Provider_Communication)
    — template + letter generator + post-sign workflow.
12. **Demo environment + pilot scope**
    (PHASE_B_Demo_Environment_and_Pilot_Scope)
    — deterministic seed script + scope template.
13. **Onboarding + training + support**
    (PHASE_B_Onboarding_Training_and_Support)
    — documentation only.
14. **CPT suggestion layer** (PHASE_C_CPT_and_Charge_Capture_Logic)
    — new table, deterministic rules, biller/coder UI.
15. **AI governance + security posture + BAA**
    (PHASE_C_AI_Governance + PHASE_C_Security_Posture_and_BAA_Readiness)
    — documentation bundle + small config knobs.
16. **Reporting + exports** (PHASE_C_Reporting_and_Exports)
    — reports_runs table + five report_key variants.
17. **Buyer objection map + readiness gates**
    (PHASE_C_Buyer_Objection_Map + PHASE_C_Sales_Readiness_Gates)
    — documentation only; commercial-team consumption.

---

## Cross-phase dependencies

- Encounter templates (Phase A) must land before consult letters
  (Phase B) and CPT suggestions (Phase C), because both downstream
  features read the structured findings produced by a template-aware
  extractor.
- RBAC expansion (Phase A) must land before any biller/coder UI
  (Phase C) or admin dashboard role scoping (Phase B).
- Messages + opt-out model (Phase B) must land before real SMS/email
  wiring in any production deployment.
- Security posture + BAA readiness (Phase C) must be published
  before Gate A in `PHASE_C_Sales_Readiness_Gates.md` (can we take
  a discovery call).

---

## Unresolved assumptions (to be confirmed before Codex starts)

1. Is the pilot-target specialty mix exactly the four templates
   above, or is pediatric ophthalmology / oculoplastics needed at
   v1? This plan assumes the four listed; adding a fifth template
   is a ~1 PR addition.
2. Is the first PM/RCM integration target confirmed as NextGen or
   AdvancedMD? The handoff payload schema is vendor-neutral but the
   order of the API integration work changes with the answer.
3. Is the `technician` role truly distinct from `front_desk` in the
   target clinic's operating model, or can they be collapsed in v1?
   The RBAC spec treats them as distinct; collapsing is a migration
   change.
4. Is there a signed clinical advisor who will review encounter
   templates before pilot? If not, templates ship as "operator to
   verify" and the pilot proposal flags this.
5. Is Twilio confirmed as the production messaging provider? The
   Phase B messaging seam ships with a `TwilioProviderSkeleton`;
   swapping to Vonage or another vendor is an interface adoption
   change, not a rewrite.

---

## Items explicitly out of scope for this closure plan

These remain deferred until customer-visible demand exists.

- Full two-way patient portal with login, messaging, scheduling,
  bill-pay
- EHR write-through for Epic specifically
- Revenue-cycle platform (beyond the handoff export + CPT
  suggestion reviewer-assist)
- Machine-learning fine-tuning on customer data
- Multi-language clinical templates (v1 is English)
- Native iOS/Android apps (tablet target is iPad Safari)
- Real-time co-editing of notes
- Voice-driven command surface beyond dictation intake
