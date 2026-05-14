# Phase 24D — Pilot Discovery Call Script

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** founder / sales engineer running the first
> 30-minute discovery call with a candidate ophthalmology practice.
> **Companion docs:**
> `phase-24d-pilot-practice-selection-criteria.md` — who to target.
> `phase-24d-demo-invite-and-agenda.md` — what to schedule next.
> `phase-24d-pilot-fit-scorecard.md` — score after the call.
> `phase-24d-pilot-objection-cheat-sheet.md` — buyer-safe answers.

This script is the source of truth for the **first** call. Read it
end-to-end before you dial. Keep the rhythm: open, qualify, pain-
score, transition to demo, close.

Total runtime budget: 30 minutes. Leave 5 minutes at the end for
next-step scheduling.

---

## 1. Opening — 60 seconds

You are not here to sell a generic AI scribe. Say so out loud.

> "Thanks for the time. I'm not here to sell you another generic
> scribe. What I want to do is understand where your clinic lane
> cycle is leaking time — front desk, technician workup, imaging
> metadata review, MD, reviewer, internal follow-up — and figure
> out if a fake-data demo of ChartNav makes sense for [Practice
> Name]. No real PHI. No autonomous diagnosis. No automatic
> orders or billing. Sound good?"

Pause. Let them confirm. Their answer tells you whether they
self-identify as in pain or in tire-kicking mode.

Common variants you'll hear:

- "Yes — we have real coordination problems." → keep going.
- "We use [scribe X] already." → "Got it. ChartNav isn't a scribe.
  Can I ask what works and what doesn't with [scribe X]?"
- "We just need cheaper dictation." → Politely re-position: "I'll
  be honest — that's not where ChartNav is strongest. Want to
  hear two minutes on what it does cover, and then you tell me if
  it's worth keeping going?"

---

## 2. Qualification questions — 10 minutes

Ask conversationally. Take notes against the
`phase-24d-pilot-tracker-template.md` columns. Do not interview —
loop back to the previous answer before asking the next question.

1. **Provider count + specialty split.** "How many providers, and
   how do they split across retina, glaucoma, cataract, and
   general ophthalmology?"
2. **Retina volume.** "What's the rough retina visit volume per
   week? Anti-VEGF injection days vs. follow-ups?"
3. **Locations.** "How many locations? Same EHR everywhere?"
4. **Technician workflow.** "Walk me through a typical retina
   follow-up. Who does workup, in what order, and where does the
   chart record live at each step?"
5. **Imaging workflow.** "Where does OCT macula / fundus photo
   metadata live today, and who sees it before the MD walks in?"
6. **Documentation lag.** "What's the typical gap between visit
   close and note finalize? How often does that exceed 24
   hours?"
7. **Review / sign-off bottleneck.** "Who reviews and signs the
   day's notes — the same provider, a reviewer, both?"
8. **Follow-up tasking.** "After a retina visit closes, how does
   the practice confirm the next-visit window? Who owns the
   task, and how often does it slip?"
9. **Internal handoff.** "How does the technician hand the
   patient off to the MD — verbally, EHR, paper, something
   else?"
10. **Current EHR.** "What's the current EHR? Any current AI
    documentation tool in use or recently evaluated?"
11. **Security review process.** "What's the practice's security
    review process for new software? Has the practice run it for
    any AI tool recently?"
12. **Pilot approver.** "Who in the practice approves a fake-data
    pilot? Who approves a real-PHI pilot if we got that far?"

Three guardrails:

- If the buyer cannot name **one** specific lane handoff that
  fails this week, the candidate is a nurture, not a priority
  pilot.
- If the buyer keeps redirecting to "but does it diagnose / pick
  IOL / auto-grade DR / submit claims," redirect once politely
  using §6 below. If they redirect again, end the qualification
  early and use the objection cheat sheet.
- If the buyer wants real PHI on day one, name the Phase 23
  real-PHI gate and ask whether a fake-data evaluation phase is
  workable first.

---

## 3. Pain scoring — 5 minutes

After the qualification block, score the practice live on a 1–5
scale in seven categories. Read each category back to the buyer
("On a 1-to-5, how painful is documentation lag for you today?")
and write the score next to your notes.

| # | Category | What you're scoring |
|---|---|---|
| 1 | Documentation lag | gap between visit close and finalized note |
| 2 | Imaging coordination | OCT / fundus metadata reaching MD on time |
| 3 | Technician handoff | tech → MD lane handoff friction |
| 4 | Follow-up tasking | next-visit window confirmation process |
| 5 | Internal communication | front desk / tech / MD / reviewer chat / handoff |
| 6 | Multi-provider visibility | shared queue and role-based dashboards |
| 7 | Security readiness | ability to run a controlled-pilot security review |

Use the pain scores when you score the candidate against
`phase-24d-pilot-fit-scorecard.md` after the call. Do not invent
scores — if you didn't get a real answer in a category, write
"unknown" and re-ask in the next conversation.

