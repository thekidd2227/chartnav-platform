# Demo Talk Track (Customer-Facing Narration)

**Audience:** ARCG operator delivering the controlled buyer demo
**Source of truth:** mirrors `docs/demo/phase-101-buyer-demo-talk-track.md`
**Posture:** Fake data only. No real PHI. No external send.

## Hard rules

- Every line below is on the approved-claims surface
  (`docs/commercial/chartnav-approved-claims-language.md`).
- The closing ask in Section 4 is fixed. Do not soften, pivot, or
  improvise. Two parallel tracks — fake-data pilot review and
  real-PHI readiness approvals — are the entire point.

## 15-minute talk track

### Open (0:00 – 0:30)

> "What I'm about to show you is ChartNav running against
> synthetic seed data. There is no real patient information on
> this screen. Everything you see is a provider-reviewed
> ophthalmology workflow surface — ChartNav does not diagnose,
> does not interpret images, and does not submit anything to any
> external system."

### Patient + workspace (0:30 – 2:00)

> "Here's the encounter list. We'll open encounter #1 — a seeded
> patient, Morgan Lee, MRN PT-1001.
>
> Across the top is the workspace state ribbon — visit mode and
> active eye. Both are provider-driven. ChartNav never infers
> visit mode or eye from clinical data."

### Vitals (2:00 – 4:00)

> "Technicians capture structured vitals — IOPs, visual acuity.
> The provider reviews and signs.
>
> Every signing event lands in the audit trail with metadata only
> — no IOP value, no transcript, no clinical body text. That's the
> guarantee."

### Documentation (4:00 – 7:00)

> "The Documentation tab walks the clinician through Transcript →
> Extracted Facts → AI Draft → Final Note.
>
> ChartNav drafts. The clinician signs. Provider review is
> required at every stage. This is workflow support, not
> autonomous documentation."

### Imaging (7:00 – 9:00)

> "Fundus charting is provider-entered findings. ChartNav does
> not interpret the photograph.
>
> The imaging metadata panel shows modality, modality group,
> review state — no image bytes are stored or transmitted
> through ChartNav."

### Adaptive overview (9:00 – 11:30)

> "On the Overview tab, the adaptive workspace reorders panels by
> the encounter's subspecialty. Retina patients see the retina
> rail first. Glaucoma patients see the cockpit first. Cataract
> patients see the surgical workflow first.
>
> ChartNav never hides a panel. It only reorders. Lower-priority
> panels collapse but remain available."

### Advanced clinical intelligence (11:30 – 13:00)

> "Phase 92 — the advanced clinical intelligence layer. Four
> sections: retina progression, glaucoma longitudinal, cataract
> conversion, FHIR export readiness.
>
> Every section is a metadata projection of provider-entered
> structured data. ChartNav does not diagnose, does not interpret
> images, does not recommend treatment, does not submit.
>
> Read aloud: 'Submission: not submitted. Transport: none.'
> That's enforced in the protocol layer, not just the UI."

### Packet export + close (13:00 – 15:00)

> "The retina visit packet exports as a metadata-only JSON
> document. Artifact hashes prove the packet was issued against
> this exact encounter state.
>
> A few things ChartNav is not: not a certified EHR, not a
> replacement for your EHR, not HIPAA-certified, not
> SOC 2-certified, not FDA-cleared. It supports HIPAA obligations
> contractually via BAA when a real-PHI pilot begins — but real
> PHI is gated separately and not approved by this build alone.
>
> [Closing ask — Section 4]"

## 30-minute walkthrough (additions)

Sections 15:00 – 30:00 are documented in
`docs/demo/phase-101-buyer-demo-talk-track.md`:

- Disease staging + medication safety deep-dive (15:00 – 18:00).
- Cataract conversion funnel (18:00 – 21:00).
- Security boundaries + audit (21:00 – 25:00).
- Release evidence + pilot readiness (25:00 – 28:00).
- Closing ask (28:00 – 30:00).

## What to say (approved-claims short list)

- "Provider-reviewed ophthalmology workflow support."
- "ChartNav drafts. The clinician signs."
- "Metadata-only export. Read-only. Does not submit."
- "Fake-data demo. No real PHI in this build."
- "Lives alongside your existing EHR. Not a replacement."
- "Every action is in the audit trail with metadata only."
- "Provider-driven, never inferred."

## Forbidden narration

Never say or write any of these:

- "ChartNav diagnoses."
- "ChartNav interprets images."
- "ChartNav recommends treatment / surgery / IOL choice /
  medication changes."
- "ChartNav writes back to your EHR."
- "ChartNav replaces your EHR."
- "ChartNav is a certified EHR."
- "ChartNav submits claims / codes / bills."
- "ChartNav is HIPAA-certified / SOC 2-certified / FDA-cleared."
- "ChartNav messages patients automatically."
- "Auto-coded / auto-billed / auto-submitted / auto-scheduled."
- "Progression confirmed / disease worsening detected / IOL power
  recommended / anti-VEGF recommended."

If a buyer asks one of those questions, refer them to
`docs/demo/phase-61-buyer-qa-safe-answers.md` and continue.

## Section 4 — Closing ask (verbatim)

> "Here's what I'd like to propose. **Approve a controlled
> fake-data pilot review** — that's a 30-day window where your
> clinical, security, and administrative owners walk the Phase
> 100 launch gate output, the dry-run runbook, and the Phase 92
> advanced intelligence panel against your own workflow
> expectations. **Separately, in parallel, complete the real-PHI
> readiness approvals** with your security and legal teams —
> BAA, security review, hosting, access, logging, backup,
> incident response. When both tracks land, we book the real-PHI
> go-live date together."

This is the **only** closing ask. Two tracks, in parallel, both
gated.
