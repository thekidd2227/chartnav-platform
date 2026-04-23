# Phase C — Buyer Objection Map

## 1. Problem solved
Sales conversations in ophthalmology IT are short and skeptical. The
buyer is a physician-owner, a clinic operator, an MSO admin, or a
revenue-cycle stakeholder, and every one of them has been burned by
a vendor promise that did not survive contact with a real schedule.
A pre-built objection map — with the honest answer, today's proof,
and the next-release strengthener — means the call does not rely on
improvisation.

## 2. Current state
Objection handling today is verbal and inconsistent. No written
playbook exists. Sales has relied on product-led demos. This document
consolidates the fourteen objections most likely to appear and the
ChartNav-aligned response to each. Every answer cites product reality
rather than aspiration.

## 3. Required state
Every stakeholder-facing rep, founder-led call, investor update, and
RFP response draws from the same objection answers. Every answer is
reviewed by product before it ships. The map is a living document
and is versioned alongside the product.

## 4. Acceptance criteria
- This document contains at least fourteen objections in the
  canonical structure below.
- Each entry has: the objection in the buyer's voice, why it is real,
  ChartNav's honest answer, proof we can point to today, what the
  next release strengthens.
- The pricing page and the sales enablement page link to this doc.
- A quarterly review updates "proof" and "next release" columns to
  match shipped reality.

## 5. Codex implementation scope
Not a code task. This is sales enablement material owned by founder
and product leadership and reviewed by the clinical advisor before
external use.

## 6. Out of scope / documentation-or-process only
- Competitive battle cards naming specific competitors. ChartNav does
  not market by comparison in v1.
- Pricing negotiation playbook. Lives separately under commercial ops.

## 7. What can be demoed honestly now vs later
The objection answers themselves reference "now" and "later" columns;
see each entry. Sales must use the "now" proof during live demos and
disclose the "later" column when asked what is coming.

## 8. Dependencies
- Phase A, B, and C documents for proof references.
- Security posture doc for the HIPAA, data ownership, and go-away
  objections.
- Pricing page for the price objection.

## 9. Truth limitations
- Some answers currently point at architecture rather than certification
  (HIPAA, SOC 2). Reps must not upgrade posture into certification in
  conversation.
- "Referenceable pilot-customer contact" does not exist yet. The
  readiness-evidence answer below is honest about that.

## 10. Risks if incomplete
- Reps improvise, drift into over-promise, and create renewal-time
  trust losses.
- Investors and advisors encounter inconsistent narrative and
  lose confidence in commercial readiness.

---

## Objection entries

### 1. "You're not Epic."

Why it is real: every health system has Epic, Cerner, or an Allscripts
descendant. "Yet another EHR" is DOA.

ChartNav's answer: correct, we are not an Epic replacement and we
never will be. ChartNav is an ophthalmology-first clinical workflow
and documentation layer. We ship in three modes: standalone for
practices that do not have or do not want to expose their EHR,
integrated read-through for practices that keep Epic as the system of
record and want ChartNav to document into it indirectly, and integrated
write-through for practices that authorize us to post signed notes
back. We do not store the enterprise's longitudinal record; we make
the ophthalmology encounter faster and cleaner.

Proof today: three deployment modes live in `backend/app/config/
deployment_mode.py`; FHIR R4 read-through is working end-to-end in
demo; the product does one vertical well rather than forty verticals
poorly.

Stronger next release: published integration patterns per mode and
an Epic read-through demo video against a sandbox tenant.

### 2. "You don't have signed pilots yet."

Why it is real: healthcare procurement treats "pilot count" as a
leading indicator of survival.

ChartNav's answer: correct, and we will not pretend otherwise. We
are pre-pilot and actively selecting the first one to three design
partners. In exchange for being first, design partners get
founder-level access, a reduced pilot fee, and direct input into
roadmap sequencing for Phase C. We will not fabricate logo slides.

Proof today: readiness evidence — 231 backend tests, 55 frontend
tests, Axe-AA CI gate, full encounter state machine, evidence chain,
SBOM per release, published security posture, BAA template ready for
redline.

Stronger next release: a first signed pilot with a readout, then a
referenceable contact.

### 3. "Is this AI reliable?"

Why it is real: every clinical AI story in the press is a hallucination
story.

ChartNav's answer: ChartNav's note generator is a deterministic
regex-based extractor today. It cannot invent clinical values. Any
field it cannot confidently populate becomes an explicit provider-
verify flag, and the pre-sign checkpoint refuses to advance the
encounter until the clinician acknowledges those flags. No LLM is
wired in the shipped build. If your deployment later opts into an
LLM option, it is per-encounter, logged, and still human-signed.

Proof today: `backend/app/services/soap_extractor.py` is deterministic;
the LLM seam is inert; the pre-sign checkpoint enforcement has
integration tests; the AI governance document is shipped with the
product.

Stronger next release: AI mode banner visible in every environment
and a published model-version changelog when the LLM seam activates.

### 4. "Does it bill?"

Why it is real: buyers equate revenue-cycle relief with software value.

ChartNav's answer: ChartNav does not bill. It produces a deterministic
billing-handoff export per signed note, including the chief complaint,
encounter date, provider NPI, carried ICD codes, and — in Phase C —
accepted CPT suggestions with rule provenance. Your biller still runs
the claim in your billing system. We never submit a claim on your
behalf, and we never auto-capture a charge.

