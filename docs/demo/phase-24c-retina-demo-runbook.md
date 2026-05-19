# Phase 24C — Morgan Lee Retina Follow-Up Sales Demo Runbook

> **Phase:** 24C — Retina workflow demo packaging.
> **Audience:** sales engineer / founder / clinical champion
> driving a live fake-data demo for an ophthalmology practice
> owner or investor.
> **Companion docs:**
> `phase-24b-retina-workflow-demo-script.md` — the narration
> source-of-truth from Phase 24B.
> `phase-24c-retina-shot-list.md` — screen capture plan.
> `phase-24c-demo-qa-checklist.md` — pre-call QA.

## 1. Purpose

Phase 24B built one deterministic fake-data retina follow-up
workflow for Morgan Lee that proves ChartNav is an
**ophthalmology clinic workflow coordination layer**, not a
generic AI scribe, not a dashboard toy, not a pile of
disconnected panels. Phase 24C **packages** that wedge so any
trained operator can run the demo from a clean reset in under
ten minutes, every time, with no surprises and zero overclaiming.

The demo proves four things in this order:

1. ChartNav coordinates the work across clinic roles (front desk
   → tech → MD → reviewer → follow-up).
2. ChartNav surfaces structured ophthalmology data (retina
   tracking + imaging metadata) without claiming to interpret it.
3. Every artifact is provider-reviewed; nothing is autonomous.
4. ChartNav does not message patients, place orders, send
   referrals, bill, code, submit claims, or replace the EHR.

## 2. Pre-call setup (5 minutes before the meeting)

```bash
# 1. Pull the approved demo branch / release.
git checkout main && git pull --ff-only origin main

# 2. Reset the demo environment (deterministic state, fake data
#    only, refuses to run against staging/production).
bash scripts/reset_phase24b_retina_demo.sh

# 3. Start the backend (port 8765 by default).
make boot

# 4. In a second terminal, start the frontend.
cd apps/web && npm run dev -- --host 127.0.0.1 --port 5173

# 5. Open http://127.0.0.1:5173/ in the browser. The default
#    identity is admin@chartnav.local (seeded).
```

Confirm before joining the call:

- The `make boot` window shows `Uvicorn running on …`.
- The frontend logs show no error.
- The top of the page shows the identity chip
  `Identity Admin · Org 1` (capitalized — Phase 19 chip).
- No real PHI is anywhere — say "fake data only" out loud once
  to yourself before screen-sharing.

## 3. Reset command — exact details

### Command

```bash
bash scripts/reset_phase24b_retina_demo.sh
```

### Expected output (truncated)

```
ChartNav Phase 24C demo reset — Morgan Lee retina follow-up.
Fake demo data only. No real PHI. No device integrations.

1. Resetting the local dev DB (alembic migrate + seed)…
   python:  apps/api/.venv/bin/python  (or python3 fallback)
   dev db:  apps/api/chartnav.db
   ok — dev DB rebuilt with Phase 24B wedge enabled.

2. Verifying Phase 24B wedge rows in apps/api/chartnav.db
   ok       Morgan Lee patient row (PT-1001) (1)
   ok       Dr. Carter provider row (1)
   ok       Phase 24B wedge queue items (7 lanes) (7)
   ok       Wedge queue items have assigned_user_id (role bind) (7)
   ok       Retina tracking row (diabetic retinopathy / 4 weeks) (1)
   ok       Imaging studies: OCT macula + fundus photo (2)
   ok       Imaging files use placeholder:// storage URIs (2)
   ok       Internal follow-up action item (1)

   All Phase 24B wedge rows present.

3. Clearing browser-side demo state.
   Paste the following into the browser DevTools console once:
   try { … localStorage.removeItem … } …

4. Buyer-safety reminders … (fake data, no real PHI, …)

Phase 24C demo reset complete.
```

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `REFUSED: DATABASE_URL is set to '…'` | `DATABASE_URL` points at a non-SQLite target | `unset DATABASE_URL` (or set to `sqlite:///<path>`) and re-run |
| `REFUSED: CHARTNAV_ENV='production'` | Environment hint blocks dev resets | This script is for local demo only — fix the environment, do **not** disable the guard |
| `MISSING  Phase 24B wedge queue items` | Seed didn't run with the wedge enabled | The script exports `CHARTNAV_SEED_PHASE_24B_WEDGE=1` automatically; if it still fails, run `python3 apps/api/scripts_seed.py` manually with that env set |
| `alembic.runtime.migration` errors | DB schema is stale or partial | Delete `apps/api/chartnav.db` manually and re-run |
| Verifier exits before the reminders | A wedge row count failed | Re-run the script; if the failure persists, run `pytest apps/api/tests/test_phase_24b_retina_wedge.py` to localize the regression |

