# ChartNav Ophthalmology Positioning — Language Guide

> **Phase:** 21C — Specialty positioning upgrade.
> **Type:** Commercial / deck language reference only. Companion
> to `docs/commercial/chartnav-approved-claims-language.md`.
> Sharper than the master claims list because it pins
> ophthalmology-specific phrasing to the merged product.

Read this before editing any deck, sales email, website draft,
investor narrative, agency pitch, or demo script. The goal is to
**stop sounding like a generic horizontal scribe app** and to
sound like what the product actually is on `main`: an
**ophthalmology clinic workflow layer**.

The merged product proof now includes:

- **Phase 20B** — structured data layer (segments, tags, problem
  list, clinic workflow templates + stages, work queue, role
  view presets).
- **Phase 20C** — role-based clinic dashboards (front desk,
  technician, doctor, reviewer, admin) with PHI-safe payload
  compaction.
- **Phase 21A** — retina + glaucoma specialty tracking (5
  tables) with measurement-event roles and metadata-only audit.
- **Phase 21B** — imaging metadata + review pipeline (3 tables)
  with generic modality labels and a binary-payload rejection
  contract.
- The existing OD/OS retinal diagram, retinal proposal review,
  NoteWorkspace draft pipeline, ScribeSessionPanel, internal
  Chat with recipient selector, Clinical Signal Filtering, and
  patient-summary / pre-visit-brief / provider-action-items
  surfaces.

---

## 1. Approved ophthalmology phrasing

These phrases are safe in any buyer-facing surface. They are
anchored to merged product.

### Product positioning

- "Ophthalmology clinic workflow layer."
- "Ophthalmology-specific by construction."
- "Built for eye-care lanes."
- "Front desk to tech workup to imaging review to provider
  sign-off."
- "Role-based clinic dashboards."
- "Structured retina and glaucoma tracking foundation."
- "Imaging metadata + review pipeline."
- "OD/OS retinal diagram with provider-reviewed annotations."
- "Provider-controlled at every transition."
- "Internal clinic coordination" *(internal Chat, not patient
  messaging)*.

### Workflow / clinical-lane language

- "Front desk lane."
- "Technician workup lane."
- "VA / IOP / refraction / dilation workup."
- "Ancillary imaging review."
- "MD encounter."
- "Sign-off queue."
- "Checkout / follow-up / internal coordination."
- "Provider-reviewed clinical workflow."
- "Provider review queue."
- "Lane-cycle time" *(only when describing the dashboard
  surface)*.

### Specialty tracking language

- "Retina tracking foundation."
- "Per-patient, per-eye review state."
- "Retina injection event history" *(metadata only — what the
  provider gave, not what ChartNav recommends)*.
- "Glaucoma tracking foundation."
- "IOP trend table" *(provider- or technician-entered values)*.
- "Visual field history" *(metadata only)*.
- "Target IOP, latest IOP, cup-to-disc ratio, RNFL status,
  visual field status, medication plan, progression risk
  label — all provider-entered."

### Imaging pipeline language

- "Imaging metadata pipeline."
- "Generic modality labels: OCT macula, OCT RNFL, fundus photo,
  widefield fundus, visual field 24-2, visual field 10-2,
  biometry packet, external PDF."
- "File metadata only — ChartNav does not store image
  binaries."
- "Storage URI references the practice's existing storage
  backend."
- "`data:image/...;base64,...` URIs are rejected by the route
  layer."
- "Mark reviewed" *(admin / clinician only)*.

### Role-based dashboard language

- "Front-desk dashboard: today's schedule, check-in pending,
  ready for technician, checkout, follow-up."
- "Technician dashboard: workup queue, imaging needed,
  dilation, testing, ready for doctor."
- "Doctor dashboard: ready for MD, pre-visit briefs, imaging
  ready for review, documentation status, sign-off queue,
  high-priority clinical items."
- "Reviewer dashboard: notes awaiting review, diagram proposal
  review, AI draft review, audit exceptions, blocked items."
- "Admin dashboard: open queue items, overdue items, unsigned
  notes, queue aging by status / priority / role / queue
  type."

### Safety / control language

- "Provider-reviewed."
- "Provider drives every transition."
- "Audit metadata-only."
- "Cross-organization access returns 404." *(no-existence-leak
  invariant)*
- "Signed retinal artifacts are immutable in place."
- "Edits to a signed artifact create an explicit fork."

