# TROUBLESHOOTING

> Failure recovery for the local buyer-demo dry run. Halt the dry
> run if any P1 trigger fires (see § "Stop-demo triggers" at the
> end of this file).

## Wrapper-script failures

| Symptom | Cause | Fix |
|---|---|---|
| `start-api.sh` prints `CHARTNAV_REPO_PATH not set` | `$CHARTNAV_REPO_PATH` unset. | `export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"` (use your actual clone path). |
| Wrapper exits with `refusing to run when CHARTNAV_ENV=production/staging/controlled-pilot` | Demo cannot run on production env. | `unset CHARTNAV_ENV` or set to `local` / `dev` / `demo` / `test`. |
| Wrapper exits with `repo path not a chartnav-platform checkout` | `$CHARTNAV_REPO_PATH` points somewhere else. | Repoint to a clean clone. |

## API / backend startup

| Symptom | Cause | Fix |
|---|---|---|
| `port 8000 already in use` | A previous API instance is still running. | `lsof -i :8000`, then `kill -TERM <pid>`. Re-run `./start-api.sh`. |
| `ModuleNotFoundError: No module named app` | The venv is not active. | From the repo: `make install`; the Makefile uses `apps/api/.venv` consistently. |
| Alembic `multiple heads detected` | Two migration heads exist. | From the repo: `cd apps/api && python3 -m alembic heads`. If more than one head, you should not start a demo. |
| Alembic `Can't locate revision identified by 'X'` | The local DB is on a different revision than the repo. | `bash scripts/reset_demo_state.sh` then `cd apps/api && python3 -m alembic upgrade head` (use the venv). |
| API responds 500 to every request | Likely seed data missing. | `./run-demo-reset.sh`, then restart the API. |

## Frontend startup

| Symptom | Cause | Fix |
|---|---|---|
| `port 5173 already in use` | Previous frontend still running. | `lsof -i :5173`, `kill -TERM <pid>`, retry. |
| `Error: Cannot find module 'react'` | `node_modules` corrupted. | `cd apps/web && rm -rf node_modules && npm ci`. |
| Frontend shows a blank screen | API not running OR API on a non-default port. | Confirm `./start-api.sh` is running. Confirm the SPA's API URL config matches `:8000`. |

## Demo data state

| Symptom | Cause | Fix |
|---|---|---|
| Patient header shows the wrong name / not Morgan Lee | Seed data not loaded. | `./run-demo-reset.sh`. |
| Encounter `#1` not present | Same — fresh DB without seed. | Same fix. |
| Vitals workup count growing every rehearsal | Each dry run creates new rows. | `./run-demo-reset.sh` before every dry run. |
| Stale fundus charts from a previous rehearsal | Same. | Same fix. |

## Feature-by-feature

### Vitals workup

| Symptom | Cause | Fix |
|---|---|---|
| **Load fake demo vitals** does nothing | The textarea was clicked, not the button. | Click the button; the button is labeled exactly "Load fake demo vitals". |
| BMI tile shows `—` after loading sample | Either height or weight didn't populate. | Reload sample. Confirm `height_value` and `weight_value` are populated. |
| Sign button enables itself | The attestation checkbox is auto-ticked. | **P1 — UI regression.** Halt the dry run; escalate. The Phase 60 vitest test pins that Sign must stay disabled until the checkbox is ticked. |

### Provider-Reviewed VisitDraft Assist

| Symptom | Cause | Fix |
|---|---|---|
| Status timeline does not flip to `Ready for Review` after Generate | API error. | Open the network tab; look for a 4xx / 5xx on `/draft-ambient`. |
| `HTTP 422 fake_data_context_required` | Client mutated `fake_data_context: false`. | Bug in the client; the panel never does this in V1. Halt and inspect. |
| "What ChartNav did NOT do" card does not render | Generate did not succeed; the card needs the response. | Re-Generate. |

### Provider-Reviewed Fundus Drawing Assist

