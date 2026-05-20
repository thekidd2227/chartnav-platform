# Phase 63B Functional Demo QA Audit

Date: 2026-05-20

Scope: audit-only functional buyer-demo QA after Phase 63A automated media capture and Phase 64 planning. No product code, backend code, API routes, tests, demo automation, media, public website, deployment configuration, real PHI, or production LLM settings were changed.

## 1. Executive summary

Buyer-demo decision: **NO-GO**.

Phase 63A media decision after functional QA: **downgrade from GO to NO-GO for buyer-demo use until functional blockers are repaired or documented with reliable operator workarounds**. The media files exist, but the current local demo stack fails critical user workflows when exercised as a clinician/admin through the running UI. Phase 63A's GO was a media-presence and capture-completion gate, not a clean end-to-end functional smoke test.

Top blockers:

1. **P0: local API database is stale.** `apps/api/chartnav.db` reports Alembic current `b3c4d5e6f7a8` while repo head is `b1c2d3e4f5a6`. Only `scribe_sessions` exists among the checked newer tables; `visit_vitals_workups`, `fundus_charts`, `imaging_studies`, and `work_queue_items` are missing. This causes backend 500s and browser "Failed to fetch" / TypeError banners.
2. **P0: Vitals, Fundus, and Ambient feature clients do not consistently use the configured API client.** `vitalsApi.ts` and `fundusApi.ts` call relative `/api/v1/...`; `ambientApi.ts` calls relative `/patients/...`. With the Vite app at `127.0.0.1:5173` and no Vite proxy configured, these calls hit the frontend dev server and return 404 or HTML, producing `HTTP 404` or `Unexpected token '<'`.
3. **P0: Technician Workup & Vitals cannot save, review, sign, or persist through the UI.** The panel renders, but `POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups` returns 404. Review/sign controls never become reachable.
4. **P0: Fundus Charts cannot generate, review, sign, or persist through the UI.** Sample chips populate text, but `POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate` returns 404. No chart editor appears.
5. **P1: Dashboard, Production Readiness, imaging, specialty tracking, and consent flows expose load failures.** Browser console shows blocked/failed fetches, and direct API probes show backend 500s for stale-table endpoints such as `/dashboards/me`, `/dashboards/admin`, and `/patients/1/imaging-studies`.

Recommendation: create **Phase 63C - Demo-Critical Functional Repair** before Phase 64 commercial implementation. Phase 64 outreach should pause until all P0/P1 blockers are fixed or downgraded with documented, repeatable workarounds.

## 2. Environment

Repo and branch:

| Item | Value |
| --- | --- |
| Working directory | `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform` |
| Audit branch | `feature/phase-63b-functional-demo-qa-audit` |
| Branch base during doc creation | `994b66b docs(demo): capture safe demo media and website video plan (#77)` |
| Recent commits present | `994b66b`, `6032732`, `5f7fcdd` |
| API | `http://127.0.0.1:8000` |
| Frontend | `http://127.0.0.1:5173` |
| API health | PASS: `{"status":"ok"}` |
| Frontend health | PASS: HTTP 200 |
| Safety env | No `CHARTNAV_` variables were set in shell output |
| Auth identities used | `admin@chartnav.local`, `clin@chartnav.local` |
| Real PHI | None used. QA-created records used synthetic `QA63B-*` patients only |
| LLM/vendor calls | None. No production LLM enabled |

Unrelated dirty files present before this audit doc was created and not touched:

```text
?? .agents/
?? .vercel/
?? apps/web/.gitignore
?? apps/web/chartnavmd-site/
?? apps/web/playwright.capture.config.ts
?? apps/web/tests/e2e/phase62_capture.spec.ts
?? docs/build/phases-1-55-comprehensive-audit.md
?? scripts/demo/capture_phase62_screenshots.mjs
?? scripts/demo/capture_phase62_video_clips.mjs
```

Seed/data state observed in UI:

