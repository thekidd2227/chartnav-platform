# ChartNav Clinical Workflow Demo Script

This script walks a buyer / pilot user / advisor / investor through
the existing ChartNav ophthalmology workflow in five or ten minutes.
It uses the **existing seeded demo data** (`demo-eye-clinic` org,
patient `PT-1001` / Morgan Lee, encounter 1) — there is no backend
demo seed and no fresh data setup for the demo. The data is
obviously fake by construction.

This document is the source of truth for *what to say* during a
demo. The companion `chartnav-demo-click-path.md` is the source of
truth for *what to click*. The companion
`chartnav-video-clip-shot-list.md` is the source of truth for what
to capture if you record clips later.

---

## Demo audience

- **Pilot ophthalmologists** evaluating ChartNav for documentation
  support.
- **Practice administrators** evaluating workflow fit.
- **Advisors / investors** evaluating product positioning.
- **Internal team** running pre-pilot rehearsals.

This script is **not** intended for patient-facing demos.

---

## Safety guardrails — say these, every time

These are the only claims you should make during a demo. They are
deliberately narrow because every product surface in the workflow
is built around the same contract.

- "ChartNav supports documentation and review workflows."
- "Every artifact requires explicit provider review before it is
  treated as final."
- "ChartNav does not diagnose, order, bill, send referrals, or
  message patients automatically."
- "The pre-visit brief and the action queue summarize available
  ChartNav records — they are not clinical decisions."

If a question pushes past these claims, reach for the buyer Q&A at
the end of this doc.

---

## Ophthalmology-specific positioning

ChartNav is a documentation + review assistant **specific to
ophthalmology**. Not a primary-care SOAP note generator. Not a
specialty-agnostic scribe.

The reasons it is specific to ophthalmology — without claiming
diagnostic capability:

- The retinal-diagram surface targets OD/OS annotations directly.
- The clinical-language scan on the action queue is tuned to a
  narrow ophthalmology vocabulary (retinal tear, retinal
  detachment, neovascularization, severe hemorrhage). It is not
  a general-purpose flagger and is documented as not a primary
  safety net.
- The structured note vocabulary is closed and ophthalmology-
  flavored (chief complaint, HPI, exam, assessment, plan).
- The patient-friendly summary template is composed from ophthalmic
  source content — visual acuity, IOP, plan / follow-up — rather
  than free-form clinical reasoning.

**What it is not:**

- Not a billing tool.
- Not an EHR.
- Not a patient portal.
- Not a primary-care charting assistant.
- Not a referral-routing system.

---

## 5-minute demo (single-screen)

| Time | Surface | What you do | What you say |
|------|---------|-------------|--------------|
| 0:00 | Workspace top | Open the **Demo workflow guide** drop-down (top of the workspace). | "Every panel in this workspace is provider-reviewed. The guide tells you exactly what we'll click in 5 minutes." |
| 0:30 | Scribe Session panel | Paste a short ophthalmology note (sample below). Click *Process*, then *Mark reviewed*, then *Finalize*. | "ChartNav drafts a structured note from the source text. The provider reviews and explicitly finalizes — never automatic." |
| 1:30 | Eye Diagram panel | Click *Generate proposals from findings*. Apply one proposal. *Save*. *Sign*. | "Proposals are read-only suggestions. Anything that lands on the diagram is tagged source=ai_approved. Signed artifacts are immutable." |
| 2:30 | Patient Summary panel | *Generate from finalized scribe* → review → finalize. | "The summary is provider-facing. ChartNav never sends it to the patient — that is explicitly deferred." |
| 3:30 | Pre-Visit Brief panel | *Generate*. Show source counts and data gaps. | "This is a derived view of existing chart records. It surfaces what is and is not on file. It is not a clinical decision." |
| 4:30 | Provider Action Queue panel | *Generate*. Accept one item, dismiss one, complete one. | "Every action is a review task — never an order, never a referral, never a message. The provider explicitly resolves each one." |

### Sample source text for the scribe paste

```
Chief complaint: blurry vision OD, two weeks.
HPI: progressive blur OD, no flashes/floaters today.
Exam: VA 20/40 OD, 20/20 OS. IOP 16/14. OD drusen at macula;
possible retinal tear superior temporal OS.
Assessment: drusen OD; suspected retinal tear OS pending review.
Plan: refraction next visit; monitor OS.
```

---

## 10-minute demo (single-screen + Q&A)

