# ChartNav HIPAA-Regulated Deployment Readiness — Plan

> **Phase scope target:** Phase 23 (build), Phase 20A.1 (this plan).
> **Type:** Planning only. No code, no migrations, no schema, no
> media binaries, no production publish.

This plan defines the **legal, technical, operational, vendor,
audit, backup, monitoring, and incident-response** controls
required before ChartNav can support a real-PHI deployment in
a HIPAA-regulated environment. It does **not** make ChartNav
HIPAA-compliant by virtue of existing — controls must be
implemented, documented, executed, and signed off.

## 1. Current Status

> **ChartNav is not approved for real PHI by default.**
> **ChartNav is not HIPAA certified.**
> This plan defines the controls needed to support future
> HIPAA-regulated deployment review.

Today, every demo / capture / pilot artifact in this repo
operates on **fake / demo / synthetic seed data**. Phase 23 is
the explicit gate between "demo-ready clinical platform" and
"clinic-grade real-PHI controlled pilot."

## 2. What Already Exists

The repo audit (Phase 20A) confirms several pieces of the
HIPAA-readiness puzzle already shipped or planned. They form
the foundation Phase 23 builds on — they are **not**
sufficient on their own.

| Existing | Notes |
|---|---|
| **Controlled-pilot PHI readiness docs (Phase 18)** | `docs/chartnav-pilot-readiness-deployment-hardening.md` — operational-hardening checklist for controlled-pilot environments |
| **Production auth readiness** | `apps/api/app/auth.py` supports two modes — `header` (dev) and `bearer` (prod, JWKS validation, sig/iss/aud/exp checks). Production deploys gate on bearer mode. |
| **Postgres requirement for production** | Backend supports both SQLite (dev/CI) and Postgres (prod/pilot). Real PHI requires Postgres in an approved hosting environment. |
| **Audit retention + redaction posture** | `security_audit_events` table with `CHARTNAV_AUDIT_RETENTION_DAYS` env knob; audit detail is metadata-only (no PHI in audit body). `ai_governance_log` stores hashed prompts/outputs only — never raw text or patient identifiers. |
| **Org isolation + RBAC posture** | `app.authz.ensure_same_org()` guard on every cross-org boundary; 404 (no existence leak) on cross-org access; role-based transition matrix in `TRANSITION_ROLES`. |
| **Claims discipline** | `scripts/check_commercial_claims.sh` + `scripts/check_website_claims.sh` enforce no HIPAA-compliant / certified-EHR / autonomous-diagnosis / automatic-orders / automatic-patient-messaging / automatic-billing claims anywhere in shipped surfaces. |
| **PHI-safe logging** | `security_audit_events.detail` is metadata-only by contract; `ai_governance_log` stores `prompt_hash` and `output_hash`, never raw values. Tested. |
| **Backup + restore scaffolding** | `scripts/` directory contains controlled-pilot operational scripts (smoke tests, claims checks). Production backup automation is Phase 23E. |
| **Forbidden-claims test matrix** | Multiple vitest + claims-check tests catch positive HIPAA / certified-EHR / autonomous claims at PR time. |

## 3. What Is Missing

The gap to **real-PHI-deployment readiness** breaks down into
nine layers. Each layer below is what Phase 23 must produce.

| Layer | Missing items |
|---|---|
| **Legal / Contract** | BAA template, customer responsibility matrix, subprocessor inventory, vendor BAA checklist, data processing / security addendum, incident notification terms, practice approval checklist, real-PHI go-live signoff |
| **Technical Security** | Production bearer/OIDC enforcement at deploy gate, MFA at IdP confirmation, formalized access control policy, session timeout policy, encryption-at-rest documentation, secrets management documentation, rate limiting policy, security headers checklist, vulnerability/dependency scanning evidence, "no SQLite for real PHI" guard, "no real PHI in local/staging" guard |
| **Audit / Monitoring** | Admin audit dashboard, failed login monitoring, cross-org access attempt alerts, PHI-safe log redaction evidence (test + report), admin security event export, backup success/failure monitoring, audit retention reporting, security event review workflow, incident evidence preservation procedure |
| **Backup / DR** | Backup policy, encrypted backup storage configuration, restore-test cadence, recovery point objective (RPO), recovery time objective (RTO), backup retention ownership matrix, "no PHI backups committed to repo" guard, practice-approved storage destination |
| **Incident Response / Breach** | Incident response runbook, severity levels, breach assessment workflow, notification workflow, evidence preservation, support-ticket PHI prohibition, rollback / disable plan, contacts and escalation owners |
| **PHI Data Governance** | PHI data-flow map, PHI field inventory, minimum-necessary principle documentation, data retention policy, data deletion / export policy, support access policy, admin access logging, environment separation policy |
| **Vendor / Subprocessor** | Cloud hosting vendor review, database hosting vendor review, storage vendor review, transcription / STT vendor review, AI/LLM vendor review (if any PHI is processed), email / SMS vendor review, BAA status per vendor, approved / not-approved PHI egress list |
| **Operational Policy** | Access control policy, workforce access policy, change management policy, secure development policy, incident response policy, backup / disaster recovery policy, vendor management policy, PHI handling policy, support operations policy, audit review policy |
| **Validation / Evidence** | Controlled-pilot environment validator script, production config checklist, backup / restore verification report, audit redaction tests, org isolation tests, RBAC tests, logging redaction tests, security review packet, risk analysis template, deployment readiness checklist |

