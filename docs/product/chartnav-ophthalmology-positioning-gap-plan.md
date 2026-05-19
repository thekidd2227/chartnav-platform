# ChartNav Ophthalmology Positioning Gap — Plan

> **Phase scope target:** Phase 21C (build), Phase 20A (this plan).
> **Type:** Planning only. No website changes, no deck rewrites,
> no production publish. This doc names the gaps + proposes the
> rewritten copy that a Phase 21C PR will land.

The repo audit confirms a recurring tension: **ChartNav's
ophthalmology depth is real, but the public-facing copy is more
horizontal than the product.** The result is buyers can't tell
from the pitch deck or website how specialty-deep the product
already is.

This plan stratifies the gap by surface, names exact phrases to
replace, and pins every ophthalmology-specific claim to the repo
evidence that supports it.

## What's already strong (preserve verbatim)

These three asset families are correctly ophthalmology-specific
and should not be touched in the rewrite:

1. **Clinical Signal Filtering narrative** (Investor Pitch
   Slide 5; Buyer Demo Slide 4)
   - Uses real retinal findings: "drusen", "OD/OS", "flame
     hemorrhage inferior"
   - Concrete example: *"Doctor says: 'Okay hold on… OD drusen
     in the macula… maybe OS flame hemorrhage inferior.'
     ChartNav separates: Ignored chatter / Clinical finding /
     Uncertain phrase / Proposed diagram annotation."*
   - **Verdict: preserve.**

2. **OD/OS retinal canvas + immutable signing contract**
   (Investor Pitch Slide 4; Buyer Demo Slide 6)
   - *"OD/OS retinal canvas is first-class — not bolted on."*
   - *"Signed retinal artifacts are immutable in place; edits
     create an explicit fork."*
   - **Verdict: preserve.**

3. **Forbidden-claims discipline across all decks** (Buyer Demo
   Slide 7; Elevator Pitch Slide 4)
   - Correctly avoids: HIPAA-compliant, certified EHR,
     autonomous diagnosis, automatic orders, automatic patient
     messaging, automatic billing/coding
   - Uses negative assertions throughout
   - **Verdict: preserve. Tighten with ophthalmology-specific
     non-goals (see Section 5 below).**

## Gap 1 — Subspecialty stratification

### Current state

- Buyer pitches mention **Retina** ~50 times across all decks
- Glaucoma + Cornea + Oculoplastics appear in the **website
  shot list** (Clinical tab collapsible groups) but NOT in
  buyer pitch decks
- **Cataract / Pediatric / Strabismus** appear NOWHERE in
  pitch decks
- Repo evidence: `clinicalShortcuts.ts` has 48 shortcuts across
  10 subspecialty groups including Glaucoma (6+), Cornea/anterior
  (6+), Oculoplastics (4+) — already shipped, not surfaced in
  marketing

### Proposed rewrite

| Surface | Add a "Choose your subspecialty mix" block |
|---|---|
| Homepage hero | Retina · Glaucoma · Cornea · Cataract · Oculoplastics · Pediatric chip strip — clicking one filters the example artifacts on the page |
| Investor pitch slide 3 | Replace single Retina example with a **3-tab "specialty depth" slide**: Retina (drusen / DME / wet AMD); Glaucoma (C/D ratio + target IOP + VF progression); Cornea (DED / keratoconus / post-DSEK) |
| Customer pitch template | Add `{{PRACTICE_SUBSPECIALTY_MIX}}` placeholder + per-subspecialty example cards; the agency partner / sales rep fills in which mix matches the prospect |
| Website Clinical tab shot | Already shows the 4 collapsible groups; add a hover-state shot showing pill cards inside each group (Phase 19I structure) |

### Per-subspecialty example anchored to repo evidence

| Subspecialty | Example (anchored to shipped clinicalShortcuts) | Status |
|---|---|---|
| Retina | "Acute PVD noted with vitreous syneresis. Negative Shafer sign. No retinal tear or retinal detachment on scleral depressed exam." (shortcut `pvd-01`) | ✅ shipped |
| Retina | OD/OS retinal canvas with drusen + flame hemorrhage symbols | ✅ shipped |
| Glaucoma | Cup-to-disc tracking + target IOP + RNFL/VF status | ⚠️ shortcuts shipped (Phase 31); structured tracking is Phase 21A |
| Cornea | "Dry eye" / "Keratitis" / post-DSEK shortcut bodies | ✅ shipped (Phase 31) |
| Cataract | Lens status + IOLMaster packet review | ❌ planned (Phase 21A) — mark as **future** in copy |
| Oculoplastics | "Chalazion" / "Blepharitis" / "Entropion" / "Ectropion" / "Ptosis" shortcuts | ✅ shipped |
| Pediatric / Strabismus | Alignment + amblyopia | ❌ planned (Phase 21A) — mark as **future** in copy |

