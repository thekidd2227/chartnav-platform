# ChartNav pilot onboarding checklist

> **How to use:** copy this file per pilot
> (`docs/pilot/onboarding-{practice-slug}.md`) and tick each box
> as it lands. Linked docs:
> [scope-template.md](./scope-template.md),
> [training-matrix.md](./training-matrix.md),
> [runbook-30-60-90.md](./runbook-30-60-90.md),
> [support-tier.md](./support-tier.md),
> [escalation-matrix.md](./escalation-matrix.md).

## Day 0 — kickoff call (60 min)

- [ ] Practice manager + clinical lead introduced to ARCG ops.
- [ ] Deployment mode confirmed (`standalone | integrated_readthrough`)
  and recorded in the per-pilot scope doc.
- [ ] Specialty templates enabled for the practice (general,
  glaucoma, cataract, retina) — confirm which specialties to use.
- [ ] Decision recorded: who is the clinician-lead (`is_lead = true`)
  and who is admin.
- [ ] Pilot duration confirmed (30 / 60 / 90 days) and recorded.
- [ ] Exit criteria reviewed against `exit-criteria.md`. Practice
  may negotiate the targets before signing the scope doc; defaults
  are not enforced.

## Day 0 — technical prerequisites

- [ ] Practice has 1+ iPad Pro 12.9 (or iPad Air 11) running
  iPadOS Safari 15+ (the tablet hardening pass — Phase A item 5
  — was specced against these devices).
- [ ] Practice has a desktop browser (Chrome / Safari / Edge) for
  the admin dashboard. The Operations entry point is hidden for
  non-admin / non-clinician-lead roles; that is intentional.
- [ ] Practice has decided which staff member will be the front-
  desk user issuing intake tokens.
- [ ] Practice's privacy officer has reviewed the truth-statement
  copy on `/intake/{token}` and on the post-visit summary; both
  surfaces explicitly say they are NOT a HIPAA-conforming portal.

## Day 1 — provisioning

- [ ] All staff identities created via `POST /users` (admin) with
  the correct role + `is_lead` attribute. Roles available:
  `admin`, `clinician`, `reviewer`, `front_desk`, `technician`,
  `biller_coder`.
- [ ] Authorized final signers selected (`is_authorized_final_signer = true`).
- [ ] Practice's referring providers loaded into
  `/referring-providers` (CMS LUHN_10 NPI validation enforced).
- [ ] Pilot staff each log in once and confirm their workspace
  loads correctly (role chip + permitted nav entries visible).

## First five encounters — clinician rubric

- [ ] Encounter created with the correct specialty template.
- [ ] Transcript ingested OR audio uploaded; missing-flag list
  surfaces.
- [ ] Provider resolves missing flags before signing (do NOT
  dismiss without correction — see `exit-criteria.md` §2 caveat).
- [ ] Note signed via the attestation flow (Phase A item 3); the
  lock indicator is visible.
- [ ] PM/RCM continuity export bundle generated for at least one
  encounter to confirm the bundle renders cleanly.

## Week 2 — review

- [ ] Admin pulls `/admin/dashboard/summary` and walks the six KPI
  cards with the clinical lead.
- [ ] Pilot tracker updated with the actual numbers (not screenshots
  — paste the values into the per-pilot tracker so 30/60/90 reviews
  have a continuous data stream).
- [ ] Issues triaged against the support tier
  (`support-tier.md`); any Sev-1 logged immediately.