## 4. Login / user roles

Demo identities (all seeded by `scripts_seed.py`; no real PHI;
demo-eye-clinic = Org 1):

| Role | Email | Display name | Used in stop |
|---|---|---|---|
| Admin | `admin@chartnav.local` | ChartNav Admin | Stop 1, 9 |
| Front desk | `front@chartnav.local` | Frankie Front-Desk | Stop 2 |
| Technician | `tech@chartnav.local` | Taylor Technician | Stop 3 |
| Clinician (Dr. Carter) | `clin@chartnav.local` | Casey Clinician | Stop 4, 6, 7, 8 |
| Reviewer | `rev@chartnav.local` | Riley Reviewer | Stop 9 |

Switch identities via the chip in the top bar
(`identity-select` testid). The identity persists in
`localStorage` under `chartnav.devIdentity`.

## 5. Exact click path — 9 stops, 6–9 minutes

Each stop has a one-line **say** and a numbered click path.
Adapted from `phase-24b-retina-workflow-demo-script.md`.

### Stop 1 — Cover + safety contract *(45 s)*

**Say:** "We'll follow one fake patient — Morgan Lee — through a
retina follow-up. Provider-reviewed end to end. Fake data only."

**Click:** none. Show the top bar identity chip
(`Identity Admin · Org 1`). Optional: open
`http://127.0.0.1:5173/landing` for the safety strip.

### Stop 2 — Front-desk dashboard *(45 s)*

**Say:** "Front desk sees Morgan's check-in arrive in the right
lane. After the visit closes, ChartNav puts an **internal staff**
follow-up task back on this lane — never a patient message."

**Click:**
1. Switch identity → `front@chartnav.local`.
2. Sidebar → **CORE → Dashboard**.
3. Show **Today's Schedule** / **Check-In Pending** / **Follow-Up**
   count cards.
4. Scroll to **Recent & Due Items** — point to `check_in` and
   `follow_up` rows tied to Morgan.

### Stop 3 — Technician dashboard *(45 s)*

**Say:** "Workup + imaging-needed live in one queue. ChartNav
does **not** interpret OCT or grade DR."

**Click:**
1. Switch identity → `tech@chartnav.local`.
2. **Workup Queue** / **Imaging Needed** / **Ready for Doctor**
   cards non-zero.
3. Scroll to **My Queue** — `technician_workup` + `imaging_needed`
   rows visible.

### Stop 4 — Doctor dashboard *(60 s)*

**Say:** "Ready for MD, draft documentation, sign-off queue — all
on one screen. Sign-off is provider-driven, never automatic."

**Click:**
1. Switch identity → `clin@chartnav.local`.
2. **Ready for MD** / **Sign-Off Queue** / **High-Priority** cards
   non-zero.
3. Scroll to **My Encounters** — `ready_for_doctor`,
   `documentation`, `signoff_needed` rows visible.

### Stop 5 — Open Morgan Lee *(30 s)*

**Say:** "One row → one workspace. No scavenger hunt."

**Click:**
1. Sidebar → **CORE → Encounters**.
2. Click `enc-row-1` (Morgan Lee, PT-1001).
3. The 9-tab workspace appears; default Overview tab.

### Stop 6 — Clinical / Ophthalmology tab *(60 s)*

**Say:** "Retina tracking is **structured intent** — not a
diagnosis. ChartNav records what the provider entered."

**Click:**
1. Click the `Clinical / Ophthalmology` tab.
2. **Specialty Tracking → Retina** card shows diabetic
   retinopathy / moderate non-proliferative / OU / 4-week
   interval / draft.

### Stop 7 — Imaging tab *(60 s)*

