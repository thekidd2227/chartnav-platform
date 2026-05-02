# ChartNav — retinal diagram video shot list

Six short clips (20–30 seconds each) for the website, sales deck,
demo follow-up emails, and social posts. Each clip is recordable
from the live app — no mockups, no stock footage.

## Production conventions (apply to every clip)

- **Source app:** the live ChartNav web app at `localhost:5173`
  with `make dev` running. Use the seeded `clin@chartnav.local`
  identity unless a clip explicitly requires a reviewer.
- **Capture window:** browser at 1280×720, OS chrome hidden
  (full-window recording, not full-screen). Cursor visible.
- **No PHI.** Use only the seeded patients (`PT-1001`, `PT-1002`,
  `PT-2001`). Never use a real patient name, DOB, or MRN.
- **No localhost / dev-only chrome.** Hide the dev identity
  picker by collapsing it before recording, or crop it out in
  post.
- **Pacing:** wait one beat between actions so the eye can
  follow. The clip is a teaser, not a tutorial.
- **No audio narration in the clip itself.** Suggested narration
  below is for the email / LinkedIn caption, the sales deck
  voice-over track, or accessibility-friendly captions.
- **Captions baked in** if the clip will be posted on LinkedIn
  or embedded autoplay-muted on the marketing site.
- **Output formats:** record to MP4 (H.264, 1080p, 30 fps).
  Export an additional WebM and a 6–10 second GIF preview for
  embeds that can't autoplay video.
- **Naming:** `clip-{n}-{kebab-name}.{mp4|webm|gif}`, all
  lowercase, no spaces.
- **Storage:** drop final masters into the existing
  `qa/screenshots/marketing/` directory or a sibling
  `qa/video/marketing/` directory if it exists in your branch.
  Do **not** commit raw multi-gigabyte source recordings to git;
  link them from your team's video drive.

---

## Clip 1 — Clinical Signal Filtering

- **Length:** 20–30 seconds.
- **Objective:** Show that ChartNav separates chatter, clinical
  text, and uncertainty from one block of dictation.
- **Scene setup:**
  - Patient chart open at `#/patients/1`, Eye Diagrams tab.
  - Click **+ New retinal diagram** and expand the **AI scribe
    (paste/dictate)** panel.
  - Textarea is empty.
- **On-screen action sequence:**
  1. Paste the sample dictation:
     > Okay hold on… OD drusen in the macula… maybe OS flame
     > hemorrhage inferior.
  2. Click **Generate proposals**.
  3. Open the **Triage details** disclosure.
  4. Hover over each track in turn so the highlight reads:
     ignored chatter, clinical text, uncertain phrase.
- **Suggested narration / caption:**
  > "ChartNav separates conversational chatter from clinical
  > findings, and surfaces uncertainty for the provider to
  > confirm. All in one pass."
- **Acceptance checklist:**
  - [ ] Triage details show all three tracks populated.
  - [ ] No identifiable patient information visible.
  - [ ] No proposal has been applied yet (none on the canvas).
  - [ ] No autoplay surprises (the clip is silent / muted).
- **File name:** `clip-1-clinical-signal-filtering.mp4`
- **Where to use it:**
  Website hero (Slot 1), sales deck "How it works" slide,
  LinkedIn announcement post, demo follow-up email subject
  *"How ChartNav separates clinical signal from chatter."*

## Clip 2 — AI Proposed Retinal Diagram

- **Length:** 20–30 seconds.
- **Objective:** Show that ChartNav proposes — but does not
  auto-apply — annotations on the OD / OS retinal canvases.
- **Scene setup:**
  - Continue from Clip 1's state (proposals already generated)
    OR re-run from the same sample if recorded standalone.
- **On-screen action sequence:**
  1. Scroll to the **Proposed annotations** list.
  2. Pause one beat on each list item so the viewer reads:
     OD drusen (severe, macula) and OS flame hemorrhage
     (uncertain, superior).
  3. Briefly hover over the **confidence summary** chips
     (`findings: 2  chatter: 1  uncertain: 1`).
  4. If `missing_flags` is present, point to the warning banner.
  5. End with the camera/cursor resting on the OD / OS canvases
     to make the contrast obvious: **proposals exist, canvases
     are still clean.**
- **Suggested narration / caption:**
  > "Proposals appear in a review panel — not on the diagram.
  > Nothing reaches the chart until the provider says so."
- **Acceptance checklist:**
  - [ ] OD/OS canvases remain blank during the entire clip.
  - [ ] Confidence summary chip values are visible.
  - [ ] Severity color hint visible on at least one proposal.
- **File name:** `clip-2-ai-proposed-retinal-diagram.mp4`
- **Where to use it:**
  Website hero (Slot 2), sales deck product page, LinkedIn
  carousel slide 2, demo follow-up email body image.

## Clip 3 — Provider Review and Apply

- **Length:** 20–30 seconds.
- **Objective:** Show the provider applying one proposal,
  rejecting another, and the canvas updating only for the
  applied one.
- **Scene setup:** Continue from Clip 2's state.
- **On-screen action sequence:**
  1. Click **Apply** on the OD drusen proposal.
  2. The OD canvas updates with the new label; the findings
     summary updates below.
  3. Click **Reject** on the OS flame hemorrhage proposal.
  4. The OS canvas remains clean; the rejected proposal is
     visibly grayed out and struck through in the panel.
  5. End with both canvases visible side by side: OD has the
     applied annotation, OS is unchanged.
