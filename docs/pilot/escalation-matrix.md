# ChartNav pilot escalation matrix

> **How to use:** when the practice opens a support ticket, classify
> it against this matrix. The severity drives the response target
> and the escalation path.

## Severity definitions

| Sev | Definition                                                                                                                 | Response target  |
|-----|----------------------------------------------------------------------------------------------------------------------------|------------------|
| 1   | Unable to sign or export ANY encounter; the application is unreachable; data integrity is at risk.                          | 1 business hour  |
| 2   | Significant workflow degradation but a workaround exists. Examples: dashboard not loading; intake submission failing for one channel; missing-flag list intermittently empty. | 4 business hours |
| 3   | Minor issue, cosmetic concern, or "how do I" question. Examples: button alignment, label copy, training question.            | 2 business days  |

## Escalation path per severity

### Sev-1

1. Practice emails `pilot-ops@arcg.example` with `[Sev-1]` in the
   subject. The body must include:
   - the encounter id (or "platform" if cross-cutting)
   - the user email of the affected staff
   - a one-line description of the symptom
2. ARCG ops acknowledges within 1 business hour.
3. ARCG opens an internal incident in our tracker (not committed
   to this repo) with the practice's reference id.
4. Status updates posted to the same email thread at minimum every
   2 business hours until resolved.

### Sev-2

1. Practice emails the same address with `[Sev-2]`.
2. ARCG ops acknowledges within 4 business hours.
3. Workaround documented in the email thread; permanent fix
   tracked in our backlog with the practice's reference id.

### Sev-3

1. Practice emails the same address with `[Sev-3]` or asks during
   the optional weekly sync.
2. ARCG ops responds within 2 business days.
3. Sev-3 items are batched into the next product update note
   the practice receives.

## Outside business hours

- Sev-1 incidents reported outside business hours (US Pacific)
  are acknowledged at the start of the next business day.
- The pilot tier does NOT include 24/7 coverage. A practice that
  needs 24/7 coverage is a paid-conversion candidate; raise that
  conversation explicitly rather than implying we can absorb it.

## Honest caveats

- These are response-time commitments, NOT resolution-time SLAs.
  Resolution time depends on root cause (a query optimization
  vs. a regression vs. a vendor issue we cannot fix on our own).
- We do not maintain a public status page for the pilot
  environment. Status updates come over the email thread.
- "Business hours" means 09:00–18:00 Pacific, Monday–Friday,
  excluding US federal holidays.
