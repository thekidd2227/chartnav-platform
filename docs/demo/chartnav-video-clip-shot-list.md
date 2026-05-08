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

## Capture URL

Always capture against `http://127.0.0.1:5173/?demo=1`. The
`?demo=1` query enables Guided Demo Mode AND hides the dev API
URL chip — buyers never see `localhost:8000` on screen. The
identity chip reads **Identity Admin · Org 1** with the email
in the `title=` attribute (Phase 19).

## Tab map (Phase 19F layout — 9 tabs, no Billing)

The encounter detail is now a 9-tab clinical workspace. Two
tabs hold all the demo content:

| Tab | Surface | Used by clips |
|---|---|---|
| **Documentation / EMR/EHR** | Scribe · Patient summary · Pre-visit brief · Provider action queue | 1, 4, 5, 6 |
| **Imaging** | OD/OS retinal diagram | 2, 3 |

Capture the tab transition (1-second click + panel transition)
when moving between Documentation and Imaging — that's part of
the new product feel.

The other 7 tabs (Overview · Clinical · Labs / Orders Review ·
Calendar · Communications · Documents · Chat) appear in the
hero "navigation reveal" hover-pan but are NOT featured in the
per-clip workflow shots. Phase 19F notes:

- *Labs / Orders Review* — review-only (View / Mark reviewed /
  Add note). The tab does not surface Submit Order, Place Order,
  or Send Referral; ChartNav never places lab, imaging, or
  procedure orders.
- **Billing is intentionally absent.** ChartNav does not bill,
  code, submit claims, or handle insurance. Do not capture any
  Billing / CPT / Charges / Insurance / Claim / Payment surface
  — there isn't one. Chat (internal staff) replaces the prior
  review-only Billing tab as the buyer-visible surface.
- *Chat* — frontend-only internal staff thread; persists to
  localStorage on the operator's machine. Demo-local. No
  patient messaging.

---

## Clip plan

### Clip 1 · Scribe lifecycle

> Tab: **Documentation / EMR/EHR**

- **Length**: 30 – 45 seconds
- **Setup**: open `enc-row-1`, click the Documentation tab.
- **What's on screen**: the Scribe session panel inside the
  Documentation tab. The pasted source text, then *Process*,
  then *Mark reviewed*, then *Finalize*. End on the read-only
  finalized state with the status badge visible.
- **Voice-over beat**: "ChartNav drafts a structured note from the
  source text. The provider reviews and finalizes — never automatic.
  Finalized sessions are immutable."
- **Capture order**: tab click → paste → process → review → finalize.

### Clip 2 · Retinal proposal review

> Tab: **Imaging**

- **Length**: 30 – 45 seconds
- **Setup**: click the Imaging tab. The OD/OS retinal diagram
  panel mounts.
- **What's on screen**: the Eye diagram panel with the
  *Generate proposals from findings* action visible, then the
  proposal modal/list, then *Apply* on one OD or OS proposal.
- **Voice-over beat**: "Proposals are read-only suggestions.
  Anything that lands on the diagram is tagged source=ai_approved
  and stays auditable."
- **Capture order**: Imaging-tab click → paste findings → generate →
  modal → apply one → modal closes.

### Clip 3 · OD/OS diagram apply / save / sign

> Tab: **Imaging**

- **Length**: 20 – 30 seconds
- **Setup**: continues from Clip 2 — already on the Imaging tab.
- **What's on screen**: applied annotations on the OD/OS retinal
  diagram, then *Save*, then *Sign*. End on the signed read-only
  state with the signed-at timestamp.
- **Voice-over beat**: "Save the unsigned artifact. Sign when the
  drawing is right. Signed artifacts are immutable in place; edits
  create an explicit fork."
- **Capture order**: apply already done → save → sign → read-only.

### Clip 4 · Patient-friendly summary

> Tab: **Documentation / EMR/EHR**

- **Length**: 30 – 45 seconds
- **Setup**: click the Documentation tab.
- **What's on screen**: the Patient summary panel banner copy
  ("Patient summary draft — provider review required. Do not send
  to patient until finalized by the provider."), then *Create*, an
  edit, *Mark reviewed*, *Finalize*. End on the finalized read-only
  state.
- **Voice-over beat**: "Provider-facing summary. ChartNav does not
  send anything to a patient. Finalized summaries are immutable."
- **Capture order**: Documentation-tab click → banner copy on
  screen → create → small edit → review → finalize.

### Clip 5 · Pre-visit brief

> Tab: **Documentation / EMR/EHR**

- **Length**: 20 – 30 seconds
- **Setup**: continues from Clip 4 — already on Documentation tab.
- **What's on screen**: the Pre-visit brief panel. Click *Generate*.
  Show the source-counts tiles, the last-visit recap, and at least
  one data-gap entry.
- **Voice-over beat**: "Derived view of available chart records.
  The data gaps are explicit. Not a clinical decision."
- **Capture order**: panel opens → generate → counts visible → gaps
  visible.

### Clip 6 · Provider action queue

> Tab: **Documentation / EMR/EHR**

- **Length**: 30 – 45 seconds
- **Setup**: continues from Clip 5 — already on Documentation tab.
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
  appearing for ~10 – 15 seconds. Include the tab transitions
  between Documentation and Imaging — they read as "this is a
  real product, not a single screen." End on a screen card or
  full-workspace shot showing the 9-tab bar.
- **Voice-over beat**: the demo-script lead-in ("Five minutes,
  seven steps, every step provider-reviewed.") plus the safety-
  guardrail bullet list as on-screen text overlay (no claim of
  HIPAA / EHR / autonomous anything).
- **Capture order**: cut from clips 1 – 6.

### Clip 8 · Clinical Signal Filtering banner (optional, hero shot)

> Tab: **Clinical / Ophthalmology**

- **Length**: 10 – 15 seconds
- **Setup**: click the **Clinical / Ophthalmology** tab.
- **What's on screen**: the Clinical tab's collapsible groups
  (Cornea / Retina / Oculoplastics / Glaucoma) with the
  Phase 17B Clinical Signal Filtering banner visible. Slow
  camera pan over the banner.
- **Voice-over beat**: "Filters conversation. Captures findings.
  Builds the diagram."
- **Capture order**: Clinical-tab click → banner visible → pan.

### Clip 9 · 9-tab navigation reveal (optional, hero shot)

- **Length**: 5 – 8 seconds
- **What's on screen**: the encounter detail header with the
  patient pill (`Identity Admin · Org 1`) + a deliberate
  left-to-right hover across the 9 tabs (Overview, Clinical,
  Documentation, Imaging, Labs / Orders Review, Calendar,
  Communications, Documents, Chat). **No Billing tab** —
  ChartNav does not bill, code, submit claims, or handle
  insurance.
- **Voice-over beat**: none — this is a visual reveal for the
  master cut and the website hero.
- **Capture order**: hover-pan across the tab bar.

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
