# Phase 19G — Media Review Manifest

> **Default approval status is `No`.** Walk every row, mark
> `Yes` / `No` / `Reshoot`, leave a note, then hand back to
> the agent for delivery overwrite or capture re-runs.

Captured against `main @ 50dc86a` (Phase 19F merge). Every file
below was generated against fake/demo seed data. No real PHI.

---

## 01 — Tab screenshots (`01_Screenshots/`)

| File | Tab / Screen | Type | Intended placement | Status | Approved? | Notes |
|---|---|---|---|---|---|---|
| `01_overview.png` | Overview tab | screenshot | review only | Captured | No | Patient Snapshot · Visit Summary · Alerts · Recent Encounters · Tasks · Favorites · Timeline (with workflow events + demo-hidden composer notice) · Allowed transitions |
| `02_clinical_ophthalmology.png` | Clinical / Ophthalmology tab | screenshot | review + website (Clinical section) | Captured | No | Phase 17B Clinical Signal Filtering banner; Cornea / Retina / Glaucoma / Oculoplastics groups |
| `03_documentation_emr_ehr.png` | Documentation / EMR/EHR tab | screenshot | review + website (Documentation section) | Captured | No | NoteWorkspace: transcript → findings → AI draft → final note |
| `04_imaging.png` | Imaging tab | screenshot | review + website (Imaging section) | Captured | No | OD/OS retinal diagram; OCT / Fundus / Attachments placeholders |
| `05_labs_orders_review.png` | Labs / Orders Review tab | screenshot | review only | Captured | No | Review-only: View / Mark reviewed / Add note. No Submit / Place / Send. |
| `06_calendar.png` | Calendar tab | screenshot | review only | Captured | No | Appointment time / provider / room / upcoming visits |
| `07_communications.png` | Communications tab | screenshot | review only | Captured | No | Internal staff handoff log only — no patient send |
| `08_documents.png` | Documents tab | screenshot | review only | Captured | No | PDFs / reports / external uploads with demo-safe storage warnings |
| `09_chat.png` | Chat tab | screenshot | review + website (Internal team coord. section) | Captured | No | Demo-local internal chat; Export .txt / .json buttons visible |
| `10_sidebar_header_closeup.png` | Sidebar (Phase 19E burgundy) | screenshot | review + website hero (sidebar reveal) | Captured | No | Burgundy sidebar with teal active stripe on Encounters; CORE / CLINICAL / OPERATIONS / ADMIN / Quick Actions groups; **no Billing**, **no Send Message** |
| `11_patient_header_demographics.png` | Patient header + demographic strip | screenshot | review only | Captured | No | Phase 19E red micro-accent stripe + Phase 19F intentional empty states ("Not available in demo" / "No allergies recorded" / etc.) |
| `12_mobile_or_narrow_layout.png` | Overview at 414×896 viewport | screenshot | review only | Captured | No | Responsive collapse of Overview cards |

---

## 02 — Website-selected images (`02_Website_Selected/`)

> Operator: copy from `01_Screenshots/` and rename to the
> filenames below before passing to the website team.

| File | Source | Type | Intended placement | Status | Approved? | Notes |
|---|---|---|---|---|---|---|
| `website_hero_overview.png` | copy of `01_overview.png` | website image | chartnavmd.com homepage hero (fallback for clip 01) | Pending copy | No | Frame on the workspace + the burgundy sidebar |
| `website_clinical_workspace.png` | copy of `02_clinical_ophthalmology.png` | website image | Clinical / Ophthalmology section | Pending copy | No | Show clinical filtering banner |
| `website_documentation_workflow.png` | copy of `03_documentation_emr_ehr.png` | website image | Documentation section | Pending copy | No | Show the four-stage workflow |
| `website_imaging_workspace.png` | copy of `04_imaging.png` | website image | Imaging section | Pending copy | No | OD/OS diagram + OCT/Fundus placeholders |
| `website_chat_internal.png` | copy of `09_chat.png` | website image | Internal team coord. section | Pending copy | No | Demo-local warning visible; Export buttons visible |