**Say:** "Metadata only. `placeholder://` is the demo contract.
No binary upload, no DICOM claim, no device-vendor claim."

**Click:**
1. Click the `Imaging` tab.
2. **Imaging Pipeline → Studies** with OCT macula + fundus photo.
3. Click a study row; the file row shows the `placeholder://`
   URI.

### Stop 8 — Documentation tab *(60 s)*

**Say:** "ChartNav drafts. Providers decide. Banners are the
contract, not decoration."

**Click:**
1. Click the `Documentation / EMR/EHR` tab.
2. Scribe Session banner ("provider review required").
3. Patient Summary banner ("Do not send to patient").
4. Provider Action Items panel — point to the seeded internal
   follow-up task (`Review task only; internal staff
   coordination.`).

### Stop 9 — Reviewer + admin dashboards *(60 s)*

**Say:** "Same seven seeded rows surface across reviewer and
admin. Five role dashboards, one workspace, zero autonomous
decisions."

**Click:**
1. Switch identity → `rev@chartnav.local`. Show **Notes Awaiting
   Review** + **Blocked Items** cards.
2. Switch identity → `admin@chartnav.local`. Show **Queue Aging
   by Status / Queue Type / Priority / Role** tables. **Open
   Queue Items** card reads ≥ 7.

**Close:**
> "Same fake patient. Same seven seeded rows. Five role
> dashboards, one workspace, zero autonomous decisions. That's
> ChartNav."

## 6. Exact narration phrases (use verbatim)

| When | Say |
|---|---|
| Opening | "ChartNav coordinates a fake-data retina follow-up across clinic roles." |
| Imaging tab | "Imaging shown here is metadata-only." |
| Documentation tab | "Provider review remains explicit." |
| Any safety question | "ChartNav does not diagnose, interpret images, place orders, send referrals, message patients, submit claims, or replace the certified EHR." |
| Closing | "Five role dashboards, one workspace, zero autonomous decisions." |

## 7. What not to say (banned, every demo, every audience)

The following positive claims are **banned** by the repo's
safe-claims contract (`scripts/check_commercial_claims.sh`,
`scripts/check_website_claims.sh`, and Phase 24A
`scripts/check_live_site_claims.sh`):

- chart fills itself / note writes itself
- hands-free scribing (as a primary claim)
- autonomous diagnosis / automatic diagnosis
- automatic OCT interpretation / auto-interpret OCT
- OCT interpretation / disease grading / DR grading
- treatment recommendation / anti-VEGF dosing recommendation
- auto-select IOL / auto-recommend anti-VEGF
- automatic orders / referrals / coding / billing / claims
- patient messaging / send to patient / portal push
- claims submission / billing automation / coding recommendations
- EHR replacement / replace your EHR
- HIPAA certified / HIPAA compliant / SOC-2 certified / FDA cleared
- real PHI ready / production-ready for PHI
- device integration (any specific device-vendor name)
- DICOM ingestion / binary image storage
- powered by IBM / powered by watsonx

If any of these appears on screen mid-demo, **stop the demo,
fix the source, re-run** — do not narrate around it.

## 8. Fallback plan if a screen fails

| Symptom | Action |
|---|---|
| Role dashboard does not load | Re-run reset; if still failing, run `pytest apps/api/tests/test_phase_24b_retina_wedge.py::TestDashboardReflection` |
| Queue item click-through fails | Re-run reset; check `assigned_user_id` is set on wedge queue items (the verifier line covers this) |
| Imaging tab is empty | Confirm `imaging_studies` + `imaging_files` rows exist via the reset verifier; re-seed if zero |
| Documentation tab is not ready | The note draft surfaces are part of Phase 12/19 wiring; restart the backend, re-open the encounter |
| Playwright fails on the wedge spec | Run `npx playwright test apps/web/tests/e2e/phase24b-retina-workflow.spec.ts --reporter=line` to localize |
| Reset fails | See **§3 Troubleshooting** above |
| Mid-demo crash | Switch to talking through `phase-24b-retina-workflow-demo-script.md` — same content, no live screen. **Never** show real PHI as a fallback. |

## 9. Objection handling

