# ChartNav HIPAA Readiness Control Matrix

> **Phase:** 23 — HIPAA-regulated deployment readiness
> implementation.
> **Status:** Foundation in place. Many controls remain
> **external / practice-dependent** by design.
>
> **ChartNav is not approved for real PHI by default. ChartNav is
> not HIPAA-certified. ChartNav may be prepared to support a
> HIPAA-regulated controlled pilot only after BAA execution,
> practice security review, production bearer authentication,
> approved hosting, backups, monitoring, audit-retention
> agreement, vendor / subprocessor review, incident-response
> contacts, and written practice approval are complete.**

This matrix lists the HIPAA Security Rule control families plus
ChartNav's status against each one. It is **not** an attestation
of compliance. It is a working document the practice's security
owner uses during their own security review.

## Status legend

| Status | Meaning |
|---|---|
| **Implemented** | Control implemented in ChartNav code or operational tooling. |
| **Partially implemented** | Some technical scaffolding exists; operational evidence required from the practice. |
| **Planned** | Listed on the roadmap; no shipping code yet. |
| **External / practice-dependent** | Control is owned by the practice, hosting provider, or identity provider. |
| **Not started** | Neither code nor docs yet. |

---

## Administrative safeguards

| Control | Status | Evidence | Owner | Gap | Required before real PHI |
|---|---|---|---|---|---|
| Security management process | Partially implemented | `chartnav-real-phi-go-live-gate.md` checklist; this matrix | Practice + ChartNav | Practice owner-identification + sign-off | Yes |
| Assigned security responsibility | External / practice-dependent | Practice security officer name + contact | Practice | None on ChartNav side | Yes |
| Workforce security | External / practice-dependent | Practice HR onboarding / termination procedures | Practice | None on ChartNav side | Yes |
| Information access management | Implemented (technical) | Role-based access in `app/authz.py`; cross-org 404; admin-only writes; admin-only security endpoints | ChartNav | Practice must assign roles | Yes |
| Security awareness + training | External / practice-dependent | Practice training records | Practice | None on ChartNav side | Yes |
| Security incident procedures | Partially implemented | `chartnav-incident-breach-response-runbook.md` | ChartNav + Practice | Practice incident contacts; legal-review of notification timelines | Yes |
| Contingency plan | Partially implemented | `chartnav-backup-disaster-recovery-policy.md` | ChartNav + Practice + Hosting | Practice restore tests; documented RPO/RTO | Yes |
| Evaluation | External / practice-dependent | Practice annual review | Practice | None on ChartNav side | Yes |
| Business Associate contracts | External / practice-dependent | BAA executed between ChartNav and practice; BAAs executed between ChartNav and each subprocessor | Practice + ChartNav + Vendors | BAA execution | **Yes — blocking gate** |

## Physical safeguards

| Control | Status | Evidence | Owner | Gap | Required before real PHI |
|---|---|---|---|---|---|
| Facility access controls | External / practice-dependent | Hosting provider physical security; practice device security | Hosting + Practice | None on ChartNav side | Yes |
| Workstation use | External / practice-dependent | Practice workstation policy | Practice | None on ChartNav side | Yes |
| Workstation security | External / practice-dependent | Practice device management | Practice | None on ChartNav side | Yes |
| Device + media controls | External / practice-dependent | Practice device retirement | Practice | None on ChartNav side | Yes |

## Technical safeguards

| Control | Status | Evidence | Owner | Gap | Required before real PHI |
|---|---|---|---|---|---|
| Access control — unique user identification | Implemented | `users.email` unique; production bearer JWT (`apps/api/app/auth.py`) | ChartNav | None | Yes |
| Access control — emergency access | Partially implemented | Admin role + audit trail in `admin_security.py` | ChartNav + Practice | Practice emergency-access procedure | Yes |
| Access control — automatic logoff | External / identity provider | Identity provider session timeout | Identity provider | Identity provider configuration | Yes |
| Access control — encryption + decryption | Implemented (transport) | HTTPS-only deployment; TLS termination at hosting; `apps/api/app/auth.py` rejects header-mode in production | ChartNav + Hosting | Practice TLS endpoints | Yes |
| Audit controls | Implemented | `security_audit_events` table; `app.audit.record` writes metadata-only audit; admin-readable via `/admin/security/events` | ChartNav | Retention agreement | Yes |
| Integrity controls — note versioning | Implemented | `note_versions` immutable; signed retinal artifacts immutable; edits create fork | ChartNav | None | Yes |
| Integrity controls — backup checksums | Partially implemented | `scripts/verify_controlled_pilot_backup.sh` | ChartNav + Hosting | Practice restore-test cadence | Yes |
| Transmission security — encryption in transit | Implemented (transport) | HTTPS-only; CORS explicit | ChartNav + Hosting | Practice TLS endpoint | Yes |
| Transmission security — integrity | Implemented | JWT signature validation; checksum verification on backup files | ChartNav | None | Yes |

