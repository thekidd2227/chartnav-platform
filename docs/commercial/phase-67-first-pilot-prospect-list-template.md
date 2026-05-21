# ChartNav — Phase 67 First Pilot Prospect List Template

> **What this is.** A pre-shaped starter template for the
> operator's first 10-row prospect list. **Simpler** than the
> canonical Phase 64 outreach-tracker schema
> (`docs/commercial/phase-64-outreach-tracker-schema.md`) — this
> is the **starter form** with only the columns the operator
> actually fills in the first week. Once the list reaches 10+
> active rows, migrate to the full Phase 64 schema for ongoing
> tracking.

## 0. How to use this template

- Copy the table below into a spreadsheet (Numbers, Google
  Sheets, or `notes.md`).
- Pre-populate the **Ideal target category** column with the
  Rank 1 / Rank 2 / Rank 3 buckets from
  `docs/commercial/phase-66-prospect-targeting-brief.md` § 1.
- Fill one row per prospect. **Stop at 10.** Do not scale the
  list before the first cycle completes.
- Never enter real patient information, real credentials, or
  unsupported claims in any cell.
- After Cycle 1 (Day 0 email + Day 3 + Day 7 follow-ups per
  `docs/commercial/phase-67-outreach-execution-log.md`),
  migrate active rows to the full Phase 64 schema.

## 1. Column set (10 columns, intentionally narrow)

| Column | Type | Required | Notes |
|---|---|---:|---|
| Ideal target category | enum | yes | `rank-1-retina` / `rank-2-glaucoma-or-comprehensive` / `rank-3-multi-specialty-eye-care`. Do not include Rank 4 or Rank 5 in the first 10. |
| Practice name | text | yes | Never enter patient identifiers. |
| Location (city + state) | text | yes | City + state only. Do not enter street address. |
| Specialty / workflow fit | text | yes | Two-sentence summary: what specialty the practice does + which of the four narrow ChartNav workflows fits best (intake / VisitDraft / Fundus Drawing / sign-lock). |
| Likely decision-maker role | enum | yes | `provider-owner` / `managing-physician` / `practice-manager` / `operations-lead`. If unknown, mark `unknown` and do not advance. |
| Source / referral path | enum + text | yes | `personal-network` (named contact), `conference` (event + year), `linkedin-search` (search terms used), `direct-research` (URL), or `existing-relationship` (years known). |
| Outreach status | enum | yes | `not-contacted` / `contacted` / `replied` / `qualified` / `demo-scheduled` / `demo-completed` / `pilot-discussion` / `paused` / `closed-no-fit`. Same enum as Phase 64 § 2. |
| Last touch date | date | yes | YYYY-MM-DD of the most recent meaningful contact. |
| Next step | text | yes | One concrete action with a date. Example: `Day-3 follow-up email — 2026-05-30`. |
| Disqualification reason | text (optional) | no | If `closed-no-fit`, name the Phase 64 § B disqualifier that fired. Otherwise blank. |
| Notes | text (optional) | no | Internal only. **No PHI. No secrets. No unsupported claims. No fabricated quotes from the prospect.** |

## 2. Pre-shaped starter table (paste this into a spreadsheet)

| # | Ideal target category | Practice name | Location | Specialty / workflow fit | Decision-maker role | Source / referral | Outreach status | Last touch | Next step | Disqualification reason | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 2 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 3 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 4 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 5 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 6 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 7 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 8 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 9 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |
| 10 |  |  |  |  |  |  | not-contacted |  | Day-0 founder email — <date> |  |  |

## 3. Fields intentionally NOT in this starter template

The full Phase 64 schema has 22 columns. The 10 above are the
minimum to begin Cycle 1. Fields **not** in this starter (defer
to Phase 64 when migrating):

- Practice type (specialty enum) — covered by "Ideal target category" coarsely; full enum needed only for the migrated tracker.
- Practice size, Buyer contact email — collect on first reply, not before.
- Fit score (1-5) — assign after the first response, not from research.
- Primary pain, Demo readiness, Demo date — fill in as the conversation advances.
- Real-PHI discussion requested, Security review status — only after a demo.
- Pilot hypothesis, Pilot length hypothesis, Pricing posture — only after pilot conversation begins.
- Owner — implicit (founder) at this stage.

This intentional narrowness keeps Cycle 1 fast.

## 4. Data hygiene rules

- **No PHI in any cell.** Practice names, locations, and roles are operator-facing only.
- **No private personal data scraped from any source.** Use what the prospect themselves has published.
- **No phone numbers, home addresses, or family member details** even for the founder's personal-network contacts.
- **No fabricated quotes** from the prospect. If a quote is in `Notes`, it must be a real exact quote from a real message.
- **No customer-traction claims** in `Notes`. ChartNav is pre-pilot today.
- **No PII export** of this list to any third-party tool that isn't already covered by an agreement the founder can name.

## 5. What "complete" looks like for the first 10

- All 10 rows have non-empty `Ideal target category`, `Practice name`, `Location`, `Specialty / workflow fit`, `Decision-maker role`, `Source / referral`.
- 0 rows in `closed-no-fit` before any outreach has gone out.
- 0 rows with `Source / referral = unknown` or empty.
- Each `Decision-maker role` is either filled or marked `unknown` (and `unknown` rows are deferred, not contacted blindly).
- Source mix: at least 50% from `personal-network` or `existing-relationship` for the first 10. Cold-only outreach is acceptable as a fallback but should not be the majority of the first cycle.

When that's true, begin
`docs/commercial/phase-67-outreach-execution-log.md` Day-0.

## 6. Safety note

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
- `docs/commercial/phase-64-outreach-tracker-schema.md` (full ongoing tracker schema)
- `docs/commercial/phase-64-buyer-qualification-checklist.md` (qualifier + disqualifier reference)
- `docs/commercial/phase-66-prospect-targeting-brief.md` (specialty-tiered ranking + outreach sources)
- `docs/commercial/phase-67-outreach-execution-log.md` (Day 0 / 3 / 7 / 14 sequence)
- `docs/commercial/phase-67-first-10-targets-research-guide.md` (how to identify the 10 manually)
