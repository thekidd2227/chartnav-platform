# Phase 23 — HIPAA-Regulated Deployment Readiness Implementation

> **Status:** Implemented (this PR).
> **Type:** 11 new security / compliance docs + 1 new admin
> endpoint + 1 new admin frontend panel + 11 backend tests + 4
> frontend tests + Phase 23 implementation doc.
> **Builds on:** Phase 20A.1 (controlled-pilot PHI readiness
> hardening) and the existing security/pilot docs.
> **Branch:** `feature/phase-23-hipaa-regulated-deployment-readiness`.
>
> **ChartNav is not approved for real PHI by default. ChartNav is
> not HIPAA-certified. This phase ships readiness artifacts and a
> metadata-only environment-shape reporter — not an attestation.**

This phase implements the legal / operational / security
documentation, validator coverage, admin evidence surface, and
audit / monitoring support a HIPAA-regulated controlled-pilot
deployment requires.

## What was implemented

### 11 new docs under `docs/security/`

| Doc | Purpose |
|---|---|
| `chartnav-hipaa-readiness-control-matrix.md` | HIPAA Security Rule control family table with implementation status + owner + gap + evidence per control. |
| `chartnav-real-phi-go-live-gate.md` | Single per-practice gate. 10 gate sections — every checkbox must close before real PHI. |
| `chartnav-baa-vendor-readiness-checklist.md` | Vendor-by-vendor BAA + PHI-egress status. |
| `chartnav-customer-responsibility-matrix.md` | Shared-responsibility model between ChartNav, practice, hosting, IdP, and optional AI/STT vendor. |
| `chartnav-subprocessor-inventory.md` | Working inventory of every subprocessor that could touch ePHI. |
| `chartnav-phi-data-flow-map.md` | Architectural data-flow reference — every place ePHI may live or transit. |
| `chartnav-security-risk-analysis-template.md` | Joint risk-register template with 20 starter rows. |
| `chartnav-incident-breach-response-runbook.md` | Step-by-step operational sequence for incident / breach response. Notification timelines marked as legal-review-required. |
| `chartnav-access-control-policy.md` | Production auth, MFA, least-privilege, role-review cadence, termination process. |
| `chartnav-backup-disaster-recovery-policy.md` | Backup tooling, cadence, destination, retention, restore testing, RPO/RTO placeholders. |
| `chartnav-support-phi-handling-policy.md` | "No PHI in support tickets" cardinal rule + secure evidence channel. |

Every doc explicitly states ChartNav is **not** HIPAA-certified
and is **not** approved for real PHI by default. Every checklist
marks practice-side / hosting-side / IdP-side / vendor-side items
as **external / practice-dependent**.

### New admin endpoint

`GET /admin/security/readiness` — admin-only, returns metadata-only
readiness summary. Status labels:

- `configured` — env var present with a non-empty value.
- `missing` — env var unset.
- `external_required` — control owned by hosting / IdP / vendor.
- `disabled` — feature intentionally disabled (safe state).

Fields returned: `organization_id`, `auth_mode`, `database_kind`,
`audit_retention_configured`, `cors_explicit_configured`,
`jwt_issuer_configured`, `jwt_audience_configured`,
`jwt_jwks_url_configured`, `stt_provider`,
`backup_config_documented`, `logging_config_documented`,
`monitoring_config_documented`, `incident_contacts_documented`,
`baa_status_configured`, `vendor_review_status_configured`,
`real_phi_go_live_gate_status`, `compliance_attestation`.

**Never returns** env values, secrets, or PHI. The
`compliance_attestation` field carries an explicit negative
disclaimer: "ChartNav is not HIPAA-certified. ChartNav is not
approved for real PHI by default. This endpoint reports
metadata-only environment shape; it does not attest to
compliance."

### New admin frontend panel

`apps/web/src/SecurityReadinessPanel.tsx` — admin-only readiness
checklist. Renders 15 status rows + the disclaimer. Status pills
are color-coded (`ok` / `warn` / `fail`). Non-admin identities
see a blocked placeholder; the panel never calls the endpoint
from a non-admin context. New sidebar entry: ADMIN > Security
Readiness.

### Tests

- Backend: 11 cases (`tests/test_phase_23_security_readiness.py`)
  — auth required, non-admin blocked, admin allowed, every label
  in the allow-list, disclaimer present, no env values leaked,
  dev header mode reports `missing`, Postgres URL reports
  `configured`, SQLite URL reports `missing`, STT default reports
  `disabled`, STT openai_whisper reports `external_required`, no
  positive compliance claims outside the disclaimer.
- Frontend: 4 cases
  (`test/SecurityReadinessPanel.test.tsx`) — non-admin blocked
  state, populated rendering with disclaimer, error path, no
  HIPAA-compliant claims outside the disclaimer.

