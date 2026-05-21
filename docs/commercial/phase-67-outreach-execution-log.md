# ChartNav — Phase 67 Outreach Execution Log

> **What this is.** The concrete Day 0 / Day 3 / Day 7 / Day 14
> outreach sequence per prospect, with explicit logging steps
> the operator performs at each touch. Builds on the founder-led
> templates in
> `docs/commercial/phase-66-founder-led-outreach-templates.md`
> and the prospect list template in
> `docs/commercial/phase-67-first-pilot-prospect-list-template.md`.

## 0. Cadence at a glance

| Day | Action | Template / asset | Routing decision |
|---|---|---|---|
| **0** | Send founder-led email (or LinkedIn DM if email unknown). | `phase-66-founder-led-outreach-templates.md` § 2 (email) or § 5 (LinkedIn DM) | Mark `contacted`. Log timestamp + outbound asset. |
| **3** | Short follow-up (Phase 64 follow-up email v1) **only if no reply**. | `phase-64-follow-up-email-v1.md` | If reply received between Day 0 and Day 3, **skip Day 3** and route to "reply received" below. |
| **7** | Short bump (LinkedIn DM v2 or one-line email) **only if no reply after Day 3**. | `phase-66-founder-led-outreach-templates.md` § 5 (DM v2) | If still no reply, mark `paused` and stop. |
| **14** | No touch. The two-follow-up cap from Phase 64 is hard. | — | Move to next prospect. |

The cadence is **two touches max after the initial email**, then
pause. Phase 64 § "Outreach status" enum is the canonical status
vocabulary.

## 1. Day 0 — initial outreach

**Decision tree before sending:**

1. Is the prospect row complete per
   `phase-67-first-pilot-prospect-list-template.md` § 5?
   If not, stop. Do not send blind outreach.
2. Does any Phase 64 § B disqualifier apply from public
   research alone (e.g., the prospect's job title is
   "Director of EHR Implementation at <health-system>")?
   If yes, set `closed-no-fit` before sending. Do not send.
3. Is the prospect in `Rank 1` or `Rank 2`?
   If `Rank 3`, ensure a named clinical champion exists first
   (per `phase-66-prospect-targeting-brief.md` § 1).

**Send the appropriate template:**

| Source | Send |
|---|---|
| Personal-network or existing-relationship | Founder-led email (`phase-66-founder-led-outreach-templates.md` § 2) with the personal hook line filled in honestly. |
| Conference contact (within 90 days) | Founder-led email with "we met at <event>" line. |
| LinkedIn-search-only (no warm path) | LinkedIn DM v1 (`phase-66-founder-led-outreach-templates.md` § 5) instead of email. |
| Direct research (no warm path, no LinkedIn) | Skip. Do not cold-email without at least a LinkedIn connection. |

**Log immediately:**

- Update prospect-list row: `Outreach status = contacted`,
  `Last touch date = YYYY-MM-DD`,
  `Next step = Day-3 follow-up if no reply — <date+3 business days>`.
- Add to `Notes`: send timestamp + outbound asset name
  (e.g., `2026-05-27 09:14 EDT — phase-66 founder-led email v1`).
- Do **not** add any speculation about the prospect's likely
  response.

## 2. Day 3 — follow-up #1

**Decision tree:**

1. Did the prospect reply between Day 0 and Day 3?
   - **If yes → skip Day 3. Route to § 4 "Reply received."**
2. Has any auto-reply / bounce / OOO arrived?
   - **Bounce or hard-fail address →** mark `paused`, add to
     `Notes`: "Day-0 send bounced — <bounce reason>." Stop.
   - **OOO with return date →** delay Day-3 follow-up until the
     return date + 1 business day. Re-log `Next step`.

**Send the appropriate follow-up:**

| Day-0 asset sent | Day-3 asset |
|---|---|
| Founder-led email (§ 2) | Phase 64 follow-up email v1 (`phase-64-follow-up-email-v1.md`) |
| LinkedIn DM v1 (§ 5) | LinkedIn DM v2 (`phase-66-founder-led-outreach-templates.md` § 5 "DM v2") |

**Log immediately:**

- `Last touch date = today`.
- `Next step = Day-7 short bump if no reply — <date+4 business days>`.
- Note the follow-up timestamp + asset name.

## 3. Day 7 — short bump #2 (last touch in Cycle 1)

**Decision tree:**

1. Has the prospect replied since Day 3?
   - **If yes →** skip Day 7. Route to § 4 "Reply received."
2. Has the prospect viewed but not replied (LinkedIn read
   receipt, email-open signal)?
   - This is **not** a signal to send a third touch. Two
     follow-ups is the hard cap. Send Day 7 if no reply; pause
     after if still no reply.

**Send a single short message:**

- LinkedIn DM v2 (`phase-66-founder-led-outreach-templates.md` § 5 "DM v2") OR
- A one-sentence email: "Hi <first name> — circling back one
  more time. If a 15-minute fake-data demo isn't useful, no
  problem — appreciate the read. — <founder name>"

**Log immediately:**

- `Last touch date = today`.
- `Next step = Day-14 paused if no reply — <date+5 business days>`.

## 4. Reply received (any day)

A real reply changes the routing entirely. Three branches:

### 4.1 Reply: interested → demo

1. Reply within 2 business hours.
2. Send the demo-invite copy
   (`phase-66-founder-led-outreach-templates.md` § 3) with
   2-3 specific time slots in the next 5 business days.
