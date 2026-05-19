# Phase 24D — Pilot Objection Cheat Sheet

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** founder / sales engineer on a discovery call or
> demo when the buyer pushes on a claim, scope question, or
> compliance question.
> **Companion docs:**
> `phase-24d-pilot-discovery-call-script.md` — the full call
> sequence.
> `phase-24c-retina-demo-runbook.md` — runbook §9 has aligned
> objection answers (keep both in sync).
> `chartnav-known-limitations-and-non-goals.md` — the product's
> formal non-goals list.

## How to use this document

Keep it open in a side window during every discovery call and
every demo. When the buyer pushes on any of the questions below,
read the **Safe answer** verbatim if you need to, and never invent
a new claim under pressure.

Two rules:

1. **Honesty over selling.** Every "no" below is a real boundary.
   Saying "yes" to win the deal will rot the safe-claims
   contract and put real PHI at risk later. Decline cleanly.
2. **One redirect per call.** If the buyer pushes the same
   forbidden-capability question twice, end the qualification
   block and use Variant 8 ("Not a fit") in
   `phase-24d-pilot-outreach-message-bank.md` to close the
   conversation gracefully.

If you hear an objection that is not on this list, add it (with a
buyer-safe answer) and ship the update as a docs-only PR.

---

## 1. "Is this just another scribe?"

**Safe answer:**

> "No. The scribe panel is one surface inside ChartNav, and every
> draft it produces is provider-reviewed — but the product wedge
> is the **ophthalmology clinic workflow layer**: role-based
> dashboards, technician handoff, imaging metadata review,
> retina tracking, sign-off queue, and internal follow-up
> tasking. If the only thing you need is cheap dictation, I'll
> be honest — ChartNav is not the cheapest tool for that job."

---

## 2. "Does it replace our EHR?"

**Safe answer:**

> "No. ChartNav is a workflow coordination layer; the practice's
> EHR remains the system of record. ChartNav publishes
> provider-reviewed draft artifacts to the EHR through the
> practice's existing workflow. 'EHR replacement' is explicitly
> not on the roadmap."

---

## 3. "Does it interpret OCTs or fundus photos?"

**Safe answer:**

> "No. ChartNav stores imaging **metadata only** — modality,
> eye, capture timestamp, study notes the technician or MD
> enters — and surfaces it for provider review. ChartNav does
> not interpret images, does not measure them, does not auto-
> grade disease, and does not own the device integration."

---

## 4. "Can it diagnose diabetic retinopathy or DME?"

**Safe answer:**

> "No. ChartNav does not diagnose retina disease, classify
> severity, or grade DR. The retina tracking row holds the
> **structured fields the provider enters** — condition, eye,
> severity, follow-up interval, provider assessment. The
> diagnosis stays with the provider."

---

## 5. "Can it place orders or send referrals?"

**Safe answer:**

> "No. Both are explicit non-goals. ChartNav does not place
> orders, does not send referrals, does not contact outside
> providers, and does not insert any order into the EHR
> automatically. The only follow-up tasks ChartNav creates are
> **internal staff coordination** — never patient-facing,
> never external."

---

## 6. "Can it message patients?"

**Safe answer:**

> "No. ChartNav does not message patients. There is no patient
> portal push, no SMS, no email, no automated reminder.
> Patient-facing communication stays with the practice's
> existing tooling. The only follow-up tasking ChartNav surfaces
> is for **internal staff coordination** — for example, the
> front desk confirming the next-visit window after a retina
> follow-up closes."

---

## 7. "Can it bill, code, or submit claims?"

**Safe answer:**

> "No. ChartNav does not bill, does not code for billing, does
> not submit claims, and does not handle insurance. None of
> those are on the roadmap. The practice's billing and coding
> tooling stays in place; ChartNav does not touch the revenue
> cycle."

---

## 8. "Is it HIPAA compliant?"

**Safe answer:**

> "ChartNav is not marketed as HIPAA compliant or HIPAA
> certified. The default deployment is fake-data only. Before
> any real PHI is ever loaded into ChartNav for your practice,
> the **Phase 23 real-PHI go-live gate** must be satisfied
> **for your practice specifically** — BAA execution, your
> security review, production authentication, approved hosting,
> backups, monitoring, incident contacts, and written practice
> approval. That gate is a per-practice checklist, not a
> certification ChartNav holds on its own. Happy to send the
> packet to your IT or compliance gatekeeper."

