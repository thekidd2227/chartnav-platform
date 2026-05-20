# TEST VISIT SCRIPT

> This is a copy of `docs/demo/phase-62-end-to-end-demo-visit-script.md`
> for offline use during the dry run. The authoritative source lives
> in the repo. If the two diverge, the repo wins.

Open the repo copy at:

```
$CHARTNAV_REPO_PATH/docs/demo/phase-62-end-to-end-demo-visit-script.md
```

And read it in your editor while you drive the demo in the browser.
Alternative: open this file in a Markdown previewer side-by-side
with the browser.

## Quick index of the visit script (read the full doc for narration)

1. **Workspace orientation** (≈ 60 sec) — open the demo encounter,
   point at the patient header + tab bar.
2. **Technician Workup & Vitals** (≈ 3 min) — Clinical tab, load
   fake demo vitals, BMI live, partial-BP warning, "What ChartNav
   did NOT do" card.
3. **Ophthalmology intake** (≈ 30 sec, folded into § 2) — VA / IOP /
   dilation section.
4. **Provider-Reviewed VisitDraft Assist** (≈ 3 min) — Documentation
   tab, fake demo transcript, structured facts, missing-information,
   "What ChartNav did NOT do".
5. **Provider-Reviewed Fundus Drawing Assist** (≈ 2.5 min) — Imaging
   tab, `Horseshoe tear 10:30 OD` chip, SVG preview, missing-
   laterality warning. **No "What ChartNav did NOT do" card on this
   surface today** (Phase 61A pinned this distinction).
6. **Warnings recap** (≈ 30 sec) — one warning per surface
   back-to-back.
7. **Provider review** (≈ 30 sec) — Reviewed pill on each surface.
8. **Sign / lock** (≈ 30 sec) — green signed-lock banner on each
   surface.
9. **Audit / safety posture** (≈ 60 sec) — side terminal:
   `python3 scripts/check_runtime_safety.py`.
10. **What ChartNav did NOT do + closing** (≈ 60 sec) — read every
    forbidden action with `(false)` on Vitals or VisitDraft;
    re-state the safety frame; pivot to Q&A using
    `docs/demo/phase-61-buyer-qa-safe-answers.md`.

Total ≈ 13 min 30 sec. Compress § 6 if running short.

## During the visit script — capture as you go

Tick off each screenshot in
`docs/demo/phase-62-screenshot-shot-list.md` (30 total) and each
video clip in `docs/demo/phase-62-video-clip-shot-list.md` (12
total) as you encounter the corresponding screen. Capture into the
repo's `artifacts/phase-62/{screenshots,video-clips}/` folders.

The shot lists tell you what must be visible and what must NOT be
visible in every frame.

## Stop-demo triggers

Halt and reset if:

- Real PHI on screen.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot`.
- Runtime safety validator returns FAIL at any point.
- A forbidden phrase appears in narration **or** UI.
- A vendor / network error exposes a secret.
- A raw transcript / draft body / vitals value appears in an audit
  log line visible during the dry run.
- Sign / finalize succeeds without the attestation checkbox being
  ticked (UI bug; escalate).

## Closing

After § 10, pivot to Q&A using
`docs/demo/phase-61-buyer-qa-safe-answers.md` (20 questions, every
answer aligned with `docs/build/current-product-truth.md`).
