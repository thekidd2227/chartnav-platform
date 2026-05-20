# Phase 63 — Safe Demo Media + Website Video Integration Report

> **Status: NO-GO for website video publication.**
>
> Source-safety is clean. The capture infrastructure, the safe-
> video plan, and the rejection of every unsafe phrasing from the
> original request are all in place. What is missing is the
> actual `.webm` files: the build sandbox has no display, so the
> operator captures them on the iMac. Until those files exist on
> disk, the website is **not** updated with video elements (broken
> `<video>` tags or empty `<source>`s are explicitly out of scope).

## 1. What videos were requested

The operator asked for videos showcasing:

- "automated hands-free scribing"
- "ambient capture with regular chatter ignored and medical
  findings listened to"
- fundus findings and capture
- vitals capture
- doctor sign-off on findings and scribe capture
- videos on the website

## 2. Unsafe requested phrases that were rejected

Phase 63 explicitly rejects every phrase below. None of them
appear in the safe-video plan, in the capture script, in the
manual-capture helper, in the website copy block, or in the
narration intent for any clip.

| Original unsafe phrase | Reason for rejection |
|---|---|
| "automated hands-free scribing" | implies autonomous live capture; ChartNav drafts from clinician-typed/pasted text |
| "ambient capture with regular chatter ignored and medical findings listened to" | implies live room-audio capture + filtering; ChartNav does not capture audio |
| "ChartNav listens to the exam room" | implies live audio capture |
| "ChartNav captures live ambient audio" | implies live audio capture |
| "AI writes the note" | implies autonomous documentation |
| "ChartNav diagnoses X" | implies diagnosis |
| "AI interprets the fundus" / "fundus diagnosis" | implies image interpretation |
| "HIPAA compliant" / "certified EHR" / "EHR replacement" | unapproved compliance / certification / replacement claim |

These pairs are encoded in the existing claim scanners
(`scripts/check_demo_claims.sh`, `scripts/check_website_claims.sh`,
`scripts/check_commercial_claims.sh`). Any narration or website
copy that strays into the rejected column will fail the scanner
before publication.

## 3. Safe replacement framing

The eight clips ship with these approved safe titles + safe
messages. The operator may rephrase narration within each safe
message, but must not introduce phrases from the rejected list.

| Clip | Safe title | Safe message |
|---|---|---|
| 01 | Workflow Workspace | ChartNav is a provider-reviewed workflow layer alongside the EHR. |
| 02 | Technician Workup & Vitals | Manual structured intake with provider-review prompts. |
| 03 | Provider-Reviewed VisitDraft Assist | Fake clinician-provided transcript becomes structured facts and a draft for clinician review. |
| 04 | VisitDraft Signal Filter | In a pasted fake transcript, ChartNav extracts clinically relevant stated facts and flags missing information for provider review. |
| 05 | Provider-Reviewed Fundus Drawing Assist | Clinician-entered findings text becomes a structured retinal diagram. |
| 06 | Doctor Review, Attestation, and Signed Lock | Doctor reviews, attests, signs, and locks Vitals, VisitDraft, and Fundus artefacts. |
| 07 | What ChartNav Did Not Do | Runtime safety, claim scanners, and visible "did not do" panels reinforce boundaries. |
| 08 | ChartNav Controlled Demo Highlight Reel | Workspace → Vitals → VisitDraft → Fundus Drawing → Doctor Sign-Off → Safety Posture. |

Full plan: `docs/demo/phase-63-safe-website-video-plan.md`.

## 4. Media capture method

Two-stage:

1. **Primary — Playwright headed capture** via
   `scripts/demo/capture_phase63_safe_demo_media.mjs`. Drives the
   local dev stack at `http://localhost:5173` with the seeded
   Morgan Lee fake demo encounter, sets header-auth identity via
   `localStorage.chartnav.devIdentity`, clicks through real
   `data-testid` selectors on the Vitals / VisitDraft / Fundus
   panels, and records each clip into `.webm` via Playwright's
   built-in `recordVideo` API. Refuses to run if `CHARTNAV_ENV` is
   production / staging / controlled-pilot, or if real-PHI gates
   are on.
