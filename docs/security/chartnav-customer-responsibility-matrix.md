# ChartNav Customer Responsibility Matrix

> **Phase:** 23.
> **Type:** Shared responsibility model. Counter-signed by the
> practice + ChartNav (ARCG Systems) before real-PHI start.
> **Not** an attestation of compliance; an explicit who-owns-what
> contract.

## Status legend

| Symbol | Meaning |
|---|---|
| **C** | ChartNav (ARCG Systems) — implemented in product / operational tooling. |
| **P** | Practice / customer — practice owns the operational responsibility. |
| **H** | Hosting provider — managed at the infrastructure layer. |
| **I** | Identity provider — managed at the IdP layer. |
| **V** | Optional AI / STT vendor — only when enabled by the practice. |
| **C+P** | Shared — both parties have explicit responsibilities. |

---

## Identity, authentication, authorization

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Bearer JWT auth code | ✅ | | | | |
| User provisioning | | ✅ | | | |
| User termination / offboarding | | ✅ | | | |
| MFA enforcement | | | | ✅ | |
| Session timeout enforcement | | | | ✅ | |
| ChartNav role assignment (`admin / clinician / reviewer / technician / front_desk`) | | ✅ | | | |
| Identity-provider configuration | | ✅ | | ✅ | |
| OIDC issuer / audience / JWKS URL configuration | | ✅ | | | |

## Hosting + infrastructure

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Application code | ✅ | | | | |
| Production deployment choice | | ✅ | | | |
| Postgres hosting | | | ✅ | | |
| TLS termination | | | ✅ | | |
| Operating system patching | | | ✅ | | |
| Physical security of hosting | | | ✅ | | |
| Hosting BAA execution | | ✅ | | | |
| Network firewall / VPC config | | ✅ | ✅ | | |

## Data

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Schema / migrations | ✅ | | | | |
| Org isolation enforcement (code) | ✅ | | | | |
| Role-based access enforcement (code) | ✅ | | | | |
| Audit logging — metadata only | ✅ | | | | |
| Audit retention duration agreement | | ✅ | | | |
| Audit retention enforcement (script) | ✅ | | | | |
| Data classification of practice records | | ✅ | | | |
| Encryption at rest | | | ✅ | | |
| Encryption in transit | ✅ | | ✅ | | |
| Practice device / workstation security | | ✅ | | | |

## Backups + disaster recovery

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Backup script | ✅ | | | | |
| Backup destination configuration | | ✅ | | | |
| Backup encryption | | | ✅ | | |
| Restore script | ✅ | | | | |
| Restore-test schedule | | ✅ | | | |
| RPO / RTO commitment | | ✅ | | | |
| Backup failure alerting | | ✅ | ✅ | | |
| Backup-vendor BAA | | ✅ | | | |

## Monitoring + logging

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Application logging code | ✅ | | | | |
| Log forwarding configuration | | ✅ | | | |
| Log retention | | ✅ | | | |
| Log-vendor BAA | | ✅ | | | |
| Health-check endpoint | ✅ | | | | |
| Alert routing | | ✅ | | | |
| On-call coverage | | ✅ | | | |

## Incident response

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Incident response runbook (Phase 23) | ✅ | | | | |
| Practice incident-response contact | | ✅ | | | |
| Vendor incident-response contacts | | ✅ | | ✅ | ✅ |
| ChartNav incident-response contact | ✅ | | | | |
| Breach notification timing — legal review | | ✅ | | | |
| Practice notification of patients (if breach) | | ✅ | | | |
| Post-incident review participation | ✅ | ✅ | | | |

## Vendor / subprocessor management

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Subprocessor inventory template | ✅ | | | | |
| Subprocessor inventory tracking | ✅ | ✅ | | | |
| BAA execution with each subprocessor | ✅ | | | | |
| Practice's vendor BAAs (hosting / log / etc.) | | ✅ | | | |
| STT / AI / LLM PHI egress approval | | ✅ | | | ✅ |
| Vendor change notification | ✅ | | | | |

## Support + operational

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| Support request triage | ✅ | | | | |
| Support access approval | | ✅ | | | |
| No PHI in support tickets | ✅ | ✅ | | | |
| Secure evidence-handling channel | | ✅ | | | |
| Support ticket retention | ✅ | | | | |
| Production rollback authority | ✅ | ✅ | | | |
| Production disable / pause authority | | ✅ | | | |

## Compliance + legal

| Responsibility | C | P | H | I | V |
|---|---|---|---|---|---|
| ChartNav-practice BAA execution | ✅ | ✅ | | | |
| Practice's HIPAA workforce training | | ✅ | | | |
| Practice's HIPAA risk analysis | | ✅ | | | |
| ChartNav HIPAA readiness control matrix | ✅ | | | | |
| Real-PHI go-live approval | | ✅ | | | |
| Real-PHI start date setting | | ✅ | | | |

## Out of scope for both

| Item | Why |
|---|---|
| Patient portal / patient messaging | ChartNav has no patient-facing surface. |
| Automatic orders / referrals | ChartNav does not submit any. |
| Automatic coding / billing | ChartNav does not bill. |
| Insurance / payment / claims | ChartNav does not handle. |
| Autonomous diagnosis | ChartNav does not diagnose. |
| Device-vendor integration claims | ChartNav has no current vendor adapters. |

---

## Sign-off

> Both parties sign below to acknowledge the above
> shared-responsibility model. This is **not** a substitute for
> the BAA; it is a working document the parties refer to during
> the controlled-pilot lifecycle.

ChartNav (ARCG Systems): `__________` Date: `__________`

Practice security owner: `__________` Date: `__________`
