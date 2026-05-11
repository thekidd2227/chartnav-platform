# ChartNav Ophthalmology Demo Script

> **Phase:** 21C — Specialty positioning upgrade.
> **Audience:** ophthalmology practice owner / clinical champion
> / advisor / investor watching the live fake-patient demo.
> **Companion to:** `chartnav-clinical-workflow-demo-script.md`
> (the original demo script — still valid) and
> `chartnav-demo-click-path.md` (what to click).

The original `chartnav-clinical-workflow-demo-script.md` walks a
Phase 6 → 8 → 9 → 10 → 11 path. **This script extends it** with
the Phase 20B / 20C / 21A / 21B product surfaces. Read both. Run
either depending on the audience.

This script is the source of truth for **what to say** during a
demo of the new specialty surfaces. The script enforces:

- Every claim is anchored to merged product on `main`.
- Forbidden phrases never appear: HIPAA compliant, certified
  EHR, autonomous diagnosis, automatic orders / referrals /
  patient messaging / billing / coding, specific device-vendor
  integrations.
- Negative assertions are used where helpful.

---

## Demo data

- Org: `demo-eye-clinic` (seeded by `scripts_seed.py`).
- Patient: `PT-1001` Morgan Lee — fake by construction.
- Encounter: `encounter_id=1` — fake.
- Provider: Dr. Carter — fake (NPI seeded for the demo only).
- **Every name, MRN, DOB, NPI is fake.** Say "fake data only"
  out loud once during the cover.

---

## Demo flow — 9 stops

