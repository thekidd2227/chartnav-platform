# Phase 101 — Buyer Demo Evidence Matrix

**Status:** living evidence tracker
**Date:** 2026-06-15
**Audience:** ChartNav operator + ARCG ops lead recording which
buyer-demo evidence rows are machine-captured, manual-captured, or
skipped on a given launch SHA

## How to use

For each row below, mark the **Status** column with one of:

- **PASS** — machine-captured by the Phase 101 capture script;
  artifact path resolves under
  `artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/`.
- **MANUAL** — captured by the operator manually (screenshot,
  short narration, hand-written note). Drop the file under
  `artifacts/buyer-demo/<YYYYMMDD-HHMMSS>/manual-screenshots/`.
- **SKIP** — evidence is optional **and** was not captured this
  run. Recorded under `missing-evidence.txt`.
- **FAIL** — evidence is required **and** could not be captured.
  Buyer demo is **NO-GO** until the row clears.

Required rows that fail block the buyer demo. Optional rows that
fail or skip do not block the demo but are recorded so the
operator can hand the buyer an accurate evidence ledger.

## Matrix

| # | Evidence row | Required? | Capture method | Expected artifact path | Fallback if capture unavailable | Status |
|---|---|---|---|---|---|---|
| 1 | Login / role-based access (admin / clinician / technician / reviewer / cross-org admin) | Required | Phase 100 launch gate R1 → backend tier 1 (`test_auth`, `test_auth_modes`, `test_rbac`, `test_scoping`, `test_admin`) + manual sign-in walkthrough per Phase 93 dry-run runbook Section 2 | `artifacts/buyer-demo/<ts>/01-phase100-launch-gate.log` | Manual screenshot of each role's tab visibility per Phase 93 Section 2 → `manual-screenshots/01-roles.png` | ☐ |
| 2 | Patient + encounter header | Required | Manual rehearsal per Phase 100 buyer demo script 0:30–2:00 | n/a (operator narration) | Reference recorded clip from `artifacts/phase-62/video-clips/` if present | ☐ |
| 3 | Visit-mode ribbon (Phase 91) | Required | Manual rehearsal per Phase 100 buyer demo script 0:30–2:00 | n/a (operator narration) | Manual screenshot → `manual-screenshots/03-visit-mode.png` | ☐ |
| 4 | Laterality switcher (Phase 91) | Required | Manual rehearsal per Phase 100 buyer demo script 0:30–2:00 | n/a (operator narration) | Manual screenshot → `manual-screenshots/04-laterality.png` | ☐ |
| 5 | Fundus workflow (Phase 56 / 72) | Required | Phase 63C smoke `fundus generate/review/sign happy path` (when O1 runs) | `artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log` | Manual rehearsal per Phase 93 Section E + manual screenshot → `manual-screenshots/05-fundus.png` | ☐ |
| 6 | Anti-VEGF retina rail (Phase 78) | Required | Phase 100 launch gate R1 → Phase 88 R3 vitest covers `InjectionCommandPanel.test.tsx` | `artifacts/buyer-demo/<ts>/phase-100-controlled-pilot-launch/phase-93-pilot-launch/release-evidence/03-vitest.log` | Manual rehearsal per Phase 93 Section H + manual screenshot → `manual-screenshots/06-anti-vegf.png` | ☐ |
| 7 | Glaucoma progression cockpit (Phase 79) | Required | Phase 88 R3 vitest covers `GlaucomaProgressionCockpit.test.tsx` | as above | Manual rehearsal per Phase 93 Section I + manual screenshot → `manual-screenshots/07-glaucoma.png` | ☐ |
| 8 | Cataract surgical workflow (Phase 80) | Required | Phase 88 R3 vitest covers `CataractSurgicalWorkflowPanel.test.tsx` | as above | Manual rehearsal per Phase 93 Section J + manual screenshot → `manual-screenshots/08-cataract.png` | ☐ |
| 9 | Provider action queue (Phase 81) | Required | Phase 88 R3 vitest covers `ProviderActionItemQueue.test.tsx` / `ProviderActionItemsPanel.test.tsx` | as above | Manual rehearsal per Phase 93 Section K + manual screenshot → `manual-screenshots/09-action-queue.png` | ☐ |
| 10 | Note validation rail (Phase 82) | Required | Phase 88 R3 vitest covers `NoteQualityFlagsPanel.test.tsx` + backend tier 2 covers `test_note_validation` + `test_note_validation_acknowledgements` | `artifacts/buyer-demo/<ts>/phase-100-controlled-pilot-launch/phase-93-pilot-launch/release-evidence/01-backend.log` | Manual rehearsal per Phase 93 Section L + manual screenshot → `manual-screenshots/10-validation-rail.png` | ☐ |
| 11 | Acknowledgement persistence audit (Phase 83) | Required | Phase 100 launch gate R1 → backend tier 2 covers `test_note_validation_acknowledgements` | as above | Manual screenshot → `manual-screenshots/11-ack-audit.png` | ☐ |
| 12 | Disease staging (Phase 84) | Required | Phase 100 launch gate R1 → backend tier 2 covers `test_disease_staging` + `test_disease_staging_integrations` + vitest covers `DiseaseStagingPanel.test.tsx` | as above | Manual rehearsal per Phase 93 Section N + manual screenshot → `manual-screenshots/12-disease-staging.png` | ☐ |
| 13 | Imaging metadata (Phase 21B + 88) | Required | Phase 100 launch gate R1 → backend tier 2 covers `test_phase_21b_imaging_pipeline` + vitest covers `ImagingMetadataPanel.test.tsx` + `ImagingPipelinePanel.test.tsx` | as above | Manual rehearsal per Phase 93 Section Q + manual screenshot → `manual-screenshots/13-imaging-metadata.png` | ☐ |
| 14 | Quality intelligence (Phase 89) | Required | Phase 100 launch gate R1 → backend tier 2 + vitest covers `QualityIntelligencePanel.test.tsx` | as above | Manual rehearsal per Phase 93 Section O + manual screenshot → `manual-screenshots/14-quality.png` | ☐ |
| 15 | Medication safety (Phase 85 + 90) | Required | Phase 100 launch gate R1 → backend tier 2 covers `test_medications` + `test_medications_integrations` | as above | Manual rehearsal per Phase 93 Section P + manual screenshot → `manual-screenshots/15-medication-safety.png` | ☐ |
| 16 | Advanced clinical intelligence panel (Phase 92) | Required | Phase 100 launch gate R1 → vitest covers `AdvancedClinicalIntelligencePanel.test.tsx` + backend covers `test_advanced_clinical_intelligence` | as above | Manual rehearsal per Phase 93 Section R + manual screenshot → `manual-screenshots/16-advanced-intelligence.png` | ☐ |
| 17 | Retina visit packet export (Phase 77) | Required | Phase 100 launch gate R1 → backend tier 3 covers `test_retina_visit_packet` + vitest covers `RetinaVisitPacketPanel.test.tsx` | as above | Manual download per Phase 100 buyer demo script 12:00–13:30 + paste JSON to `manual-screenshots/17-packet.json` | ☐ |
| 18 | FHIR / export readiness (Phase 87) | Required | Phase 100 launch gate R1 → backend tier 2 covers `test_fhir_export` | as above | Manual rehearsal per Phase 93 Section S + manual screenshot → `manual-screenshots/18-fhir.png` | ☐ |
| 19 | Phase 100 gate output (`summary.txt` + `go-no-go.txt`) | Required | Phase 101 capture R1 | `artifacts/buyer-demo/<ts>/phase-100-controlled-pilot-launch/summary.txt` + `go-no-go.txt` | n/a — required | ☐ |
| 20 | Phase 63C smoke output | Optional | Phase 101 capture O1 (only when local stack + URLs answer) | `artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log` | SKIP if no local stack; recorded under `missing-evidence.txt` | ☐ |
| 21 | Playwright screenshot / video capture | Optional | Phase 101 capture O2 (only when `@playwright/test` is installed + local stack reachable) | `artifacts/buyer-demo/<ts>/screenshots/*.png` + `videos/*.webm` | SKIP if not reachable; existing Phase 62 media collected as O3; otherwise drop manual captures into `manual-screenshots/` | ☐ |
| 22 | Existing Phase 62 media collection | Optional | Phase 101 capture O3 — pulls from `artifacts/phase-62/screenshots/` + `artifacts/phase-62/video-clips/` | `artifacts/buyer-demo/<ts>/screenshots/` + `videos/` | SKIP if source dirs empty | ☐ |

## Per-SHA evidence ledger

For each capture run, record the SHA + artifact dir + per-row
status here:

| Capture timestamp | SHA | Artifact dir | Required rows PASS / FAIL | Optional rows PASS / SKIP | Operator | Buyer-demo recommendation |
|---|---|---|---|---|---|---|
| __________________ | __________ | __________ | __ / __ | __ / __ | ___________ | GO / CONDITIONAL / NO-GO |

## Forbidden evidence

The matrix never tracks any of the following. If the operator sees
anything like this in a captured artifact, **stop**, do not hand
the artifact to a buyer, and re-run after removing the source.

- Real patient identifiers (any name that isn't the seeded
  synthetic set).
- Real provider / organization / payer names.
- Real PHI (numeric values, dates, free-text notes that aren't
  seeded).
- Live FHIR endpoint responses from a real practice.
- LLM-generated content from a production vendor.
- Any "auto-coded" / "auto-billed" / "auto-submitted" /
  "auto-scheduled" / "disease worsening detected" /
  "progression confirmed" / "IOL power recommended" /
  "anti-VEGF recommended" string in the captured logs or shots.
