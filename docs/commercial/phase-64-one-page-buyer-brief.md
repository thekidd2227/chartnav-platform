# ChartNav — One-Page Buyer Brief (Phase 64)

> **Internal / shareable brief.** Use this when introducing
> ChartNav to a small or mid-size ophthalmology / retina practice
> before a controlled demo. One page. Plain language. No
> overclaims.

## What ChartNav is

ChartNav is a **provider-reviewed ophthalmology workflow layer**
that runs alongside the practice's existing systems. It supports
four narrow workflows for an eye-care visit:

1. **Technician Workup & Vitals** — manual structured intake by a
   technician, with live BMI computation, partial-BP review
   prompts, and a visible "What ChartNav did NOT do" panel.
2. **Provider-Reviewed VisitDraft Assist** — the clinician pastes
   a fake or real-text transcript; ChartNav extracts structured
   facts (chief complaint, HPI, visual acuity, IOP, imaging
   metadata, assessment context, plan-as-stated) and produces a
   draft note labelled "DRAFT — provider review required."
3. **Provider-Reviewed Fundus Drawing Assist** — the clinician
   types findings (e.g., "horseshoe tear at 10:30 OD"); ChartNav
   deterministically produces a **structured retinal diagram**
   (concentric rings + clock-hour labels + finding glyphs).
4. **Doctor review, attestation, and signed lock** — every
   artefact requires a clinician sign-off; signed artefacts are
   immutable.

## What ChartNav is not

- **Not a certified EHR** and not a replacement for the
  practice's existing EHR.
- **Not HIPAA-certified.** ChartNav is designed to support
  HIPAA-aware data-handling practices, but real-PHI use is
  conditional on a security review and a BAA.
- **Does not diagnose**, place orders, send referrals, message
  patients, bill, or code.
- **Does not interpret fundus photos or OCT images.** Fundus
  Drawing Assist works from clinician-entered findings text only.
- **Does not capture exam-room audio** and does not run an
  ambient scribe. VisitDraft Assist works from a transcript the
  clinician types or pastes.
- **No production LLM activation today.** The controlled buyer
  demo uses a deterministic stub. Real-LLM evaluation is on the
  roadmap, subject to security review.
- **Does not integrate with medical devices and does not provide remote patient monitoring** today.

## The problem ChartNav addresses

Eye-care practices carry a heavy documentation burden, repeated
manual structured intake, and handoff friction between
technician, clinician, and signed chart. ChartNav targets the
provider-reviewed parts of that flow — the parts where structured
input from a clinician or technician is the source of truth and
provider sign-off remains required.

## Controlled demo scope

A controlled fake-data demo is available for buyer review. The
demo uses the seeded "Morgan Lee · PT-1001" fake patient and
covers all four workflows above. Demo evidence includes 30
screenshots, 12 video clips, a runtime-safety validator output,
and three claim-scanner outputs (commercial / website / demo) —
all reproducible from the repo.

Functional-readiness state at the time of writing:

- Phase 63C functional smoke: **BUYER-DEMO FUNCTIONAL GO: YES**.
- Commit basis: `8d2b6dd` (Phase 63C-2 on `main`).
- All claim scanners + runtime safety + Alembic safety: **PASS**.

## Pilot next step

If the practice is interested after a controlled demo, the next
step is a paid pilot conversation. Pilot framing is hypothesis-
only today:

- 30 / 60 / 90-day controlled pilots.
- Fake-data demo first.
- Real-PHI use only after security review and explicit approval.
- Limited users / providers / locations.
- Manually measured success metrics first.
- No production LLM unless separately approved.

ChartNav is not seeking enterprise procurement, multi-site
rollout, or full health-system integration on day one. Best fit
is a provider-owner or practice-manager who can decide on a
narrow paid pilot.

## Safety note (every conversation)

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav does not diagnose, does not interpret fundus or OCT
  images, does not place orders, does not send referrals or
  patient messages, does not bill, does not code, does not
  integrate with medical devices or RPM, and is not a certified
  EHR.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/release/release-evidence-checklist.md`
