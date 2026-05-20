# ChartNav — Demo Asset Index (Phase 64)

> **Pointer index for buyer-demo media + the new functional
> readiness gate.** Distinguishes **media presence** (Phase 63A)
> from **functional readiness** (Phase 63C / 63C-2). A buyer who
> sees only "media exists" is not the same as a buyer who sees
> the functional smoke return GO.

## 1. Functional readiness — the canonical gate

The Phase 63C functional smoke is the authoritative
buyer-demo-readiness gate. It exercises the actual HTTP API for
Vitals, VisitDraft, Fundus, and manual_note payload shaping.

| Item | Value |
|---|---|
| Script | `scripts/demo/phase63c_functional_smoke.sh` |
| Latest local outcome | **`BUYER-DEMO FUNCTIONAL GO: YES`** |
| Commit basis | `8d2b6dd` (Phase 63C-2 on `main`) |
| Includes | DB at Alembic head + required tables, seeded clinician + Morgan encounter introspection, API + frontend health, Vite-path-not-misrouted guard, full Vitals lifecycle (create → enter → review → sign), full VisitDraft lifecycle, full Fundus lifecycle, manual_note string-rejected and object-accepted. |
| Recovery flag | `--reset` runs `bash scripts/reset_demo_state.sh` first for a clean Morgan-only DB. |

Run it (operator-side):

```bash
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

> **Media presence ≠ buyer-demo functional GO.** Phase 63A's
> "30 screenshots + 12 video clips exist" gate is a media gate,
> not a functional gate. Both gates must be green for an outreach
> conversation to lean on demo evidence; the functional smoke is
> the stronger signal.

## 2. Captured media (Phase 63A)

| Folder | Contents |
|---|---|
| `artifacts/phase-62/screenshots/` | 30 PNG screenshots from a real Playwright headed run against the live local stack. Filenames follow `01_workspace_landing.png` through `30_product_truth_safety_statements.png`. |
| `artifacts/phase-62/video-clips/` | 12 video clips (`.webm` / `.mov`) covering workspace, vitals, VisitDraft, fundus, sign-off, and safety-terminal evidence. |
| `artifacts/phase-62/dry-runs/2026-05-20/report.md` | The dated dry-run report describing how the media was captured + transparency caveats. |

These artefacts are **not committed binaries** — they are
generated locally by the Phase 63A capture script. The capture
script + the count gate live in:

- `scripts/demo/phase63a_capture_demo_media.mjs` — Playwright
  capture script.
- `scripts/demo/phase63a_count_media.sh` — file-presence gate
  (exit 0 iff every required filename exists).
- `scripts/demo/phase63a_start_demo_stack.sh` — boots the local
  API + frontend with the safe-env file and refuses any real
  vendor `*_API_KEY`.
- `scripts/demo/phase63a_open_media_review.sh` — opens the
  screenshot and video folders, the dated report, the
  release-evidence checklist, and `current-product-truth.md` for
  buyer-demo media review.

## 3. Operator commands the buyer can re-run

The buyer's technical reviewer can re-run any of these on their
own machine after cloning the repo:

| Command | Purpose |
|---|---|
| `bash scripts/check_runtime_safety.py` (via `python3`) | Runtime safety validator. |
| `bash scripts/check_commercial_claims.sh` | Phase 17 commercial-claims scanner. |
| `bash scripts/check_website_claims.sh` | Public landing-page claims scanner. |
| `bash scripts/check_demo_claims.sh` | Demo-surface claims scanner. |
| `bash scripts/check_alembic_safety.sh` | Migration safety. |
| `bash scripts/demo/phase63c_functional_smoke.sh` | Phase 63C buyer-demo functional gate. |
| `bash scripts/demo/phase63a_count_media.sh` | Phase 63A media-presence gate. |
| `bash scripts/demo/phase63a_open_media_review.sh` | Open the media review surfaces locally. |

## 4. Demo storyline and narration

| Path | What it covers |
|---|---|
| `docs/demo/phase-62-end-to-end-demo-visit-script.md` | The end-to-end ~13 min visit narration for the controlled demo. |
| `docs/demo/phase-62-screenshot-shot-list.md` | What each of the 30 screenshots must show + must not show. |
| `docs/demo/phase-62-video-clip-shot-list.md` | What each of the 12 video clips must show + must not show. |
| `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` | What the buyer-demo evidence packet must contain. |
| `docs/demo/phase-62a-buyer-demo-go-no-go-status.md` | One-page GO / NO-GO snapshot. |
| `docs/demo/phase-61-buyer-qa-safe-answers.md` | 20-question buyer Q&A bank. |

## 5. What this index is NOT

- It is not a marketing site. The public website is out of scope
  for Phase 64.
- It is not a promise that media has been reviewed for any
  specific buyer's use case — that review is per-engagement.
- It is not a certification document. ChartNav does not hold
  HIPAA / SOC 2 / HITRUST / FDA certification.
- It does not claim other practices have used the demo — Phase
  64 outreach uses ChartNav's own controlled fake-data demo only.

## Safety note

- Fake-data demo first.
- Paid pilot subject to security review for any real-PHI use.
- Provider review and sign-off required on every artefact.
- ChartNav is not HIPAA-certified.
- ChartNav is not a certified EHR and does not replace any EHR.
- ChartNav does not diagnose.
- ChartNav does not interpret fundus or OCT images.
- ChartNav does not place orders, send referrals, or message patients.
- ChartNav does not bill or code.
- ChartNav does not integrate with medical devices and does not provide remote patient monitoring.

## Related documents

- `docs/build/current-product-truth.md`
- `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
- `docs/build/phase-63c-demo-critical-functional-repair-report.md`
- `docs/build/phase-63c1-functional-smoke-500-repair-report.md`
- `docs/build/phase-63c2-vitals-smoke-transition-repair-report.md`
- `docs/commercial/phase-64-security-review-packet-index.md`
- `docs/commercial/phase-64-paid-pilot-positioning.md`
