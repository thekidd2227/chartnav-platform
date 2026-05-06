# ChartNav Desktop Demo Delivery Package (Phase 17)

> Top-level contract for the desktop demo delivery package. This
> doc explains what `/Users/jean-maxcharles/Desktop/chartnav decks`
> contains, how it gets there, and how to use it.

---

## Purpose

A presenter on the operator's Mac should be able to:

1. Open `/Users/jean-maxcharles/Desktop/chartnav decks/`.
2. Find every commercial deck, every demo doc, every pilot doc,
   and every operator script in **one organized folder**.
3. Boot ChartNav locally with a single double-click.
4. Stop ChartNav locally with a single double-click.
5. Reset the demo environment with a single double-click.
6. Hand off the right doc to a buyer / investor / advisor /
   partner without going hunting in the repo.

The Desktop folder is **a generated review package**, not source.
The repo holds the source docs and the export scripts. The
Desktop folder is regenerated whenever the operator runs
`scripts/export_chartnav_decks_to_desktop.sh`.

---

## What's in the Desktop folder

```
/Users/jean-maxcharles/Desktop/chartnav decks/
├── README.md                          # Map of the folder
├── 00_START_HERE/                     # Entry doc + safety contract
├── 01_Decks/                          # 15 deck Markdown source files
├── 02_One_Pagers/                     # One-page sales deck
├── 03_Demo_Package/                   # Demo script, click path,
│                                      #   shot list (Phase 13/15)
├── 04_Pilot_Sales/                    # Phase 14 pilot packet
│                                      #   + pilot handoff checklist
├── 05_Objection_Handling/             # Buyer objections doc
├── 06_Pricing_Packaging/              # Pricing-notes doc
├── 07_Website_Proof/                  # Phase 16 landing-page docs
├── 08_Local_Demo_Launcher/            # START / STOP / RESET
│                                      #   .command files + guides
└── 09_Review_Checklists/              # Demo review + readiness
                                       #   checklists
```

Every file under the Desktop folder is a **copy** of the
corresponding repo source. When the repo source updates, the
operator re-runs the export script to refresh the Desktop folder.

---

## Source-of-truth contract

| Asset | Source-of-truth path in repo | Desktop destination |
|---|---|---|
| Deck Markdown source files (15) | `docs/decks/*.md` | `01_Decks/` |
| One-page sales | `docs/decks/chartnav-one-page-sales-deck.md` | `02_One_Pagers/` |
| Demo script (what to say) | `docs/demo/chartnav-clinical-workflow-demo-script.md` | `03_Demo_Package/` |
| Demo click path (what to click) | `docs/demo/chartnav-demo-click-path.md` | `03_Demo_Package/` |
| Demo video shot list | `docs/demo/chartnav-video-clip-shot-list.md` | `03_Demo_Package/` |
| Demo operator guide | `docs/demo/chartnav-demo-operator-guide.md` | `03_Demo_Package/` |
| Demo environment | `docs/demo/chartnav-demo-environment.md` | `03_Demo_Package/` |
| Pilot readiness checklist | `docs/pilot/chartnav-pilot-readiness-checklist.md` | `04_Pilot_Sales/` |
| Pilot deployment guide | `docs/pilot/chartnav-pilot-deployment-guide.md` | `04_Pilot_Sales/` |
| Admin onboarding | `docs/pilot/chartnav-admin-onboarding-checklist.md` | `04_Pilot_Sales/` |
| Security review packet | `docs/pilot/chartnav-security-review-packet.md` | `04_Pilot_Sales/` |
| Support runbook | `docs/pilot/chartnav-support-runbook.md` | `04_Pilot_Sales/` |
| Demo-to-pilot transition | `docs/pilot/chartnav-demo-to-pilot-transition-plan.md` | `04_Pilot_Sales/` |
| Known limitations | `docs/pilot/chartnav-known-limitations-and-non-goals.md` | `04_Pilot_Sales/` |
| Pilot success metrics | `docs/pilot/chartnav-pilot-success-metrics.md` | `04_Pilot_Sales/` |
| Pilot handoff checklist | `docs/commercial/pilot/chartnav-pilot-handoff-checklist.md` | `04_Pilot_Sales/` |
| Buyer objections | `docs/commercial/objections/chartnav-buyer-objection-handling.md` | `05_Objection_Handling/` |
| Pricing notes | `docs/commercial/pricing/chartnav-pricing-packaging-notes.md` | `06_Pricing_Packaging/` |
| Master kit | `docs/commercial/chartnav-deck-master-kit.md` | `00_START_HERE/` |
| Approved claims | `docs/commercial/chartnav-approved-claims-language.md` | `00_START_HERE/` |
| Readiness map | `docs/commercial/chartnav-commercial-readiness-map.md` | `00_START_HERE/` |
| Phase 16 contract | `docs/chartnav-website-proof-upgrade-conversion-layer.md` | `07_Website_Proof/` |
| Website shot list | `docs/website/chartnav-website-shot-list.md` | `07_Website_Proof/` |
| Local demo startup | `docs/commercial/demo-package/chartnav-local-demo-startup-guide.md` | `08_Local_Demo_Launcher/` |
| Local demo troubleshooting | `docs/commercial/demo-package/chartnav-local-demo-troubleshooting.md` | `08_Local_Demo_Launcher/` |
| Demo review checklist | `docs/commercial/demo-package/chartnav-demo-review-checklist.md` | `09_Review_Checklists/` |

