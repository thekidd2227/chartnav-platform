# Phase 69 — Controlled Demo Booking and Buyer Qualification Handoff

> **Status: docs-only commercial handoff increment.** Phase 69
> converts a Phase 68 qualified outreach reply into a safe controlled
> fake-data demo booking workflow. It does not create prospects, perform
> outreach, process real PHI, approve a pilot, change product behavior,
> or deploy anything.

## 1. Start Conditions Verified

Phase 69 starts after Phase 68 merged on `main`.

Required Phase 68 files are present:

- `docs/commercial/phase-68-first-manual-outreach-cycle-review.md`
- `docs/commercial/phase-68-reply-classification-template.md`

Phase 69 uses these Phase 68 categories as entry points:

- `interested-demo-requested`
- `interested-asks-security-questions`
- `referral-to-another-role` when the referred role is identified

## 2. What Phase 69 Adds

| File | Purpose |
|---|---|
| `docs/commercial/phase-69-controlled-demo-booking-checklist.md` | Qualification gate and booking checklist for controlled fake-data demos. |
| `docs/commercial/phase-69-buyer-qualification-handoff-template.md` | Private commercial-owner to demo-operator handoff template. |
| `docs/commercial/phase-69-demo-scheduling-email-templates.md` | Safe scheduling emails and calendar copy for the fake-data demo. |
| `docs/build/phase-69-controlled-demo-booking-and-qualification-handoff.md` | Build report, scope, safety notes, checks, and GO/NO-GO. |

If the commercial claims scanner enumerates support docs, Phase 69 also
adds the three commercial files to `scripts/check_commercial_claims.sh`
for scanner coverage.

## 3. Safety Notes

Phase 69 preserves the commercial and pilot boundaries:

- no invented prospects;
- no real names, emails, phone numbers, scraped personal data, or PHI
  added to the repo;
- no outreach performed;
- no product features;
- no backend, frontend, API route, migration, website, or deploy
  change;
- no production LLM;
- no compliance certification claim;
- do not claim ChartNav is a certified EHR or replaces any EHR;
- do not claim diagnosis, autonomous documentation, image
  interpretation, orders, coding, billing, messaging, referrals,
  device integration, or remote patient monitoring.

## 4. Handoff Model

Phase 69 defines two handoffs:

1. **Commercial owner to demo operator.** Confirm buyer
   qualification, fake-data boundary, buyer role, stated workflow
   interest, safety questions, and Phase 63C smoke readiness.
2. **Demo operator to security-review path.** If the demo produces a
   real-PHI, pilot, or security-review question, route through Phase 65
   and Phase 65A materials before any real-PHI use.

Phase 69 does not duplicate the Phase 65 go/no-go gate, Phase 65A
security crosswalk, Phase 66 discovery questions, or Phase 68 reply
classification table. It connects them.

## 5. Final GO / NO-GO

**GO for scheduling a controlled fake-data demo after review** when:

- buyer qualifies under the Phase 69 checklist;
- Phase 63C smoke is green;
- fake-data boundary is acknowledged;
- no Phase 64 disqualifier is active;
- demo operator is assigned;
- the scheduling email uses Phase 69 safe copy.

**NO-GO** when:

- Phase 63C smoke is not green;
- buyer requests real PHI before security review;
- buyer asks for a capability ChartNav does not support;
- buyer requires production LLM;
- buyer requires compliance certification;
- do not proceed if the buyer requires ChartNav to be a certified EHR or
  replace an EHR;
- do not proceed if the buyer asks for diagnosis, autonomous
  documentation, image interpretation, orders, coding, billing,
  messaging, referrals, device integration, or remote patient
  monitoring.

## 6. Validation

Commands run:

```bash
bash scripts/check_commercial_claims.sh
bash scripts/check_demo_claims.sh
bash scripts/check_website_claims.sh
bash scripts/test_claim_policy_fixtures.sh
git diff --check
python3 scripts/check_runtime_safety.py
PHASE63C_API_URL="http://127.0.0.1:8765" PHASE63C_WEB_URL="http://127.0.0.1:5173" bash scripts/demo/phase63c_functional_smoke.sh
```

Results:

- Commercial claims: PASS, 0 fail / 0 warn.
- Demo claims: PASS, 0 positive-claim hits.
- Website claims: PASS, 0 fail / 0 warn.
- Claim policy fixtures: PASS.
- Runtime safety: PASS.
- `git diff --check`: PASS.
- Phase 63C functional smoke: 20 pass / 0 fail.
- Buyer-demo functional signal: `BUYER-DEMO FUNCTIONAL GO: YES`.

## 7. Recommended Next Phase

**Phase 70 — Controlled Demo Outcome Review and Security-Review
Routing.**

Phase 70 should run only after at least one controlled fake-data demo
has happened or has been meaningfully attempted. It should classify demo
outcomes, route qualified buyers into security review, and identify
whether scheduling, demo narrative, or buyer-fit assumptions need
repair.

## Related Documents

- `docs/commercial/phase-68-first-manual-outreach-cycle-review.md`
- `docs/commercial/phase-68-reply-classification-template.md`
- `docs/commercial/phase-64-buyer-qualification-checklist.md`
- `docs/commercial/phase-64-demo-asset-index.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/pilot/phase-65-controlled-pilot-go-no-go-gate.md`
- `docs/pilot/phase-65-security-review-handoff-checklist.md`
- `docs/pilot/phase-65a-security-review-evidence-crosswalk.md`