2. **Fallback — manual capture** via
   `~/Desktop/ChartNav-Buyer-Demo-Build/prepare-phase63-video-capture.sh`,
   which opens the local app, the safe-video plan, the capture
   folders, QuickTime, and Screenshot. The operator records
   manually if Playwright cannot drive the UI on this iMac (e.g.
   because of an auth header propagation issue or because a
   transient vendor popup blocks the script).

Both paths write to the same target filenames so the manifest
keeps a single source of truth.

## 5. Files actually created in this phase

| Path | Purpose |
|---|---|
| `docs/demo/phase-63-safe-website-video-plan.md` | Eight-clip plan + safe titles + must-not-say lists + website copy block. |
| `scripts/demo/capture_phase63_safe_demo_media.mjs` | Playwright headed capture script (operator runs on the iMac). |
| `artifacts/phase-62/desktop-bundle/.chartnav-demo-env` | Bundle bootstrap env so wrappers self-recover when `CHARTNAV_REPO_PATH` is unset. |
| `artifacts/phase-62/desktop-bundle/prepare-phase63-video-capture.sh` | Manual-fallback helper. Opens the app + plan + folders + QuickTime/Screenshot. |
| `artifacts/phase-62/desktop-bundle/start-api.sh` | Patched to source `.chartnav-demo-env` when `CHARTNAV_REPO_PATH` is missing. |
| `artifacts/phase-62/desktop-bundle/start-web.sh` | Same. |
| `artifacts/phase-62/desktop-bundle/run-safety-checks.sh` | Same + production-env refusal + LLM gate refusal at wrapper entry. |
| `artifacts/phase-62/desktop-bundle/run-demo-reset.sh` | Same. |
| `artifacts/phase-63/screenshots/` | Empty (`.gitkeep`) — populated by operator. |
| `artifacts/phase-63/video-clips/` | Empty (`.gitkeep`) — populated by operator. |
| `artifacts/phase-63/website-media/` | Empty (`.gitkeep`) — populated when web-optimized copies are made. |
| `artifacts/phase-63/dry-run/` | Receives a `<YYYY-MM-DD>-capture-summary.json` from the Playwright script. |
| `artifacts/phase-63/manifest.json` | Per-clip + per-screenshot truth table. All 16 entries currently `exists: false`. |
| `docs/build/phase-63-safe-demo-media-website-report.md` | This report. |

## 6. Files still missing (the operator's queue)

Eight `.webm` files in `artifacts/phase-63/video-clips/` and eight
`.png` posters in `artifacts/phase-63/screenshots/`. Filenames are
fixed by the manifest and the plan:

```
artifacts/phase-63/video-clips/01_workspace_orientation.webm
artifacts/phase-63/video-clips/02_vitals_capture.webm
artifacts/phase-63/video-clips/03_visitdraft_transcript_to_draft.webm
artifacts/phase-63/video-clips/04_visitdraft_signal_filter.webm
artifacts/phase-63/video-clips/05_fundus_drawing_assist.webm
artifacts/phase-63/video-clips/06_doctor_review_signoff.webm
artifacts/phase-63/video-clips/07_safety_posture.webm
artifacts/phase-63/video-clips/08_three_minute_highlight_reel.webm

artifacts/phase-63/screenshots/01_workspace_orientation.png
artifacts/phase-63/screenshots/02_vitals_capture.png
artifacts/phase-63/screenshots/03_visitdraft_transcript_to_draft.png
artifacts/phase-63/screenshots/04_visitdraft_signal_filter.png
artifacts/phase-63/screenshots/05_fundus_drawing_assist.png
artifacts/phase-63/screenshots/06_doctor_review_signoff.png
artifacts/phase-63/screenshots/07_safety_posture.png
artifacts/phase-63/screenshots/08_highlight_reel_thumbnail.png
```

The manifest's `exists` flag is `false` for all sixteen until the
operator runs the capture pass and flips each to `true`.

## 7. Was the website updated?

**No.** Per the brief: "If actual videos do not exist: do NOT add
broken video elements to the website. Instead add no website
change."

