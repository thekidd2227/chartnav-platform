# Phase 93 — Real-PHI Readiness Review

**Status:** review document
**Date:** 2026-06-11
**Audience:** ChartNav operator, prospective pilot practice's
security / compliance owner, ARCG legal
**Branch:** `feature/phase-93-pilot-launch-readiness-program`

> **Bottom line:** This repository phase alone does **not** approve
> real PHI in any ChartNav environment. Every gate listed below
> must be closed with written, dated, attributable evidence
> **before** any real protected health information moves through
> ChartNav. If any gate is open, the answer is **no**.

This review extends, and does not replace,
`docs/security/chartnav-real-phi-readiness-status.md` and
`docs/security/chartnav-real-phi-go-live-gate.md`. It is the
Phase 93 sign-off form.

## 1. Statement of non-approval

Phase 91 (Unified Ophthalmology Workspace Engine), Phase 92
(Advanced Clinical Intelligence Layer), and Phase 93 (Pilot
Launch Readiness Program) are **not** a real-PHI approval.

- ChartNav remains a fake-data-only product in this build.
- Local + staging environments refuse non-loopback `DATABASE_URL`
  on reset.
- The release evidence gate (Phase 88) and the Phase 93 launch
  gate run only against synthetic data.
- The buyer-evidence packets, demo scripts, screenshots, and
  videos generated under this phase are explicitly labelled
  "demo mode — no real PHI."

A practice that wishes to move to real PHI must complete every
section below. A signed printout of this review is held by ARCG
and a counterpart copy is held by the practice.

## 2. BAA + vendor review

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 2.1 | Business Associate Agreement executed between the practice (covered entity) and ARCG Systems (business associate) | ARCG legal + practice legal | signed BAA PDF, effective date | ☐ |
| 2.2 | Subprocessor list acknowledged (hosting, monitoring, log destination) | ARCG legal | `docs/security/chartnav-subprocessor-inventory.md` cross-referenced | ☐ |
| 2.3 | Each subprocessor has its own BAA chain **or** is excluded from the PHI path | ARCG legal | BAA chain index | ☐ |
| 2.4 | LLM / STT vendor decision is locked to "no production LLM in this build" | ARCG security + practice CTO | `docs/security/chartnav-llm-provider-decision-memo.md` + `chartnav-stt-vendor-readiness.md` | ☐ |
| 2.5 | The practice has reviewed and accepted the Customer Responsibility Matrix | practice CTO / CISO | `docs/security/chartnav-customer-responsibility-matrix.md` countersigned | ☐ |
| 2.6 | Data Processing Addendum signed if the practice requires one | ARCG legal | DPA PDF | ☐ |

## 3. Hosting + production auth

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 3.1 | Practice-approved hosting region + residency | practice CTO | written approval | ☐ |
| 3.2 | Production-grade Postgres (managed or self-hosted) with backups + point-in-time-recovery | ARCG ops | `scripts/pg_verify.sh` PASS log, backup config screenshots | ☐ |
| 3.3 | Production bearer JWT issuer + audience configured to a practice-controlled identity provider | practice CTO + ARCG ops | OIDC issuer URL, audience claim, redacted token sample | ☐ |
| 3.4 | TLS terminated by a practice-approved load balancer / ingress | practice CTO | cert subject + issuer | ☐ |
| 3.5 | All defaults reviewed for production posture (no demo seed, no fake adapters, no `?demo=1`) | ARCG ops | `env validate` log | ☐ |
| 3.6 | `docs/security/chartnav-production-auth-readiness.md` walked end-to-end | ARCG ops + practice CTO | signed copy | ☐ |

## 4. Access control review

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 4.1 | Named-user list approved by practice administrator | practice administrator | user list + role assignments | ☐ |
| 4.2 | RBAC matrix matches the practice's expected separation of duties | practice CISO | `docs/security/chartnav-access-control-policy.md` countersigned | ☐ |
| 4.3 | Reviewer role is enforced read-only | ARCG ops | `apps/api/tests/test_rbac.py` log from gate | ☐ |
| 4.4 | Per-organization isolation passes the cross-org regression test | ARCG ops | gate log entry for `test_scoping.py` | ☐ |
| 4.5 | Demo identities (`@chartnav.local`) disabled in production | ARCG ops | env override log | ☐ |
| 4.6 | Emergency break-glass procedure documented and walked through | practice administrator + ARCG ops | break-glass runbook countersigned | ☐ |

## 5. Logging + audit retention

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 5.1 | Audit log destination is practice-approved | practice CTO | destination + retention table | ☐ |
| 5.2 | No clinical free text reaches the audit log (sentinel-token regression test) | ARCG ops | `tests/test_end_to_end_clinical_workflow.py::TestEndToEndAuditRedaction` log | ☐ |
| 5.3 | `CHARTNAV_AUDIT_RETENTION_DAYS` set to a practice-approved value | ARCG ops | env config screenshot | ☐ |
| 5.4 | `scripts/audit_retention.py` operator CLI walked through | ARCG ops | dry-run output | ☐ |
| 5.5 | Monitoring + alerting destinations approved | practice CTO + ARCG ops | `docs/security/chartnav-monitoring-logging-readiness.md` countersigned | ☐ |

