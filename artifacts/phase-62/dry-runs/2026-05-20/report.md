# Phase 62 buyer-demo dry-run report — 2026-05-20

> **Status: PENDING MANUAL CAPTURE — NO-GO for live buyer demo.**
>
> This report is the dated scaffold the operator fills in on the
> iMac when the actual dry-run captures happen. It is created
> empty (with PENDING markers) because the sandbox that built this
> repo cannot record screen output. Until the operator captures
> the 30 screenshots + 12 video clips listed below and the safety
> scripts all pass on the iMac, **the buyer demo is NO-GO**.
>
> When the operator completes a dry run, they replace each PENDING
> marker with the actual outcome ("PASS · path-to-evidence" or
> "FAIL · failure summary"). The repo's source-safety scripts are
> already passing — that is what makes this NO-GO purely an
> evidence-collection gap, not a product-safety gap.

## 0. Pre-flight on the iMac

| Item | Status | Notes |
|---|---|---|
| `CHARTNAV_REPO_PATH` exported | PENDING | `export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"` |
| Repo on `main` and up to date | PENDING | `git checkout main && git pull origin main` |
| API venv exists at `apps/api/.venv/` | PENDING | Required for Alembic safety check (Phase 62A wrapper). |
| Web `node_modules` installed | PENDING | `pnpm install` (or `npm install`) in `apps/web/`. |
| `~/Desktop/ChartNav-Buyer-Demo-Build/` refreshed | PENDING | See `artifacts/phase-62/desktop-bundle/START_HERE.md`. |
| `.env` in the Desktop folder uses the bundle `.env.example` | PENDING | No real keys; deterministic stub provider. |

## 1. Source-safety scripts (must all PASS)

Run `bash ~/Desktop/ChartNav-Buyer-Demo-Build/run-safety-checks.sh`.

| Script | Status | Notes |
|---|---|---|
| `scripts/check_runtime_safety.py` | PENDING | Should print PASS. |
| `scripts/check_commercial_claims.sh` | PENDING | Should print PASS. |
| `scripts/check_website_claims.sh` | PENDING | Should print PASS. |
| `scripts/check_demo_claims.sh` | PENDING | Should print PASS. |
| `scripts/test_claim_policy_fixtures.sh` | PENDING | Should print PASS. |
| `scripts/check_alembic_safety.sh` | PENDING | Uses API venv interpreter (Phase 62A wrapper). |
| `git diff --check` | PENDING | No whitespace errors. |

If any script fails: **STOP. Do not proceed to capture.** Fix on the
repo branch, re-run all six, then resume.

## 2. Screenshots (30 total)

Source list: `docs/demo/phase-62-screenshot-shot-list.md` (also
available offline under `artifacts/phase-62/desktop-bundle/docs/`).

Save into `artifacts/phase-62/screenshots/` using the exact
filenames the shot list specifies.

| # | Filename | Status | Notes |
|---|---|---|---|
| 01 | `01_workspace_orientation.png` | PENDING MANUAL CAPTURE | |
| 02 | `02_clinical_tab_loaded.png` | PENDING MANUAL CAPTURE | |
| 03 | `03_vitals_demo_loaded.png` | PENDING MANUAL CAPTURE | |
| 04 | `04_vitals_bmi_live.png` | PENDING MANUAL CAPTURE | |
| 05 | `05_vitals_partial_bp_warning.png` | PENDING MANUAL CAPTURE | |
| 06 | `06_vitals_what_chartnav_did_not_do.png` | PENDING MANUAL CAPTURE | |
| 07 | `07_vitals_review_attestation.png` | PENDING MANUAL CAPTURE | |
| 08 | `08_vitals_signed_lock.png` | PENDING MANUAL CAPTURE | |
| 09 | `09_ophth_intake_va_iop.png` | PENDING MANUAL CAPTURE | |
| 10 | `10_ophth_signed_lock.png` | PENDING MANUAL CAPTURE | |
| 11 | `11_visitdraft_empty.png` | PENDING MANUAL CAPTURE | On-screen title is "Provider-Reviewed Ambient Documentation Assist"; narrate as VisitDraft Assist. |
| 12 | `12_visitdraft_transcript.png` | PENDING MANUAL CAPTURE | |
| 13 | `13_visitdraft_structured_facts.png` | PENDING MANUAL CAPTURE | |
| 14 | `14_visitdraft_draft_note.png` | PENDING MANUAL CAPTURE | |
| 15 | `15_visitdraft_safety_flags.png` | PENDING MANUAL CAPTURE | |
| 16 | `16_visitdraft_what_chartnav_did_not_do.png` | PENDING MANUAL CAPTURE | |
| 17 | `17_visitdraft_reviewed.png` | PENDING MANUAL CAPTURE | |
| 18 | `18_visitdraft_signed_lock.png` | PENDING MANUAL CAPTURE | |
| 19 | `19_fundus_empty.png` | PENDING MANUAL CAPTURE | No "What ChartNav did NOT do" card on Fundus today. |
| 20 | `20_fundus_findings.png` | PENDING MANUAL CAPTURE | |
| 21 | `21_fundus_svg.png` | PENDING MANUAL CAPTURE | |
| 22 | `22_fundus_legend.png` | PENDING MANUAL CAPTURE | |
| 23 | `23_fundus_warning.png` | PENDING MANUAL CAPTURE | |
| 24 | `24_fundus_attestation.png` | PENDING MANUAL CAPTURE | |
| 25 | `25_fundus_signed_lock.png` | PENDING MANUAL CAPTURE | |
| 26 | `26_warnings_recap.png` | PENDING MANUAL CAPTURE | |
| 27 | `27_audit_terminal.png` | PENDING MANUAL CAPTURE | |
| 28 | `28_safety_validator_pass.png` | PENDING MANUAL CAPTURE | |
| 29 | `29_closing_summary.png` | PENDING MANUAL CAPTURE | |
| 30 | `30_repo_clean_diff.png` | PENDING MANUAL CAPTURE | |

