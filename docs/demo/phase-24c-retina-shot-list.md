# Phase 24C — Retina Workflow Screenshot & Recording Shot List

> **Phase:** 24C — Retina workflow demo packaging.
> **Companion to:** `phase-24c-retina-demo-runbook.md` (spoken
> script + click paths) and `phase-24b-retina-shot-list.md` (the
> Phase 24B editorial shot list — still valid).
>
> **No screenshot or video file is checked in by this phase.**
> This document is editorial / shot-list only. Phase 24C does
> **not** generate media.

Each shot below assumes the operator has just run
`bash scripts/reset_phase24b_retina_demo.sh` against a clean
local dev DB, started the backend (`make boot`) and frontend
(`npm run dev -- --host 127.0.0.1 --port 5173`), and opened the
app in a browser.

Reset between captures so the deterministic state matches every
shot exactly (same patient row, same seven queue items, same two
imaging studies, same retina tracking row, same action item).

---

## Editorial guardrails (read once before shooting)

Every shot must:

- carry the buyer-safe top-bar identity chip
  (`Identity <Role> · Org 1`) visible somewhere in the frame;
- include the on-screen safety affordance for that panel
  (provider-review banner, "Do not send to patient", "metadata
  only", etc.) wherever one exists;
- use the narration verbatim from
  `phase-24c-retina-demo-runbook.md` (the demo script is the
  source of truth — do not improvise on camera).

Never include in any shot or voice-over:

- HIPAA-compliant / HIPAA-certified / certified-EHR positioning
- autonomous diagnosis / automatic diagnosis / hands-free
  scribing
- auto-interpret OCT / auto-grade DR / auto-select IOL /
  anti-VEGF dosing recommendation
- automatic orders / referrals / coding / billing / claims
- patient messaging / send to patient / portal push
- EHR replacement / replace your EHR
- powered by IBM / powered by watsonx
- DICOM / a specific OCT or fundus-camera vendor
- real PHI / production-ready for PHI

If any of these appears on screen during a take, **re-record** —
do not edit around it.

---

## Shot list — 12 shots, 6–9 min full reel

### Shot 1 — Dashboard opening shot *(20 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` |
| Route | `/` → Sidebar → **CORE → Dashboard** |
| Show | The admin dashboard with **Open Queue Items / Overdue / Unsigned Notes / Active Locations / Providers** count cards. **Open Queue Items** ≥ 7. |
| Don't show | Any real-PHI-suggestive name; any encounter row pre-clicked. |
| Narration | "ChartNav coordinates a fake-data retina follow-up across clinic roles." |
| Filename | `01-admin-dashboard-cover.png` |
| Fake data reminder | Org slug `demo-eye-clinic`, PT-1001 Morgan Lee. |

### Shot 2 — Front desk queue with Morgan Lee *(20 s)*

| Field | Value |
|---|---|
| Identity | `front@chartnav.local` |
| Route | Sidebar → **CORE → Dashboard** (front-desk view) |
| Show | **Today's Schedule / Check-In Pending / Follow-Up** count cards non-zero. Scroll to **Recent & Due Items** — `check_in` and `follow_up` rows tied to Morgan are both visible. |
| Don't show | Any patient-messaging affordance (there is none — confirm). |
| Narration | "Front desk sees Morgan's check-in arrive in the right lane. After the visit closes, ChartNav puts an internal staff follow-up task back on this lane — never a patient message." |
| Filename | `02-front-desk-check-in.png` |
| Fake data reminder | All names + MRNs are fake. |

### Shot 3 — Technician handoff / workup queue *(20 s)*

| Field | Value |
|---|---|
| Identity | `tech@chartnav.local` |
| Route | Sidebar → **CORE → Dashboard** (technician view) |
| Show | **Workup Queue / Imaging Needed / Ready for Doctor** count cards non-zero. **My Queue** shows `technician_workup` + `imaging_needed` rows. |
| Don't show | Any device-vendor logo / brand on the imaging row. |
| Narration | "Workup and imaging metadata review live in one queue. ChartNav does not interpret OCT or grade disease." |
| Filename | `03-technician-workup.png` |
| Fake data reminder | Imaging "captured upstream" by the practice's own workflow. |

### Shot 4 — Morgan Lee encounter overview *(20 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` (or any role with access) |
| Route | Sidebar → **CORE → Encounters** → row `enc-row-1` |
| Show | 9-tab workspace with **Overview** tab active. Encounter status pill `in progress`. Patient identifier `PT-1001`. |
| Don't show | A scribe panel mid-streaming; an external LLM identifier. |
| Narration | "One row, one workspace. Same patient, every role. No scavenger hunt." |
| Filename | `04-encounter-overview.png` |
| Fake data reminder | Morgan Lee = fake by construction. |

### Shot 5 — Imaging metadata: OCT macula *(25 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` (or admin) |
| Route | Workspace → **Imaging** tab |
| Show | **Imaging Pipeline → Studies** with OCT macula row. Click the row; file table shows the `placeholder://demo/oct_macula_morgan_lee_demo.dcm` URI. |
| Don't show | Any pixel render of a real OCT; any DICOM library badge; any "auto-interpretation" affordance. |
| Narration | "Imaging shown here is metadata-only. The `placeholder://` URI is the demo contract." |
| Filename | `05-imaging-oct-macula-metadata.png` |
| Fake data reminder | Storage URI is a placeholder, not a real file. |

### Shot 6 — Imaging metadata: fundus photo *(20 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Route | Workspace → **Imaging** tab |
| Show | The fundus photo study row. Click the row; file row shows `placeholder://demo/fundus_photo_morgan_lee_demo.jpg`. |
| Don't show | A photo. There is no photo. Confirm the panel is the metadata table, not a viewer. |
| Narration | "Same contract for the fundus capture. ChartNav does not interpret fundus photographs." |
| Filename | `06-imaging-fundus-metadata.png` |
| Fake data reminder | Metadata only; no binary storage. |

### Shot 7 — Retina tracking *(25 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Route | Workspace → **Clinical / Ophthalmology** tab |
| Show | **Specialty Tracking → Retina** card. Diabetic retinopathy / moderate non-proliferative / OU / 4-week interval / status pill = needs review / draft assessment text. |
| Don't show | An auto-grading affordance; an anti-VEGF dosing recommendation; an "AI suggested" badge. |
| Narration | "Retina tracking is structured intent — not a diagnosis. The follow-up window drives the next visit." |
| Filename | `07-retina-tracking-card.png` |
| Fake data reminder | Diabetic retinopathy fact is fake / demo only. |

### Shot 8 — Provider-reviewed draft *(25 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Route | Workspace → **Documentation / EMR/EHR** tab |
| Show | Scribe Session banner ("provider review required"), Patient Summary banner ("Do not send to patient"), Pre-Visit Brief banner ("may be incomplete"), Provider Action Items banner ("take action automatically"). |
| Don't show | A "Send to patient" button. There isn't one. Confirm. |
| Narration | "ChartNav drafts. Providers decide. Banners are the contract, not decoration." |
| Filename | `08-documentation-banners.png` |
| Fake data reminder | All note content is fake / placeholder. |

### Shot 9 — Sign-off / reviewer queue *(20 s)*

| Field | Value |
|---|---|
| Identity | `rev@chartnav.local` |
| Route | Sidebar → **CORE → Dashboard** (reviewer view) |
| Show | **Notes Awaiting Review / AI Draft Review / Audit Exceptions / Blocked Items** count cards. (The wedge does not seed a `note_review` item; the cards still render with whatever Phase 20C counts apply.) |
| Don't show | An "auto-approve" affordance. |
| Narration | "Reviewers see the sign-off lane. Approval is always explicit." |
| Filename | `09-reviewer-signoff-lane.png` |
| Fake data reminder | No real provider sign-off captured. |

### Shot 10 — Internal follow-up task *(20 s)*

| Field | Value |
|---|---|
| Identity | `clin@chartnav.local` |
| Route | Workspace → **Documentation / EMR/EHR** tab → **Provider Action Items** panel |
| Show | The seeded action item with title containing `Review task only; internal staff coordination.` |
| Don't show | Any "send to patient" / "patient portal push" affordance. |
| Narration | "The only follow-up task ChartNav creates is internal staff coordination — never a patient-facing message." |
| Filename | `10-internal-followup-action.png` |
| Fake data reminder | Task is auto-seeded; review only. |

### Shot 11 — Admin dashboard reflection *(20 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` |
| Route | Sidebar → **CORE → Dashboard** (admin view) |
| Show | **Open Queue Items** ≥ 7. **Queue Aging by Status / Queue Type / Priority / Role** tables include the wedge lane queue types. |
| Don't show | An "auto-resolve" or "auto-close" affordance. |
| Narration | "Same seven seeded rows surface across reviewer and admin. Five role dashboards, one workspace, zero autonomous decisions." |
| Filename | `11-admin-queue-aging.png` |
| Fake data reminder | All counts derived from seeded fake data. |

### Shot 12 — Final safety / disclaimer screen *(20 s)*

| Field | Value |
|---|---|
| Identity | `admin@chartnav.local` |
| Route | `http://127.0.0.1:5173/landing` (or `?intro=1`) |
| Show | The landing page negative-assertion strip: "Not a certified EHR", "Not HIPAA-certified", "Does not autofill IOP", "Does not interpret OCT", "Real-PHI pilot requires BAA". |
| Don't show | A "Get started — sign up now" CTA. There isn't one. Confirm. |
| Narration | "ChartNav is not approved for real PHI by default. A controlled real-PHI pilot requires BAA, practice security review, and the Phase 23 readiness gate." |
| Filename | `12-safety-close.png` |
| Fake data reminder | Closing card; verifies the safe-claims contract. |

---

## Reset checklist between takes

1. `bash scripts/reset_phase24b_retina_demo.sh`
2. Confirm `All Phase 24B wedge rows present.` line.
3. Paste the localStorage cleanup snippet into DevTools.
4. Reload the browser; reset identity to the role for the next
   shot.
5. Run `bash scripts/check_commercial_claims.sh` once per
   recording session. Must pass before any take.

## Repo evidence map

| Shot | Code path |
|---|---|
| 1, 11 | `apps/web/src/RoleDashboard.tsx::AdminDashboardView` |
| 2 | `FrontDeskDashboardView` |
| 3 | `TechnicianDashboardView` |
| 4 | `apps/web/src/App.tsx` → `ClinicalTabbedWorkspace.tsx` |
| 5, 6 | `apps/web/src/ImagingPipelinePanel.tsx` |
| 7 | `apps/web/src/SpecialtyTrackingPanel.tsx` |
| 8, 10 | `apps/web/src/NoteWorkspace.tsx` (Phase 12 / 19 banners) |
| 9 | `ReviewerDashboardView` |
| 12 | `apps/web/src/LandingPage.tsx` |

Authoritative seed: `apps/api/scripts_seed.py::_seed_phase_24b_retina_wedge`.
Authoritative test: `apps/api/tests/test_phase_24b_retina_wedge.py`.