## 6. Backup + disaster recovery review

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 6.1 | Backup destination encrypted at rest, in a practice-approved region | practice CTO | destination config | ☐ |
| 6.2 | Backup cadence + retention approved by the practice | practice CTO | written approval | ☐ |
| 6.3 | `scripts/backup_controlled_pilot_postgres.sh` rehearsed against staging | ARCG ops | rehearsal log | ☐ |
| 6.4 | `scripts/restore_controlled_pilot_postgres.sh` rehearsed against staging | ARCG ops | rehearsal log | ☐ |
| 6.5 | `scripts/verify_controlled_pilot_backup.sh` PASS against the rehearsal artifact | ARCG ops | verify log | ☐ |
| 6.6 | RTO + RPO documented and signed | practice CTO + ARCG ops | `docs/security/chartnav-backup-disaster-recovery-policy.md` countersigned | ☐ |
| 6.7 | DR drill rehearsed within the last 90 days | ARCG ops | drill report | ☐ |

## 7. Incident + breach response

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 7.1 | Practice incident contact + escalation chain on file | practice administrator | contact card | ☐ |
| 7.2 | ARCG incident on-call rotation on file | ARCG ops | rotation export | ☐ |
| 7.3 | Incident response runbook walked through | ARCG ops + practice CISO | `docs/security/chartnav-incident-breach-response-runbook.md` countersigned | ☐ |
| 7.4 | Breach notification timeline acknowledged | ARCG legal + practice legal | timeline acknowledgement | ☐ |
| 7.5 | Tabletop exercise rehearsed within the last 180 days | ARCG ops + practice CISO | exercise notes | ☐ |

## 8. Support + PHI handling policy

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 8.1 | Support PHI handling policy walked through | ARCG ops + practice CISO | `docs/security/chartnav-support-phi-handling-policy.md` countersigned | ☐ |
| 8.2 | Support tickets do not include PHI (sanitization rule) | ARCG ops | ticket policy doc | ☐ |
| 8.3 | Out-of-band channels (Slack, email) excluded from PHI | ARCG ops | channel policy doc | ☐ |

## 9. Written pilot-site approval

| # | Gate | Owner | Evidence required | Status |
|---|---|---|---|---|
| 9.1 | Practice clinical owner signs explicit go-live approval | practice clinical owner | signed approval PDF | ☐ |
| 9.2 | Practice security owner signs explicit go-live approval | practice CISO | signed approval PDF | ☐ |
| 9.3 | Practice administrator signs explicit go-live approval | practice administrator | signed approval PDF | ☐ |
| 9.4 | Go-live date locked in writing | practice administrator + ARCG ops | go-live email thread | ☐ |
| 9.5 | First-week monitoring cadence locked | practice CISO + ARCG ops | monitoring schedule | ☐ |

## 10. Decision matrix

| Outcome | Meaning |
|---|---|
| GO | Every gate above closed with evidence. Real-PHI go-live may proceed at the signed date. |
| Conditional GO | At most two non-section-9 gates remain open with a named owner and a closure date within 14 days. Real-PHI cannot start until those gates close. |
| NO-GO | Any section-9 gate, or three or more other gates, remain open. ChartNav remains a fake-data product for this practice until the next review. |

This Phase 93 review **does not override** the Phase 18 controlled-
pilot go-live checklist
(`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`).
Both must be green for go-live; the Phase 93 sheet captures the
Phase 91 + Phase 92 + Phase 93 deltas, the Phase 18 sheet captures
the underlying ChartNav baseline.

## 11. What ChartNav still does NOT claim under real PHI

Even with every gate closed, ChartNav still:

- is **not** HIPAA-certified, SOC 2-certified, HITRUST-certified,
  or FDA-cleared.
- is **not** a certified electronic health record.
- does **not** replace the practice's existing EHR.
- does **not** diagnose, recommend treatment, recommend surgery,
  recommend medication changes, recommend IOL choices, or
  recommend imaging modality changes.
- does **not** interpret fundus photographs, OCT scans, visual
  fields, or any imaging modality.
- does **not** place orders, send referrals, bill, code, submit
  claims, or message patients.
- does **not** submit to MIPS, IRIS, CMS, payers, or any external
  registry from this build.

These non-claims survive go-live. They are enforced by the claim
scanners and the runtime safety scanner on every release.

## 12. Reviewer signatures

| Role | Name | Date | Outcome |
|---|---|---|---|
| Practice clinical owner | ___________________ | __________ | GO / Conditional / NO-GO |
| Practice security owner / CISO | ___________________ | __________ | GO / Conditional / NO-GO |
| Practice administrator | ___________________ | __________ | GO / Conditional / NO-GO |
| ARCG ops owner | ___________________ | __________ | GO / Conditional / NO-GO |
| ARCG legal | ___________________ | __________ | GO / Conditional / NO-GO |

Next review date: __________ (no later than 90 days after go-live).
