# ChartNav Website Shot List

Editorial plan for screenshot / video clips that capture the
existing ChartNav workflow against the local seeded fake-data
stack. **No video files or screenshots are checked into this
repo.**

This document is the editorial / shot-list only. Producing actual
media is out of scope for Phase 16. Capture work happens
out-of-repo.

Pair with:

- `docs/demo/chartnav-clinical-workflow-demo-script.md` — what to
  *say*.
- `docs/demo/chartnav-demo-click-path.md` — what to *click*.
- `docs/demo/chartnav-video-clip-shot-list.md` — the Phase 13
  shot list, which targets the in-product demo guide.
- `docs/chartnav-website-proof-upgrade-conversion-layer.md` —
  Phase 16 contract that this document supports.

---

## Editorial guardrails

Every captured shot must visibly include the safety contract on
its panel — the negative-assertion banner copy that ships with
each Phase 6 / 8 / 9 / 10 / 11 / 13 / 15 surface.

Voice-over and on-screen captions must use only the safe
phrasing list documented in
`chartnav-website-proof-upgrade-conversion-layer.md`. Forbidden
phrasing (HIPAA compliant, certified EHR, autonomous diagnosis,
automatic orders, submit referral, billing automation, send
patient message, replaces a doctor, external LLM certainty,
production-ready for PHI, real patient data ready) is not allowed
in any captured shot, in any caption, or in any voice-over.

If a captured shot accidentally includes unsafe phrasing on
screen — a tooltip, a caption, an OS notification — re-record
the shot. Do not edit around it.

The capture environment is the local seeded fake-data stack.
Real-PHI shots are explicitly forbidden:

- All seeded names, MRNs, DOBs, NPIs are fake by construction
  (`scripts_seed.py`).
- Reset between captures with `bash scripts/reset_demo_state.sh`
  (Phase 15).
- Do not capture against staging or controlled-pilot environments.

---

## Capture URL

Always capture against `http://127.0.0.1:5173/?demo=1`. The
`?demo=1` query enables Guided Demo Mode AND hides the dev API
URL chip, so buyers never see `localhost:8000` on screen. The
identity chip reads **Identity Admin · Org 1** with the email
in the chip's `title=` attribute (Phase 19).

## Tab map (Phase 19F layout — 9 tabs, no Billing)

The encounter detail is now a 9-tab clinical workspace. Two
tabs hold the demo content used by the website cuts; capture
the tab transition (1-second click + panel transition) when
moving between Documentation and Imaging — that's part of the
new product feel.

| Tab | What's inside | Used by stages |
|---|---|---|
| **Documentation / EMR/EHR** | Scribe · Patient summary · Pre-visit brief · Provider action queue | Stages 1, 4, 5, 6 |
| **Imaging** | OD/OS retinal diagram | Stages 2, 3 |
| **Clinical / Ophthalmology** | Phase 17B Clinical Signal Filtering banner + collapsible groups | Optional hero |

Other tabs (Overview, Labs / Orders Review, Calendar,
Communications, Documents, Chat) are not part of the
seven-stage website cut and should not appear in the per-stage
stills. They DO appear in the *9-tab navigation reveal* hero.

**Phase 19F notes:** *Labs / Orders Review* is review-only
(View / Mark reviewed / Add note). **Billing is intentionally
absent** — ChartNav does not bill, code, submit claims, or
handle insurance. The Chat tab covers internal staff comms
and is the buyer-visible replacement for the prior review-only
Billing surface. Communications covers internal staff
handoffs (no patient messaging). None of these tabs are
workflow capture targets — they exist to show platform
breadth in the navigation reveal.

---

## Shot list

### Hero shots (for the landing page)

These match the Phase 16 landing page sections. Capture for
website use only — they are not in-product features.

- **Hero — workspace overview.** Wide screenshot of the
  encounter detail with `enc-row-1` (Morgan Lee) selected.
  Identity chip reads **Identity Admin · Org 1**; the API URL
  chip is hidden by `?demo=1`. Show the sticky patient-encounter
  header and the 9-tab clinical workspace bar (Overview,
  Clinical, Documentation, Imaging, Labs / Orders Review,
  Calendar, Communications, Documents, Chat) — **no Billing
  tab**, ChartNav does not bill, code, submit claims, or
  handle insurance. Land on the **Documentation / EMR/EHR** tab
  so the scribe / summary / brief / action-queue panels are
  visible.
- **Hero — safety banner.** Tight screenshot of the
  Phase 11 action queue banner copy on the **Documentation /
  EMR/EHR** tab: *"Provider action suggestions — review required.
  ChartNav does not create orders, send referrals, message
  patients, or take action automatically."*
- **Hero — guided demo mode.** Wide screenshot of the workspace
  with `?demo=1` enabled, showing the Phase 15 stepper at
  Step 1 of 8 with the *DEMO MODE · fake data only* badge.
  The API URL chip is hidden; the identity chip reads
  **Identity Admin · Org 1**.
