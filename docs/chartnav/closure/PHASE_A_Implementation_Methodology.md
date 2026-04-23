# Phase A — Implementation Methodology

## 1. Problem solved

The buyer brief flagged that ChartNav's pilot story is technical — it does not yet describe how a clinic actually adopts the product over ninety days. A pilot with no go-live sequence, no training matrix, no support window, no rollback plan, and no coexistence logic is indistinguishable from a demo. The first clinic that runs into friction without a named runbook will churn, and there will be no reference account.

This methodology is the operational contract: what we do, when we do it, who does it, how the clinic continues operating if ChartNav fails, and what honest support looks like given the company's current size.

## 2. Current state

- ChartNav ships with 231 backend tests, 55 frontend tests, and an Axe-AA release gate. State machine, pre-sign checkpoint, and typed-name approval are live.
- Deployment modes in code: `standalone`, `integrated_readthrough` (FHIR R4 read), `integrated_writethrough` (501 unless a vendor adapter exists).
- No signed pilots. No SOC 2 / HITRUST certification. No 24×7 support. No pager-duty-equivalent.
- Seeded roles: `admin`, `clinician`, `reviewer` (org1 + org2). `front_desk` is in code only; `technician` and `biller_coder` do not yet exist (added in the RBAC spec in this closure batch).
- No customer-facing training material, no runbook for on-site go-live, no documented rollback path.

## 3. Required state

A documented, repeatable Phase A pilot methodology covering:

1. A T-30 through T+30 go-live sequence.
2. A role-by-role training matrix with hours, topics, and owner.
3. An honest support window (business-hours email during pilot).
4. A named escalation path.
5. A rollback plan that guarantees the clinic can keep documenting for 90 days even if ChartNav is pulled.
6. A coexistence pattern based on `integrated_readthrough` — ChartNav runs **alongside** the existing EHR, not in place of it.
7. A sample week-by-week 90-day pilot runbook.

## 4. Acceptance criteria

- Go-live sequence documented, rehearsed at least once against a synthetic clinic before the first real pilot.
- Training matrix signed off by clinical lead + an ophthalmology advisor.
- Support window, SLOs, and escalation path published in the pilot agreement and in `docs/chartnav/pilot/support.md`.
- Rollback plan tested end-to-end on a non-production database: a clinic can export all their ChartNav data in the canonical handoff format, and can continue on paper or on their prior EHR without ChartNav for the remainder of the 90-day window.
- Coexistence mode (`integrated_readthrough`) smoke-tested against a FHIR R4 sandbox; read-only pattern demonstrably does not write to the EHR.
- Week-by-week runbook lives in `docs/chartnav/pilot/90_day_runbook.md`.

## 5. Codex implementation scope

This is primarily a documentation and process deliverable. The code footprint is deliberately small:

- `apps/api/app/api/routes.py` — `GET /admin/pilot-health` returning a pilot-scoped health snapshot (encounter count, sign rate, export rate, error rate last 7d), gated by `admin`.
- `apps/web/src/features/admin/PilotHealthPane.tsx` — read-only pane for the admin role.
- `scripts/pilot/export_all_for_clinic.py` — one-shot export of every signed encounter in a named org to the canonical handoff format; used at end-of-pilot or rollback.
- `docs/chartnav/pilot/` (new directory): `go_live_sequence.md`, `training_matrix.md`, `support.md`, `escalation.md`, `rollback.md`, `coexistence.md`, `90_day_runbook.md`.

## 5.1 Go-live sequence

| Milestone | Owner | Deliverable |
|---|---|---|
| T-30 | ARCG ops | Pilot agreement signed, clinic org provisioned, five role accounts created, FHIR endpoint confirmed if `integrated_readthrough` |
| T-21 | Clinical lead | Template advisor-review sign-off recorded, clinic-specific CPT/ICD favorites captured |
| T-14 | Engineering | Environment hardened, backups verified, pilot-health pane live, export script dry-run against synthetic org |
| T-7 | Training | Role-by-role training delivered (see 5.2), iPads provisioned with Safari bookmark + mic permission pre-granted, touch-target audit passed on physical devices |
| T-3 | Ops | Parallel-run rehearsal: one tech + one provider chart a full exam on ChartNav **and** their prior EHR; handoff bundle imported into biller workflow as a dry run |
| T-0 | Ops + Clinical | Live go-live with a single clinic day, at most one provider, at most six patients; ARCG ops on-site or on-call for every encounter |
| T+7 | Ops | Review: sign rate, export rate, missing-data-flag distribution, provider time-in-note; decide whether to expand to a second provider |
| T+30 | Ops + Clinical | Midpoint review; rollback-or-continue decision with written rationale |

## 5.2 Training matrix

| Role | Hours | Topics | Delivered by |
|---|---|---|---|
| admin | 2.0 | User management, pilot-health pane, audit review, rollback | ARCG ops |
| front_desk | 1.0 | Schedule, reminders, encounter-creation handoff to tech | Clinical lead |
| technician | 2.0 | Template selection, VA/IOP/pupils capture, slit-lamp structured entry, iPad discipline | Clinical lead + ophthalmology advisor |
| clinician | 3.0 | Trust UI, pre-sign checkpoint, attestation flow, template structure, CPT/ICD entry discipline, offline behavior | Ophthalmology advisor |
| biller_coder | 1.5 | Export bundle, handoff payload, CSV/PDF ingest into current PM/RCM | ARCG ops + clinic biller |

