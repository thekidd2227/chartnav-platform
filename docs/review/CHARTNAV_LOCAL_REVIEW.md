# ChartNav — local review

Run the whole ChartNav platform on your Mac with **one command** to test it
hands-on. Everything is **synthetic** — no real patients, no live external
services, no cloud.

## Prerequisites

- **Docker Desktop** installed and **running** (the launcher checks this).
  Get it: https://www.docker.com/products/docker-desktop/
- macOS (the launcher auto-opens the browser; the stack itself is OS-agnostic).
- Ports free: **5173** (web), **8000** (API), **9000/9001** (MinIO).

## Start / stop / reset

```bash
cd ~/chartnav-platform
./scripts/review/start_chartnav_review.sh     # build + start + verify + open browser
./scripts/review/stop_chartnav_review.sh      # stop, KEEP data
./scripts/review/reset_chartnav_review.sh     # stop + WIPE data (fresh seed next start)
```

First start builds images and can take a few minutes; later starts are fast.

## What you get

| URL | What |
|---|---|
| http://localhost:5173 | ChartNav web app (React) |
| http://localhost:8000 | API (FastAPI) |
| http://localhost:8000/healthz | API liveness · `/readyz` = DB readiness |
| http://localhost:9000 / :9001 | MinIO S3 store / console (dev) |

The stack: React (Vite) · FastAPI · PostgreSQL · MinIO · deterministic synthetic
ophthalmology seed · **dev identity selection** (pick a user, no password) ·
persistent Docker volumes.

## Demo identities

Pick one in the app's dev identity selector (details in
`DEMO_IDENTITIES.md`):

```
admin@chartnav.local   clin@chartnav.local   tech@chartnav.local
front@chartnav.local   rev@chartnav.local
admin@northside.local  (second clinic, for cross-tenant testing)
```

## What to try

Follow `FEATURE_TEST_SCRIPT.md` for a guided walkthrough (patient chart, Open
chart, retina eye-diagram, fundus, cross-tenant denial, roles, audit).

## Troubleshooting

- **"daemon not running"** → start Docker Desktop, re-run.
- **Port in use** → free it (`lsof -iTCP:5173`) or stop the other app.
- **Weird DB state** → `./scripts/review/reset_chartnav_review.sh` then start.
- **Logs** → `docker compose -f scripts/review/docker-compose.yml logs -f`
  (startup log: `scripts/review/.logs/up.log`).
- **Re-verify a running env** → `./scripts/review/verify_chartnav_review.sh`.

## Honest scope

This is a **review/demo** environment, not production and not a compliance
artifact. See `KNOWN_LIMITATIONS.md`. ChartNav does not diagnose, interpret
images autonomously, or bill — all clinical content is provider-controlled.
