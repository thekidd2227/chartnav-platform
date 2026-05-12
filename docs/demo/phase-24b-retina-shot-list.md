# Phase 24B — Morgan Lee Retina Workflow Shot List

> **Phase:** 24B — Retina workflow wedge.
> **Companion to:** `phase-24b-retina-workflow-demo-script.md`
> (spoken script) and `chartnav-video-clip-shot-list.md` (the
> Phase 21C ophthalmology video plan — still valid).
>
> **No video files are checked into this repo.** This document is
> editorial / shot-list only.

The Phase 24B wedge is a 6–9 minute single-patient walkthrough.
This shot list is what to **capture** if you record clips against
the local stack. Each clip is a single take, pre-reset DB, against
the seeded fake data (`demo-eye-clinic` / PT-1001 / Morgan Lee).

Use `make reset-db` (or `rm chartnav.db && alembic upgrade head
&& python scripts_seed.py`) between takes. The wedge is
deterministic and idempotent; the same seven queue rows show up
every run.

---

## Editorial guardrails

Every clip must:

- visibly include the provider-review safety banner on any
  documentation panel it covers;
- use the safe phrasing from
  `phase-24b-retina-workflow-demo-script.md`;
- avoid every forbidden phrase in §Forbidden phrases (do not
  narrate around an on-screen forbidden phrase — re-record).

Voice-over phrases (verbatim from the demo script):

- "ChartNav is the ophthalmology clinic workflow coordination
  layer."
- "Every artifact is provider-reviewed; every transition is
  provider-driven."
- "ChartNav does not diagnose, interpret OCT, grade DR, place
  orders, send referrals, bill, or message patients."

Never say:

- HIPAA compliant / HIPAA certified
- Certified EHR / EHR replacement
- Autonomous diagnosis / automatic diagnosis / hands-free scribing
- Auto-interpret OCT / auto-grade DR / auto-select IOL / auto-
  recommend anti-VEGF
- Automatic orders / referrals / coding / billing / claims
- Patient messaging / portal push / send to patient
- Powered by IBM / watsonx
- DICOM / a specific device vendor

---

## Shot list — 9 clips

Each clip targets 20–75 s; full reel runs 6–9 min.

### Clip 1 — Cover / safety contract *(30 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` |
| Where | Top bar |
| Capture | The seeded identity chip ("Identity Admin · Org 1"). Optional B-roll: landing page negative-assertion strip. |
| Voice-over | "We'll follow one fake patient — Morgan Lee — through a retina follow-up. Fake data only. Provider-reviewed end to end." |

### Clip 2 — Front-desk dashboard *(45 s)*

| Field | Value |
|---|---|
| Identity | `front@chartnav.local` |
| Where | Sidebar → CORE → Dashboard |
| Capture | **Today's Schedule** / **Check-In Pending** / **Follow-Up** count cards. Scroll to **Recent & Due Items** showing the seeded `check_in` and `follow_up` lanes. |
| Voice-over | "Front desk sees Morgan's check-in arrive in the right lane, and after sign-off, an internal staff follow-up task — never a patient message." |

### Clip 3 — Technician dashboard *(45 s)*

| Field | Value |
|---|---|
| Identity | `tech@chartnav.local` |
| Where | Sidebar → CORE → Dashboard |
| Capture | **Workup Queue** + **Imaging Needed** + **Ready for Doctor** count cards. Scroll to **My Queue** showing `technician_workup` + `imaging_needed`. |
| Voice-over | "Workup and imaging metadata review live in one queue. ChartNav does not interpret OCT or grade disease." |

### Clip 4 — Doctor dashboard *(60 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Where | Sidebar → CORE → Dashboard |
| Capture | **Ready for MD** / **Imaging Ready for Review** / **Sign-Off Queue** / **High-Priority Clinical Items** count cards. Scroll to **My Encounters** showing `ready_for_doctor`, `documentation`, `signoff_needed`. |
| Voice-over | "One screen — ready for MD, draft documentation, sign-off queue. Sign-off is provider-driven, never automatic." |

