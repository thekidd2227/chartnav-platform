# ChartNav Deck Master Kit

> Authoritative master narrative for every ChartNav deck. Pair
> with `chartnav-approved-claims-language.md` (banned vs. allowed
> phrasing) and the brand-guidelines deck (visual style).

---

## Approved master narrative

> **One sentence:** ChartNav is an ophthalmology-specific clinical
> workflow assistant — provider-reviewed at every step.
>
> **Three sentences:** ChartNav helps ophthalmology providers
> spend less time on charts and more time on patients. The
> product surfaces a structured note, an OD/OS retinal canvas, a
> patient-friendly summary, and a pre-visit brief — and a
> provider review queue that lists review tasks only. Every
> clinical artifact is provider-reviewed; ChartNav does not
> diagnose, create orders, send referrals, bill, or message
> patients automatically.
>
> **Six sentences:** ChartNav is built and operated by Ariel's
> River Contracting Group, LLC, dba ARCG Systems — a Maryland-
> based Service-Disabled Veteran-Owned Small Business with
> federal healthcare past performance at the Mann-Grandstaff VA
> Medical Center, Spokane WA. The product is ophthalmology-
> specific by construction: an OD/OS retinal canvas,
> ophthalmology-flavored findings vocabulary, and a closed
> structured-note model. Eight modules run in production code:
> AI scribe session lifecycle, findings-to-retinal-diagram
> proposal review, OD/OS retinal drawing canvas, patient-friendly
> summary draft, pre-visit clinical brief, provider action
> review queue, guided demo mode, and a pilot-readiness package.
> The provider drives every transition. Pricing is $299–$499 per
> provider per month, $5,000 per practice per month flat, or
> $10,000 flat for a 4–6 week controlled pilot. Real PHI requires
> a BAA and a security review before deployment.

Use the one-, three-, or six-sentence version depending on the
audience and the time you have.

---

## Buyer personas

### Persona 1 — Ophthalmology private-practice owner

- **Profile:** practice owner / managing partner, 2–10 providers,
  single or small multi-location.
- **Cares about:** documentation friction, retinal-finding
  workflow, pre-visit chart prep, staff time, compliance posture.
- **Doesn't care about:** investor metrics, fundraising stage,
  partner economics.
- **Right deck:**
  `chartnav-sales-deck.md` (11 slides) or
  `chartnav-long-sales-pitch-deck.md` (15 slides) plus
  `chartnav-customer-pitch-deck-template.md` for the customized
  proposal. Use `chartnav-one-page-sales-deck.md` as the
  follow-up email attachment. For the live demo itself use
  `chartnav-buyer-demo-deck.md` — never the operator demo deck
  in front of a buyer.

### Persona 2 — Practice security / compliance owner

- **Profile:** in-house compliance lead or IT director.
- **Cares about:** BAA terms, audit posture, hosting decisions,
  authentication mode, backup / restore.
- **Doesn't care about:** sales pitch, fundraising, investor
  metrics.
- **Right deck:** none — instead hand them
  `docs/pilot/chartnav-security-review-packet.md` and
  `docs/pilot/chartnav-pilot-deployment-guide.md`.

### Persona 3 — Investor / advisor

- **Profile:** angel investor, seed-stage VC associate, or
  commercial advisor.
- **Cares about:** market, moat, build proof, traction,
  fundraising stage, milestones.
- **Doesn't care about:** click-by-click product mechanics
  (those go in the demo).
- **Right deck:**
  `chartnav-investor-pitch-deck.md` (15 slides) plus
  `chartnav-financial-fundraising-deck.md` (8 slides
  supplement). Open with the elevator-pitch deck for cold intros.
  For the live demo segment use `chartnav-buyer-demo-deck.md`.

### Persona 4 — Federal-healthcare-adjacent buyer (VA, federal
contracting)

- **Profile:** federal-healthcare-related practice or program
  evaluating clinical workflow tools.