| Question | Safe answer |
|---|---|
| "Is this just another scribe?" | "No — ChartNav coordinates the clinic's workflow across roles, queues, and structured ophthalmology data. The scribe panel is one surface; the workflow layer is the product." |
| "Does ChartNav interpret OCTs or fundus photos?" | "No. ChartNav stores imaging metadata only and surfaces it for provider review. It does not interpret, grade, or measure images." |
| "Does ChartNav diagnose retina disease?" | "No. The retina tracking row holds the structured fields the provider enters. ChartNav does not diagnose, classify severity, or recommend treatment." |
| "Does ChartNav place orders or send referrals?" | "No. Both are explicit no-go on the safe-claims contract. The product never sends orders, referrals, or messages on the practice's behalf." |
| "Does ChartNav message patients?" | "No. Every patient-facing touchpoint is the practice's existing tooling. ChartNav's only follow-up tasks are **internal staff coordination**." |
| "Is ChartNav HIPAA compliant?" | "ChartNav is not certified to any third-party compliance framework today. A controlled real-PHI pilot is gated by BAA execution and the Phase 23 readiness checklist; default deployments use fake data only." |
| "Does ChartNav replace the EHR?" | "No. ChartNav is the clinic's coordination layer; the practice's EHR remains the system of record. ChartNav publishes draft artifacts to the EHR via the practice's existing workflow." |

## 10. Final safety close

Use this paragraph verbatim when wrapping the demo or when a
buyer asks "what would it take to put real data in this?":

> "ChartNav is not approved for real PHI by default. A controlled
> real-PHI pilot requires BAA execution, practice security
> review, production authentication, approved hosting, backups,
> monitoring, incident contacts, and written practice approval.
> The readiness gate is documented in
> `docs/security/chartnav-real-phi-go-live-gate.md`. Until that
> gate is satisfied for a given practice, the demo stays
> fake-data-only."

## 11. UI guardrails already shipped (don't re-introduce them)

This is documentation of existing guardrails the demo relies on —
the runbook does not add new UI in Phase 24C.

- **Phase 15 Guided Demo Mode** — append `?demo=1` to the URL or
  set `localStorage.chartnav.demoMode = "1"` to mount the
  "DEMO MODE · fake data only" badge + 8-step stepper. Source:
  `apps/web/src/GuidedDemoMode.tsx`.
- **Per-panel provider-review banners** — every NoteWorkspace
  panel ships its own banner (`provider review required`, `Do
  not send to patient`, etc.). Phase 24B did not alter these.
- **Landing page negative-assertion strip** — visit
  `http://127.0.0.1:5173/landing` (or `?intro=1`) to show the
  ChartNav safe-claims block including "Not a certified EHR",
  "Not HIPAA-certified", "Does not interpret OCT", "Real-PHI
  pilot requires BAA".
- **Buyer-safe identity chip** — the top bar shows
  `Identity <Role> · Org <N>` rather than raw emails. Phase 19.
- **No forbidden controls in the workspace** — no `Send to
  patient`, `Place order`, `Submit referral`, `Submit claim`
  buttons exist. Enforced by the Phase 12 + Phase 24B Playwright
  smoke specs.

## 12. References

- `apps/api/scripts_seed.py` — Phase 24B wedge seed
  (`_seed_phase_24b_retina_wedge`).
- `apps/api/tests/test_phase_24b_retina_wedge.py` — authoritative
  Phase 24B test (18 tests + Phase 24C-merge-gate assignment
  test).
- `apps/web/tests/e2e/phase24b-retina-workflow.spec.ts` —
  Playwright wedge spec.
- `scripts/reset_phase24b_retina_demo.sh` — this runbook's
  reset command.
- `scripts/check_commercial_claims.sh`,
  `scripts/check_website_claims.sh`,
  `scripts/check_live_site_claims.sh` — claim-safety gates.
- `docs/demo/phase-24b-retina-workflow-demo-script.md` —
  narration source-of-truth (Phase 24B).
- `docs/demo/phase-24b-retina-shot-list.md` — Phase 24B shot
  list (still valid).
- `docs/demo/phase-24c-retina-shot-list.md` — Phase 24C
  screen-capture plan.
- `docs/demo/phase-24c-demo-qa-checklist.md` — pre-call QA.
- `docs/security/chartnav-real-phi-go-live-gate.md` — Phase 23
  per-practice real-PHI gate.
