# ChartNav — Phase 68 Reply Classification Template

> **What this is.** The canonical 9-category classification
> table the operator applies to each prospect's most-recent
> reply during the Phase 68 cycle review
> (`docs/commercial/phase-68-first-manual-outreach-cycle-review.md`).
> Exactly one category per prospect. The category drives the
> next-action decision and the Phase 64 outreach-status enum
> update.

## 0. Classification rules

- **Exactly one category per prospect** at the end of Cycle 1.
  If a conversation evolves across touches, classify based on
  the **most recent reply**, not the first.
- **Tag from the prospect's words**, not from inference about
  what the operator hopes they meant.
- **If unsure between two categories, default to the safer
  category** (e.g., between `interested-asks-pricing` and
  `not-a-fit`, choose `not-a-fit`; between
  `interested-asks-security-questions` and `unsafe-request`,
  choose `unsafe-request`).
- **Document the verbatim quote** that led to the
  classification in the Phase 67 tracker's `Notes` (with the
  caveat in Phase 68 § 12: do not externalise quotes).

## 1. The 9 categories

### 1.1 `interested-demo-requested`

**Definition:** Prospect explicitly asks for the controlled
fake-data demo, names a time window, or accepts the demo
invite outright.

**Phase 64 status enum:** `demo-scheduled` (once a time is on
the calendar) or `replied` (interim).

**Next action:** Send the demo-invite copy from
`docs/commercial/phase-66-founder-led-outreach-templates.md`
§ 3 within 2 business hours.

**Anti-signal to watch:** If the prospect asks for the demo
**on real PHI**, do not advance. Reclassify as `unsafe-request`
(§ 1.9).

### 1.2 `interested-asks-security-questions`

**Definition:** Prospect engages substantively and asks about
HIPAA posture, BAA, subprocessors, audit logging, hosting,
backup, incident response, or any security topic before
agreeing to a demo.

**Phase 64 status enum:** `security-review`.

**Next action:** Send the security-review packet index
(`docs/commercial/phase-64-security-review-packet-index.md`)
+ the Phase 65A crosswalk
(`docs/pilot/phase-65a-security-review-evidence-crosswalk.md` § 6).
Use the operator's "what to send first" decision tree in
Phase 65A § 8.

**Anti-signal to watch:** If a question demands HIPAA
certification (or SOC 2 / HITRUST / FDA) as a hard
precondition, that's a Phase 64 § B disqualifier →
reclassify as `not-a-fit` (§ 1.6).

### 1.3 `interested-asks-pricing`

**Definition:** Prospect engages and asks about price /
contract length / pilot cost **before** seeing the controlled
demo or before scoping pilot value.

**Phase 64 status enum:** `replied` (pricing posture =
`discovery-only`).

**Next action:** Use the verbatim safe response from
`docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
§ J emergency phrase 3: "Pricing is still a discovery topic
for early controlled pilots. Let me understand your workflow
first and come back with a written hypothesis."

Then offer the demo. If the prospect insists on a quote before
the demo, that's a Phase 64 § B "needs enterprise procurement
on day one" disqualifier → reclassify as `not-a-fit` (§ 1.6).

**Anti-signal to watch:** If the prospect demands a final
quote with no demo at all, reclassify per above.

### 1.4 `referral-to-another-role`

**Definition:** Prospect declines personally but names a
specific colleague (office manager, second provider, IT lead)
who would be the right next contact.

**Phase 64 status enum:** `replied` (original prospect closes;
new prospect row opens for the referred contact).

**Next action:**

1. Thank the original prospect briefly (one sentence).
2. Open a new Phase 67 tracker row for the referred contact.
   `Source / referral = "referral from <original prospect
   name>"` (internal only — never quote externally without
   permission).
3. If the original prospect offered to make the introduction
   themselves, wait for that introduction before reaching out.
4. Apply Phase 67 Day-0 outreach to the referred contact only
   after the original prospect confirms the introduction.

**Anti-signal to watch:** If the referral path is "send your
deck to my procurement team," that's a Phase 64 § B
disqualifier → close the original row as `not-a-fit` and do
not pursue the referral.

### 1.5 `not-now`

**Definition:** Prospect engages politely but says the timing
is wrong (mid-EHR-migration, mid-acquisition, year-end close,
mid-staffing-transition).

**Phase 64 status enum:** `paused`.

**Next action:**

1. Acknowledge briefly. **Do not push.**
2. Ask one specific question: "What would have to be true for
   the right time to be Q<X>?" — captured for future
   re-research.
