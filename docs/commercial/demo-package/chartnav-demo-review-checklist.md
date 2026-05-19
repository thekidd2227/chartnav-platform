# ChartNav Demo Review Checklist

> Operator dry-run before every live demo. Ten minutes,
> deliberate. Pair with `chartnav-local-demo-startup-guide.md`
> (boot the stack) and `chartnav-local-demo-troubleshooting.md`
> (fix issues you find).

---

## 24 hours before the demo

- [ ] Reboot the local stack and confirm `http://127.0.0.1:8000/health`
      returns 200.
- [ ] `bash scripts/reset_demo_state.sh` — confirm exit 0 and
      "Demo reset complete."
- [ ] Walk the full Guided Demo Mode 8-step path end to end. Time
      yourself; aim for 5 minutes.
- [ ] Confirm every panel shows its negative-assertion safety
      banner.
- [ ] Confirm no console errors during the run.
- [ ] Confirm the buyer's expected use case is supported by the
      seeded fake demo patient (Morgan Lee, PT-1001 — retina
      follow-up). If the buyer is glaucoma-focused, decide
      whether the seeded patient is good enough or whether you
      need to verbally adapt.

## 1 hour before the demo

- [ ] Reboot the stack so nothing is stale from earlier work.
- [ ] `bash scripts/reset_demo_state.sh`.
- [ ] Hard-refresh the browser (Cmd-Shift-R) at
      `http://localhost:5173/?demo=1`.
- [ ] Confirm DEMO MODE badge appears at the top.
- [ ] Confirm Phase 13 collapsed demo guide appears below it.
- [ ] Confirm the identity selector + identity badge.
- [ ] Confirm `enc-row-1` opens cleanly.
- [ ] Close every other browser tab — no notifications, no
      stale Slack pop-ups.
- [ ] Disable OS-level notifications on macOS (Focus mode) for
      the duration of the meeting.
- [ ] Have the demo deck open in a second window
      (`docs/decks/chartnav-demo-deck.md` rendered, or your
      preferred slide tool).

## 5 minutes before the demo

- [ ] Open `http://localhost:5173/?demo=1` in the browser.
- [ ] Click `enc-row-1`.
- [ ] Confirm the workspace is loaded with the DEMO MODE
      stepper at Step 1 of 8.
- [ ] Have the demo script tab open
      (`docs/demo/chartnav-clinical-workflow-demo-script.md`).
- [ ] Have the click path tab open
      (`docs/demo/chartnav-demo-click-path.md`).
- [ ] Have the objection handling tab open
      (`docs/commercial/objections/chartnav-buyer-objection-handling.md`).
- [ ] Take three breaths. Don't rush.

## During the demo

- [ ] Read the safety contract aloud at the start ("Provider-
      reviewed workflow support. ChartNav does not diagnose,
      create orders, send referrals, bill, or message patients
      automatically.").
- [ ] Pause on each panel's negative-assertion banner copy.
- [ ] Click only what the click-path doc says to click.
- [ ] Don't promise features that aren't built.
- [ ] If a question pushes past the safe-claims contract, fall
      back to the objection-handling answers verbatim.

## After the demo

- [ ] Click **Reset demo** in Guided Demo Mode.
- [ ] Send the follow-up email with:
  - The Phase 14 pilot readiness packet (`docs/pilot/`).
  - The one-page sales deck
    (`docs/decks/chartnav-one-page-sales-deck.md`).
  - The pilot hand-off checklist
    (`docs/commercial/pilot/chartnav-pilot-handoff-checklist.md`).
- [ ] Record the meeting outcome (interested / pause / pass)
      in the operator's notes (out-of-repo).
- [ ] If the buyer flagged unsafe phrasing on screen, file an
      issue immediately — don't wait for the next demo.

---

## Common mistakes to avoid

- ❌ Running the demo with leftover state from a previous
  walkthrough.
- ❌ Running with an identity in the wrong org (cross-org
  access returns 404 by design — looks broken to a buyer).
- ❌ Skipping the negative-assertion safety bullets.
- ❌ Promising orders / coding / referrals / patient
  messaging — those surfaces don't exist.
- ❌ Reading from an unfinished deck. Use the locked Markdown
  source in `docs/decks/`.
- ❌ Capturing screenshots / video on real PHI. The local
  environment is fake data only by construction; verify
  before any capture.

---

## Severity escalation

If anything during the demo looks like a data-safety incident
(possible cross-org leak, audit-log content question, etc.):

1. Stop the demo politely.
2. Open `docs/pilot/chartnav-support-runbook.md` and treat as
   `S1`.
3. Notify the engineering lead within 1 hour.
4. Don't continue the meeting on the same environment until
   resolution.
