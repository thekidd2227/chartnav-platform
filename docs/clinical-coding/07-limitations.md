# Limitations (honest)

This document exists to pre-empt overclaiming. The Clinical Coding
Intelligence feature is deliberately small, strictly advisory, and
dependent on official sources that we retain verbatim. Every
limitation below is surfaced in the UI or the API response where a
buyer or auditor could reasonably encounter it.

## What this feature does not do

1. **No autonomous coding.** It never writes an ICD-10-CM code onto
   a chart, note, claim, or superbill on its own. The clinician
   picks the code; the service just makes picking easier.
2. **No reimbursement guarantee.** Nothing in this feature asserts
   that a given code will be paid, covered, or approved by any
   payer. Coverage depends on the payer's current policy, which
   changes more often than the CDC releases.
3. **No medical-necessity assertion.** The advisory hints surface
   documentation reminders, never a determination.
4. **No payer-policy certainty.** When a support-rule references
   CMS LCDs (local coverage determinations), the rule text
   explicitly directs the clinician to verify the current payer
   policy. We do not ship the LCDs themselves.
5. **No billing submission.** This feature does not bill, claim,
   transmit 837P, post charges, or integrate with a revenue-cycle
   platform.
6. **No NCCI edits.** No national-correct-coding-initiative edits,
   bundling rules, or modifier logic ship in v1.
7. **Not a coding certification.** This is reviewer-assist, not
   certified coding software. Certified coders should remain in
   the loop.
8. **No ICD-10-PCS.** Only ICD-10-CM (diagnosis) is ingested. PCS
   (procedure) is not in scope.
9. **No SNOMED / LOINC / RxNorm.** Out of scope for this feature.

## What could go wrong (and what we did about it)

| Risk | Mitigation |
|---|---|
| CDC changes the order-file column layout | Committed fixture matches the real FY2026 column layout byte-for-byte; parser tests will fail on any drift before production sees it. |
| Stale release in production | Admin audit surface shows `downloaded_at` + checksum; sync is rerunnable and idempotent. |
| Operator trusts a fixture-derived release | Version row is labeled `source_authority="CMS (local fixture)"` whenever the fixture supplied the file; UI renders the authority string literally. |
| Advisory hint mistaken for payer policy | Hint rows carry a `source_reference` column; hints that reference CMS LCDs explicitly say "verify current payer policy". |
| User deletes another user's favorite | Favorite routes filter by `user_id = caller.user_id`; no cross-user mutation is possible. |
| Tampering with raw files | `manifest_json` records per-file SHA-256; operators can re-checksum the retained raw dir and compare. |

## Roadmap items deliberately out of scope

- CPT / HCPCS suggestion (lives in the Phase C charge-capture spec).
- Automatic population of the encounter `assessment` field from
  selected codes.
- Real-time LCD lookup.
- Code linking to diagnostic tests (e.g. suggesting 92083 when
  glaucoma is selected) — belongs in the CPT suggestion layer, not
  here.
- Multi-language code descriptions. CDC ships English only in the
  order file.
- Historical releases prior to FY2025 — can be added to
  `CDC_NCHS_RELEASE_SOURCES` as needed; the schema supports
  arbitrarily many releases simultaneously.