| Expected demo anchor | Observed state |
| --- | --- |
| Morgan Lee / PT-1001 / Encounter #1 | Present, but no longer top record |
| User-observed Maria / MRN 12345 / Encounter #4/#5 | Reproduced in list |
| Provider casing mismatch | Reproduced: `Maria charlie` on #5 and `Maria Charlie` on #4 |
| QA synthetic records | Created during audit: `QA63B-62081` (#6) and `QA63B-68784` (#7) |

Local DB state:

```text
apps/api alembic current: b3c4d5e6f7a8
apps/api alembic heads:   b1c2d3e4f5a6 (head)
apps/api/chartnav.db tables checked:
  version=b3c4d5e6f7a8
  table=scribe_sessions
Missing checked tables:
  work_queue_items
  visit_vitals_workups
  fundus_charts
  imaging_studies
```

Audit artifacts generated outside the repo:

| Artifact | Purpose |
| --- | --- |
| `/tmp/phase63b-functional-demo-qa/results.json` | Browser console/network/result capture |
| `/tmp/phase63b-functional-demo-qa/*.png` | QA screenshots for each tested scenario |

## 3. Test matrix

| Area | Scenario | Identity | Result | Severity | Error observed | Evidence | Suspected source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Admin dashboard | Open Dashboard | admin | FAIL | P1 | `TypeError: Failed to fetch` | Browser: `/dashboards/me` failed; direct API 500 | Missing `work_queue_items`; `apps/api/app/api/role_dashboards.py` |
| Encounters list | Open Encounters | admin, clinician | PASS with data confusion | P2 | No load failure; top records are QA/Maria instead of Morgan | Browser list shows #7/#6/#5/#4 before Morgan #1 | Demo seed/reset discipline |
| Patients nav | Click Patients | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Lab / Orders nav | Click Lab / Orders | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Multi-Clinic | Open Multi-Clinic | admin | FAIL | P1 | `Failed to fetch` | Browser: `/admin/multi-clinic-summary` failed | Missing `work_queue_items`; admin rollup |
| Tasks nav | Click Tasks | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Messages nav | Click Messages | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Chat nav | Click Chat | admin | PASS-disabled | P3 | Disabled sidebar item | Browser state | Expected placeholder at sidebar level |
| Security Readiness | Open Security Readiness | admin | PASS with residual errors | P2 | Security page backend route works, but prior dashboard/multi-clinic errors remain in console | Direct route OK earlier; browser retained prior failures | Error state isolation |
| Production Readiness | Open Production Readiness | admin | FAIL | P1 | `TypeError: Failed to fetch` | Browser: `/dashboards/admin` failed; direct API 500 | Missing `work_queue_items` |
| Documents nav | Click Documents | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Reports nav | Click Reports | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| Settings nav | Click Settings | admin | PASS-disabled | P3 | Disabled with future-phase title | Browser state | Expected placeholder |
| New Encounter | Create synthetic encounter | admin | PASS with demo-data drift | P2 | Success, new #6 appears ahead of seeded patient | Browser screenshot 23 | Demo reset/state discipline |
| New Encounter | Create synthetic encounter | clinician | PASS with demo-data drift | P2 | Success, new #7 appears ahead of seeded patient | Browser screenshot 24 | Demo reset/state discipline |
| Manual event | Submit `manual_note` with string event data | direct API | FAIL expected by backend | P1 | 400 `invalid_event_data` | Direct API probe | Frontend free-text composer permits string fallback; backend requires object |
| Clinical tab | Open Clinical / Ophthalmology | clinician | FAIL | P1 | `Unexpected token '<'`; `Failed to fetch` | Browser screenshot 27 | Relative feature APIs plus stale specialty tables |
| Vitals | Load panel and fake demo vitals | clinician | PARTIAL | P0 | Panel and button work locally; list fetch errors remain | Browser screenshots 27-28 | Vitals client/API routing |
| Vitals | Save draft | clinician | FAIL | P0 | `HTTP 404` | Browser: `POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups` 404 | `apps/web/src/features/vitals/vitalsApi.ts` |
| Vitals | Review/sign/persist | clinician | FAIL | P0 | Review/sign selectors never appear | Browser screenshots 30-35 | Save failure prevents state transition |
| Documentation | Open Documentation / EMR/EHR | clinician | FAIL | P1 | `Unexpected token '<'` | Browser screenshot 36 | Ambient relative API returns Vite HTML |
| Consent | Save patient audio consent | clinician | FAIL | P1 | `Failed to fetch`; preflight blocked | Browser: `PUT http://localhost:8000/encounters/1/audio-consent` net::ERR_FAILED | Backend preflight/route issue and/or missing route handling |
| Ambient VisitDraft | Generate fake-data draft | clinician | FAIL | P0 | `HTTP 404` | Browser: `POST http://127.0.0.1:5173/patients/1/scribe-sessions` 404 | `apps/web/src/features/ambient/ambientApi.ts` |
| Ambient VisitDraft | Review/sign/persist | clinician | FAIL | P0 | Review/sign selectors never appear | Browser screenshots 39-42 | Generate failure prevents state transition |
| Shortcuts/Favorites | Search/click shortcut | clinician | FAIL | P1 | Shortcut button disabled/no insertion; prior JSON load error remains | Browser screenshots 43-45 | Active note unavailable due documentation load/generate failure |
| Imaging | Open Imaging | clinician | FAIL | P1 | `Failed to fetch`; `Unexpected token '<'` | Browser screenshot 46 | Missing `imaging_studies` plus fundus relative API |
| Fundus Charts | Select OD/sample | clinician | PARTIAL | P0 | Text populates locally but prior load error remains | Browser screenshot 47 | UI local state only |
| Fundus Charts | Generate chart | clinician | FAIL | P0 | `HTTP 404` | Browser: `POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate` 404 | `apps/web/src/features/fundus/fundusApi.ts` |
| Fundus Charts | Review/sign/persist | clinician | FAIL | P0 | Review/sign selectors never appear | Browser screenshots 49-52 | Generate failure prevents chart editor |
| Identity consistency | Verify patient/encounter order | admin, clinician | FAIL for demo-readiness | P2 | Morgan #1 exists but is displaced by Maria/QA records | Browser list snapshots | Demo reset/seed contamination |
| Phase 63A media | Compare media gate to live function | n/a | FAIL for readiness | P0 | Existing media does not prove current workflow function | Phase 63A report caveats | Capture script lacks clean-state functional assertions |

## 4. Defect inventory

### QA-63B-001 - Local API database is stale and missing demo-critical tables

Severity: **P0**

Steps to reproduce:

1. Start the existing API stack.
2. Run `cd apps/api && .venv/bin/python -m alembic current && .venv/bin/python -m alembic heads`.
3. Query `apps/api/chartnav.db` for demo-critical tables.
4. Open Dashboard, Clinical, Imaging, Vitals, or Fundus in the browser.

Expected behavior: the running demo DB is at Alembic head and contains all tables needed by shipped demo-critical features.

Actual behavior: running DB is at `b3c4d5e6f7a8`, head is `b1c2d3e4f5a6`, and checked tables such as `work_queue_items`, `visit_vitals_workups`, `fundus_charts`, and `imaging_studies` are absent. Backend logs show `sqlite3.OperationalError: no such table`.

Visible error: `TypeError: Failed to fetch`, `Failed to fetch`, `Unexpected token '<'`, or `HTTP 404` depending on the surface.

Network/API error:

```text
GET /dashboards/me -> 500
GET /dashboards/admin -> 500
GET /patients/1/imaging-studies -> 500
GET /api/v1/encounters/1/vitals-workups -> 500 when called directly against API with auth
GET /api/v1/encounters/1/fundus-charts -> 500 when called directly against API with auth
```

Backend log excerpts:

```text
sqlite3.OperationalError: no such table: work_queue_items
sqlite3.OperationalError: no such table: visit_vitals_workups
sqlite3.OperationalError: no such table: fundus_charts
sqlite3.OperationalError: no such table: imaging_studies
```

Likely source files/routes:

```text
apps/api/app/api/role_dashboards.py
apps/api/app/api/vitals_workup.py
apps/api/app/api/fundus_charts.py
apps/api/app/api/imaging_pipeline.py
apps/api/alembic/versions/
scripts/demo/phase63a_start_demo_stack.sh
```

Demo impact: blocks core buyer-demo workflow. Demo cannot be trusted without a clean reset/migration path.

Recommended owner for fix: backend/platform demo reliability.

Do not fix in this PR: audit-only.

### QA-63B-002 - Feature API clients bypass configured API base/auth and call Vite

Severity: **P0**

Steps to reproduce:

1. Open `http://127.0.0.1:5173`.
2. Set identity to `clin@chartnav.local`.
3. Open encounter #1.
4. Use Vitals, Ambient VisitDraft, or Fundus controls.

Expected behavior: feature clients call `http://localhost:8000` or the configured API URL with demo auth headers.

Actual behavior: feature clients call relative paths on the frontend origin:

```text
POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups -> 404
POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate -> 404
POST http://127.0.0.1:5173/patients/1/scribe-sessions -> 404
GET http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups -> Vite HTML shell in direct probe
GET http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts -> Vite HTML shell in direct probe
```

Visible error: `HTTP 404` and `Unexpected token '<', "<!doctype "... is not valid JSON`.

Console error:

```text
Failed to load resource: the server responded with a status of 404 (Not Found)
```

Likely source files:

```text
apps/web/src/features/vitals/vitalsApi.ts
apps/web/src/features/fundus/fundusApi.ts
apps/web/src/features/ambient/ambientApi.ts
apps/web/src/api.ts
apps/web/vite.config.ts
```

Evidence: `vitalsApi.ts` uses `const BASE = "/api/v1"`; `fundusApi.ts` uses `const BASE = "/api/v1"`; `ambientApi.ts` uses `const BASE = ""`; `apps/web/vite.config.ts` has no dev proxy. These clients do not use the repo's central API helper with configured base URL and `X-User-Email`.

Demo impact: blocks Vitals, Ambient VisitDraft, and Fundus core workflows even if the DB is migrated.

Recommended owner for fix: frontend platform/API integration.

Do not fix in this PR: audit-only.

### QA-63B-003 - Dashboard and Production Readiness load failures

Severity: **P1**

Steps to reproduce:

1. Set identity to `admin@chartnav.local`.
2. Open Dashboard.
3. Open Production Readiness.

Expected behavior: admin readiness pages load or show a controlled empty state.

Actual behavior: red banner shows `TypeError: Failed to fetch`. Browser console shows failed fetches for dashboard endpoints. Direct API calls return 500 because `work_queue_items` is absent in local DB.

Visible error:

```text
TypeError: Failed to fetch
```

Network/API error:

```text
GET http://localhost:8000/dashboards/me -> browser net::ERR_FAILED after API 500
GET http://localhost:8000/dashboards/admin -> browser net::ERR_FAILED after API 500
```

Likely source files/routes:

```text
apps/api/app/api/role_dashboards.py
apps/web/src/RoleDashboard.tsx
apps/web/src/ProductionReadinessDashboard.tsx
```

Demo impact: serious admin-demo trust issue. A buyer seeing readiness pages fail undermines the controlled-demo story.

Recommended owner for fix: backend/platform and admin frontend.

Do not fix in this PR: audit-only.

### QA-63B-004 - Multi-Clinic admin summary fails in current stack

Severity: **P1**

Steps to reproduce:

1. Set identity to `admin@chartnav.local`.
2. Click Multi-Clinic.

Expected behavior: Multi-Clinic summary loads or displays a controlled empty state.

Actual behavior: red `Failed to fetch` banner appears. Console shows `GET http://localhost:8000/admin/multi-clinic-summary net::ERR_FAILED`. This appears tied to stale DB dependency on `work_queue_items`.

Likely source files/routes:

```text
apps/api/app/api/multi_clinic.py
apps/web/src/MultiClinicDashboard.tsx
```

Demo impact: serious if admin operations are in scope for the buyer demo.

Recommended owner for fix: backend/platform and admin frontend.

Do not fix in this PR: audit-only.

### QA-63B-005 - Manual note event composer can send invalid backend payload

Severity: **P1**

Steps to reproduce:

1. Direct API reproduction:
   `POST /encounters/1/events` with `{"event_type":"manual_note","event_data":"hello"}`.
2. Compare with valid object payload:
   `{"event_type":"manual_note","event_data":{"note":"hello"}}`.

Expected behavior: frontend should shape manual-note data as an object or block submission with a clear validation message.

Actual behavior: backend correctly rejects the string with:

```json
{"detail":{"error_code":"invalid_event_data","reason":"manual_note event_data must be a JSON object"}}
```

Valid object payload returns 201.

Likely source files:

```text
apps/web/src/App.tsx
apps/api/app/api/routes.py
```

Source finding: `App.tsx` tells users "JSON is parsed if valid; otherwise sent as a string." `routes.py` requires `manual_note` `event_data` to be an object containing `note`.

Demo impact: the observed red banner is reproducible at API level and likely appears whenever free-text is submitted for a manual note event.

Recommended owner for fix: frontend encounter timeline.

Do not fix in this PR: audit-only.

### QA-63B-006 - Technician Workup & Vitals cannot save, review, sign, or persist

Severity: **P0**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Clinical / Ophthalmology.
4. Click `Load fake demo vitals`.
5. Click `Save draft`.
6. Try review/sign and refresh.

Expected behavior: fake demo values save as a draft, can advance to entered, can be reviewed, require attestation to sign, and persist after refresh.

Actual behavior: form renders and demo sample loads locally, but save calls Vite:

```text
POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups -> 404
```

Review/sign selectors do not appear because no workup is created. Direct API against backend also currently fails because `visit_vitals_workups` is missing in local DB.

Visible error:

```text
HTTP 404
Failed to fetch
```

Likely source files/routes:

```text
apps/web/src/features/vitals/VitalsWorkupPanel.tsx
apps/web/src/features/vitals/vitalsApi.ts
apps/api/app/api/vitals_workup.py
apps/api/alembic/versions/*visit_vitals_workups*.py
```

Demo impact: blocks the Phase 60 core buyer-demo feature.

Recommended owner for fix: frontend API integration plus demo DB reset/migration.

Do not fix in this PR: audit-only.

### QA-63B-007 - Specialty tracking panels leak stale-DB errors into Clinical tab

Severity: **P1**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Clinical / Ophthalmology.

Expected behavior: specialty tracking panels load or show a controlled empty state without breaking other workup surfaces.

Actual behavior: console shows failed calls for glaucoma/retina endpoints and red banners show `Failed to fetch`.

Console/network evidence:

```text
GET http://localhost:8000/patients/1/glaucoma -> net::ERR_FAILED
GET http://localhost:8000/patients/1/retina -> net::ERR_FAILED
GET http://localhost:8000/patients/1/glaucoma/iop -> net::ERR_FAILED
GET http://localhost:8000/patients/1/glaucoma/visual-fields -> net::ERR_FAILED
```

Backend logs include stale-table failures for glaucoma tables in the same run history.

Likely source files/routes:

```text
apps/web/src/SpecialtyTrackingPanel.tsx
apps/api/app/api/specialty_tracking.py
apps/api/alembic/versions/
```

Demo impact: creates noisy red banners around otherwise demo-critical clinical workflow.

Recommended owner for fix: backend/platform and clinical frontend.

Do not fix in this PR: audit-only.

### QA-63B-008 - Patient audio consent save fails

Severity: **P1**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Documentation / EMR/EHR.
4. Enter fake consent note.
5. Click `Save consent`.

Expected behavior: consent saves reliably and recording/upload controls reflect saved consent state.

Actual behavior: browser reports:

```text
PUT http://localhost:8000/encounters/1/audio-consent -> net::ERR_FAILED
Access to fetch ... blocked by CORS policy: Response to preflight request doesn't pass access control check: It does not have HTTP ok status.
```

Visible error:

```text
Failed to fetch
```

Likely source files/routes:

```text
apps/web/src/AudioConsentPanel.tsx
apps/api/app/api/audio_consent.py or route module owning /encounters/{id}/audio-consent
```

Demo impact: blocks dictation/consent story and creates uncertainty around consent state.

Recommended owner for fix: backend route/CORS/preflight and documentation frontend.

Do not fix in this PR: audit-only.

### QA-63B-009 - Ambient VisitDraft generation routes to frontend origin and fails

Severity: **P0**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Documentation / EMR/EHR.
4. Load fake sample or paste fake transcript.
5. Click generate.

Expected behavior: creates a provider-reviewed draft from fake/demo transcript data, then exposes review/sign flow.

Actual behavior:

```text
POST http://127.0.0.1:5173/patients/1/scribe-sessions -> 404
```

Review/sign controls do not appear.

Likely source files/routes:

```text
apps/web/src/features/ambient/ambientApi.ts
apps/web/src/features/ambient/AmbientDocumentationPanel.tsx
apps/api/app/api/scribe_sessions.py
```

Demo impact: blocks the Provider-Reviewed VisitDraft Assist workflow.

Recommended owner for fix: frontend API integration.

Do not fix in this PR: audit-only.

### QA-63B-010 - Clinical shortcuts/favorites are nonresponsive in failed note state

Severity: **P1**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Documentation / EMR/EHR.
4. Search shortcuts.
5. Click a shortcut/favorite.

Expected behavior: shortcut inserts into the active draft/note, and favorite star persists.

Actual behavior: the shortcut action is effectively disabled/nonresponsive because the active note/draft state is not available after documentation load/generate failures. Browser retained `Unexpected token '<'` from the broken relative API path.

Likely source files:

```text
apps/web/src/NoteWorkspace.tsx
apps/web/src/features/ambient/ambientApi.ts
```

Demo impact: serious workflow gap if the buyer demo includes shortcuts as a productivity proof point.

Recommended owner for fix: frontend documentation workspace after API integration repair.

Do not fix in this PR: audit-only.

### QA-63B-011 - Imaging/Fundus startup exposes imaging pipeline failure

Severity: **P1**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Imaging.

Expected behavior: Imaging tab loads available image metadata panels and Fundus Charts independently.

Actual behavior:

```text
GET http://localhost:8000/patients/1/imaging-studies -> net::ERR_FAILED in browser
Direct API GET /patients/1/imaging-studies -> 500
Backend log: sqlite3.OperationalError: no such table: imaging_studies
```

Likely source files/routes:

```text
apps/web/src/ImagingPipelinePanel.tsx
apps/api/app/api/imaging_pipeline.py
apps/api/alembic/versions/f7a8b9c0d1e2_phase_21b_imaging_pipeline.py
```

Demo impact: red banner appears before or alongside Fundus; undermines imaging demo reliability.

Recommended owner for fix: backend/platform demo DB plus imaging frontend error isolation.

Do not fix in this PR: audit-only.

### QA-63B-012 - Fundus Charts cannot generate, review, sign, or persist

Severity: **P0**

Steps to reproduce:

1. Set identity to `clin@chartnav.local`.
2. Open encounter #1.
3. Open Imaging.
4. Select OD.
5. Click `Horseshoe tear 10:30 OD` sample.
6. Click `Generate Chart`.
7. Try review/sign and refresh.

Expected behavior: sample findings generate a chart, SVG appears, warnings/legend appear, review/sign requires attestation, and state persists.

Actual behavior: sample text populates locally, but generate calls Vite and fails:

```text
POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate -> 404
```

No chart editor appears. Review/sign selectors do not appear. Direct API against backend also currently fails because `fundus_charts` is missing in local DB.

Likely source files/routes:

```text
apps/web/src/features/fundus/FundusChartPanel.tsx
apps/web/src/features/fundus/fundusApi.ts
apps/api/app/api/fundus_charts.py
apps/api/alembic/versions/e1f2a3041508_fundus_charts.py
```

Demo impact: blocks the Phase 55/56 core buyer-demo feature.

Recommended owner for fix: frontend API integration plus demo DB reset/migration.

Do not fix in this PR: audit-only.

### QA-63B-013 - Encounter/demo identity state is not reset to buyer-demo anchor

Severity: **P2**

Steps to reproduce:

1. Open Encounters as admin or clinician.
2. Inspect top list rows.

Expected behavior: controlled demo starts from known seeded patient `Morgan Lee / PT-1001 / Encounter #1`, or docs clearly direct operator to that record.

Actual behavior: current list shows newly created QA records and Maria records above Morgan:

```text
#7 QA63B-68784 QA Synthetic Patient Dr QA
#6 QA63B-62081 QA Synthetic Patient Dr QA
#5 12345 Maria charlie
#4 123456 Maria Charlie
#2 PT-1002 Jordan Rivera
#1 PT-1001 Morgan Lee
```

Demo impact: user can easily land on the wrong encounter. The `charlie`/`Charlie` casing mismatch adds polish risk.

Recommended owner for fix: demo reset/seed owner.

Do not fix in this PR: audit-only.

### QA-63B-014 - Phase 63A automated media GO is misleading as a functional readiness gate

Severity: **P0 for buyer-demo readiness**

Steps to reproduce:

1. Inspect `artifacts/phase-62/dry-runs/2026-05-20/report.md`.
2. Inspect `docs/build/phase-63a-automated-demo-media-capture-report.md`.
3. Compare with current live browser flow.

Expected behavior: media GO means the demo can be operated live through the same workflows.

Actual behavior: media exists, but current live workflows fail. Phase 63A report itself documents caveats:

```text
Vitals sign/lock continuity (07 == 09 == 10 by byte size). The local SQLite DB persists between scenes.
Shot 16 fallback. ... fell back to a full-page screenshot.
Clip 12 is ~20 s, not 3 min.
```

The capture script uses `maybeClick` and file-existence gates. That is reasonable for media capture, but not sufficient for live buyer-demo readiness.

Likely source files:

```text
scripts/demo/phase63a_capture_demo_media.mjs
artifacts/phase-62/dry-runs/2026-05-20/report.md
docs/build/phase-63a-automated-demo-media-capture-report.md
```

Demo impact: buyer-facing screenshots/videos may still be usable after manual review, but should not be treated as proof that the live demo works.

Recommended owner for fix: demo automation/QA.

Do not fix in this PR: audit-only.

## 5. Mandatory defect checks

| Mandatory check | Result | Notes |
| --- | --- | --- |
| invalid `manual_note` `event_data` 400 | Reproduced by direct API | String payload returns `invalid_event_data`; object payload returns 201 |
| Production Readiness TypeError Load failed | Reproduced | Browser banner `TypeError: Failed to fetch`; API 500 on dashboard |
| Dashboard TypeError Load failed | Reproduced | Browser banner `TypeError: Failed to fetch`; API 500 on dashboard |
| Consent save/load failed | Reproduced | `PUT /encounters/1/audio-consent` blocked/failed in browser |
| Vitals HTTP 404 | Reproduced | `POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups` |
| Vitals cannot save/review/sign | Reproduced | Save fails; controls never appear |
| Fundus HTTP 404 | Reproduced | `POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate` |
| Fundus Generate Chart no-op | Reproduced | Button produces 404 and no chart editor |
| Fundus cannot review/sign | Reproduced | Generate fails; controls never appear |
| Shortcuts/favorites nonresponsive | Reproduced | Shortcut disabled/no insertion in failed note state |
| Identity/encounter mismatch | Reproduced | Maria #4/#5 and QA #6/#7 precede Morgan #1 |
| Automated media GO misleading | Reproduced by comparison | Media files exist, but live function fails; report caveats confirm state persistence/fallback |

## 6. Evidence appendix

### URLs tested

```text
http://127.0.0.1:5173/
http://127.0.0.1:8000/health
http://127.0.0.1:8000/dashboards/me
http://127.0.0.1:8000/dashboards/admin
http://127.0.0.1:8000/admin/security/readiness
http://127.0.0.1:8000/admin/multi-clinic-summary
http://127.0.0.1:8000/patients/1/imaging-studies
http://127.0.0.1:8000/api/v1/encounters/1/vitals-workups
http://127.0.0.1:8000/api/v1/encounters/1/fundus-charts
http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups
http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts
```

### Failed browser network requests

Representative failures from `/tmp/phase63b-functional-demo-qa/results.json`:

```text
GET http://localhost:8000/dashboards/me -> net::ERR_FAILED
GET http://localhost:8000/dashboards/admin -> net::ERR_FAILED
GET http://localhost:8000/admin/multi-clinic-summary -> net::ERR_FAILED
GET http://localhost:8000/patients/1/imaging-studies -> net::ERR_FAILED
PUT http://localhost:8000/encounters/1/audio-consent -> net::ERR_FAILED
POST http://127.0.0.1:5173/api/v1/encounters/1/vitals-workups -> 404
POST http://127.0.0.1:5173/api/v1/encounters/1/fundus-charts/generate -> 404
POST http://127.0.0.1:5173/patients/1/scribe-sessions -> 404
```

### Console errors

Representative console messages:

```text
Access to fetch at 'http://localhost:8000/dashboards/me' from origin 'http://127.0.0.1:5173' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
Access to fetch at 'http://localhost:8000/encounters/1/audio-consent' from origin 'http://127.0.0.1:5173' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: It does not have HTTP ok status.
Failed to load resource: net::ERR_FAILED
Failed to load resource: the server responded with a status of 404 (Not Found)
```

Note: several CORS-looking browser errors are likely the browser-facing symptom of backend 500s without a CORS response header. Direct API probes and logs show stale-table backend failures beneath many of them.

### Backend log excerpts

Representative excerpts from `artifacts/phase-62/dry-runs/2026-05-20/api.log`:

```text
sqlite3.OperationalError: no such table: visit_vitals_workups
sqlite3.OperationalError: no such table: fundus_charts
sqlite3.OperationalError: no such table: imaging_studies
sqlite3.OperationalError: no such table: work_queue_items
```

Fundus direct API log excerpt:

```text
GET /api/v1/encounters/1/fundus-charts
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: fundus_charts
```

Imaging direct API log excerpt:

```text
GET /patients/1/imaging-studies
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: imaging_studies
```

### Source pointers inspected

```text
apps/web/src/features/vitals/vitalsApi.ts
apps/web/src/features/fundus/fundusApi.ts
apps/web/src/features/ambient/ambientApi.ts
apps/web/src/api.ts
apps/web/vite.config.ts
apps/web/src/App.tsx
apps/web/src/AudioConsentPanel.tsx
apps/web/src/NoteWorkspace.tsx
apps/web/src/ClinicalTabbedWorkspace.tsx
apps/api/app/main.py
apps/api/app/api/routes.py
apps/api/app/api/vitals_workup.py
apps/api/app/api/fundus_charts.py
apps/api/app/api/imaging_pipeline.py
apps/api/app/api/role_dashboards.py
apps/api/app/api/multi_clinic.py
apps/api/alembic/versions/
scripts/demo/phase63a_capture_demo_media.mjs
artifacts/phase-62/dry-runs/2026-05-20/report.md
artifacts/phase-62/dry-runs/2026-05-20/media-manifest.json
docs/build/phase-63a-automated-demo-media-capture-report.md
```

## 7. Phase recommendation

Recommended next phase: **Phase 63C - Demo-Critical Functional Repair**.

Phase 63C should repair or explicitly downgrade with reliable workarounds:

1. Demo DB reset/migration to Alembic head before any live demo.
2. Centralized frontend API client usage for Vitals, Fundus, Ambient, consent, and any remaining feature-local clients.
3. Dashboard/Production Readiness controlled empty states and table availability.
4. Vitals save/review/sign/persistence.
5. Ambient fake-data draft/review/sign/persistence.
6. Fundus generate/review/sign/persistence.
7. Manual-note event payload shaping.
8. Demo seed reset so Morgan Lee / PT-1001 / Encounter #1 is the reliable starting point, or the runbook names the actual record to use.
9. Media gate upgrade from file-presence capture to clean-state functional assertions.

Phase 64 commercial implementation should remain paused until all P0/P1 defects above are fixed, or the demo script explicitly excludes the broken surfaces with safe language and verified fallback evidence.

