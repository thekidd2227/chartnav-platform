# ChartNav Buyer-Demo Bundle — offline docs

> **Read-only snapshot.** These 12 markdown files are point-in-time
> copies of the canonical docs in the ChartNav repo. They are
> shipped with the buyer-demo bundle so the operator can read every
> demo document offline (e.g. on a plane, on a venue Wi-Fi that
> blocks GitHub).
>
> **If these copies diverge from the repo, the repo wins.** Always
> trust `$CHARTNAV_REPO_PATH/docs/...` over the bundle copy.

## What is in this folder

| Bundle copy | Canonical source in the repo |
|---|---|
| `current-product-truth.md` | `docs/build/current-product-truth.md` |
| `release-evidence-checklist.md` | `docs/release/release-evidence-checklist.md` |
| `phase-61-controlled-buyer-demo-runbook.md` | `docs/demo/phase-61-controlled-buyer-demo-runbook.md` |
| `phase-61-buyer-demo-checklist.md` | `docs/demo/phase-61-buyer-demo-checklist.md` |
| `phase-61-buyer-qa-safe-answers.md` | `docs/demo/phase-61-buyer-qa-safe-answers.md` |
| `phase-61-demo-storyboard.md` | `docs/demo/phase-61-demo-storyboard.md` |
| `phase-62-end-to-end-demo-visit-script.md` | `docs/demo/phase-62-end-to-end-demo-visit-script.md` |
| `phase-62-screenshot-shot-list.md` | `docs/demo/phase-62-screenshot-shot-list.md` |
| `phase-62-video-clip-shot-list.md` | `docs/demo/phase-62-video-clip-shot-list.md` |
| `phase-62-demo-dry-run-report.md` | `docs/demo/phase-62-demo-dry-run-report.md` |
| `phase-62-controlled-buyer-demo-evidence-packet.md` | `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md` |
| `phase-62-local-build-delivery.md` | `docs/demo/phase-62-local-build-delivery.md` |

## Suggested reading order for the operator

1. `current-product-truth.md` — the single source of truth about
   what ChartNav is and is not. Read this first.
2. `phase-62-local-build-delivery.md` — how the iMac buyer-demo
   build is structured.
3. `phase-62-end-to-end-demo-visit-script.md` — the live narration
   script (~13 min 30 sec).
4. `phase-62-screenshot-shot-list.md` and
   `phase-62-video-clip-shot-list.md` — what to capture during the
   dry run.
5. `phase-62-demo-dry-run-report.md` — the checklist the operator
   ticks off during the dry run.
6. `phase-62-controlled-buyer-demo-evidence-packet.md` — what the
   evidence packet must contain on demo day.
7. `phase-61-controlled-buyer-demo-runbook.md`,
   `phase-61-buyer-demo-checklist.md`,
   `phase-61-buyer-qa-safe-answers.md`,
   `phase-61-demo-storyboard.md` — the Phase 61 operator package
   (still authoritative for narration tone + Q&A).
8. `release-evidence-checklist.md` — the artefacts the buyer
   receives after the demo.

## Refresh procedure (operator)

When a new phase ships and updates any of the above documents,
refresh this folder by re-running the bundle staging command from
`START_HERE.md`. The bundle is intentionally re-copied wholesale —
do not edit files in this `docs/` folder directly.
