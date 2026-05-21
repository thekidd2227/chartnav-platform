# ChartNav — Phase 66 What-Not-To-Promise Cheat Sheet

> **One-page cheat sheet** the operator opens in a side pane
> during every prospect conversation. Consolidates the safety
> frame scattered across Phase 64 commercial docs and the
> Phase 65 pilot docs into a single page. Every line is a
> negation by design — the cheat sheet exists so the operator
> never has to improvise on the boundaries.

## A. Compliance

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav is HIPAA-compliant." | Covered entities and BAs implement HIPAA; vendors do not "have" HIPAA compliance. | "ChartNav is designed to support HIPAA-aware data-handling practices and is BAA-ready before any real-PHI use. It is not HIPAA-certified." |
| "ChartNav is HIPAA-certified." | No such certification exists for ChartNav. | Same as above. |
| "ChartNav is SOC 2-certified." | Not pursued. | "SOC 2 is not pursued at this stage." |
| "ChartNav is HITRUST-certified." | Not pursued. | "HITRUST is not pursued at this stage." |
| "ChartNav is FDA-cleared." | Not pursued. ChartNav is documentation support, not a clinical decision device. | "FDA clearance is not pursued; ChartNav is documentation support, not a clinical decision device." |
| "Our vendor (OpenAI / Anthropic / IBM) confers HIPAA compliance." | No vendor confers compliance. | "BAA-ready before real PHI; certification is operational, not vendor-conferred." |

## B. Capability — autonomous documentation

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav is an AI scribe." | Implies autonomous documentation. | "Provider-Reviewed VisitDraft Assist — fake transcript to provider-review draft." |
| "ChartNav does hands-free scribing." | Implies autonomous live capture. | Same as above. |
| "ChartNav listens to the exam room / captures ambient audio." | ChartNav does not capture audio. | "ChartNav drafts from a transcript the clinician types or pastes." |
| "ChartNav writes the note." | Implies autonomous documentation. | "ChartNav drafts a structured note from clinician-provided input; the clinician reviews, edits if needed, attests, and signs." |
| "Hands-free clinical documentation." | Same as above. | Same as above. |
| "ChartNav auto-signs notes." | No auto-sign path exists. | "Doctor review, attestation, and signed lock on every artefact. There is no auto-sign." |

## C. Capability — diagnosis / image interpretation

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav diagnoses X." | ChartNav does not diagnose. | "ChartNav surfaces missing-information prompts; provider diagnoses." |
| "ChartNav interprets fundus images." | ChartNav does not interpret images. | "Provider-Reviewed Fundus Drawing Assist — clinician-entered findings text to structured retinal diagram." |
| "ChartNav interprets OCT." | Same. | "ChartNav does not interpret OCT images." |
| "ChartNav auto-grades diabetic retinopathy." | ChartNav does not grade DR. | "ChartNav does not auto-grade DR or any other disease." |
| "ChartNav recommends treatment." | ChartNav does not recommend treatment. | "ChartNav does not produce treatment recommendations." |

## D. Capability — operations

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav places orders." | Out of scope. | "ChartNav does not place orders." |
| "ChartNav sends referrals." | Out of scope. | "ChartNav does not send referrals." |
| "ChartNav messages patients." | Out of scope. | "ChartNav does not message patients." |
| "ChartNav bills or codes." | Out of scope. | "ChartNav does not bill or code." |
| "ChartNav integrates with medical devices." | Out of scope. | "ChartNav does not integrate with medical devices." |
| "ChartNav does remote patient monitoring." | Out of scope. | "ChartNav does not provide remote patient monitoring." |

## E. Positioning

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav is a certified EHR." | ChartNav is not a certified EHR. | "ChartNav is not a certified EHR." |
| "ChartNav replaces your EHR." | ChartNav is not an EHR replacement. | "ChartNav is a provider-reviewed workflow layer that runs alongside your existing EHR." |
| "ChartNav integrates with <Epic / ModMed / RevolutionEHR / Eye Care Leaders>." | No production EHR integration is shipped. | "ChartNav runs alongside the EHR. Bidirectional writeback is a separate scoping conversation that would follow a successful pilot." |
| "ChartNav competes with Cora / <named competitor>." | ChartNav does not benchmark against named competitors. | "We focus on the four narrow workflows we do well today: structured intake, provider-reviewed VisitDraft, fundus drawing assist, doctor sign-off." |

