# ChartNav — Phase 69 Controlled Demo Booking Checklist

> **What this is.** The operator checklist for moving a qualified
> outreach reply into a controlled fake-data demo. It begins after
> Phase 68 classifies a prospect as `interested-demo-requested` or
> a security-question route that still accepts the fake-data demo.
> It does not perform outreach, create prospects, approve real PHI,
> or start a pilot.

## 1. Use This Checklist When

Use Phase 69 only when all of these are true:

- The prospect exists in the Phase 67 tracker or full Phase 64
  outreach tracker.
- Phase 68 classified the most recent reply as
  `interested-demo-requested`, `interested-asks-security-questions`,
  or `referral-to-another-role` with the referred role identified.
- No Phase 64 § B disqualifier is active.
- The buyer accepts the fake-data demo boundary.
- A likely decision-maker or champion role is named.
- Phase 63C functional smoke is green before the demo is booked.

Do not use this checklist for no-response rows, not-now rows,
unsubscribe rows, unsafe-request rows, or prospects asking for real PHI
before security review.

## 2. Demo Qualification Gate

The buyer is qualified for a controlled fake-data demo only when every
row below is true.

| Gate | Required evidence | If not true |
|---|---|---|
| Reply category | Phase 68 category is `interested-demo-requested`, `interested-asks-security-questions`, or a valid referred role. | Keep in Phase 68 routing; do not schedule. |
| Decision path | Provider-owner, managing physician, practice manager, operations lead, or named clinical champion is known. | Ask one clarifying question; do not send calendar invite. |
| Demo boundary | Buyer accepts seeded fake-patient demo and no real PHI. | Stop and route to security-review explanation. |
| Fit | Ophthalmology, retina, glaucoma, or eye-care workflow fit is documented. | Close or pause; do not demo outside current scope. |
| Safety frame | Buyer accepts provider-reviewed workflow layer positioning. | Do not proceed if they require autonomous documentation, diagnosis, image interpretation, billing, orders, referrals, messages, device integration, or replacing the EHR. |
| Functional readiness | Phase 63C smoke returns `BUYER-DEMO FUNCTIONAL GO: YES`. | Do not book until fixed or rescheduled. |

## 3. Before Booking

Commercial owner completes:

- [ ] Verify tracker row has current `Practice name`, `Location`,
      `Decision-maker role`, `Source / referral`, `Outreach status`,
      and `Next step`.
- [ ] Confirm no real names, emails, phone numbers, scraped personal
      data, or PHI are being committed to the repo.
- [ ] Confirm Phase 68 classification and reason are in the tracker.
- [ ] Confirm Phase 64 buyer qualification has zero active
      disqualifiers.
- [ ] Confirm buyer has not asked for a production LLM, real-PHI use
      before approval, autonomous scribe, diagnosis, image
      interpretation, orders, coding, billing, messaging, referrals,
      device integration, or replacing the EHR.
- [ ] Run or confirm current Phase 63C smoke output.
- [ ] Choose demo operator and backup owner.
- [ ] Select two or three time options within the next 5 business days.

## 4. What To Send Before The Demo

Send only what matches the buyer's stage.

| Buyer state | Send | Do not send |
|---|---|---|
| Wants demo | Phase 69 scheduling email + calendar invite. | Security packet unless asked. |
| Asks what they will see | Phase 64 one-page buyer brief + demo agenda. | Product roadmap promises or pricing. |
| Asks security before demo | Phase 64 security-review packet index + Phase 65A crosswalk pointer. | BAA, legal docs, secrets, or real-PHI instructions. |
| Asks pricing before demo | Phase 64 paid-pilot positioning safe response; pricing is discovery-only. | Do not send price quote, discount, contract terms, or ROI guarantee. |
| Asks for real-PHI use | Real-PHI request routing note; security review must precede any real-PHI path. | Upload link, test patient request, or production date. |

## 5. What Not To Send

Do not send:

- real patient examples;
- screenshots from live clinical systems;
- patient names, MRNs, DOBs, images, recordings, or appointment data;
- internal tracker rows;
- private prospect notes;
- secrets, API keys, env files, or credentials;
- unreviewed product roadmap;
- price quote or contract unless separately approved;
- public customer references;
- third-party compliance certification claim;
- production LLM claim.

## 6. What Not To Claim

During booking, the operator must not claim:

