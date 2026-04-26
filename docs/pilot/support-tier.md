# ChartNav pilot support tier

> **How to use:** this is the support contract that governs the
> pilot. There is no separate signed support agreement; the master
> service agreement references this document.

## What the pilot tier includes

- **Channel:** business-hours email (`pilot-ops@arcg.example`).
- **Hours:** 09:00–18:00 Pacific, Monday through Friday, excluding
  US federal holidays. The escalation matrix
  (`escalation-matrix.md`) defines per-severity response targets.
- **Optional weekly sync:** 30 minutes, default Wednesdays 12:00 PT.
  The practice may decline; we do not assume visibility into
  usage between scheduled syncs.
- **Pilot tracker access:** the practice may request a copy of
  their per-pilot tracker at any time.

## What the pilot tier does NOT include

- 24/7 on-call / pager rotation.
- Named Customer Success Manager (CSM). Pilot is supported by
  ARCG ops directly.
- Shared Slack Connect with SLAs.
- Branded learning-management-system integration (SCORM,
  Cornerstone, etc.).
- Carrier-level SLAs on outbound SMS / email — the Phase B
  messaging layer is stub-only and renders all status labels as
  "Stub-..." while no real provider is wired.
- Real-time dashboards beyond what the in-product Operations
  surface ships (Phase 2 item 2).

## Escalation path

See [`escalation-matrix.md`](./escalation-matrix.md) for the Sev-1 /
Sev-2 / Sev-3 definitions and response targets. In summary:

- **Sev-1** — unable to sign or export any encounter — 1 business hour
- **Sev-2** — significant workflow degradation, workaround exists — 4 business hours
- **Sev-3** — minor, cosmetic, or question — 2 business days

Sev-1 incidents are paged to ARCG ops via the email address above
plus a phone-tree fallback documented at the top of the per-pilot
tracker (not committed to this repo for security).

## Conversion to paid

- The paid tier replaces this document with a contracted SLA.
- 24/7 coverage and a named CSM are paid-tier features. The
  conversion conversation is the day-60 review (see runbook).
- Until conversion, the pilot tier above is the contract.

## Honest limitations

- ARCG is the support contact in pilot. There is no third-party
  service desk.
- The severity-matrix response times are business-hours
  commitments and must be stated as such in any subsequent
  procurement review.
- We do not have a published track record of historical response
  times because there is no historical pilot volume yet —
  representations to that effect must be qualified.
