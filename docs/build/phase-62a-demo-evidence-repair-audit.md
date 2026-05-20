# Phase 62A — Demo Evidence Repair Audit

> Post-merge audit of Phase 62 (merged at `47820ed`). Phase 62 shipped
> source-safety clean — all six safety scripts pass, every claim
> scanner is green, every backend + frontend test still passes — but
> the buyer-demo evidence package is **not** operator-ready yet.
> Codex's audit identified six blockers; this audit confirms them and
> records the repair decision.

## 1. Current Desktop bundle contents (`artifacts/phase-62/desktop-bundle/`)

| File | Status |
|---|---|
| `README.md` | Present. References a `docs/` folder that does not exist. |
| `START_HERE.md` | Present. References a `docs/` folder that does not exist. |
| `RUN_LOCAL_DEMO.md` | Present. Tab name "Documentation / EMR-EHR" needs to read "Documentation / EMR/EHR" (with the slash). |
| `TEST_VISIT_SCRIPT.md` | Present. Tab name + VisitDraft label both need adjustment. |
| `TROUBLESHOOTING.md` | Present. Acceptable. |
| `start-api.sh` | Executable. Acceptable. |
| `start-web.sh` | Executable. Acceptable. |
| `run-safety-checks.sh` | Executable. **BROKEN** — calls bare `python3` for `check_runtime_safety.py` and bare `bash scripts/check_alembic_safety.sh`; the latter needs the API venv to run Alembic upgrade against the temp DB. |
| `run-demo-reset.sh` | Executable. Acceptable. |
| `.env.example` | Placeholder. Acceptable. |
| `docs/` | **MISSING.** README/START_HERE link to it; the operator cannot open the bundle docs offline. |

## 2. Missing `docs/` folder issue

Phase 62 staged the wrappers and top-level markdown but did not stage
read-only copies of the per-feature runbooks. README.md / START_HERE.md
say "Read-only copy of the Phase 62 + Phase 61 + Phase 61A buyer-demo
docs + the product-truth doc + the release-evidence checklist" but
no such folder was created. The operator cannot complete an offline
dry run from the bundle alone — they must keep jumping back into the
repo.

**Repair decision: Option A** — add
`artifacts/phase-62/desktop-bundle/docs/` with read-only copies of
the 12 docs the bundle references. Include a small `docs/README.md`
that names the canonical repo paths and says "if these diverge from
the repo, the repo wins."

## 3. Current screenshot / video status

| Folder | Files |
|---|---|
| `artifacts/phase-62/screenshots/` | `.gitkeep` only. |
| `artifacts/phase-62/video-clips/` | `.gitkeep` only. |
| `artifacts/phase-62/dry-runs/` | does not exist. |

**No actual screenshots captured. No actual videos captured. No dated
dry-run report exists.** The sandbox cannot capture display output,
so this is — and remains — operator manual work on the iMac. Phase
62A explicitly records the **PENDING MANUAL CAPTURE** state and
creates the dated dry-run scaffolding the operator fills in.

## 4. Current local Desktop folder status

`~/Desktop/ChartNav-Buyer-Demo-Build/` exists only if the operator
already ran the `cp -R` from the Phase 62 ship-notes. The sandbox has
no `~/Desktop`. Phase 62A delivers exact, paste-able commands the
operator runs to create (or refresh) the folder, with safety
guarantees:

- No real `.env` written.
- No real API key copied.
- No production config copied.
- No local DB file or PHI copied.

## 5. UI-label mismatch around VisitDraft

The Phase 62 visit script and shot lists describe the buyer-facing
label **"Provider-Reviewed VisitDraft Assist"** as if the UI already
says that. Live UI:

```
apps/web/src/features/ambient/AmbientDocumentationPanel.tsx:285:
    Provider-Reviewed Ambient Documentation Assist

apps/web/src/ClinicalTabbedWorkspace.tsx:909:
    Provider-Reviewed Ambient Documentation Assist
```

The current on-screen card label is still **"Provider-Reviewed Ambient
Documentation Assist"**. The Phase 62 brief introduced VisitDraft as a
**narration-only** rename; the UI rename is a separate phase. Phase 62A
docs must clarify this **everywhere** — operator narration says
"VisitDraft Assist" while the visible label still says "Ambient
Documentation Assist". This is not a product-code change.

Also: docs use the tab name `Documentation / EMR-EHR` (hyphen). The
SPA renders `Documentation / EMR/EHR` (slash between EMR and EHR).
Phase 62A corrects this.

## 6. `run-safety-checks.sh` venv / Alembic issue

The current wrapper:

```bash
python3 scripts/check_runtime_safety.py
…
bash scripts/check_alembic_safety.sh
```

`scripts/check_alembic_safety.sh` runs `python -m alembic …`. On a
fresh checkout where the API deps live in `apps/api/.venv/`, system
`python3` lacks `alembic` and `sqlalchemy`. The check fails with
`No module named alembic`.

**Repair:** prefer the API venv when it exists. Export `PYTHON` so
`check_alembic_safety.sh` (which honours `PYTHON`) uses the venv
interpreter. If the venv is missing, emit a clear warning and fall
back to `python3` (the operator's environment may have `alembic`
installed system-wide, but probably doesn't).

## 7. Repair decision

Phase 62A is **docs-only**. No product UI rename, no service change,
no migration. Specifically:

1. Stage a `docs/` folder under the desktop bundle (Option A above)
   with read-only copies of the 12 demo + product-truth + release
   docs. Add `docs/README.md` index.
2. Rewrite every "Provider-Reviewed VisitDraft Assist" claim in Phase
   62 demo docs + the desktop bundle to clarify it is a **narration
   label only**; the visible UI card today still reads "Provider-
   Reviewed Ambient Documentation Assist".
3. Fix the tab-name typo: `Documentation / EMR-EHR` → `Documentation
   / EMR/EHR`.
4. Make `run-safety-checks.sh` venv-aware. Export `PYTHON` to the API
   venv when available; warn-and-fall-back otherwise.
5. Create `artifacts/phase-62/dry-runs/2026-05-20/` with a
   pre-filled `report.md` that records the **PENDING MANUAL CAPTURE**
   state. The operator updates it when the captures happen.
6. Add a new `docs/demo/phase-62a-buyer-demo-go-no-go-status.md`
   summary so anyone joining mid-phase can see the buyer-demo state
   at a glance.
7. Provide explicit operator commands to create / refresh the
   `~/Desktop/ChartNav-Buyer-Demo-Build/` folder on the iMac (the
   sandbox cannot create files in the operator's actual Desktop).

## 8. Out of scope (explicitly)

- **No product UI rename.** The card label change is a separate
  phase. Phase 62A does not edit
  `apps/web/src/features/ambient/AmbientDocumentationPanel.tsx`
  or `apps/web/src/ClinicalTabbedWorkspace.tsx`.
- **No backend change.**
- **No migration.**
- **No real PHI.**
- **No production LLM activation.**
- **No public marketing-site update.**
- **No deploy.**

## 9. Validation plan

Re-run all 6 safety scripts + frontend tests + targeted backend
tests after the docs + scanner / venv-wrapper edits. The only new
change to `scripts/` is the demo-claims FILES list extension for
the new dry-run report + go/no-go status doc.

## Related documents

- `docs/build/phase-62-demo-dry-run-preflight-audit.md`
- `docs/demo/phase-62-end-to-end-demo-visit-script.md`
- `docs/demo/phase-62-controlled-buyer-demo-evidence-packet.md`
- `docs/demo/phase-62-local-build-delivery.md`
- `docs/build/phase-61a-demo-package-accuracy-repair.md`
