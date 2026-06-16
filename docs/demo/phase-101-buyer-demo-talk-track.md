# Phase 101 — Buyer Demo Talk Track

**Status:** operator talk track
**Date:** 2026-06-15
**Audience:** ChartNav operator delivering a controlled buyer
demo against the fake-data stack on a Phase 101-captured SHA
**Branch:** `feature/phase-101-mcp-independent-buyer-demo-evidence-capture`

## Purpose

A scripted talk track the operator can rehearse and deliver
verbatim. Every line below has been audited against the Phase 93
forbidden-narration list. The track is paired with the Phase 100
controlled-pilot buyer demo script
(`docs/demo/phase-100-controlled-pilot-buyer-demo-script.md`),
which covers the click-path side. This document covers the
voice-over side.

This track exists because the operator cannot rely on MCP /
Kapture to surface live in-app text on a buyer call — the
narration is the operator's responsibility, and a tight script
makes that safer.

## Hard rules

- **No claims beyond the approved-claims surface.** Every line
  below is on the approved-claims list
  (`docs/commercial/chartnav-approved-claims-language.md`).
- **No real PHI.** Demo is fake-data only.
- **No production LLM.** No live vendor scripts.
- **Closing ask is fixed.** See Section 4. Do not improvise on
  the close — the ask is the entire point.

## 15-minute talk track

### Open (0:00 — 0:30)

> "What I'm about to show you is ChartNav running against
> synthetic seed data. There is no real patient information on
> this screen. Everything you see is a provider-reviewed
> ophthalmology workflow surface — ChartNav does not diagnose,
> does not interpret images, and does not submit anything to any
> external system."

### Patient + workspace (0:30 — 2:00)

> "Here's the encounter list. We'll open encounter #1 — a seeded
> patient, Morgan Lee, MRN PT-1001.
>
> Across the top, this is the Phase 91 workspace state ribbon —
> visit mode and active eye. Both are **provider-driven**.
> ChartNav never infers visit mode or eye from clinical data."

### Vitals workup (2:00 — 4:00)

> "Technicians capture structured vitals — IOPs, visual acuity.
> Provider reviews and signs.
>
> Every signing event lands in the audit trail with **metadata
> only** — no IOP value, no transcript, no clinical body text.
> That's the guarantee."

### Documentation (4:00 — 7:00)

> "The Documentation tab walks the clinician through Transcript →
> Extracted Facts → AI Draft → Final Note.
>
> ChartNav drafts. The clinician signs. Provider review is
> required at every stage. This is workflow support, not
> autonomous documentation."

### Imaging tab (7:00 — 9:00)

> "Fundus charting is provider-entered findings. ChartNav does
> not interpret the photograph.
>
> The imaging metadata panel shows modality, modality group,
> review state — no image bytes are stored or transmitted
> through ChartNav."

### Adaptive overview (9:00 — 11:30)

> "On the Overview tab, the Phase 86 adaptive workspace
> reorders panels by the encounter's subspecialty. Retina
> patients see the retina rail first. Glaucoma patients see the
> cockpit first. Cataract patients see the surgical workflow
> first.
>
> ChartNav never hides a panel. It only reorders. Lower-priority
> panels collapse but remain available."

### Advanced clinical intelligence (11:30 — 13:00)

> "Phase 92 — the advanced clinical intelligence layer. Four
> sections: retina progression, glaucoma longitudinal, cataract
> conversion, FHIR export readiness.
>
> Every section is a **metadata projection** of provider-entered
> structured data. ChartNav does not diagnose, does not
> interpret images, does not recommend treatment, does not
> submit.
>
> See the FHIR readiness chips: packet renderable, submission
> not submitted, transport none. That's enforced in the
> protocol layer, not just the UI."

### Packet export + close (13:00 — 15:00)

> "The retina visit packet exports as a metadata-only JSON
> document. Artifact hashes prove the packet was issued against
> this exact encounter state.
>
> A few things ChartNav is **not**: not a certified EHR, not a
> replacement for your EHR, not HIPAA-certified, not
> SOC 2-certified, not FDA-cleared. It supports HIPAA
> obligations contractually via BAA when a real-PHI pilot
> begins — but real PHI is gated separately and not approved by
> this build alone.
>
> [Closing ask — Section 4]"

## 30-minute talk track

Use the 15-minute track above, then continue:

### Disease staging + medication safety (15:00 — 18:00)

> "Disease staging records the provider's stage entry against
> known systems — AMD AREDS, DR ETDRS, glaucoma POAG. Phase 92's
> retina section then surfaces the staging history as a count,
> not a diagnosis.
>
> Medication safety counts active medications, refill gaps,
> active safety events. Counts only — ChartNav does not write
> prescriptions, does not recommend medication changes, does not
> contact the pharmacy."

