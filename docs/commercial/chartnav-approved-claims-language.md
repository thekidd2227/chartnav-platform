# ChartNav Approved Claims Language

> Authoritative claims contract for every deck, doc, page, email,
> caption, voice-over, and pitch. Same heuristic Phase 13 / 14 /
> 15 / 16 already enforce in tests.

---

## Approved claims (use freely)

### Product positioning

- "provider-reviewed"
- "documentation support"
- "clinical workflow support"
- "ophthalmology-specific charting assistant"
- "draft for review"
- "review required"

### Workflow language

- "draft / review / finalize"
- "explicit provider review"
- "provider drives every transition"
- "signed retinal artifacts are immutable in place"
- "edits to a signed artifact create an explicit fork"
- "audit metadata-only"
- "cross-organization access returns 404"

### Clinical Signal Filtering language (prime feature — buyer-facing)

- "Clinical Signal Filtering"
- "Filters conversation. Captures findings. Builds the diagram."
- "separates casual speech from clinical findings"
- "flags uncertainty for provider review"
- "proposes retinal diagram annotations the provider applies,
  edits, or rejects"
- "ignored chatter / clinical finding / uncertain phrase /
  proposed diagram annotation"
- "the provider applies, edits, or rejects every proposal before
  anything is saved or finalized"

### Pilot / safety language

- "controlled pilot"
- "fake patient demo"
- "Business Associate Agreement"
- "BAA required before any real PHI is processed"
- "requires legal / security review before PHI"
- "designed to support HIPAA-aware data-handling practices"
- "intended to be deployed in a controlled-pilot mode that meets
  the practice's HIPAA posture"

### Negative-assertion safety bullets (use exact phrasing)

- "ChartNav supports documentation and review workflows."
- "ChartNav does not diagnose, create orders, send referrals,
  bill, or message patients automatically."
- "Every clinical artifact requires explicit provider review
  before it is treated as final."

### Pricing language

- "$299–$499 per provider per month"
- "$5,000 per practice per month flat"
- "$10,000 flat for a 4–6 week controlled pilot"
- "multi-practice annual discounts: 2–4 = 10%; 5–9 = 15%; 10+ =
  enterprise pricing"

### Federal / credibility language (federal-healthcare-adjacent
decks only)

- "operated by Ariel's River Contracting Group, LLC, dba ARCG
  Systems"
- "Maryland-based"
- "SDVOSB-certified Service-Disabled Veteran-Owned Small
  Business" (operating entity)
- "past performance: federal healthcare contracting at
  Mann-Grandstaff VA Medical Center, Spokane WA"
- "Maryland small business with HUBZone / DBE / MBE / SBE /
  NMSDC certifications carried by the operating entity"

---

## Forbidden claims (never use)

These appear in customer-facing artifacts only inside an explicit
negative-assertion line ("does not …", "Not …", "never …") or
inside a forbidden-phrase enumeration like this list itself.

### Compliance / certification

- ❌ "HIPAA compliant"
- ❌ "HIPAA certified"
- ❌ "SOC 2 certified"
- ❌ "certified EHR"
- ❌ "production-ready for PHI"
- ❌ "real patient data ready"

### Capability

- ❌ "autonomous diagnosis"
- ❌ "automatic diagnosis"
- ❌ "guaranteed accuracy"
- ❌ "guaranteed documentation accuracy"
- ❌ "automatic orders"
- ❌ "order OCT"
- ❌ "submit referral"
- ❌ "send referral"
- ❌ "billing automation"
- ❌ "coding automation"
- ❌ "send patient message"
- ❌ "auto-message patients"
- ❌ "replaces a doctor"
- ❌ "external LLM certainty"
- ❌ "AI draws automatically"
- ❌ "AI decides"
- ❌ "AI diagnosis"
- ❌ "automatic charting"
- ❌ "hands-free diagnosis"
- ❌ "hands-free charting"
- ❌ "hands-off documentation"

---

## Caution claims (case-by-case)

These can appear when carefully framed; default to avoiding them
unless there's a strong reason.

| Claim | Caution |
|---|---|
| "FDA cleared" | We are not. Don't use. |
| "AI-powered" | Use "assistant" or "deterministic generators" instead. "AI-powered" is broad and invites unsafe inferences. |
| "100% accurate" | We don't promise accuracy. Use "deterministic" or "structured" instead. |
| "Saves \<X\>% of provider time" | We don't have validated numeric improvement claims. Use "documentation support" or "workflow support" instead. |
| "Replaces \<feature\> in your EHR" | We sit alongside the EHR; we don't replace it. Use "complements" or "alongside." |

---

## Substitution table

Always replace forbidden phrasing with approved phrasing.

| Forbidden phrasing | Approved replacement |
|---|---|
| "HIPAA compliant" | "designed to support HIPAA-aware data-handling practices" |
| "HIPAA certified" | "BAA-ready before real PHI" |
| "SOC 2 certified" | "security review packet available" |
| "certified EHR" | "documentation + review assistant alongside the EHR" |
| "autonomous diagnosis" | "provider-reviewed documentation" |
| "automatic orders" | "review tasks only — no orders" |
| "submit referral" | "no referral surface in the product" |
| "send patient message" | "no patient-send surface in the product" |
| "replaces a doctor" | "documentation support — provider decides" |
| "production-ready for PHI" | "controlled-pilot mode after BAA + security review" |
| "real patient data ready" | "fake-data demo first; real PHI after gating" |
| "AI draws automatically" | "AI proposes; provider applies, edits, or rejects" |
| "AI decides" | "AI proposes; provider decides" |
| "AI diagnosis" | "provider-reviewed documentation" |
| "automatic charting" | "draft documentation the provider reviews" |
| "hands-free diagnosis" | "provider-in-the-loop documentation" |
| "guaranteed documentation accuracy" | "provider-reviewed; provider corrects" |

---

## Examples

### ✅ OK

> *"ChartNav supports documentation and review workflows. ChartNav
> does not diagnose, create orders, send referrals, bill, or
> message patients automatically."*

> *"Pilots run against fake demo data first. Real PHI requires
> a BAA and a security review."*

> *"We follow HIPAA-aware data-handling practices."*

### ❌ Not OK

> *"ChartNav is HIPAA-compliant."* — never.

> *"ChartNav automatically orders OCT scans when needed."* —
> never. Use *"ChartNav surfaces review tasks; the provider
> orders."*

> *"ChartNav replaces your scribe."* — never. Use *"ChartNav
> supports your scribe."*

### ⚠️ Edge case

> *"ChartNav reduces documentation time by 30%."*

This is a forbidden numeric capability claim until we have
operating data. Replace with *"ChartNav is designed to reduce
documentation friction; pilots measure your specific baseline."*
