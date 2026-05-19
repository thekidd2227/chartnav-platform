# chartnavmd.com Media Replacement Plan (Phase 19G)

> **DO NOT PUSH TO PRODUCTION YET.** This plan stages new
> images and video clips for chartnavmd.com replacement. Live
> site update only happens AFTER Jean-Max signs off every row
> in `06_Manifest/media_manifest.md` AND explicitly authorizes
> the swap.
>
> If you find yourself reading this plan with the goal of
> editing the live site, stop and re-confirm the approval
> status with Jean-Max in writing.

## Source of truth

All media here was captured against `main @ 50dc86a`
(Phase 19F merge). The post-billing-removal final clinical
demo UI. Fake/demo seed data only — no real PHI.

## Asset inventory

### Images (`07_Ready_For_ChartNavMD_After_Approval/images/`)

| File | Source | Use |
|---|---|---|
| `website_hero_overview.png` | `01_Screenshots/01_overview.png` | Homepage hero (fallback for video clip 01) |
| `website_clinical_workspace.png` | `01_Screenshots/02_clinical_ophthalmology.png` | Clinical / Ophthalmology section image |
| `website_documentation_workflow.png` | `01_Screenshots/03_documentation_emr_ehr.png` | Documentation section image |
| `website_imaging_workspace.png` | `01_Screenshots/04_imaging.png` | Imaging section image |
| `website_chat_internal.png` | `01_Screenshots/09_chat.png` | Internal team coordination section image |

### Video clips (`07_Ready_For_ChartNavMD_After_Approval/videos/`)

| File | Use | Duration |
|---|---|---|
| `website_clip_01_clinical_workspace_overview.mp4` | Homepage hero | 8–15 s |
| `website_clip_02_ophthalmology_workflow.mp4` | Clinical section | 8–15 s |
| `website_clip_03_documentation_workflow.mp4` | Documentation section | 8–15 s |
| `website_clip_04_imaging_workspace.mp4` | Imaging section | 8–15 s |
| `website_clip_05_internal_chat.mp4` | Internal team coordination section | 8–12 s |
| `website_clip_06_full_workspace_navigation.mp4` | Demo preview section | 25–45 s |

WEBM mirrors and PNG thumbnails are optional but encouraged
for browser compatibility and lazy-load posters.

## Suggested placement

### Homepage hero
- **Primary:** `website_clip_01_clinical_workspace_overview.mp4`
  (autoplay, muted, loop, `playsinline`).
- **Fallback (image):** `website_hero_overview.png` (used when
  the user has reduced-motion preferences enabled or the video
  fails to load).
- **Suggested alt text (image):** "ChartNav clinical workspace
  showing the Overview tab with patient header, demographic
  strip, and 9-tab clinical workspace navigation. Demo data."
- **Suggested caption / overlay:** "Provider-reviewed clinical
  workspace for specialist practices."

### Clinical / Ophthalmology section
- **Primary:** `website_clip_02_ophthalmology_workflow.mp4`.
- **Fallback (image):** `website_clinical_workspace.png`.
- **Suggested alt text (image):** "ChartNav Clinical /
  Ophthalmology tab with Cornea, Retina, Glaucoma, and
  Oculoplastics groups and clinical-signal-filtering banner.
  Demo data."
- **Suggested caption:** "Capture findings. Filter conversation.
  Build the diagram."

### Documentation section
- **Primary:** `website_clip_03_documentation_workflow.mp4`.
- **Fallback (image):** `website_documentation_workflow.png`.
- **Suggested alt text (image):** "ChartNav Documentation tab
  showing the four-stage workflow: Transcript, Extracted Facts,
  AI Draft, Final Note. Provider review required. Demo data."
- **Suggested caption:** "Transcript to draft to final note —
  every stage provider-reviewed."

### Imaging section
- **Primary:** `website_clip_04_imaging_workspace.mp4`.
- **Fallback (image):** `website_imaging_workspace.png`.
- **Suggested alt text (image):** "ChartNav Imaging tab with
  OD/OS retinal diagram and OCT, Fundus Photos, and Attachments
  placeholders. Demo data."
- **Suggested caption:** "OD/OS retinal annotations the
  clinician approves. ChartNav proposes; the clinician signs."

### Internal team coordination section
- **Primary:** `website_clip_05_internal_chat.mp4`.
- **Fallback (image):** `website_chat_internal.png`.
- **Suggested alt text (image):** "ChartNav Chat tab showing
  internal staff thread with demo-local warning and Export
  options. Demo data."
- **Suggested caption:** "Internal-only staff coordination.
  No patient messaging. No external delivery."

### Demo preview section (longer clip)
- **Primary:** `website_clip_06_full_workspace_navigation.mp4`.
- **Fallback (image):** none — link out to a tour page if
  the video can't play.
- **Suggested caption:** "30 seconds across the workspace —
  Overview to Chat. No billing, no patient messaging, no
  autonomous diagnosis."

## Hard guardrails for the website copy

The replacement copy on chartnavmd.com must remain consistent
with the safe-claims contract enforced in-repo. Specifically:

- ❌ No "HIPAA compliant" / "FDA cleared" / "EHR replacement"
  claims.
- ❌ No "autonomous diagnosis" / "auto-coding" / "auto-billing"
  / "claim submission" claims.
- ❌ No "patient messaging" / "patient portal" / "external
  delivery" claims.
- ❌ No "Submit Order" / "Place Order" / "Send Referral"
  feature copy.
- ✅ Provider-reviewed every step. Clinician approves the
  output.
- ✅ Internal staff coordination only.
- ✅ Specialist practices (ophthalmology / clinical-signal
  filtering scoped surfaces).
- ✅ Demo data shown — no real PHI.

If the website team wants to write new homepage copy, run it
through the same forbidden-phrase list (see
`scripts/check_commercial_claims.sh` in the repo).

## Approval workflow

1. Capture the 6 website clips per
   `03_Website_Video_Clips/CLIP_CAPTURE_INSTRUCTIONS/WEBSITE_CLIP_CAPTURE_INSTRUCTIONS.md`.
2. Copy the 5 image candidates from `02_Website_Selected/`
   into `07_Ready_For_ChartNavMD_After_Approval/images/`.
3. Copy the 6 approved clips from `03_Website_Video_Clips/MP4/`
   into `07_Ready_For_ChartNavMD_After_Approval/videos/`.
4. Walk every row of `06_Manifest/media_manifest.md`. Mark
   `Approved? = Yes / No / Reshoot` with notes.
5. **Hand back to the agent in writing**: "Approved — proceed
   to chartnavmd.com swap" OR "Reshoot the following: …".
6. Only after step 5 does the live site get touched.

## Rollback note

The legacy Desktop folders (`chartnav imags`,
`ChartNav_Media_Central`, `clips_final`, `clips_generated`,
`raw_clips`, `Screenshots`, `Video_Clips`) are intentionally
preserved. They contain the previous chartnavmd.com asset
baseline. If a Phase 19G clip needs to be reshot, those
folders are the comparison reference.

## Owner

Jean-Max Charles — final approver.
ChartNav agent — capture + staging only. Does not push to
production without explicit Jean-Max sign-off in writing.
