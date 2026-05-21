# ChartNav — Phase 68 First Manual Outreach Cycle Review

> **What this is.** The structured review workflow the operator
> runs **after** Cycle 1 manual outreach completes (per
> `docs/commercial/phase-67-outreach-execution-log.md`).
> Distinguishes "review the cycle" from "execute the cycle" so
> the operator does not edit positioning, claims, or
> safety-frame text in the middle of an active conversation
> stream.

## 1. Purpose

Phase 67 ships the **execution** layer (Day 0 / 3 / 7 sequence,
research workflow, prospect list template, logging discipline).
Phase 68 ships the **review** layer that runs once Cycle 1
reaches its terminal state (all 10 prospects in one of
`demo-scheduled` / `demo-completed` / `pilot-discussion` /
`security-review` / `paused` / `closed-no-fit`).

The review does three jobs:

1. **Classify each prospect's reply** against the canonical
   9-category table in
   `docs/commercial/phase-68-reply-classification-template.md`.
2. **Decide the next action per prospect** (advance to demo,
   route to security review, pause, close-no-fit, hand back to
   operator for one more touch).
3. **Aggregate cycle-level signals** about source quality,
   message resonance, and any safety-frame triggers — without
   inventing customer-traction claims.

## 2. When to use it

Run Phase 68 review **after** all 10 prospects in the Cycle 1
list have reached terminal state. Do **not** run Phase 68 in
the middle of Cycle 1 — partial reviews invite mid-cycle
positioning drift.

Terminal-state criterion (same as Phase 67 § 6):

- `demo-scheduled` / `demo-completed` / `pilot-discussion` /
  `security-review`, **or**
- `paused` (after two follow-ups, no reply), **or**
- `closed-no-fit` (disqualifier fired or prospect declined).

If any row is still in `not-contacted`, `contacted`, or
`replied` (awaiting next touch), Cycle 1 is not done — finish
the execution log first.

## 3. Inputs from the Phase 67 tracker

Open the Cycle 1 prospect list (per
`docs/commercial/phase-67-first-pilot-prospect-list-template.md`).
For each of the 10 rows you need:

- `Practice name`
- `Ideal target category` (Rank 1 / 2 / 3)
- `Source / referral`
- `Outreach status` (terminal)
- `Last touch date`
- `Notes` (the timestamped touch log)

Do **not** copy real names or contact details out of the
tracker into any externally-shareable doc. The review stays
internal.

## 4. Review cadence

- **First review:** within 5 business days of the last prospect
  reaching terminal state.
- **Reviewer:** the founder (or the named ChartNav commercial
  owner). No external reviewer in Phase 68.
- **Duration:** 60-minute time-box for 10 prospects. If the
  review runs long, the cycle was too sloppy — fix the
  execution discipline before the next cycle.
- **Cadence after first cycle:** one review per cycle. Do not
  run rolling weekly reviews; that turns into busywork.

## 5. Reply classification

For each prospect's most-recent reply (or `no-response` for
prospects that ended in `paused` after two follow-ups), tag the
reply with **exactly one** of the 9 categories defined in
`docs/commercial/phase-68-reply-classification-template.md`:

1. `interested-demo-requested`
2. `interested-asks-security-questions`
3. `interested-asks-pricing`
4. `referral-to-another-role` (office manager / physician / IT)
5. `not-now`
6. `not-a-fit`
7. `no-response`
8. `unsubscribe-or-do-not-contact`
9. `unsafe-request` (real-PHI before approval, autonomous-claim
   demand, HIPAA-cert-as-precondition, etc.)

The category drives the next-action decision in § 6-12.

## 6. Qualified / not-qualified rules

A prospect is **qualified** for the next phase (controlled demo
booking → security review) when **all four** hold:

- Reply classification is one of `interested-demo-requested`,
  `interested-asks-security-questions`, or `referral-to-another-role`
  (with the referred role now identified).
- Zero Phase 64 § B disqualifiers fired
  (`docs/commercial/phase-64-buyer-qualification-checklist.md`).
- Decision-maker role is named (provider-owner / managing-
  physician / practice-manager / operations-lead).
- No unsafe-request flag fired in any touch of the conversation.

If any of the four fails, the prospect is **not qualified** for
this cycle. Set status per § 7-12 and document the reason in
`Notes`.

## 7. Demo-booked handling

For prospects classified `interested-demo-requested`:

1. Verify the prospect meets all four § 6 qualifying conditions.
2. Send the demo-invite copy from
   `docs/commercial/phase-66-founder-led-outreach-templates.md`
   § 3 with 2-3 concrete time slots within the next 5 business
   days.
3. Update the Phase 67 tracker: `Outreach status =
   demo-scheduled`, fill `Demo date` when confirmed.
4. Migrate the row to the full Phase 64 outreach-tracker schema
   (`docs/commercial/phase-64-outreach-tracker-schema.md`) for
   the longer-cycle fields.
