# ChartNav pilot exit criteria — rationale

> **Why this document exists:** the pilot scope template
> (`docs/pilot/scope-template.md`) lists target numbers without
> arguing for them. This file says **why** each target was chosen
> so the 30/60/90 reviews can be honest conversations rather than
> reverse-engineered narratives.

---

## 1. Median time from transcript ingest to signed note (≤ 8 min)

- Source: `/admin/dashboard/summary.median_sign_to_export_minutes_7d`
  reports the lag between sign and export. We track the
  ingest→sign lag separately in the ChartNav-internal
  `note_lifecycle` event log because it is the bigger value on the
  clinician's clock.
- Why ≤ 8 minutes: typical dictation-to-Word workflows in
  ophthalmology run 6–12 minutes per encounter. Beating the lower
  end of that band on average is what makes ChartNav worth
  changing the workflow for. Pilot exit at the same band — or
  worse — means the product has not earned the swap.
- Honest caveat: this metric reflects ChartNav-mediated paths only.
  In `integrated_readthrough` mode some encounters bypass ChartNav
  entirely; the dashboard hint copy notes this.

## 2. Missing-flag resolution rate (≥ 70 % over 14 days)

- Source: `/admin/dashboard/summary.missing_flag_resolution_rate_14d`.
- Why ≥ 70 %: the missing-flag system is the bridge between draft
  generation and clinician sign. A < 50 % resolution rate suggests
  flags are being dismissed wholesale (not actually addressing the
  documentation gap) or that the templates are over-flagging
  benign cases.
- Honest caveat: a resolution rate above 95 % is suspicious — it
  usually means flags are being dismissed without correction. We
  expect the steady state for a healthy pilot to be 70–90 %.

## 3. Reminder completion rate (≥ 75 % rolling 30 days)

- Source: derived from the `reminders` table; not yet a dashboard
  card in Phase B, computable from `GET /reminders` filtered by
  status.
- Why ≥ 75 %: reminders are the lowest-stakes operational
  primitive in the product. A practice that cannot complete 75 %
  of recall + follow-up nudges has either too many reminders
  generated or too few staff hours to address them — both signals
  worth surfacing at the 30-day review.

## 4. Clinician satisfaction (≥ 4/5, raw)

- Source: out-of-product async survey at days 30 and 60.
- Why raw scores instead of NPS: a 2-clinician pilot has too small
  an N to report a normalized NPS without misleading the buyer.
  Raw scores with the N called out are the honest report shape.

---

## What is NOT a Phase B exit criterion

- Revenue lift / RVU lift / CPT capture rate — Phase A item 4
  ships an advisory PM/RCM handoff bundle; we explicitly do not
  generate codes, so revenue impact is not attributable to ChartNav
  in Phase B.
- HIPAA-conforming patient-portal engagement metrics — there is no
  patient portal; the post-visit summary is a magic-link surface,
  not a portal.
- Real SMS / email delivery rates — no real provider is wired in
  Phase B.

A buyer asking for any of these belongs in a Phase C conversation;
the runbook (`docs/pilot/runbook-30-60-90.md`) calls that out as
an explicit "park this for Phase C" item at the 60-day review.
