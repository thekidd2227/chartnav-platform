# Phase 24B — Morgan Lee Retina Follow-Up Workflow Demo Script

> **Phase:** 24B — Retina workflow wedge.
> **Audience:** ophthalmology practice owner / clinical champion
> / advisor / investor watching the live fake-patient demo.
> **Companion to:** `chartnav-ophthalmology-demo-script.md` (the
> Phase 21C ophthalmology-specific script — still valid). This
> script is **narrower** and **deeper**: one patient, one
> diagnosis, one round trip through the clinic, with the seeded
> wedge driving every screen.

The intent of Phase 24B is to demonstrate ChartNav as an
**ophthalmology clinic workflow coordination layer**, not a
generic AI scribe, not a dashboard toy, not a pile of
disconnected panels. Every screen below is anchored to the same
seeded fake patient (PT-1001 Morgan Lee) and the same seven
seeded work-queue rows. The point is to **show the workflow,
not pitch the technology**.

---

## Demo data — fake by construction

- Org: `demo-eye-clinic` (seeded by `scripts_seed.py`).
- Patient: `PT-1001` Morgan Lee — fake.
- Encounter: `encounter_id=1` — fake.
- Provider: Dr. Carter — fake NPI seeded for the demo only.
- Retina diagnosis: diabetic retinopathy, moderate non-
  proliferative, OU, 4-week follow-up interval. Fake.
- Imaging metadata: one OCT macula study + one fundus photo
  study — metadata only, **`placeholder://` storage URIs**.
  **No binary image is ever uploaded or stored.**
- Action item: review the retina follow-up window after sign-off.
  Title is `Review task only; internal staff coordination.`
- Every name, MRN, DOB, NPI, and follow-up interval is fake. Say
  **"fake data only"** out loud once at the cover.

Reset between takes with `make reset-db` (or rerun
`alembic upgrade head && python scripts_seed.py` against an
ephemeral SQLite DB).

---

## What the wedge proves

| Stop | What the buyer sees | What ChartNav is, in one sentence |
|---|---|---|
| 1 | Cover, "fake data only" | Workflow layer for ophthalmology, not an AI scribe. |
| 2 | Front-desk dashboard | Check-in arrives in the right lane. |
| 3 | Technician dashboard | Workup + imaging-needed live in one queue. |
| 4 | Doctor dashboard | "Ready for MD" + sign-off queue, both on one screen. |
| 5 | Open the Morgan Lee encounter | One row → full workspace, no scavenger hunt. |
| 6 | Clinical / Ophthalmology tab | Retina tracking row visible; not autonomous. |
| 7 | Imaging tab | OCT + fundus metadata in the pipeline; not interpretation. |
| 8 | Documentation tab | Provider-reviewed draft with the safety banner. |
| 9 | Reviewer + admin dashboards | Sign-off lane, queue aging, internal follow-up. |

