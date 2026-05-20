# Phase 62 — Buyer Demo Dry-Run Preflight Audit

> Pre-implementation audit on `main` at `5349c4a` (Phase 61A merged).
> Phase 62 is **demo packaging, evidence, and local-build delivery**.
> No product code changes are planned. The output of Phase 62 is:
> a dry-run scenario, a dry-run report template, a screenshot shot
> list, a video-clip shot list, an evidence-packet index, and a local
> Desktop bundle the operator can copy to their iMac. No actual
> screenshots / videos are captured in this sandbox — those require
> the operator's local display + browser tooling.

## 1. Current demo docs found

| Path | Phase | Use in Phase 62 |
|---|---|---|
| `docs/demo/phase-61-controlled-buyer-demo-runbook.md` | 61 (corrected by 61A) | Authoritative master operator script. |
| `docs/demo/phase-61-buyer-demo-checklist.md` | 61 (corrected by 61A) | Authoritative checklist. |
| `docs/demo/phase-61-buyer-qa-safe-answers.md` | 61 (corrected by 61A) | Authoritative Q&A. |
| `docs/demo/phase-61-demo-storyboard.md` | 61 (corrected by 61A) | Operator storyboard. |
| `docs/demo/phase-60-vitals-workup-demo-runbook.md` | 60 | Per-feature runbook (Vitals). |
| `docs/demo/phase-59-ambient-demo-qa-checklist.md` | 59 | Per-feature QA lockdown (Ambient / VisitDraft Assist). |
| `docs/demo/phase-57-ambient-documentation-demo-runbook.md` | 57 | Per-feature runbook (Ambient / VisitDraft Assist). |
| `docs/demo/phase-56-fundus-demo-runbook.md` | 56 | Per-feature runbook (Fundus Drawing Assist). |
| `docs/build/phase-61a-demo-package-accuracy-repair.md` | 61A | Documents the Fundus V1 vs Ambient/Vitals difference. |

## 2. Current feature surfaces

| Internal name | Buyer-facing name (Phase 62) | Status | Where it mounts |
|---|---|---|---|
| Ambient Documentation Assist | **Provider-Reviewed VisitDraft Assist** | Shipped; fake-data only by default | Documentation / EMR-EHR tab |
| Fundus Charting V1 | **Provider-Reviewed Fundus Drawing Assist** | Shipped; deterministic by default | Imaging tab |
| Technician Workup & Structured Vitals | (unchanged) Technician Workup & Vitals | Shipped | Clinical / Ophthalmology tab |

The buyer-facing rename applies to **new Phase 62 demo docs only**.
Existing internal docs (workflow, code, audit) keep the internal
names so source code, env vars (`CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST`),
and API paths remain unchanged.

## 3. Current test / build commands

| Command | Purpose |
|---|---|
| `python3 scripts/check_runtime_safety.py` | Runtime safety validator. |
| `bash scripts/check_commercial_claims.sh` | Commercial claim scanner. |
| `bash scripts/check_website_claims.sh` | Website claim scanner. |
| `bash scripts/check_demo_claims.sh` | Demo claim scanner (22 files post-Phase 61). |
| `bash scripts/test_claim_policy_fixtures.sh` | Manifest sync + fixture tests. |
| `bash scripts/check_alembic_safety.sh` | Single-head + portable migrations. |
| `cd apps/api && python3 -m pytest tests/test_{vitals_workup,ambient_documentation,fundus_charts,fundus_charts_phase56,fundus_llm_guardrails,runtime_safety,llm_provider}.py -q` | Backend targeted sweep. |
| `cd apps/web && npx tsc --noEmit && npx vitest run && npm run build` | Frontend typecheck + tests + production bundle. |
| `make boot` / `docker compose up` | Local app boot (covered by existing `chartnav-demo-environment.md`). |
| `bash scripts/reset_demo_state.sh` | Reset general demo state. |
| `bash scripts/reset_phase24b_retina_demo.sh` | Reset Phase 24B retina demo state. |

## 4. Known demo constraints

- **No real PHI** in any artefact (visit script, screenshots, video,
  Desktop bundle).
- **No production LLM**. Optional OpenAI assist remains fake-data-only
  behind env gates; not enabled in the dry run.
- **No HIPAA-compliance / EHR-replacement / autonomous-documentation /
  diagnosis / treatment-recommendation / image-interpretation /
  device-integration / RPM** claims anywhere.
- Fundus V1 has **no** `forbidden_actions` response field and **no**
  "What ChartNav did NOT do" UI card (Phase 61A pinned this). The
  Phase 62 docs must use the same scoping.