## Audit + integrity

| Control | Status | Evidence | Gap |
|---|---|---|---|
| Audit retention | Partially implemented | `CHARTNAV_AUDIT_RETENTION_DAYS` env knob; `scripts/audit_retention.py` enforces | Practice retention agreement |
| Audit content | Implemented | Detail strings are metadata-only — no PHI, no clinical body text. Sentinel tests enforce. | None on ChartNav side |
| Audit access | Implemented | `/admin/security/events` admin-only with org isolation | None on ChartNav side |
| AI governance log | Implemented | `ai_governance_log` table; hashed prompts/outputs only; no raw text or patient identifiers | None on ChartNav side |

## Backup + DR

| Control | Status | Evidence | Gap |
|---|---|---|---|
| Backup tooling | Implemented | `scripts/backup_controlled_pilot_postgres.sh` (refuses SQLite, never prints secrets) | Approved storage destination |
| Restore tooling | Implemented | `scripts/restore_controlled_pilot_postgres.sh` (confirmation required) | Practice restore-test schedule |
| Backup verification | Implemented | `scripts/verify_controlled_pilot_backup.sh` | None on ChartNav side |
| Backup encryption | External / hosting-dependent | Hosting provider managed encryption | Approved hosting choice |

## Incident response

| Control | Status | Evidence | Gap |
|---|---|---|---|
| Incident severity levels | Implemented | `chartnav-incident-breach-response-runbook.md` | Practice escalation contacts |
| Containment procedures | Implemented | Rollback / disable steps documented | None |
| Practice notification | Partially implemented | Notification workflow drafted | Practice contacts + legal-review of timelines |
| Vendor notification | Partially implemented | Vendor notification workflow drafted | Per-vendor contacts |
| Breach assessment | Partially implemented | Assessment template | Legal review |
| Post-incident review | Implemented | Template in runbook | Practice cadence |

## Vendor + subprocessor management

| Control | Status | Evidence | Gap |
|---|---|---|---|
| Subprocessor inventory | Implemented (template) | `chartnav-subprocessor-inventory.md` | Per-vendor BAA execution status |
| BAA execution tracking | Partially implemented | `chartnav-baa-vendor-readiness-checklist.md` | Real BAAs |
| PHI egress controls | Implemented | STT/AI providers default to disabled; `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER` override gate | Practice approval for any external egress |
| Vendor security review | External / practice-dependent | Practice procurement security review | None on ChartNav side |

## Risk analysis + management

| Control | Status | Evidence | Gap |
|---|---|---|---|
| Risk analysis template | Implemented | `chartnav-security-risk-analysis-template.md` | Practice + ChartNav joint risk register |
| Risk mitigation tracking | Partially implemented | Template includes owner / target / evidence columns | Live tracking |
| Annual review cadence | External / practice-dependent | Practice review cadence | None on ChartNav side |

## Policies + procedures

| Document | Status | Path |
|---|---|---|
| Real PHI go-live gate | Implemented | `chartnav-real-phi-go-live-gate.md` |
| Access control policy | Implemented | `chartnav-access-control-policy.md` |
| Backup / DR policy | Implemented | `chartnav-backup-disaster-recovery-policy.md` |
| Support PHI handling policy | Implemented | `chartnav-support-phi-handling-policy.md` |
| Incident / breach runbook | Implemented | `chartnav-incident-breach-response-runbook.md` |
| Customer responsibility matrix | Implemented | `chartnav-customer-responsibility-matrix.md` |
| BAA / vendor checklist | Implemented | `chartnav-baa-vendor-readiness-checklist.md` |
| Subprocessor inventory | Implemented | `chartnav-subprocessor-inventory.md` |
| PHI data flow map | Implemented | `chartnav-phi-data-flow-map.md` |
| Risk analysis template | Implemented | `chartnav-security-risk-analysis-template.md` |

---

## Summary statement

ChartNav has implemented the **technical** controls a HIPAA
Security Rule controlled-pilot environment requires (production
bearer auth, org isolation, role-based access, metadata-only
audit, backup + restore + verify tooling, no PHI egress to
external AI / STT without explicit override, no patient-facing
messaging, no automatic orders / referrals / claims / billing).

ChartNav has **not** implemented the **administrative** controls
that are the practice's responsibility (workforce training, BAA
execution, identity-provider configuration, hosting choice,
audit retention agreement, restore-test cadence, incident
contacts, written practice approval). Those gates appear in
`chartnav-real-phi-go-live-gate.md` and must all close before
real PHI is processed.
