# Phase 24D — Demo Invite & Agenda

> **Phase:** 24D — Pilot Practice Selection & Outreach Packaging.
> **Audience:** sales / founder scheduling the 30-minute fake-data
> retina workflow demo with a candidate practice.
> **Companion docs:**
> `phase-24d-pilot-discovery-call-script.md` — the call before the
> demo.
> `phase-24c-retina-demo-runbook.md` — the operator's runbook for
> the demo itself.
> `phase-24d-post-demo-follow-up-template.md` — the email after
> the demo.

Use the template below to send the calendar invite + agenda. Edit
only the bracketed fields. Do not edit the **demo title**, the
**prep note**, or the **safe-claims line** — those are the
boilerplate the buyer's compliance team will read first.

---

## Demo title (do not edit)

**ChartNav Retina Workflow Demo — Fake Data Only**

---

## Duration

30 minutes (block 35 in your calendar to leave 5 minutes for
next-step scheduling).

---

## Attendees — who to invite

| Attendee | Role on the call |
|---|---|
| **Practice administrator** | confirms the lane-cycle pain and owns the operations conversation |
| **Retina physician** (or clinical champion) | confirms the clinical safety boundaries and the no-diagnosis / no-interpretation contract |
| **Technician / ops lead** (if possible) | grounds the technician-handoff and imaging-metadata flow |
| **IT / security** (if available) | starts the security-review conversation early; not blocking for the demo itself |

If only one attendee can join, prioritize the practice
administrator. The clinical champion should attend the **second**
conversation if not the first.

---

## Agenda (30 minutes total)

| Time | Topic |
|---|---|
| **0:00 – 0:03** | Clinic pain confirmation — restate the two specific lane-cycle pains we heard on discovery |
| **0:03 – 0:08** | Role dashboard overview — front desk / technician / MD / reviewer / admin |
| **0:08 – 0:18** | Morgan Lee fake-data retina workflow — end-to-end (front desk → workup → imaging metadata → retina tracking → documentation → sign-off → internal follow-up) |
| **0:18 – 0:23** | Provider-reviewed documentation + safety boundaries — every artifact is a draft until a provider signs it; ChartNav does **not** diagnose, interpret images, place orders, send referrals, message patients, bill, code, or submit claims |
| **0:23 – 0:28** | Pilot fit + security next steps — controlled fake-data pilot, real-PHI gate, BAA path |
| **0:28 – 0:30** | Next action — schedule security-review handoff, or schedule second clinical demo, or graceful close |

If the call is heading off-track (multiple forbidden-claim
questions, real-PHI urgency without security review), pull from
`phase-24d-pilot-objection-cheat-sheet.md` and adjust. Better to
end early on a clean answer than to overrun a confused agenda.

---

## Prep note (paste into the invite body, do not edit)

```
Prep note — read before the call:

- This demo uses ChartNav's seeded Morgan Lee fake-data retina
  follow-up workflow. Every name, MRN, DOB, NPI, and follow-up
  detail is synthetic.
- No real PHI is used or shown.
- ChartNav is an ophthalmology clinic workflow layer. It does
  not diagnose, interpret OCTs or fundus photographs, place
  orders, send referrals, message patients, submit claims,
  automate coding or billing, or replace your certified EHR.
- ChartNav is not marketed as HIPAA compliant or HIPAA
  certified. Before any real PHI is ever loaded into ChartNav
  for [Practice Name], the Phase 23 real-PHI gate must be
  satisfied: BAA execution, practice security review,
  production authentication, approved hosting, backups,
  monitoring, incident contacts, and written practice approval.

What the demo will show:

- Role-based clinic dashboards (front desk, technician, MD,
  reviewer, admin).
- One synthetic patient (Morgan Lee, PT-1001) moving through
  the lane cycle: front-desk readiness, technician workup,
  imaging metadata review (OCT macula + fundus photo —
  metadata only, no binary upload), retina tracking,
  provider-reviewed documentation draft, sign-off queue, and
  the internal staff follow-up task that confirms the next
  visit window.
- The provider-review banners that gate every artifact.
- The negative-assertion safety strip on the landing page.

What the demo will not show:

- Any real patient data.
- Any "auto-grade DR" / "auto-select IOL" / "auto-recommend
  anti-VEGF" affordance — those are explicit non-goals.
- Any "send to patient" / "submit referral" / "submit claim"
  affordance — those are explicit non-goals.
- Any specific OCT or fundus-camera vendor integration —
  device integrations are roadmap, not current state.

Please flag in advance if anyone in your group needs the
security-review packet before the call. Happy to send it.
```

---

## Calendar invite template

**Subject:** ChartNav Retina Workflow Demo — Fake Data Only —
[Practice Name]

**Location:** [video conference link]

**Body:**

```
Thanks for the time — looking forward to walking the lane cycle
for [Practice Name].

Agenda (30 minutes):

  0:00 – 0:03  Clinic pain confirmation
  0:03 – 0:08  Role dashboard overview
  0:08 – 0:18  Morgan Lee fake-data retina workflow
  0:18 – 0:23  Provider-reviewed documentation + safety
               boundaries
  0:23 – 0:28  Pilot fit + security next steps
  0:28 – 0:30  Next action

[Insert the "Prep note" block from above here verbatim.]

Attendees (proposed):
  - [Practice administrator name]
  - [Retina physician / clinical champion name]
  - [Technician / ops lead name, if available]
  - [IT / security name, if available]

If you'd like the security-review packet in advance, reply and
I'll send it before the call.

Thanks,
[Your Name]
ChartNav
```

---

## Pre-demo operator checklist (sender side, do **not** include in invite)

Run through the Phase 24C QA checklist before joining the call.
See `docs/demo/phase-24c-demo-qa-checklist.md` for the full
sequence. At a minimum:

- [ ] `bash scripts/reset_phase24b_retina_demo.sh` completed
      (all 8 wedge invariants reported `ok`)
- [ ] backend running (`make boot`)
- [ ] frontend running (`npm run dev` in `apps/web`)
- [ ] browser identity reset to `admin@chartnav.local`
- [ ] no real PHI on any shared screen / tab
- [ ] `bash scripts/check_demo_claims.sh` passed today
- [ ] runbook open in a side window
  (`docs/demo/phase-24c-retina-demo-runbook.md`)
- [ ] objection cheat sheet open in a side window
  (`phase-24d-pilot-objection-cheat-sheet.md`)

## References

- `phase-24d-pilot-practice-selection-criteria.md`
- `phase-24d-pilot-discovery-call-script.md`
- `phase-24d-pilot-objection-cheat-sheet.md`
- `phase-24d-post-demo-follow-up-template.md`
- `phase-24d-pilot-fit-scorecard.md`
- `phase-24d-pilot-tracker-template.md`
- `docs/demo/phase-24c-retina-demo-runbook.md`
- `docs/demo/phase-24c-demo-qa-checklist.md`
- `docs/demo/phase-24c-retina-shot-list.md`
- `chartnav-pilot-readiness-checklist.md`
- `chartnav-security-review-packet.md`
- `docs/security/chartnav-real-phi-go-live-gate.md`
