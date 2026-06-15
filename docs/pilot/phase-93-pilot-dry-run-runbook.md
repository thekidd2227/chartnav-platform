# Phase 93 — Pilot Dry-Run Runbook

**Status:** operator checklist
**Date:** 2026-06-11
**Audience:** ChartNav operator running a controlled buyer or pilot
dry-run on a local stack
**Branch:** `feature/phase-93-pilot-launch-readiness-program`

## Purpose

Walk one operator through a clean fake-data dry-run that proves the
ChartNav stack is end-to-end functional before a buyer demo, a
controlled pilot kick-off, or a release-evidence capture session.

This runbook does **not** approve real PHI. Every step in this
document runs against the synthetic fake-data demo. The reset
script refuses non-local `DATABASE_URL`.

## Hard rules (verbatim)

- **No real PHI.** Local + staging are fake-data only by
  construction. The seed and reset scripts enforce this at runtime.
- **No production LLM.** Every LLM-shaped surface in ChartNav is
  deterministic / fake-adapter / out of the demo loop entirely.
- **No live vendor scripts.** Do not source `.env.prod` and do not
  point the runbook at a real practice EHR / FHIR endpoint.
- **No claims of EHR replacement / certified EHR / autonomous
  diagnosis / autonomous treatment / autonomous image
  interpretation / autonomous orders / billing / coding** — both in
  this runbook's narration and in any artifact the operator
  captures during the dry-run.

## 0. Pre-flight

| # | Step | Evidence |
|---|---|---|
| 0.1 | `git checkout main && git pull --ff-only origin main` is clean. | `git log -1 --oneline` |
| 0.2 | `bash scripts/release/chartnav_release_evidence_gate.sh` PASSED on this SHA within the last 24h. | `artifacts/release-evidence/<latest>/summary.txt` |
| 0.3 | `bash scripts/release/phase93_pilot_launch_gate.sh` PASSED on this SHA. | `artifacts/phase-93-pilot-launch/<latest>/summary.txt` |
| 0.4 | All claim scanners pass: commercial, website, demo, pilot readiness. | latest log dir |
| 0.5 | `git diff --check` clean. | shell |

If any pre-flight step fails, **stop**. Do not run the dry-run.

## 1. Demo reset

Goal: every surface starts from the canonical seeded state, with no
leftover artifacts from a previous session.

| # | Step | Expected |
|---|---|---|
| 1.1 | `bash scripts/reset_demo_state.sh` | exits 0, reports refusing non-local DB if `DATABASE_URL` is non-loopback |
| 1.2 | Backend boots: `cd apps/api && .venv/bin/uvicorn app.main:app --port 8765` | `GET /healthz` → 200 |
| 1.3 | Frontend dev server boots: `cd apps/web && npm run dev` | `http://127.0.0.1:5173` returns the ChartNav shell |
| 1.4 | Browser shows the encounter list for `clin@chartnav.local`. | encounter rows present |

## 2. Role walkthrough

Sign in with each operator identity in turn and confirm the role
banner + tab visibility match the role's allowlist.

| Role | Identity header | Required visible | Required hidden / inert |
|---|---|---|---|
| Admin | `admin@chartnav.local` | every tab, transitions allowed | no "submit claim" / "bill" / "send to patient" surfaces |
| Clinician | `clin@chartnav.local` | clinical, documentation, imaging, orders-labs (review-only) | no destructive admin tools |
| Technician | `tech@chartnav.local` | vitals workup, imaging pipeline, scribe handoff | no signing actions |
| Reviewer | `rev@chartnav.local` | reviewer-only read paths | no write actions on clinical artifacts |

## 3. Clinical spine

Run the Phase 1 clinical loop on encounter #1, fake patient PT-1001:

1. **Vitals workup** — record OD/OS IOP, visual acuity. The vitals
   panel must show the row with a `pending_review` status.
2. **Visit draft** — capture a short fake-data complaint, generate
   the deterministic draft, and confirm `draft_status = drafted`.
3. **Fundus chart** — open the OD/OS canvas, plot one annotation,
   submit, and confirm `status = pending_review`.
4. **Provider review + signed lock** — sign each artifact, confirm
   the audit trail row appears with **metadata only** (event_type,
   actor_email, actor_role, timestamp, ref_id). No clinical body
   text. No transcript text. No IOP/VA/BP numeric values.

## 4. Clinical intelligence surfaces

For each surface below, confirm the panel renders with seeded data,
shows explicit `Insufficient data` banners where there is none, and
contains **none** of the forbidden phrases listed under "Forbidden
narration" at the bottom of this doc.

