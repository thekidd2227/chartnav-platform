# ChartNav — Phase 69 Demo Scheduling Email Templates

> **What this is.** Safe scheduling copy for prospects who passed the
> Phase 68 reply review and Phase 69 booking checklist. These templates
> schedule a controlled fake-data demo only. They do not perform bulk
> outreach, create prospect claims, quote pricing, approve real PHI, or
> start a pilot.

## 1. Template Rules

Before sending any template:

- Verify the prospect is qualified under
  `phase-69-controlled-demo-booking-checklist.md`.
- Use only one real reason from the existing conversation.
- Offer two or three concrete times.
- State the demo is fake-data only.
- Do not ask for patient examples.
- Do not include real patient data.
- Do not promise pricing, pilot approval, compliance certification,
  production LLM, replacing an EHR, diagnosis, image interpretation,
  orders, billing, coding, messaging, referrals, or device integration.

## 2. Demo Scheduling Email — Standard

Use when the buyer explicitly asked for the demo.

```text
Subject: ChartNav fake-data demo — scheduling

Hi <first name>,

Thanks for the reply. A controlled fake-data demo makes sense as the
next step.

The demo uses a seeded fake patient only. Please do not send patient
examples, screenshots, MRNs, images, recordings, or real clinical data
before or during the call.

In 15 minutes, we can walk through:

- Technician Workup & Vitals;
- Provider-Reviewed VisitDraft Assist from a clinician-provided fake
  transcript;
- Provider-Reviewed Fundus Drawing Assist from clinician-entered
  findings text;
- doctor review, attestation, and signed lock.

A few options:

- <date/time option 1>
- <date/time option 2>
- <date/time option 3>

If one works, I will send a calendar invite with the fake-data scope
and short agenda.

— <founder name>
```

## 3. Demo Scheduling Email — Security Question First

Use when the buyer is interested but asks security questions before
confirming a time.

```text
Subject: ChartNav demo + security-review path

Hi <first name>,

Good question. The demo itself is fake-data only. Real-PHI use is a
separate path that requires security review and explicit approval
before any real patient data is used.

For the demo, we can keep the scope simple: a 15-minute walkthrough of
the provider-reviewed ophthalmology workflow using seeded fake data.

I can also send the security-review packet index before the call so
your team can see how we handle the real-PHI gate.

Would either of these work for the fake-data demo?

- <date/time option 1>
- <date/time option 2>
- <date/time option 3>

— <founder name>
```

Attach or link only:

- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md` when
  the buyer asks detailed security questions

Do not attach legal agreements, secrets, env files, or real-PHI
materials.

## 4. Demo Scheduling Email — Pricing Question First

Use when the buyer asks about price before the demo.

```text
Subject: ChartNav demo first, then pilot scope

Hi <first name>,

Pricing for early controlled pilots is still a discovery topic. We
design it around the narrow scope of the pilot, not a list price.

The clean next step is a 15-minute fake-data demo so you can see the
current product truth before we discuss any pilot hypothesis.

The demo uses seeded fake data only. No real PHI.

Would one of these times work?

- <date/time option 1>
- <date/time option 2>
- <date/time option 3>

— <founder name>
```

Do not add a price, discount, ROI estimate, or time-savings promise.

## 5. Demo Scheduling Email — Referred Role

Use when Phase 68 classified a reply as `referral-to-another-role`
and the original prospect gave permission for the introduction.

```text
Subject: ChartNav fake-data demo — intro from <referrer role/name>

Hi <first name>,

<referrer name> suggested you may be the right person to look at
ChartNav's controlled fake-data demo.

ChartNav is a provider-reviewed ophthalmology workflow/documentation
support layer. The demo uses seeded fake data only and does not require
patient examples from your practice.

In 15 minutes, we can show structured technician intake,
provider-reviewed VisitDraft Assist, fundus drawing from
clinician-entered findings text, and doctor sign-off.

Would one of these work?

- <date/time option 1>
- <date/time option 2>
- <date/time option 3>

— <founder name>
```

Do not imply the referrer endorsed ChartNav or agreed to pilot unless
that is true in writing and approved for use.

## 6. Calendar Invite Body

Use after the buyer confirms a time.

```text
ChartNav controlled fake-data demo

Thanks for the time.

Scope:
- 15-minute controlled fake-data demo.
- Seeded fake patient only.
- No real PHI, patient examples, MRNs, recordings, images, or live
  clinical system screenshots.

Agenda:
1. Workspace orientation.
2. Technician Workup & Vitals.
3. Provider-Reviewed VisitDraft Assist from clinician-provided fake
   transcript.
4. Provider-Reviewed Fundus Drawing Assist from clinician-entered
   findings text.
5. Doctor review, attestation, and signed lock.
6. Questions and next-step routing.

Boundaries:
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace your EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, message patients,
  bill, or code.
- Real-PHI use requires security review and explicit approval before
  any real patient data is used.
```

## 7. Pre-Demo Packet

Send only what is needed.

Default packet:

- `docs/commercial/phase-64-one-page-buyer-brief.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`

If the buyer asked security questions:

- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`

If the buyer asked what happens after demo:

- `docs/commercial/phase-64-paid-pilot-positioning.md`

Do not send:

- actual tracker rows;
- real prospect notes;
- real patient examples;
- screenshots from production systems;
- legal drafts unless separately approved;
- pricing quote;
- roadmap promise;
- production LLM or vendor claim.

## 8. Reschedule Template

```text
Subject: Re: ChartNav fake-data demo

Hi <first name>,

No problem. We can reschedule and keep the same fake-data demo scope.

Here are a few alternate times:

- <date/time option 1>
- <date/time option 2>
- <date/time option 3>

Same boundary as before: no real PHI or patient examples are needed
for the demo.

— <founder name>
```

## 9. Stop / Decline Template

Use if the buyer asks for something outside current ChartNav truth.

```text
Hi <first name>,

Thanks for clarifying. ChartNav is not the right fit for that request
today.

The current scope is provider-reviewed ophthalmology workflow support
using a controlled fake-data demo and a security-review path before
any real-PHI use. We do not support the capability you described.

Appreciate the time.

— <founder name>
```

Use this instead of trying to keep the buyer in motion when a hard
disqualifier fires.

## Safety Note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not provide remote patient monitoring or medical device
  integration.

## Related Documents

- `docs/commercial/phase-69-controlled-demo-booking-checklist.md`
- `docs/commercial/phase-69-buyer-qualification-handoff-template.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-64-one-page-buyer-brief.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