5. Hand off to **Phase 69 — Controlled Demo Booking and Buyer
   Qualification Handoff** when that workflow ships. In the
   interim, continue with Phase 66 / 67 templates plus the
   Phase 65 controlled-pilot go-no-go gate
   (`docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`).

## 8. No-response handling

For prospects classified `no-response` (`paused` after the two
follow-ups in Phase 67 § 1-3):

1. Confirm the Phase 67 cadence was completed cleanly (Day 0 +
   Day 3 + Day 7, no third touch).
2. Set status `paused`. **Do not auto-add to a re-engagement
   cadence.**
3. If the prospect later publishes a substantive new signal
   (talk, post, podcast appearance mentioning documentation
   burden), the operator may re-research the prospect from
   scratch in a future cycle. Wait at least 60 days.
4. Document the pause reason in `Notes`: `"paused — no response
   after Phase 67 Day-0/Day-3/Day-7 cycle"`.

## 9. Not-a-fit handling

For prospects classified `not-a-fit`:

1. Reply with a short, polite thank-you. Offer nothing further.
2. Set status `closed-no-fit`.
3. Document the specific Phase 64 § B disqualifier that fired
   (if the prospect named one) in `Disqualification reason`.
   If the prospect simply declined without naming a reason,
   note `"declined — no reason given"`.
4. Do **not** count `not-a-fit` as a negative outcome. A clean
   no is a successful Cycle 1 result — it preserves time and
   trust.

## 10. Security-review handoff trigger

For prospects classified `interested-asks-security-questions`:

1. Send the security-review packet index from
   `docs/commercial/phase-64-security-review-packet-index.md`
   plus the Phase 65A crosswalk from
   `docs/pilot/phase-65a-security-review-evidence-crosswalk.md` § 6
   ("Buyer-question crosswalk").
2. Set status `security-review`.
3. Use the operator's "what to send first" decision tree in
   `docs/pilot/phase-65a-security-review-evidence-crosswalk.md` § 8.
4. Apply the Phase 65 controlled-pilot go-no-go gate
   (`docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`)
   before any conversation that touches real-PHI scope.
5. If the security questions include a hard precondition (e.g.,
   HIPAA certification before any review), that's a Phase 64 § B
   disqualifier → reclassify as `not-a-fit` per § 9.

## 11. Stop / pause criteria for Cycle 1 → Cycle 2

After reviewing all 10 prospects, the operator decides whether
to start Cycle 2 (10 new prospects). **Stop or pause Cycle 2 if
any** of these hold:

| Stop / pause condition | Why |
|---|---|
| Any `unsafe-request` classification surfaced in Cycle 1. | Need to debrief and tighten positioning before re-engaging. |
| Reply rate < 20% across all 10 (count of `replied` + `demo-scheduled` + `demo-completed` ÷ 10). | List quality or message resonance was off; fix before scaling. |
| Phase 63C functional smoke is no longer green on the iMac stack. | Cannot run a controlled fake-data demo; outreach without a working demo wastes prospect time. |
| Any prospect surfaced a Phase 64 § B disqualifier the operator did not anticipate in Phase 67 research. | Tighten the research-stage screen before the next cycle. |
| Any safety-frame trigger in operator narration (forbidden phrase used, even verbally on a call). | Re-read `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md` and re-memorise the 3 emergency phrases before next cycle. |

If none of the stop conditions hold and the operator has time
+ capacity, Cycle 2 can begin per Phase 67 workflow with a new
list of 10.

## 12. What this review must NOT claim

- **No customer-traction claims.** ChartNav is pre-pilot today.
  Cycle 1 results are internal; do not externalise.
- **No quotes attributed to a prospect** unless the prospect
  themselves used the exact words in writing and has not asked
  for confidentiality.
- **No public summary** of Cycle 1 (blog post, LinkedIn post,
  pitch slide, press) without explicit founder sign-off.
- **No projection** of revenue / ROI / time-savings from a
  Cycle 1 reply rate. Cycle 1 is too small to project from.
- **No claim that any practice has agreed to pilot** based on
  Phase 68 review alone. Pilot agreement requires a signed
  written approval per
  `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md` Gate 3.
- ChartNav is not HIPAA-certified — never claim otherwise in any review artefact.
- ChartNav is not a certified EHR and does not replace any EHR — never claim otherwise.
- ChartNav does not provide autonomous diagnosis — never claim otherwise.
- ChartNav does not provide autonomous documentation — never claim otherwise.
- ChartNav does not place orders, send referrals, message patients, bill, or code — never claim otherwise.
- ChartNav does not interpret fundus or OCT images — never claim otherwise.
- The safety frame applies to internal review docs as much as to outbound email.

## 13. Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md` (full migration target)
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
- `docs/commercial/phase-67-first-pilot-prospect-list-template.md`
- `docs/commercial/phase-67-outreach-execution-log.md`
- `docs/commercial/phase-68-reply-classification-template.md`
- `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
