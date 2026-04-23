# Phase C — Sales Readiness Gates

## 1. Problem solved
ChartNav is the kind of product that can be ruined by a single bad
early conversation. Premature outbound to strangers produces dead
deals, broken references, and a damaged narrative that persists for
quarters. A gated checklist between "we can demo to a warm advisor",
"we can accept a real pilot", and "we can take meetings with strangers"
forces explicit qualification of each transition.

## 2. Current state
- Phase A (ophthalmology encounter templates, structured charting and
  attestation) is drafted and partially shipped.
- Phase B (referring-provider communication) is drafted.
- Phase C specs (CPT suggestion, AI governance, security posture,
  reporting, objection map, this doc) are drafted.
- Pricing page is live on SourceDeck infrastructure.
- No signed pilot. No independent security review. No published
  case study. ARCG and ChartNav name ownership in progress.
- Sales enablement is ad hoc.

## 3. Required state
Three gates — A, B, and C — each with explicit items, per-item owner,
verification method, and a blocker statement naming what is true if
the item is not complete. Gates advance only when every item is
green. The default is no: the burden is on the gate sponsor to show
green, not on a reviewer to show red.

## 4. Acceptance criteria
- This document lists every gate item with owner, verification, and
  blocker text.
- A data-room checklist is included and mapped to the gates.
- The sales enablement page links to this doc.
- Gate state is reviewed before every board, investor, or advisor
  conversation where commercial posture is a topic.

## 5. Codex implementation scope
Not a code task. This is a founder-and-product-leadership artifact
reviewed by clinical and legal advisors.

## 6. Out of scope / documentation-or-process only
- Individual deal qualification (BANT, MEDDICC). That is the seller's
  job per deal.
- Investor data room. Mentioned here only as a dependency.

## 7. What can be demoed honestly now vs later
This document is itself the honesty-versus-polish filter. It tells
the founder and reps what is demoable, what is not, and what must be
true before a given class of conversation is appropriate.

## 8. Dependencies
- Every Phase A, B, and C document referenced.
- Outside counsel for the BAA template review.
- Clinical advisor for the pilot proposal sign-off.
- Independent security consultant or SOC 2 Type I engagement for
  Gate C.

## 9. Truth limitations
- These gates reduce the probability of an avoidable self-inflicted
  wound. They do not guarantee a sale or a successful pilot. They are
  about readiness, not outcome.
- The item list is based on what is honest for ChartNav in its
  current segment and may drift as the product and market evolve.

## 10. Risks if incomplete
- Discovery calls land without a coherent narrative and the buyer
  disqualifies on first contact.
- A pilot is accepted before support operations can sustain it, the
  pilot stalls, and the would-be reference becomes a cautionary tale.
- A stranger-sourced meeting is taken before the security package is
  publishable and the procurement cycle dies in questionnaire hell.

---

## Gate A — can we take a discovery call?

Purpose: confirm ChartNav has a coherent, honest story and the
minimum paperwork to survive a procurement-aware first conversation.

| Item | Owner | Verification | Blocker if missing |
|---|---|---|---|
| Core messaging: one-sentence positioning, three-sentence elevator, one-paragraph "what we are not" | Founder | Committed to `docs/chartnav/messaging/positioning.md`, reviewed by clinical advisor | Reps improvise, message drifts, buyer disqualifies |
| Honest status sheet: phase completion, pilot count, certifications | Founder | Committed to `docs/chartnav/status/current-state.md`, refreshed weekly | Sales claims land that do not survive diligence |
| Pricing page live and linkable | Product | `sourcedeck/pricing.html` deployed, tiers reviewed by commercial | Price becomes a late-stage surprise |
| ARCG and ChartNav name ownership | Founder | Trademark filing status confirmed in writing | Third party asserts the mark mid-sales-cycle |
| BAA template ready for redline | Legal | `docs/chartnav/legal/BAA-template.md` reviewed by outside counsel | Cannot move from "interesting" to "signable" |
| Security posture v1 published | Product | `docs/chartnav/security/security-posture.md` committed | Procurement questionnaires stall on basics |
| AI governance policy v1 published | Product | `docs/chartnav/policy/ai-governance.md` and buyer-safe version committed | AI question derails the call |
| Objection map published | Founder + product | `PHASE_C_Buyer_Objection_Map.md` committed | Reps improvise answers |
| Demo environment reproducible from a single command | Engineering | `make demo-env` script works from clean checkout | Demo drift embarrasses rep or founder |

Exit criterion: all items green and reviewed by founder within the
last two weeks.

---