- **Suggested narration / caption:**
  > "Apply puts the annotation on the canvas. Reject means it
  > never reaches the chart. Provider stays in control."
- **Acceptance checklist:**
  - [ ] Applied label clearly visible on OD.
  - [ ] OS canvas demonstrably empty after reject.
  - [ ] Status pills show *applied* and *rejected* in the
        proposal list.
  - [ ] Findings textarea has been updated for the applied
        finding only.
- **File name:** `clip-3-provider-review-and-save.mp4`
- **Where to use it:**
  Website hero (Slot 3), sales deck "Provider control" slide,
  LinkedIn carousel slide 3, compliance follow-up email
  attachment alt-text.

## Clip 4 — Manual Retinal Annotation

- **Length:** 20–30 seconds.
- **Objective:** Show that the diagram is not AI-only — manual
  annotation is fully supported.
- **Scene setup:**
  - Fresh / empty retinal diagram workspace.
  - AI scribe panel collapsed for this clip.
- **On-screen action sequence:**
  1. Choose the **text** tool from the toolbar.
  2. Click on the OD canvas; type a short label (e.g.
     `lattice`) in the prompt; press OK.
  3. Switch to the **pen** tool.
  4. Free-hand a small annotation on the OS canvas.
  5. Pause so viewer can see the **Findings (auto-summary)**
     line in the findings textarea reflect the manual labels
     after Save (or, for shorter clips, end before Save and
     rely on Clip 5 for the persistence story).
- **Suggested narration / caption:**
  > "Manual pen and labeled symbols are first-class. The AI
  > scribe is an assist, not a replacement."
- **Acceptance checklist:**
  - [ ] Manual label visible on OD; manual stroke visible on
        OS.
  - [ ] Toolbar visible long enough to read tool names.
  - [ ] No accidental scribe panel pop-up mid-clip.
- **File name:** `clip-4-manual-retinal-annotation.mp4`
- **Where to use it:**
  User guide page hero, training onboarding video, sales deck
  "What providers can do without AI" slide.

## Clip 5 — Save to Patient Chart

- **Length:** 20–30 seconds.
- **Objective:** Show persistence — saving an artifact, the
  list updating, and reload restoring annotations + findings.
- **Scene setup:** Continue from Clip 3 OR Clip 4. There must
  be at least one annotation visible before recording starts.
- **On-screen action sequence:**
  1. Click **Save diagram**.
  2. The "Last saved" timestamp updates; the *unsaved changes*
     marker disappears.
  3. Click **← Back to diagrams**.
  4. The list shows the new artifact row with the title and
     `v1` indicator.
  5. Click the artifact in the list; the canvas reloads with
     the same annotations and findings textarea content.
- **Suggested narration / caption:**
  > "Saved diagrams reload exactly. No drift, no re-running
  > the AI on the same record."
- **Acceptance checklist:**
  - [ ] List item visible after save.
  - [ ] Reload restores both canvas annotations and findings
        textarea content.
  - [ ] Version `v1` indicator visible.
- **File name:** `clip-5-save-to-patient-chart.mp4`
- **Where to use it:**
  Website "How it works" detail section, user guide,
  enterprise procurement attachment ("audit story" thread).

## Clip 6 — Sign and Version Protection

- **Length:** 20–30 seconds.
- **Objective:** Show that signing locks the diagram and that a
  post-sign edit creates a new version.
- **Scene setup:** Continue from Clip 5 (artifact saved, v1).
- **On-screen action sequence:**
  1. Click **Sign diagram**.
  2. The signed badge appears; the canvas / toolbar / scribe
     panel disappear (read-only state).
  3. Briefly show the disabled / locked appearance.
  4. (Optional, if recording a longer cut) Reopen the diagram
     in edit mode — explain via caption that the platform forks
     a new version on edit; the signed v1 row is preserved.
  5. End on the artifact list view showing the signed badge
     next to the diagram.
- **Suggested narration / caption:**
  > "Signed diagrams are immutable. Amendments fork into a new
  > version — the signed record is preserved exactly."
- **Acceptance checklist:**
  - [ ] Signed badge visible on the artifact in the list.
  - [ ] Toolbar / scribe panel hidden after signing (read-only).
  - [ ] Caption explicitly mentions versioning so viewers
        without sound still understand the protection model.
- **File name:** `clip-6-sign-and-version-protection.mp4`
- **Where to use it:**
  Compliance / enterprise sales follow-up emails, audit-story
  one-pager, government RFP response artifact, security review
  attachment.

---

## Master schedule (suggested)

| Day | Activity                                                                      |
| --- | ----------------------------------------------------------------------------- |
| 1   | Boot `make dev` once, capture all six clips back-to-back into raw masters.    |
| 1   | Scrub for any accidental PHI / dev chrome leaks.                              |
| 2   | Edit + add captions; export MP4 + WebM + GIF for each clip.                   |
| 2   | Hand the six MP4 files to marketing for the website video placeholder swap.  |
| 2   | Drop the GIF previews into LinkedIn / X drafts.                              |
| 3   | Send the demo follow-up email template (one-pager + Clip 1 + Clip 3).        |

## What NOT to record

- Live patient data of any kind.
- The dev identity picker dropdown (collapse it first).
- Localhost URL bar (crop or hide).
- The Admin panel.
- Anything that implies autonomous diagnosis, auto-charting, or
  certified-EHR claims. If a UI string drifts in that direction,
  pause the recording and route through clinical review.
