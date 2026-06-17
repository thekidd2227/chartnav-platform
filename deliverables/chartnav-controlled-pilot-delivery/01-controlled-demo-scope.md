# Controlled Demo Scope

**Audience:** Practice clinical owner, administrator, security
owner; ARCG ops lead
**Status:** Authoritative for this delivery package
**Real-PHI:** Not authorized by this scope. See
`06-no-real-phi-attestation.md`.

## 1. What the practice may do under this scope

Under this delivery package, the practice + ARCG operator may:

- Walk through the ChartNav Overview, Documentation, Imaging,
  Clinical, Orders & Labs (review-only), Calendar,
  Communications (internal-only), Documents, and Chat tabs.
- Sign vitals workups, visit drafts, and fundus charts against
  the seeded synthetic encounter (Morgan Lee · PT-1001 ·
  Encounter #1).
- Review the Phase 86 adaptive workspace and the Phase 91 visit-
  mode + active-laterality ribbon.
- Review the Phase 92 Advanced Clinical Intelligence panel
  (retina, glaucoma, cataract, FHIR readiness) and the safety
  boundaries it asserts.
- Download the retina visit packet (metadata-only JSON).
- Capture screenshots / video clips against the synthetic
  patient. Every captured frame must display the demo banner
  ("demo mode — no real PHI").

## 2. What the practice may **not** do under this scope

- Use real patient information of any kind. The reset script
  refuses non-loopback `DATABASE_URL`. The seeded identities are
  fake.
- Connect ChartNav to the practice's production EHR, scheduling,
  billing, registry, or messaging systems.
- Enable a production LLM, live STT, or any live vendor API.
- Submit anything (claim, registry, FHIR write-back, payer
  message, patient message) from ChartNav.
- Present this package as a HIPAA / SOC 2 / HITRUST / FDA /
  certified-EHR / EHR-replacement attestation. ChartNav is none
  of those.

## 3. Stack the operator runs

| Component | Default | Notes |
|---|---|---|
| Backend API | `http://127.0.0.1:8765` | uvicorn, SQLite, `CHARTNAV_LLM_ENABLED=0`, `CHARTNAV_ENV=local` |
| Frontend | `http://127.0.0.1:5173` | Vite dev server, `VITE_API_URL=http://127.0.0.1:8765` |
| Database | `apps/api/chartnav.db` (SQLite, loopback only) | Seeded synthetic patients/encounters |
| Identity | `clin@chartnav.local` (clinician seed) + admin / technician / reviewer seeds | Demo identities only |

The exact start commands and their guardrails live in
`07-local-demo-operator-commands.md`.

## 4. Evidence the operator produces during the demo

- `artifacts/release-evidence/<ts>/summary.txt` — Phase 88
  release evidence gate (tiered backend tests, frontend
  typecheck, vitest, 5 claim scanners, runtime safety, git diff
  --check, claim policy fixtures).
- `artifacts/phase-100-controlled-pilot-launch/<ts>/summary.txt`
  + `go-no-go.txt` — Phase 100 launch gate, with the release-
  side recommendation (CONDITIONAL GO or NO-GO).
- `artifacts/buyer-demo/<ts>/summary.txt` +
  `no-real-phi-attestation.txt` + `missing-evidence.txt` — Phase
  101 buyer-demo evidence bundle.
- (Optional, only when reachable) `artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log`
  with the 20-step Phase 63C functional smoke (clinician auth,
  vitals workflow, visit-draft workflow, fundus workflow,
  manual-note shape).

These are the four pointers ARCG hands to the practice CISO.

## 5. Hard rules during the demo

Every rule from the dry-run runbook + buyer-demo script is in
force during this scope:

- No real PHI. No production LLM. No live vendor scripts.
- No external send, no upload, no patient messaging.
- The forbidden-narration list in `03-demo-talk-track.md` is
  authoritative. Do not say or write anything claiming
  diagnosis, treatment recommendation, image interpretation,
  certified-EHR status, EHR replacement, submission, or
  autonomous behaviour.

## 6. Exit criteria — controlled fake-data pilot

A controlled fake-data pilot is **done** when:

- The practice has walked the Phase 100 GO / NO-GO form
  (`05-go-no-go-form.md`).
- The practice has signed or declined the no-real-PHI
  attestation.
- ARCG has handed the evidence bundle pointers.
- The practice and ARCG have a documented next step: continue to
  Scope B real-PHI readiness, schedule a follow-up demo, or
  close.