### Cataract conversion funnel (18:00 — 21:00)

> "The cataract conversion funnel is metadata. Any record →
> planned date → biometry → consent → post-op day 1. Each step
> is a chip the provider sees, never a recommendation ChartNav
> makes.
>
> ChartNav does not schedule surgery, does not recommend IOL
> choices, does not auto-bill."

### Security boundaries + audit (21:00 — 25:00)

> "Behind the demo, every clinical write lands in a metadata-
> only audit log. The release evidence gate runs a sentinel-
> token regression test on every CI commit — it proves no
> clinical body text reaches the audit log's detail field.
>
> ChartNav is **not** HIPAA-certified, **not** a certified EHR,
> **does not** replace your EHR, **does not** process real PHI
> in this build. Those non-claims are enforced by the claim
> scanners and the runtime safety scanner on every release.
>
> Real PHI is a separate conversation. Eight blocks need to
> close: BAA, vendor, security review, hosting, access, backup,
> incident response, written practice approval. We walk that
> together when the time comes."

### Release evidence + pilot readiness (25:00 — 28:00)

> "On the release-engineering side, ChartNav ships one
> operator command — the Phase 100 controlled-pilot launch gate.
> It runs the backend tier 1 + 2 + 3 release tests, the frontend
> typecheck, the full vitest suite, five claim scanners,
> runtime safety, git diff, claim policy fixtures, and the
> Phase 93 doc inventory. One command, one dated artifact, one
> PASS/FAIL summary, one go/no-go recommendation.
>
> That's what the ARCG ops lead attaches to the launch
> GO/NO-GO form when we propose a pilot."

### Closing (28:00 — 30:00)

> "[Closing ask — Section 4]"

## What to say (approved-claims short list)

- "Provider-reviewed ophthalmology workflow support."
- "ChartNav drafts. The clinician signs."
- "Metadata-only export. Read-only. Does not submit."
- "Fake-data demo. No real PHI in this build."
- "Lives alongside your existing EHR. Not a replacement."
- "Every action is in the audit trail with metadata only."
- "Provider-driven, never inferred."

## What NOT to claim (forbidden-narration extract)

The full forbidden-narration list lives in
`docs/pilot/phase-93-pilot-dry-run-runbook.md` Section "Forbidden
narration". Memorize at least the headline items:

- "ChartNav diagnoses." — NEVER.
- "ChartNav interprets images." — NEVER.
- "ChartNav recommends treatment / surgery / IOL choice / medication
  changes." — NEVER.
- "ChartNav writes back to your EHR." — NEVER.
- "ChartNav replaces your EHR." — NEVER.
- "ChartNav is a certified EHR." — NEVER.
- "ChartNav submits claims / codes / bills." — NEVER.
- "ChartNav is HIPAA-certified / SOC 2-certified / FDA-cleared." —
  NEVER.
- "ChartNav messages patients automatically." — NEVER.
- "Auto-coded / auto-billed / auto-submitted / auto-scheduled." —
  NEVER.
- "Progression confirmed / disease worsening detected / IOL power
  recommended." — NEVER.

If a buyer asks one of those questions, refer them to
`docs/demo/phase-61-buyer-qa-safe-answers.md` for the safe answer
template and continue.

## Clinical safety boundary

> "ChartNav surfaces what the provider entered. It does not draw
> clinical conclusions, does not recommend a treatment path,
> does not interpret a fundus photo, does not classify
> progression, does not select an IOL, does not write a
> prescription. Every clinical decision remains with the
> provider; ChartNav supports the workflow around that decision."

## Real-PHI boundary

> "Today's demo is fake-data only. Real PHI requires a separate
> approval track: a signed BAA with ARCG Systems, an accepted
> security review, a production identity provider, a
> production-grade Postgres with backups, an audit log
> destination, a backup + DR rehearsal, an incident response
> runbook walkthrough, and the practice's written go-live
> approval. Until every one of those gates closes, ChartNav stays
> on fake data."

## Section 4 — Closing ask (verbatim)

> "Here's what I'd like to propose. **Approve a controlled
> fake-data pilot review** — that's a 30-day window where your
> clinical, security, and administrative owners walk the Phase
> 100 launch gate output, the Phase 93 dry-run runbook, and the
> Phase 92 advanced intelligence panel against your own workflow
> expectations. **Separately, in parallel, complete the
> real-PHI readiness approvals** with your security and legal
> teams — BAA, security review, hosting, access, logging,
> backup, incident response. When both tracks land, we book the
> real-PHI go-live date together."

This is the **only** closing ask. Do not soften it. Do not pivot
to a real-PHI start date in the same breath as the fake-data
pilot review. Two tracks, in parallel, both gated.
