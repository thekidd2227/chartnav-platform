# Phase 19G — Sales/Demo Clip Capture Instructions

> Six clips for the sales/demo motion (separate from the
> chartnavmd.com website clips, which have their own runbook
> in `03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS/`).
>
> **Fake/demo seed data only. No real PHI. Demo mode hides the
> dev API URL chip.** If you can see `localhost:8000` on screen
> at any point, stop and reload `?demo=1`.

## Capture environment

| Setting | Value |
|---|---|
| Local app | `npm run dev` from `apps/web/` (default port 5173) |
| Backend | `apps/api` running locally (the operator's usual dev stack) |
| URL | `http://localhost:5173/?demo=1` |
| Viewport | 1440 × 900 (or 1600 × 1000 if your screen accommodates) |
| Recorder | macOS Screenshot toolbar (Cmd-Shift-5 → "Record selected portion") or Loom |
| Filename prefix | `clip_NN_*.mp4` (NN matches the list below) |
| Output folder | `04_Demo_Clip_Instructions/` (drop the recorded files here) |

Browser hygiene before recording:

- New incognito / private window so favicons/extension UI don't bleed in.
- Hide the address bar if your recorder allows (otherwise crop in post).
- No DevTools open.
- No Slack / Mail / iMessage notifications visible.

---

## clip_01_overview_to_clinical

**Filename:** `clip_01_overview_to_clinical.mp4`
**Duration target:** 12–18 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Page loads → DEMO MODE badge visible top-right.
2. Click `enc-row-1` (Morgan Lee) in the encounter list.
3. Workspace mounts on **Overview** (default).
4. Slow scroll over the Overview cards (Patient Snapshot →
   Visit Summary → Alerts → Recent Encounters → Tasks →
   Favorites → Timeline) for ~4 seconds.
5. Click the **Clinical / Ophthalmology** tab.
6. Pause for ~2 seconds on the Clinical tab to let the
   Phase 17B Clinical Signal Filtering banner read.

**Show:**
- Burgundy sidebar with teal active stripe on Encounters.
- Patient header red micro-accent stripe.
- Demographic strip with intentional empty-state copy.
- 9-tab bar with Chat as the last tab and **no Billing**.

**Don't show:**
- Localhost API URL chip.
- Browser address bar (or crop in post).
- DevTools.
- Real names/MRNs (seeded data only).

---

## clip_02_documentation_workflow

**Filename:** `clip_02_documentation_workflow.mp4`
**Duration target:** 18–25 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Click `enc-row-1` (Morgan Lee).
2. Click the **Documentation / EMR/EHR** tab.
3. Pan slowly over the four-stage workflow header (Transcript →
   Extracted Facts → AI Draft → Final Note).
4. Scroll through the NoteWorkspace tiers — transcript,
   findings with confidence chips, draft.
5. Hover briefly on the "Provider review required" copy.

**Show:**
- The four-stage workflow text.
- The provider-review banner copy.
- Findings with confidence chips.

**Don't show:**
- Any "ChartNav diagnoses" / "autonomous" / "HIPAA compliant"
  language. (None should be present — if it is, stop and file
  an issue.)

---

## clip_03_imaging_workspace

**Filename:** `clip_03_imaging_workspace.mp4`
**Duration target:** 12–18 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Click `enc-row-1`.
2. Click the **Imaging** tab.
3. Pan over the OD/OS retinal diagram.
4. Pan over the OCT / Fundus / Attachments placeholders.

**Show:**
- OD/OS diagram.
- "Provider proposes / clinician approves" language if
  visible.

**Don't show:**
- Real fundus photos. (Demo placeholders only.)

---

## clip_04_labs_orders_review_only

**Filename:** `clip_04_labs_orders_review_only.mp4`
**Duration target:** 10–14 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Click `enc-row-1`.
2. Click the **Labs / Orders Review** tab.
3. Hover the View / Mark reviewed / Add note buttons (don't
   click — they're disabled review-only by design).
4. Pan over the disclaimer footnote.

**Show:**
- Labs / Imaging Orders / Procedure Plan / Review Notes
  cards.
- "Allowed actions: View / Mark reviewed / Add note" footnote.
- Disabled state on all action buttons (no clickable orders).

**Don't show:**
- Submit Order / Place Order / Send Referral (none should be
  present — if any appears, stop and file an issue).

---

## clip_05_communications_documents_chat

**Filename:** `clip_05_communications_documents_chat.mp4`
**Duration target:** 18–25 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Click `enc-row-1`.
2. Click the **Communications** tab → pause 3 s.
3. Click the **Documents** tab → pause 3 s.
4. Click the **Chat** tab → pause 5 s.
5. On Chat, briefly hover the "Demo-local internal chat — do
   not enter real PHI" warning.

**Show:**
- Communications: internal staff handoff log.
- Documents: PDF / report / external upload placeholders with
  storage warnings.
- Chat: demo-local warning, staff thread, Export .txt /
  Export .json buttons.

**Don't show:**
- "Send to Patient" / "Patient Portal" / external messaging.
  (None should appear.)

---

## clip_06_full_demo_walkthrough

**Filename:** `clip_06_full_demo_walkthrough.mp4`
**Duration target:** 60–90 seconds
**Starting route:** `http://localhost:5173/?demo=1`

**Click path:**
1. Page loads → DEMO MODE badge visible.
2. Click `enc-row-1` (Morgan Lee).
3. Visit each tab in order, ~6–10 seconds each:
   Overview → Clinical / Ophthalmology → Documentation /
   EMR/EHR → Imaging → Labs / Orders Review → Calendar →
   Communications → Documents → Chat.
4. End on the Chat tab with the demo-local warning visible.

**Show:**
- Smooth left-to-right tab progression.
- Burgundy sidebar present throughout.
- Phase 19F empty-state copy on the patient header
  throughout.

**Don't show:**
- Billing tab (there isn't one).
- Frantic clicking, address bar, DevTools, real PHI.

---

## After capture

1. Drop the six MP4s into `04_Demo_Clip_Instructions/`.
2. Update `06_Manifest/media_manifest.md` rows under
   "Sales/demo clips" with `Approved? = Yes/No/Reshoot` notes.
3. If a clip is approved AND also slated for chartnavmd.com,
   copy it into
   `07_Ready_For_ChartNavMD_After_Approval/videos/` per
   the website-clip runbook.
