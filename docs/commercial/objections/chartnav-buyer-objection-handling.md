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

---

## Phase 21C — ophthalmology specialty objections

The objection set below extends the existing list with
ophthalmology-specific concerns surfaced by the Phase 20B / 20C
/ 21A / 21B product depth merged into `main`. Pair with the
positioning language guide at
`docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`
and the homepage positioning doc at
`docs/website/chartnav-ophthalmology-homepage-positioning.md`.

### "Is this just another scribe?"

**Answer:** *"No. Scribing is one layer. ChartNav also connects
role-based clinic dashboards, a structured data layer with
patient segments / tags / problem list / work queues, retina and
glaucoma tracking, an imaging metadata + review pipeline,
provider-reviewed retinal diagrams, the NoteWorkspace
documentation flow, and an internal Chat for staff coordination.
The whole product is the ophthalmology clinic workflow layer —
documentation is one slice."*

**Don't say:** "We replace your scribe." "AI scribe."

---

### "Does ChartNav interpret OCTs or fundus photos?"

**Answer:** *"No. The imaging pipeline records study metadata
and review state — modality, eye, status, capture date, file
metadata, structured measurements the provider types in.
ChartNav stores the URI, not the binary. Provider interpretation
stays with the clinician."*

**Don't say:** "Auto-interpret OCT." "Auto-grade DR." "Auto-
measure central macular thickness." "Auto-measure RNFL
thickness."

---

### "Does ChartNav diagnose glaucoma progression or retina disease?"

**Answer:** *"No. ChartNav supports structured tracking and
review workflows. Diagnosis and management decisions remain
provider-authored. Cup-to-disc ratio, RNFL status, visual field
status, progression risk label — all provider-entered.
Severity, follow-up interval, provider assessment on the retina
side — all provider-entered."*

**Don't say:** "Auto-flag progression." "Auto-determine cup-to-
disc ratio." "Auto-grade DR severity."

---

### "Does ChartNav order tests, imaging, or referrals automatically?"

**Answer:** *"No. Labs / Orders Review is read-only. ChartNav
does not submit orders, referrals, or imaging requests. The
imaging pipeline records studies the practice has already
captured upstream — it is not an ordering system."*

**Don't say:** "Automatic orders." "Automatic referrals."
"Submit imaging request."

---

### "Does ChartNav select IOL power or anti-VEGF dosing?"

**Answer:** *"No. Biometry packets surface in the imaging
pipeline as metadata + review status — the provider selects the
IOL. Retina injection events record what the provider gave —
ChartNav does not recommend a drug or a dose."*

**Don't say:** "Auto-select IOL power." "Auto-recommend anti-VEGF
dose." "Auto-suggest medication."

---

### "Is ChartNav HIPAA compliant?"

**Answer:** *"ChartNav is not certified to HIPAA and is not
approved for real PHI by default. The product is built around
HIPAA-aware data-handling practices — provider-in-the-loop,
audit metadata-only, org isolation, no patient-side delivery,
no external-LLM PHI egress — but software itself is not
'certified to HIPAA' and we don't claim it is. A controlled PHI
pilot requires a Business Associate Agreement, security review,
production auth, approved hosting, backups, monitoring, vendor
review, incident contacts, and written practice approval."*

**Don't say:** "HIPAA compliant." "HIPAA certified."

---

### "Do you integrate with Cirrus / Spectralis / Triton / Optos / IOLMaster / Humphrey?"

**Answer:** *"Not today. ChartNav has an imaging metadata +
review foundation with generic modality labels — OCT macula,
OCT RNFL, fundus photo, widefield fundus, visual field 24-2 /
10-2, biometry packet, external PDF. Vendor-specific adapters
are on the roadmap; we will not claim an adapter exists unless
the code ships."*

**Don't say:** "We integrate with Cirrus / Spectralis / Triton
/ Optos / IOLMaster / Humphrey / Topcon" *unless* the adapter
actually ships.

---

### "Do you support cornea / cataract / oculoplastics / pediatric tracking?"

**Answer:** *"Cornea, cataract, oculoplastics, and pediatric are
all served today by the clinical shortcut bank — Dry eye,
Keratitis, Pterygium, Chalazion, Blepharitis, Entropion,
Ectropion, Ptosis, and so on are pinnable shortcuts the
provider applies during documentation. Structured tracking
tables for cornea, cataract pre-op, oculoplastics, and pediatric
are planned for later phases — the foundation merged into main
today is retina + glaucoma tracking + the imaging metadata
pipeline."*

**Don't say:** "We track cornea K-max today." "We have a
cataract pre-op packet." "MRD1 and levator are tracked." Those
are planned, not implemented.

---

### "Does ChartNav submit to IRIS Registry or report MIPS?"

**Answer:** *"Not today. Both are on the roadmap. ChartNav
does not currently submit to the IRIS Registry and does not
currently report MIPS metrics. We will say it the day the
adapter ships."*

**Don't say:** "We submit to IRIS Registry." "MIPS reporting
included."

---

### "Does the technician identity see the same data as the doctor?"

**Answer:** *"Role-based, but layered. Both can read clinical
data within their org. The technician can create imaging
studies, file metadata, measurement events, and retina injection
events — that's the operator-capture role. The technician
cannot mark a study reviewed, cannot create or patch a
retina/glaucoma tracking row. Reviewer is read-only across all
clinical specialty surfaces. Front desk has no access to the
clinical specialty surfaces at all."*

**Don't say:** "Everyone sees everything." "Technicians can sign
notes."

---

### "What happens if a real PHI screenshot accidentally lands on the demo stack?"

**Answer:** *"The demo stack is hard-wired to the fake-data
seed. Cross-org reads return 404 with no existence leak. Audit
events are metadata-only — provider_assessment, notes,
storage_uri, file_name, and measurement values are never
serialized into audit detail. If a screenshot accidentally
captures real PHI, the contract is to abort the capture, file
an incident, and reset the local stack."*

**Don't say:** "It can't happen." "Real PHI is fine on the
demo stack."