3. Update prospect-list row: `Outreach status = demo-scheduled`,
   add `Demo date` if confirmed.
4. Pre-call: open
   `docs/commercial/phase-66-buyer-discovery-questions.md` and
   pre-pick 5 questions based on the prospect's specialty tier.
   Open `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
   in a side pane for the call.
5. Run the demo per the visit script
   (`docs/demo/phase-62-end-to-end-demo-visit-script.md`).
6. Within 24 hours of demo: send the post-demo follow-up email
   (`phase-66-founder-led-outreach-templates.md` § 4) with
   Option A / B / C picked honestly.

### 4.2 Reply: not interested → closed-no-fit

1. Reply with a short, polite thank-you. **Do not push back.**
   **Do not auto-add to a re-engagement cadence.**
2. Update prospect-list row: `Outreach status = closed-no-fit`,
   `Disqualification reason = "prospect declined"` (or the
   specific reason if they named one, e.g., "wants ambient
   scribe", "wants HIPAA cert as precondition").
3. If they named a specific Phase 64 § B disqualifier as the
   reason, note it verbatim in `Notes`. This is signal for
   future positioning, not a re-engagement trigger.

### 4.3 Reply: ambiguous / questions → keep in `replied`

1. Reply with one short, targeted clarifying question or one
   safety-frame document (typically
   `docs/commercial/phase-64-one-page-buyer-brief.md`).
2. Update prospect-list row: `Outreach status = replied`,
   `Next step = await clarification — follow up in <N> business days`.
3. If the prospect asks a hard question, use the canonical Q&A
   bank `docs/demo/phase-61-buyer-qa-safe-answers.md`. Use the
   three emergency phrases from
   `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md` § J
   if unsure.

## 5. Logging discipline (every touch)

For every outbound touch, the prospect's row gets:

- Updated `Last touch date`.
- Updated `Outreach status` if it changed.
- Updated `Next step` with a concrete date.
- Notes entry: `<YYYY-MM-DD HH:MM TZ> — <asset name> — <one-line summary>`.

For every inbound reply, the prospect's row gets:

- Updated `Outreach status`.
- Updated `Last touch date` (= reply date).
- Notes entry: `<YYYY-MM-DD HH:MM TZ> — REPLY — <one-line summary of intent>`.
- **No verbatim quoting of the reply** in `Notes` unless the
  reply is a single safe phrase. Keep replies confidential.

## 6. Cycle 1 close criteria

Cycle 1 completes when all 10 prospects on the list have either:

- `demo-scheduled` / `demo-completed` / `pilot-discussion` /
  `security-review`, or
- `paused` (after two follow-ups, no reply), or
- `closed-no-fit` (disqualifier fired or prospect declined).

When Cycle 1 closes:

1. Migrate any active rows (those still in `replied`,
   `demo-scheduled`, etc.) to the full Phase 64 outreach-tracker
   schema (`docs/commercial/phase-64-outreach-tracker-schema.md`).
2. Open the Phase 67 close-out review (see § 8).
3. Decide whether to start Cycle 2 with 10 new prospects.

## 7. What never goes in this log

- **Customer-traction claims.** ChartNav is pre-pilot today;
  the log reflects that.
- **Quotes attributed to a prospect that they did not actually
  say.**
- **PHI of any kind.** Prospect contact info is operator-facing
  only; no patient data ever.
- **Forbidden phrasing** from
  `docs/commercial/chartnav-approved-claims-language.md` §
  forbidden phrasing.
- **Compliance / certification claims** about ChartNav.
- **ROI / revenue uplift / time-savings guarantees** in `Notes`
  or in any outbound message.
- **A third follow-up after Day 7.** The two-follow-up cap is
  hard. After Day 7, the prospect goes to `paused`.

## 8. Cycle 1 close-out review (do this with the founder)

When the 10 prospects have all reached a terminal state:

| Question | Where to look | What to do with the answer |
|---|---|---|
| What was the reply rate? | Count of `replied` + `demo-scheduled` + `demo-completed` / 10. | If < 20%, review prospect-list quality (source mix, tier) before Cycle 2. |
| What was the demo conversion rate? | Count of `demo-completed` / count of `replied`. | If < 30%, review the demo narrative against `docs/demo/phase-62-end-to-end-demo-visit-script.md`. |
| Were any safety-frame triggers hit? | Search `Notes` for verbatim mentions of forbidden phrases. | Any hit → halt Cycle 2; debrief with the operator. |
| Did any prospect ask for a Phase 64 § B disqualifier as a precondition? | `Disqualification reason` column on `closed-no-fit` rows. | Note the pattern; do not adjust ChartNav's positioning to chase it. |
| What sources produced the best fit? | `Source / referral` column on `demo-completed` rows. | Lean Cycle 2 toward those sources. |

This review is the only place Cycle 1 results get summarized.
**Do not publish, share externally, or quote the close-out
review without explicit founder sign-off.**

## 9. Safety note

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
- `docs/commercial/phase-64-outreach-email-v1.md`
- `docs/commercial/phase-64-follow-up-email-v1.md`
- `docs/commercial/phase-64-linkedin-dm-script.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
- `docs/commercial/phase-67-first-pilot-prospect-list-template.md`
- `docs/commercial/phase-67-first-10-targets-research-guide.md`
