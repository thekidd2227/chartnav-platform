# RUN LOCAL DEMO

> Boot ChartNav on your iMac for a controlled buyer-demo dry run.

## Prerequisites

- macOS with Python 3.11+, Node 20+, npm, git installed.
- `$CHARTNAV_REPO_PATH` exported and points at a clean clone of
  `chartnav-platform` on `main`.
- Repo at `main` (no uncommitted changes).
- A Python venv at `$CHARTNAV_REPO_PATH/apps/api/.venv` with the
  backend deps installed (`make install` from the repo root does
  this).
- `npm install` already run under `apps/web` (or the
  `start-web.sh` wrapper will run it on first boot).

## Backend (API)

```bash
./start-api.sh
```

This runs `make boot` in the repo, which starts the API on
`http://localhost:8000`. Stop with Ctrl-C.

If you prefer to drive `make` directly:

```bash
cd "$CHARTNAV_REPO_PATH"
make boot
```

Smoke check from a third terminal:

```bash
curl -s http://localhost:8000/health
```

Expected: `200` and a JSON `{"status": "ok"}`-shaped response (the
exact shape may vary; the wrapper prints what it expects).

## Frontend (web)

```bash
./start-web.sh
```

This runs `npm run dev` in `apps/web`, which starts the frontend
on `http://localhost:5173`. Stop with Ctrl-C.

If you prefer to drive `npm` directly:

```bash
cd "$CHARTNAV_REPO_PATH/apps/web"
npm run dev
```

## Local URLs

| Service | URL |
|---|---|
| API | `http://localhost:8000` |
| Frontend | `http://localhost:5173` |
| Demo encounter | `http://localhost:5173/?encounter=1` (or the equivalent route the SPA uses — the SPA opens the first seeded encounter by default if header-auth is on) |

If the SPA defaults to a different route, navigate to the Clinical /
Ophthalmology tab manually after the seeded patient loads.

## Auth (header mode)

Default dev auth is **header** mode (no JWT required). The SPA
should pass the demo identity automatically; if it doesn't, set the
`X-User-Email` header via a curl / fetch override.

Demo identities (seeded org `demo-eye-clinic`):

| Role | Email | Use for |
|---|---|---|
| clinician | `clin@chartnav.local` | Default operator identity. |
| admin | `admin@chartnav.local` | Full-access scenarios. |
| technician | `tech@chartnav.local` | Vitals workup scenes that need the technician identity. |
| reviewer | `rev@chartnav.local` | Read-only verification (rare in this demo). |

Cross-org identities (`*@northside.local`) are available for the
cross-org-404 verification step; not used in the buyer demo.

## Demo encounter URL

The seeded demo encounter:

- `id=1`
- `patient_identifier=PT-1001`
- `patient_name=Morgan Lee`
- `provider_name=Dr. Carter`
- org `demo-eye-clinic`

After the SPA loads, the patient header should display these
exact strings. If it doesn't, run `./run-demo-reset.sh` to reset
the local demo state and retry.

## How to reset fake demo state

```bash
./run-demo-reset.sh
```

This calls `bash scripts/reset_demo_state.sh` in the repo. It
deletes any vitals / scribe-session / fundus-chart rows you've
created during the dry run and re-seeds the baseline fake demo
state. **Always reset before a buyer demo.**

If you specifically need to reset Phase 24B retina state, run the
repo-side script directly:

```bash
bash "$CHARTNAV_REPO_PATH/scripts/reset_phase24b_retina_demo.sh"
```

## What to do if the API or frontend won't start

See `TROUBLESHOOTING.md` for the full table. Quick gates:

- Backend port `:8000` busy → `lsof -i :8000` to find the process,
  stop it, retry.
- Frontend port `:5173` busy → `lsof -i :5173`, same fix.
- Alembic head mismatch → from the repo: `cd apps/api && python3 -m
  alembic upgrade head` (use the venv).
- npm dep mismatch → from `apps/web`: `rm -rf node_modules && npm
  ci`.
- Safety scanner FAIL → **do not start the demo**. See the
  TROUBLESHOOTING table.

## Cleanup commands

After the dry run:

```bash
# Stop API and frontend (Ctrl-C in their respective terminals).
./run-demo-reset.sh         # reset local demo state
# Optionally close all extra terminals.
unset CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST
unset CHARTNAV_FUNDUS_DRAFTING_ASSIST
./run-safety-checks.sh      # verify all green post-cleanup
```

## Do NOT

- Do not run `make verify` against a real-PHI database.
- Do not export `CHARTNAV_LLM_ENABLED=1` for this dry run.
- Do not export `CHARTNAV_LLM_REAL_PHI_APPROVED=1`.
- Do not set `CHARTNAV_ENV=production` / `staging` /
  `controlled-pilot`.
- Do not paste any real API key into `.env`.
- Do not publish any Docker image. Local boot only.
