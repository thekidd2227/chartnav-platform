# Phase 93 — End-to-End Validation Checklist

**Status:** operator checklist
**Date:** 2026-06-11
**Audience:** ChartNav operator validating a build before a buyer
demo, a pilot kick-off, or a release-evidence capture

## Purpose

A single checklist that walks an operator from a freshly-reset
fake-data stack through every Phase 1 spine and Phase 2 clinical
intelligence surface, and confirms each is functionally correct
**without** introducing any clinical claim.

This is a **functional** checklist. Safety language is enforced by
the claim scanners and the runtime safety scanner; this list does
not duplicate that work.

## How to use

Run each section in order. Every row that's not green stops the
release. A row may be GREEN, AMBER (work in progress, blocking
buyer demo but not local dev), or RED (blocker).

The expected backend / web URLs are the local default:

- API: `http://127.0.0.1:8765`
- Web: `http://127.0.0.1:5173`

If you point this checklist at a different host, confirm it is a
fake-data demo stack first.

## Section A — Demo reset + boot

| # | Step | Expected | Status |
|---|---|---|---|
| A1 | `bash scripts/reset_demo_state.sh` | exit 0; refuses non-local DB | ☐ |
| A2 | Backend boots (`uvicorn` on 8765) | `GET /healthz` → 200 | ☐ |
| A3 | Frontend dev server boots (5173) | shell renders | ☐ |
| A4 | `verify_seed_invariants.py` passes | exit 0 | ☐ |
| A5 | No leftover artifacts from a prior session | encounter list shows only seeded rows | ☐ |

## Section B — Identity + role behavior

For each identity below, sign in via the dev identity selector (or
`X-User-Email` header) and confirm the role banner + tab visibility.

| # | Identity | Role | Expected | Status |
|---|---|---|---|---|
| B1 | `admin@chartnav.local` | admin | every tab visible; transitions allowed | ☐ |
| B2 | `clin@chartnav.local` | clinician | clinical write paths; cross-org rows return 404 | ☐ |
| B3 | `tech@chartnav.local` | technician | vitals workup + imaging pipeline writable; no signing | ☐ |
| B4 | `rev@chartnav.local` | reviewer | read-only across clinical surfaces | ☐ |
| B5 | `admin@northside.local` | admin (other org) | sees Northside encounters only; encounter #1 returns 404 | ☐ |

## Section C — Vitals workup (Phase 60)

| # | Step | Expected | Status |
|---|---|---|---|
| C1 | Open encounter #1 → Clinical tab → Vitals Workup | panel renders, no fake numbers in placeholder | ☐ |
| C2 | Record OD IOP = 18 mmHg | row appears with `pending_review` | ☐ |
| C3 | Record OS IOP = 20 mmHg | row appears with `pending_review` | ☐ |
| C4 | Provider reviews + signs the vitals workup | `signed_at` populated; status = `signed` | ☐ |
| C5 | Audit row appears under the encounter timeline | metadata only; no IOP value in `detail` | ☐ |

## Section D — Visit draft (Phase 65-75)

| # | Step | Expected | Status |
|---|---|---|---|
| D1 | Open Documentation tab | scribe → review → finalize stepper visible | ☐ |
| D2 | Start a scribe session (fake adapter only) | session created with deterministic transcript | ☐ |
| D3 | Generate visit draft | `draft_status = drafted`; no real LLM call | ☐ |
| D4 | Provider edits draft | edits persist | ☐ |
| D5 | Provider signs draft | `finalized_at` populated; status = `finalized` | ☐ |
| D6 | Audit row appears | metadata only; no transcript text in `detail` | ☐ |

## Section E — Fundus chart (Phase 56 / 72)

