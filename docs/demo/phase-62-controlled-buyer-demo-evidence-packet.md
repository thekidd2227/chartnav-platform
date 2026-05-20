# Phase 62 — Controlled Buyer Demo Evidence Packet

> **Internal operator artefact.** Not customer-facing marketing.
> Not a compliance attestation. Not a HIPAA / SOC 2 / EHR
> certification. Documents the dry-run + screenshots + video
> clips + safety checks that the operator runs before a buyer
> demo. **Fake-data only. No real PHI.**

## 1. Purpose

The packet is the single, dated bundle of evidence that:

- ChartNav's current product surfaces work end-to-end on fake demo
  data;
- the safety posture (review prompts, provider review/sign,
  signed-lock state, claim scanners, runtime safety validator) is
  enforced at the moment the buyer demo is scheduled;
- the operator's narration is rehearsed and constrained to the
  approved framing in `docs/demo/phase-61-buyer-qa-safe-answers.md`;
- no real PHI, no production LLM, no public marketing change has
  occurred.

The packet is **referenced by**, not embedded in, customer
deliverables. Buyers may receive **selected screenshots** and the
**3-minute highlight reel** (clip 12) under a fake-data disclaimer
— never the full packet.

## 2. Repo SHA recorded for the packet

Recorded by the operator at packet assembly time:

```
git log --oneline -1 > artifacts/phase-62/dry-runs/YYYY-MM-DD/sha.txt
```

The completed packet's SHA stamp must match the repo head when
screenshots / video were captured.

## 3. Included docs (sources in this repo)

| Doc | Path |
|---|---|
| Phase 62 preflight audit | `docs/build/phase-62-demo-dry-run-preflight-audit.md` |
| End-to-end visit script | `docs/demo/phase-62-end-to-end-demo-visit-script.md` |
| Dry-run report (template) | `docs/demo/phase-62-demo-dry-run-report.md` |
| Screenshot shot list | `docs/demo/phase-62-screenshot-shot-list.md` |
| Video clip shot list | `docs/demo/phase-62-video-clip-shot-list.md` |
| Local Desktop build delivery | `docs/demo/phase-62-local-build-delivery.md` |
| Master buyer-demo runbook | `docs/demo/phase-61-controlled-buyer-demo-runbook.md` |
| Buyer demo checklist | `docs/demo/phase-61-buyer-demo-checklist.md` |
| Buyer Q&A safe answers | `docs/demo/phase-61-buyer-qa-safe-answers.md` |
| Demo storyboard | `docs/demo/phase-61-demo-storyboard.md` |
| Phase 61A repair note | `docs/build/phase-61a-demo-package-accuracy-repair.md` |
| Current product truth | `docs/build/current-product-truth.md` |
| Release evidence checklist | `docs/release/release-evidence-checklist.md` |
| Claim policy manifest | `docs/commercial/claims-policy.json` |

## 4. Included screenshots (manual capture)

30 screenshots specified in
`docs/demo/phase-62-screenshot-shot-list.md`, saved under
`artifacts/phase-62/screenshots/01_…png` through `30_…png`. The
sandbox cannot capture display output; the operator runs the shot
list on their iMac.

A `.gitkeep` placeholder under `artifacts/phase-62/screenshots/`
keeps the path in the repo. Actual PNG files are **gitignored** by
default — operators copy completed PNGs into a dated
`artifacts/phase-62/dry-runs/YYYY-MM-DD/screenshots/` subfolder for
the packet they assemble.

## 5. Included video clips (manual capture)

12 clips specified in
`docs/demo/phase-62-video-clip-shot-list.md`, saved under
`artifacts/phase-62/video-clips/01_…mov` through `12_…mov`. Same
sandbox limitation; operators capture locally.

## 6. Validation checklist

Run all of the following before the operator signs the packet's
go/no-go:

