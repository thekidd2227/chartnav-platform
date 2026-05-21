# ChartNav — Phase 66 Buyer Discovery Questions

> **What this is.** A 15-question deeper discovery list,
> organized by workflow stage, for the founder-led first call
> with a qualified prospect. Builds on
> `docs/commercial/phase-64-call-opener.md` (which has 5
> top-level discovery questions to pick three from). This Phase
> 66 list is the full universe to draw from once a prospect
> engages past the initial outreach.

## 0. How to use this list

- Send the prospect a heads-up that 3-5 of these will come up on
  the call. Do not send all 15 — that turns the call into a
  survey instead of a conversation.
- Pick the questions that match the prospect's specialty tier
  (see `phase-66-prospect-targeting-brief.md` § 1). A retina
  practice gets different questions than a glaucoma practice.
- Listen for **own-the-workflow** signals (provider names a
  specific user, names a specific point in the day, names a
  specific dollar figure or hour count). Note them in the
  outreach tracker
  (`phase-64-outreach-tracker-schema.md`).
- If a question surfaces a Phase 64 § B disqualifier, pause
  politely and route per the call-opener's hard-stop table.

## 1. Discovery questions by workflow stage

### A. Intake (technician hand-off into chart)

1. **Who does intake today, what role, and what tools do they
   use?** Look for: named role (technician / scribe / midlevel),
   specific tool (paper, the EHR's intake template, an external
   form).
2. **When intake is incomplete or wrong, how does the provider
   find out — and at what point in the day?** Look for: clear
   handoff break; intake-redo rate; provider-visible vs
   provider-invisible problems.
3. **What's the minimum structured intake the provider needs
   before walking in the room?** Look for: a real list (VA, IOP,
   allergies, meds, chief complaint) vs "everything." If it's
   "everything," the prospect hasn't scoped intake yet.

### B. In-clinic charting (during the visit)

4. **When the provider needs to write a note during or after the
   visit, what tool is open and what's the typical sequence?**
   Look for: provider voice-types into the EHR; provider does
   freehand notes on paper; provider dictates to a scribe;
   provider writes in the EHR after-hours.
5. **For visits where fundus findings are discussed, how is the
   finding captured today?** Look for: dictation; freehand
   sketch; chart-template free-text field; specialty diagram
   tool. Retina-specific.
6. **How often does the provider miss laterality (OD / OS / OU)
   in the note that they had right in the room?** Look for: real
   number. If "never," the prospect is being polite.

### C. Sign / lock / handoff

7. **What's the typical gap between visit end and signed chart?**
   Look for: hour count or day count. After-hours charting
   signal.
8. **Who else looks at the note before sign?** Look for: scribe
   review, midlevel review, attending review. Maps to ChartNav's
   reviewer / clinician role split.
9. **What happens to a chart that doesn't get signed by EOD?**
   Look for: queue, escalation, after-hours catch-up, the next
   day. Provider review burden signal.

### D. After-hours and weekend work

10. **How many hours per week does the provider spend charting
    outside scheduled clinical time?** Look for: real number.
    If the answer is "none" or "I don't track," provider may be
    underreporting.
11. **What does the provider's most productive 30 minutes of
    charting look like — and what makes it productive?** Look
    for: specific routine, time of day, tool combination.

### E. Operations and support

12. **If a workflow broke for one provider for one day, who
    would notice and how would they raise it?** Look for: named
    point of contact, named channel (in-EHR ticket, IT helpdesk,
    practice manager). Maps to
    `docs/pilot/phase-65-issue-incident-triage-template.md`.
13. **What's the practice's hard limit on a pilot's scope —
    number of providers, locations, hours of staff time per
    week, weeks before reassessment?** Look for: real
    constraints. If "no limits," the prospect hasn't scoped a
    pilot mentally.

### F. Financial framing (last, never first)

14. **If a tool reliably reduced after-hours charting by 30
    minutes per provider per day, what would that be worth to
    the practice on the margin?** Look for: provider's own
    framing. Do not anchor with a number first. Do not promise
    that ChartNav delivers the 30 minutes.
15. **What would have to be true for the practice to start a
    paid pilot in 30 / 60 / 90 days?** Look for: named blockers
    (security review, IT capacity, fiscal year). Maps to
    `phase-65-controlled-pilot-go-no-go-gate.md`.

## 2. Specialty-tiered question selection

Use the priority ranking from
`phase-66-prospect-targeting-brief.md` § 1 to pick the right
five questions for a 15-minute slot.

| Practice tier | Pick these 5 from § 1 | Why |
|---|---|---|
| Rank 1 — Retina | Q1, Q4, Q5, Q7, Q15 | Workflow handoff + fundus capture + sign-lock cadence + pilot scoping. |
| Rank 2 — Glaucoma / general ophthalmology | Q1, Q2, Q3, Q9, Q15 | Intake completeness + sign cadence + pilot scoping. |
| Rank 3 — Multi-specialty eye-care | Q1, Q4, Q12, Q13, Q15 | Workflow handoff + operations + scope-discipline + pilot scoping. |
| Rank 4 — Subspecialty surgical | Q4, Q7, Q9, Q14, Q15 | Charting cadence + sign-lock + financial framing. Lower priority. |
| Rank 5 — Health-system | — | Not in scope for Phase 66 outreach. |

## 3. Questions that operators must NOT ask

These questions look discovery-like but trip the safety frame:

| Question to NOT ask | Why |
|---|---|
| "Would you want ChartNav to autonomously sign notes?" | Implies an auto-sign capability that does not and will not exist. |
| "What would you want our AI to diagnose first?" | Implies a diagnostic-AI capability. ChartNav does not diagnose. |
| "Which fundus / OCT images should we interpret first?" | ChartNav does not interpret images. |
| "Would you want to ingest real patient data during the demo?" | Implies real-PHI in the demo. Demo is fake-data only. |
| "Do you want orders / referrals / patient messages out of ChartNav?" | ChartNav does not place orders, send referrals, or message patients. Asking creates expectation. |
| "Are you HIPAA-compliant?" | Wrong direction — covered entities and BAs implement HIPAA; vendors do not "have" HIPAA compliance. Use `phase-66-buyer-discovery-questions.md` § 1 Q15 instead, framed around the practice's readiness for a controlled pilot. |
| "What's your budget for an AI scribe?" | Anchors on a category ChartNav is not in. ChartNav is not an AI scribe. |

If a prospect ASKS one of these questions of you, route per the
hard-stop table in
`docs/commercial/phase-64-call-opener.md` § "Hard-stop topics."

## 4. After the call

Within 4 business hours of the call:

1. Update the outreach tracker
   (`phase-64-outreach-tracker-schema.md`) with the prospect's
   discovery-question answers, fit score, any disqualifiers
   triggered, and the next action.
2. If the prospect is interested in a demo, send the calendar
   invite using
   `phase-66-founder-led-outreach-templates.md` § 3.
3. If the prospect declined, mark `closed-no-fit` and send a
   polite thank-you. Do not auto-add them to a re-engagement
   cadence without their explicit OK.

## 5. Safety note

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
- `docs/commercial/phase-64-call-opener.md` (5-question discovery used during the 60-second opener)
- `docs/commercial/phase-64-buyer-qualification-checklist.md` (qualifier + disqualifier universe)
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
