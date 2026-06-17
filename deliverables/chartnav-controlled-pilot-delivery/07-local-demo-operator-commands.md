# Local Demo Operator Commands

**Audience:** ARCG ops operator
**Posture:** Fake data only. No production LLM. No live vendor.
**Source of truth:** mirrors
`docs/demo/phase-101-mcp-independent-buyer-demo-runbook.md` and
`scripts/release/phase100_controlled_pilot_launch_gate.sh`.

## 0. One-time workstation prerequisites

| # | Check | How |
|---|---|---|
| 0.1 | `git`, `bash`, `python3`, `curl` on PATH | `which git bash python3 curl` |
| 0.2 | Repo cloned at `$HOME/Desktop/ARCG/chartnav-platform` | `git -C ~/Desktop/ARCG/chartnav-platform rev-parse HEAD` |
| 0.3 | Backend deps installed (system `alembic` + `uvicorn` OK; venv optional) | `which alembic uvicorn` |
| 0.4 | Frontend deps installed | `cd apps/web && npm ci` (once per machine) |
| 0.5 | (Optional) Playwright chromium for screenshot capture | `cd apps/web && npx playwright install --with-deps chromium` |

The Phase 101 seed helper uses whichever `alembic` / `python3` is
on PATH — no `apps/api/.venv` is required.

## 1. Sync main + clean working tree

```bash
cd "$HOME/Desktop/ARCG/chartnav-platform"

git checkout main
git pull --ff-only origin main
git log --oneline -5
git status --short   # expect empty (ignored .codex/, .tmp/, dist/ OK)
```

If the tree is dirty or `git pull` reports conflicts: stop.
Capture only against a clean SHA.

## 2. Venv-free SQLite seed (fake data)

```bash
bash scripts/demo/phase101_local_seed_sqlite.sh
```

Expected last line:
```
[phase101-local-seed] PASS  apps/api/chartnav.db seeded
```

The helper refuses to run if `DATABASE_URL` is set to anything
other than the local SQLite default. It uses whichever
`alembic` / `python3` is on PATH; on workstations with a system
install but no venv, this is the supported path.

Equivalent verbose commands:

```bash
cd apps/api
DATABASE_URL="sqlite:///./chartnav.db" \
  CHARTNAV_ENV=local CHARTNAV_LLM_ENABLED=0 \
  alembic upgrade head

DATABASE_URL="sqlite:///./chartnav.db" \
  CHARTNAV_ENV=local CHARTNAV_LLM_ENABLED=0 \
  python3 scripts_seed.py
```

## 3. Start the API on `127.0.0.1:8765` (Shell 1)

```bash
cd "$HOME/Desktop/ARCG/chartnav-platform/apps/api"

DATABASE_URL="sqlite:///./chartnav.db" \
  CHARTNAV_ENV=local CHARTNAV_LLM_ENABLED=0 \
  CHARTNAV_RATE_LIMIT_PER_MINUTE=0 \
  uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning
```

Wait until `curl -fsS http://127.0.0.1:8765/health` returns
`{"status":"ok"}`.

## 4. Start the web app on `127.0.0.1:5173` (Shell 2)

```bash
cd "$HOME/Desktop/ARCG/chartnav-platform/apps/web"

VITE_API_URL="http://127.0.0.1:8765" \
  npx vite --host 127.0.0.1 --port 5173
```

Wait until `curl -fsS http://127.0.0.1:5173` returns 200. Then
open `http://127.0.0.1:5173` in a browser.

## 5. Phase 100 controlled-pilot launch gate

```bash
cd "$HOME/Desktop/ARCG/chartnav-platform"
bash scripts/release/phase100_controlled_pilot_launch_gate.sh
```

Reads:
- `artifacts/phase-100-controlled-pilot-launch/<ts>/summary.txt`
  → expect `OVERALL: PASS`
- `artifacts/phase-100-controlled-pilot-launch/<ts>/go-no-go.txt`
  → expect `RECOMMENDATION: CONDITIONAL GO`

## 6. Phase 101 buyer-demo capture (no-reset, with live stack)

```bash
PHASE101_SMOKE_RESET=0 \
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

`PHASE101_SMOKE_RESET=0` tells the capture to call the Phase 63C
smoke without `--reset` (the operator pre-seeded via Section 2;
this avoids the `make reset-db` path that needs
`apps/api/.venv/bin/alembic`).

Reads:
- `artifacts/buyer-demo/<ts>/summary.txt` → expect
  `OVERALL: PASS` and `BUYER-DEMO RECOMMENDATION: CONDITIONAL GO`
- `artifacts/buyer-demo/<ts>/no-real-phi-attestation.txt`
  (present, unmodified)
- `artifacts/buyer-demo/<ts>/missing-evidence.txt` (SKIP/FAIL
  ledger for the practice's CISO)
- `artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log` → expect the
  embedded smoke to end with `Phase 63C functional smoke: 20 pass / 0 fail`

## 7. Phase 63C functional smoke (standalone, optional)

```bash
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

(Run without `--reset` since Section 2 already seeded.)

Expected last line:
```
BUYER-DEMO FUNCTIONAL GO: YES
```

## 8. Stop the local servers

In **Shell 2** (web) press `Ctrl+C`. In **Shell 1** (API) press
`Ctrl+C`. If a stale process is bound to a port:

```bash
# Find then kill the process bound to 8765 or 5173
lsof -i :8765 -i :5173
kill <PID>          # graceful; use `kill -9 <PID>` only if needed
```

If you used `nohup` / `&` to background the servers:

```bash
pkill -f "uvicorn app.main:app"
pkill -f "vite --host 127.0.0.1 --port 5173"
```

## 9. Update the manifest

After Sections 5 and 6 succeed, fill in `artifacts/manifest.txt`
in this delivery folder with the dated artifact paths the gates
printed. That manifest is the single pointer the practice's CISO
opens.

## 10. Boundaries reminder

These commands are local-only. The operator does **not**:

- Touch `.env*` files.
- Print, log, or copy raw API keys (the SAM-source service
  appends the key only in the main process and redacts it from
  errors).
- Send email, contact a COR, or upload to SAM / PIEE / eBuy /
  GSA / agency portals / patient portals.
- Submit bids, quotes, proposals, or government responses.
- Push, deploy, publish, or open GitHub releases from this
  package.
