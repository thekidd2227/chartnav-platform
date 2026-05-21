# ChartNav — Phase 69 Buyer Qualification Handoff Template

> **What this is.** A private handoff template from commercial owner
> to demo operator after Phase 68 identifies a buyer who may be ready
> for a controlled fake-data demo. This template is not a prospect
> list, sales claim, pilot agreement, or security approval.

## 1. Handoff Rule

Complete this handoff only after:

- Phase 68 classified the reply as `interested-demo-requested`,
  `interested-asks-security-questions`, or a valid
  `referral-to-another-role`.
- Phase 64 disqualifiers are clear or explicitly routed.
- The buyer accepts fake-data demo boundaries.
- No unsafe request is active.

Do not complete this handoff for no-response, do-not-contact,
not-a-fit, or unsafe-request rows.

## 2. Internal Handoff Summary

Keep this in the private tracker or approved internal notes location,
not in the repo if it contains practice-specific details.

| Field | Entry |
|---|---|
| Handoff date |  |
| Commercial owner |  |
| Demo operator |  |
| Tracker row reference |  |
| Phase 68 reply category |  |
| Current outreach status |  |
| Buyer role |  |
| Specialty / workflow fit |  |
| Decision-maker path |  |
| Demo qualification state | qualified / needs clarification / stop |
| Proposed demo window |  |
| Phase 63C smoke status | green / not run / blocked |
| Security question present? | yes / no |
| Pricing question present? | yes / no |
| Real-PHI request present? | yes / no |
| Stop criteria present? | yes / no |
| Next owner |  |
| Next action and date |  |

## 3. Qualification Checklist

| Question | Yes / No | Notes |
|---|---|---|
| Buyer accepts controlled fake-data demo only? |  |  |
| Buyer is in ophthalmology, retina, glaucoma, or related eye-care workflow? |  |  |
| Buyer has a named role with workflow influence? |  |  |
| Buyer understands ChartNav is provider-reviewed workflow support? |  |  |
| Buyer has not requested real PHI before security review? |  |  |
| Buyer has not requested autonomous documentation, diagnosis, image interpretation, orders, billing, coding, referrals, messages, device integration, or replacing the EHR? |  |  |
| Buyer has not required production LLM? |  |  |
| Phase 63C smoke is green or scheduled to be run before booking? |  |  |
| Demo operator is assigned? |  |  |

If any answer is `No`, do not book until the issue is resolved or the
prospect is reclassified.

## 4. Buyer Question Routing

| Buyer asks | Route to | Safe operator response |
|---|---|---|
| "Can we see the demo?" | Phase 69 booking checklist and scheduling templates. | "Yes, we can schedule a controlled fake-data demo." |
| "What will we see?" | Phase 64 buyer brief and demo asset index. | "The demo shows structured intake, provider-reviewed VisitDraft, fundus drawing from clinician-entered findings, and signed lock." |
| "Is this secure enough for PHI?" | Phase 64 security-review packet index and Phase 65A crosswalk. | "The demo is fake-data only. Real-PHI use requires security review and approval." |
| "What does it cost?" | Phase 64 paid pilot positioning. | "Pricing is a discovery topic for early controlled pilots." |
| "Can we use real charts?" | Phase 65 go/no-go gate. | "Not before security review and explicit approval." |
| "Does it replace our EHR?" | Phase 64 buyer qualification disqualifiers. | "ChartNav does not replace your EHR." |
| "Does it diagnose or interpret images?" | Phase 66 what-not-to-promise cheat sheet. | "ChartNav does not diagnose or interpret fundus or OCT images." |
| "Can it do orders, billing, coding, messages, referrals, or device integration?" | Phase 64 buyer qualification disqualifiers. | "Those are not in scope." |

## 5. Commercial Owner Responsibilities

Before handing off:

- [ ] Confirm the buyer's reply category.
- [ ] Confirm no stop criteria are active.
- [ ] Confirm demo interest is real, not inferred.
- [ ] Confirm the buyer knows the demo uses fake data only.
- [ ] Confirm the likely buyer role and specialty fit.
- [ ] Summarize the buyer's stated interest in one sentence.
- [ ] Identify any security, pricing, or real-PHI questions.
- [ ] Assign the demo operator.
- [ ] Choose whether to send scheduling templates or ask one
      clarifying question first.

## 6. Demo Operator Responsibilities

Before accepting the handoff:

- [ ] Review the Phase 68 reply classification.
- [ ] Review the buyer's stated interest.
- [ ] Open the Phase 61 buyer Q&A.
- [ ] Open the Phase 62 demo visit script.
- [ ] Open the Phase 66 what-not-to-promise cheat sheet.
- [ ] Run or confirm the Phase 63C smoke result.
- [ ] Confirm no real PHI will be used.
- [ ] Confirm the demo will use only seeded fake data.
- [ ] Confirm no production LLM or vendor API call is required.

## 7. Handoff Outcomes

| Outcome | Meaning | Next action |
|---|---|---|
| `book-demo` | Buyer qualified and wants a fake-data demo. | Send scheduling email. |
| `ask-clarifying-question` | One missing item blocks booking. | Ask one narrow question. |
| `send-security-packet-first` | Buyer wants security posture before scheduling. | Send Phase 64 security index + Phase 65A crosswalk. |
| `route-pricing` | Buyer asks pricing before demo. | Use Phase 64 paid pilot positioning. |
| `pause-real-phi-request` | Buyer asks for real-PHI use before security review. | Pause booking and route to Phase 65. |
| `closed-no-fit` | A hard disqualifier fired. | Close per Phase 68. |

## 8. Notes Discipline

Notes may include:

- one-sentence summary of buyer's stated workflow interest;
- reply classification;
- date of next action;
- owner;
- safety-routing flag.

Notes must not include:

- patient information;
- long verbatim buyer replies;
- private staff details;
- scraped contact data;
- unsupported claims;
- secrets or credentials;
- legal documents;
- real-PHI examples.

## 9. Stop Criteria

Stop the handoff if:

- the buyer asks to use real patient data before security review;
- the buyer asks ChartNav to diagnose, interpret images, place orders,
  bill, code, refer, message patients, or act autonomously;
- the buyer asks for production LLM;
- do not continue if the buyer requires ChartNav to be a certified EHR
  or replace the buyer's EHR;
- the buyer requires compliance certification as a precondition;
- the demo operator cannot run a fake-data demo safely.

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
- `docs/commercial/phase-69-demo-scheduling-email-templates.md`
- `docs/commercial/phase-68-reply-classification-template.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/pilot/phase-65-security-review-handoff-checklist.md`
