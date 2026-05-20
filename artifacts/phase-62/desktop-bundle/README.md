# ChartNav Buyer-Demo Build — Desktop Bundle

> **Fake-data only.** This is the operator's local desktop bundle
> for running, rehearsing, and capturing evidence for a controlled
> ChartNav buyer demo. **No real PHI.** **No production LLM.** No
> HIPAA-compliance / certified-EHR / EHR-replacement claims.

## What this is

A self-contained set of operator docs + thin wrapper scripts you
copy from the repo's `artifacts/phase-62/desktop-bundle/` directory
to your iMac's `~/Desktop/ChartNav-Buyer-Demo-Build/`. After that
copy, you do everything from this folder; you never need to open
the repo directly during a demo dry-run.

## What this is NOT

- ❌ A pre-built distributable. The bundle assumes the ChartNav
  repo is cloned at `~/Desktop/ARCG/chartnav-platform` (or wherever
  you cloned it) and contains the wrappers that call into that
  repo. **The wrappers refuse to run if `CHARTNAV_REPO_PATH` is
  unset or invalid.**
- ❌ A real-PHI environment. The fake-data discipline in
  `docs/demo/phase-61-buyer-demo-checklist.md` § 1 applies.
- ❌ A production deploy. No `docker compose up -d` in production
  mode, no infra changes.
- ❌ A vendor-credential bundle. No real `.env`, no real API key, no
  production config.

## How to set this up

From the repo, copy the staged bundle to your Desktop:

```bash
# Replace this path with wherever you cloned the chartnav-platform repo.
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"

cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle" \
   "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
cd "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
ls
```

Then export `CHARTNAV_REPO_PATH` permanently for this terminal (or
add it to your shell rc):

```bash
echo 'export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"' \
  >> ~/.zshrc
source ~/.zshrc
```

## Where to go next

| If you want to … | Open |
|---|---|
| Start here, see the layout | `START_HERE.md` |
| Boot the app for a dry run | `RUN_LOCAL_DEMO.md` |
| Walk through the buyer-demo scenario | `TEST_VISIT_SCRIPT.md` |
| Recover from a failure | `TROUBLESHOOTING.md` |

## Files in this bundle

| File | Purpose |
|---|---|
| `README.md` | This file. |
| `START_HERE.md` | First read; layout + setup gates. |
| `RUN_LOCAL_DEMO.md` | API + frontend boot instructions. |
| `TEST_VISIT_SCRIPT.md` | Walkthrough operator script. |
| `TROUBLESHOOTING.md` | Failure recovery table. |
| `start-api.sh` | Wrapper: `make boot` in the repo. |
| `start-web.sh` | Wrapper: `npm run dev` under `apps/web`. |
| `run-safety-checks.sh` | Wrapper: runs all 6 safety scripts. |
| `run-demo-reset.sh` | Wrapper: `bash scripts/reset_demo_state.sh`. |
| `.env.example` | Placeholder env vars (no secrets). |
| `docs/` | Read-only copy of the Phase 62 + Phase 61 + Phase 61A buyer-demo docs + the product-truth doc + the release-evidence checklist. |

## Safety boundary recap

- No real PHI in any artifact you produce here.
- No real `.env` checked into the bundle. The `.env.example` shows
  the variable names; you fill in values only on your machine and
  never echo them on camera.
- The wrappers never enable production LLM. They never set
  `CHARTNAV_LLM_ENABLED=1` or `CHARTNAV_LLM_REAL_PHI_APPROVED=1`.
- The wrappers refuse to run if `CHARTNAV_ENV` is set to
  `production`, `staging`, or `controlled-pilot`.
- The wrappers never publish a Docker image; they only call local
  Makefile targets.
- Anthropic and IBM watsonx remain unwired (the production code
  enforces this; the wrappers do not change the env).

## Related repo docs

- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-demo-dry-run-report.md`
- `docs/demo/phase-62-screenshot-shot-list.md`
- `docs/demo/phase-62-video-clip-shot-list.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62-local-build-delivery.md`