## Gap 2 — Eye-clinic operational lane language

### Current state

The buyer pitches describe the **ChartNav product workflow**
(scribe → proposals → diagram → summary → brief → action queue)
but not the **eye-clinic operating cycle** (front desk → tech
workup → VA → IOP → refraction → dilation → ancillary imaging
→ MD encounter → recheck → injection → ASC scheduling →
checkout → provider sign-off → chart-closure lag).

### Proposed rewrite

Add a **new pitch slide** ("Eye-clinic workflow fit") to:

- Buyer Demo Deck (slide 5, between Clinical Signal Filtering
  and OD/OS retinal canvas slides)
- Customer Pitch Template
- Website "How ChartNav fits" section

Slide content:

```
Front desk          Technician          MD encounter        Sign-off
──────────          ──────────          ────────────        ────────
Today's schedule    VA / IOP            Pre-visit brief     Review queue
Check-in            Refraction          OD/OS canvas        AI-draft check
Demographics        Dilation            Clinical Signal     Diagram approval
Insurance prep      Imaging requested   Filtering           Note signature
Recall queue        Handoff to MD       Action queue        Chart closure
                                        Scribe lifecycle
                                        Note draft
```

Caption: *"ChartNav doesn't replace your scheduling, billing, or
PACS. It surfaces the right thing at the right point in the day
— from technician workup to provider sign-off — so the chart
closes before the patient leaves."*

## Gap 3 — Real ophthalmology artifact vocabulary

### Current state

Buyer pitches mention **VA, IOP, refraction** in demo source
text but not in the headline framing. They never mention
**OCT macula, OCT RNFL, HVF 24-2, HVF 10-2, fundus photo,
Optos widefield, IOLMaster, IRIS Registry, MIPS** — even though
the imaging pipeline plan (Phase 21B) names them all and the
shortcut bank already references C/D ratio, RNFL, VF.

### Proposed rewrite

Add an **artifact-vocabulary glossary** to:

- One-pagers folder (new doc: `chartnav-ophthalmology-artifact-glossary.md`)
- Customer pitch template (appendix slide)
- Website "What ChartNav understands" section

Glossary entries (each tagged with status):

| Artifact | Status | What ChartNav does today |
|---|---|---|
| OCT macula | Planned (Phase 21B) | Metadata + review-queue surface; clinician annotates findings on OD/OS canvas |
| OCT RNFL | Planned (Phase 21B) | Same metadata pipeline; flows into glaucoma_tracking after clinician review |
| HVF 24-2 / HVF 10-2 | Planned (Phase 21B) | PDF report import + clinician-tagged progression flag |
| Fundus photo (CFP) | Planned (Phase 21B) | Image storage + OD/OS canvas annotation flow |
| Optos widefield | Planned (Phase 21B) | Same as CFP |
| IOLMaster / biometry packet | Planned (Phase 21B) | Packet upload + clinician-driven IOL selection (**ChartNav does not select IOL power**) |
| IRIS Registry submission | Future / not in scope this year | — |
| MIPS measure attestation | Future / not in scope this year | — |
| OD/OS retinal canvas annotations | ✅ Shipped | First-class (drusen, DME, neovascularization, RD, lattice, etc.); 13 symbol types; immutable signing |
| Clinical-shortcut subspecialty bank (48 shortcuts) | ✅ Shipped | PVD, RD, Wet/Dry AMD, DR/DME, ERM/VMT, BRVO/CRVO, post-injection, Glaucoma, Cornea, Oculoplastics |
| AI scribe transcript → findings → AI draft → signed note | ✅ Shipped | Phase 17/18/19 |
| Quick-comment pad (50 phrases / 5 categories) | ✅ Shipped | HPI, Visual function, External/anterior, Posterior, Assessment/plan |

