# ChartNav Ophthalmology Homepage Positioning

> **Phase:** 21C — Ophthalmology specialty positioning upgrade.
> **Type:** Website/copy planning only. This document defines the
> recommended homepage narrative + subspecialty sections + safe
> "what ChartNav does not do" copy. **No production website is
> updated by this PR.** No `chartnavmd.com` change is published.
> No screenshots or media binaries are committed.

This document is the authoritative source for the
ophthalmology-specific homepage narrative. The website shot list
at `docs/website/chartnav-website-shot-list.md` lists which
ChartNav screen each section captures.

Every claim below is pinned to product proof merged into `main`
through the Phase 20–21B chain. Anything marked
**[future / planned]** is named so explicitly. Forbidden claims
(HIPAA compliant, certified EHR, autonomous diagnosis, automatic
orders / referrals / patient messaging, automatic
billing / coding, device-specific integrations) are not used.

---

## 1. Hero positioning

**Recommended hero headline — pick one. Do not lead with "replace
scribes" or with cost-cutting.**

### Option A *(recommended default — clinic operating system framing)*

> **ChartNav is the clinical workflow layer for ophthalmology
> practices.**
>
> Front desk to tech workup to imaging review to provider
> sign-off — built for eye-care lanes. Provider-reviewed at every
> step. Provider-controlled at every transition.

### Option B *(lane-cycle framing)*

> **From tech workup to imaging review to provider sign-off —
> built for eye-care lanes.**
>
> Role-based clinic dashboards, structured retina and glaucoma
> tracking, OD/OS retinal diagram review, and an imaging metadata
> pipeline — all in one provider-reviewed workspace.

### Option C *(documentation-first framing)*

> **Ophthalmology documentation, imaging review, and clinic
> coordination — in one provider-reviewed workspace.**
>
> Tech workup, VA / IOP / refraction context, OCT / fundus / VF
> review metadata, retina and glaucoma tracking, and structured
> documentation that stays under provider control.

### Hero subcopy — must reference these surfaces

The hero subcopy (one paragraph, 50–70 words) must reference:

- **Front desk** lane.
- **Technician workup** (VA / IOP / refraction / dilation).
- **Imaging review** (OCT macula, OCT RNFL, fundus, widefield,
  visual field 24-2 / 10-2, biometry, external PDF).
- **Retina / glaucoma tracking.**
- **Provider-reviewed documentation.**
- **Internal clinic coordination** (Chat with recipient
  selector).

Do **not** reference: billing, claims, insurance, patient
messaging, specific device vendors, HIPAA certification, or
"replaces scribes."

---

## 2. Subspecialty sections

The homepage should give buyers a single scroll path through six
ophthalmology subspecialties. Each section follows the same
template: buyer pain → ChartNav product proof → demo scene → safe
claim → future / planned items.

### 2.1 Retina

| Slot | Copy |
|---|---|
| **Buyer pain** | Injection-day chart closure is brutal. OCT macula, OCT RNFL, and fundus photos live in vendor viewers, disconnected from the encounter note. Retinal findings get re-typed every visit. |
| **ChartNav product proof** | Phase 21A retina tracking (per patient + eye condition, severity, follow-up interval, provider assessment) + Phase 21A retina injection events + Phase 21B imaging metadata pipeline (OCT macula / OCT RNFL / fundus / widefield) + the existing OD/OS retinal diagram canvas with provider-reviewed annotations. |
| **Demo scene** | Doctor opens an injection-day encounter, sees the retina tracking card (last OCT date, last fundus date, follow-up interval), reviews the imaging study list, opens the OD/OS retinal canvas to sign findings. |
| **Safe claim** | "Retina tracking foundation: provider-reviewed structured fields plus an imaging metadata pipeline. The OD/OS retinal diagram stays provider-controlled." |
| **Future / planned** | Spectralis / Cirrus / Triton / Optos device adapters; auto-population of injection cadence from prior history; CRT trending. |

