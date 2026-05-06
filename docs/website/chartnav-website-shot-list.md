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

## Shot list

### Hero shots (for the landing page)

These match the Phase 16 landing page sections. Capture for
website use only — they are not in-product features.

- **Hero — workspace overview.** Wide screenshot of the
  workspace with `enc-row-1` (Morgan Lee) selected. Identity
  badge visible. Shows the Phase 13 collapsed demo guide and
  the Phase 5B / 8 / 9 / 10 / 11 panel stack at a glance.
- **Hero — safety banner.** Tight screenshot of the
  Phase 11 action queue banner copy: *"Provider action
  suggestions — review required. ChartNav does not create
  orders, send referrals, message patients, or take action
  automatically."*
- **Hero — guided demo mode.** Wide screenshot of the workspace
  with `?demo=1` enabled, showing the Phase 15 stepper at
  Step 1 of 8 with the *DEMO MODE · fake data only* badge.

### Workflow stage shots

One shot per stage in the seven-stage landing-page diagram.
These map directly to the inline SVG workflow on the website,
giving buyers a visual proof for each stage. Each shot is 30 –
45 seconds (clip) or one screenshot (still).

- **Stage 1 · Scribe lifecycle.** Paste source text →
  *Process* → *Mark reviewed* → *Finalize*. End on the read-only
  finalized state.
- **Stage 2 · Findings proposals.** From the Eye diagram panel,
  *Generate proposals from findings*. Show the modal/list.
- **Stage 3 · OD/OS diagram apply / save / sign.** Apply one
  proposal; *Save*; *Sign*. End on the signed read-only state.
- **Stage 4 · Patient summary.** Show the patient-summary
  banner copy (*"Do not send to patient until finalized by the
  provider."*) → *Create* → small edit → *Mark reviewed* →
  *Finalize*. End on the finalized read-only state.
- **Stage 5 · Pre-visit brief.** *Generate*. Show source-counts
  tiles, last-visit recap, and at least one data-gap entry.
- **Stage 6 · Provider action queue.** Show the queue banner
  copy → *Generate* → Accept on one item → Dismiss on a second →
  Complete on the accepted one.
- **Stage 7 · Guided demo mode.** *Next step* repeatedly through
  the 8-step Phase 15 stepper, ending on the close-out cue.
  Reset before the next take.

### Compositional shots

These are website-specific composition shots assembled from
the per-stage clips. They power the "Before / With ChartNav"
section and the "Built for pilot conversations" CTA.

- **Workflow montage.** 60–90 second master cut from Stages 1–7
  in order, with brief on-screen captions naming each stage.
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
