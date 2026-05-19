# Phase 24C — Demo QA Checklist

> **Phase:** 24C — Retina workflow demo packaging.
> **Use this every time** you run the Morgan Lee retina
> follow-up demo for a buyer, advisor, or investor.
> **Companion to:** `phase-24c-retina-demo-runbook.md` (script +
> click paths) and `phase-24c-retina-shot-list.md` (capture plan).

Tick every box in §1 and §2 before screen-sharing. If anything
fails, **do not start the demo** until the failure is resolved.
There is no graceful fallback for a broken demo — there is only
a clean reset.

---

## 1. Pre-demo (terminal + browser, 5 min before the call)

- [ ] Latest main pulled: `git checkout main && git pull --ff-only origin main`
- [ ] Working tree clean: `git status --short` is empty
- [ ] No uncommitted Phase 24C changes (unless intentionally on the
      `feature/phase-24c-retina-demo-packaging` branch for testing)
- [ ] Reset command run: `bash scripts/reset_phase24b_retina_demo.sh`
- [ ] Reset output shows `All Phase 24B wedge rows present.`
- [ ] Reset's eight wedge verifications all `ok` (none `MISSING`)
- [ ] Backend started: `make boot` shows `Uvicorn running on http://127.0.0.1:8765`
- [ ] Frontend started: `cd apps/web && npm run dev` shows
      `Local:   http://127.0.0.1:5173/`
- [ ] Browser DevTools localStorage cleanup snippet pasted once
- [ ] Identity chip in top bar reads `Identity Admin · Org 1`
- [ ] Demo Mode (Phase 15) — optional: append `?demo=1` to URL only
      if you intend to show the stepper. Not required by Phase 24C.
- [ ] Fake-data disclosure visible somewhere on the chrome
      (identity chip "Org 1 · admin" is sufficient; or the
      `/landing` safety strip)
- [ ] **"Fake data only"** said out loud to yourself once

## 2. Data verification (browser, 2 min before the call)

Open the encounters list and the Morgan Lee workspace and
verify these without screen-sharing:

- [ ] Morgan Lee row exists (`enc-row-1`) with `PT-1001` patient id
- [ ] Encounter status is `in progress` (not `completed`)
- [ ] Fake MRN / DOB visible on the patient header (no real-looking
      number; format is `PT-1001` / `1962-03-14`)
- [ ] Workspace opens with 9 tabs (Overview, Clinical /
      Ophthalmology, Documentation / EMR/EHR, Imaging, Labs /
      Orders Review, Calendar, Communications, Documents, Chat)
- [ ] Queue items present (cross-role):
  - [ ] `front@chartnav.local` → dashboard → `check_in` lane card
        non-zero
  - [ ] `front@chartnav.local` → dashboard → `follow_up` lane card
        non-zero
  - [ ] `tech@chartnav.local` → dashboard → `workup` + `imaging
        needed` cards non-zero
  - [ ] `clin@chartnav.local` → dashboard → `ready for MD` +
        `sign-off` cards non-zero
  - [ ] `admin@chartnav.local` → dashboard → **Open Queue Items**
        ≥ 7
- [ ] Retina tracking visible on the Clinical / Ophthalmology tab
      (Diabetic retinopathy / OU / 4-week interval / draft)
- [ ] OCT macula metadata visible on the Imaging tab (modality
      `oct_macula`, eye `OU`, `placeholder://` storage URI)
- [ ] Fundus photo metadata visible on the Imaging tab (modality
      `fundus_photo`, `placeholder://` storage URI)
- [ ] Provider-reviewed draft visible on Documentation tab with
      every banner copy intact (scribe / summary / brief / action
      items)
- [ ] Internal follow-up task visible in Provider Action Items
      with title `Review task only; internal staff coordination.`

## 3. Navigation smoke (browser, 2 min before the call)

Click each link / tab once and confirm the panel renders:

- [ ] Sidebar **CORE → Dashboard** loads
- [ ] Sidebar **CORE → Encounters** loads
- [ ] Sidebar **CORE → Multi-Clinic** (if visible for admin) loads
- [ ] Sidebar **CORE → Security Readiness** loads (admin only)
- [ ] Front desk queue dashboard click-through to encounter (if
      wired) does **not** 500 or 404
- [ ] Technician queue dashboard view loads
- [ ] Doctor queue dashboard view loads
- [ ] Reviewer queue dashboard view loads
- [ ] Admin queue dashboard view loads
- [ ] Encounter → **Overview** tab loads
- [ ] Encounter → **Clinical / Ophthalmology** tab loads (retina
      card visible)
- [ ] Encounter → **Documentation** tab loads (banners visible)
- [ ] Encounter → **Imaging** tab loads (study list visible)
- [ ] Encounter → **Labs / Orders Review** tab loads
- [ ] Encounter → **Communications** tab loads
- [ ] Encounter → **Documents** tab loads
- [ ] Encounter → **Chat** tab loads
- [ ] Admin dashboard reflects the wedge in Queue Aging tables