## 3. Video clips (12 total)

Source list: `docs/demo/phase-62-video-clip-shot-list.md`.

Save into `artifacts/phase-62/video-clips/` using the exact
filenames the shot list specifies.

| # | Filename | Status | Notes |
|---|---|---|---|
| 01 | `01_workspace_orientation.mov` | PENDING MANUAL CAPTURE | |
| 02 | `02_vitals_intake_to_warning.mov` | PENDING MANUAL CAPTURE | |
| 03 | `03_vitals_did_not_do_then_review.mov` | PENDING MANUAL CAPTURE | |
| 04 | `04_vitals_sign_lock.mov` | PENDING MANUAL CAPTURE | |
| 05 | `05_visitdraft_transcript_to_draft.mov` | PENDING MANUAL CAPTURE | On-screen title still reads "Provider-Reviewed Ambient Documentation Assist"; operator narrates as VisitDraft Assist. |
| 06 | `06_visitdraft_safety_did_not_do.mov` | PENDING MANUAL CAPTURE | |
| 07 | `07_visitdraft_sign_lock.mov` | PENDING MANUAL CAPTURE | |
| 08 | `08_fundus_findings_to_svg.mov` | PENDING MANUAL CAPTURE | |
| 09 | `09_fundus_missing_laterality_warning.mov` | PENDING MANUAL CAPTURE | |
| 10 | `10_fundus_sign_lock.mov` | PENDING MANUAL CAPTURE | |
| 11 | `11_audit_terminal_safety_validator.mov` | PENDING MANUAL CAPTURE | |
| 12 | `12_closing_recap.mov` | PENDING MANUAL CAPTURE | |

## 4. Stop-demo triggers (operator must confirm none fired)

- [ ] No real PHI on screen at any point.
- [ ] `CHARTNAV_ENV` was never `production` / `staging` / `controlled-pilot`.
- [ ] Runtime safety validator did not FAIL.
- [ ] No forbidden phrase appeared in narration or UI.
- [ ] No vendor / network error exposed a secret.
- [ ] No raw transcript / draft body / vitals value appeared in an
      audit log line visible during the dry run.
- [ ] No sign / finalize completed without the attestation checkbox
      being ticked.

## 5. Go / No-Go signal

| Gate | Status |
|---|---|
| Source-safety scripts all PASS | PENDING |
| All 30 screenshots captured | PENDING |
| All 12 video clips captured | PENDING |
| No stop-demo trigger fired | PENDING |

**Today's signal: NO-GO** (pending capture). Re-evaluate after the
operator completes the dry run and updates this report.

## 6. Operator notes (free-form)

_Fill in anything notable that happened during the dry run —
timing surprises, UI glitches, narration tweaks, anything Q&A
unexpectedly asked about._

---

**Next dated dry-run report:** when the operator reruns the dry
run on a future date, create a sibling folder
`artifacts/phase-62/dry-runs/YYYY-MM-DD/report.md` instead of
overwriting this one. Each dry run is its own dated artefact.
