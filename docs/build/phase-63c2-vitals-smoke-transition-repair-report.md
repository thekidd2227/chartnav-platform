# Phase 63C-2 — Vitals Smoke Transition Repair Report

> **Status: smoke gate fixed.** The Phase 63C functional smoke's
> last failing vitals gates now PASS because the smoke now drives
> the `draft → entered → reviewed → signed` transition correctly.
> No backend code changed; the state-machine rule was correct and
> the smoke was missing the intermediate `advance_to_entered`
> PATCH.

## 1. Failure reproduced

Per the brief, the operator's smoke run on `http://127.0.0.1:8765`
reported:

```
FAIL  vitals review
      ↳ vitals_review body:
      {"detail":{"error_code":"invalid_transition","reason":"review requires status=entered (current: 'draft')"}}

FAIL  vitals sign
      ↳ vitals_sign body:
      {"detail":{"error_code":"invalid_transition","reason":"sign requires status=reviewed (current: 'draft')"}}
```

All other gates PASSed:

- DB at Alembic head
- Required tables present
- API + frontend health
- Vite path guard
- Vitals create → 201
- VisitDraft full workflow
- Fundus full workflow
- manual_note string rejected (400)
- manual_note object accepted (201)

## 2. Root cause

The vitals state machine is `draft → entered → reviewed → signed`.
Each transition is enforced server-side
(`apps/api/app/api/vitals_workup.py` lines 679, 737). The canonical
sequence (proven by `apps/api/tests/test_vitals_workup.py:328-431`)
is:

| Step | Method + path | Body | Resulting status |
|---|---|---|---|
| Create | `POST /api/v1/encounters/{id}/vitals-workups` | vitals payload | `draft` |
| Enter | `PATCH /api/v1/vitals-workups/{id}` | `{"advance_to_entered": true}` | `entered` |
| Review | `POST /api/v1/vitals-workups/{id}/review` | `{}` | `reviewed` |
| Sign | `POST /api/v1/vitals-workups/{id}/sign` | `{"attested": true}` | `signed` |

The pre-Phase-63C-2 smoke (introduced in Phase 63C, strengthened in
Phase 63C-1) skipped the PATCH `advance_to_entered` step. It
created a draft workup, then tried to review it directly. The
backend correctly returned 409 `invalid_transition`.

**Verdict: smoke was wrong; backend was right.**

The brief explicitly forbade loosening backend state-machine rules
"unless the route contract is clearly wrong." It is not wrong —
the state machine is intentional and tested.

## 3. Whether backend or smoke was wrong

**Smoke was wrong.** No backend change.

## 4. Files changed

| Path | Why |
|---|---|
| `scripts/demo/phase63c_functional_smoke.sh` | Added the missing `PATCH /api/v1/vitals-workups/{id}` step with `{"advance_to_entered": true}` between create and review. New gate "vitals advance draft→entered" prints PASS/FAIL with detail. Review/sign FAIL messages now explain the prerequisite state. |
| `apps/api/tests/test_phase63c1_smoke_payloads.py` | New test `test_smoke_vitals_full_lifecycle_matches_state_machine`: pins the full create → enter → review → sign sequence, asserts review-without-enter returns 409, and asserts double-sign returns 409/422 (signed is terminal). |
| `docs/build/phase-63c2-vitals-smoke-transition-repair-report.md` | This report. |
| `scripts/check_demo_claims.sh` | FILES list extended for this report so the demo scanner covers it. |

**No backend product code, no route signature, no schema, no
migration, no claim policy change, no public website change, no
deploy.**

## 5. Tests added / updated

**New**:
- `tests/test_phase63c1_smoke_payloads.py::test_smoke_vitals_full_lifecycle_matches_state_machine`
  pins the full lifecycle including:
  - Create returns 201 in `draft`
  - Review-without-enter returns 409 `invalid_transition` (this is
    what bit the smoke; pinning ensures the rule stays in place)
  - PATCH `advance_to_entered:true` → 200 + `entered`
  - Review → 200 + `reviewed`
  - Sign `attested:true` → 200 + `signed`
  - Double-sign → 409/422 (terminal-state guard)

**Unchanged**:
- `apps/api/tests/test_vitals_workup.py` (74 tests) — already
  covered the transitions individually. No drift.
- All other backend + frontend tests.

## 6. Before / after smoke result

**Before Phase 63C-2** (operator's iMac, brief):

```
FAIL  vitals review     (409 invalid_transition: review requires entered)
FAIL  vitals sign       (409 invalid_transition: sign requires reviewed)
…
BUYER-DEMO FUNCTIONAL GO: NO
```

**After Phase 63C-2** (in-process repro, fresh seed):

```
PASS  POST /api/v1/encounters/1/vitals-workups -> 201 (id=1)
PASS  vitals advance draft→entered -> 200
PASS  vitals review -> 200
PASS  vitals sign -> 200
```

End-to-end:

```
create:  201  id 1   status=draft
enter:   200        status=entered
review:  200        status=reviewed
sign:    200        status=signed
```

Plus the new pinned regression test passes 6/6.

## 7. Buyer-demo GO / NO-GO

- **Repo-side: GO** — every safety gate passes; new regression
  test pins the full lifecycle including the negative
  invalid-transition case; demo claim scanner passes 34 files.
- **Operator-side: GO is expected** once the operator re-runs the
  smoke (`bash scripts/demo/phase63c_functional_smoke.sh` against
  their port 8765 stack). All 5 pre-63C-2 PASS gates remain green,
  plus the 3 vitals gates now flip green.

## 8. Exact next command for Jean-Max

After Phase 63C-2 merges:

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
```

Expected HEAD: `<merge sha> fix(demo): repair vitals transition in functional smoke (#NN)`.

Then re-run the smoke (no need for `--reset` — the fix is purely in
the smoke's request sequence; existing DB state should be fine):

```bash
cd "$CHARTNAV_REPO_PATH"
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase63c_functional_smoke.sh
```

Expected last line: `BUYER-DEMO FUNCTIONAL GO: YES`.

## Related documents

- `docs/build/phase-63c-demo-critical-functional-repair-report.md`
- `docs/build/phase-63c1-functional-smoke-500-repair-report.md`
- `docs/build/phase-63b-functional-demo-qa-audit.md` (on its own
  branch)
- `docs/build/current-product-truth.md`