### 2.2 Glaucoma

| Slot | Copy |
|---|---|
| **Buyer pain** | IOP trends, target IOP, cup-to-disc ratio, RNFL thinning, and visual field progression sit in 4 different surfaces. Reviewing a glaucoma patient takes 6 clicks across 3 systems. |
| **ChartNav product proof** | Phase 21A glaucoma tracking (per patient + eye type, target IOP, latest IOP, cup-to-disc, RNFL status, VF status, medication plan, progression risk label) + IOP measurement events + visual field test events + Phase 21B imaging pipeline (OCT RNFL, visual field 24-2 / 10-2 metadata). |
| **Demo scene** | Doctor opens a glaucoma follow-up encounter, sees the glaucoma tracking card, scans the IOP trend table, opens the visual field history, marks the encounter "reviewed." |
| **Safe claim** | "Provider-reviewed glaucoma tracking: target IOP, IOP trend table, VF history, RNFL status. ChartNav does not autofill IOP, does not autofill cup-to-disc ratio, does not select medications." |
| **Future / planned** | Humphrey HFA adapter; OCT RNFL thickness import; MD/PSD trending; progression risk scoring (planned as provider-reviewed only). |

### 2.3 Cornea / Anterior Segment

| Slot | Copy |
|---|---|
| **Buyer pain** | Dry-eye, keratitis, post-surgical cornea follow-ups all need anterior-segment templates that don't fight the doctor. |
| **ChartNav product proof** | Existing clinical shortcut bank (`clinicalShortcuts.ts`) ships Cornea / Anterior Segment shortcuts: Dry eye, Keratitis, Corneal abrasion, Epithelial defect, Pterygium, Anterior chamber depth — pinnable favorites the clinician applies during documentation. |
| **Demo scene** | Clinical / Ophthalmology tab → Cornea / Anterior Segment group → favorite a shortcut → it appears in the Documentation tab when the provider drafts the note. |
| **Safe claim** | "Cornea and anterior-segment review prompts the provider applies — never autofilled, never auto-charted." |
| **Future / planned** | Structured cornea tracking (K-max, thinnest pachymetry, post-DSEK pump function); IOLMaster biometry import. |

> **Do not claim a cornea-tracking table.** Phase 21A ships retina
> and glaucoma tracking only. Cornea structured tracking is
> planned, not implemented.

### 2.4 Cataract / Refractive

| Slot | Copy |
|---|---|
| **Buyer pain** | Cataract pre-op packets, biometry, and refraction prep are scattered across paper, vendor PDFs, and the EHR. |
| **ChartNav product proof** | Phase 21B imaging pipeline supports a **Biometry packet** modality and an **External PDF report** modality; both are metadata + review only — the practice's biometry device stays in place, ChartNav records the existence + review state of the packet. |
| **Demo scene** | Imaging tab → Biometry packet study → file metadata row → mark reviewed. |
| **Safe claim** | "Biometry packets and external PDF reports surface in ChartNav as metadata + review status. The provider reviews; ChartNav does not select IOL power." |
| **Future / planned** | Cataract pre-op packet template; surgical-day chart closure flow; ASC scheduling integration. |

### 2.5 Oculoplastics

| Slot | Copy |
|---|---|
| **Buyer pain** | Lid, lash, and adnexal complaints get under-coded because the chart didn't have structured prompts. |
| **ChartNav product proof** | Clinical shortcut bank ships Oculoplastics / Lids / Adnexa shortcuts: Chalazion, Blepharitis, Entropion, Ectropion, Ptosis. |
| **Demo scene** | Clinical tab → Oculoplastics group → favorite the relevant shortcut → it appears for the provider during documentation. |
| **Safe claim** | "Oculoplastics review prompts the provider applies — never autofilled." |
| **Future / planned** | Structured oculoplastics tracking with MRD1 / levator function fields. *Do not include MRD1 / levator in current copy — they are not in the current shortcut bank.* |