---

## 03 — Website video clips (`03_Website_Video_Clips/`)

> **Manual capture required.** See
> `03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS/WEBSITE_CLIP_CAPTURE_INSTRUCTIONS.md`
> for exact recording steps. Drop MP4s into
> `03_Website_Video_Clips/MP4/` and copy approved clips into
> `07_Ready_For_ChartNavMD_After_Approval/videos/`.

| File | Tab / Screen | Type | Intended placement | Duration | Status | Approved? | Notes |
|---|---|---|---|---|---|---|---|
| `website_clip_01_clinical_workspace_overview.mp4` | Overview | website clip | Homepage hero | 8–15 s | Manual capture | No | Burgundy sidebar + patient header + demographic strip + tab row |
| `website_clip_02_ophthalmology_workflow.mp4` | Clinical / Ophthalmology | website clip | Clinical section | 8–15 s | Manual capture | No | Search · categories · Favorites · Retina/Cornea/Glaucoma/Oculoplastics |
| `website_clip_03_documentation_workflow.mp4` | Documentation / EMR/EHR | website clip | Documentation section | 8–15 s | Manual capture | No | Transcript → Extracted Facts → AI Draft → Final Note · provider review language |
| `website_clip_04_imaging_workspace.mp4` | Imaging | website clip | Imaging section | 8–15 s | Manual capture | No | OCT · Fundus · Attachments · Selected Image Viewer |
| `website_clip_05_internal_chat.mp4` | Chat | website clip | Internal team coord. | 8–12 s | Manual capture | No | Demo-local warning · staff thread · export options |
| `website_clip_06_full_workspace_navigation.mp4` | All 9 tabs | website clip | Demo preview section | 25–45 s | Manual capture | No | Sequential tab tour, no Billing, professional pacing |

WEBM versions and PNG thumbnail frames are optional — drop into
`03_Website_Video_Clips/WEBM/` and
`03_Website_Video_Clips/GIF_or_Preview_Frames/` if produced.

---

## 04 — Sales/demo clip instructions (`04_Demo_Clip_Instructions/`)

| File | Type | Status | Approved? | Notes |
|---|---|---|---|---|
| `CLIP_CAPTURE_INSTRUCTIONS.md` | instruction | Generated | No | Sales/demo clips (separate from website clips) — clip_01..06 runbook |

---

## 05 — Archive reference (`05_Archive_Reference/`)

| File | Type | Status | Approved? | Notes |
|---|---|---|---|---|
| _(empty)_ | — | Reserved | — | Drop reference shots from legacy Desktop folders here ONLY if you need a side-by-side comparison. Legacy folders themselves are NOT deleted in this phase. |

---

## 07 — Ready for chartnavmd.com (after approval) (`07_Ready_For_ChartNavMD_After_Approval/`)

| File | Type | Status | Approved? | Notes |
|---|---|---|---|---|
| `images/website_*.png` | website image | Pending copy from 02 | No | Copy after row-by-row approval above |
| `videos/website_clip_*.mp4` | website clip | Pending manual capture | No | Copy after capture + row-by-row approval |
| `instructions/CHARTNAVMD_WEBSITE_MEDIA_REPLACEMENT_PLAN.md` | instruction | Generated | No | Suggested placements / alt text / captions |

---

## Sign-off

- [ ] Every row has `Approved? = Yes` (or is intentionally `Reshoot`).
- [ ] No row contains forbidden vocabulary (Billing / CPT / etc.).
- [ ] No row contains real PHI.
- [ ] `07_Ready_For_ChartNavMD_After_Approval/` is populated with approved files only.
- [ ] Final-delivery folder still untouched on disk.
- [ ] chartnavmd.com still untouched.

Reviewer: Jean-Max
Date: ____________