## 4. Safety sweep (browser, 1 min before the call)

Confirm none of these appear anywhere on the rendered screens
(workspace, dashboards, landing strip):

- [ ] No empty critical screens (every demoed panel has content)
- [ ] No broken queue links (no 404 / 500 toast)
- [ ] No forbidden positive claim text on screen:
  - [ ] No "HIPAA-compliant" / "HIPAA-certified"
  - [ ] No "SOC-2 certified" / "FDA cleared"
  - [ ] No "certified EHR" (positive)
  - [ ] No "autonomous diagnosis" / "automatic diagnosis"
  - [ ] No "chart fills itself" / "note writes itself"
  - [ ] No "hands-free scribing" (as a claim)
  - [ ] No "replace your EHR" / "EHR replacement"
  - [ ] No "auto-interpret OCT" / "auto-grade DR" / "auto-select
        IOL" / "auto-recommend anti-VEGF"
  - [ ] No "automatic orders" / "automatic referrals" /
        "automatic coding" / "automatic billing"
  - [ ] No "patient messaging" / "send to patient" / "portal
        push" (positive)
  - [ ] No "submit claim" / "claims submission" / "insurance
        handling"
  - [ ] No "powered by IBM" / "powered by watsonx"
  - [ ] No specific device-vendor or OCT/fundus-camera brand name
  - [ ] No "DICOM ingestion" / "binary image storage" (positive)
  - [ ] No "real PHI" / "production-ready for PHI"
- [ ] No real patient name, DOB, MRN, phone number, address, or
      photograph anywhere on screen (Morgan Lee / PT-1001 only)
- [ ] No billing / coding / insurance UI affordance visible
- [ ] No patient-messaging / portal-push UI affordance visible
- [ ] No device-integration UI affordance visible
- [ ] No "auto-interpret" / "auto-grade" badge or button anywhere

## 5. Validation (terminal, before the demo OR before every PR)

Run these once per demo day (or before merging Phase 24C):

- [ ] `bash scripts/check_commercial_claims.sh` → PASS
- [ ] `bash scripts/check_website_claims.sh` → PASS
- [ ] `bash scripts/check_live_site_claims.sh <captured.html>`
      → PASS (if the live site is in scope this week)
- [ ] `python3 -m pytest apps/api/tests/test_phase_24b_retina_wedge.py`
      → 18+ tests pass (the 18 baseline + any Phase 24C-merge-gate
      additions)
- [ ] `python3 -m pytest apps/api/tests/test_phase_20c_role_dashboards.py`
      → all green (Phase 20C must remain wedge-independent)
- [ ] `(cd apps/web && npx tsc --noEmit)` → exits 0
- [ ] `(cd apps/web && npx vitest run)` → all green
- [ ] `(cd apps/web && npm run build)` → exits 0
- [ ] `(cd apps/web && npx playwright test phase24b-retina-workflow.spec.ts)`
      → 8/8 (or current) pass — only if Playwright deps installed

## 6. Demo-day checklist (final 60 seconds before sharing screen)

- [ ] Reset script run within the last hour
- [ ] Browser tabs are clean (no unrelated tabs visible)
- [ ] Notifications muted (Slack, email, calendar)
- [ ] Second monitor primary, demo on the shared screen
- [ ] Voice-over phrases from runbook §6 reviewed
- [ ] Forbidden phrases from runbook §7 reviewed
- [ ] Fallback plan in mind (runbook §8)
- [ ] Objection-handling answers from runbook §9 in mind
- [ ] Phone / second device ready to capture failures if needed

## 7. Post-demo (within 24 hours)

- [ ] Note any screen that surprised the buyer or failed mid-call
- [ ] If a forbidden phrase slipped onto a screen, file a SEV-2
      bug and fix before the next demo (do **not** re-run the
      demo until fixed)
- [ ] If the buyer pushed back on a claim, capture the exact
      language and add to `docs/commercial/objections/`
- [ ] If anything in the runbook / shot list / this checklist was
      wrong, file a PR against this branch's docs

---

## Source-of-truth references

- `scripts/reset_phase24b_retina_demo.sh` — demo reset.
- `scripts/check_commercial_claims.sh`,
  `scripts/check_website_claims.sh`,
  `scripts/check_live_site_claims.sh` — claim-safety gates.
- `apps/api/scripts_seed.py::_seed_phase_24b_retina_wedge` —
  what gets seeded.
- `apps/api/tests/test_phase_24b_retina_wedge.py` — authoritative
  Phase 24B test.
- `apps/web/tests/e2e/phase24b-retina-workflow.spec.ts` —
  Playwright spec.
- `docs/demo/phase-24c-retina-demo-runbook.md` — narration +
  click path.
- `docs/demo/phase-24c-retina-shot-list.md` — capture plan.
- `docs/security/chartnav-real-phi-go-live-gate.md` — Phase 23
  real-PHI gate (use for objection handling).