## 4. Required Artifacts (Phase 23 deliverables)

These are the docs Phase 23 will land under
`docs/security/` (new directory) and `docs/compliance/` (new
directory):

| Artifact | Path |
|---|---|
| HIPAA readiness control matrix | `docs/compliance/chartnav-hipaa-readiness-control-matrix.md` |
| BAA + vendor readiness checklist | `docs/compliance/chartnav-baa-vendor-readiness-checklist.md` |
| Customer responsibility matrix | `docs/compliance/chartnav-customer-responsibility-matrix.md` |
| Subprocessor inventory | `docs/compliance/chartnav-subprocessor-inventory.md` |
| PHI data-flow map | `docs/security/chartnav-phi-data-flow-map.md` |
| Security risk analysis template | `docs/security/chartnav-security-risk-analysis-template.md` |
| Incident / breach response runbook | `docs/security/chartnav-incident-breach-response-runbook.md` |
| Access control policy | `docs/security/chartnav-access-control-policy.md` |
| Backup / disaster recovery policy | `docs/security/chartnav-backup-disaster-recovery-policy.md` |
| Support PHI handling policy | `docs/security/chartnav-support-phi-handling-policy.md` |

Each artifact follows the same template: scope · owner ·
trigger conditions · controls · evidence required · review
cadence · sign-off owner.

## 5. Required Product / Admin Features

These are product-side additions that Phase 23 implements on
top of existing surfaces. Every one is **optional** at install
time and gated on admin-role + practice-approved configuration.

| Feature | Purpose |
|---|---|
| **Admin audit dashboard** | Read-only view of `security_audit_events` filtered by event type, actor, time window. Charts for failed-login rate, cross-org-access attempts, role-forbidden denials. |
| **Security event export** | Admin-only CSV / JSON export of `security_audit_events` for the practice's audit reviewer. PHI-safe by construction (audit detail is metadata-only). |
| **Audit retention status panel** | Shows current `CHARTNAV_AUDIT_RETENTION_DAYS` setting, oldest retained event, count of events purged in last cycle. |
| **Backup verification status panel** | Shows last backup time, last restore-test time, restore-test result. Pure metadata (no backup contents). |
| **Org / location / user access review panel** | Admin lists active users, roles, last login, location assignments. Supports periodic access review per HIPAA workforce-access policy. |
| **Production configuration readiness view** | Read-only check: production auth mode, Postgres in use, audit retention configured, backup configured, monitoring configured. Surfaces a single readiness score + drill-down. |
| **Incident evidence export** | Bundled export of relevant `security_audit_events` + `ai_governance_log` rows for incident investigation. Admin-only, audit-logged, time-windowed. |
| **Subprocessor / vendor status view** | Reads `docs/compliance/chartnav-subprocessor-inventory.md` (committed source of truth) and renders BAA status + PHI egress posture per vendor. |

All of these are **read-only admin views over existing data**.
None introduces a new PHI surface; none changes the clinical
workflow.

## 6. Real-PHI Go-Live Gates

A controlled-pilot real-PHI deployment cannot begin until
**every** gate below is checked. Phase 23F produces the formal
checklist; this is the spec the checklist enforces.

- ✅ **BAA executed** between ChartNav (or the practice's
  ChartNav-deploying entity) and the practice
- ✅ **Practice security owner identified** (named individual
  + escalation contact)
- ✅ **Security review accepted** by the practice (signed
  acceptance of `docs/compliance/chartnav-customer-responsibility-matrix.md`)
- ✅ **Production auth configured** — `bearer` mode only;
  JWKS endpoint configured; MFA enforced at IdP