## F. Production LLM + vendors

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav uses OpenAI / GPT / ChatGPT in production." | No production LLM is approved. | "The controlled demo uses a deterministic stub. Real-LLM evaluation is roadmap, not commitment." |
| "ChartNav uses Anthropic / Claude in production." | Same. | Same. |
| "ChartNav uses IBM watsonx in production." | Same. | Same. |
| "Our LLM is HIPAA-compliant." | Wrong framing. | "No production LLM is approved today. `CHARTNAV_LLM_ENABLED=0` in every demo + pilot default." |
| "OpenAI / Anthropic / IBM has signed a BAA for us." | Vendor BAA chain is per-deployment, not vendor-conferred. | "Vendor / subprocessor BAA execution is reviewed per deployment, not asserted vendor-wide." |

## G. Customer traction

| Do NOT say | Why | Safe answer |
|---|---|---|
| "<Practice name> uses ChartNav." | No public customers. | "ChartNav is in pre-pilot today. I do not have public customer references." |
| "We have <N> practices in pilot." | Pre-pilot. | Same. |
| "Our customers report <metric>." | No customers. | "Pilot success metrics framework is operational and manually-measured; we have no published metric claims yet." |
| "<Provider> endorses ChartNav." | No public endorsements. | Same. |

## H. Outcomes / business value

| Do NOT say | Why | Safe answer |
|---|---|---|
| "ChartNav saves <N> hours per provider per week." | Not measured at scale. | "Documentation turnaround time is one of the pilot success metrics; we measure it manually with the practice." |
| "ChartNav increases revenue by <N>%." | Out of scope. | "Pricing is a discovery topic; revenue effects are not in scope today." |
| "ChartNav guarantees ROI." | ROI guarantees are not in scope. | "ROI is not guaranteed. Pricing is a discovery topic for early controlled pilots." |
| "ChartNav improves clinical outcomes." | Documentation support is not a clinical outcomes intervention. | "ChartNav is documentation support. Clinical outcome claims are explicitly out of scope (see `phase-64-pilot-success-metrics.md` § 3)." |

## I. Pilot scope

| Do NOT say | Why | Safe answer |
|---|---|---|
| "We can start on real PHI next Monday." | Real-PHI use is gated by security review. | "Real-PHI use is conditional on a completed security review and an executed BAA. The first pilot starts on the fake-data demo." |
| "We'll set up the pilot in your production EHR by end of week." | Bidirectional EHR writeback is not in scope for the controlled pilot. | "Bidirectional EHR writeback is a separate scoping conversation that would follow a successful pilot." |
| "The pilot will roll out to all <N> providers in your practice." | Pilot is intentionally small. | "Initial pilot is limited to one or two providers and one location." |
| "Pricing is $<N> per provider per month." | No published pricing today. | "Pricing for early controlled pilots is still a discovery topic." |

## J. Emergency phrases

Three phrases the operator says verbatim when the prospect
pushes hard. Memorize them.

1. **"ChartNav is designed to support HIPAA-aware data-handling
   practices and is BAA-ready before any real-PHI use. It is
   not HIPAA-certified — certification is operational, not
   vendor-conferred."**
2. **"ChartNav drafts; the clinician reviews and signs. There
   is no auto-sign and no ambient capture."**
3. **"Pricing is still a discovery topic for early controlled
   pilots. Let me understand your workflow first and come back
   with a written hypothesis."**

If unsure what to say, say one of these three and route the
specific question to the canonical Q&A bank
(`docs/demo/phase-61-buyer-qa-safe-answers.md`).

## K. Safety note

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
- `docs/commercial/chartnav-approved-claims-language.md` (canonical claims-language reference)
- `docs/demo/phase-61-buyer-qa-safe-answers.md` (20-question buyer Q&A bank)
- `docs/commercial/phase-64-call-opener.md` § "Hard-stop topics"
- `docs/commercial/phase-66-prospect-targeting-brief.md`
- `docs/commercial/phase-66-founder-led-outreach-templates.md`
- `docs/commercial/phase-66-buyer-discovery-questions.md`
