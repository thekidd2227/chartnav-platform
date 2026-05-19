# Phase 19G — Website Video Clip Capture Instructions

> Six short MP4s queued for chartnavmd.com replacement after
> Jean-Max approves. **The live site is NOT updated in this
> phase** — clips land in
> `03_Website_Video_Clips/MP4/` for review and a copy of the
> approved set lands in
> `07_Ready_For_ChartNavMD_After_Approval/videos/`.

## Capture environment

| Setting | Value |
|---|---|
| URL | `http://localhost:5173/?demo=1` |
| Viewport | **1440 × 900** (or 1600 × 1000 if your screen accommodates) |
| Recorder | macOS Screenshot toolbar (Cmd-Shift-5 → "Record selected portion") or Loom in HD |
| Container | MP4, H.264, 30 fps. WEBM optional in `WEBM/`. |
| Filename prefix | `website_clip_NN_*.mp4` (NN matches list below) |
| Output folder | `03_Website_Video_Clips/MP4/` |

Hygiene before recording:

- Incognito / private window. No favicons, no extension chrome.
- **No browser address bar in frame** (or crop in post).
- **No terminal in frame.**
- **No localhost:8000 API URL chip** — `?demo=1` hides it; if
  you see it, reload with the query string.
- DevTools closed.
- Slack / Mail / iMessage notifications muted.
- Smooth cursor movement only — no frantic clicking.
- Pace: clip should feel deliberate, not hurried.

Forbidden vocabulary check (if any appears on screen during
capture, stop and file an issue):

- Billing / CPT / Charges / Insurance / Submit Claim / Auto-code /
  Auto-bill / Send Claim / Charge Patient / Bill Insurance /
  Payment / Claim
- Submit Order / Place Order / Send Referral
- Send to Patient / Patient Portal / External Message Delivery

---

## website_clip_01_clinical_workspace_overview

**Filename:** `website_clip_01_clinical_workspace_overview.mp4`
**Purpose:** Hero / homepage proof clip.
**Duration target:** 8–15 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace just loaded with `enc-row-1` (Morgan
Lee) selected. Overview tab is active.

**Click path:**
1. Hold for ~2 s on the loaded Overview.
2. Slow camera pan from the burgundy sidebar (top-left) →
   patient header → demographic strip → Overview cards →
   tab row.

**Stop screen:** still on Overview, tab bar fully visible.

**Show:**
- Burgundy sidebar.
- Patient header with red micro-accent stripe.
- Demographic strip with intentional empty-state copy.
- Tab row showing all 9 tabs (no Billing).
- Overview cards (Patient Snapshot · Visit Summary · etc.).

**Avoid:**
- Address bar in frame.
- API URL chip.
- Real names beyond the seeded "Morgan Lee" demo patient.

---

## website_clip_02_ophthalmology_workflow

**Filename:** `website_clip_02_ophthalmology_workflow.mp4`
**Purpose:** Clinical feature section.
**Duration target:** 8–15 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted, click **Clinical /
Ophthalmology** tab.

**Click path:**
1. Pause for 1–2 s on the Clinical Signal Filtering banner.
2. Hover the search input.
3. Slow scroll over the categories: Favorites → Retina →
   Cornea / Anterior Segment → Glaucoma → Oculoplastics /
   Lids / Adnexa → General Ophthalmology.

**Stop screen:** Clinical tab fully scrolled, banner visible.

**Show:**
- Phase 17B Clinical Signal Filtering banner.
- Search input.
- Collapsible category groups.

**Avoid:**
- Expanding all groups at once (frantic feel).
- Clicking through to other tabs (this is a Clinical-tab clip).

---

## website_clip_03_documentation_workflow

**Filename:** `website_clip_03_documentation_workflow.mp4`
**Purpose:** Documentation section.
**Duration target:** 8–15 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted, click **Documentation /
EMR/EHR** tab.

**Click path:**
1. Pause for 1–2 s on the workflow stepper / header
   (Transcript → Extracted Facts → AI Draft → Final Note).
2. Slow scroll through the NoteWorkspace tiers:
   transcript → findings (with confidence chips) → draft.
3. Briefly hover the "Provider review required" / "ChartNav
   does not finalize without provider sign-off" language.

**Stop screen:** the Final Note / signoff section.

**Show:**
- Four-stage workflow text.
- Findings with confidence chips.
- Provider-review banner.

**Avoid:**
- Editing or pasting transcript text (this is a tour, not a
  workflow demo).

---

## website_clip_04_imaging_workspace

**Filename:** `website_clip_04_imaging_workspace.mp4`
**Purpose:** Imaging feature section.
**Duration target:** 8–15 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted, click **Imaging** tab.

