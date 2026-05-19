# ChartNav Operator Demo Deck

> **Internal-only.** Used by the operator (Jean-Max / Maria) to
> rehearse the live ChartNav demo before a buyer meeting. 8 slides.
> Pair with `docs/demo/chartnav-clinical-workflow-demo-script.md`
> (the original Phase-6→11 narration), the newer
> `docs/demo/chartnav-ophthalmology-demo-script.md` (Phase
> 20C / 21A / 21B narration), and
> `docs/demo/chartnav-demo-click-path.md` (what to click — Phase
> 21C addendum at the bottom of that doc covers the new
> dashboards / tracking / imaging surfaces).
>
> **Phase 21C-follow-up.** Click path slide expanded with the
> three new Phase 20C / 21A / 21B paths (role dashboards, retina
> + glaucoma tracking, imaging pipeline). Safety reminders point
> at the ophthalmology language guide.

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
  - Phase 20C role-based **Dashboard** sidebar entry opens —
    use the *View as* selector to confirm all five role views
    (front desk / technician / doctor / reviewer / admin) load.
  - Phase 21A **Specialty Tracking** panel renders at the top
    of the Clinical tab for the seeded patient.
  - Phase 21B **Imaging Pipeline** panel renders at the top of
    the Imaging tab.
  - No console errors on page load.
  - Buyer demo deck open as the on-screen narration source.
- **Speaker notes:** If any item fails, fix or fall back per
  the troubleshooting doc.
- **Visual:** 9-row checklist.

## Slide 5 — Click path

- **Title:** What to click, in order.
- **Content (full ophthalmology walkthrough — 14 steps):**
  1. Sidebar → CORE → **Dashboard**. Switch identity to admin,
     toggle the *View as* selector through front desk →
     technician → doctor → reviewer → admin. Phase 20C.
  2. Sidebar → CORE → **Encounters**.
  3. `enc-row-1` (Morgan Lee, PT-1001) to open the encounter.
  4. **Overview** tab — structured patient context.
  5. **Clinical** tab — scroll the Specialty Tracking panel.
     Retina section: existing card + Mark reviewed. Glaucoma
     section: existing card + IOP measurements + visual field
     tests. Phase 21A.
  6. **Clinical** tab — clinical shortcut pill grid. Pin a
     favorite under Retina or Glaucoma.
  7. **Documentation** tab — paste source / transcript text →
     review → finalize. Provider-review badge visible.
  8. Findings proposals — generate from finalized findings text.
  9. OD/OS retinal diagram — apply each proposal → save → sign.
  10. **Imaging** tab — Imaging Pipeline panel. Click an OCT
      macula study; show file metadata table + measurements
      table. Mark reviewed (admin / clinician only). Phase 21B.
  11. Patient-friendly summary — generate → review → finalize.
  12. Action review queue — accept the suggested review tasks.
  13. **Chat** tab — open the recipient selector on a staff
      identity. Internal coordination only. Export a
      conversation.
  14. Reset demo before closing.
- **Speaker notes:** Phase 21C demo script
  (`docs/demo/chartnav-ophthalmology-demo-script.md`) is the
  authoritative narration for these 14 steps. Don't extemporize
  the click order. If the buyer is short on time, compress by
  collapsing steps 6 + 8 (clinical shortcuts + findings
  proposals) into a 30-second mention.
- **Visual:** 14-step list with phase tags.

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
  - Use the **ophthalmology language guide** at
    `docs/commercial/chartnav-ophthalmology-positioning-language-guide.md`
    as the source of truth for buyer phrasing.
  - If a question pushes past the safe-claims contract, fall
    back to the buyer-objection-handling answers verbatim
    (`docs/commercial/objections/chartnav-buyer-objection-handling.md`
    — Phase 21C added 11 ophthalmology-specific Q&A blocks).
  - **Never** name a specific device vendor (Cirrus / Spectralis
    / Triton / Optos / IOLMaster / Humphrey / Topcon) as a
    current integration. Always frame as "imaging metadata +
    review foundation; vendor adapters are future / planned."
  - **Never** claim "auto-grade DR." Do not say it.
  - **Never** claim "auto-interpret OCT." Do not say it.
  - **Never** claim "auto-determine cup-to-disc ratio." Do not say it.
  - **Never** claim "auto-select IOL power." Do not say it.
  - **Never** claim "auto-recommend anti-VEGF dosing." Do not say it.
  - ChartNav does none of these.
- **Speaker notes:** This is what keeps Phase 17B + Phase 21C
  safe across every rehearsal and live run.
- **Visual:** plain bullets.