## Gate B — can we accept a pilot?

Purpose: confirm ChartNav can be safely operated in a real clinic for
ninety days without exposing the customer or the product to
avoidable failure modes.

| Item | Owner | Verification | Blocker if missing |
|---|---|---|---|
| Phase A and Phase B complete and merged to main | Engineering | Release tag cut from main with Phase A + B scope | Pilot will surface incomplete clinical surface |
| Phase C CPT suggestion shipped behind a feature flag | Engineering | `cpt_suggestions` table exists; panel renders; tests green | Revenue-cycle ROI story collapses at readout |
| Reports and exports surface shipped | Engineering | `POST /admin/reports/*` and bulk export live; tests green | Cannot produce pilot readout; cannot answer "export our data" |
| Support ops runbook written | Founder + engineering | `docs/chartnav/runbooks/support-ops.md` committed, includes on-call expectations | First production issue has no playbook |
| Pilot proposal template signed off by clinical advisor | Founder | `docs/chartnav/commercial/pilot-proposal-template.md` committed with advisor sign-off noted | Pilot scope drift kills the readout |
| Deployment operator security runbook | Engineering | `docs/chartnav/runbooks/deployment-operator-security.md` committed | Pilot operator misconfigures environment |
| Release compliance checklist enforced in CI | Engineering | `docs/chartnav/security/release-compliance-checklist.md` linked from release workflow | Uncontrolled release leaks into pilot |
| Demo environment matches pilot environment topology | Engineering | Demo uses same deployment mode the pilot will use | Pilot reveals gaps hidden in demo mode |
| Pricing for pilot fee and post-pilot subscription committed | Commercial | Pricing page reflects committed tiers; internal commercial memo signed | Negotiation drifts, discounts compound |
| Evidence chain HMAC enabled in pilot environment | Engineering | `EVIDENCE_HMAC_KEY` set; manifest reports true | Audit trail integrity defensible only on paper |

Exit criterion: all items green and a named design-partner customer
is ready to sign.

---

## Gate C — can we go beyond pilot?

Purpose: confirm ChartNav can be sold to strangers without founder
presence on every call.

| Item | Owner | Verification | Blocker if missing |
|---|---|---|---|
| At least one pilot completed with a written readout | Founder | `docs/chartnav/readouts/pilot-<customer-id>.md` committed, anonymized version available | No evidence conversion is possible |
| At least one referenceable pilot-customer contact | Founder | Customer contact named and consented in writing | "Who can we call?" is unanswerable |
| Independent security review completed or SOC 2 Type I in progress | Founder + security lead | Written consultant report or auditor engagement letter on file | Enterprise procurement cannot progress |
| Penetration test completed | Engineering | Report on file, remediation items tracked | Enterprise procurement cannot progress |
| Case study published, buyer-approved | Commercial | Public page linked from SourceDeck | Warm intros lack a landing proof point |
| Stranger-outbound playbook | Commercial | `docs/chartnav/commercial/outbound-playbook.md` committed | Outbound drifts into over-promise |
| Internal call review cadence | Commercial | Weekly call-review meeting with notes | Rep drift goes undetected |
| Pricing confirmed against two signed deals | Commercial | Two signed agreements at the posted tier with minimal discount | Pricing is aspirational, not validated |

Exit criterion: all items green and founder explicitly approves going
wide.

---

## Data-room checklist

Items a qualified buyer or investor receives in diligence. Shipped as
a single organized folder with a table-of-contents README.

- Company: legal entity, jurisdiction, cap table summary.
- Trademark: ARCG and ChartNav mark status.
- Product: current phase status, architecture overview, deployment-
  mode summary.
- Security: security posture document, BAA template, evidence-chain
  description, audit-retention runbook, SBOM per release, image
  digests per release, release-compliance checklist.
- AI governance: AI governance policy and buyer-safe version.
- Engineering quality: test counts (backend, frontend), Axe-AA
  CI gate evidence, recent CHANGELOG, release cadence.
- Commercial: pricing tiers, pilot proposal template, objection map,
  readiness gates (this doc).
- Legal: BAA template, standard MSA draft, DPA if applicable.
- Pilots and references: pilot readouts (anonymized where required),
  referenceable contact list.
- Roadmap: Phase A, B, C documents; next-phase working draft.

Intentionally not included (do not claim): SOC 2 report, HITRUST
certification, ISO 27001 certification, FDA clearance, any
certification ChartNav does not in fact hold. If a buyer asks and the
item is not in the data room, the answer is "we do not have that
today" — not silence, not deflection, not aspirational language.