**Hard rule:** every "Planned" row stays **Planned** in copy
until the adapter or surface ships. **Never** claim a Cirrus,
Spectralis, Triton, Optos, IOLMaster, or other vendor
integration in marketing without the actual adapter in
`apps/api/app/integrations/`.

## Gap 4 — Show a specialty-correct chart fragment

### Current state

The website shot list shows ChartNav UI screenshots, but no
**static, fake, redacted homepage artifact** that a buyer can
read in 3 seconds and see "yes, this is an eye chart."

### Proposed rewrite

Add a static SVG/PNG (Phase 21C build, not committed in this
plan) homepage artifact with:

- **Patient line**: `Demo Patient · DOB Not available in demo · MRN PT-DEMO`
- **VA line**: `VA OD 20/40 · OS 20/20`
- **IOP couplet**: `IOP OD 16 · OS 14 (GAT, dilated)`
- **Lens status**: `Lens NS 1+ OD · NS 2+ OS`
- **Retinal canvas thumbnail**: OD/OS schematic with two
  symbol annotations (drusen macula OD, microaneurysm
  inferotemporal OD)
- **Auto-summary block**: 1-line retinal summary fed by
  `summarizeAnnotations()`
- **A/P one-liner**: `Dry AMD bilateral, monitor; recheck
  6 months. PVD OD, retinal-detachment precautions reviewed.`
- **Provider-review note**: `Reviewed by Dr. Carter · signed
  2026-05-09 · immutable`

**Constraints on this artifact:**
- Fake / demo data only
- No real PHI
- No real provider name or credential string
- "Demo" or "Sample" watermark visible
- Must match a screenshot you can actually capture from
  `?demo=1` mode (so it stays honest)

## Gap 5 — Tighten "what we don't do"

### Current non-goals (correctly safe but generic)

From Buyer Demo Slide 7:
- Does not diagnose autonomously
- Does not create orders
- Does not submit referrals
- Does not bill or code automatically
- Does not message patients automatically
- Not a certified EHR replacement
- Not real-PHI production without legal / security review

### Proposed ophthalmology-specific addition

Add a **second non-goals block** specifically scoped to
ophthalmology, signaling product depth:

- ChartNav does not autofill VA, IOP, or refraction. Tonometry,
  acuity, and refractive measurements are entered by the
  technician or clinician.
- ChartNav does not auto-grade diabetic retinopathy. Severity
  is clinician-selected.
- ChartNav does not auto-determine cup-to-disc ratio. C/D is
  clinician-entered.
- ChartNav does not auto-detect glaucoma progression from
  visual-field reports.
- ChartNav does not select IOL power. The IOLMaster packet is
  surfaced as a reviewable artifact; the clinician selects the
  IOL.
- ChartNav does not auto-dose anti-VEGF injections. Medication
  + dose are clinician-entered.
- ChartNav does not auto-prescribe dry-eye therapy.
- ChartNav does not auto-prescribe patching schedules or
  atropine for amblyopia.
- ChartNav does not finalize retinal annotations without
  explicit provider approval.
- ChartNav does not interface with ASC surgical scheduling
  systems.
- ChartNav does not transmit imaging files to external systems
  without explicit clinician + admin confirmation.

These show specialty literacy. A buyer reading this list
**knows** the team understands the day-to-day clinical work.

## Gap 6 — Future language support

### Plan but do not ship-claim

Future copy candidates for Phase 21C (mark explicitly as
**future / planned**):

- Spanish patient-friendly summaries
- Haitian Creole patient-friendly summaries
- Post-injection precautions in Spanish + Haitian Creole
- Post-cataract drop schedules in Spanish + Haitian Creole
- Front-desk language support for DC / Florida / New York
  clinic populations

**Rule:** each entry must be tagged "future" in copy until the
underlying language pack ships in `apps/web/src/i18n/` or
equivalent.

## Per-asset positioning gap table