### Clip 5 — Open Morgan Lee *(20 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` |
| Where | Sidebar → CORE → Encounters → row 1 |
| Capture | Click `enc-row-1`. The 9-tab workspace appears, default tab Overview. |
| Voice-over | "One row, one workspace. Same patient — every role. No scavenger hunt." |

### Clip 6 — Clinical / Ophthalmology tab *(60 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` (or `clin@chartnav.local`) |
| Where | Workspace → Clinical / Ophthalmology tab |
| Capture | **Specialty Tracking → Retina** card showing diabetic retinopathy / moderate non-proliferative / OU / 4-week interval / draft. |
| Voice-over | "Retina tracking is structured intent — not a diagnosis. The follow-up window drives the next visit, the practice still decides." |

### Clip 7 — Imaging tab *(60 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` (or `tech@chartnav.local`) |
| Where | Workspace → Imaging tab |
| Capture | **Imaging Pipeline → Studies** with OCT macula + fundus photo rows. Click a row — the file table shows the `placeholder://` storage URI. |
| Voice-over | "Metadata only. The `placeholder://` URI is the demo contract. No binary upload, no DICOM claim, no device-vendor claim." |

### Clip 8 — Documentation tab *(60 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Where | Workspace → Documentation tab |
| Capture | Scribe Session banner ("provider review required"), Patient Summary banner ("Do not send to patient"), Provider Action Items banner ("take action automatically"). Scroll to the seeded action item: `Review task only; internal staff coordination.` |
| Voice-over | "ChartNav drafts. Providers decide. Banners are not decoration — they're the contract." |

### Clip 9 — Reviewer + admin dashboards *(75 s)*

| Field | Value |
|---|---|
| Identity | `rev@chartnav.local` then `admin@chartnav.local` |
| Where | Sidebar → CORE → Dashboard |
| Capture | Reviewer view (Notes Awaiting Review / Blocked Items cards). Then switch to admin — show **Queue Aging by Status / Queue Type / Priority / Role**. Open Queue Items card reads ≥ 7. |
| Voice-over | "Same seven seeded rows surface across reviewer and admin. Five role dashboards, one workspace, zero autonomous decisions." |

---

## Reset checklist before each take

1. `rm -f apps/api/chartnav.db`
2. `cd apps/api && alembic upgrade head`
3. `python scripts_seed.py`
4. Open the web app, set identity to `admin@chartnav.local`,
   confirm Morgan Lee row exists.
5. Run `bash scripts/check_commercial_claims.sh` and
   `bash scripts/check_website_claims.sh` — both must pass
   before recording.

---

## Repo evidence map

| Clip | Code path |
|---|---|
| 2 | `apps/api/scripts_seed.py::_seed_phase_24b_retina_wedge` (check_in + follow_up); `apps/web/src/RoleDashboard.tsx::FrontDeskDashboardView` |
| 3 | Same seed (technician_workup + imaging_needed); `TechnicianDashboardView` |
| 4 | Same seed (ready_for_doctor + documentation + signoff_needed); `DoctorDashboardView` |
| 5 | `apps/web/src/App.tsx` encounter list → `ClinicalTabbedWorkspace.tsx` |
| 6 | `_ensure_retina_tracking_for_wedge` → `SpecialtyTrackingPanel.tsx` |
| 7 | `_ensure_imaging_study_for_wedge` + `_ensure_imaging_file_for_wedge` → `ImagingPipelinePanel.tsx` |
| 8 | `_ensure_action_item_for_wedge` → existing Phase 12 / 19 banners |
| 9 | `ReviewerDashboardView` + `AdminDashboardView` over the same queue |

Authoritative backend test:
`apps/api/tests/test_phase_24b_retina_wedge.py` (18 tests).
