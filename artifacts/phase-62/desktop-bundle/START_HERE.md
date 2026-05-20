# START HERE

> First thing to read after you copy this bundle to your Desktop.

## A. Create (or refresh) `~/Desktop/ChartNav-Buyer-Demo-Build/`

The bundle lives in the repo under
`artifacts/phase-62/desktop-bundle/`. Copy it to your Desktop with
the commands below. **The bundle never carries a real `.env`, a
real API key, production config, or any local database file.**

```bash
# 1. Anchor the repo path.
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"

# 2. Confirm you are on a clean main with the latest Phase 62A.
git status
git log --oneline -1

# 3. Refresh the Desktop bundle. -R copies the docs/ subfolder too.
#    The trailing slash on the source matters: it means "copy the
#    contents of desktop-bundle into the destination".
rm -rf "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle/" \
      "$HOME/Desktop/ChartNav-Buyer-Demo-Build"

# 4. Sanity-check the result.
ls "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
ls "$HOME/Desktop/ChartNav-Buyer-Demo-Build/docs"
```

After step 4 you should see the wrappers
(`start-api.sh`, `start-web.sh`, `run-safety-checks.sh`,
`run-demo-reset.sh`), the top-level markdown
(`README.md`, `START_HERE.md`, `RUN_LOCAL_DEMO.md`,
`TEST_VISIT_SCRIPT.md`, `TROUBLESHOOTING.md`), the
`.env.example` placeholder, and the offline `docs/` folder with 12
read-only doc copies + a `README.md` index.

If you want to keep a personal `.env` next to the wrappers, copy
`.env.example` to `.env` **only in this Desktop folder** and edit
locally. Do not push that `.env` anywhere — it is intentionally
gitignored.

## 0. Sanity gates (do these before opening any demo URL)

1. `CHARTNAV_REPO_PATH` is exported and points at your local
   chartnav-platform clone. The wrapper scripts in this folder
   refuse to run otherwise.
2. From `$CHARTNAV_REPO_PATH`, on `main`, pull latest:
   ```bash
   cd "$CHARTNAV_REPO_PATH"
   git checkout main
   git pull --ff-only origin main
   git log --oneline -1   # record this SHA for the dry-run report
   ```
3. `CHARTNAV_ENV` is **unset** or one of: `local`, `dev`, `demo`,
   `test`. The wrappers refuse to run if `CHARTNAV_ENV` is set to
   `production`, `staging`, or `controlled-pilot`.
4. No real `CHARTNAV_OPENAI_API_KEY` /
   `CHARTNAV_ANTHROPIC_API_KEY` in this shell. The wrappers do not
   require any vendor key.
5. Browser is at 100% zoom, viewport at least 1440×900.

## 1. Run the safety gates

From this bundle directory:

```bash
./run-safety-checks.sh
```

Expected: every line ends in `PASS` or `PASSED`. If any line is
`FAIL`, **stop**. Do not proceed to a dry run with a failing
safety gate.

## 2. Boot the app

In one terminal:

```bash
./start-api.sh        # API at http://localhost:8000
```

In a second terminal:

```bash
./start-web.sh        # Frontend at http://localhost:5173
```

(The first time, the wrappers will print the underlying Makefile /
npm command they're about to run, so you can audit them before
they execute.)

## 3. Open the demo encounter

The seeded fake demo patient is **Morgan Lee · PT-1001 ·
Encounter #1 · Dr. Carter**. The URL pattern is in
`RUN_LOCAL_DEMO.md`.

If header-auth is the dev auth mode (the default for `local`),
include the `X-User-Email` header. For a clinician (default
operator identity), use `clin@chartnav.local`. For the technician
scenes (Vitals workup as technician), use `tech@chartnav.local`.

## 4. Walk through the visit script

Open `TEST_VISIT_SCRIPT.md` in this folder. It is a copy of
`docs/demo/phase-62-end-to-end-demo-visit-script.md` in the repo —
follow it section by section.

## 5. Capture evidence (manual)

While walking the script, capture:

- **30 screenshots** per `docs/demo/phase-62-screenshot-shot-list.md`
  (copy in this bundle under `docs/`).
- **12 video clips** per `docs/demo/phase-62-video-clip-shot-list.md`.

Save everything under
`$CHARTNAV_REPO_PATH/artifacts/phase-62/screenshots/` and
`$CHARTNAV_REPO_PATH/artifacts/phase-62/video-clips/`. Those folders
are gitignored by default; the operator copies finished artefacts
into a dated subfolder for the packet.

## 6. Complete the dry-run report

Open `docs/demo/phase-62-demo-dry-run-report.md` (template), copy
it to `$CHARTNAV_REPO_PATH/artifacts/phase-62/dry-runs/YYYY-MM-DD/
report.md`, and fill in every section.

## 7. Reset the local demo state (post-demo)

```bash
./run-demo-reset.sh
```

This calls `bash scripts/reset_demo_state.sh` in the repo.

## 8. Go / no-go check

Open `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
§ 10 — the buyer-demo go/no-go checklist. The dry run is **GO**
only when every line is `[x]`.

---

## Stop-demo triggers (any one → halt + reset)

- Real PHI on screen.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot`.
- Runtime safety validator returns FAIL at any point.
- A forbidden phrase appears in narration or UI.
- A vendor / network error exposes a secret in a stack trace.
- A raw transcript / draft body / vitals value appears in an audit
  log line visible during the dry run.
- Sign / finalize succeeds **without** the attestation checkbox
  having been ticked.

If any trigger fires, halt the dry run, reset, and file the
near-miss in `TROUBLESHOOTING.md` or escalate.
