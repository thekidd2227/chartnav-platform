# ChartNav marketing screenshot — source audit

**Date:** 2026-06-25
**Author:** reconciliation pass (governed asset-bank establishment)
**Canonical approved location:** `public/marketing-assets/chartnav/approved/` (the ONLY source of truth)
**Staging (non-public, unreviewed):** `qa/screenshots/marketing/staging/`

## Purpose

Inventory every existing screenshot/capture source in the repo, classify each,
and decide what (if anything) is eligible for promotion into the governed
marketing asset bank. **Existence in the stash or a QA folder does not imply
approval.** Approval requires the strict gates in
`manifests/screenshot-manifest.schema.json`.

## Capture tools / sources

| Source | Exists | Class | Notes |
|---|---|---|---|
| `apps/web/tests/e2e/visual.spec.ts` | yes | active capture source (QA visual) | Playwright visual spec; QA regression, not marketing. |
| `apps/web/tests/e2e/phase19g-capture.spec.ts` | yes | active capture source (demo media) | Phase 19G capture; QA/demo evidence. |
| `apps/web/tests/screenshot-capture.mjs` | yes | active capture source | Generic screenshot capture. |
| `apps/web/tests/full-screenshot-capture.mjs` | yes | active capture source | Full-surface capture. |
| `apps/web/tests/marketing-capture.mjs` | yes (untracked, from stash) | duplicate / superseded | The stash's marketing capture; **superseded** by `scripts/marketing/capture_chartnav_marketing_assets.mjs` (governed). Not promoted here; left as historical. |
| `tools/media-review/capture_phase19g_media.sh` | yes | historical artifact | Phase 19G media review helper. |
| `scripts/demo/phase63a_capture_demo_media.mjs` | **missing** | — | Referenced by mission; not present in repo. |
| `scripts/demo/capture_phase63_safe_demo_media.mjs` | **missing** | — | Referenced by mission; not present in repo. |
| `artifacts/phase-62/`, `artifacts/phase-63/` | **missing** | — | Not present. |
| `docs/demo/` | yes | historical artifact | Demo docs/evidence; not marketing-approved. |
| `docs/commercial/phase-64-demo-asset-index.md` | **missing** | — | Not present. |
| `qa/screenshots/clinical-shortcuts/` | yes | QA evidence | Clinical-shortcuts QA captures; not marketing. |
| `qa/screenshots/marketing/*.png` (10 files) | yes (untracked, from stash) | **prohibited for marketing use as-is** | See per-file review below. |

> QA/test/phase/artifact folders remain **historical evidence** and are not
> moved or deleted; nothing depends on them for marketing.

## Per-file review — `qa/screenshots/marketing/` (10 PNGs, May 19 capture)

Pixel-inspected: **01, 04, 05, 06** (representative: empty-canvas, chrome-bearing,
clean list, standalone graphic). The remaining six were gated on the
**provenance** rule below, which applies uniformly; they were not individually
pixel-audited (flagged honestly — re-capture is required regardless).

| File | Pixel-checked | Findings | Decision |
|---|---|---|---|
| 01-chartnav-encounter-workspace.png | yes | synthetic data (Jordan Rivera/PT-1002); **"POWERED BY ARCG SYSTEMS" footer** (wrong/old branding); ~2008×13844 mostly-empty canvas (poor composition). | archive |
| 02-chartnav-quick-comments-clinical-palette.png | no | provenance gate. | archive |
| 03-chartnav-clinical-shortcuts-search.png | no | provenance gate. | archive |
| 04-chartnav-admin-panel.png | yes | **localhost API debug chip in top bar** (`API http://localhost…`) **and** "POWERED BY ARCG SYSTEMS" footer. Hard fails localhost + debug-UI + old-branding gates. | archive |
| 05-chartnav-encounter-list.png | yes | clean synthetic list; no chrome in crop; **but no commit-SHA provenance**. | archive |
| 06-chartnav-trust-model-pipeline.png | yes | clean standalone graphic (TRANSCRIPT→EXTRACTED FACTS→AI DRAFT→PROVIDER SIGNED); no PHI/chrome; **but no commit-SHA provenance**. | archive |
| 07-chartnav-dictation-input.png | no | provenance gate. | archive |
| 08-chartnav-full-encounter-workspace.png | no | provenance gate (chrome-bearing; same global localhost chip + ARCG footer expected). | archive |
| 09-chartnav-new-encounter.png | no | provenance gate. | archive |
| 10-chartnav-encounter-timeline.png | no | provenance gate. | archive |

### Disqualifying conditions

1. **No verifiable provenance (applies to all 10).** None carry capture
   metadata or a commit SHA, so `app_version` (required: 40-char SHA) and
   `captured_from = "real running application"` cannot be honestly asserted.
   They were produced outside the governed pipeline and predate the current
   reconciled build.
2. **Localhost / debug UI (chrome-bearing frames).** The shared top bar shows a
   `API http://localhost…` chip (confirmed in 04) — fails `contains_localhost`
   and `contains_debug_ui`.
3. **Old / wrong branding.** A `POWERED BY ARCG SYSTEMS` footer (confirmed in
   01, 04) is not ChartNav branding.

## Decision

**No screenshot is promoted.** All 10 are archived as `archived-not-approved`
in `archive/` and recorded in the manifest; they are excluded from the
marketing agent's approved query (`approved-assets.json`). The `approved/`
tree is intentionally empty pending **fresh captures through the governed
pipeline** (`scripts/marketing/capture_chartnav_marketing_assets.mjs`), which
runs the real app in demo mode (hiding the localhost/API chip), uses ChartNav
branding, and writes commit-SHA + timestamp capture metadata. Those staged
captures are then human-reviewed and promoted via
`scripts/marketing/promote_chartnav_asset.py`.

This is deliberately conservative: it satisfies "do not classify a screenshot
as approved merely because it exists in the stash" and keeps every approved
asset provably from a known, clean ChartNav build.