**Click path:**
1. Pause for 1–2 s on the OD/OS retinal diagram.
2. Pan over the OCT placeholder.
3. Pan over the Fundus Photos placeholder.
4. Pan over the Attachments placeholder.
5. Hover the Imaging Notes panel.

**Stop screen:** full Imaging tab visible with the diagram +
all three placeholders in frame.

**Show:**
- OD/OS retinal diagram.
- OCT / Fundus / Attachments placeholders with their
  demo-safe empty-state copy.
- Imaging Notes panel.

**Avoid:**
- Drawing on the canvas (a separate clip if needed).
- Uploading anything (placeholders only).

---

## website_clip_05_labs_orders_review_only

**Filename:** `website_clip_05_labs_orders_review_only.mp4`
**Purpose:** Review-only proof section.
**Duration target:** 8–12 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted, click **Labs / Orders
Review** tab.

**Click path:**
1. Pause for 1–2 s on the four review-only cards (Lab Results,
   Imaging Orders, Procedure Plan, Review Notes).
2. Hover over the disabled **View / Mark reviewed / Add note**
   buttons.
3. Pan over the disclaimer footnote.

**Stop screen:** Labs / Orders Review tab fully visible with
the disclaimer footnote in frame.

**Show:**
- Four review-only cards.
- The "Allowed actions: View / Mark reviewed / Add note"
  footnote.
- Disabled state on every action button — no clickable
  orders, no Submit / Place / Send.

**Avoid:**
- Pretending the buttons work — they're disabled by design.
- Submit Order / Place Order / Send Referral language anywhere
  in frame.

---

## website_clip_06_internal_chat_recipient_selector

**Filename:** `website_clip_06_internal_chat_recipient_selector.mp4`
**Purpose:** Internal team coordination section (Phase 19I).
**Duration target:** 8–12 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted, click **Chat** tab. Default
recipient is Dr. Carter.

**Click path:**
1. Pause for 1–2 s on the demo-local warning ("Demo-local
   internal chat — do not enter real PHI").
2. Pan over the **recipient selector** ("Send internal message
   to") and the recipient card showing Dr. Carter / Clinician /
   Online.
3. Click the recipient dropdown and switch to **Dr. Patel**.
   The recipient card updates to Dr. Patel / Clinician / Away
   and the composer placeholder updates to "Message Dr. Patel
   internally…".
4. Briefly hover the **Export .txt** and **Export .json**
   buttons.

**Stop screen:** Chat tab visible with the Dr. Patel recipient
card + Export buttons in frame.

**Show:**
- Demo-local warning text.
- Recipient selector dropdown.
- Recipient card with name / role / presence indicator.
- Composer placeholder reflecting selected recipient.
- Export .txt / Export .json buttons.

**Avoid:**
- Listing a patient as a recipient. (None should appear — if
  the dropdown surfaces "patient", stop and file an issue.)
- Anything that suggests the chat reaches a patient.

---

## website_clip_07_full_workspace_navigation

**Filename:** `website_clip_07_full_workspace_navigation.mp4`
**Purpose:** Longer demo preview.
**Duration target:** 25–45 seconds.
**Route:** `http://localhost:5173/?demo=1`

**Start screen:** workspace mounted on Overview.

**Click path:**
1. Hold ~3 s on Overview.
2. Click each tab in order, holding ~3 s on each:
   Clinical / Ophthalmology → Documentation / EMR/EHR →
   Imaging → Labs / Orders Review → Calendar →
   Communications → Documents → Chat.
3. End with ~3 s on Chat with the demo-local warning visible.

**Stop screen:** Chat tab.

**Show:**
- Smooth left-to-right tab progression.
- Burgundy sidebar throughout.
- 9 tabs total — no Billing.
- Phase 19F empty-state copy on the patient header throughout.

**Avoid:**
- Skipping a tab (we want all 9 visible in sequence).
- Clicking Submit Order / Send Referral / etc. (none should be
  present anyway).

---

## After capture

For each clip:

1. Drop the MP4 into `03_Website_Video_Clips/MP4/`.
2. (Optional) Drop a WEBM into `03_Website_Video_Clips/WEBM/`.
3. (Optional) Drop a PNG thumbnail into
   `03_Website_Video_Clips/GIF_or_Preview_Frames/`.
4. Update the matching row in `06_Manifest/media_manifest.md`
   with `Approved? = Yes / No / Reshoot` and a note.
5. If approved, copy the MP4 (and WEBM/thumbnail if produced)
   into `07_Ready_For_ChartNavMD_After_Approval/videos/`.

The chartnavmd.com replacement plan in
`07_Ready_For_ChartNavMD_After_Approval/instructions/CHARTNAVMD_WEBSITE_MEDIA_REPLACEMENT_PLAN.md`
maps each approved clip to its homepage / feature-section
placement. **Do not push to the live site until Jean-Max
signs off on every row.**
