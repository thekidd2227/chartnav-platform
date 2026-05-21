# ChartNav — Phase 66 Founder-Led Outreach Templates

> **What this is.** Founder-voice variants of the outreach
> templates Phase 64 ships in operator voice. Use these when
> ChartNav's founder is the one writing the email or DM.
> Differences from Phase 64: personal context, single specific
> motivating problem, shorter, less templated. Same safe
> positioning — no hands-free claim, no AI-scribe claim, no
> diagnosis claim, no HIPAA-certification claim, no EHR
> replacement claim.

## 1. When to use founder-led vs operator-led

| Situation | Use |
|---|---|
| Outreach to a personal-network contact (residency colleague, conference connection, referred lead) | Founder-led (this doc) |
| Outreach to a Rank 1 retina practice owner-operator | Founder-led (this doc) |
| Cold outreach without a personal connection | Operator-led (`phase-64-outreach-email-v1.md`) |
| Follow-up after no reply to cold | Operator-led (`phase-64-follow-up-email-v1.md`) |
| Post-demo follow-up that proposes a scoped pilot | **Founder-led (this doc § 4 below — genuinely new in Phase 66)** |
| LinkedIn DM to an owner-operator | Founder-led (this doc § 5 below) |
| Calendar invite copy for the controlled demo | **Founder-led (this doc § 3 below — genuinely new in Phase 66)** |

## 2. Founder-led outreach email v1

Subject line (pick one, keep short):

- "Quick note on your <retina / glaucoma / ophthalmology> documentation workflow"
- "ChartNav — provider-reviewed workflow layer (15-min demo?)"
- "From <referrer> — fake-data demo of an ophthalmology workflow tool"

Body (target ~150 words, under 200):

```
Hi <first name>,

I'm <founder first name>. I work on **ChartNav**, a provider-
reviewed workflow layer for <retina / ophthalmology> practices.

I'm reaching out because <specific reason: "we met at <event>",
"your talk on <topic> raised the same documentation problem I'm
trying to address", "<mutual contact> suggested you'd have a
useful read on this">.

What ChartNav does today, narrowly:

- structured technician intake (vitals, IOP, visual acuity);
- a provider-reviewed VisitDraft from a transcript the clinician
  types or pastes (it's not ambient capture and not an AI scribe);
- a provider-reviewed Fundus Drawing Assist from clinician-
  entered findings text (it's not image interpretation);
- doctor review, attestation, and signed lock on every artefact.

ChartNav is not an EHR and does not replace your EHR. It does
not diagnose. It is not HIPAA-certified — real-PHI use would
only follow a security review.

Would a 15-minute fake-data demo (seeded fake patient, no real
PHI) be useful?

— <founder name>
<founder role>
<founder contact>
```

**Operator notes (do not paste):**

- Replace `<specific reason>` with one true thing. Do not
  fabricate. If you don't have a reason, use
  `phase-64-outreach-email-v1.md` (operator-led, no personal
  hook required).
- Do not promise pilot pricing, customer references, time
  savings, ROI, or compliance certification.
- If the prospect is Rank 1 retina, lead with the Fundus Drawing
  Assist line. If Rank 2 glaucoma / comprehensive, lead with the
  technician intake line.

## 3. Demo invite copy (calendar invite, NEW in Phase 66)

When the prospect agrees to the demo, send a calendar invite
with this body. This isn't in Phase 64.

Calendar title:

```
ChartNav fake-data demo — <practice name> + <founder name>
```

Calendar body:

```
Thanks for the time. Quick details before the call:

What we'll cover (~15 min):

- Workspace orientation and the four narrow workflows.
- Technician Workup & Vitals on a seeded fake patient (Morgan
  Lee, PT-1001 — fake by construction).
- Provider-Reviewed VisitDraft Assist from a pasted fake
  transcript.
- Provider-Reviewed Fundus Drawing Assist from clinician-entered
  findings text.
- Doctor review, attestation, and signed lock.

What this demo is and is not:

- It is a controlled fake-data demo. No real PHI.
- ChartNav is not HIPAA-certified. ChartNav is designed to support HIPAA-aware data-handling practices and is not HIPAA-certified.
- ChartNav is not an EHR and does not replace your EHR. This is not an EHR demo.
- ChartNav does not capture exam-room audio. This is not an ambient-scribe demo.

What to bring:

- The questions in
  `phase-66-buyer-discovery-questions.md` § 1 (I'll send these
  before the call).
- An honest read on which of the four workflows would matter
  for your practice and which would not.

What I'll send afterwards:

- A one-page summary of what we discussed.
- The Phase 64 buyer brief
  (`phase-64-one-page-buyer-brief.md`).
- The Q&A bank
  (`phase-61-buyer-qa-safe-answers.md`).
- If interest is real, a draft pilot-scope hypothesis (not a
  quote — pricing is still a discovery topic).

— <founder name>
```

