# Phase 61 — Controlled Buyer Demo Package Audit

> Pre-implementation audit on `main` at `7d6a8d3` (Phase 60 + Phase 59
> audit doc merged; PR #68 closed as superseded). No product behaviour
> changes are made in Phase 61. The work is **docs-only**: a master
> controlled buyer-demo runbook plus a checklist, a Q&A safe-answers
> sheet, an internal operator storyboard, and (if necessary) tiny
> consistency fixes in existing demo docs.

## 1. Existing demo docs found

| Path | Scope | Status |
|---|---|---|
| `docs/demo/chartnav-demo-operator-guide.md` | General operator guide; references `scripts/reset_demo_state.sh`. | Up-to-date. |
| `docs/demo/chartnav-demo-environment.md` | Environment setup. | Up-to-date. |
| `docs/demo/chartnav-demo-click-path.md` | Generic click path. | Older but stable; covers the Phase 19/24 era. |
| `docs/demo/chartnav-clinical-workflow-demo-script.md` | Clinical workflow narration. | Older. |
| `docs/demo/chartnav-ophthalmology-demo-script.md` | Ophthalmology-specific narration. | Older. |
| `docs/demo/chartnav-video-clip-shot-list.md` | Video shot list. | Older. |
| `docs/demo/phase-24b-retina-workflow-demo-script.md` | Phase 24B retina script. | Historical. |
| `docs/demo/phase-24b-retina-shot-list.md` | Phase 24B shot list. | Historical. |
| `docs/demo/phase-24c-retina-demo-runbook.md` | Phase 24C retina runbook. | Template for the modern runbook shape. |
| `docs/demo/phase-24c-demo-qa-checklist.md` | Phase 24C QA checklist. | Template for checklists. |
| `docs/demo/phase-24c-retina-shot-list.md` | Phase 24C shot list. | Historical. |
| `docs/demo/phase-56-fundus-demo-runbook.md` | Fundus charting demo runbook. | Current. |
| `docs/demo/phase-57-ambient-documentation-demo-runbook.md` | Ambient documentation assist demo runbook. | Current. |
| `docs/demo/phase-59-ambient-demo-qa-checklist.md` | Ambient QA lockdown checklist. | Current (Phase 60 fixed the `reset_demo.sh` nit). |
| `docs/demo/phase-60-vitals-workup-demo-runbook.md` | Technician workup + vitals runbook. | Current. |

## 2. Existing workflow docs found

| Path | Scope |
|---|---|
| `docs/workflow/ambient-documentation-assist.md` | Phase 57 feature contract + safety boundary. |
| `docs/workflow/fundus-charting.md` | Phase 55 feature contract + Phase 56 polish notes. |
| `docs/workflow/structured-vitals-workup.md` | Phase 60 feature contract. |

## 3. Gaps in the current buyer demo package

The repo has **three excellent per-feature demo runbooks** (fundus, ambient, vitals) and a generic operator guide, but **no master buyer-facing controlled-demo runbook** that:

1. Walks through the full ChartNav workflow in a single defensible end-to-end sequence (intake → ambient draft → fundus charting → review/sign → audit posture).
2. Concentrates all the safety framing + forbidden-claim language in one place.
3. Provides a single Q&A sheet covering every claim a buyer is likely to test ("Is this an EHR?", "Is OpenAI used?", "Does it diagnose?").
4. Provides a scene-by-scene storyboard the operator can rehearse with.
5. Provides a single buyer-demo checklist combining pre-demo / during-demo / post-demo gates.

Phase 61 fills exactly that gap. It does **not** replace the per-feature runbooks — those remain the authoritative source for each feature's click path. It links to them.

## 4. Risky language to avoid in any Phase 61 doc

The forbidden phrases below are all blocked by `scripts/check_commercial_claims.sh` / `check_website_claims.sh` / `check_demo_claims.sh`. Phase 61 docs use **negative phrasings** ("not HIPAA compliant", "does not replace your EHR") when these topics come up — never positive forms — and never as live narration claims:

- HIPAA compliant / HIPAA certified.
- EHR replacement / "replaces your EHR".
- Autonomous documentation / autonomous diagnosis / autonomous interpretation.
- Hands-free scribing / ambient scribe parity / AI writes the note / chart fills itself / note writes itself / production LLM documentation.
- AI diagnoses retinal disease / fundus image interpretation / OCT interpretation.
- OpenAI-powered clinical documentation / ChatGPT clinical documentation / GPT-powered / Claude-powered / Anthropic-powered / IBM watsonx-powered.
- Treatment recommendation / AI prescribes / AI orders labs.
- Live device integration / vital-signs device integration / BP cuff integration.
- Remote patient monitoring / RPM-ready / continuous patient monitoring.
- Real PHI ready / production-ready for PHI / vendor-approved for PHI / BAA-ready by default.
- Automatic billing / automatic coding / billing-aware coding / coding recommendations.
- Automatic orders / automatic referrals / send patient message / patient messaging.
- Guaranteed ROI / ROI guarantee.
- Better than Cora / Cora replacement / Cora-killer / etc.

## 5. Recommended demo order

The Phase 61 master runbook prescribes a single canonical order that matches the encounter timeline (intake first, then documentation, then specialty work, then sign-off, then audit posture). Each scene reuses the existing per-feature runbook for its detailed click path:

1. **Clinical workspace orientation** — open the demo encounter; show the tabbed workspace; point at the patient header's empty-state copy ("Not available in demo / Not recorded").
2. **Technician Workup & Structured Vitals** (Clinical tab) — load fake demo vitals; explain BMI is server-calculated; demonstrate a partial-BP warning is a *review prompt*, not a diagnosis; advance Draft → Entered.
3. **Ambient Documentation Assist** (Documentation tab) — paste the fake demo transcript; click Generate; point at the safety banner, structured facts, missing-information, and "What ChartNav did NOT do" card; advance to Ready-for-Review.
4. **Fundus Charting** (Imaging tab) — click a sample chip; Generate; point at the OD/OS clarity, the warnings panel, and the AI-drafted tag.
5. **Provider Review and Sign-off** — return to each artifact (vitals, ambient draft, fundus chart). Mark each Reviewed, then read the attestation aloud, tick the box, click Sign & Lock. Show the signed-lock banner on each surface.
6. **Audit + Release Posture** — run `python3 scripts/check_runtime_safety.py` in a side terminal; point at PASS. Open `docs/release/release-evidence-checklist.md` to show the operator artefact the demo would produce in a real release.
7. **Closing** — point at the "What ChartNav did NOT do" cards across the three signed artifacts. Re-state the safety frame.

## 6. Recommended operator flow

- One operator drives the screen; if available, one narrator reads the safe narration aloud.
- Demo identity is `clin@chartnav.local` (clinician) unless a scene needs a technician (`tech@chartnav.local`). Reviewer / front-desk identities are demonstrated only when refusal behaviour is explicitly part of the script.
- Browser zoom = 100%. Two-column layouts collapse on narrow viewports; this is intentional but reads better at default zoom.
- A second terminal is open with `python3 scripts/check_runtime_safety.py` ready to run on demand.
- The operator never opens a real `.env`, never echoes any `CHARTNAV_OPENAI_API_KEY`, and never types the literal word "production" anywhere visible on screen.

## 7. Known limitations

- The master runbook is an **operator artefact**, not a CI script. Operators must complete the pre-demo checklist by hand before every customer demo.
- The buyer Q&A sheet aligns with `docs/build/current-product-truth.md` at the time of writing. If the product truth row for a feature changes, the Q&A must be re-aligned in the same PR.
- Phase 61 does not add a video shot list; the existing `docs/demo/chartnav-video-clip-shot-list.md` covers that gap for the Phase 19/24 era. A Phase 61 video shot list is a separate phase.
- The Phase 61 docs cite the per-feature runbooks as the authoritative click paths. If a buyer asks for the deepest possible drill-down on (e.g.) fundus warnings, the operator pivots to `docs/demo/phase-56-fundus-demo-runbook.md`.
- Demo scanner's FILES list will be expanded to include the three new Phase 61 docs.

## Related documents

- `docs/build/current-product-truth.md` — single source of truth.
- `docs/commercial/claims-policy.json` — canonical forbidden-phrase manifest.
- `scripts/check_runtime_safety.py` — runtime gate.
- `docs/demo/phase-56-fundus-demo-runbook.md`, `phase-57-ambient-documentation-demo-runbook.md`, `phase-60-vitals-workup-demo-runbook.md` — per-feature runbooks.
