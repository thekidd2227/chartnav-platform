# Tablet manual sign-off — Phase A

Spec source: `docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md`
(see §4 acceptance criteria, item 5).

## Purpose

The Playwright + Axe-AA gates check the structural floor (touch
targets ≥ 44pt, no horizontal scroll, offline banner appears, no
serious/critical Axe violations). They do not, and cannot, replace
a clinician sitting in front of a real iPad Pro 12.9 in the exam
lane.

This file is the manual-QA record. A release that touches encounter
charting on tablet **must** carry an updated entry below before it
can be cut.

## Checklist (run on a physical iPad Pro 12.9 in iPadOS Safari)

Each box must be ticked, dated, and initialed by a clinical
advisor. Anything left unchecked blocks the release.

- [ ] Encounter create + chart + sign flow works end-to-end in
  **portrait** orientation.
- [ ] Same flow in **landscape** orientation.
- [ ] Sign / attest / export buttons clear the home indicator (not
  hidden under the bottom safe-area inset).
- [ ] IOP field surfaces the numeric keypad on tap; slash separator
  preserved; mm Hg suffix visible.
- [ ] VA field accepts `20/40` and `20/25-2` without auto-correct.
- [ ] MRN field does not auto-capitalize the first letter.
- [ ] Toggling airplane mode mid-encounter shows the offline banner
  within ~2s; sign and export are visibly disabled while offline.
- [ ] On reconnect, queued input flushes; any conflict surfaces a
  resolution panel rather than silently merging.
- [ ] VoiceOver reaches every primary action on the encounter page
  in logical order; the trust-tier tabs announce on change.
- [ ] Audio capture pauses when the tab is backgrounded; resume is
  explicit, not automatic.

## Sign-off log

| Release tag | Reviewer (clinical advisor) | iPad model + iPadOS | Date | Notes |
|---|---|---|---|---|
| _phase-a-foundation (preview)_ | _pending pilot_ | _pending_ | _pending_ | Spec-required structural gates green via Playwright + vitest. Manual sign-off pending pilot clinic hardware. |

## Truth note

This file is a process artifact. It does not assert ChartNav has
been certified by Apple, Epic, or any external accessibility
auditor. Phase A ships with the structural floors enforced in CI
plus this checklist; clinical pilot feedback is the next gate.