- **Hero — 9-tab navigation reveal.** 5–8 second clip of a
  deliberate left-to-right hover-pan across the 9-tab bar of
  the clinical workspace (Overview → Clinical → Documentation
  → Imaging → Labs / Orders Review → Calendar → Communications
  → Documents → Chat). No voice-over. Reads as "this is a
  real product, not a single screen." There is **no Billing
  tab** — ChartNav does not bill, code, submit claims, or
  handle insurance.
- **Hero — Clinical Signal Filtering banner.** 10–15 second
  clip on the **Clinical / Ophthalmology** tab. Slow camera
  pan over the Phase 17B Clinical Signal Filtering banner and
  the collapsible groups (Cornea / Retina / Oculoplastics /
  Glaucoma).

### Workflow stage shots

One shot per stage in the seven-stage landing-page diagram.
These map directly to the inline SVG workflow on the website,
giving buyers a visual proof for each stage. Each shot is 30 –
45 seconds (clip) or one screenshot (still).

Each stage shot starts with a 1-second click on its anchor tab
so the capture reads as "this lives inside a real workspace,"
not a single panel floating in the void.

- **Stage 1 · Scribe lifecycle.** *Tab: Documentation / EMR/EHR.*
  Click the Documentation tab → paste source text →
  *Process* → *Mark reviewed* → *Finalize*. End on the read-only
  finalized state.
- **Stage 2 · Findings proposals.** *Tab: Imaging.* Click the
  Imaging tab → from the Eye diagram panel, *Generate proposals
  from findings*. Show the modal/list.
- **Stage 3 · OD/OS diagram apply / save / sign.** *Tab: Imaging.*
  Continues from Stage 2 (already on Imaging tab). Apply one
  proposal; *Save*; *Sign*. End on the signed read-only state.
