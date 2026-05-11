# ChartNav One-Page Sales Deck

> Single-page leave-behind. Use as the email attachment after a
> discovery call. Private-practice variant — no SDVOSB / VA past
> performance reference (see the company / agency-partner /
> investor decks for the federal-credibility variant).
>
> **Phase 21C-follow-up.** Re-anchored around the ophthalmology
> clinic workflow layer positioning. The previous "5 strongest
> features" list is replaced with a 7-pillar list reflecting the
> Phase 20B / 20C / 21A / 21B product surfaces now shipped on
> main.

**Audience:** ophthalmology practice owner / clinical champion
who saw a discovery call and needs something to forward to a
partner.
**Purpose:** restate the offer in a single page so the buyer
can read it in 60 seconds.
**CTA / next step:** schedule the live fake-patient demo.

**Safe-claims contract.** Every line obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`
and the ophthalmology language guide at
`docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`.

---

## ChartNav — ophthalmology workflow layer for high-throughput eye clinics.

### Headline

**Built for eye-care lanes. Provider-reviewed at every step.**

ChartNav is an ophthalmology clinic workflow layer that connects
intake, technician workup, imaging review, retina/glaucoma
tracking, provider-reviewed documentation, review queues, and
internal coordination.

Clinical Signal Filtering at the documentation layer:
**Filters conversation. Captures findings. Builds the diagram.**

### The problem

Ophthalmology doctors move fast. Findings get buried in narrative
notes. Retinal findings live in free text, disconnected from the
OD/OS diagram. OCT, fundus, and visual field studies sit in
vendor viewers — disconnected from the encounter chart. Pre-visit
chart prep is manual. Patient-friendly summaries get written from
scratch every encounter.

A horizontal scribe app cannot model any of this.

### The solution — the eye-clinic lane cycle

Front desk → technician workup (VA / IOP / refraction /
dilation) → ancillary imaging review (OCT / fundus / VF /
biometry / external PDF metadata) → MD encounter → review /
sign-off → checkout / follow-up / internal coordination.

Every lane has a role-scoped dashboard. Every clinical artifact
is provider-reviewed. Nothing finalizes without a click.

### Clinical Signal Filtering — concrete example

Doctor says: *"Okay hold on… OD drusen in the macula… maybe OS
flame hemorrhage inferior."*

ChartNav separates:

- **Ignored chatter** — "Okay hold on"
- **Clinical finding** — "OD drusen in the macula"
- **Uncertain phrase** — "maybe OS flame hemorrhage inferior"
- **Proposed diagram annotation** — provider review required

### The 7 strongest product pillars

1. **Role-based clinic dashboards** — five role views (front
   desk, technician, doctor, reviewer, admin) over a shared
   structured work queue. Org-scoped, role-scoped.
2. **Structured data foundation** — patient segments, tags,
   problem list, clinic workflow templates and stages, work
   queue items, role view presets.
3. **Retina + glaucoma specialty tracking** — per-patient,
   per-eye structured tracking; provider-entered values for
   condition, severity, target IOP, latest IOP, cup-to-disc,
   RNFL, VF status, medication plan, progression risk.
   Plus retina injection event, IOP measurement, and visual
   field test history.
4. **Imaging metadata + review pipeline** — generic modality
   labels (OCT macula, OCT RNFL, fundus, widefield, VF 24-2 /
   10-2, biometry packet, external PDF). Metadata only — no
   image binaries.
5. **OD/OS retinal diagram + provider-reviewed annotations** —
   Clinical Signal Filtering proposes; the provider applies,
   edits, or rejects each proposal. Signed retinal artifacts
   are immutable; edits create an explicit fork.
6. **Provider-reviewed documentation** — transcript →
   extracted findings → AI draft → final note stepper, with the
   provider-review badge on every step.
7. **Internal coordination** — Chat with recipient selector
   targeting staff identities; conversation export. No
   patient-facing messaging surface.

### Provider-control safeguards

- Draft → reviewed → finalized — every transition is a click.
- Signed retinal artifacts are immutable in place; edits fork.
- Audit-friendly design with metadata-only logging — no
  clinical body text in audit detail.
- Per-organization isolation; cross-org requests return 404
  (no existence leak), not 403.

### What ChartNav is not

- Not a certified EHR replacement.
- Not HIPAA-certified — controlled-pilot path requires BAA,
  security review, production auth, approved hosting.
- Not autonomous diagnosis.
- Does not autofill IOP, refraction, or cup-to-disc ratio.
- Does not interpret OCTs, fundus photos, or visual fields.
- Does not select IOL power or anti-VEGF dosing.
- Does not grade diabetic retinopathy severity.
- Does not submit orders, referrals, claims, or imaging
  requests.
- Does not send patient messages automatically.
- Not a current vendor integration with Cirrus / Spectralis /
  Triton / Optos / IOLMaster / Humphrey / Topcon — those
  adapters are roadmap.

### Pricing snapshot

- **Per-provider:** $299–$499 / provider / month.
- **Per-practice flat:** $5,000 / practice / month (alternative
  to per-provider).
- **Pilot tier:** $10,000 flat for a 4–6 week controlled pilot.
- **Multi-practice annual discounts:** 2–4 = 10%; 5–9 = 15%;
  10+ enterprise.

### Pilot CTA

Schedule the live fake-patient demo. After the demo, we'll send
the pilot readiness packet (eight docs covering deployment,
security review, support runbook, success metrics, and the demo
→ pilot transition plan).

**Contact:** jeanmax@arivergroup.com · chartnavmd.com