---

## .command files

Three macOS-double-click scripts ship in `08_Local_Demo_Launcher/`:

### `START_CHARTNAV.command`

Opens a Terminal window, `cd`s into the repo at
`/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform`, runs
`make dev`, then opens the browser to
`http://localhost:5173/?demo=1`.

Fallback paths if `make dev` is not available are documented
inside the script.

### `STOP_CHARTNAV.command`

Sends SIGTERM to the local API and frontend dev servers if they
are bound to the standard ports (`:8000`, `:5173`). Does not
kill unrelated processes.

### `RESET_DEMO_DATA.command`

Wraps `bash scripts/reset_demo_state.sh` from the repo. The
underlying script refuses to run if `DATABASE_URL` points at
anything other than the local SQLite default.

All three .command files are marked executable by the export
script.

---

## What's NOT in the Desktop folder

- Backend code, migrations, schema, alembic versions.
- Frontend component source.
- Tests.
- The repo's `.git` folder.
- Binary screenshots, videos, or PDF deck exports.
- Real PHI.
- Auth credentials, secrets, or environment-variable values.
- `node_modules`, `.venv`, or any other build artifact.
- Anything from the parent `apps/api/` or `apps/web/src/`
  trees beyond what the script explicitly copies.

---

## Safety rules baked into the export

1. **The Desktop folder is never committed to the repo.** Every
   path under it is in `.gitignore`. The repo's source is the
   only source-of-truth.
2. **The export script does not embed real secrets.** It reads
   only from `docs/`, `scripts/`, and the brand assets — all of
   which are already public-safe.
3. **The reset script refuses non-local DB URLs.** The same
   guard that ships in the repo's `scripts/reset_demo_state.sh`
   gates the Desktop `RESET_DEMO_DATA.command`.
4. **No binary media** is generated by the export. Every file
   on the Desktop is a Markdown / shell / text file copy of a
   Markdown / shell / text file from the repo.

---

## Re-export workflow

Whenever any source doc updates in the repo:

```
bash scripts/export_chartnav_decks_to_desktop.sh
```

The script:
1. Recreates the Desktop folder structure (or uses the existing
   one).
2. Copies every doc listed in the Source-of-truth contract above
   to its destination subfolder.
3. Generates the README in the Desktop folder root.
4. Generates the three .command files.
5. Marks the .command files executable.
6. Prints a summary tree of what was exported.

The script is idempotent — running it twice produces the same
Desktop folder state.

---

## Phase 17 deliverable

Phase 17 ships:
- 15 deck Markdown source files (`docs/decks/`).
- 6 commercial support docs (`docs/commercial/`).
- 4 demo-package docs (`docs/commercial/demo-package/` plus this
  contract).
- 3 export / launcher scripts (`scripts/`).
- 1 vitest claims-tests file (`apps/web/src/test/`).
- This Phase 17 contract doc.
- A foundation-doc Phase 17 section.

The Desktop folder is the *consumed* output of Phase 17, not
part of the repo's source tree.
