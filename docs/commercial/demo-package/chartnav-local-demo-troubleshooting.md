# ChartNav Local Demo Troubleshooting

> First-line fixes for common demo-environment problems. If the
> issue isn't here, fall back to
> `docs/pilot/chartnav-support-runbook.md`.

---

## The browser shows "Could not load …" on every panel

**Probable cause:** API on `:8000` is not responding.

1. Check the terminal where you ran `make dev` or
   `make boot` — look for tracebacks.
2. `curl http://127.0.0.1:8000/health` should return 200.
3. If not, restart: stop the stack, then re-run `make dev`.

---

## Workspace is empty — no encounter rows

**Probable cause:** seed didn't run, or identity is unset.

1. `make reset-db` — should print *"Seed complete."*
2. Confirm identity badge says `admin@chartnav.local · admin ·
   org 1`. If not, click the identity selector and pick that
   user.
3. Hard-refresh (Cmd-Shift-R).

---

## DEMO MODE banner is missing at the top of the workspace

**Probable cause:** URL doesn't include `?demo=1` (or the
localStorage flag isn't set).

1. Confirm URL is `http://localhost:5173/?demo=1`.
2. Or open DevTools → Console and paste:

   ```
   localStorage.setItem("chartnav.demoMode", "1");
   ```

   then refresh.

---

## Stepper is on the wrong step

**Probable cause:** previous demo's state persisted in
localStorage.

1. Click **Reset demo** in the Guided Demo Mode controls.
   Stepper returns to Step 1.
2. Or run the full demo reset:

   ```
   bash scripts/reset_demo_state.sh
   ```

   then hard-refresh.

---

## Action queue is empty after clicking Generate

**Probable cause:** no finalized chart text exists yet — the
clinical-language scan only fires against finalized scribe /
signed retinal artifact / finalized patient summary content.

1. Walk the scribe lifecycle first (Steps 3–4 of Guided Demo
   Mode).
2. Optionally, sign a retinal artifact.
3. Then re-click Generate on the action queue.

---

## Pre-visit brief shows zero source counts

Same root cause as the empty action queue. The brief is a
*derived view* of existing chart records. Run the scribe and
artifact lifecycles first, then click Generate.

---

## Generate fails with `403 role_forbidden`

**Probable cause:** identity is `rev@chartnav.local` (reviewer
role — read-only).

1. Switch identity to `admin@chartnav.local` or
   `clin@chartnav.local`.
2. Refresh.

---

## Generate fails with `404 patient_not_found`

**Probable cause:** identity is in the wrong org.

1. Confirm identity badge reads `admin@chartnav.local · admin ·
   org 1`. Cross-org access returns 404 by design.
2. If you're testing the cross-org behavior intentionally,
   that's expected — switch back to the chartnav org.

---

## `make reset-db` fails

**Probable cause:** dev DB file is locked, or the venv didn't
install cleanly.

1. Try `rm -f apps/api/chartnav.db` and re-run `make reset-db`.
2. If that fails, re-run `make install` to rebuild the venv.

---

## `bash scripts/reset_demo_state.sh` says "REFUSED"

**Probable cause:** `DATABASE_URL` is set to something other
than `sqlite:///<path>`.

This is the safety guard. The script refuses to reset anything
other than the local SQLite dev DB.

1. `unset DATABASE_URL`
2. Re-run the reset script.

---

## Browser cache hides a fresh demo update

**Probable cause:** the dev server served a stale bundle.

1. Hard-refresh (Cmd-Shift-R).
2. If still stale, close the browser tab and reopen.

---

## "Address already in use" when starting the stack

**Probable cause:** another process is bound to `:8000` or
`:5173`.

1. `lsof -i :8000` — if anything is listed, kill it (or change
   the port via the API's `--port` flag).
2. `lsof -i :5173` — same for the frontend.
3. Re-start the stack.

---

## I ran the demo against staging by accident

If you somehow pointed the local browser at the staging stack:

1. Don't proceed — staging is fake-data only but not the same
   environment as the demo.
2. Stop the demo. Switch the browser back to `localhost:5173`.
3. Verify the API health endpoint at
   `http://127.0.0.1:8000/health` returns 200 from the local
   stack.

If you ran the demo against a **controlled-pilot** environment
by accident — stop immediately. Treat as an `S1` per the support
runbook (`docs/pilot/chartnav-support-runbook.md`). Demos run on
local fake data only.

---

## What to do if you can't fix it before the meeting

1. Don't fake the demo on a non-working environment.
2. Walk the buyer through the click path verbally using the
   one-page sales deck.
3. Hand them the pilot readiness packet.
4. Schedule a follow-up demo within 24 hours after the issue
   is fixed.
5. File the issue against
   `docs/pilot/chartnav-support-runbook.md` so it doesn't
   recur.
