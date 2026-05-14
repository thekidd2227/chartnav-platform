# Phase 24D — Post-Demo Follow-Up Template

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** sales / founder following up within 24 hours of
> the fake-data retina workflow demo.
> **Companion docs:**
> `phase-24d-demo-invite-and-agenda.md` — the call this email
> follows.
> `phase-24d-pilot-fit-scorecard.md` — score the practice before
> sending.
> `phase-24d-pilot-tracker-template.md` — log the update.

Use the template below. Send within **24 hours** of the demo. Pick
one subject from §"Subject options" and edit the bracketed fields.
Do not attach internal-only docs — see §"Attachments" for what to
share.

---

## Subject options

Pick one. All three test cleanly with compliance teams.

1. **Follow-up: ChartNav fake-data retina workflow demo —
   [Practice Name]**
2. **Next step: controlled pilot fit for ChartNav —
   [Practice Name]**
3. **ChartNav demo recap and security-review path —
   [Practice Name]**

If the demo closed with "not a fit," use Variant 8 in
`phase-24d-pilot-outreach-message-bank.md` instead of this
template.

---

## Email body (template)

```
Hi [First Name],

Thanks for the 30 minutes today. Quick recap, what you said, and
what I'm proposing as the next step.

What we walked through
----------------------

- One synthetic patient (Morgan Lee, PT-1001 — fully fake, no
  real PHI) moving end-to-end through the clinic lane cycle:
  front-desk readiness → technician workup → imaging metadata
  review (OCT macula + fundus photo — metadata only) → retina
  tracking → provider-reviewed documentation draft → sign-off
  queue → internal staff follow-up task.
- Role-based clinic dashboards across front desk, technician,
  MD, reviewer, and admin — each role sees only the queues it
  owns.
- The provider-review banners that gate every artifact, plus the
  landing-page negative-assertion strip
  ("Not a certified EHR", "Not HIPAA-certified",
   "Does not interpret OCT", "Real-PHI pilot requires BAA").

What I heard from you
---------------------

You named two specific pains:

  1. [Pain 1 — quote the buyer's words; e.g., "the OCT
      metadata doesn't surface to the retina MD before the
      patient is in the chair"].
  2. [Pain 2 — quote the buyer's words; e.g., "the front
      desk loses track of the next-visit window after a retina
      follow-up"].

Both map cleanly onto what ChartNav coordinates today. Neither
requires diagnostic AI, image interpretation, automatic orders,
patient messaging, or billing automation — and ChartNav does not
do any of those things, which I confirmed on the call.

Suggested next step
-------------------

A controlled fake-data pilot, evaluated in four moves:

  1. Security-review packet → your IT / compliance gatekeeper
     ([gatekeeper name]) reviews ChartNav's scope, fake-data
     evaluation phase, and the Phase 23 real-PHI gate.
  2. Pilot readiness checklist → the practice walks the items in
     `chartnav-pilot-readiness-checklist.md` and tells us where
     the gaps are.
  3. Pilot agreement scope → fake data only for the first
     evaluation window. Real PHI is gated behind BAA execution,
     this security review, production authentication, approved
     hosting, backups, monitoring, incident contacts, and
     written practice approval — that's the Phase 23 gate, not
     a marketing line.
  4. Controlled go-live → once gate items are satisfied, the
     practice's clinical champion runs a short controlled pilot
     and we measure against
     `chartnav-pilot-success-metrics.md`.

Real PHI stays out of ChartNav for [Practice Name] until the
Phase 23 real-PHI gate is satisfied for your practice
specifically. That gate is a per-practice checklist — not a
certification ChartNav holds on its own, and not something we
ask the practice to take on faith.

Two questions to keep moving
----------------------------

  a. Can I send the security-review packet to [gatekeeper
     name]?
  b. Does a 30-minute follow-up next [Day] at [Time block]
     work for a small clinical group (you + your retina lead +
     the operations champion)?

If the answer to either question is "not yet," tell me what
you'd need to hear or see to get there.

Thanks,
[Your Name]
[Your Title], ChartNav
[Your contact info]
```

---

## Attachments / checklist references

What you can share, by audience:

| Audience | Share | Notes |
|---|---|---|
| Practice administrator | `chartnav-pilot-readiness-checklist.md`, `chartnav-known-limitations-and-non-goals.md` | Both are operator-facing and safe-claims-clean. |
| Clinical champion | `docs/demo/phase-24c-retina-demo-runbook.md` (excerpt — Stops 6 / 7 / 8 only), `chartnav-known-limitations-and-non-goals.md` | Send the relevant runbook stops, not the whole operator runbook. |
| IT / security gatekeeper | `chartnav-security-review-packet.md`, `chartnav-controlled-pilot-go-live-checklist.md`, `docs/security/chartnav-real-phi-go-live-gate.md` | Use Variant 7 in `phase-24d-pilot-outreach-message-bank.md` as the handoff email. |
| Decision maker | `chartnav-pilot-success-metrics.md`, `chartnav-known-limitations-and-non-goals.md` | Lead with what success looks like and what's explicitly out of scope. |

### Do **not** share with the practice

These are internal-only and would confuse the buyer (or worse,
read like overclaiming):

- `phase-24d-pilot-practice-selection-criteria.md` — internal
  qualification logic.
- `phase-24d-pilot-outreach-message-bank.md` — internal templates.
- `phase-24d-pilot-discovery-call-script.md` — internal script.
- `phase-24d-pilot-fit-scorecard.md` — internal scoring.
- `phase-24d-pilot-tracker-template.md` — internal pipeline.
- `phase-24d-pilot-objection-cheat-sheet.md` — internal responses.
- `docs/demo/phase-24c-demo-qa-checklist.md` — operator-only
  preflight.
- `docs/demo/phase-24c-retina-shot-list.md` — editorial-only.

If any of these need to be quoted to the buyer, rewrite the
specific section into the email body first. Do not forward the
internal doc.

---

## Real-PHI language (boilerplate — quote verbatim when needed)

Use this paragraph as the controlled-pilot real-PHI close. It is
the same paragraph the discovery call script and the demo runbook
use, so the buyer hears identical language at every touchpoint.

> "ChartNav is not approved for real PHI by default. A controlled
> real-PHI pilot requires BAA execution, practice security
> review, production authentication, approved hosting, backups,
> monitoring, incident contacts, and written practice approval.
> The readiness gate is documented in
> `docs/security/chartnav-real-phi-go-live-gate.md`. Until that
> gate is satisfied for [Practice Name], the engagement stays
> fake-data-only."

---

## Tracker update (within 15 minutes of sending)

Open `phase-24d-pilot-tracker-template.md` and update:

- `demo_completed?` → yes / today's date
- `objections` → free text; one per row if multiple
- `next_step` → "security packet sent to [gatekeeper name]" or
  "second clinical demo scheduled for [Date]" or "no
  response — follow up [Date]"
- `pilot_fit_score` → from
  `phase-24d-pilot-fit-scorecard.md`
- `status` → `demo completed` / `security review` /
  `pilot candidate` / `nurture` / `not fit`
- `last_touch` → today's date

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-outreach-message-bank.md`
- `phase-24d-pilot-discovery-call-script.md`
- `phase-24d-demo-invite-and-agenda.md`
- `phase-24d-pilot-fit-scorecard.md`
- `phase-24d-pilot-objection-cheat-sheet.md`
- `phase-24d-pilot-tracker-template.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-known-limitations-and-non-goals.md`
- `chartnav-security-review-packet.md`
- `chartnav-controlled-pilot-go-live-checklist.md`
- `chartnav-pilot-success-metrics.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