Each stop has a one-line **say** (the safe claim) and a
**show** (what's on screen). The full walkthrough is 6–9 minutes.

---

## Demo flow — 9 stops

### Stop 1 — Cover + safety contract *(45 s)*

**Say:**
> "We're going to follow one patient — Morgan Lee, fake by
> construction — through a retina follow-up. Front desk to
> provider sign-off. Everything you see is provider-reviewed.
> Nothing here is autonomous. No real patient data."

**Show:** Top bar with the seeded identity chip. Optional:
landing page with the negative-assertion safety strip.

**Forbidden:** Do not lead with "AI scribe", "hands-free
scribing", or "saves money." Do not say "HIPAA compliant" or
"certified EHR." The repo's safe-claims contract bans those.

---

### Stop 2 — Front-desk dashboard *(45 s)*

**Say:**
> "First view — front desk. Morgan Lee's retina follow-up
> arrived as a check-in item, and after the visit closes,
> ChartNav puts an internal staff follow-up task back on this
> same lane so the office knows to confirm the next visit
> window. No patient message. No claim submission. Internal
> staff coordination only."

**Show:**
1. Sidebar → **CORE → Dashboard**.
2. Switch identity to `front@chartnav.local`.
3. Point to the **Today's Schedule** + **Check-In Pending** +
   **Follow-Up** count cards.
4. Scroll to **Recent & Due Items** — the seeded `check_in` row
   and the seeded `follow_up` row both show up in the lane.

**Repo evidence:** `apps/api/scripts_seed.py`
`_seed_phase_24b_retina_wedge()` seeds the
`("check_in", …, "front_desk", …)` and
`("follow_up", …, "front_desk", …)` queue rows.

---

### Stop 3 — Technician dashboard *(45 s)*

**Say:**
> "Next — technician. Same patient. The workup queue is what the
> tech sees on their phone, paired with the imaging-needed lane
> for OCT and fundus capture. ChartNav does not interpret OCT.
> It does not grade DR. It coordinates the work — workup,
> imaging metadata review, hand-off to the doctor."

**Show:**
1. Switch identity to `tech@chartnav.local`.
2. **Workup Queue** + **Imaging Needed** + **Ready for Doctor**
   count cards are all non-zero.
3. Scroll to **My Queue** — the seeded `technician_workup` and
   `imaging_needed` rows both reference the Morgan Lee
   encounter.

**Forbidden:** Do not say "auto-grade DR", "interpret OCT",
"auto-select IOL", or "auto-recommend anti-VEGF."

---

### Stop 4 — Doctor dashboard *(60 s)*

**Say:**
> "Now the doctor. One screen — ready for MD, pre-visit briefs,
> imaging ready for review, documentation in progress, sign-off
> queue. Morgan's retina follow-up is high priority. Sign-off
> is gated by explicit provider action — never automatic."

**Show:**
1. Switch identity to `clin@chartnav.local`.
2. **Ready for MD** + **Imaging Ready for Review** + **Sign-Off
   Queue** + **High-Priority Clinical Items** count cards are
   all non-zero.
3. Scroll to **My Encounters** — the seeded `ready_for_doctor`,
   `documentation`, and `signoff_needed` rows are all visible.

---

### Stop 5 — Open the Morgan Lee encounter *(30 s)*

**Say:**
> "From any role's dashboard, the operator clicks into
> encounters. One row — one workspace. No scavenger hunt."

**Show:**
1. Sidebar → **CORE → Encounters**.
2. Click row `enc-row-1` (Morgan Lee, PT-1001).
3. The 9-tab workspace appears.

---

### Stop 6 — Clinical / Ophthalmology tab *(75 s)*

**Say:**
> "The Clinical tab is where the ophthalmology-specific tracking
> lives. The retina row says: diabetic retinopathy, moderate
> non-proliferative, OU, 4-week interval, draft, pending
> provider review. ChartNav does not diagnose. It tracks the
> structured intent so the next visit gets scheduled correctly."

**Show:**
1. Click `ctw-tab-clinical`.
2. **Specialty Tracking → Retina** — the seeded retina card is
   visible with `condition`, `eye=OU`, `follow_up_interval=4
   weeks`, status pill.

**Repo evidence:** `apps/api/scripts_seed.py`
`_ensure_retina_tracking_for_wedge()` writes the row;
`apps/web/src/SpecialtyTrackingPanel.tsx` renders it.

---

### Stop 7 — Imaging tab *(60 s)*

**Say:**
> "Imaging. ChartNav stores **metadata only** — no binary upload
> path. The `placeholder://` storage URI is the explicit demo
> contract. The technician marks the study captured upstream;
> the doctor reviews and signs off. No interpretation, no auto-
> grading, no device-vendor claim."

**Show:**
1. Click `ctw-tab-imaging`.
2. **Imaging Pipeline → Studies** — OCT macula + fundus photo
   rows visible.
3. Hover or click a row — the file row shows the
   `placeholder://` storage URI.

**Forbidden:** Do not name any specific OCT device, fundus
camera, or imaging vendor. Do not say "DICOM."

---

### Stop 8 — Documentation tab *(60 s)*

**Say:**
> "Documentation. The provider-review banner is the contract:
> every artifact is a draft until a provider signs it. ChartNav
> drafts. Providers decide."

**Show:**
1. Click `ctw-tab-documentation`.
2. **Scribe / Summary / Brief / Provider Action Items** panels
   each show their provider-review banner copy.
3. The seeded action item (`Review task only; internal staff
   coordination.`) appears in the provider action items panel.

**Repo evidence:** Phase 12 / 19 banner copy is preserved
verbatim; Phase 24B did not alter it.

---

### Stop 9 — Reviewer + admin dashboards *(60 s)*

**Say:**
> "Last — the audit view. Reviewer sees the sign-off lane.
> Admin sees queue aging across status, priority, role, and
> queue type. Same seven seeded rows show up on every dashboard
> that owns a slice of the work."

**Show:**
1. Switch identity to `rev@chartnav.local` → sign-off lane.
2. Switch identity to `admin@chartnav.local` → **Queue Aging
   by Status / Queue Type / Priority / Role** tables include
   the wedge rows.
3. Confirm: open queue items count ≥ 7.

**Close:**
> "Same fake patient. Same seven seeded rows. Five role
> dashboards, one workspace, zero autonomous decisions. That's
> ChartNav — the ophthalmology clinic workflow coordination
> layer."

---

## Forbidden phrases (do not say, do not put on screen)

| Forbidden | Why |
|---|---|
| HIPAA-compliant / HIPAA-certified | Not certified. Pilot only. |
| Certified EHR | ChartNav is not an EHR. |
| Autonomous diagnosis / automatic diagnosis | Banned by the safe-claims contract. |
| Auto-interpret OCT / auto-grade DR / auto-select IOL / auto-recommend anti-VEGF | Banned. |
| Automatic orders / referrals / coding / billing / claims | Banned. |
| Patient messaging / portal push / send to patient | Banned. |
| Replace your EHR / EMR / scribe / doctor | Banned. |
| Hands-free scribing / chart fills itself / note writes itself | Banned. |
| Powered by IBM / watsonx | Banned (device-vendor framing). |
| DICOM / specific OCT / fundus camera vendor | Banned (device-vendor framing). |
| IRIS Registry submission / MIPS submission | Roadmap, not current. |

If anything on this list appears on the screen mid-demo, **stop
the demo, fix the source, re-run**. Do not narrate around it.

---

## Repo evidence map

| Stop | Code path |
|---|---|
| 2 | `scripts_seed.py::_seed_phase_24b_retina_wedge` `check_in` + `follow_up` rows; `RoleDashboard.tsx` FrontDeskDashboardView |
| 3 | Same seed, `technician_workup` + `imaging_needed` rows; TechnicianDashboardView |
| 4 | Same seed, `ready_for_doctor` + `documentation` + `signoff_needed`; DoctorDashboardView |
| 5 | `App.tsx` encounter list → ClinicalTabbedWorkspace |
| 6 | `_ensure_retina_tracking_for_wedge` → `SpecialtyTrackingPanel.tsx` |
| 7 | `_ensure_imaging_study_for_wedge` + `_ensure_imaging_file_for_wedge` (`placeholder://` only) → `ImagingPipelinePanel.tsx` |
| 8 | `_ensure_action_item_for_wedge` → NoteWorkspace banner copy (Phase 12 / 19) |
| 9 | ReviewerDashboardView + AdminDashboardView consume the same seeded queue |

Backend authoritative test:
`apps/api/tests/test_phase_24b_retina_wedge.py` (18 tests).

---

## Reset checklist before each take

1. `rm -f apps/api/chartnav.db`
2. `cd apps/api && alembic upgrade head`
3. `python scripts_seed.py`
4. Open the web app, set identity to `admin@chartnav.local`,
   confirm Morgan Lee row exists.
5. Run `bash scripts/check_commercial_claims.sh` —
   must pass before recording.

The wedge is fully idempotent — running step 3 a second time
must not duplicate any of the seven seeded queue rows, the
retina row, or the imaging studies/files.

---

## Phase 24C addendum

After completing the Phase 24B Morgan Lee walkthrough, use `phase-24c-demo-hardening-product-wedge-expansion.md` for the controlled post-24B operator segment. The addendum covers the Retina Workflow v2 preservation proof, the deterministic glaucoma second-specialty proof, and the Admin/Ops Dashboard queue-aging and workload visibility proof.

The Phase 24C addendum does **not** change the clinical-safety boundary for this demo. Keep narration limited to workflow coordination, staff routing, operational visibility, deterministic fake data, and provider-reviewed context. Do not claim diagnosis, treatment recommendation, autonomous decisioning, patient messaging, billing, orders, or device interpretation.