### 2.6 Pediatric / Strabismus *(future / planned)*

| Slot | Copy |
|---|---|
| **Buyer pain** | Pediatric vision exams + strabismus measurements need their own templates. |
| **ChartNav product proof** | Not yet implemented. Phase 21A retina/glaucoma tracking + Phase 21B imaging pipeline give the foundation. |
| **Demo scene** | None on `main`. Use the placeholder language. |
| **Safe claim** | None. Mark this section explicitly as **[future / planned]** on the live homepage. |
| **Future / planned** | Pediatric chart template; strabismus tracking (alignment measurements at distance / near, stereopsis); amblyopia treatment cadence tracking. |

---

## 3. Eye-clinic lane cycle section

Replace the current generic workflow language with this
ophthalmology lane cycle. Each lane is pinned to a shipped or
planned ChartNav feature.

```
Front desk
   ↓  role-based front-desk dashboard (Phase 20C)
   ↓  work queue: check-in / ready-for-workup / checkout
       (Phase 20B)
Tech workup
   ↓  role-based technician dashboard (Phase 20C)
   ↓  work queue: workup queue / VA / IOP / refraction /
       dilation / testing
   ↓  imaging pipeline: capture metadata + storage URI
       (Phase 21B)
Ancillary imaging review
   ↓  imaging pipeline: ready-for-review status
       (Phase 21B)
   ↓  retina + glaucoma tracking surfaces show the last
       OCT / fundus / VF dates (Phase 21A)
MD encounter
   ↓  role-based doctor dashboard: ready-for-MD + high-priority
       + sign-off (Phase 20C)
   ↓  NoteWorkspace draft → provider review → final note
   ↓  OD/OS retinal diagram canvas with provider-reviewed
       annotations
   ↓  retina + glaucoma tracking review (Phase 21A)
Review / sign-off
   ↓  role-based reviewer dashboard: notes awaiting review +
       AI draft review + audit exceptions (Phase 20C)
   ↓  imaging study "mark reviewed" (Phase 21B, admin /
       clinician only)
   ↓  retina/glaucoma tracking "mark reviewed" (Phase 21A)
Checkout / follow-up / internal coordination
   ↓  internal Chat with recipient selector (existing surface)
   ↓  no patient messaging — internal staff only
```

The homepage should render this as a horizontal step bar or a
vertical scroll diagram. **Do not** add automation arrows that
imply auto-routing without provider review.

---

## 4. Specialty-correct fake chart fragment plan

The homepage should include one ophthalmology-specific demo
artifact, rendered as a static visual (or a captioned screenshot
from the local fake-data stack). Required content:

- **Patient header** — fake name, fake MRN, fake DOB. Use the
  seeded `PT-1001 Morgan Lee` row to keep the demo artifact
  consistent with the rest of the materials.
- **VA line** — `OD 20/40 OS 20/30 sc` (fake but realistic for
  the seeded encounter).
- **IOP couplet** — `OD 18 / OS 16` (mmHg, Goldmann; fake).
- **Lens status** — `OD 2+ NS / OS 1+ NS` (fake).
- **OD/OS retinal diagram** — captured from the existing
  `RetinalDrawingCanvas` with 2 demo annotations on OD (drusen +
  flame hemorrhage inferior — both already in the shipped retinal
  symbol set).
- **Auto-summary block** — one paragraph drafted by ChartNav with
  the provider-review badge clearly visible.
- **One-line A/P** — provider-typed.
- **Provider-review note** — explicit "signed by Dr. Carter at
  10:14" timestamp pulled from the seeded encounter.

### Rules for the fake chart fragment

- **No real PHI** — the fragment must use seeded fake data only.
- **No claim of fully automated chart completion** — every block
  must show the provider-review badge.
- **No device names** — the OCT / fundus mentions on the same
  page reference the generic modality labels (`OCT macula`,
  `Fundus photo`), never `Cirrus` / `Spectralis` / `Triton` /
  `Optos`.