3. Document the timing constraint in `Notes`.
4. Set a future-research reminder for the timing the prospect
   named (e.g., "re-research in Q3 after EHR migration
   complete").
5. Do **not** auto-reach out at the stated future date — go
   through fresh research (Phase 67 § 1) at that time, in case
   anything else has changed.

**Anti-signal to watch:** "Not now" repeated across multiple
cycles → treat as `not-a-fit` permanently.

### 1.6 `not-a-fit`

**Definition:** Prospect explicitly declines on positioning
grounds: wrong specialty, wrong size, wrong workflow,
already-uses-competing-product, or the prospect names a Phase
64 § B disqualifier.

**Phase 64 status enum:** `closed-no-fit`.

**Next action:**

1. Thank the prospect briefly in one sentence.
2. Document the specific decline reason in
   `Disqualification reason` (verbatim if they gave a clear
   reason; "declined — no reason given" otherwise).
3. **No re-engagement cadence.** Wait at least 90 days before
   re-researching; only re-engage if the disqualifier has
   visibly dissolved (e.g., they switched specialty focus).

**A clean "no" is a successful outcome.** It preserves trust
and time.

### 1.7 `no-response`

**Definition:** Prospect did not reply to the Day 0 message,
the Day 3 follow-up, **and** the Day 7 short bump (per Phase
67 § 1-3).

**Phase 64 status enum:** `paused`.

**Next action:**

1. Confirm the cadence was completed cleanly (3 touches max,
   no third follow-up after Day 7).
2. Mark `paused` with `Notes`: `"paused — no response after
   Phase 67 Day-0/Day-3/Day-7 cycle"`.
3. **Do not auto-add to a re-engagement cadence.** Wait at
   least 60 days; only re-engage if the prospect publishes a
   substantive new signal that the operator can reference
   genuinely.

### 1.8 `unsubscribe-or-do-not-contact`

**Definition:** Prospect explicitly asks not to be contacted
again, via any phrasing ("please remove me", "do not contact
again", "unsubscribe", "stop", "I'm not interested in this
kind of outreach").

**Phase 64 status enum:** `closed-no-fit` with `Disqualification
reason = "do-not-contact request"`.

**Next action:**

1. Reply with a one-sentence confirmation: "Understood — I'll
   remove you from outreach. Thank you for the read."
2. Mark `closed-no-fit`. Add `do-not-contact` flag in `Notes`.
3. **Permanent exclusion.** Do not re-research the prospect in
   any future cycle. Add their email + name to a
   do-not-contact list the operator maintains out-of-repo.
4. If the prospect made the request publicly (e.g., on
   LinkedIn), do not reply publicly — handle privately.

### 1.9 `unsafe-request`

**Definition:** Prospect asks for something that ChartNav
explicitly does not do, in a way that would require ChartNav to
make an unsafe claim or process data unsafely. Examples:

- "Send me real-patient PHI screenshots before the demo."
- "Can you autonomously sign notes during the pilot?"
- "We need it to interpret fundus / OCT images."
- "We'll start using it on real charts next Monday before any
  paperwork."
- "Confirm in writing that ChartNav is HIPAA-certified." (Never agree — ChartNav is not HIPAA-certified.)
- "Show me how the AI diagnoses our patients."
- "Activate the production LLM for our pilot day one."

**Phase 64 status enum:** `closed-no-fit` with
`Disqualification reason = "unsafe request — <specific demand>"`.

**Next action:**

1. Reply with the appropriate verbatim safe answer from
   `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`.
   Three emergency phrases in § J cover the most common cases.
2. Explicitly decline what the prospect asked for. **Do not
   try to satisfy the request by reframing.** Do not promise
   anything that would soften the decline.
3. Mark `closed-no-fit`.
4. **Trigger a Phase 68 § 11 stop-criterion check** — any
   `unsafe-request` classification in Cycle 1 pauses Cycle 2
   until the operator debriefs.
5. Document the verbatim ask in `Notes` (internal only — this
   informs positioning audits, not externalisation).

## 2. Classification cheat sheet (single-page operator view)

| Prospect's most-recent reply, in essence | Category | Phase 64 status |
|---|---|---|
| "Yes, let's do the demo." | `interested-demo-requested` | `demo-scheduled` |
| "I'm interested — what's your HIPAA posture?" | `interested-asks-security-questions` | `security-review` |
| "Sounds interesting — what does it cost?" | `interested-asks-pricing` | `replied` |
| "I'm not the right person — talk to <name>." | `referral-to-another-role` | `replied` (close old, open new) |
| "Bad timing — we're in the middle of <X>." | `not-now` | `paused` |
| "We're not the right fit because <reason>." | `not-a-fit` | `closed-no-fit` |
| (no reply after Day 0 / 3 / 7) | `no-response` | `paused` |
| "Remove me / unsubscribe / do not contact." | `unsubscribe-or-do-not-contact` | `closed-no-fit` |
| "Send real-PHI demo / autonomously sign / interpret fundus / confirm HIPAA-cert / etc." | `unsafe-request` | `closed-no-fit` (+ stop-criterion check) |

Pin this on the side pane during cycle review.

## 3. Documentation discipline

For every classification, the Phase 67 tracker's `Notes` cell
gets:

- `<YYYY-MM-DD HH:MM TZ> — CLASSIFIED — <category>`.
- A one-sentence summary of why (e.g., "asked for HIPAA
  certification before demo").
- The verbatim trigger quote, **only if** the quote is short
  and contains no confidential content from the prospect's
  side.

What never goes in `Notes`:

- The prospect's private business details inferred from the
  reply (financial info, staffing details, regulatory issues
  they hinted at).
- Speculation about why the prospect declined.
- Forbidden phrases from
  `docs/commercial/chartnav-approved-claims-language.md` §
  forbidden phrasing.
- Customer-traction claims of any kind.

## 4. Safety note

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
- `docs/commercial/phase-64-outreach-tracker-schema.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
- `docs/commercial/phase-67-outreach-execution-log.md`
- `docs/commercial/phase-68-first-manual-outreach-cycle-review.md`
- `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