- ✅ **Postgres hosted in approved environment** (per the
  practice's approved hosting list); SQLite gate explicitly
  blocks production data
- ✅ **Backups configured** + **restore tested** within last
  90 days; restore evidence on file
- ✅ **Monitoring configured** — failed login alerts,
  cross-org access alerts, audit retention alerts wired to
  the practice's SOC / on-call
- ✅ **Audit retention agreed** in writing (per the practice's
  `CHARTNAV_AUDIT_RETENTION_DAYS` value)
- ✅ **Incident contacts documented** + escalation tree on file
- ✅ **Vendor / subprocessor review complete** — every vendor
  in `docs/compliance/chartnav-subprocessor-inventory.md`
  reviewed; BAA status per vendor confirmed
- ✅ **STT / AI / LLM PHI egress approved or disabled** —
  if a vendor lacks a BAA, that surface is disabled in
  production for the practice
- ✅ **Support process approved** — per
  `docs/security/chartnav-support-phi-handling-policy.md`;
  support tickets prohibit PHI by policy + tooling check
- ✅ **Written practice approval** — signed go-live document
  from the practice's named security owner
- ✅ **Real PHI start date approved** — explicit cutover date,
  not implicit; recorded in the practice's deployment log

## 7. Explicit Non-Claims

- **ChartNav is not HIPAA certified.** No regulatory body
  certifies HIPAA compliance; the term "HIPAA certified" is
  a marketing fiction the platform avoids.
- **ChartNav is not HIPAA compliant by default.** Code
  existing does not produce compliance. Compliance is a
  function of how the platform is deployed, configured,
  contracted, monitored, and operated — by both ChartNav and
  the deploying practice.
- **ChartNav is not a certified EHR.** ChartNav is a
  provider-reviewed clinical workflow + AI scribe layer, not
  an ONC-certified EHR.
- **ChartNav does not become PHI-ready because the code
  exists.** Real-PHI readiness requires the legal,
  operational, vendor, deployment, and practice-approval
  gates in Section 6.
- **Real PHI requires legal, operational, vendor, deployment,
  and practice approval gates.** All of them. Skipping any
  gate is a real-PHI gap.
- **The HIPAA readiness work in Phase 23 prepares ChartNav
  for security review.** It does not constitute the security
  review itself or its outcome.

## 8. Implementation Sequence (Phase 23 subphases)

Phase 23 is large enough that it ships in six subphases.
Each subphase is one PR with its own merge gate.

### Phase 23A — HIPAA Readiness Control Matrix + Responsibility Matrix

**Scope.** Land the two cornerstone compliance docs that every
later subphase references.

**Files likely touched.**
- `docs/compliance/chartnav-hipaa-readiness-control-matrix.md` (new)
- `docs/compliance/chartnav-customer-responsibility-matrix.md` (new)
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md` (note 23A merge)

**Tests required.**
- `bash scripts/check_commercial_claims.sh` 0 fail / 0 warn
- Forbidden-phrase grep on the two new docs: every
  HIPAA-positive phrase must be in safe negative-assertion
  context (`does not`, `is not`, `Correctly avoids`, etc.)
- `python scripts/build_docs.py` if available

**Risks.** Scope creep into actual policy-writing — Phase 23A
documents the matrix shape; the policies themselves are
Phase 23C. Mitigation: explicit "do not include policy bodies"
checklist in the Phase 23A PR.

**Merge criteria.** Both docs land; no positive HIPAA claim;
roadmap updated.

**Do NOT touch.** Backend / frontend / migrations / package
files / production config.

### Phase 23B — PHI Data Flow + Subprocessor / Vendor Inventory

**Scope.** Document the actual PHI data flow through ChartNav
+ catalog every external vendor that could receive PHI.

**Files likely touched.**
- `docs/security/chartnav-phi-data-flow-map.md` (new)
- `docs/compliance/chartnav-subprocessor-inventory.md` (new)
- `docs/compliance/chartnav-baa-vendor-readiness-checklist.md` (new)
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md`

**Tests required.**
- claims-check + website-claims-check 0 fail / 0 warn
- Forbidden-phrase grep on the three new docs
- The PHI data-flow map must explicitly mark every vendor +
  every storage hop + every API egress with PHI-presence
  status (always / never / conditional)

**Risks.** Vendor list completeness depends on what's actually
deployed. Mitigation: matrix has a "TBD per practice" column
that the deploying practice fills.

**Merge criteria.** All three docs landed; vendor matrix has
at minimum cloud hosting / database hosting / storage / STT /
AI/LLM rows.

**Do NOT touch.** Real vendor BAAs (those are signed off-repo);
backend config; deployment scripts.

### Phase 23C — Policies and Incident / Breach Runbooks

**Scope.** Land the operational policy set + the
incident-response runbook.

**Files likely touched.**
- `docs/security/chartnav-access-control-policy.md` (new)
- `docs/security/chartnav-backup-disaster-recovery-policy.md` (new)
- `docs/security/chartnav-support-phi-handling-policy.md` (new)
- `docs/security/chartnav-incident-breach-response-runbook.md` (new)
- `docs/security/chartnav-security-risk-analysis-template.md` (new)
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md`

**Tests required.**
- claims-check + website-claims-check 0 fail / 0 warn
- Forbidden-phrase grep on every new doc
- Each policy doc has the same template (scope · owner ·
  trigger · controls · evidence · review cadence · sign-off)

**Risks.** Policy text quality — these need legal review
before the practice signs them. Mitigation: docs explicitly
labeled "Template — practice-specific completion required"
where applicable.

**Merge criteria.** All five docs landed; each follows the
template; each has a clear sign-off owner field.

**Do NOT touch.** Real policy execution (that's the practice's
operations team); backend / frontend product code.

### Phase 23D — Admin Security Dashboard + Audit Event Export

**Scope.** First **product code** subphase of Phase 23. Adds
admin-only views that expose existing `security_audit_events`
+ `ai_governance_log` data to the practice's audit reviewer.

**Files likely touched.**
- `apps/api/app/api/admin_security.py` (new) — read-only
  endpoints for audit dashboard + export
- `apps/api/app/services/audit_export.py` (new) — CSV / JSON
  export, PHI-safe by construction
- `apps/web/src/AdminSecurityDashboard.tsx` (new) — read-only
  view, charts, export button
- `apps/api/tests/test_admin_security_*.py` (new)
- `apps/web/src/test/AdminSecurityDashboard.test.tsx` (new)
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md`

**Tests required.**
- Migration up/down (none; no schema changes — new endpoints
  read existing tables)
- RBAC: `admin` role only on every new endpoint
- Org isolation: cross-org export returns 404 (no existence
  leak)
- Audit row written for every export action
- Forbidden-phrase scan on new UI — no "compliance score" /
  "HIPAA dashboard" / "certified" labels
- vitest covers the dashboard render + export wiring

**Risks.** Export format must be PHI-safe — `audit detail` is
metadata-only by existing contract, but a regression here
would be high-impact. Mitigation: explicit test that scans
exported payloads for `condition_label`, `criteria_json`,
clinical-text shape patterns; failing if any appears.

**Merge criteria.** All 8 CI checks green; admin role only;
PHI-safe payload tested.

**Do NOT touch.** Clinical data tables; non-admin user views;
patient-side surfaces; existing 9-tab clinical workspace.

### Phase 23E — Backup / Restore Evidence + Monitoring Evidence

**Scope.** Operational tooling + evidence collection for
backup verification, restore testing, and production
monitoring posture.

**Files likely touched.**
- `scripts/verify_backup_integrity.sh` (new)
- `scripts/restore_test_runner.sh` (new)
- `apps/api/app/api/backup_status.py` (new) — read-only
  metadata endpoint
- `apps/web/src/AdminBackupStatus.tsx` (new)
- `docs/security/chartnav-backup-disaster-recovery-policy.md`
  (extend with verification cadence + RPO/RTO numbers)
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md`

**Tests required.**
- Backup verification script idempotent + safe to re-run
- Restore-test runner uses synthetic / non-PHI fixtures only
- Backup status endpoint exposes timestamps + checksums only,
  never backup contents
- RBAC: admin only
- Audit row written for every backup metadata read

**Risks.** Real backup configuration is per-practice. Phase
23E provides the verifier + status surface; the actual
backups + storage destination are the practice's
responsibility (per the customer responsibility matrix).
Mitigation: docs explicit about the boundary.

**Merge criteria.** All 8 CI checks green; backup status
panel renders; verifier script lints clean.

**Do NOT touch.** Real production backups; practice-owned
storage; real PHI fixtures.

### Phase 23F — Final Controlled-Pilot Real-PHI Gate Review Packet

**Scope.** Bundle every artifact from Phase 23A–E into a
single review-ready packet that a practice's security owner
can sign off in one sitting.

**Files likely touched.**
- `docs/compliance/chartnav-controlled-pilot-real-phi-gate-review-packet.md` (new)
- `scripts/generate_pilot_readiness_packet.sh` (new) — bundles
  the per-phase artifacts into one PDF / Markdown packet
  with per-section sign-off lines
- `docs/product/chartnav-phase-20-22-implementation-roadmap.md`
- `apps/api/app/api/production_readiness.py` (new) —
  read-only endpoint that surfaces the readiness score
  computed from existing config
- `apps/web/src/AdminProductionReadiness.tsx` (new)

**Tests required.**
- Packet bundler script generates the packet with all
  sections present
- Production-readiness endpoint surfaces correct score for
  known good / known bad config combinations (test fixtures)
- No real PHI in any test fixture
- claims-check + website-claims-check 0 fail / 0 warn on the
  full packet

**Risks.** Practice may interpret a green readiness score as
"we're HIPAA compliant." Mitigation: every render of the
score includes the explicit non-claims block from Section 7.

**Merge criteria.** Packet bundles correctly; readiness score
endpoint covered by tests; explicit non-claims rendered
alongside any score display.

**Do NOT touch.** Sign-off itself (that's the practice's
security owner, not ChartNav); real-PHI deployment activation
(that's gated on the signed packet).

## 9. Exact Safe Readiness Statement

This is the **only** approved phrasing for ChartNav's HIPAA
readiness posture in marketing, sales, customer pitches,
website copy, decks, contracts, support tickets, and any
public statement:

> **ChartNav is not approved for real PHI by default.
> ChartNav may be prepared to support a HIPAA-regulated
> controlled pilot only after BAA execution, practice
> security review, production bearer authentication,
> approved hosting, backups, monitoring, audit-retention
> agreement, vendor/subprocessor review, incident-response
> contacts, and written practice approval are complete.**

Variations that **drop, soften, or rephrase** any of those
clauses are not approved phrasing.

## 10. Hard Constraints

- ❌ No HIPAA-compliant claim
- ❌ No HIPAA-certified claim
- ❌ No "approved for real PHI by default" claim
- ❌ No "code-as-compliance" framing
- ❌ No real PHI in any test, demo, capture, or fixture
- ❌ No PHI backups committed to the repo
- ❌ No SQLite for real PHI
- ❌ No local / dev auth for real PHI
- ❌ No real PHI in local or staging environments
- ❌ No support ticket containing PHI (policy + tooling check)
- ❌ No vendor egress without confirmed BAA + approved-egress status
- ✅ Every claim about HIPAA readiness is paired with the
  exact safe readiness statement (Section 9)
- ✅ Every product feature added in Phase 23 is admin-only,
  read-only over existing data, and audit-logged
- ✅ Every Phase 23 subphase merges only after its tests pass
  and a reviewer confirms no positive HIPAA claim slipped in

## 11. Connection to Existing Phase 20A Plans

Phase 23 is **independent** of the product-feature roadmap
(20B → 22) but interacts with it:

| Phase | Interaction with Phase 23 |
|---|---|
| Phase 20B (Structured Data Layer) | Adds work_queue_items + role_view_presets; Phase 23D admin dashboard reads from existing `security_audit_events`, not these new tables, so no coupling |
| Phase 20C (Role-Based Dashboards) | Adds front_desk + technician roles. Phase 23 access control policy (23C) documents the role permission matrix including these additive roles |
| Phase 21A (Specialty Modules) | New tables (retina_tracking, glaucoma_tracking, etc.) become PHI under the data-flow map (23B) |
| Phase 21B (Imaging Pipeline) | Imaging files are PHI. The data-flow map (23B) explicitly covers imaging storage URI hosting; the backup policy (23C) covers imaging backup; the vendor inventory (23B) covers the storage backend vendor |
| Phase 21C (Positioning) | The exact safe readiness statement (Section 9) is the **only** HIPAA-readiness phrasing allowed in updated decks / website / one-pagers |
| Phase 22 (Multi-Clinic) | Multi-location deployments multiply BAA / vendor-review surface area. Customer responsibility matrix (23A) accommodates per-location approval |

## 12. Implementation Order Recommendation

Phase 23 can begin **in parallel** with product work (20B → 22)
because the artifact deliverables (23A–C) are docs-only and
don't conflict with code PRs. The product-code subphases (23D–F)
land last because they need the docs as the source of truth.

Suggested order:

1. **23A** + **23B** in parallel — both are docs-only
2. **23C** after 23A merges (policies reference the control matrix)
3. **23D** after 23A–C land (admin dashboard implements the policy contract)
4. **23E** in parallel with 23D (operational tooling, independent of admin UI)
5. **23F** last — bundles everything into the review packet

**Real PHI cannot begin** until **every** Phase 23 gate is
completed and **the practice's signed go-live document is on
file**. No exceptions.