Proof today: the Phase B admin dashboard exposes signed-note counts;
the handoff export structure is defined in the Phase C reports doc;
the CPT suggestion layer is in the Phase C plan.

Stronger next release: shipped CPT suggestion layer and a handoff
export that includes accepted suggestions.

### 5. "We can't rip out our EHR."

Why it is real: they can't, and asking is offensive.

ChartNav's answer: we are not asking you to. Integrated read-through
mode lets ChartNav read from your FHIR R4 endpoint, render the
ophthalmology encounter experience, and hand a signed note back to
your team as a document, leaving your EHR as the system of record.

Proof today: FHIR R4 read-through is functional; write-through mode
is configurable off by default.

Stronger next release: signed pilot in read-through mode with
documented integration setup time.

### 6. "Write-through to Epic?"

Why it is real: some buyers want a fully round-tripped flow.

ChartNav's answer: write-through mode exists and is configurable per
deployment. When an adapter does not support write, the API returns
HTTP 501 `adapter_write_not_supported` and the UI surfaces the
fallback: download the signed note as a document and attach it through
your existing EHR's standard import flow. We do not fake a write.

Proof today: the 501 response path exists in the adapter layer.

Stronger next release: a named Epic write-through reference
deployment.

### 7. "HIPAA compliant?"

Why it is real: every purchase requires a signed BAA.

ChartNav's answer: ChartNav is architecturally built to the HIPAA
Security Rule — RBAC, audit logging, evidence chain, session
governance, retention tooling, non-root container, SBOM per release.
We are not claiming SOC 2, HITRUST, or ISO 27001 certification. A
BAA template is ready for your counsel's redline.

Proof today: the security posture document, the BAA template, the
`GET /about/security` manifest.

Stronger next release: SOC 2 Type I engagement in progress, then
complete.

### 8. "Who owns the data?"

Why it is real: vendor lock-in is a procurement red flag.

ChartNav's answer: in standalone mode, you own the database and the
object store; we do not host them. In integrated modes, your EHR
remains the system of record for any data written back. Either way,
the bulk-export surface produces a portable CSV and JSON archive on
demand.

Proof today: standalone deployment guide; Phase C bulk-export
surface.

Stronger next release: a documented, timed export-to-tarball drill
completed during the pilot.

### 9. "What if you go away?"

Why it is real: every vendor in this segment has gone away at least
once.

ChartNav's answer: standalone mode runs in your environment. The
bulk export produces your full data in open formats. Source
availability for on-prem customers is negotiable in the pilot MSA.
The answer is designed so that our disappearance is survivable.

Proof today: standalone deployment mode; bulk export in Phase C.

Stronger next release: a written source-escrow or source-availability
rider.

### 10. "What's the price?"

Why it is real: if price is not anchored early, procurement assumes
the worst.

ChartNav's answer: the pilot is a fixed fee with a 30/60/90 structure.
Post-pilot pricing is per-provider per-month for the core workflow,
with optional modules (CPT suggestion, bulk export) priced as add-ons.
The pricing page reflects the current tiers.

Proof today: pricing page is live and anchored.

Stronger next release: public per-provider price for the single-
clinic tier after the first signed pilot.

### 11. "What's the timeline?"

Why it is real: buyers need a clear runway to commit.

ChartNav's answer: the pilot is 30/60/90. Day 0–30 is deployment,
role setup, and template tuning. Day 31–60 is live clinical use with
founder-attached support. Day 61–90 is readout: metrics on
draft-to-signed turnaround, missing-flag rate, reminders completion.
At day 90 we either convert, extend, or part on good terms.

Proof today: the runbook for deployment-operator setup is published;
the reports surface produces the readout metrics.

Stronger next release: a shipped pilot with an anonymized readout we
can share in sales conversations.

### 12. "Ophthalmology-only forever?"

Why it is real: the buyer wants to know whether they are investing in
a niche tool or a future platform.

ChartNav's answer: ophthalmology-first is deliberate. The encounter
state machine, template engine, structured findings model, and
reporting pipeline are vertical-agnostic. A second vertical is a
content and template pack on top of the same substrate; it is not a
rewrite. We will not add a second vertical during Phase C because
doing one vertical well is how we win the first.

Proof today: the template engine is structurally separate from the
ophthalmology content; the SOAP extractor is rule-pack driven.

Stronger next release: an internal prototype of a second-vertical
template pack kept private until the first is fully won.

### 13. "What happens if your extractor is wrong?"

Why it is real: clinicians do not trust black boxes.

ChartNav's answer: the extractor is rule-based and every field has
an explicit provider-verify flag when the extractor is not confident.
The clinician sees the draft in the three-tier trust UI — green for
deterministic fill, amber for provider-verify, red for absent and
required — and must clear amber and red before signing.

Proof today: three-tier trust UI is shipped; the pre-sign checkpoint
blocks unacknowledged flags.

Stronger next release: an in-UI "explain this field" action that
names the specific rule that fired.

### 14. "How do you handle breaches?"

Why it is real: the answer reveals whether the vendor has actually
thought about it.

ChartNav's answer: the incident response section of the security
posture document names the breach notification window, the evidence
preserved via the hash-linked event chain, and the escalation path.
In standalone mode, primary response is the deployment operator's
responsibility; ChartNav assists.

Proof today: incident response section exists in the security
posture doc; evidence chain with optional HMAC is implemented.

Stronger next release: a tabletop exercise completed with a pilot
customer.