- **Cares about:** SDVOSB certification, federal past performance,
  HUBZone / DBE / MBE / SBE / NMSDC certifications carried by the
  operating entity, security posture.
- **Right deck:** `chartnav-company-deck.md` (slide 8 federal
  credibility track is appropriate here) or
  `chartnav-agency-partner-pitch-deck.md` (if going through a
  partner channel).

### Persona 5 — Agency / referral partner

- **Profile:** advisor or agency with existing ophthalmology
  practice relationships.
- **Cares about:** the trust transfer, the safe phrasing list,
  the boundaries.
- **Doesn't care about:** the product mechanics (those go in the
  practice's demo).
- **Right deck:** `chartnav-agency-partner-pitch-deck.md` (7
  slides). Partner economics conversations happen 1:1.

---

## Reusable slide language

### Cover line (every deck)
> *"ChartNav — provider-reviewed clinical workflow for
> ophthalmology."*

Optional sub-line on internal / federal-aimed decks:
> *"Operated by Ariel's River Contracting Group, LLC, dba ARCG
> Systems · Maryland-based."*

### Safety line (every deck — read aloud)
> *"Provider-reviewed workflow support. ChartNav does not
> diagnose, create orders, send referrals, bill, or message
> patients automatically."*

### Workflow stage line (every deck that lists modules)
> *"Seven explicit steps. The provider drives every transition.
> Scribe → proposals → diagram → summary → brief → action queue
> → guided demo."*

### Clinical Signal Filtering — the prime feature line (every buyer-facing deck)
> *"Filters conversation. Captures findings. Builds the diagram."*

**Supporting copy** (every buyer-facing deck must use this language
or a faithful paraphrase):

> Doctors do not dictate in perfect templates. ChartNav separates
> casual speech from clinical findings, flags uncertainty,
> proposes retinal diagram annotations, and keeps the provider in
> control.

**Concrete example** (every buyer-facing deck should include this
or an equivalent):

> Doctor says:
>
> *"Okay hold on… OD drusen in the macula… maybe OS flame
> hemorrhage inferior."*
>
> ChartNav separates:
>
> - **Ignored chatter:** "Okay hold on"
> - **Clinical finding:** "OD drusen in the macula"
> - **Uncertain phrase:** "maybe OS flame hemorrhage inferior"
> - **Proposed diagram annotation:** provider review required

The provider applies, edits, or rejects every proposal before
anything is saved or finalized.

### Pricing block
> *"$299–$499 per provider per month, OR $5,000 per practice per
> month flat. Pilot: $10,000 flat for a 4–6 week controlled
> pilot. Multi-practice annual discounts: 2–4 = 10%; 5–9 = 15%;
> 10+ = enterprise."*

### "What ChartNav is not" block (private-practice version)
> *"Not a certified EHR replacement. Not autonomous diagnosis.
> Not automatic orders, coding, referrals, or patient messaging.
> Not real-PHI production without legal / security review."*

### "What ChartNav is not" block (federal-adjacent version)
Same as above plus:
> *"SDVOSB certification applies to the operating entity, not
> directly to the software product."*

### Contact CTA block
> *"Demo request: jeanmax@arivergroup.com · chartnavmd.com."*

---

## Approved feature names

Use these exact strings for module names across every deck:

- Clinical Signal Filtering (prime differentiator — surfaces in
  scribe + proposals + diagram together)
- AI scribe session lifecycle
- Findings-to-retinal-diagram proposal review
- OD/OS retinal drawing canvas
- Patient-friendly summary
- Pre-visit clinical brief
- Provider action review queue
- Guided demo mode
- Pilot-readiness package

---

## Approved CTAs

Pick one per deck:

- "Request a fake-patient demo" (primary, hero)
- "Discuss a controlled ophthalmology pilot" (mid-funnel)
- "Review the provider-in-control workflow" (mid-funnel)
- "See how the workflow works" (top-of-funnel; in-page anchor)
- "Schedule the live fake-patient demo" (close)

---

## Banned claims

See `chartnav-approved-claims-language.md` for the full list and
the substitution table.
