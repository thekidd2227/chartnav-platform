# ChartNav pilot runbook — days 1, 7, 14, 30, 60, 90

> **How to use:** the runbook describes what ARCG does and what the
> practice does at each milestone. The 30 / 60 / 90 reviews are the
> exit-criteria checkpoints; numbers come from
> `/admin/dashboard/summary` and from
> [`exit-criteria.md`](./exit-criteria.md).

## Day 1 — kickoff complete

- ARCG: provision accounts; share onboarding checklist URL; install
  the iPad Safari bookmark.
- Practice: confirm intake-token sharing channel with front desk
  (text / email / scheduling tool — ChartNav does NOT auto-deliver).
- Joint: walk through the first encounter together end-to-end.

## Day 7 — first-week review (15 min)

- Pull `/admin/dashboard/summary` together.
- Triage missing-flag patterns: are flags being resolved or
  dismissed wholesale? See `exit-criteria.md` §2 caveat.
- Confirm the practice is using the correct specialty templates;
  general-ophth catch-all is allowed but not the goal.

## Day 14 — adoption check (30 min)

- KPI cards walked card by card.
- Reminder load reviewed: is the practice generating reminders
  faster than they can complete them? If yes, surface "reminders-
  overdue" as the priority operational issue.
- Intake queue: any tokens issued but not redeemed? Check that
  the front-desk channel is actually reaching patients.

## Day 30 — first formal review (60 min)

Agenda (timed):

| Time | Topic |
|------|-------|
| 0–10 | Walk the dashboard. Numbers to compare to scope-doc targets. |
| 10–25 | Review missing-flag resolution rate. If < 50 %, drill into one offending template. |
| 25–40 | Review the documented sign-to-export lag. If > 12 min p50, root cause one encounter together. |
| 40–55 | Practice answers: what would make ChartNav indispensable in the next 30 days? |
| 55–60 | Decision: continue, adjust scope, or end. |

ARCG produces a 1-page written summary the same day with the
numbers, the qualitative answer, and the next-30-days commitment.

## Day 60 — second formal review (60 min)

- Same dashboard walk-through.
- The "what would make this indispensable" question becomes the
  Phase C / paid-conversion ask. Anything outside Phase B scope
  (real SMS / email, full patient portal, code generation,
  predictive analytics) is parked here, not promised.
- Decision point: paid conversion, extended pilot (max 30 days),
  or graceful exit with the PM/RCM continuity export bundle for
  every signed encounter (Phase A item 4).

## Day 90 — graceful exit (only if not converting)

- ARCG generates the handoff bundle for every signed encounter.
- Practice receives the PDF + JSON + manifest set as a single
  archive.
- ChartNav purges the operational DB within 30 days.
- ARCG sends a final 1-page debrief with raw exit metrics.

## What happens between reviews (cadence)

- Optional weekly sync (30 min, Wed 12:00 PT default). Practice
  may decline.
- Business-hours email per `support-tier.md`.
- ARCG does NOT log into the practice's account between scheduled
  syncs unless an active Sev-1 / Sev-2 ticket requires it.

## What this runbook does NOT promise

- 24/7 monitoring of practice usage.
- Named CSM. Pilot is supported by ARCG ops directly.
- Carrier-level SLAs on outbound communications. The Phase B
  messaging layer is stub-only.