| Current generic claim | Stronger ophthalmology-specific version | Source repo evidence | Status today | Risk if shipped as-is | Recommended doc/website update phase |
|---|---|---|---|---|---|
| "Provider-reviewed clinical workflow" | "Provider-reviewed ophthalmology workflow with first-class OD/OS retinal canvas" | `RetinalDrawingCanvas.tsx` + `chart_artifacts` immutable signing | True | Low | Phase 21C |
| "Clinical workflow" | "Eye-clinic workflow — front desk → technician → MD → sign-off" | `App.tsx` sidebar groups + Phase 20C dashboards | Partial | Medium (need Phase 20C dashboards before claim is "true") | Phase 21C copy after Phase 20C ships |
| "AI documentation" | "Provider-reviewed AI scribe with hashed-prompt governance log" | `ai_governance_log` table + `ScribeSessionPanel.tsx` | True | Low | Phase 21C |
| "Patient summaries" | "Patient-friendly visit summaries written from the signed note (clinician reviews before any patient handoff)" | `PatientSummaryPanel.tsx` + `chartnav-patient-friendly-summary.md` | True | Low | Phase 21C |
| "Review queue" | "Provider action queue — VA gaps, IOP rechecks, dilation gaps, pending OCT reads, sign-off backlog" | `ProviderActionItemsPanel.tsx` + Phase 20C reviewer dashboard | Partial | Medium | Phase 21C copy after Phase 20C ships |
| "Specialty practice" | "Ophthalmology-specific — Retina, Glaucoma, Cornea, Cataract, Oculoplastics" | `clinicalShortcuts.ts` 10 groups + Phase 21A tracking modules | Partial (4 groups in shortcuts; Cataract / Pediatric in Phase 21A plan) | Medium | Phase 21C copy after Phase 21A ships |
| "Documentation support" | "Subspecialty shorthand bank — PVD, RD, Wet/Dry AMD, DR/DME, ERM/VMT, BRVO/CRVO, post-injection, Glaucoma, Cornea, Oculoplastics" | `clinicalShortcuts.ts` 10 groups | True | Low | Phase 21C |
| "AI proposes annotations" | "Rule-based proposal engine matches findings text against 13 retinal symbol types; provider reviews and accepts/rejects each" | `services/retinal_proposals.py` + `RetinalProposalReview.tsx` | True | Low | Phase 21C |
| "Imaging" (if/when added) | "Imaging review pipeline — OCT / fundus / VF / biometry metadata; clinician reviews each study before annotation lands on the OD/OS canvas" | Phase 21B plan | **Future** | High if claimed before Phase 21B ships | Phase 21C only after Phase 21B ships |
| "Multi-clinic" (if/when added) | "Multi-location operating model with provider-location assignments, schedule blocks, operating hours" | Phase 22 plan | **Future** | High if claimed before Phase 22 ships | Phase 21C only after Phase 22 ships |

## What this plan deliberately does not propose

- ❌ **No** rewrite of the Phase 17B Clinical Signal Filtering
  banner — it's already correct
- ❌ **No** removal of the OD/OS canvas as the moat narrative
  — it's the strongest existing positioning
- ❌ **No** new claims of HIPAA / certified EHR / autonomous
  diagnosis / device integrations
- ❌ **No** customer / pilot / metric claims — those need
  separate legal-review approval
- ❌ **No** chartnavmd.com publish in this phase (or in Phase
  21C until explicit Jean-Max sign-off)

## Required tests (Phase 21C copy + claims)

- `bash scripts/check_commercial_claims.sh` must pass on every
  rewritten doc
- `bash scripts/check_website_claims.sh` must pass on every
  website-bound copy change
- The "Planned" / "Future" tag is present on every artifact
  vocabulary row that references unshipped capability
- No vendor name (Cirrus, Spectralis, Triton, Optos, IOLMaster)
  appears in shipped copy without an actual adapter
- Forbidden-phrase grep on docs/website + docs/decks: no
  "HIPAA compliant" / "certified EHR" / "autonomous diagnosis"
  / "automatic orders" / "automatic patient messaging" /
  "automatic billing"
- Subspecialty stratification: at minimum Retina + Glaucoma +
  Cornea + Oculoplastics named in any updated buyer-pitch
  slide that previously said "specialty practice"
- Eye-clinic operational language present in any updated
  "How ChartNav fits" surface

## Implementation handoff

Phase 21C is the **build phase** for these positioning changes.
This Phase 20A doc enumerates the gaps; the Phase 21C PR
will:

1. Update buyer-pitch decks under `docs/decks/`
2. Update website shot list under `docs/website/`
3. Add `docs/commercial/one-pagers/chartnav-ophthalmology-artifact-glossary.md`
4. Update homepage copy + add the static specialty chart fragment
5. Update non-goals language across all decks
6. Mark every "future" capability explicitly

Phase 21C **does not** publish to chartnavmd.com. Production
website update is gated on a separate explicit-approval phase.