The full walkthrough is 8–12 minutes. Each stop has a one-line
**say** (the safe claim) and a **show** (what's on screen).

### Stop 1 — Cover + safety contract *(45 s)*

**Say:**
> "We'll walk through ChartNav for one fake patient — front desk
> to provider sign-off. ChartNav is the clinical workflow layer
> for ophthalmology practices. Every artifact is provider-
> reviewed. Every transition is provider-driven. No real patient
> data."

**Show:** Landing or top-bar with the `DEMO MODE` badge.

**Forbidden:** Do not lead with "AI scribe" or "saves money."

---

### Stop 2 — Role-based dashboard *(60 s)*

**Say:**
> "ChartNav now has five role-specific dashboards: front desk,
> technician, doctor, reviewer, admin. Each role sees only the
> queues they own. No HIPAA claim, no certification claim — just
> role-scoped, org-scoped views of the work queue."

**Show:** Sidebar → CORE → Dashboard. Switch identity to
`admin@chartnav.local` and use the **View as** selector to show:
- Front desk (today's schedule, check-in pending, ready for
  technician, checkout, follow-up).
- Technician (workup queue, imaging needed, dilation, testing,
  ready for doctor).
- Doctor (ready for MD, pre-visit briefs, imaging ready for
  review, documentation status, sign-off queue, high-priority
  clinical items).
- Reviewer (notes awaiting review, diagram proposal review, AI
  draft review, audit exceptions, blocked items).
- Admin (open queue items, overdue, unsigned notes, queue
  aging by status / priority / role / queue type).

**Repo evidence:** Phase 20C `RoleDashboard.tsx` +
`role_dashboards.py`.

**Forbidden:** Do not narrate this as "AI routes work" — the
queues are populated by structured rules, not autonomous
decisions.

---

### Stop 3 — Patient chart Overview *(45 s)*

**Say:**
> "Patient chart Overview surfaces the structured context the
> doctor needs in 5 seconds: tags, segments, problem list,
> recent encounters."

**Show:** Click the patient row → Overview tab. Reference
existing structured data (Phase 20B) — patient tags + segment
memberships + problem list rows.

**Forbidden:** Do not narrate this as a "complete chart" — it is
context that supports the clinical encounter.

---

### Stop 4 — Clinical / Ophthalmology *(60 s)*

**Say:**
> "Clinical tab houses ophthalmology subspecialty shortcuts —
> retina, glaucoma, cornea / anterior segment, oculoplastics,
> general. The provider pins favorites; the shortcut applies
> during documentation. ChartNav surfaces review prompts. It
> does not auto-diagnose."

**Show:** Clinical tab → scroll the subspecialty groups → pin a
favorite (e.g. *Drusen* under Retina / AMD / DME).

**Repo evidence:** `clinicalShortcuts.ts`, `quickComments.ts`,
`ClinicalTabbedWorkspace.tsx` Clinical tab.

**Forbidden:** Do not claim the shortcuts auto-write the note.

---

### Stop 5 — Retina + glaucoma specialty tracking *(75 s)*

**Say:**
> "Phase 21A added retina and glaucoma tracking. Retina tracking
> per patient and per eye: condition, severity, last OCT date,
> last fundus date, follow-up interval, provider assessment.
> Retina injection event history. Glaucoma tracking with target
> IOP, latest IOP, cup-to-disc ratio, RNFL status, visual field
> status, medication plan, progression risk — all provider-
> entered. IOP measurement events. Visual field test events.
> ChartNav does not autofill IOP, does not autofill cup-to-disc
> ratio, does not select medications."

**Show:** Clinical tab → Specialty Tracking panel at the top.
- Retina section: existing tracking row + "Mark reviewed."
- Glaucoma section: existing tracking row + IOP measurements
  table + visual field tests table.

**Repo evidence:** Phase 21A `specialty_tracking.py` +
`SpecialtyTrackingPanel.tsx`.

**Forbidden:** Do not claim the panel grades severity. Do not
claim it recommends medications.

---

### Stop 6 — Imaging pipeline *(60 s)*

**Say:**
> "Phase 21B added the imaging metadata + review pipeline.
> Generic modality labels: OCT macula, OCT RNFL, fundus photo,
> widefield fundus, visual field 24-2 / 10-2, biometry packet,
> external PDF. ChartNav stores file metadata, not binaries. The
> route layer rejects `data:` URIs. We do not integrate with
> specific devices today. We do not interpret OCT scans, fundus
> photographs, or visual fields."

**Show:** Imaging tab → ImagingPipelinePanel.
- Click a study in the list (left column).
- Show file metadata table (right column).
- Show measurements table.
- For an admin / clinician identity, click "Mark reviewed."

**Repo evidence:** Phase 21B `imaging_pipeline.py` +
`ImagingPipelinePanel.tsx`.

**Forbidden:** Do not name specific vendors (Cirrus / Spectralis
/ Triton / Optos / IOLMaster / Humphrey / Topcon). Do not claim
auto-interpretation.

---

### Stop 7 — Documentation (NoteWorkspace) *(90 s)*

**Say:**
> "Documentation tab walks the transcript → extracted findings →
> AI draft → final note stepper. Every step is provider-
> reviewed. Generated drafts are explicitly labeled with the
> provider-review badge. When the provider edits a generated
> draft, the badge flips to 'provider (edited)'. Signed notes
> are immutable in place."

**Show:** Documentation tab → walk the stepper for the seeded
encounter. Make a small edit to flip the badge.

**Repo evidence:** `NoteWorkspace.tsx`, `ScribeSessionPanel.tsx`.

**Forbidden:** Do not narrate this as "auto-generates the note"
without saying provider review is required.

---

### Stop 8 — Chat (internal coordination) *(45 s)*

**Say:**
> "ChartNav has an internal-only Chat with a recipient selector.
> No patient-facing messaging surface. The recipient selector
> targets staff identities; selected conversations can be
> exported. This is internal clinic coordination, not patient
> communication."

**Show:** Chat tab → recipient selector → quick demo of an
internal chat note → export.

**Forbidden:** Do not call it "patient messaging" — it isn't.

---

### Stop 9 — Safety close *(45 s)*

**Say (verbatim block):**
> "What ChartNav does not do:
> ChartNav does not autofill IOP, refraction, or cup-to-disc
> ratio. ChartNav does not interpret OCTs, fundus photos, or
> visual fields. ChartNav does not select IOL power or
> anti-VEGF dosing. ChartNav does not grade diabetic retinopathy
> severity. ChartNav does not finalize retinal annotations
> without explicit provider approval. ChartNav does not send
> patient messages automatically. ChartNav does not submit
> orders, referrals, claims, or imaging requests. ChartNav is
> not certified as an EHR and does not claim HIPAA compliance.
> A controlled pilot requires a Business Associate Agreement
> and security review before any real PHI is processed."

**CTA:**
> "If you want to evaluate a controlled fake-patient pilot, the
> next step is a security review conversation."

---

## Per-audience tailoring

| Audience | Stops to emphasize | Stops to compress |
|---|---|---|
| Ophthalmology practice owner | 2 (dashboards), 5 (tracking), 6 (imaging), 9 (safety) | 7 (documentation — they know notes) |
| Clinical champion (MD) | 5 (tracking), 6 (imaging), 7 (documentation) | 8 (chat) |
| Practice administrator | 2 (dashboards), 8 (chat), 9 (safety) | 7 (documentation) |
| Advisor / investor | 1 (cover), 2 (dashboards), 5 (tracking), 6 (imaging), 9 (safety) | 3 (overview), 4 (clinical) |
| Technician | 2 (technician dashboard), 4 (shortcuts), 5 (tracking — measurement events), 6 (imaging) | 9 (safety; technicians know the limits) |

---

## Forbidden surface during the demo

- Do not switch to staging or controlled-pilot data.
- Do not capture a clip while the screen displays anything that
  could be construed as real PHI.
- Do not narrate any of the forbidden phrases from
  `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.
- Do not promise device adapter availability.
- Do not promise IRIS Registry / MIPS integration.