---

## 4. Transition to demo — 90 seconds

If the pain scores point to a fit (any two categories ≥ 3, no
red flags from §6 below), transition to the demo offer.

> "Based on what you described, the cleanest way to show the
> concept is the **Morgan Lee fake-data retina workflow**. It's a
> 30-minute walkthrough — one synthetic patient, no real PHI,
> end-to-end from front-desk readiness through provider sign-off
> and internal follow-up tasking. You'll see exactly what
> ChartNav does and what it does not do. Want me to send three
> slots?"

If the pain scores point away from a fit, do not push. Move to
§5.

---

## 5. Close — 90 seconds

Pick the close that matches the call. Do not improvise a fifth
option.

### 5.1 Schedule demo

> "Great. I'll send a 30-minute invite for [Day, Time 1], [Day,
> Time 2], or [Day, Time 3]. Pick one and I'll set it. The invite
> will include the demo agenda and a one-line note that we'll be
> on fake data only."

Attach `phase-24d-demo-invite-and-agenda.md` as the body
template.

### 5.2 Send security packet

> "Before the demo, can I send your IT / compliance person the
> security review packet? It covers ChartNav's scope, the
> fake-data evaluation phase, and the Phase 23 real-PHI gate —
> the per-practice checklist that has to be satisfied before any
> real PHI is loaded."

Attach `chartnav-security-review-packet.md`. Use variant 7 in
`phase-24d-pilot-outreach-message-bank.md` for the email.

### 5.3 Not a fit

> "Honestly — based on what you described, I don't think ChartNav
> is the right fit for [Practice Name] right now. [Specific
> reason: 'autonomous diagnosis isn't on our roadmap', 'we don't
> do automatic billing', 'we need a fake-data evaluation phase
> before real PHI']. I'd rather be honest about that than push a
> tool that doesn't match where you are. If the picture changes,
> happy to reconnect."

Use variant 8 in
`phase-24d-pilot-outreach-message-bank.md` as the follow-up
email.

### 5.4 Follow-up later

> "Sounds like the timing isn't right today, but the pain
> ([specific pain]) is real. Can I reach out again in [60 / 90]
> days? I won't pitch you in the meantime — I'll just send one
> short update on the lane cycle work if it stays relevant."

Set a reminder in `phase-24d-pilot-tracker-template.md` (status =
"nurture", last_touch = today).

---

## 6. What not to say

These are the same lines from the safe-claims contract. Any one
of these on a discovery call is a SEV-2 incident — call the team,
debrief, and fix the script before the next call.

**Never say:**

- "ChartNav is HIPAA compliant" / "HIPAA certified."
- "ChartNav is a certified EHR" / "ChartNav replaces your EHR."
- "ChartNav diagnoses retina disease" / "ChartNav auto-grades
  DR" / "ChartNav interprets OCTs."
- "ChartNav recommends anti-VEGF dosing" / "ChartNav selects the
  IOL."
- "ChartNav places orders" / "sends referrals" / "messages
  patients" / "submits claims" / "automates coding or billing."
- "The chart fills itself" / "the note writes itself."
- "ChartNav is hands-free scribing." (As a primary claim. The
  product is a workflow layer.)
- A specific OCT / fundus camera vendor by name. Device
  integrations are roadmap, not current state.

**When the buyer pushes on a forbidden claim, redirect once:**

> "Honest answer — no. ChartNav doesn't do that and it's not on
> the roadmap. The product wedge is workflow coordination: lane
> cycle visibility, imaging metadata review, role-based
> dashboards, provider-reviewed documentation, internal
> follow-up tasking. If [the forbidden capability] is a day-one
> requirement, a different tool is the right answer."

If the buyer pushes a second time, end the qualification block
and use Variant 8 ("Not a fit") as the close.

---

## 7. Post-call admin (within 15 minutes of the call)

- Update `phase-24d-pilot-tracker-template.md` with: pain scores,
  status, next step, owner, last touch.
- Score the candidate on
  `phase-24d-pilot-fit-scorecard.md`. Save the score next to the
  tracker row.
- If you committed to send the security packet, send it before
  end of business.
- If you committed to a demo, send the invite using
  `phase-24d-demo-invite-and-agenda.md`.
- Log any new objection wording you heard in
  `phase-24d-pilot-objection-cheat-sheet.md` (append, do not
  overwrite) so the next call benefits.

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-outreach-message-bank.md`
- `phase-24d-demo-invite-and-agenda.md`
- `phase-24d-post-demo-follow-up-template.md`
- `phase-24d-pilot-fit-scorecard.md`
- `phase-24d-pilot-objection-cheat-sheet.md`
- `phase-24d-pilot-tracker-template.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-demo-to-pilot-transition-plan.md`
- `chartnav-security-review-packet.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
