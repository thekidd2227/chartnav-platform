# ChartNav Buyer Objection Handling

> Common objections + safe responses. Read this before the demo.
> Pair with `docs/commercial/chartnav-approved-claims-language.md`.

---

## "Are you HIPAA compliant?"

**Answer:** *"We follow HIPAA-aware data-handling practices —
provider-in-the-loop, audit metadata-only, org isolation, no
patient-side delivery, no external-LLM PHI egress. Software
itself is not certified to HIPAA; covered entities and business
associates implement HIPAA safeguards. We require a Business
Associate Agreement before any real PHI is processed."*

**Don't say:** "HIPAA compliant," "HIPAA certified."

---

## "Is this an EHR?"

**Answer:** *"No. ChartNav is documentation and review support
that lives alongside your existing chart system. We sit next to
the EHR, not in front of it."*

**Don't say:** "We replace your EHR," "Certified EHR."

---

## "Does this diagnose?"

**Answer:** *"No. ChartNav surfaces structured chart context for
provider review. Your provider diagnoses; ChartNav does not."*

**Don't say:** "Autonomous diagnosis," "Automatic diagnosis,"
"AI diagnoses."

---

## "Does this create orders?"

**Answer:** *"No. There is no order-creation surface in the
product. The closest thing is the provider action queue, which
suggests review tasks only — never orders, never coding, never
referrals, never patient messages. Suggested → accepted →
completed; the provider clicks every transition."*

**Don't say:** "We can add order entry," "We can integrate with
ordering."

---

## "Does this integrate with Epic?"

**Answer:** *"We have a clean integration boundary — a bridge
layer with a FHIR-shaped adapter — but we don't ship a specific
Epic / Cerner / Athena / NextGen integration today. EHR-specific
integrations are pursued in dedicated phases. The pilot motion
runs ChartNav alongside your existing EHR, not as a replacement."*

**Don't say:** "Yes, fully integrated," "We're an Epic-certified
app."

---

## "Why ophthalmology first?"

**Answer:** *"Ophthalmology is specialty-specific by construction
— OD/OS retinal canvas, ophthalmology-flavored findings
vocabulary (drusen, dot/blot hemorrhage, flame hemorrhage,
microaneurysm, neovascularization), and a closed structured-note
vocabulary. We're not a primary-care SOAP-note generator. The
moat is specialty fit + provider-in-control safety contract."*

---

## "What's Clinical Signal Filtering and how is it different from a generic AI scribe?"

**Answer:** *"Doctors do not dictate in perfect templates.
Clinical Signal Filtering separates casual speech from clinical
findings, flags uncertainty, and proposes retinal diagram
annotations — the four classifications are ignored chatter,
clinical finding, uncertain phrase, and proposed diagram
annotation. The provider applies, edits, or rejects every
proposal before anything is saved or finalized. A generic AI
scribe writes a SOAP note from the audio; ChartNav does that
plus the ophthalmology-specific retinal-diagram workflow on top
— and surfaces uncertainty for explicit provider review."*

**Don't say:** "AI draws automatically," "AI decides," "AI
diagnosis," "automatic charting," "hands-free diagnosis,"
"hands-free charting," "guaranteed documentation accuracy."

---

## "Why not just use an AI scribe?"

**Answer:** *"AI scribes are specialty-agnostic. ChartNav is
ophthalmology-specific end-to-end: the retinal canvas, the
findings vocabulary, the action-queue clinical-language scan,
and the patient-friendly summary template are all tuned to
ophthalmology. The scribe is one of eight modules, not the whole
product."*

---

## "How do we pilot safely?"

**Answer:** *"Three modes: local (fake-data only, dev demo),
staging (fake-data only, buyer demo), controlled-pilot (real
PHI, only after a BAA and a security review of the deployment
posture). Pilot fee is $10,000 flat for a 4–6 week pilot.
Eight-doc pilot readiness packet covers deployment, admin
onboarding, security review, support runbook, demo-to-pilot
transition, success metrics, known limitations, and the
demo-to-pilot transition plan."*

**Reference:** `docs/pilot/chartnav-pilot-readiness-checklist.md`.

---

## "What happens with real PHI?"

**Answer:** *"Real PHI runs only in controlled-pilot mode. That
mode requires: a BAA executed; CHARTNAV_AUTH_MODE=bearer against
a real OIDC issuer; hosting on infrastructure the practice has
approved; an audit retention window agreed; Postgres backups
with tested restore; network egress confirmed; a logging
destination approved; incident response contacts in place;
optional pen test / vuln scan if the practice requires one. We
won't load real PHI into local or staging."*

**Reference:** `docs/pilot/chartnav-security-review-packet.md`.

---

## "Who reviews the outputs?"

**Answer:** *"Your provider. ChartNav is provider-reviewed at
every step: drafts wait for explicit review; finalize is a click;
signed retinal artifacts are immutable in place; edits to signed
artifacts create an explicit fork. The provider drives every
state transition."*

---

## "What about an external LLM?"

**Answer:** *"Today's generators are deterministic — regex /
aggregation over already-stored chart text. No external LLM is
enabled. The architecture leaves room for an LLM source under
the same provider-review contract — that is documented as
deferred and is not enabled."*

---

## "What's the price?"

**Answer:** *"Per-provider monthly subscription is $299–$499 per
provider per month. Per-practice flat tier is $5,000 per practice
per month — practices pick one or the other, not both. Pilot fee
is $10,000 flat for a 4–6 week pilot. Multi-practice annual
discounts are 10% for 2–4 practices, 15% for 5–9 practices, and
custom enterprise pricing for 10+ practices. Pilot fees are not
discounted unless approved case-by-case."*

---

## "Are you SDVOSB / DBE / MBE / SBE / HUBZone / NMSDC certified?"

**Answer (federal-healthcare-adjacent buyers only):** *"The
operating entity — Ariel's River Contracting Group, LLC,
dba ARCG Systems — is SDVOSB / HUBZone / DBE / MBE / SBE /
NMSDC certified. Past performance includes federal healthcare
contracting at the Mann-Grandstaff VA Medical Center in Spokane
WA. The certifications attach to the operating entity, not
specifically to the software product — frame that clearly when
relevant to a federal procurement path."*

**Don't say (private-practice ophthalmology buyers):** the
SDVOSB / federal certifications. They are real but not relevant
to a private-practice ophthalmology sales conversation, and
mentioning them invites confusion about whether the software
itself is certified.

---

## "Can you give me success metrics from existing pilots?"

**Answer:** *"We don't have N=many yet — we'd be presenting fake
metrics if we did, and we won't. The pilot success-metrics
template covers ten metrics with baseline / target / cadence
fields the practice fills in. Your specific numbers come from
your specific pilot."*

**Reference:** `docs/pilot/chartnav-pilot-success-metrics.md`.

---

## "What if the demo breaks?"

**Answer:** *"There's a fallback path. The pre-recorded
seven-clip plan is editorial-only in this repo, but if the local
stack fails, we walk you through the click path verbally and
follow up with a recorded session within 24 hours. The pilot
readiness packet is the part you can review independently of the
demo."*

---

## "Who's the team?"

**Answer:** *"Two co-founders — Jean-Max Charles (Founder of
ARCG Systems, Co-founder of ChartNav, President & Sales Director
of Ariel's River Contracting Group, LLC; SDVOSB operator) and
Maria Jackson (VP Operations, formerly Lead Scribe at McKesson,
10+ years in healthcare operations across ophthalmology). We're
recruiting advisors — target archetypes are a retina sub-
specialist, a practice administrator, and a healthcare-IT
operator."*