| # | Command | Expected |
|---|---|---|
| 1 | `python3 scripts/check_runtime_safety.py` | `PASS - no unsafe runtime combinations detected.` |
| 2 | `bash scripts/check_commercial_claims.sh` | `PASSED — 0 fail / 0 warn.` |
| 3 | `bash scripts/check_website_claims.sh` | `PASSED — 0 fail / 0 warn.` |
| 4 | `bash scripts/check_demo_claims.sh` | `PASSED — 0 positive-claim hits across N demo file(s).` |
| 5 | `bash scripts/test_claim_policy_fixtures.sh` | `PASS - claim policy sync fragments are present` + `PASS - claim policy fixtures behave as expected.` |
| 6 | `bash scripts/check_alembic_safety.sh` | `PASSED - Alembic safety checks completed.` |
| 7 | `cd apps/api && python3 -m pytest tests/test_vitals_workup.py tests/test_ambient_documentation.py tests/test_fundus_charts.py tests/test_runtime_safety.py -q` | all pass |
| 8 | `cd apps/web && npx tsc --noEmit && npx vitest run && npm run build` | typecheck clean; vitest green; build succeeds |
| 9 | `git diff --check` | clean |
| 10 | `git status --short` (on `main`) | empty (no untracked / no modified) |

## 7. What this packet proves

- The fake-data demo flow works end-to-end on `main` at the recorded
  SHA, on the operator's local machine, at the recorded date/time.
- The safety posture is enforced by the runtime safety validator +
  claim scanners + Alembic safety + per-feature tests at the
  recorded SHA.
- The operator has rehearsed the full visit script and stayed inside
  the approved framing in
  `docs/demo/phase-61-buyer-qa-safe-answers.md`.
- The signed-and-locked artefact contract holds on Vitals, VisitDraft
  Assist, and Fundus Drawing Assist.
- Audit `detail` strings on every workflow action remain metadata-
  only — the canary regression tests pin this.

## 8. What this packet does **not** prove

- **Not** HIPAA certification.
- **Not** SOC 2 certification.
- **Not** ISO 27001 / HITRUST / FedRAMP certification.
- **Not** certified EHR evidence.
- **Not** production LLM approval. The packet captures the
  fake-data path; the optional OpenAI fake-data assist is **not**
  enabled.
- **Not** real-PHI approval. Every artefact in the packet uses
  synthetic data only.
- **Not** evidence of autonomous documentation, diagnosis, image
  interpretation, treatment recommendation, order / referral /
  patient-message / billing / coding automation, device integration,
  or remote patient monitoring — because ChartNav does **not** do
  any of those.
- **Not** evidence of any vendor partnership (OpenAI, Anthropic,
  IBM watsonx, Whisper, etc.). The packet's safety posture is
  vendor-neutral.

## 9. Safety boundaries the packet must preserve

The operator **halts** packet assembly if any of the following are
observed:

- Real PHI appears in any screenshot / video / completed report.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot`
  at any point during capture.
- The runtime safety validator returns `FAIL` at any point.
- A forbidden phrase from
  `docs/demo/phase-61-buyer-qa-safe-answers.md` § 9 appears in any
  artefact.
- A vendor / network error exposes an API key, full Authorization
  header, or OpenAI organisation id in a captured terminal frame.
- A raw transcript / draft body / vitals value appears in an audit
  log line that was captured.
- Sign / finalize succeeds **without** the attestation checkbox
  having been ticked (UI bug; escalate, do not capture).

The operator deletes the affected file and re-captures after
fixing the source. The dry-run report records the near-miss.

## 10. Buyer-demo go/no-go checklist

The packet is **GO** for a buyer demo only if all of:

- [ ] All 10 validation commands in § 6 pass.
- [ ] At least 25 of 30 screenshots are captured (the remaining 5
      are documented as deferred in the dry-run report).
- [ ] At least 8 of 12 video clips are captured, **including** clip
      12 (the 3-minute highlight reel).
- [ ] The Phase 62 visit script (`docs/demo/phase-62-end-to-end-
      demo-visit-script.md`) has been rehearsed end-to-end at
      least once.
- [ ] The Phase 61 buyer-demo checklist
      (`docs/demo/phase-61-buyer-demo-checklist.md`) has been
      completed (pre-demo § 1 all `[x]`).
- [ ] No P1 issue is open in the dry-run report.
- [ ] No forbidden phrase appears in any captured artefact.

If any line is unchecked, the packet is **NO-GO** and the operator
schedules another dry run.

---

## Related documents

- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-demo-dry-run-report.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/phase-62-local-build-delivery.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/demo/phase-61-buyer-demo-checklist.md`
- `docs/demo/phase-61-buyer-qa-safe-answers.md`
- `docs/build/current-product-truth.md`
- `docs/release/release-evidence-checklist.md`
- `docs/commercial/claims-policy.json`