- Sandbox cannot capture screenshots or video — the shot lists are
  authored as **`[MANUAL CAPTURE REQUIRED]`** entries that the local
  operator runs on their iMac with browser tooling.

## 5. Screenshot / video capture requirements

- Browser at 100% zoom; resolution at least 1440×900.
- Use the seeded fake demo patient (Morgan Lee, `PT-1001`, encounter
  `#1`, provider `Dr. Carter`).
- Use the built-in **Load fake demo …** sample buttons; never type
  real clinical content.
- For terminal screenshots (runtime safety / claim scanners / Alembic
  safety): show the command + the `PASS` / `PASSED` line. Never echo
  `CHARTNAV_OPENAI_API_KEY` / `CHARTNAV_ANTHROPIC_API_KEY` values.
- For video clips: 15–45 seconds each. No audio narration in the file
  itself — narration is captured in the shot-list "narration" field
  for live use.
- All artifacts saved under `artifacts/phase-62/screenshots/` and
  `artifacts/phase-62/video-clips/` (paths are repo-relative).

## 6. Local Desktop bundle delivery plan

A delivery folder is staged inside the repo at
`artifacts/phase-62/desktop-bundle/`. The operator copies the entire
folder to their iMac `~/Desktop/ChartNav-Buyer-Demo-Build/` via a one
line `cp -R` command documented in
`docs/demo/phase-62-local-build-delivery.md`.

The bundle includes:

- `README.md`, `START_HERE.md`, `RUN_LOCAL_DEMO.md`,
  `TEST_VISIT_SCRIPT.md`, `TROUBLESHOOTING.md`.
- Copies of the four Phase 61 docs + Phase 62 visit script and shot
  lists.
- `.env.example` with placeholder env vars (no secrets).
- Wrapper scripts that delegate to repo scripts:
  `start-api.sh`, `start-web.sh`, `run-safety-checks.sh`,
  `run-demo-reset.sh`.
- A copy of `docs/build/current-product-truth.md` and
  `docs/release/release-evidence-checklist.md` for the operator's
  go/no-go reference.

The bundle **does not** include:

- Any real `.env` file or secret.
- A frontend production bundle (those live under `apps/web/dist/`
  after `npm run build`; the README explains how to rebuild locally).
- Any real PHI, screenshot of real PHI, or production config.
- Any pre-built Docker image (operator runs `docker compose up`
  themselves if applicable).

## 7. Unsafe wording sweep

`grep` shows the existing internal docs reference `ambient scribe` /
`hands-free` / `automatic charting` / `AI writes the note` **only in
negative-assertion / forbidden-phrase-catalog context** — every
occurrence is part of a `❌`, "is not", "does not", or "Banned"
construct. The three claim scanners already pass. No code change is
required.

Phase 62 buyer-facing docs use **"Provider-Reviewed VisitDraft
Assist"** instead of "ambient" wherever the wording is
buyer-facing. The internal source code, env vars, URL paths, and
existing workflow doc names (e.g.
`docs/workflow/ambient-documentation-assist.md`) keep the internal
"ambient" name to avoid a code-side rename.

## 8. Output deliverables (Phase 62)

| File | Purpose |
|---|---|
| `docs/demo/phase-62-end-to-end-demo-visit-script.md` | End-to-end visit scenario the operator follows. |
| `docs/demo/phase-62-demo-dry-run-report.md` | Template the operator completes per dry run. |
| `docs/demo/phase-62-screenshot-shot-list.md` | 30 required screenshots with capture spec. |
| `docs/demo/phase-62-video-clip-shot-list.md` | 12 required video clips with capture spec. |
| `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` | Evidence-packet index. |
| `docs/demo/phase-62-local-build-delivery.md` | Local Desktop bundle delivery instructions. |
| `artifacts/phase-62/desktop-bundle/...` | Staged Desktop deliverable. |
| `artifacts/phase-62/screenshots/.gitkeep` | Placeholder directory for manual capture. |
| `artifacts/phase-62/video-clips/.gitkeep` | Placeholder directory for manual capture. |
| `scripts/check_demo_claims.sh` | Extended FILES list to cover Phase 62 demo docs. |

## 9. Out of scope (explicitly)

- **No** product feature added.
- **No** backend business-logic change.
- **No** frontend component change.
- **No** migration.
- **No** public marketing-site update.
- **No** deploy.
- **No** screenshot / video capture in the sandbox (the operator runs
  the shot lists on their iMac).

## Related documents

- `docs/build/current-product-truth.md`
- `docs/build/phase-61a-demo-package-accuracy-repair.md`
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md`
- `docs/release/release-evidence-checklist.md`
- `docs/commercial/claims-policy.json`
