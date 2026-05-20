# ChartNav Pilot Docs Index

This directory is the operational source-of-truth for **what must be
true before ChartNav talks to a practice**, **what's said during
outreach / discovery / demo**, **what's gated by security review**,
and **what's on the controlled-pilot path to a real-PHI deployment**.

Nothing in this directory is a marketing claim. Every file is
operator-facing: a checklist, a runbook, a script, or a template the
team uses inside a sales / pilot motion.

## Phase 24D — Pilot selection & outreach packaging *(new)*

Use the Phase 24C demo as the anchor. The Phase 24D docs decide
**who to point it at** and **what to say next**.

| File | What it is | When you use it |
|---|---|---|
| [`phase-24d-pilot-practice-selection-criteria.md`](./phase-24d-pilot-practice-selection-criteria.md) | Who qualifies, who doesn't, ideal personas, discovery questions, red flags, pilot acceptance bar | Before any outreach. |
| [`phase-24d-pilot-outreach-message-bank.md`](./phase-24d-pilot-outreach-message-bank.md) | 8 outreach variants (warm intro, cold admin, cold retina, LinkedIn, follow-up, post-demo, security handoff, graceful close) | Drafting outreach. |
| [`phase-24d-pilot-discovery-call-script.md`](./phase-24d-pilot-discovery-call-script.md) | First-call script: open, qualify, pain-score, transition, close, what not to say | Before the discovery call. |
| [`phase-24d-demo-invite-and-agenda.md`](./phase-24d-demo-invite-and-agenda.md) | Demo invite template, agenda, prep note, operator preflight | Scheduling the 30-min fake-data demo. |
| [`phase-24d-post-demo-follow-up-template.md`](./phase-24d-post-demo-follow-up-template.md) | Within-24h follow-up email + attachment matrix by audience | Closing the demo loop. |
| [`phase-24d-pilot-fit-scorecard.md`](./phase-24d-pilot-fit-scorecard.md) | 10-category 0–3 scorecard + recommendation bands + mandatory disqualifiers | After discovery / after demo. |
| [`phase-24d-pilot-objection-cheat-sheet.md`](./phase-24d-pilot-objection-cheat-sheet.md) | 12 buyer-safe responses to the questions that test the safe-claims contract | Open in a side window during every call. |
| [`phase-24d-pilot-tracker-template.md`](./phase-24d-pilot-tracker-template.md) | Pipeline tracker columns + status values + operating rules (no PHI) | Pipeline hygiene; daily / weekly cadence. |

## Phase 65 — controlled pilot readiness execution

Use these after the Phase 63C fake-data buyer-demo smoke is green
and a buyer is moving from outreach/demo into security review. These
docs do not approve real PHI; they organize the gates, handoffs,
operations, triage, metrics, and exit decision for a controlled pilot.

| File | What it is | When you use it |
|---|---|---|
| [`phase-65-controlled-pilot-go-no-go-gate.md`](./phase-65-controlled-pilot-go-no-go-gate.md) | Gate 0-5 decision tool from fake-data demo to expansion decision | Before moving between demo, paid pilot conversation, security review, real-PHI approval, monitored operation, and expansion. |
| [`phase-65-security-review-handoff-checklist.md`](./phase-65-security-review-handoff-checklist.md) | Buyer security-review handoff checklist and evidence map | When a qualified buyer asks for security review. |
| [`phase-65-pilot-operator-runbook.md`](./phase-65-pilot-operator-runbook.md) | Operator runbook for a limited monitored pilot after approval | Once Gate 3 is closed and a first session is scheduled. |
| [`phase-65-issue-incident-triage-template.md`](./phase-65-issue-incident-triage-template.md) | S1-S4 issue template and escalation rules | In the practice-approved private support tracker. |
| [`phase-65-success-metric-tracker-schema.md`](./phase-65-success-metric-tracker-schema.md) | Operational metric tracker schema | Weekly pilot reviews; no clinical outcome claims. |
| [`phase-65-pilot-exit-criteria-decision-memo-template.md`](./phase-65-pilot-exit-criteria-decision-memo-template.md) | Exit criteria and expansion decision template | End-of-pilot decision meeting. |

## Phase 24C — Sales-ready demo package

The reset → demo → recap motion the Phase 24D docs hook into.

- [`../demo/phase-24c-retina-demo-runbook.md`](../demo/phase-24c-retina-demo-runbook.md) — narration + click path.
- [`../demo/phase-24c-retina-shot-list.md`](../demo/phase-24c-retina-shot-list.md) — 12-shot capture plan.
- [`../demo/phase-24c-demo-qa-checklist.md`](../demo/phase-24c-demo-qa-checklist.md) — pre-call QA.
- `scripts/reset_phase24b_retina_demo.sh` — one-command deterministic reset.
- `scripts/check_demo_claims.sh` — paragraph-aware claim-safety gate.

## Phase 13 / 14 — pilot readiness foundations

- [`chartnav-pilot-readiness-checklist.md`](./chartnav-pilot-readiness-checklist.md) — what must be true to demo / pilot.
- [`chartnav-demo-to-pilot-transition-plan.md`](./chartnav-demo-to-pilot-transition-plan.md) — demo → controlled-pilot gates.
- [`chartnav-controlled-pilot-go-live-checklist.md`](./chartnav-controlled-pilot-go-live-checklist.md) — controlled-pilot go-live items.
- [`chartnav-pilot-deployment-guide.md`](./chartnav-pilot-deployment-guide.md) — deployment guide.
- [`chartnav-admin-onboarding-checklist.md`](./chartnav-admin-onboarding-checklist.md) — practice admin onboarding.
- [`chartnav-known-limitations-and-non-goals.md`](./chartnav-known-limitations-and-non-goals.md) — formal non-goals list.
- [`chartnav-pilot-success-metrics.md`](./chartnav-pilot-success-metrics.md) — what success looks like.
- [`chartnav-support-runbook.md`](./chartnav-support-runbook.md) — support escalation runbook.
- [`chartnav-security-review-packet.md`](./chartnav-security-review-packet.md) — packet for the practice's IT / compliance gatekeeper.

## Phase 23 — real-PHI gate (security)

- [`../security/chartnav-real-phi-go-live-gate.md`](../security/chartnav-real-phi-go-live-gate.md) — the per-practice checklist that gates any real-PHI deployment. Every Phase 24D doc that mentions real PHI points here.

## Cross-referenced from outside `docs/pilot/`

- [`../commercial/chartnav-commercial-readiness-map.md`](../commercial/chartnav-commercial-readiness-map.md) — what's built, demo-ready, pilot-ready, not yet.
- [`../commercial/chartnav-approved-claims-language.md`](../commercial/chartnav-approved-claims-language.md) — the master approved-language list. The Phase 24D outreach copy must stay consistent with this file.
- [`../commercial/chartnav-ophthalmology-positioning-language-guide.md`](../commercial/chartnav-ophthalmology-positioning-language-guide.md) — Phase 21C ophthalmology-specific language guide.

## House rules

- **No real PHI** in any file under `docs/pilot/`. Practice
  contact info is fine; patient data is not. The Phase 24D
  tracker explicitly bans it.
- **No marketing claims that contradict the safe-claims
  contract.** The objection cheat sheet is the working contract;
  the commercial scripts under `scripts/check_*claims*.sh`
  enforce it mechanically.
- **No website publish, no media generation** from this
  directory. Those are separate motions with their own gates.
- **Internal-only docs are internal-only.** The post-demo
  follow-up template lists which Phase 24D files are safe to
  share with a practice and which are internal-operator-only.
  When in doubt, rewrite into the email body — do not forward
  the internal doc.
