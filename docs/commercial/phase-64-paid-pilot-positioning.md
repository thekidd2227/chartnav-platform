# ChartNav — Paid Pilot Positioning Memo (Phase 64)

> **Internal hypothesis memo for paid-pilot conversations.** All
> framing is draft / hypothetical. No final pricing claims. No
> customer-traction claims. No compliance certification claims.
> Use this as the basis for discovery conversations, not as a
> contract or quote.

## 1. Purpose

Define how the team talks about a **controlled paid pilot** when
a qualified buyer asks "what would the next step look like?"
after a fake-data demo. The memo is hypothesis-only until a
separate approved pricing memo and pilot agreement template
exist.

## 2. Pilot framing hypotheses

| Pilot length | What it covers | Real PHI? | Production LLM? |
|---|---|---|---|
| **30-day controlled pilot** | Fake-data demo + structured intake / VisitDraft / Fundus Drawing / signed lock on the practice's own seeded fake patients. Manual success metrics. | No. | No. |
| **60-day controlled pilot** | Same as 30-day plus optional limited-scope **real-PHI evaluation** after a completed security review and an executed BAA. Limited to one or two providers and one or two locations. | Only after security review and BAA. | No. |
| **90-day controlled pilot** | Same as 60-day plus a structured workflow-fit review and a manual outcomes write-up at end of pilot. | Only after security review and BAA. | No. |

All three lengths share these defaults:

- Fake-data demo first.
- Provider review and sign-off required on every artefact.
- No production LLM activation unless separately approved in a
  follow-on agreement.
- No device integration, no RPM, no patient messaging, no
  billing or coding, no orders, no referrals.
- No bidirectional EHR writeback unless separately scoped.
- Limited number of users / providers / locations.
- Manually measured success metrics (see
  `docs/commercial/phase-64-pilot-success-metrics.md`).

## 3. Pricing posture

**Pricing remains a discovery topic** for early controlled pilots.
The team does not have a published price point today and does not
quote one on first contact. If a buyer pushes for a number,
acknowledge it is a discovery topic:

> "Pricing for early controlled pilots is still a discovery topic
> — we are designing it around the narrow scope of the pilot, not
> a list price. Happy to come back with a written hypothesis
> after we understand your workflow."

Do not state revenue uplift as a fact. ChartNav offers no ROI guarantee.
Do not state time-savings guarantees as facts. Do not state customer
traction as a fact. Do not state clinical outcome improvements as
facts. Those claims are blocked by the commercial-claims scanner and
by the safety frame.

## 4. Objection handling (paste-able)

The canonical buyer Q&A bank is
`docs/demo/phase-61-buyer-qa-safe-answers.md`. The most common
objections that show up at the pilot-discussion stage are
re-anchored here.

| Objection | Safe response |
|---|---|
| "Why no HIPAA certification?" | "ChartNav is designed to support HIPAA-aware data-handling practices and is BAA-ready before any real-PHI use. It is not HIPAA-certified — certification is operational, not a vendor-conferred status. The security-review packet index lists what we can show before a BAA." |
| "Can we use real charts on day one?" | "Real-PHI use is conditional on a completed security review and an executed BAA. We start every pilot with the fake-data demo, then route real-PHI conversations through security review before any production data touches ChartNav." |
| "We want an ambient scribe." | "ChartNav is not an ambient scribe. The VisitDraft Assist works from a transcript a clinician types or pastes — we do not capture exam-room audio and we do not run a hands-free workflow. If a hands-free ambient scribe is the core requirement, we are not the right fit today." |
| "Does the AI write the note?" | "ChartNav drafts a structured note from clinician-provided input — the clinician reviews, edits if needed, attests, and signs. The signed artefact comes from the clinician's review, not from autonomous documentation." |
| "Does ChartNav interpret fundus or OCT images?" | "No. Fundus Drawing Assist works from clinician-entered findings text only. ChartNav does not interpret fundus photos or OCT images and does not auto-grade diabetic retinopathy." |
| "Can it replace our EHR?" | "ChartNav is not a certified EHR and does not replace your EHR. It is a workflow layer that runs alongside the EHR you already use." |
| "Who else is using it?" | "ChartNav is in pre-pilot today. We do not have public customer references. Happy to share the safety frame, the controlled demo, and this pilot positioning instead." |
| "What's the pilot price?" | "Pricing for early controlled pilots is still a discovery topic. We design it around the narrow scope of the pilot. Let me understand your workflow first and come back with a written hypothesis." |
| "Do you integrate with my EHR?" | "Not in the controlled pilot scope today. Bidirectional EHR writeback is a separate scoping conversation that would follow a successful pilot, not precede it." |
| "Do you have an LLM in production?" | "The controlled demo uses a deterministic stub. Real-LLM evaluation is roadmap, not commitment. The vendor evaluation paths (OpenAI / Anthropic / IBM watsonx) are exactly that — evaluation paths, never advertised as a shipped production capability." |

## 5. What a pilot conversation includes

If the buyer is qualified (per
`docs/commercial/phase-64-buyer-qualification-checklist.md`) and
wants to talk pilot, plan the conversation as:

1. **Recap demo state.** Confirm the buyer saw the controlled
   fake-data demo and the safety frame.
2. **Confirm scope boundaries.** Walk through § 2 above. Make
   sure the buyer signs off on "no real PHI until security
   review," "no production LLM," "no device integration," etc.
3. **Define one or two success metrics.** Pull from
   `docs/commercial/phase-64-pilot-success-metrics.md`.
4. **Define users / providers / locations.** Keep it small.
5. **Discuss pricing as a hypothesis.** Acknowledge it is not a
   final quote.
6. **Set the security-review entry point.** Point at
   `docs/commercial/phase-64-security-review-packet-index.md`.
7. **Agree on next step + owner.** Update the outreach tracker.

## 6. What a pilot conversation does NOT include

- No promise of HIPAA certification.
- No promise of FDA, SOC 2, or HITRUST certification.
- ChartNav does not promise autonomous documentation.
- ChartNav does not promise ambient scribing.
- ChartNav does not promise diagnosis.
- ChartNav does not promise image interpretation.
- ChartNav does not promise treatment recommendations.
- ChartNav does not promise device integration or RPM.
- ChartNav does not promise automatic orders.
- ChartNav does not promise automatic billing.
- ChartNav does not promise automatic coding.
- ChartNav does not promise patient messaging or referral automation.
- ChartNav is not a certified EHR and does not promise EHR replacement.
- No invented customer references.
- No invented ROI / time-savings / clinical outcome claim.
- No production LLM activation as a default — that is a separate
  conversation.

## Safety note

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
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/commercial/pilot/chartnav-pilot-handoff-checklist.md`
  (existing Phase 17 pilot handoff)
- `docs/commercial/phase-64-pilot-success-metrics.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