**Operator notes:**

- Do not paste the markdown file references into the calendar
  body literally. Replace with attached PDFs or in-thread links.
- Do not send the calendar invite before the prospect has
  confirmed availability.
- Do not over-promise post-demo deliverables. The four bullets
  in "What I'll send afterwards" are the maximum commitment.

## 4. Post-demo follow-up email (NEW in Phase 66)

Phase 64's follow-up email (`phase-64-follow-up-email-v1.md`)
handles the case where the prospect did not reply to the first
cold outreach. **Post-demo follow-up is different.** This
template is what you send within 24 hours of completing the
controlled fake-data demo if the prospect engaged.

Subject line:

```
Recap + next step — ChartNav fake-data demo
```

Body (target ~200 words):

```
Hi <first name>,

Thanks for the time today.

A short recap of what we walked through:

- The four narrow workflows you saw: Technician Workup &
  Vitals; Provider-Reviewed VisitDraft Assist; Provider-Reviewed
  Fundus Drawing Assist; Doctor Review / Signed Lock.
- The two specific points where you said it would matter for
  <practice name>: <fill in: e.g., "after-hours charting on
  follow-up days" and "technician intake variability between
  Monday and Friday">.
- The two points where you flagged it would not matter (or not
  yet): <fill in: e.g., "we already have a working intake
  template" or "we'd want EHR writeback before any pilot">.

Where I think the right next step is:

<Pick ONE option only:>

OPTION A — qualified for a pilot conversation.
Propose a 30 / 60 / 90-day controlled pilot hypothesis.
Limited to one or two providers and one location.
Fake-data demo first; real-PHI use only after security review.
No production LLM. No device integration. Manually-measured
success metrics from
`phase-64-pilot-success-metrics.md`.

OPTION B — qualified but blocked.
Name the specific blocker that fired
(`phase-64-buyer-qualification-checklist.md` § B). Offer to
revisit in 60 / 90 days if the blocker is likely to dissolve.

OPTION C — not the right fit today.
Honest decline. Offer the safety-frame docs in case it changes
later. Mark the outreach-tracker row `closed-no-fit`.

Attached:

- The one-page buyer brief
  (`phase-64-one-page-buyer-brief.md`).
- The 20-question Q&A bank
  (`phase-61-buyer-qa-safe-answers.md`).

If pilot looks right: I'll write up a one-page pilot-scope
hypothesis (still a hypothesis, not a quote — see
`phase-64-paid-pilot-positioning.md` for the framing) and send
it within 48 hours. If you'd rather sit with it, that's also a
fine answer.

— <founder name>
```

**Operator notes:**

- Pick exactly one of Option A / B / C. Do not paste all three
  in the actual email.
- The "two points where it would matter" and "two points where
  it would not" lines are not optional — fill in real specifics
  from the demo, or do not send the email.
- Do not promise a price point.
- Do not promise a deployment date.
- Do not name another practice that has signed a pilot — none
  has.

## 5. LinkedIn DM — founder-led variant

Phase 64's LinkedIn DM (`phase-64-linkedin-dm-script.md`) is in
operator voice. Founder-voice variant:

```
Hi <first name>, thanks for connecting.

I'm <founder first name>, working on ChartNav — a provider-
reviewed workflow layer for <retina / ophthalmology> practices.
Not an EHR; not an ambient scribe; not HIPAA-certified.

The narrow scope: structured technician intake, provider-
reviewed VisitDraft from a clinician-pasted transcript,
provider-reviewed Fundus Drawing Assist from clinician-entered
findings text, doctor review and signed lock.

15-min fake-data demo (seeded fake patient, no real PHI) —
worth a look?

— <founder name>
```

Same hard rules as Phase 64 LinkedIn DM:

- No links to real-practice references — none exist today.
- No promise of compliance certification or pricing.
- Two messages max per prospect across cycles. After that, mark
  `paused` in the outreach tracker.

## 6. Safety note

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
- `docs/commercial/phase-64-outreach-email-v1.md` (operator-led variant)
- `docs/commercial/phase-64-follow-up-email-v1.md` (no-reply follow-up; not post-demo)
- `docs/commercial/phase-64-linkedin-dm-script.md` (operator-led DM)
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
- `docs/commercial/phase-66-what-not-to-promise-cheat-sheet.md`