| # | Step | Expected | Status |
|---|---|---|---|
| E1 | Open Imaging tab → OD/OS retinal workbench | canvas renders | ☐ |
| E2 | Plot one OD annotation | annotation persists | ☐ |
| E3 | Submit fundus chart | status = `pending_review` | ☐ |
| E4 | Provider signs fundus chart | status = `signed`; `signed_at` populated | ☐ |

## Section F — Signed-lock + audit trail (Phase 73 + 83)

| # | Step | Expected | Status |
|---|---|---|---|
| F1 | All three Phase 1 artifacts (vitals, draft, fundus) signed | each immutable to further edits by non-admin | ☐ |
| F2 | Audit log queries return rows for each signing event | metadata only; no clinical body | ☐ |
| F3 | Acknowledgement persistence (Phase 83) | pre-sign ack rows present | ☐ |
| F4 | Cross-org caller cannot read encounter #1 audit rows | 404 | ☐ |

## Section G — Retina visit summary + packet (Phase 76 + 77)

| # | Step | Expected | Status |
|---|---|---|---|
| G1 | Open `RetinaVisitSummaryPanel` | section counts > 0 | ☐ |
| G2 | Open `RetinaVisitPacketPanel` | metadata-only packet renders | ☐ |
| G3 | Download packet JSON | `schema_version = chartnav.retina_visit_packet/1.0` | ☐ |
| G4 | Packet contains `advanced_clinical_intelligence_summary` block (Phase 92) | `submission_status = not_submitted` | ☐ |
| G5 | Packet contains `safety_boundaries` list | all asserted = true | ☐ |

## Section H — Anti-VEGF retina rail (Phase 78)

| # | Step | Expected | Status |
|---|---|---|---|
| H1 | Open `InjectionCommandPanel` | OD/OS lanes render | ☐ |
| H2 | Seed an OD injection at 8wk interval | lane reflects new injection | ☐ |
| H3 | Forbidden language audit | no "interval should be shortened/extended/recommended" | ☐ |

## Section I — Glaucoma progression cockpit (Phase 79)

| # | Step | Expected | Status |
|---|---|---|---|
| I1 | Open `GlaucomaProgressionCockpit` | OD/OS lanes + modality chips visible | ☐ |
| I2 | With IOP rows present, latest values render | trend list shows numeric values | ☐ |
| I3 | Forbidden language audit | no "progression confirmed" / "advanced glaucoma" / "surgery recommended" | ☐ |

## Section J — Cataract surgical workflow (Phase 80)

| # | Step | Expected | Status |
|---|---|---|---|
| J1 | Open `CataractSurgicalWorkflowPanel` | record list visible | ☐ |
| J2 | Add a planned-surgery record | row persists; conversion funnel updates | ☐ |
| J3 | Forbidden language audit | no "IOL power recommended" / "phaco recommended" / "auto-scheduled" | ☐ |

## Section K — Provider action queue (Phase 81)

| # | Step | Expected | Status |
|---|---|---|---|
| K1 | Open `ProviderActionItemQueue` | items aggregate from spine + Phase 78-80 | ☐ |
| K2 | Mark an item reviewed | status updates; audit row appears | ☐ |
| K3 | Cross-org caller sees only own-org items | 404 on other org's items | ☐ |

## Section L — Note validation rail (Phase 82)

| # | Step | Expected | Status |
|---|---|---|---|
| L1 | Open `NoteValidationRail` | deterministic checks render | ☐ |
| L2 | Resolve one validation row | row clears; audit row appears | ☐ |
| L3 | Forbidden language audit | no "this note is correct" / "auto-coded" | ☐ |

## Section M — Acknowledgement persistence audit (Phase 83)

| # | Step | Expected | Status |
|---|---|---|---|
| M1 | Sign an artifact that requires an acknowledgement | `ack_required` recorded | ☐ |
| M2 | Acknowledgement row visible in audit timeline | metadata only | ☐ |
| M3 | Re-signing without re-ack is blocked | explicit error | ☐ |

## Section N — Disease staging (Phase 84)

