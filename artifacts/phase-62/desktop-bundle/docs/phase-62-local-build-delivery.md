# Phase 62 — Local Desktop Build Delivery

> Describes the staged Desktop bundle the operator copies to their
> iMac before a buyer-demo dry run. **Fake-data only. No real PHI.
> No production LLM. No deploy.**

## 1. Folder created

The deliverable is staged inside the repo at
`artifacts/phase-62/desktop-bundle/`. The operator copies the
entire folder to `~/Desktop/ChartNav-Buyer-Demo-Build/` once. After
that, the operator drives everything from the Desktop copy.

## 2. Files included

| File | Purpose |
|---|---|
| `README.md` | Overview of the bundle + safety boundary recap. |
| `START_HERE.md` | First-read setup gates + step-by-step intro. |
| `RUN_LOCAL_DEMO.md` | API + frontend boot instructions, local URLs, auth headers, reset commands. |
| `TEST_VISIT_SCRIPT.md` | Index pointer to the visit script in the repo. |
| `TROUBLESHOOTING.md` | 30+ symptom → fix entries; explicit stop-demo triggers. |
| `start-api.sh` | Wrapper: `make boot` in the repo. Refuses production-shaped `CHARTNAV_ENV`. |
| `start-web.sh` | Wrapper: `npm run dev` under `apps/web`. Same refusal. |
| `run-safety-checks.sh` | Wrapper: runs all 6 safety scripts + `git diff --check`. |
| `run-demo-reset.sh` | Wrapper: `bash scripts/reset_demo_state.sh`. Refuses production env. |
| `.env.example` | Placeholder env vars — no secrets, no real vendor keys. Documents the must-not-set gates. |

The bundle does **not** include:

- A pre-built frontend production bundle. The operator runs
  `npm run build` from the repo if they need one.
- Any real `.env` file or secret.
- Any vendor API key.
- Any real PHI.
- Any Docker image artefact (operator runs `docker compose up`
  themselves only if needed).

## 3. Startup commands the operator runs

From the operator's iMac:

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"

# One-time copy (operator's actual Desktop path varies):
cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle" \
   "$HOME/Desktop/ChartNav-Buyer-Demo-Build"

cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
./run-safety-checks.sh   # gate
./start-api.sh           # terminal 1
./start-web.sh           # terminal 2
# Walk the visit script (see TEST_VISIT_SCRIPT.md).
./run-demo-reset.sh      # post-demo cleanup
```

## 4. Fake-data constraints

- Operator uses the seeded fake demo patient (**Morgan Lee ·
  PT-1001 · Encounter #1 · Dr. Carter**).
- Every panel uses its built-in **Load fake demo…** sample button.
  Operator never types real clinical content.
- `CHARTNAV_ENV` is `local` / `dev` / `demo` / `test`.
- `CHARTNAV_LLM_ENABLED`, `CHARTNAV_LLM_REAL_PHI_APPROVED`, and
  `CHARTNAV_REAL_PHI_ENABLED` are unset or `0`.
- No real `CHARTNAV_OPENAI_API_KEY` / `CHARTNAV_ANTHROPIC_API_KEY`.
- All four wrapper scripts refuse to run with production-shaped
  env. They exit with a non-zero code and a clear message.

## 5. Known limitations

- The bundle is **not** a turnkey installer. It assumes Python
  3.11+, Node 20+, npm, git, and a clean local clone of the repo
  at `$CHARTNAV_REPO_PATH`.
- The bundle does **not** include a SQLite database file — the
  Makefile's `reset-db` + `seed` + `migrate` targets prepare one
  on first boot.
- The wrapper scripts call into the repo via `$CHARTNAV_REPO_PATH`.
  If the operator's clone is at a different path, they export the
  variable accordingly.
- Screenshot + video capture is the **operator's job** on the iMac.
  The sandbox cannot generate display output. The shot lists
  (`phase-62-screenshot-shot-list.md`,
  `phase-62-video-clip-shot-list.md`) tell the operator what to
  capture, where to save it, and what must / must not be visible
  in every frame.
- The bundle copies only the docs the operator needs offline (Phase
  62 visit script, dry-run report, shot lists, evidence packet
  index; Phase 61 runbook + checklist + Q&A safe-answers +
  storyboard; Phase 61A repair note; current product truth;
  release-evidence checklist). The full repo docs tree is **not**
  duplicated — the operator opens the repo for anything not in the
  bundle.

## 6. How Charlie should test every feature

A single end-to-end pass over the bundle:

1. From the repo at `main`, run `./run-safety-checks.sh`. Expect
   PASS on every line.
2. Run `./start-api.sh` in terminal 1, `./start-web.sh` in
   terminal 2. Open `http://localhost:5173`.
3. Walk the Phase 62 visit script
   (`docs/demo/phase-62-end-to-end-demo-visit-script.md`) section
   by section.
4. Capture the 30 screenshots into
   `$CHARTNAV_REPO_PATH/artifacts/phase-62/screenshots/`.
5. Capture the 12 video clips into
   `$CHARTNAV_REPO_PATH/artifacts/phase-62/video-clips/`.
6. Complete the dry-run report
   (`docs/demo/phase-62-demo-dry-run-report.md`).
7. Run `./run-demo-reset.sh` post-demo.
8. Re-run `./run-safety-checks.sh` post-demo.
9. Open the evidence packet
   (`docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`)
   § 10 — the buyer-demo go/no-go checklist. The dry run is **GO**
   only when every line is `[x]`.

If anything fails, consult `TROUBLESHOOTING.md` in the bundle.

## 7. Cleanup commands

```bash
# Stop API + frontend (Ctrl-C in their respective terminals).
./run-demo-reset.sh

# Unset any session env vars set for the dry run.
unset CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST
unset CHARTNAV_FUNDUS_DRAFTING_ASSIST

# Verify all gates remain PASS post-cleanup.
./run-safety-checks.sh
```

## Related documents

- `docs/build/phase-62-demo-dry-run-preflight-audit.md` — audit + reuse decisions.
- `docs/demo/phase-62-end-to-end-demo-visit-script.md` — canonical scenario.
- `docs/demo/phase-62-demo-dry-run-report.md` — report template.
- `docs/demo/phase-62-screenshot-shot-list.md` — 30 screenshots.
- `docs/demo/phase-62-video-clip-shot-list.md` — 12 video clips.
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` — packet index.
- `docs/demo/phase-61-controlled-buyer-demo-runbook.md` — master runbook.
- `docs/demo/phase-61-buyer-demo-checklist.md` — pre/during/post checklist.
- `docs/demo/phase-61-buyer-qa-safe-answers.md` — Q&A safe answers.
- `docs/build/current-product-truth.md` — single source of truth.
- `docs/release/release-evidence-checklist.md` — release-gate template.
