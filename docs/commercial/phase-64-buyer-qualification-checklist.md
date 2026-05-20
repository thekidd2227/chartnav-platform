# ChartNav — Buyer Qualification Checklist (Phase 64)

> **Use this before a controlled demo or pilot discussion to
> decide whether the buyer fits Phase 64's target profile.** A
> "yes" on most qualifying boxes plus zero disqualifiers means
> proceed. Any disqualifier checked → pause and route, do not
> proceed.

## A. Qualifying signals (target wins one box per row)

- [ ] **Practice type** — small to mid-size ophthalmology, retina,
      glaucoma, or multi-specialty eye-care practice.
- [ ] **Decision maker reachable** — provider-owner, managing
      physician, practice manager, or operations lead is in the
      conversation (or one introduction away).
- [ ] **Documentation burden visible** — provider voices the
      problem in their own words (intake redo, handoff friction,
      after-hours charting, repetitive structured fields).
- [ ] **Open to a controlled paid pilot** — buyer is willing to
      start with a 30 / 60 / 90-day controlled pilot rather than
      a full procurement.
- [ ] **Fake-data demo acceptable** — buyer is willing to look at
      the seeded fake-patient demo before any real-PHI
      discussion.
- [ ] **Limited scope acceptable** — buyer can evaluate with one
      or two providers and one or two locations.
- [ ] **Manual success metrics acceptable** — buyer is willing to
      define one or two narrow success metrics manually rather
      than expecting automatic ROI dashboards on day one.
- [ ] **Workflow-layer framing accepted** — buyer accepts ChartNav
      is a workflow layer alongside their EHR, not a system-of-
      record replacement.

## B. Disqualifiers (any one → pause and route, do not proceed)

> If any of these is true today, ChartNav is not the right fit
> for the controlled pilot framing Phase 64 supports. Decline
> politely. Do not invent capabilities to keep the conversation
> alive.

- [ ] **Needs certified EHR replacement.** ChartNav is not a
      certified EHR and does not replace the buyer's EHR.
- [ ] **Needs autonomous scribe / hands-free / exam-room audio
      capture.** ChartNav does not capture exam-room audio. The
      VisitDraft Assist works from a transcript the clinician
      types or pastes. If hands-free ambient scribing is the
      core need, decline.
- [ ] **Needs real-PHI launch immediately.** Real-PHI use is
      conditional on a security review and an executed BAA. If
      "we want to use this on real charts next Monday" is the
      ask, decline or route to security review first.
- [ ] **Needs deep EHR writeback before pilot.** Bidirectional
      EHR writeback is not in scope for the controlled pilot.
- [ ] **Needs enterprise procurement on day one.** Multi-site
      health-system procurement, full security-questionnaire
      compliance, and centralized IT sign-off are out of scope
      for Phase 64.
- [ ] **Needs production LLM right now.** The controlled demo
      uses a deterministic stub. Real-LLM evaluation is roadmap,
      not commitment.
- [ ] **Needs image interpretation.** ChartNav does not
      provide fundus image interpretation, does not provide OCT interpretation,
      and does not auto-grade diabetic retinopathy. The Fundus
      Drawing Assist works from clinician-entered findings text
      only.
- [ ] **Needs device integration or RPM.** ChartNav does not
      integrate with medical devices and does not provide remote
      patient monitoring today.
- [ ] **Needs HIPAA-certification documentation before any
      conversation.** ChartNav is designed to support HIPAA-aware
      data-handling practices but is not HIPAA-certified. If a
      certification document is a hard precondition, route to
      `docs/commercial/phase-64-security-review-packet-index.md`
      first.

## C. Fit-score guide (informal, 1–5)

- **5 / strong fit:** all 8 qualifying signals; 0 disqualifiers;
  owner-operator is the decision maker; willing to schedule a
  demo this week or next.
- **4 / good fit:** 6+ qualifying signals; 0 disqualifiers;
  decision maker is one introduction away.
- **3 / explore:** 4–5 qualifying signals; 0 disqualifiers;
  discovery still in progress.
- **2 / weak:** ≤ 3 qualifying signals **or** 1 minor
  disqualifier that may dissolve with discovery.
- **1 / not now:** 1+ hard disqualifier from § B that is
  unlikely to change in 90 days.

Use these scores in the outreach tracker's "Fit score" field. The
score is internal and informal; the gating decision is still on
the disqualifier list, not the score.

## D. Objection-handling pointers

When buyers push on positioning, use the safe answers in:

- `docs/demo/phase-61-buyer-qa-safe-answers.md` (20 canonical
  buyer questions with approved phrasing).

Common pushes that map directly to disqualifiers in § B should be
acknowledged honestly, not finessed.

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
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-outreach-tracker-schema.md`