The 10-minute version repeats the 5-minute beats and adds three
deeper dives:

1. **Audit metadata-only** (after step 6 above):

   "Every mutation across all five panels emits a metadata-only
   audit row. Section bodies, summary text, scribe text, and brief
   sections never reach the audit log. Sentinel-token regression
   tests assert this on every PR."

2. **Org isolation** (after step 6):

   "Every patient is resolved inside the caller's organization
   before any other lookup. A cross-org caller sees a 404 for the
   same patient_id — no existence leak. Defense in depth re-asserts
   the org filter on every per-source SELECT."

3. **Clinical-language scans on the action queue** (during step 7):

   "The queue surfaces review tasks when finalized chart text
   contains language like 'retinal tear' or 'severe hemorrhage'.
   The vocabulary is small on purpose — false positives are tolerable
   because every suggestion is provider-reviewed. The queue is not a
   primary safety net."

---

## Buyer Q&A — what to say (and what not to say)

### "Does ChartNav diagnose?"

**Say:** "No. ChartNav supports documentation and review. The
provider diagnoses; ChartNav surfaces structured chart context for
their review."

**Do not say:** "It's autonomous." "It's HIPAA-certified." "It
replaces a doctor."

### "Does ChartNav write orders?"

**Say:** "No. There is no order-creation surface in the product.
The closest thing is the action queue, which only suggests
*review* tasks the provider explicitly accepts or dismisses."

**Do not say:** "We can add order entry." (That is out of scope and
explicitly deferred — we don't promise it.)

### "Can ChartNav message patients?"

**Say:** "No. There is no patient-messaging surface in the product.
The patient-friendly summary panel renders no patient-send action."

### "Do you call OpenAI / GPT / an external LLM?"

**Say:** "Today's generators are deterministic regex / aggregation
over already-stored chart text. The architecture leaves room for an
external-LLM source under the same provider-review contract — that
is documented as deferred and is not enabled."

### "Is this HIPAA-compliant?"

**Say:** "We follow HIPAA-aware data-handling practices: org
isolation, metadata-only audit, no patient-side delivery, no
external-LLM PHI egress. Compliance certifications are pursued
separately from product features."

**Do not say:** "We are HIPAA-certified." (HIPAA does not certify
software. Avoid the phrase.)

### "Can you integrate with my EHR?"

**Say:** "ChartNav exposes a clean integration boundary — we have
a bridge layer with a FHIR adapter shape. EHR-specific integrations
are pursued in dedicated phases and are out of scope for this
demo."

### "What do you do that an LLM scribe doesn't?"

**Say:** "We're ophthalmology-specific end-to-end: the OD/OS retinal
diagram, the structured note vocabulary, the action queue's
clinical-language flags, and the patient-friendly summary template
are all tuned to ophthalmology workflow. We're a documentation /
review surface, not a generic note generator."

---

## What not to claim, ever

These claims are unsafe and should never appear in a demo, in
marketing, or in copy anywhere in the product:

- "HIPAA compliant" (use *HIPAA-aware data-handling practices*).
- "Certified EHR" (we are not an EHR).
- "Autonomous diagnosis" or "automatic diagnosis."
- "Guaranteed accuracy."
- "Automatic orders."
- "Order OCT."
- "Submit referral" / "send referral."
- "Billing automation" / "coding automation."
- "Send patient message" / "auto-message patients."
- "Replaces a doctor."
- "External LLM certainty."

If you catch yourself saying any of these on a demo, stop and
correct: "I want to be careful — ChartNav doesn't do that. What it
does is …"

---

## What to do after the demo

- Hand the buyer the link to
  `docs/chartnav-patient-chart-foundation.md` for the full per-phase
  contract.
- Capture any feature requests as Phase candidates — do not promise
  them in the room.
- File any unsafe-language slips you noticed yourself making against
  Phase 13 follow-up.

---

## Demo data policy

- The demo uses only the existing fake seed data
  (`demo-eye-clinic` org, `PT-1001` Morgan Lee, encounter 1).
- No real PHI, no real names, no real MRNs, no real DOBs, no real
  phone numbers, no real addresses.
- No demo data is generated specifically for the demo — every name,
  every encounter, every transcript line is from the existing
  `scripts_seed.py` and the ad-hoc paste in step 0:30 of the
  5-minute demo.
- Reset between demos by re-running `make reset-db` and `make seed`,
  or letting `make verify` do it for you.