- Do not say ChartNav is HIPAA-certified.
- Do not say ChartNav is a certified EHR.
- ChartNav replaces any EHR.
- ChartNav diagnoses.
- ChartNav autonomously documents or signs.
- ChartNav captures exam-room audio.
- ChartNav interprets fundus or OCT images.
- ChartNav places orders, sends referrals, messages patients, bills,
  or codes.
- ChartNav integrates with medical devices or provides remote patient
  monitoring.
- ChartNav has production LLM approval.
- Any practice has agreed to pilot unless a written agreement exists.

## 7. Security Questions During Booking

If the buyer asks security questions before confirming a demo:

1. Acknowledge the question.
2. Confirm the demo remains fake-data only.
3. Send `docs/commercial/phase-64-security-review-packet-index.md`.
4. Send `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
   if the question is detailed.
5. Set tracker `Next step` to either `security review packet sent` or
   `demo booking pending security read`.
6. Do not move toward real PHI until the Phase 65 go/no-go gate says
   the security-review path is ready.

If the buyer requires HIPAA certification, SOC 2, HITRUST, FDA
clearance, production LLM, autonomous clinical behavior, or real-PHI
use before security review, stop booking and reclassify per Phase 68.

## 8. Pricing Questions During Booking

Use the Phase 64 pricing posture:

> Pricing for early controlled pilots is still a discovery topic. We
> design it around the narrow scope of the pilot. Let me understand
> your workflow first and come back with a written hypothesis.

Allowed:

- say pricing is discovery-only;
- explain that pilot scope drives the later hypothesis;
- offer the fake-data demo as the next step.

Not allowed:

- quote a price;
- promise a discount;
- promise ROI;
- claim time savings;
- say a pilot is already agreed.

## 9. Real-PHI Requests During Booking

If the buyer asks to use real charts, upload real data, or test with
their patients:

1. Stop the demo-booking path.
2. Say the demo is fake-data only.
3. Route to the Phase 65 security-review path.
4. Record `real-PHI request before approval` in the private tracker.
5. Do not ask the buyer to send examples.
6. Do not create a workaround.

Safe response:

> The demo is fake-data only. Real-PHI use requires a completed
> security review, legal approval if applicable, and a controlled
> environment approval before any real patient data is used.

## 10. Handoff To Demo Operator

The commercial owner gives the demo operator a short internal handoff:

| Field | Required content |
|---|---|
| Tracker row ID | Private tracker reference only, not public. |
| Buyer role | Provider-owner, managing physician, practice manager, operations lead, IT, or security. |
| Specialty fit | Retina / glaucoma / comprehensive ophthalmology / multi-specialty eye-care. |
| Reply category | Phase 68 category. |
| Stated interest | One-sentence summary of what they want to see. |
| Safety concerns | Security, pricing, real-PHI, LLM, EHR, or none. |
| Demo status | Proposed, booked, confirmed, reschedule needed. |
| Required prep | Phase 63C smoke, Phase 61 Q&A, Phase 62 visit script, Phase 66 cheat sheet. |

Do not include private contact data, patient information, verbatim long
reply text, or confidential buyer details in a repo file.

## 11. Handoff After Demo

After the controlled fake-data demo:

- If buyer wants security review: route to
  `docs/pilot/phase-65-security-review-handoff-checklist.md`.
- If buyer wants pilot scope: route to
  `docs/commercial/phase-64-paid-pilot-positioning.md` and the
  Phase 65 go/no-go gate.
- If buyer is not a fit: close per Phase 68 `not-a-fit` handling.
- If buyer asks unsafe questions: close or pause; do not keep selling.

## 12. Stop Criteria

Stop the Phase 69 handoff if:

- Phase 63C smoke is not green.
- Buyer requests real PHI before security review.
- Buyer requires a capability ChartNav does not support.
- Buyer asks for public customer references that do not exist.
- Buyer requires production LLM.
- Buyer requires certification as a precondition.
- Buyer requires product behavior outside provider-reviewed workflow
  support.
- Operator cannot name the decision-maker role or demo operator.

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

- `docs/commercial/phase-68-first-manual-outreach-cycle-review.md`
- `docs/commercial/phase-68-reply-classification-template.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-demo-asset-index.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`
- `docs/pilot/phase-65-security-review-handoff-checklist.md`
