# ChartNav Security Risk Analysis Template

> **Phase:** 23.
> **Type:** Template for the joint ChartNav + practice risk
> register. Each line is a working risk; the practice and
> ChartNav own different mitigations.

## How to use this template

1. Copy this file to a working risk register inside the
   practice's security records (do **not** check the working
   register into this repo — keep this file as the canonical
   template).
2. Walk every line during the practice's security review.
3. Mark **Closed** rows when the listed mitigation evidence
   exists.
4. Re-walk annually or after any material architectural change.

## Columns

| Column | Meaning |
|---|---|
| **Asset** | The thing being protected (data, system, role, vendor). |
| **Threat** | What could go wrong. |
| **Vulnerability** | Why the threat is plausible. |
| **Likelihood** | Low / Medium / High / Critical. |
| **Impact** | Low / Medium / High / Critical. |
| **Current control** | What ChartNav / the practice already has in place. |
| **Gap** | What's missing today. |
| **Mitigation** | What closes the gap. |
| **Owner** | ChartNav / Practice / Hosting / Identity provider / Vendor. |
| **Target date** | When the gap closes. |
| **Evidence** | Where to find the proof the gap is closed. |

---

## Starter rows *(template — customize per practice)*

| # | Asset | Threat | Vulnerability | Likelihood | Impact | Current control | Gap | Mitigation | Owner | Target date | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Postgres database | Unauthorized read of ePHI | DB credentials stolen or misconfigured | Medium | Critical | Hosting-managed network isolation; bearer auth gate | Practice TLS endpoint verification | Practice security review during Gate 3 | Practice + Hosting | Before real-PHI start | Practice's hosting BAA + ChartNav's validator output |
| 2 | Session tokens | Token replay or theft | JWT bearer at rest in browser | Medium | High | Short-lived tokens issued by identity provider; HTTPS-only transport | Identity-provider session timeout enforcement | Identity-provider configuration | Identity provider | Before real-PHI start | IdP session-timeout setting |
| 3 | User account | Unauthorized access via stolen credentials | Password-only auth | High | Critical | Production bearer mode rejects header auth; identity-provider MFA expected | MFA enforcement at IdP | Practice enforces MFA at identity provider | Practice + IdP | Before real-PHI start | IdP MFA policy |
| 4 | Audit log | Audit gap on critical operation | Audit-event class incomplete | Low | High | `should_audit` helper; metadata-only `detail`; sentinel tests | Periodic audit-class review | Joint review on each phase | ChartNav + Practice | Annual + on major releases | This repo's `tests/test_phase_*.py` audit checks |
| 5 | Audit log | PHI leak via audit detail | Audit serializer accidentally includes clinical text | Low | Critical | Metadata-only contract; sentinel tests for every Phase 21A / 21B / 22 audit event | Continued sentinel coverage on new endpoints | Add sentinel test for every new audited event | ChartNav | Continuous | Test suite |
| 6 | Backup file | Unauthorized read of backup | Backup destination misconfigured | Medium | Critical | Encrypted at hosting layer; destination must be approved | Practice-approved destination + BAA | Practice approves destination during Gate 4 | Practice + Hosting | Before real-PHI start | Backup destination in hosting console |
| 7 | Backup file | Backup not restorable | Restore never tested | Medium | Critical | `scripts/restore_controlled_pilot_postgres.sh` exists | Restore test in non-production | Practice runs restore test | Practice | Before real-PHI start | Restore-test log |
| 8 | STT vendor (OpenAI Whisper) | PHI egress without BAA | STT enabled inadvertently | Low | Critical | Disabled by default; explicit `CHARTNAV_PILOT_ALLOW_STT_OPENAI_WHISPER` gate | Practice approval if enabled | Practice signs off on STT BAA before enabling | Practice + Vendor | Only if enabled | Override env value + BAA |
| 9 | AI / LLM vendor | PHI egress without BAA | External LLM enabled inadvertently | Low | Critical | Deterministic default; ChartNav's audit `ai_governance_log` stores hashed prompts only | Practice approval if enabled | Practice signs off on LLM BAA before enabling | Practice + Vendor | Only if enabled | LLM configuration + BAA |
| 10 | Imaging storage | PHI egress without BAA | Storage URI points at a non-approved vendor | Medium | Critical | ChartNav stores metadata only; binaries live in practice's storage; `data:` URI rejected | Practice approves storage backend BAA | Practice signs off | Practice | Before real-PHI start | Storage vendor BAA |
| 11 | Cross-organization access | Cross-org leak | Bypassed isolation check | Low | Critical | `ensure_same_org` + 404 (no existence leak); 32+ Phase 22 tests cover isolation | Continued coverage on new endpoints | Add isolation tests on every new resource | ChartNav | Continuous | Test suite |
| 12 | Provider role assignment | Wrong-role access | Practice fails to assign correct role | Medium | High | RBAC enforced in code; admin assigns roles | Practice role-review cadence | Practice reviews roles quarterly | Practice | Quarterly | Practice's role-review log |
| 13 | Support ticket | PHI in support ticket | Operator pastes PHI accidentally | Medium | High | Support PHI handling policy; explicit policy in `chartnav-support-phi-handling-policy.md` | Operator training | Practice + ChartNav training | Practice + ChartNav | Continuous | Training records |
| 14 | Production credentials | Secret leak | Secrets committed to repo | Low | Critical | `.gitignore` rules; `scripts/validate_controlled_pilot_env.sh` never prints values | Secret-scanning in CI | Add `gitleaks`-like scan | ChartNav | Phase 24 candidate | CI workflow |
| 15 | Incident response | Slow practice notification | Practice contact stale | Medium | High | `chartnav-incident-breach-response-runbook.md` includes contact captured during Gate 8 | Annual practice-contact refresh | Practice re-confirms annually | Practice + ChartNav | Annual | Renewed contacts |
| 16 | Vendor change | New vendor without BAA | Architecture change adds vendor | Low | Critical | Vendor change process documented | Continued enforcement | ChartNav notifies before routing PHI through new vendor | ChartNav + Practice | Continuous | Vendor change notification log |
| 17 | Audit retention | Audit log over-retained | Retention not enforced | Low | Medium | `CHARTNAV_AUDIT_RETENTION_DAYS` + `scripts/audit_retention.py` | Practice-agreed retention duration | Set during Gate 6 | Practice + ChartNav | Before real-PHI start | Env value + BAA / side letter |
| 18 | Audit retention | Audit log under-retained | Retention set too short | Low | Medium | Same as above | Practice-agreed retention duration | Set during Gate 6 | Practice + ChartNav | Before real-PHI start | Env value + BAA / side letter |
| 19 | Note export | Exfiltration of signed notes | Admin export endpoint misuse | Low | Critical | Admin role required + audit on every export + immutable signed artifacts | Admin role-review cadence | Practice reviews admin role quarterly | Practice | Quarterly | Practice's role-review log |
| 20 | Imaging review | Marked reviewed without provider check | Role policy bypassed | Low | High | `_require_review_access` checks admin/clinician only; technician cannot mark reviewed | Continued coverage on new endpoints | Add role tests on every new write endpoint | ChartNav | Continuous | Test suite |

---

## How to extend this template

Add new rows when:

- A new ChartNav phase introduces a new endpoint, table, or
  vendor relationship.
- The practice's threat model identifies a risk not in the
  starter list.
- A near-miss incident surfaces a new attack class.
- An audit finding identifies a missing control.

Do **not** delete rows when they close — mark them **Closed**
and keep the evidence pointer. The closed rows form the
historical record.

## What this template does NOT do

- Does not attest to HIPAA compliance.
- Does not replace the practice's own risk analysis.
- Does not bind a specific date to mitigation work.
- Does not list every conceivable risk — it lists the ones
  ChartNav's architecture surfaces. Practice-side risks
  (workforce training, physical security, etc.) are owned by
  the practice.
