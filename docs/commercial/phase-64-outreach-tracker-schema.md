# ChartNav — Outreach Tracker Schema (Phase 64)

> **Markdown schema for the internal outreach tracker.** No CRM
> integration. No product-code dependency. Drop the table into a
> spreadsheet or markdown table; the field set + enums are the
> contract. Do not log PHI, real credentials, or unsupported
> claims in any row.

## 0. How to use this schema

- Create one row per buyer (practice + decision maker). One
  practice should not have two competing rows; if multiple
  contacts in the same practice are in play, use the **Notes**
  column to record them.
- Keep the table internal. Do not share rows externally.
- Update the **Outreach status** column on every interaction.
- Never enter real patient information, real credentials, or
  unsupported claims in any column.

## 1. Field set

| Field | Type | Required | Notes |
|---|---|---:|---|
| Practice name | text | yes | The practice. Never enter patient identifiers. |
| Practice type | enum | yes | `ophthalmology` / `retina` / `glaucoma` / `multi-specialty-eye-care` / `other`. |
| Practice size | enum | no | `solo` / `2-5 providers` / `6-15 providers` / `16+ providers`. Use coarse buckets. |
| Buyer contact name | text | yes | First + last; no honorifics required. |
| Buyer contact role | enum | yes | `provider-owner` / `managing-physician` / `practice-manager` / `operations-lead` / `administrator` / `other`. |
| Buyer contact email | text | no | If used for outreach; never paste any PHI in adjacent fields. |
| Contact source | enum | yes | `referral` / `linkedin` / `conference` / `direct-research` / `existing-relationship`. |
| First contact date | date | yes | YYYY-MM-DD. |
| Outreach status | enum | yes | See § 2 below. |
| Fit score | integer 1-5 | no | From `docs/commercial/phase-64-buyer-qualification-checklist.md` § C. |
| Disqualifiers triggered | text (comma list) | no | List of `phase-64-buyer-qualification-checklist.md` § B items that fired. Pause the row if non-empty. |
| Primary pain | text | no | `documentation-burden` / `structured-intake` / `handoff-friction` / `imaging-workflow` / `demo-curiosity` / `other`. |
| Demo readiness | enum | yes | See § 3 below. |
| Demo date | date | no | YYYY-MM-DD when the controlled fake-data demo was held. |
| Real-PHI discussion requested | yes/no | yes | If yes, route to security review before any real-PHI use. |
| Security review status | enum | yes | See § 4 below. |
| Pilot hypothesis | text | no | Free text. Keep as hypothesis, never as a commitment. |
| Pilot length hypothesis | enum | no | `30-day` / `60-day` / `90-day` / `not-discussed`. |
| Pricing posture | enum | yes | `not-discussed` / `discovery-only` / `written-hypothesis-sent` / `out-of-scope`. Never enter a final quote. |
| Next action | text | yes | Concrete follow-up action. |
| Next action date | date | no | YYYY-MM-DD. |
| Owner | text | yes | Internal owner — single person. |
| Last touch date | date | yes | YYYY-MM-DD of the most recent meaningful interaction. |
| Notes | text | no | No PHI, no secrets, no unsupported claims. |

## 2. Outreach status enum

| Value | Meaning |
|---|---|
| `not-contacted` | Identified as a prospect; no outreach yet. |
| `contacted` | First message (email / LinkedIn DM) sent. |
| `replied` | Buyer replied; conversation active. |
| `qualified` | Buyer passes the qualification checklist (zero disqualifiers). |
| `demo-scheduled` | Controlled fake-data demo on the calendar. |
| `demo-completed` | Controlled fake-data demo delivered. |
| `pilot-discussion` | Discussing paid pilot per `phase-64-paid-pilot-positioning.md`. |
| `security-review` | Security review in flight before any real-PHI use. |
| `paused` | Conversation paused (no reply after two follow-ups, or buyer requested pause). |
| `closed-no-fit` | Conversation closed — one or more disqualifiers from `phase-64-buyer-qualification-checklist.md` § B fired and will not change in 90 days. |

## 3. Demo readiness enum

| Value | Meaning |
|---|---|
| `not-ready` | Demo not staged. |
| `fake-data-demo-ready` | Local stack runs; Phase 63C functional smoke green; bundle wrappers refresh OK. |
| `dry-run-complete` | A dated dry-run report is signed off by the operator and a reviewer (`artifacts/phase-62/dry-runs/<date>/report.md`). |
| `buyer-demo-complete` | The buyer saw the controlled fake-data demo live and no stop-demo trigger fired. |

## 4. Security review status enum

| Value | Meaning |
|---|---|
| `not-started` | Buyer has not asked about real PHI yet. |
| `requested` | Buyer asked for security review packet (`phase-64-security-review-packet-index.md` sent). |
| `in-review` | Buyer's security team is reviewing. |
| `responded-in-writing` | We have answered the buyer's security questionnaire in writing. |
| `approved-for-next-step` | Security review accepted; BAA conversation can begin. |
| `blocked` | Security review surfaced a blocker (e.g., buyer requires HIPAA certification as a precondition). |

## 5. Pricing posture enum (do not enter a final quote)

| Value | Meaning |
|---|---|
| `not-discussed` | Pricing has not come up. |
| `discovery-only` | Pricing is a discovery topic; no number stated. |
| `written-hypothesis-sent` | A pilot hypothesis with cost framing was sent in writing. Still hypothesis, not quote. |
| `out-of-scope` | Buyer wants a final quote on day one; this row is paused or closed. |

## 6. Example row (synthetic)

| Practice name | Practice type | Buyer contact role | Outreach status | Fit score | Demo readiness | Real-PHI discussion requested | Security review status | Pilot length hypothesis | Pricing posture | Next action | Next action date | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Synthetic Eye Center (fake) | retina | provider-owner | replied | 4 | fake-data-demo-ready | no | not-started | not-discussed | not-discussed | 15-min fake-data demo | 2026-05-27 | <operator name> |

> Synthetic. No real practice. No real patient information. Only
> shown to illustrate the schema.

## 7. What never goes in any row

- Real patient names, MRNs, dates of birth, contact info, or any
  other PHI.
- Real vendor API keys, OAuth tokens, BAA drafts, or contract
  redlines.
- Customer-traction claims that are not true today (ChartNav is
  pre-pilot; the tracker reflects this).
- Forbidden phrases from
  `docs/commercial/chartnav-approved-claims-language.md` §
  forbidden phrasing.
- ROI / revenue uplift / time-savings guarantees.
- Compliance / certification claims.

## Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-demo-asset-index.md`