- **Stage 4 · Patient summary.** *Tab: Documentation / EMR/EHR.*
  Click the Documentation tab → show the patient-summary
  banner copy (*"Do not send to patient until finalized by the
  provider."*) → *Create* → small edit → *Mark reviewed* →
  *Finalize*. End on the finalized read-only state.
- **Stage 5 · Pre-visit brief.** *Tab: Documentation / EMR/EHR.*
  Continues from Stage 4 (already on Documentation tab).
  *Generate*. Show source-counts tiles, last-visit recap, and at
  least one data-gap entry.
- **Stage 6 · Provider action queue.** *Tab: Documentation /
  EMR/EHR.* Continues from Stage 5 (already on Documentation
  tab). Show the queue banner copy → *Generate* → Accept on one
  item → Dismiss on a second → Complete on the accepted one.
- **Stage 7 · Guided demo mode.** *Tab-agnostic — the stepper
  overlays the workspace.* *Next step* repeatedly through the
  8-step Phase 15 stepper, ending on the close-out cue. Reset
  before the next take.

### Compositional shots

These are website-specific composition shots assembled from
the per-stage clips. They power the "Before / With ChartNav"
section and the "Built for pilot conversations" CTA.

- **Workflow montage.** 60–90 second master cut from Stages 1–7
  in order, with brief on-screen captions naming each stage.
  Keep the Documentation ↔ Imaging tab transitions visible
  between stages — they read as "real product, multiple
  surfaces" rather than one panel cycling through states.
- **Before / With ChartNav split.** Side-by-side 30-second clip
  contrasting unstructured paper-style workflow on the left
  with the ChartNav workspace on the right. Captions only —
  no voice-over.
- **Pilot-readiness still.** A single still showing the docs
  tree under `docs/pilot/` open in a code editor or on the
  GitHub UI, captioned "Pilot-readiness package — eight docs."
  No voice-over.

---

## What not to capture

- Any screen showing real patient data. The local seeded
  environment is fake-data only by construction; if a developer
  happens to have real data loaded, do not capture against it.
- Any feature that does not exist (no order entry, no patient
  messaging, no referral submission, no billing screen, no LLM
  badge). If it is not visible in the current product, it
  cannot appear in a capture.
- Any UI that contains forbidden phrasing. If a tooltip or
  caption accidentally surfaces "HIPAA compliant" or
  "autonomous diagnosis" on screen, file an issue and stop the
  shoot until it is corrected.

---

## Where the captured media lives

**Not in this repo.** Image, video, and audio assets belong in
a separate marketing or shared-storage location. This repo
carries the editorial plan and the in-product demo / landing
surfaces only.

If a future phase explicitly justifies committing media (e.g.
a tiny SVG-only icon set), it must be addressed in that phase's
contract — Phase 16 does not commit media.

---

## Capture workflow checklist

For each capture session:

1. Run `bash scripts/reset_demo_state.sh` to reset the local
   stack to the seeded fake-data baseline.
2. Confirm the identity badge shows the expected seeded user.
3. Confirm the URL and any visible captions are free of
   forbidden phrasing.
4. Capture the shot.
5. Save the captured media to the out-of-repo storage location.
6. Log the captured shot ID against this shot list.
7. After the session, reset again so the next operator starts
   from a clean baseline.

If any step fails, abort the capture for that shot and re-run
the safety checks before retrying.

---

## Phase 21C — ophthalmology specialty surface additions

The Phase 21C positioning upgrade introduces the
ophthalmology-specific narrative on the homepage. The recommended
website media sections below extend the existing shot list. **No
media is captured by this PR.** Capture work happens out-of-repo
under the same safety contract as the earlier sections.

The companion narrative + section copy lives in
`docs/website/chartnav-ophthalmology-homepage-positioning.md`.

### Homepage hero shot

- **Subject:** the role-based dashboard (Phase 20C) for an admin
  identity, showing the **View as** selector mid-toggle between
  *Doctor* and *Reviewer*.
- **Fallback:** Encounter workspace Overview tab on `PT-1001
  Morgan Lee`.
- **Caption:** "Role-based clinic dashboards. Front desk to
  provider sign-off. Provider-reviewed at every step."
- **Forbidden:** no vendor names, no auto-routing language, no
  HIPAA-compliance text on screen.

### Eye-clinic lane cycle band

- **Subject:** horizontal step bar with the seven lane-cycle
  steps from the homepage doc Section 3 (front desk → tech
  workup → ancillary imaging review → MD encounter → review /
  sign-off → checkout / follow-up / internal coordination).
- **Source:** static graphic. May be assembled from individual
  dashboard captures (one per lane).
- **Caption:** "Built for eye-care lanes."
- **Forbidden:** do not imply auto-routing of work without
  provider review.

### Retina section

- **Shot 1:** Specialty Tracking panel → Retina section with a
  populated tracking card. Capture against `PT-1001` after
  seeding retina tracking via the demo click path.
- **Shot 2:** OD/OS retinal diagram canvas with two demo
  annotations (drusen + flame hemorrhage inferior).
- **Shot 3:** Imaging Pipeline panel filtered to an OCT macula
  + fundus photo study list.
- **Caption:** "Retina tracking foundation. Provider-reviewed
  annotations. Imaging metadata + review pipeline."
- **Forbidden:** no Cirrus / Spectralis / Triton / Optos device
  names. No "auto-grade DR" language.

### Glaucoma section

- **Shot 1:** Specialty Tracking panel → Glaucoma section with
  target IOP / latest IOP / cup-to-disc / RNFL / VF status
  values populated.
- **Shot 2:** IOP measurements table (Goldmann row + iCare row).
- **Shot 3:** Visual field tests table (24-2 + 10-2 rows with
  reliability + progression flag).
- **Caption:** "Provider-reviewed glaucoma tracking. No autofill.
  No autonomous diagnosis."
- **Forbidden:** no Humphrey / Octopus device names. No
  "auto-flag progression" language.

### Imaging section

- **Shot:** ImagingPipelinePanel split view — studies list on
  the left, selected study detail (file metadata + measurements
  + review workbench) on the right.
- **Caption:** "Imaging metadata + review pipeline. Generic
  modality labels. File metadata only — no image binaries. No
  device-vendor integration."
- **Forbidden:** no vendor names, no "auto-interpret" wording.
  Do not capture a shot where the storage URI on screen looks
  like a `data:` URI (the route rejects those — should never
  happen in fake-data demos, but worth noting).

### Documentation section

- **Shot:** NoteWorkspace stepper — Transcript → Extracted Facts
  → AI Draft → Final Note — with the provider-review badge
  clearly on screen.
- **Caption:** "Provider-reviewed documentation. The provider
  applies, edits, or rejects every proposal before anything is
  signed."
- **Source:** existing NoteWorkspace surface — no Phase 21C
  changes to this component.

### Internal coordination section

- **Shot:** Chat tab with the recipient selector open, targeting
  an internal staff identity.
- **Caption:** "Internal clinic coordination. Recipient
  selector. Conversation export. No patient-facing messaging."
- **Forbidden:** do not narrate this as "patient messaging" —
  it isn't.

### Safety section *(specialty-specific non-goals)*

A single static panel on the homepage rendering the
negative-assertion block from
`chartnav-ophthalmology-homepage-positioning.md` Section 5.
**No screen capture needed.** Inline text on the website only.

### Per-Phase-21C-clip safety checklist

For each capture from this addendum:

1. Reset the local stack (`bash scripts/reset_demo_state.sh`).
2. Switch to the identity required by the shot (default:
   `clin@chartnav.local` for tracking + imaging; `admin@chartnav.local`
   for the dashboard hero).
3. Confirm the URL and any visible captions are free of
   forbidden phrasing (Cirrus / Spectralis / Triton / Optos /
   IOLMaster / Humphrey / Topcon / HIPAA compliant / certified
   EHR / autonomous diagnosis / auto-interpret).
4. Capture.
5. Save to out-of-repo storage. **Do not commit any media
   binary in this PR.**
