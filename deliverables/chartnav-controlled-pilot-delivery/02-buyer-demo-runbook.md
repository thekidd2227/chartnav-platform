# Buyer Demo Runbook (ARCG Operator)

**Audience:** ARCG ops operator running a controlled fake-data
buyer demo for an ophthalmology practice
**Source of truth:** This file mirrors the in-repo runbook
`docs/demo/phase-101-mcp-independent-buyer-demo-runbook.md` and
the Phase 100 controlled-pilot buyer demo script
`docs/demo/phase-100-controlled-pilot-buyer-demo-script.md`.
**Posture:** Fake data only. No real PHI. No send / submit /
upload.

## 0. Pre-flight (T-15 minutes)

| # | Check | Pass condition |
|---|---|---|
| 0.1 | Workstation is on the latest `main` | `git log -1 --oneline` matches the build manifest |
| 0.2 | Working tree clean | `git status --short` empty (ignored `.codex/`, `.tmp/`, `dist/` OK) |
| 0.3 | Local seed succeeds | `bash scripts/demo/phase101_local_seed_sqlite.sh` exits 0 |
| 0.4 | Phase 100 launch gate passes | `bash scripts/release/phase100_controlled_pilot_launch_gate.sh` writes `OVERALL: PASS` |
| 0.5 | Web + API both respond | `curl -fsS http://127.0.0.1:8765/health` → `{"status":"ok"}`; `curl -fsS http://127.0.0.1:5173` → 200 |
| 0.6 | Demo banner visible | Browser shows "demo mode — no real PHI" indicator |
| 0.7 | Notifications muted, unrelated tabs closed | Screen-share-safe |

If any row is RED, **stop**. Do not run the demo.

## 1. Demo reset

Two paths — pick whichever the workstation supports.

### 1.a `make reset-db` path (requires `apps/api/.venv`)

```bash
bash scripts/reset_demo_state.sh
```

Exit 0; refuses any non-loopback `DATABASE_URL`.

### 1.b Venv-free SQLite seed helper (recommended on fresh workstations)

```bash
bash scripts/demo/phase101_local_seed_sqlite.sh
```

Uses whichever `alembic` and `python3` are on PATH. Deletes
`apps/api/chartnav.db` and re-runs the canonical
`alembic upgrade head` + `python3 scripts_seed.py` sequence.

## 2. Start the local stack

**Shell 1 — backend (port 8765):**

```bash
cd apps/api
DATABASE_URL="sqlite:///./chartnav.db" \
  CHARTNAV_ENV=local CHARTNAV_LLM_ENABLED=0 \
  CHARTNAV_RATE_LIMIT_PER_MINUTE=0 \
  uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning
```

**Shell 2 — frontend (port 5173):**

```bash
cd apps/web
VITE_API_URL="http://127.0.0.1:8765" \
  npx vite --host 127.0.0.1 --port 5173
```

Wait until both `GET /health` and `GET /` return 200. Then open
`http://127.0.0.1:5173` in a browser.

## 3. Role walkthrough

Sign in with each operator identity in turn and confirm the role
banner + tab visibility match the role's allowlist:

| Identity | Role | Expected |
|---|---|---|
| `admin@chartnav.local` | admin | every tab visible; transitions allowed |
| `clin@chartnav.local` | clinician | clinical write paths; cross-org rows 404 |
| `tech@chartnav.local` | technician | vitals workup + imaging pipeline writable; no signing |
| `rev@chartnav.local` | reviewer | read-only across clinical surfaces |
| `admin@northside.local` | admin (other org) | Northside encounters only; encounter #1 returns 404 |

## 4. 15-minute buyer-demo sequence

Open encounter #1 (Morgan Lee · PT-1001) as `clin@chartnav.local`.

| Time | Step | Beat |
|---|---|---|
| 0:00 – 0:30 | Open demo | "Synthetic demo environment. No real patient data on screen." |
| 0:30 – 2:00 | Patient + workspace ribbon | Show Phase 91 visit-mode + active-laterality. "Provider-driven, never inferred." |
| 2:00 – 4:00 | Vitals workup | Record OD/OS IOPs; sign; show metadata-only audit row. |
| 4:00 – 7:00 | Documentation | Scribe → review → finalize. "ChartNav drafts. The clinician signs." |
| 7:00 – 10:00 | Adaptive Overview | Walk Phase 86 panels (action queue, validation rail, retina summary/packet, anti-VEGF, glaucoma cockpit, cataract workflow, disease staging, medication safety, quality intelligence, imaging metadata, ophthalmic medication safety, advanced clinical intelligence). |
| 10:00 – 12:00 | Phase 92 advanced intelligence | Retina / glaucoma / cataract / FHIR sections; read "submission: not submitted, transport: none." |
| 12:00 – 13:30 | Packet export | Download the retina visit packet JSON; show schema_version + safety_boundaries. |
| 13:30 – 15:00 | Close + Q&A | Safety boundaries banner + demo-environment disclosure. Use `03-demo-talk-track.md` for any sensitive question. |

The full 30-minute walkthrough adds disease staging + medication
safety, cataract conversion funnel, security boundaries + audit
deep-dive, and release-evidence demo. See
`docs/demo/phase-100-controlled-pilot-buyer-demo-script.md` for
the verbatim script.

## 5. Capture evidence

```bash
bash scripts/release/phase100_controlled_pilot_launch_gate.sh

PHASE101_SMOKE_RESET=0 \
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

Hand the practice the three artifact dir paths the gate prints
(plus the Phase 88 release-evidence dir, linked from the Phase
100 bundle).

## 6. Failure recovery

| Symptom | Action |
|---|---|
| Reset script refuses to run | Confirm `DATABASE_URL` is loopback. Use the venv-free helper. |
| API `/health` returns 5xx | Re-seed; check uvicorn shell for traceback. Do not run demo. |
| Frontend renders blank tabs | `cd apps/web && npx tsc --noEmit`; re-build. Do not improvise live. |
| Phase 63C smoke fails on a single step | Re-run with `--reset` (if venv present) or re-seed via helper + re-run no-reset. |
| Phase 100 gate FAIL on any required check | Open the per-check log under the gate's dated dir; do not run the demo. |
| Forbidden phrase appears in narration | Correct immediately: "Let me re-state — ChartNav does NOT recommend treatment; it surfaces a metadata projection of provider-entered structured data." |
| Buyer asks "can you do real PHI today?" | Open `06-no-real-phi-attestation.md` Section 1 and read aloud. Offer to schedule the joint review. |

## 7. Sign-off

The operator does not present this as a customer-ready
deliverable until every checkbox below is green:

- [ ] Pre-flight Section 0 — every row PASS
- [ ] Phase 100 launch gate — OVERALL: PASS
- [ ] Phase 101 capture — OVERALL: PASS (R1; O1/O2/O3 may SKIP)
- [ ] Demo rehearsed end-to-end at least once on this build
- [ ] No forbidden narration in the rehearsal
