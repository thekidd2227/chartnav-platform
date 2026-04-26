# ChartNav pilot scope — template

> **How to use:** copy this file, name it after the pilot
> (`docs/pilot/scope-{practice-slug}.md`), and fill every section
> with the practice's actual numbers. Sign at the bottom before any
> production-credentialed account is provisioned. The
> `scripts/check_pilot_docs.py` lint requires that every section is
> filled — placeholder strings cause CI to fail the pilot-docs job
> (see `escalation-matrix.md` for which tokens are flagged).

---

## Parties

- **Practice name:** Example Eye Associates
- **Primary contact:** Jane Roe, Practice Manager (jane@example-eye.test)
- **Clinical lead:** Dr. Casey Clinician, MD
- **ARCG contact:** ChartNav Pilot Operations (pilot-ops@arcg.example)
- **Support path:** business-hours email + optional weekly sync (see
  `docs/pilot/support-tier.md`)

## Scope

- **Deployment mode:** `standalone` (no PM/EHR write-back; ChartNav
  is the source of the signed note for pilot purposes only)
- **Providers in pilot:** 2 (Dr. Smith — General Ophth; Dr. Lee —
  Retina)
- **Specialty templates enabled:** general_ophthalmology, retina
- **Pilot duration:** 60 days
- **Volume target:** approximately 80 encounters total over the
  pilot window (~40 per provider)

## Exit criteria (measurable, computed from `/admin/dashboard/summary`)

- **Median time from transcript ingest to signed note:** target
  ≤ 8 minutes (p50)
- **Missing-flag resolution rate (14-day rolling):** target ≥ 70 %
- **Reminder completion rate (rolling 30 days):** target ≥ 75 %
- **Clinician satisfaction score:** target ≥ 4 of 5 from the 2
  participating clinicians, collected by short async survey at day
  30 and day 60 (small N — published as raw scores, not as NPS-
  normalized values)

The dashboard cards are the source of truth for the first three
metrics. The clinician satisfaction number is collected outside the
product and recorded in the practice's pilot tracker.

## Support

- Business-hours email: `pilot-ops@arcg.example` (response targets
  in `docs/pilot/escalation-matrix.md`)
- Optional weekly sync: Wednesdays 12:00–12:30 PT (the practice may
  decline; the runbook does not assume the sync is taken)
- Escalation path:
  - **Sev-1** — unable to sign or export any encounter — 1 business hour
  - **Sev-2** — significant workflow degradation, workaround exists — 4 business hours
  - **Sev-3** — minor, cosmetic, or question — 2 business days

## Data and privacy

- **BAA signed:** yes (signed 2026-04-15; copy filed under the
  practice's master agreements folder — not committed to this repo)
- **Data residency:** US-East
- **Data handling at pilot end:** if the practice elects not to
  convert, ChartNav exports the signed-note bundle for each pilot
  encounter (PM/RCM continuity export, Phase A item 4) and purges
  the operational DB within 30 days of pilot end.

## Sign-off

| Role             | Name              | Date        |
|------------------|-------------------|-------------|
| Practice manager | Jane Roe          | 2026-04-26  |
| Clinical lead    | Dr. Casey Clinician | 2026-04-26  |
| ARCG operations  | Pat ChartNav      | 2026-04-26  |

This document is operational, not contractual. The signed master
service agreement governs the legal relationship.