---

## 9. "Does it integrate with our imaging devices?"

**Safe answer:**

> "Not today. ChartNav stores imaging metadata only; the binary
> capture stays in the practice's existing imaging workflow.
> Specific OCT or fundus-camera vendor integrations are roadmap
> items, not current state. If a particular device integration
> is a day-one requirement for [Practice Name], I'd flag that
> as a fit gap and we can talk about whether ChartNav makes
> sense at all right now."

---

## 10. "What happens if the AI is wrong?"

**Safe answer:**

> "Every artifact ChartNav produces — scribe drafts,
> documentation drafts, retina tracking summaries, action
> items — is a **draft until a provider signs it**. The
> provider-review banner is present on every panel that drafts
> content. ChartNav does not act autonomously. There is no path
> from a draft to a placed order, a sent referral, or a patient
> message. If a draft is wrong, the provider edits it before
> sign-off; the artifact is never released into the patient
> record on its own."

---

## 11. "How do we pilot without real PHI?"

**Safe answer:**

> "That's the default. The first pilot phase is a **fake-data
> evaluation**: seeded synthetic patients (e.g., Morgan Lee,
> PT-1001), fake providers (Dr. Carter), fake imaging metadata.
> Your clinical champion can drive the workflow end-to-end —
> front desk readiness, technician workup, imaging metadata
> review, retina tracking, provider-reviewed documentation,
> sign-off, internal follow-up — without ever touching real
> patient data. We measure success against
> `chartnav-pilot-success-metrics.md` using the fake-data
> dataset. Real PHI is gated behind the Phase 23 readiness gate
> for your practice when and if you want to move to the next
> phase."

---

## 12. "What does our staff actually do differently?"

**Safe answer:**

> "Front desk works the **check-in** + **follow-up** lanes
> instead of paper sticky notes or ad-hoc EHR tasks. Technicians
> work the **workup** + **imaging-needed** lanes and mark
> imaging metadata as ready for review. The MD sees the
> **ready-for-doctor**, **documentation**, and **sign-off**
> lanes on one screen, with the retina tracking row and the
> imaging metadata in the same workspace. Reviewers see the
> **sign-off queue** and the audit-exceptions tab. The admin
> sees queue aging across status, priority, role, and queue
> type. Same patient, same lane cycle — the change is **role
> visibility**, not the addition of any automation that wasn't
> there before."

---

## Bonus — quick-reference table

When the call is moving fast, use this table to find the answer
in one line. Then read the full safe answer above before
elaborating.

| Buyer question shape | One-line answer |
|---|---|
| "Does it diagnose / grade / interpret / classify [anything]?" | "No. ChartNav does not diagnose or interpret. The provider does." |
| "Does it auto-place orders / referrals / messages / claims?" | "No. ChartNav coordinates internal workflow; it does not act outside the practice." |
| "Does it replace [EHR / scribe / billing / coding]?" | "No. ChartNav is a workflow layer, not a replacement for any of those systems." |
| "Is it HIPAA / SOC-2 / FDA / HITRUST [anything]?" | "ChartNav holds no third-party compliance certifications. Real-PHI use is per-practice gated." |
| "Does it integrate with [device vendor]?" | "Imaging metadata only today. Specific device integrations are roadmap." |
| "How do we evaluate it without real PHI?" | "Fake-data evaluation phase first. Seeded synthetic patient end-to-end." |

---

## Phrase budget — buyer-safe vocabulary

Use these phrases when paraphrasing. They are the same words used
in the Phase 24C runbook and the Phase 24D outreach copy.

- "ophthalmology clinic workflow layer"
- "lane cycle visibility"
- "role-based clinic dashboards"
- "imaging metadata review"
- "retina tracking"
- "provider-reviewed documentation"
- "internal staff coordination"
- "fake-data evaluation phase"
- "controlled-pilot readiness"
- "Phase 23 real-PHI gate"

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-outreach-message-bank.md`
- `phase-24d-pilot-discovery-call-script.md`
- `phase-24d-demo-invite-and-agenda.md`
- `phase-24d-post-demo-follow-up-template.md`
- `phase-24d-pilot-fit-scorecard.md`
- `phase-24d-pilot-tracker-template.md`
- `docs/demo/phase-24c-retina-demo-runbook.md`
- `chartnav-known-limitations-and-non-goals.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-security-review-packet.md`
- `chartnav-pilot-success-metrics.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