| Surface | Panel | Smoke check |
|---|---|---|
| Retina visit summary | `RetinaVisitSummaryPanel` | section counts > 0 for seeded encounter |
| Retina visit packet | `RetinaVisitPacketPanel` | `download` produces a JSON file; `schema_version` is `chartnav.retina_visit_packet/1.0` |
| Anti-VEGF rail | `InjectionCommandPanel` | OD/OS lanes render, latest interval surfaces |
| Glaucoma cockpit | `GlaucomaProgressionCockpit` | OD/OS lanes, modality chips, no progression-claim language |
| Cataract workflow | `CataractSurgicalWorkflowPanel` | record list visible, no auto-scheduling |
| Provider action queue | `ProviderActionItemQueue` | items aggregate from upstream surfaces |
| Note validation rail | `NoteValidationRail` | deterministic checks render, ack flow works |
| Disease staging | `DiseaseStagingPanel` | per-eye staging rows visible |
| Medication safety | `MedicationSafetyPanel` (Phase 85 + Phase 90) | counts only; no Rx workflow |
| Quality intelligence | `QualityIntelligencePanel` | specs list, submission status pinned to `not_submitted` |
| Imaging metadata | `ImagingMetadataPanel` | modality groups present |
| Advanced Clinical Intelligence (Phase 92) | `AdvancedClinicalIntelligencePanel` | Retina / Glaucoma / Cataract / FHIR sections render with OD/OS chips |
| FHIR export readiness | block inside Phase 92 panel + Phase 87 endpoint | `submission_status: not_submitted`, `transport: none` |

## 5. Buyer-demo sequence

A buyer-facing demo should follow this exact sequence. Each step is
one click + a short verbal beat; total runtime ~12 minutes.

1. **Open ChartNav** on the encounter list. Identify it explicitly
   as a fake-data demo.
2. **Pick the seeded encounter #1.** Show the patient-encounter
   header and the Phase 91 visit-mode + active-laterality ribbon.
3. **Vitals workup** — show structured capture + pending review.
4. **Documentation tab** — show the scribe → review → finalize
   stepper (do not play live audio; the demo uses the deterministic
   fake adapter).
5. **Imaging tab** — show the OD/OS canvas + the imaging metadata
   panel; emphasise that ChartNav does not interpret images.
6. **Overview tab** — walk the Phase 86 adaptive panels in order:
   action queue, validation rail, retina summary, anti-VEGF,
   glaucoma cockpit, cataract workflow, disease staging,
   medication safety, quality intelligence, imaging metadata,
   ophthalmic medication safety, Advanced Clinical Intelligence
   (Phase 92).
7. **FHIR export readiness** — open the Phase 92 panel's FHIR
   section, verbally re-state: read-only export, never submits, no
   transport.
8. **Close** with the safety boundaries banner and the
   demo-environment disclosure.

## 6. Screenshots + video clip capture

Use the existing shot lists when capturing buyer-facing evidence —
**do not invent new claims** in the narration:

- `docs/demo/chartnav-video-clip-shot-list.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/chartnav-demo-click-path.md`

Capture rules:

- Browser must show `http://127.0.0.1:5173` or a clearly-labelled
  demo URL. No real practice domain.
- Patient identifiers must be the seeded fake values (PT-1001,
  Morgan Lee, etc.). No real patient identifiers.
- No real provider names, no real organization names, no real
  payer names.
- The demo-banner / "fake data" / "demo mode" indicator must be
  visible in every captured frame that shows clinical data.

## 7. Failure recovery

| Symptom | Action |
|---|---|
| Reset script refuses to run | Confirm `DATABASE_URL` is loopback (`sqlite:///./chartnav.db` or `postgres://…@127.0.0.1`). Do not override. |
| Backend `/healthz` returns 5xx | Check `apps/api/.venv/bin/python -m pytest -q apps/api/tests/test_auth.py` first — a degraded auth module breaks every endpoint. |
| Frontend bundles but tabs render blank | `cd apps/web && npx tsc --noEmit` and re-check the latest console error. Do not silently downgrade vitest. |
| Phase 63C smoke fails on a single step | Re-run with `bash scripts/demo/phase63c_functional_smoke.sh --reset --verbose` and consult the per-step recovery hint. Do not skip steps. |
| Release evidence gate fails on any R# check | Open the per-check log under `artifacts/release-evidence/<latest>/0?-*.log` and follow the recovery hint at the top of the gate script. Do not run the demo. |
| Claim scanner flags a doc | Open the flagged file, fix the language, re-run. Do not edit the scanner allowlist. |

## 8. Sign-off

The operator does not run a buyer demo until every checkbox below is
green:

- [ ] Pre-flight Section 0 — every row PASS.
- [ ] Demo reset Section 1 — every row PASS.
- [ ] Role walkthrough Section 2 — every role row PASS.
- [ ] Clinical spine Section 3 — every artifact reaches `signed`
      with a metadata-only audit row.
- [ ] Clinical intelligence Section 4 — every surface PASS.
- [ ] Buyer-demo sequence Section 5 — rehearsed end-to-end at least
      once on this build.
- [ ] No forbidden narration heard or written during the rehearsal.

## Forbidden narration

The dry-run operator must not say or write any of these phrases in
the rehearsal narration, the screenshots, or the videos:

- "ChartNav diagnoses"
- "ChartNav recommends treatment"
- "ChartNav interprets images"
- "ChartNav writes back to your EHR"
- "ChartNav replaces your EHR"
- "ChartNav is a certified EHR"
- "ChartNav submits claims / codes / bills"
- "ChartNav is HIPAA-certified" / "HITRUST-certified" /
  "SOC 2-certified" / "FDA-cleared"
- "ChartNav messages patients automatically"
- "Auto-coded" / "auto-billed" / "auto-submitted" / "auto-scheduled"
- "Progression confirmed" / "Disease worsening detected" /
  "IOL power recommended"
