# ChartNav Video Clip Shot List

Plan for short video clips that capture the existing ChartNav
clinical workflow. **No video files are checked into this repo.**
This document is the editorial / shot-list only.

Pair with `chartnav-clinical-workflow-demo-script.md` for spoken
cues and `chartnav-demo-click-path.md` for exact clicks. Capture
each clip as a single take against the local stack with the seeded
demo data; reset between takes with `make reset-db`.

All shots use the existing fake demo data (`demo-eye-clinic` /
PT-1001 / Morgan Lee). No real PHI, ever.

---

## Editorial guardrails

Every clip must visibly include the provider-review safety copy on
the panel it covers. The point of the videos is to **show** the
contract, not just narrate it.

Voice-over must use the safe phrasing from the demo script:

- "ChartNav supports documentation and review workflows."
- "Every artifact requires explicit provider review."
- "ChartNav does not diagnose, order, bill, send referrals, or
  message patients automatically."

Never claim:

- HIPAA compliant / certified EHR / autonomous diagnosis
- guaranteed accuracy / automatic orders / submit referral
- billing automation / coding automation / send patient message
- replaces a doctor / external LLM certainty

If a clip accidentally captures unsafe wording on screen or in the
voice-over, re-record the clip — do not edit around it.

---

## Clip plan

### Clip 1 · Scribe lifecycle

- **Length**: 30 – 45 seconds
- **What's on screen**: the Scribe session panel. The pasted source
  text, then *Process*, then *Mark reviewed*, then *Finalize*. End
  on the read-only finalized state with the status badge visible.
- **Voice-over beat**: "ChartNav drafts a structured note from the
  source text. The provider reviews and finalizes — never automatic.
  Finalized sessions are immutable."
- **Capture order**: paste → process → review → finalize.

### Clip 2 · Retinal proposal review

- **Length**: 30 – 45 seconds
- **What's on screen**: the Eye diagram panel with the
  *Generate proposals from findings* action visible, then the
  proposal modal/list, then *Apply* on one OD or OS proposal.
- **Voice-over beat**: "Proposals are read-only suggestions.
  Anything that lands on the diagram is tagged source=ai_approved
  and stays auditable."
- **Capture order**: paste findings → generate → modal → apply one →
  modal closes.

### Clip 3 · OD/OS diagram apply / save / sign

- **Length**: 20 – 30 seconds
- **What's on screen**: applied annotations on the OD/OS retinal
  diagram, then *Save*, then *Sign*. End on the signed read-only
  state with the signed-at timestamp.
- **Voice-over beat**: "Save the unsigned artifact. Sign when the
  drawing is right. Signed artifacts are immutable in place; edits
  create an explicit fork."
- **Capture order**: apply already done → save → sign → read-only.

### Clip 4 · Patient-friendly summary

- **Length**: 30 – 45 seconds
- **What's on screen**: the Patient summary panel banner copy
  ("Patient summary draft — provider review required. Do not send
  to patient until finalized by the provider."), then *Create*, an
  edit, *Mark reviewed*, *Finalize*. End on the finalized read-only
  state.
- **Voice-over beat**: "Provider-facing summary. ChartNav does not
  send anything to a patient. Finalized summaries are immutable."
- **Capture order**: banner copy on screen → create → small edit →
  review → finalize.

### Clip 5 · Pre-visit brief

- **Length**: 20 – 30 seconds
- **What's on screen**: the Pre-visit brief panel. Click *Generate*.
  Show the source-counts tiles, the last-visit recap, and at least
  one data-gap entry.
- **Voice-over beat**: "Derived view of available chart records.
  The data gaps are explicit. Not a clinical decision."
- **Capture order**: panel opens → generate → counts visible → gaps
  visible.

### Clip 6 · Provider action queue

- **Length**: 30 – 45 seconds
- **What's on screen**: the Provider action queue panel banner copy
  ("Provider action suggestions — review required. ChartNav does
  not create orders, send referrals, message patients, or take
  action automatically."), then *Generate*, then Accept on one item,
  Dismiss on a second, Complete on the accepted one.
- **Voice-over beat**: "Suggested → accepted → completed; dismissed
  is terminal. Every transition is the provider's explicit click."
- **Capture order**: banner copy on screen → generate → accept →
  dismiss → complete.

### Clip 7 · Full workflow montage (master cut)

- **Length**: 60 – 90 seconds (assembled from clips 1 – 6)
- **What's on screen**: a chronological cut from scribe → propose →
  diagram → summary → brief → action queue, with each panel
  appearing for ~10 – 15 seconds. End on a screen card or full-
  workspace shot.
- **Voice-over beat**: the demo-script lead-in ("Five minutes,
  seven steps, every step provider-reviewed.") plus the safety-
  guardrail bullet list as on-screen text overlay (no claim of
  HIPAA / EHR / autonomous anything).
- **Capture order**: cut from clips 1 – 6.

---

## What not to film

- Any screen showing real patient data. The local stack uses fake
  seed data only; if a developer accidentally has real data
  loaded, do not capture clips against it.
- Any feature that does not exist (no order entry, no patient
  messaging, no referral submission, no billing screen). If it's
  not in the click path, it's not in the clips.
- Any UI that contains unsafe claims. If you see "HIPAA compliant"
  or "autonomous diagnosis" on screen, file an issue and stop the
  shoot.

---

## Where the clips live

**Not in this repo.** Video files (mp4 / mov / webm) and
screenshots (png / jpg) belong in a separate marketing or shared
storage location. This repo carries the editorial plan and the
in-app demo guide only.

If we ever check media into the repo, do it in a Phase that
explicitly justifies it — Phase 13 does not.
