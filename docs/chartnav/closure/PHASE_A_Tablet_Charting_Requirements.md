# Phase A — Tablet Charting Requirements

## 1. Problem solved

Ophthalmology techs and physicians chart on iPads, not desktops. The buyer brief flagged that ChartNav's UI was designed desktop-first and has not been proven on the iPad Pro 12.9 form factor that dominates the exam lane. A tablet experience that fails on touch targets, safe-area, keyboard behavior, or Axe-AA undercuts the "ophthalmology-first" promise at the only surface the clinician actually touches.

This spec defines the tablet charting bar ChartNav must clear before any pilot clinic is given iPads. It is a product requirement, not an OS port — ChartNav remains a web app served to iPad Safari.

## 2. Current state

- The web app renders on iPad Safari and is functionally usable, but was designed and tested primarily at desktop breakpoints.
- Axe-AA gate in `qa/a11y/` runs on desktop viewports; tablet viewports are not part of the release gate today.
- Audio capture uses `navigator.mediaDevices.getUserMedia` and works in iPad Safari 15+. The STT stub (`[stub-transcript]` emitter) does not stress-test microphone permission, background-tab suspension, or mic hand-off to another app.
- Touch targets and form-field hints are inherited from generic component defaults; no ophthalmology-specific input affordances (numeric keypad on IOP, mm-Hg suffix, slash-separator discipline).
- **ChartNav is not offline-first.** There is no service worker for clinical data, no IndexedDB queue, no background sync.

## 3. Required state

**3.1 Layout and touch.**

- Touch targets ≥ 44pt (iOS HIG); the encounter-page primary actions (sign, attest, save, export) meet or exceed this and do not collide in landscape or portrait.
- Safe-area insets respected via `env(safe-area-inset-*)` — notch and home-indicator do not obscure actionable UI on iPad Pro 12.9 (both orientations) and iPad Air 11.
- Landscape and portrait layouts both render the 3-tier trust UI (transcript / findings / draft) without horizontal scrolling on the default 1024×1366 and 1194×834 viewports.

**3.2 Form-field behavior.**

- IOP fields: `inputmode="decimal"` with a custom slash separator between OD and OS; numeric keypad surfaces by default.
- VA fields: autocomplete off; no auto-capitalize; slash form supported (`20/40`, `20/25-2`).
- MRN field: `autocapitalize="off"`, `autocorrect="off"`, `spellcheck="false"`.
- Name and free-text note fields: sentence-case auto-capitalize permitted; spell-check on.

**3.3 Network and offline.**

- Explicit assertion: ChartNav is **not** offline-first.
- When the network drops, the tablet queues input locally in browser storage (IndexedDB), shows a persistent banner — `data-testid="offline-banner"` — and refuses state transitions (`sign`, `export`) while offline.
- On reconnect, the queue flushes; any conflict with a newer server version is surfaced with a conflict resolution panel, never silently merged.

**3.4 Audio capture.**

- Mic permission requested at first use only; persisted per-origin by Safari.
- If the tab is backgrounded, recording pauses and the UI shows a resumable state; the provider must explicitly resume.
- Documented limitation: iPad Safari will release the mic when an incoming call or FaceTime starts; ChartNav stops capture, preserves the partial transcript, and prompts the user.

**3.5 Accessibility.**

- Axe-AA passes on the tablet viewport set.
- VoiceOver can reach every actionable control on the encounter page in logical order; the 3-tier trust UI announces each tab change.

## 4. Acceptance criteria

- Playwright mobile device profile tests in `qa/e2e/tablet/` exercise both the iPad Pro 12.9 (1024×1366) and iPad Air 11 (1194×834) profiles, in both orientations, covering encounter create → chart → sign.
- Axe-AA gate in `qa/a11y/` runs against both tablet viewports in addition to desktop. CI fails the release if any tablet scan has a serious or critical violation.
- `qa/e2e/tablet/offline.spec.ts` simulates offline by intercepting network; verifies the banner, the disabled sign action, and the on-reconnect flush.
- Touch-target audit script `qa/a11y/touch_targets.ts` confirms every interactive element on the encounter page has a hit-box ≥ 44×44 CSS pt at both viewports.
- Manual QA checklist signed by a clinical advisor on a physical iPad Pro 12.9 — captured in `docs/chartnav/qa/tablet_manual_signoff.md`.

## 5. Codex implementation scope

- `apps/web/src/styles/tablet.css` — safe-area insets, breakpoint rules for 1024–1366px portrait and 834–1194px landscape.
- `apps/web/src/features/encounter/IopInput.tsx`, `VaInput.tsx`, `MrnInput.tsx` — specialized inputs with the `inputmode`, `autocapitalize`, and separator discipline defined above.
- `apps/web/src/core/offline/queue.ts` — IndexedDB-backed queue with per-encounter key, single-writer guarantee, and a `useOnlineStatus` hook driving the banner.
- `apps/web/src/core/offline/OfflineBanner.tsx` — `data-testid="offline-banner"`.
- `apps/web/src/features/encounter/AudioCapture.tsx` — background-tab pause handler; permission-error surface.
- `qa/e2e/tablet/*.spec.ts` — Playwright specs.
- `qa/a11y/touch_targets.ts` — audit script invoked from the release gate.

## 6. Out of scope / documentation-or-process only

- Native iOS app (React Native or Swift). Not in scope.
- Offline-first clinical documentation with full merge / CRDT semantics. Not in scope; explicitly documented as a non-goal for Phase A.
- Stylus/Apple Pencil drawing (e.g. corneal diagrams). Parked.
- Peripheral integration (Tonopen, Lensmeter, OCT workstation handoff). Parked.

## 7. Demo honestly now vs. later

**Now:** chart a retina encounter on a physical iPad Pro in both orientations, toggle airplane mode mid-note and show the banner plus the replay on reconnect, run VoiceOver through the sign flow.

**Later:** full offline-first documentation, Apple Pencil annotation, native iOS wrapper if a clinic insists on App Store distribution.

## 8. Dependencies

- Phase A Encounter Templates (layouts depend on the template's section order).
- Phase A Structured Charting and Attestation (sign flow is the single end-of-encounter action tested on tablet).
- Phase A RBAC (role chip must remain visible on tablet).

## 9. Truth limitations

- ChartNav is **not** offline-first. A clinic with unreliable network will feel the limitation.
- iPad Safari audio behavior is bounded by Apple. We document limitations; we do not claim we can work around them.
- Axe-AA is a useful floor, not a ceiling. A passing Axe-AA scan is necessary but not sufficient for accessibility; ongoing manual review with a screen-reader user is the real bar.

## 10. Risks if incomplete

- Techs and clinicians abandon ChartNav within the first week because the iPad layout hides the sign button under the safe-area, or the IOP keypad defaults to the alphabet. Pilot fails for reasons unrelated to clinical value.
- An accessibility complaint from a patient or staff member (ADA Title III) on a tablet-only surface becomes a legal exposure the company is not prepared for.
- A network blip during the pre-sign modal drops the attestation silently if the offline guard is missing, compromising the locked-record story the Structured Charting spec depends on.
