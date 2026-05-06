# ChartNav Local Demo Startup Guide

> How to boot the local stack on your Mac and open the demo URL.
> Pair with `chartnav-local-demo-troubleshooting.md` (when things
> break) and `chartnav-demo-review-checklist.md` (the operator
> dry-run before a meeting).

---

## One-time setup

You only do this once per machine.

1. Install Node 18+ (or whatever the repo's `apps/web/package.json`
   currently requires).
2. Install Python 3.11+.
3. From the repo root:

   ```
   make install        # backend venv + dev deps
   make web-install    # frontend deps
   make reset-db       # alembic migrate + seed (idempotent)
   ```

4. Verify the seed: `make seed` should print
   *"Seed complete."*

---

## Start the stack

Two options. Pick one.

### Option A — `START_CHARTNAV.command` (Desktop launcher)

If Phase 17's desktop demo package is exported to your Desktop:

1. Open `/Users/jean-maxcharles/Desktop/chartnav decks/`.
2. Double-click `08_Local_Demo_Launcher/START_CHARTNAV.command`.
3. The script `cd`s into
   `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform`,
   boots the local stack, and opens the browser to
   `http://localhost:5173/?demo=1`.

### Option B — `make dev` (manual)

From the repo root:

```
make dev
```

This boots the API on `:8000` and the frontend on `:5173`. Open
`http://localhost:5173/?demo=1` in your browser.

---

## Open the right URL

Depending on what you're showing:

- **Live demo for a buyer:** `http://localhost:5173/?demo=1` —
  this enables the Phase 15 Guided Demo Mode stepper.
- **Public landing / proof page:**
  `http://localhost:5173/?intro=1` (or `/landing`) — this is the
  Phase 16 buyer-readable landing page.
- **Workspace (no demo overlay):** `http://localhost:5173/` —
  the unmodified product view.

If you want both the landing page and the demo overlay:
`http://localhost:5173/landing` then click into the workspace and
append `?demo=1` once you're at an encounter.

---

## Confirm before the meeting

- [ ] Identity badge reads `admin@chartnav.local · admin · org 1`.
- [ ] `enc-row-1` (Morgan Lee) opens cleanly.
- [ ] DEMO MODE banner appears at the top of the workspace.
- [ ] Phase 13 collapsed demo guide appears below the banner.
- [ ] All five clinical panels render (eye-diagram, scribe,
      patient-summary, pre-visit-brief, provider-action-items).
- [ ] No console errors on page load.

---

## Reset between demos

Two levels of reset:

### Stepper reset only

In Guided Demo Mode, click **Reset demo**. The stepper returns to
Step 1; no data is touched.

### Full reset

```
bash scripts/reset_demo_state.sh
```

What it does:
1. Refuses to run if `DATABASE_URL` is anything other than
   `sqlite:///<path>` (refuses against staging / controlled-pilot).
2. Runs `make reset-db` (alembic migrate + idempotent seed).
3. Prints a DevTools snippet for clearing browser-side demo state
   (`localStorage.removeItem("chartnav.demoStep")` etc.).

After a full reset, hard-refresh the browser (Cmd-Shift-R).

---

## Stop the stack

Two options. Pick one.

### Option A — `STOP_CHARTNAV.command` (Desktop launcher)

If Phase 17's desktop demo package is exported to your Desktop:

1. Double-click
   `08_Local_Demo_Launcher/STOP_CHARTNAV.command`.

### Option B — Terminal interrupt

If you started the stack with `make dev` in a terminal, press
**Ctrl-C** to stop it. Use `lsof -i :8000` and `lsof -i :5173`
to verify nothing is still bound to those ports.

---

## What the demo environment is and is not

✅ The local demo environment **is**:
- Fake-data only (`demo-eye-clinic` org, PT-1001 Morgan Lee).
- Safe for live demos with buyers, advisors, investors, partners.
- Reset-able via the demo reset script.

❌ The local demo environment **is not**:
- A staging environment (use `make staging-up` for staging).
- A controlled-pilot environment (use the Phase 14 deployment
  guide for that).
- Suitable for real PHI (real PHI requires controlled-pilot mode
  with BAA + security review).