---

## 5. "What ChartNav does not do" section *(ophthalmology-specific)*

Replace the generic "we don't replace doctors" boilerplate with
ophthalmology-loaded negative assertions. These are accurate
contract statements anchored to the merged product.

- **ChartNav does not autofill IOP.** IOP is provider- or
  technician-entered, with explicit method (Goldmann / iCare /
  applanation).
- **ChartNav does not autofill refraction.**
- **ChartNav does not autofill cup-to-disc ratio.** The provider
  records cup-to-disc in glaucoma tracking; ChartNav does not
  measure it from any image.
- **ChartNav does not interpret OCT scans, fundus photographs,
  or visual fields.** The imaging pipeline records metadata + review
  state; provider interpretation stays with the clinician.
- **ChartNav does not select IOL power.** Biometry packets surface
  as metadata + review; the provider selects the lens.
- **ChartNav does not select anti-VEGF dosing.** Retina injection
  events record what the provider gave; ChartNav does not
  recommend a drug or dose.
- **ChartNav does not grade diabetic retinopathy severity.**
  Severity is a provider-entered field on retina tracking.
- **ChartNav does not finalize retinal annotations without
  explicit provider approval.** Proposals are reviewed → applied
  → signed; signed artifacts are immutable in place.
- **ChartNav does not send patient messages automatically.**
  ChartNav has no patient-facing messaging surface. Internal
  Chat is for staff coordination only.
- **ChartNav does not submit orders, referrals, claims, or
  imaging requests.** Labs / Orders Review is read-only.
- **ChartNav is not certified as an EHR and does not claim HIPAA
  compliance.** Real-PHI deployment requires BAA, security
  review, production auth, approved hosting, backups, monitoring,
  vendor review, incident contacts, and written practice approval
  (the Phase 20A.1 controlled-pilot readiness contract).

---

## 6. Pinning every section to product evidence

| Homepage section | Repo evidence |
|---|---|
| Hero: clinic workflow layer | Phase 20B `structured_data.py` + Phase 20C `role_dashboards.py` + Phase 21A `specialty_tracking.py` + Phase 21B `imaging_pipeline.py` |
| Lane cycle: front desk → tech → imaging → MD → review | Phase 20B `work_queue_items` + Phase 20C `RoleDashboard.tsx` |
| Retina section | Phase 21A `retina_tracking`, `retina_injection_events`; Phase 21B imaging modalities `oct_macula`, `fundus_photo`, `widefield_fundus` |
| Glaucoma section | Phase 21A `glaucoma_tracking`, `glaucoma_iop_measurements`, `glaucoma_visual_field_tests`; Phase 21B `oct_rnfl`, `visual_field_24_2`, `visual_field_10_2` |
| Cornea section | `apps/web/src/clinicalShortcuts.ts` Cornea group |
| Cataract section | Phase 21B `biometry_packet`, `external_pdf` modalities |
| Oculoplastics section | `apps/web/src/clinicalShortcuts.ts` Oculoplastics group |
| OD/OS retinal diagram | `apps/web/src/RetinalDrawingCanvas.tsx` + `services/chart_artifacts.py` + `services/retinal_proposals.py` |
| Auto-summary block | Phase 9 patient-summary surface |
| Internal Chat coordination | Existing Chat tab with recipient selector |

---

## 7. Out of scope (do not include on the homepage)

- HIPAA compliance claim.
- Certified EHR claim.
- Specific device vendor adapter claim (Cirrus / Spectralis /
  Triton / Optos / IOLMaster / Humphrey / Topcon).
- IRIS Registry submission claim.
- MIPS reporting claim.
- ASC scheduling integration claim.
- Multi-clinic scaling claim beyond "designed for".
- Real-PHI customer story (none exist; every story is a fake
  Morgan Lee demo until a pilot ships).
- Replaces scribes / replaces EHRs / replaces doctors framing.
- Cost-cutting headline.