| Symptom | Cause | Fix |
|---|---|---|
| SVG preview is blank | Generate did not return drawing data. | Re-load the sample chip; click Generate again. |
| Operator narration accidentally claims a "What ChartNav did NOT do" card on fundus | The card does **not** exist on this surface (Phase 61A pinned this). | **Halt narration and restate** following the corrected wording in Phase 61A: fundus enforces the posture through warnings + provider review/sign + signed-lock + claim scanners. |
| Sign succeeds without attestation | UI regression. | **P1.** Halt and escalate. |

## Safety scanners and runtime validator

| Symptom | Cause | Fix |
|---|---|---|
| `check_runtime_safety.py` returns FAIL with `LLM_ENABLED_PRODUCTION` | `CHARTNAV_LLM_ENABLED=1` set in this shell. | `unset CHARTNAV_LLM_ENABLED`. |
| FAIL with `LLM_OPENAI_REAL_PHI` | `CHARTNAV_LLM_REAL_PHI_APPROVED=1`. | `unset CHARTNAV_LLM_REAL_PHI_APPROVED`. |
| FAIL with `FUNDUS_OPENAI_NOT_DEMO` / `AMBIENT_OPENAI_NOT_DEMO` | The opt-in env var is set + `CHARTNAV_ENV` is non-demo. | Either set `CHARTNAV_ENV` to `demo` / `local` / `test`, **or** unset `CHARTNAV_FUNDUS_DRAFTING_ASSIST` / `CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST`. |
| FAIL with `LLM_PROVIDER_BLOCKED` | `CHARTNAV_LLM_PROVIDER=anthropic` or `=ibm_watsonx`. | `unset CHARTNAV_LLM_PROVIDER` (defaults to `deterministic_stub`). |
| `check_commercial_claims.sh` returns FAIL | A forbidden phrase appears in a tracked source file. | Halt the dry run. Fix the wording at the source (do not weaken the scanner). Re-run. |
| `check_alembic_safety.sh` returns FAIL | Multiple Alembic heads or a SQLite-only migration pattern landed. | Halt. Resolve in a separate PR (this is not a dry-run-side fix). |

## Network / vendor

| Symptom | Cause | Fix |
|---|---|---|
| Browser network tab shows an outgoing call to `api.openai.com` | The OpenAI fake-data assist is enabled. **You did not authorise that for this demo.** | `unset CHARTNAV_AMBIENT_DOCUMENTATION_ASSIST` and `unset CHARTNAV_FUNDUS_DRAFTING_ASSIST`. Re-run the safety validator. Confirm `PASS` before resuming. |
| Browser dev-tools console exposes an `Authorization: Bearer sk-…` header on screen | Visible secret on camera. | **P1 — halt the dry run immediately**, stop the recording, redact the file, do not include it in the evidence packet. |

## Stop-demo triggers (any one → halt + reset)

- Real PHI on screen.
- `CHARTNAV_ENV` is `production` / `staging` / `controlled-pilot`.
- Runtime safety validator returns FAIL at any point.
- A forbidden phrase appears in narration **or** UI.
- A vendor / network error exposes a secret value.
- A raw transcript / draft body / vitals value appears in an audit
  log line visible during the dry run.
- Sign / finalize succeeds **without** the attestation checkbox
  having been ticked.
- Any "diagnosis confirmed" / "treatment recommended" /
  "order placed" / "billing code" / "ICD-10" / "CPT" /
  "referral submitted" / "patient message sent" text appears in
  the UI.

## After a halt

1. Stop the screen-share / recording.
2. Reset the local demo state: `./run-demo-reset.sh`.
3. Unset any session env vars set for the dry run.
4. Re-run `./run-safety-checks.sh` and confirm PASS on every line.
5. File the near-miss in the dry-run report
   (`docs/demo/phase-62-demo-dry-run-report.md` § 6).
6. Update the operator runbook / claim policy / scanners as a
   normal PR if the near-miss revealed a gap. Do **not** edit
   anything live.