### Pilot / readiness language

- "Controlled pilot."
- "Fake-patient demo."
- "BAA required before any real PHI is processed."
- "Designed to support HIPAA-aware data-handling practices."
  *(NOT "HIPAA compliant.")*

---

## 2. Avoid / forbidden phrasing

The following phrases must not appear in any buyer-facing
surface. The `scripts/check_commercial_claims.sh` and
`apps/web/src/test/CommercialDeckClaims.test.tsx` are
authoritative; this list is the human-readable version.

### Generic / horizontal framing

- "Replaces scribes."
- "Replaces your scribe."
- "AI scribe."
- "Generic AI assistant."
- "Horizontal documentation tool."
- "Save money on scribes." *(cost-cutting hero — wrong
  emphasis)*
- "Workflow automation." *(too generic — use "role-based
  clinic dashboards" or "lane cycle" instead)*

### Unsupported certifications / status claims

- "HIPAA compliant."
- "HIPAA certified."
- "SOC 2 certified."
- "Certified EHR."
- "Production-ready for PHI."
- "Real patient data ready."

### Unsupported clinical-decision claims

- "Autonomous diagnosis."
- "Automatic diagnosis."
- "AI diagnoses."
- "Auto-grade diabetic retinopathy."
- "Auto-grade DR severity."
- "Auto-interpret OCT."
- "Auto-interpret fundus."
- "Auto-determine cup-to-disc ratio."
- "Auto-measure central macular thickness."
- "Auto-measure RNFL thickness."
- "Auto-select IOL power."
- "Auto-select anti-VEGF dosing."
- "Auto-recommend glaucoma medication."

### Unsupported workflow-automation claims

- "Automatic orders."
- "Automatic referrals."
- "Automatic patient messaging."
- "Send to patient." *(no patient-facing surface)*
- "Automatic billing."
- "Automatic coding."
- "Claims submission."
- "Insurance handling."
- "Payment handling."
- "Copay / co-pay / deductible / EOB / remit."
- "CPT auto-suggest."
- "ICD-10 auto-suggest."

### Unsupported device / vendor integrations

The brand names below are forbidden in any
"we-integrate-with" form. Generic modality labels are fine.

- Cirrus / Spectralis / Triton / Optos / IOLMaster / Humphrey
  / Topcon / Octopus *(any "we integrate with X" claim
  without a shipped adapter)*
- IRIS Registry submission *(not implemented)*
- MIPS reporting *(not implemented)*
- ASC scheduling integration *(not implemented)*

### Unsupported subspecialty claims

- "Cornea tracking" *(Phase 21A ships retina + glaucoma only;
  cornea is shortcut bank only — see homepage doc Section 2.3)*
- "Oculoplastics tracking with MRD1 / levator" *(MRD1 / levator
  not in the shortcut bank — do not name them)*
- "Pediatric / strabismus tracking" *(not implemented)*
- "Cataract pre-op packet" *(planned only)*

---

## 3. Future / planned phrasing rules

When a forward-looking claim is unavoidable, follow these rules:

1. **Tag it explicitly:** `[future / planned]`,
   `[planned for a later phase]`, or "Roadmap:".
2. **Anchor it to a roadmap phase number** if known
   (Phase 21B+, Phase 22, etc.).
3. **Never imply availability today.** "We plan to integrate
   with Cirrus" is fine; "We integrate with Cirrus" is not.
4. **Never promise a date** unless an internal commitment
   exists.

Approved templates:

> "ChartNav has an imaging metadata + review foundation today.
> Vendor-specific OCT adapters are planned for a later phase."

> "ChartNav records retina injection events today. CRT trending
> from OCT exports is on the roadmap."

> "ChartNav supports provider-reviewed glaucoma tracking today.
> Humphrey HFA import is planned, not implemented."

---

## 4. Specialty examples — safe phrasing snippets

### Retina

- ✅ "Injection-day chart closure: open the retina tracking
  card, review the imaging study list, sign findings on the
  OD/OS retinal canvas."
- ✅ "Retina tracking captures condition, severity,
  follow-up interval, and provider assessment — provider-
  authored."
- ❌ "Auto-grade DR severity."
- ❌ "Auto-suggest anti-VEGF dose."

### Glaucoma

- ✅ "Glaucoma follow-up: target IOP, latest IOP, cup-to-disc
  ratio, RNFL status, VF status, progression risk — all
  provider-entered."
- ✅ "Visual field history shows test type, reliability, and
  the provider's progression flag."
- ❌ "Auto-determine cup-to-disc ratio from disc photo."
- ❌ "Auto-flag glaucoma progression."

### Imaging

- ✅ "Generic modality labels: OCT macula, OCT RNFL, fundus
  photo, widefield fundus, visual field 24-2, visual field
  10-2, biometry packet, external PDF."
- ✅ "File metadata only — ChartNav stores the URI, not the
  binary."
- ❌ "We integrate with Cirrus / Spectralis / Triton / Optos /
  Humphrey."
- ❌ "Auto-interpret the OCT."

### Cornea / cataract / oculoplastics / pediatric

- ✅ "Cornea / anterior-segment shortcuts the provider applies
  during documentation."
- ✅ "Biometry packet metadata captures the existence + review
  state of the packet."
- ❌ "We select the IOL."
- ❌ "We track cornea K-max / pachymetry / DSEK pump function
  today." *(planned only)*

---

## 5. Negative-assertion bank

These are the cleanest one-liners for "what ChartNav does not
do." Reuse them verbatim in decks, the homepage, the demo
script, and the objection responses.

- ChartNav does not autofill IOP.
- ChartNav does not autofill refraction.
- ChartNav does not autofill cup-to-disc ratio.
- ChartNav does not interpret OCTs, fundus photos, or visual
  fields.
- ChartNav does not select IOL power.
- ChartNav does not select anti-VEGF dosing.
- ChartNav does not grade diabetic retinopathy severity.
- ChartNav does not finalize retinal annotations without
  explicit provider approval.
- ChartNav does not send patient messages automatically.
- ChartNav does not submit orders, referrals, claims, or
  imaging requests.
- ChartNav has no patient-facing messaging surface.
- ChartNav is not certified as an EHR.
- ChartNav does not claim HIPAA compliance.

---

## 6. Per-deck guidance

This guide is the master. Each existing deck's update is
captured in the Phase 21C PR alongside it. Decks where the
ophthalmology positioning upgrade matters most:

| Deck | Phase 21C focus |
|---|---|
| `chartnav-investor-pitch-deck.md` | Replace the single Retina anchor slide with the 5-surface specialty proof (Phase 20C + 21A + 21B + OD/OS canvas + Chat). |
| `chartnav-buyer-demo-deck.md` | Add lane-cycle slide (Section 3 of the homepage doc) + per-subspecialty mix slide. |
| `chartnav-one-page-sales-deck.md` | Update the headline + bullet list to mention role dashboards / retina + glaucoma tracking / imaging pipeline. |
| `chartnav-customer-pitch-deck-template.md` | Add the `{{PRACTICE_SUBSPECIALTY_MIX}}` placeholder + per-subspecialty example block. |
| `chartnav-sales-deck.md` | Add lane cycle + safety-close negative assertions. |
| `chartnav-demo-deck.md` | Walk Phase 20C dashboards + Phase 21A tracking + Phase 21B imaging panel. |
| `chartnav-operator-demo-deck.md` | Add the operator click path for the 3 new surfaces. |
| `chartnav-elevator-pitch-deck.md` | Tighten the 30-second pitch around "ophthalmology clinic workflow layer." |
| `chartnav-product-roadmap-deck.md` | Move Phase 20B / 20C / 21A / 21B from "planned" to "shipped"; mark Phase 22 / 23 as planned. |

> **Implementation note:** This PR does not rewrite every deck's
> body text. The Phase 21C deliverable is the **language
> contract** + the **homepage positioning** + the **demo script**
> + the **objection handling additions**. Deck-by-deck body
> rewrites that exceed the contract should ship in a follow-up
> docs PR so reviewers can compare deck-by-deck.

---

## 7. Validation

Every phrase in this guide is checked against:

- `scripts/check_commercial_claims.sh` — pre-merge sanity
  check.
- `scripts/check_website_claims.sh` — pre-merge sanity check.
- `apps/web/src/test/CommercialDeckClaims.test.tsx` — the
  authoritative vitest suite.
- `apps/web/src/test/WebsiteProofUpgrade.test.tsx` — landing
  page safe-claims contract.

If a new banned phrase is added to this guide, also add it to
the vitest suites and the bash scripts in the same PR.