`apps/web/` is untouched in Phase 63. No new component, no new
landing-page section, no `apps/web/public/demo-media/` folder, no
test changes. The `apps/web/src/i18n/landing.en.ts` /
`landing.es.ts` copy decks are not edited.

The website integration is Phase 63B's job, and it can only land
when:

1. All eight `.webm` files exist on disk.
2. The operator has reviewed each clip against the
   must-not-say list in the safe-video plan.
3. A teammate has spot-checked the captures for forbidden text /
   real-PHI exposure / vendor-key leakage.
4. The manifest's eight video entries all have
   `website_ready: true`.

## 8. Website routes / components changed

**None.** No React routes, no `apps/web/src/` component, no new
test, no test deletion, no i18n key. The vitest + tsc + build
pipeline for the website is untouched by Phase 63.

## 9. Safety checks run

| Check | Status |
|---|---|
| `scripts/check_runtime_safety.py` | PASS (re-verified pre-commit; see § 11 below) |
| `scripts/check_commercial_claims.sh` | PASS |
| `scripts/check_website_claims.sh` | PASS |
| `scripts/check_demo_claims.sh` | PASS (new safe-video plan doc added to FILES list; 0 hits across 31 demo files) |
| `scripts/test_claim_policy_fixtures.sh` | PASS |
| `scripts/check_alembic_safety.sh` | PASS |
| `git diff --check` | clean |
| Manifest schema | hand-verified; 8 screenshots × 8 video clips × correct counts |
| Capture script syntax | `node --check` clean |
| Bundle wrappers | `bash -n` clean for all 5 wrappers |

## 10. GO / NO-GO for website publication

**NO-GO.** Website integration is blocked by missing media. See § 7.

The buyer-demo dry-run separately (Phase 62A scaffold,
`artifacts/phase-62/dry-runs/2026-05-20/report.md`) is still
**NO-GO** for live buyer demo until the operator captures the
Phase 62 evidence set. Phase 63 does not change that signal — it
adds a Phase 63 capture path that produces the same artefacts in
a website-friendly form (`.webm` + poster `.png`).

When both:

- the Phase 62A dry-run report flips to GO **and**
- all sixteen Phase 63 manifest entries flip `exists: true` /
  `website_ready: true`

then Phase 63B (website integration) becomes unblocked.

## 11. No real PHI confirmation

- The Playwright script uses only the seeded Morgan Lee fake demo
  encounter (`apps/api/scripts_seed.py`).
- The signal-filter clip's transcript is hard-coded to include
  small-talk lines that are obviously not PHI ("How's the dog
  doing?", "Did you watch the game last night?").
- No vendor API key is read by the capture path.
- The script refuses to run if `CHARTNAV_REAL_PHI_ENABLED=1` or
  `CHARTNAV_LLM_REAL_PHI_APPROVED=1` is set.
- The bundle wrappers refuse to run on `CHARTNAV_ENV=production /
  staging / controlled-pilot`.

## 12. No production LLM confirmation

- `CHARTNAV_LLM_ENABLED` is forced to `0` in the bundle's
  `.chartnav-demo-env`. The wrappers refuse to run if it is `1`.
- `CHARTNAV_LLM_PROVIDER` is forced to `deterministic_stub`.
- `CHARTNAV_OPENAI_API_KEY`, `CHARTNAV_ANTHROPIC_API_KEY`,
  `CHARTNAV_WATSONX_API_KEY`, and the pilot-allow flags are
  explicitly unset by the bootstrap env file.
- The capture script does not source any vendor config and does
  not send any vendor API request.

## 13. No public overclaim confirmation

- No website file is edited.
- The approved website copy block + safe titles in
  `docs/demo/phase-63-safe-website-video-plan.md` are pre-checked
  against the three claim scanners (commercial / website / demo).
  The demo scanner already runs against this doc as part of its
  FILES list update.
- Phase 63B (website integration) cannot land without re-running
  all three scanners on the resulting copy.

## Related documents

- `docs/demo/phase-63-safe-website-video-plan.md`
- `docs/build/current-product-truth.md`
- `docs/build/phase-62a-demo-evidence-repair-audit.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `artifacts/phase-63/manifest.json`