Total: ~10 role-hours per clinic. Sessions are live (Zoom or in-person), recorded, and followed by a 15-minute written Q&A window.

## 5.3 Support window

- **Hours:** business hours in the clinic's local timezone, Monday–Friday.
- **Channel:** a dedicated pilot email alias (`pilot-<clinic>@chartnav.local` in dev; real alias in prod).
- **SLO, honestly stated:** first response within 4 business hours; resolution target within 1 business day for P1 (encounter cannot be signed), 3 business days for P2 (export bundle incorrect), best-effort for P3.
- **What we do not offer in Phase A:** 24×7 on-call, phone pager, dedicated customer success manager, formal uptime SLA. These are out of scope and explicitly disclaimed in the pilot agreement.

## 5.4 Escalation path

1. Clinic front desk or clinical lead emails the pilot alias.
2. ARCG ops triages and engages engineering if the issue is a code defect.
3. If a P1 spans more than one business day, the ARCG founder is paged via the on-call runbook. Pager-duty-equivalent is the ARCG ops phone tree — we do **not** claim a PagerDuty / OpsGenie integration in Phase A.

## 5.5 Rollback plan

- The clinic retains full access to their prior documentation pathway (paper, existing EHR, or scribe-based workflow) for at least 90 days after go-live.
- At any time, the clinic can request a full export via `scripts/pilot/export_all_for_clinic.py`. Every signed encounter is delivered in the canonical handoff payload plus PDF. Unsigned drafts are **not** exported — they are clinical opinions in progress and are discarded on rollback.
- The pilot agreement names the rollback trigger: any clinical or compliance concern from the clinical lead, any unresolved P1 at 3 business days, or any security finding from the clinic's IT.

## 5.6 Coexistence logic (`integrated_readthrough`)

- ChartNav reads from the EHR's FHIR R4 endpoint: `Patient`, `Encounter`, `Observation`, `Condition`, `MedicationRequest`. Read-only, no write.
- ChartNav does **not** replace the EHR. The clinic's existing schedule, billing, and long-term record remain in the EHR.
- At sign time, the handoff bundle is produced; the biller imports it into the EHR's PM module. ChartNav stays an adjunct.
- The `standalone` mode is permitted for clinics with no modern EHR, but every buyer conversation should default to `integrated_readthrough` framing to avoid positioning ChartNav as an EHR replacement.

## 5.7 Sample 90-day runbook (week-by-week)

| Week | Activity |
|---|---|
| 1 | One provider, one tech, half-day clinic. ARCG ops on-site. Daily retro. |
| 2 | Same pair, full clinic day. Retro twice. Review missing-data-flag rate. |
| 3 | Add second provider. Template-review cycle with advisor if any findings look wrong. |
| 4 | First biller feedback session on handoff bundle. Adjust CSV column shape if needed (schema bump to 1.0.x). |
| 5–6 | Steady-state for two providers. Focus on time-in-note measurement. |
| 7 | Midpoint review (T+30 gate). Go / adjust / stop decision written down. |
| 8–10 | If "go," extend to all providers on retina and glaucoma templates. |
| 11 | Load test the export pipeline at week-full volume. |
| 12 | Pilot closeout: reference-account decision, contract conversion or rollback. |

## 6. Out of scope / documentation-or-process only

- Formal SaaS operations (multi-region, auto-scaling, 99.9% SLA contract).
- SOC 2 Type II or HITRUST certification audit.
- Customer-success tiering, named CSMs, QBRs.
- Patient-facing portal or patient communications.
- Procurement paperwork templates (MSA, BAA, DPA) — exist, but live under `docs/chartnav/legal/`, not under this methodology.

## 7. Demo honestly now vs. later

**Now:** walk a buyer through the 90-day runbook, the training matrix, and the pilot-health pane. Show the rollback export on a seeded org. Point at the `integrated_readthrough` FHIR read working against a sandbox.

**Later:** formal SLA contracts, 24×7 support, customer success org, certification attestations, multi-pilot parallel operation.

## 8. Dependencies

- Phase A RBAC (admin pilot-health pane requires the five-role matrix).
- Phase A Structured Charting and Attestation (rollback export relies on locked, attested encounters).
- Phase A PM / RCM Continuity (handoff payload is what the biller ingests at T+7 and at rollback).
- Phase A Tablet Charting (T-7 training on physical iPads assumes the tablet spec is met).

## 9. Truth limitations

- No 24×7 support. No pager. No uptime SLA. No SOC 2.
- ARCG ops is a small team. The methodology assumes one pilot at a time, not five in parallel.
- `integrated_writethrough` returns 501 for unsupported vendors. A clinic whose EHR requires write-back cannot use that mode yet, and the methodology routes them to `integrated_readthrough` or `standalone` instead.
- Rollback export covers signed encounters only. Clinics must understand that drafts in progress are not part of the record of truth.

## 10. Risks if incomplete

- First pilot goes live without a runbook. The first friction point (a mis-typed attestation, a dropped mic permission, a biller CSV column mismatch) becomes the story told to every other buyer.
- Clinic cannot articulate a rollback path to their IT and compliance reviewers. Pilot never starts.
- ARCG over-promises on support during the sale and under-delivers at week three. The reference account turns hostile.
- Without a coexistence pattern, ChartNav is evaluated as an EHR replacement, loses that comparison on breadth, and never gets a chance to win on depth.
