# ChartNav Operator Demo Deck

> **Internal-only.** Used by the operator (Jean-Max / Maria) to
> rehearse the live ChartNav demo before a buyer meeting. 8 slides.
> Pair with `docs/demo/chartnav-clinical-workflow-demo-script.md`
> (what to say) and `docs/demo/chartnav-demo-click-path.md` (what
> to click).

**Audience:** internal — the operator running the live demo.
**Purpose:** pre-flight checklist + reset commands + fallback
plan in one place. **Never** present this deck to a buyer.
**CTA / next step:** dry-run the full click path against a fresh
local stack within 60 minutes of the demo meeting.

**Safe-claims contract.** Every slide obeys the approved-language
list at `docs/commercial/chartnav-approved-claims-language.md`.

---

## Slide 1 — Cover (operator-only)

- **Title:** ChartNav demo — operator pre-flight.
- **Content:**
  - "Internal rehearsal deck. Not for buyers."
  - "Pair with the buyer demo deck for what to actually say on
    screen."
- **Visual:** logo + "INTERNAL" stamp.

## Slide 2 — Boot the local stack

- **Title:** Boot the demo stack.
- **Content:**
  - From the desktop launcher: double-click
    `08_Local_Demo_Launcher/START_CHARTNAV.command`.
  - From the terminal: `cd <repo>` then `make dev`.
  - Verify the API health endpoint returns `200`.
  - Confirm the browser opens to
    `http://localhost:5173/?demo=1`.
- **Speaker notes:** Boot the stack at least 60 minutes before
  the meeting; if anything fails, fall back to the verbal walk-
  through using the buyer demo deck slides.
- **Visual:** terminal mock.

## Slide 3 — Reset demo data

- **Title:** Reset between rehearsals (and after the live demo).
- **Content:**
  - Click **Reset demo** in Guided Demo Mode for a stepper-only
    reset.
  - For a full reset, run `bash scripts/reset_demo_state.sh` from
    the repo root.
  - The reset script refuses to run if `DATABASE_URL` points at
    anything other than the local SQLite default — that's by
    design.
  - Hard-refresh the browser (Cmd-Shift-R) after a full reset.
- **Speaker notes:** Always reset between rehearsals. Never
  demo with leftover state from a previous walkthrough.
- **Visual:** two-step diagram (stepper reset vs. full reset).

## Slide 4 — Pre-flight checklist (within 60 minutes of meeting)

- **Title:** What to verify before the buyer joins.
- **Content:**
  - Identity badge reads `admin@chartnav.local · admin · org 1`.
  - `enc-row-1` (Morgan Lee) opens cleanly.
  - DEMO MODE banner appears at the top of the workspace.
  - All five clinical panels render
    (eye-diagram, scribe, patient-summary, pre-visit-brief,
    provider-action-items).
  - No console errors on page load.
  - Demo deck open in a second window for narration.
  - Buyer demo deck open as the on-screen narration source.
- **Speaker notes:** If any item fails, fix or fall back per
  the troubleshooting doc.
- **Visual:** 7-row checklist.

## Slide 5 — Click path

- **Title:** What to click, in order.
- **Content:**
  1. `enc-row-1` to open the encounter.
  2. Pre-visit brief — generate.
  3. Scribe — paste source / transcript text → review → finalize.
  4. Findings proposals — generate from finalized findings text.
  5. OD/OS retinal diagram — apply each proposal → save → sign.
  6. Patient-friendly summary — generate → review → finalize.
  7. Action review queue — accept the suggested review tasks.
  8. Reset demo before closing.
- **Speaker notes:** Mirror the in-product Guided Demo Mode
  stepper. Don't extemporize the click order.
- **Visual:** 8-step list.

## Slide 6 — Fallback plan if the stack breaks mid-demo

- **Title:** What to do if something fails on screen.
- **Content:**
  - Don't fake it on a half-working environment.
  - Switch to the buyer demo deck and walk the click path
    verbally, slide by slide.
  - Hand the buyer the one-page sales deck and the pilot
    readiness packet.
  - Schedule a follow-up demo within 24 hours after the issue is
    fixed.
  - File an issue against the support runbook so it does not
    recur.
- **Speaker notes:** Buyers tolerate a deferred demo. They do
  not tolerate a broken-feeling product.
- **Visual:** 5-step fallback flow.

## Slide 7 — Stop the stack after the demo

- **Title:** Tear down cleanly.
- **Content:**
  - From the desktop launcher: double-click
    `08_Local_Demo_Launcher/STOP_CHARTNAV.command`.
  - From the terminal: `Ctrl-C` in the terminal where `make dev`
    is running.
  - Verify ports `:8000` and `:5173` are released
    (`lsof -i :8000` and `lsof -i :5173`).
- **Speaker notes:** Always stop the stack between demos. Stale
  servers leak browser state.
- **Visual:** terminal mock.

## Slide 8 — Safety reminders for the operator

- **Title:** Operator safety contract.
- **Content:**
  - Demos run on **fake data only** by construction.
  - Never load real PHI into a local or staging environment.
  - Never run the reset script against staging or controlled-
    pilot environments.
  - Read the safety bullets aloud at the start of every demo.
  - If a question pushes past the safe-claims contract, fall
    back to the buyer-objection-handling answers verbatim.
- **Speaker notes:** This is what keeps Phase 17B safe across
  every rehearsal and live run.
- **Visual:** plain bullets.