## Scripts (unchanged — already enforce Phase 23 contracts)

The existing `scripts/validate_controlled_pilot_env.sh`,
`scripts/backup_controlled_pilot_postgres.sh`,
`scripts/restore_controlled_pilot_postgres.sh`,
`scripts/verify_controlled_pilot_backup.sh`, and
`scripts/smoke_controlled_pilot.sh` already enforce the Phase 23
contracts:

- `CHARTNAV_AUTH_MODE=bearer` gate.
- JWT issuer / audience / JWKS URL gate.
- `DATABASE_URL` Postgres gate (refuses SQLite).
- Explicit CORS gate (no wildcard).
- Audit retention gate.
- STT/AI provider disabled-by-default with explicit override gate.
- No fake-data seeding in controlled-pilot.
- Backup scripts never print secrets and require restore
  confirmation.

No script edits needed. All five script files `bash -n` clean.

## Non-goals (intentional)

- ❌ **No claim of HIPAA compliance.** Every doc says ChartNav
  is not HIPAA-certified.
- ❌ **No claim of certified-EHR status.**
- ❌ **No real PHI.** Every doc is fake-data-friendly.
- ❌ **No fake BAAs, no fake security approvals, no fake customer
  approvals, no fake pen-test reports, no fake SOC 2.**
- ❌ **No production credentials, no secrets committed.**
- ❌ No patient portal / patient messaging.
- ❌ No automatic orders / referrals / coding / billing /
  insurance / payment / claims.
- ❌ No DICOM ingestion / binary image storage expansion / device
  vendor integration.
- ❌ No `chartnavmd.com` publish / website / commercial-deck /
  media changes.

## Real-PHI gates that remain external

Phase 23 ships **technical scaffolding** but most go-live gates
are **practice-side**. Required before real PHI:

- BAA executed between practice and ChartNav.
- BAA executed between ChartNav and every subprocessor that
  touches ePHI.
- Practice security owner identified.
- Practice security review accepted.
- Production bearer auth + MFA at IdP.
- Postgres in approved hosting environment.
- Backups configured and restore tested.
- Monitoring + alerting configured.
- Audit retention agreed.
- Vendor / subprocessor review complete.
- STT / AI / LLM PHI egress approved or disabled.
- Incident contacts documented.
- Support process approved.
- Written practice approval.
- Real PHI start date approved.

Every one of these lives in `chartnav-real-phi-go-live-gate.md`.

## Files touched

- `docs/security/chartnav-hipaa-readiness-control-matrix.md` (new)
- `docs/security/chartnav-real-phi-go-live-gate.md` (new)
- `docs/security/chartnav-baa-vendor-readiness-checklist.md` (new)
- `docs/security/chartnav-customer-responsibility-matrix.md` (new)
- `docs/security/chartnav-subprocessor-inventory.md` (new)
- `docs/security/chartnav-phi-data-flow-map.md` (new)
- `docs/security/chartnav-security-risk-analysis-template.md` (new)
- `docs/security/chartnav-incident-breach-response-runbook.md` (new)
- `docs/security/chartnav-access-control-policy.md` (new)
- `docs/security/chartnav-backup-disaster-recovery-policy.md` (new)
- `docs/security/chartnav-support-phi-handling-policy.md` (new)
- `apps/api/app/api/admin_security.py` (appended `/readiness`
  endpoint)
- `apps/api/tests/test_phase_23_security_readiness.py` (new, 11
  tests)
- `apps/web/src/api.ts` (Phase 23 types + function appended)
- `apps/web/src/SecurityReadinessPanel.tsx` (new)
- `apps/web/src/App.tsx` (top-view switch + ADMIN > Security
  Readiness sidebar entry)
- `apps/web/src/styles.css` (Phase 23 CSS)
- `apps/web/src/test/SecurityReadinessPanel.test.tsx` (new, 4
  tests)
- `docs/product/phase-23-hipaa-regulated-deployment-readiness-implementation.md`
  (this file)

## Validation

- `bash scripts/check_commercial_claims.sh` — **PASSED** (0 fail
  / 0 warn).
- `bash scripts/check_website_claims.sh` — **PASSED** (0 fail
  / 0 warn).
- `bash -n` on all five readiness scripts — clean.
- `npx tsc --noEmit` — clean.
- `npx vitest run` — 535 passed (4 new + 531 existing).
- `npx vite build` — clean (438.3 kB JS, 56.4 kB CSS).
- `pytest tests/test_phase_23_security_readiness.py` — 11 / 11
  passing.

## Remaining external requirements

This phase **does not** make any single real-PHI pilot possible
on its own. Every controlled-pilot deployment still requires the
practice-side gates listed in
`chartnav-real-phi-go-live-gate.md`. Phase 23 simply gives the
practice's security owner a working set of artifacts to walk
during their review.