| # | Step | Expected | Status |
|---|---|---|---|
| N1 | Open `DiseaseStagingPanel` | per-eye staging rows visible | ☐ |
| N2 | Add an AMD AREDS stage row | persists; appears in retina summary stage history | ☐ |
| N3 | Forbidden language audit | no "auto-staged" / "category 4 confirmed" | ☐ |

## Section O — Quality intelligence (Phase 89)

| # | Step | Expected | Status |
|---|---|---|---|
| O1 | Open `QualityIntelligencePanel` | spec list visible | ☐ |
| O2 | Submission status pinned to `not_submitted` | yes | ☐ |
| O3 | Forbidden language audit | no "MIPS submitted" / "IRIS registry submitted" | ☐ |

## Section P — Medication safety (Phase 85 + 90)

| # | Step | Expected | Status |
|---|---|---|---|
| P1 | Open Phase 85 `MedicationSafetyPanel` | counts render | ☐ |
| P2 | Open Phase 90 ophthalmic `MedicationSafetyPanel` | per-eye counts render; `submission_status = not_submitted` | ☐ |
| P3 | Forbidden language audit | no "prescription written" / "medication change recommended" | ☐ |

## Section Q — Imaging metadata (Phase 21B + 88) 

| # | Step | Expected | Status |
|---|---|---|---|
| Q1 | Open `ImagingMetadataPanel` | modality groups visible | ☐ |
| Q2 | Mark one study reviewed | status updates; audit row appears | ☐ |
| Q3 | No image bytes are stored or transmitted | confirmed by metadata-only payload | ☐ |

## Section R — Advanced clinical intelligence (Phase 92)

| # | Step | Expected | Status |
|---|---|---|---|
| R1 | Open `AdvancedClinicalIntelligencePanel` | Retina / Glaucoma / Cataract / FHIR sections render | ☐ |
| R2 | Phase 91 visit-mode + active-laterality chips reflect workspace state | yes | ☐ |
| R3 | Insufficient-data banners surface when no seeded data | yes | ☐ |
| R4 | All five safety boundaries asserted | yes | ☐ |
| R5 | Forbidden language audit | no autonomy / interpretation / treatment / submission phrases | ☐ |

## Section S — FHIR export readiness (Phase 87)

| # | Step | Expected | Status |
|---|---|---|---|
| S1 | Open `GET /api/v1/fhir/*` (read-only) | DocumentReference renders | ☐ |
| S2 | `submission_status = not_submitted` | yes | ☐ |
| S3 | `transport = none` | yes | ☐ |
| S4 | No write endpoints exist | confirmed by route table | ☐ |

## Section T — Release evidence gate

| # | Step | Expected | Status |
|---|---|---|---|
| T1 | `bash scripts/release/chartnav_release_evidence_gate.sh` | `OVERALL: PASS` in summary.txt | ☐ |
| T2 | `bash scripts/release/phase93_pilot_launch_gate.sh` | `OVERALL: PASS` in summary.txt | ☐ |
| T3 | All claim scanners green | commercial, website, demo, pilot readiness, runtime safety | ☐ |
| T4 | `git diff --check` clean | yes | ☐ |

## Sign-off

A build is **not validated** until every row above is green. The
operator records:

- the date + time + git SHA of the last successful run,
- the path to the artifact dir of the last successful release
  evidence gate,
- the path to the artifact dir of the last successful Phase 93
  gate.

These three pointers are the operator's proof-of-state for the
dry-run / buyer demo / pilot kick-off that follows.

## Out of scope

- Real PHI. Real-PHI gates live in
  `docs/security/phase-93-real-phi-readiness-review.md`.
- Production LLM. No production LLM is part of any validated
  build.
- Live vendor scripts. Do not run `dev_live_watsonx_eval.py` as
  part of validation.
- Real practice integration. The release stack does not connect to
  a real EHR / FHIR endpoint / billing system.
