# Phase 63C-1 — Functional Smoke 500 Repair Report

> **Headline:** the operator's reported 500s on the four POSTs are
> **not reproducible** against a freshly migrated + seeded DB. I ran
> the smoke's exact JSON payloads against the actual route schemas
> (in-process via FastAPI `TestClient`) on a clean seed and on a
> deliberately-contaminated seed (Maria + QA encounters + 50 audit
> rows). All five gates returned the expected `201` / `400`. The
> route handlers, the request schemas, and the smoke's payloads are
> correct.
>
> The operator's 500s therefore come from environment-specific
> accumulated state on their iMac — most likely a `users` row,
> `security_audit_events` schema mismatch, or seed step that
> silently failed on a dup-key collision. I cannot see that state
> from the sandbox.
>
> Phase 63C-1 ships the things that **let the operator surface and
> recover from that state on their own machine**:
>
> 1. **Enhanced smoke** with full failure-body printing, DB
>    introspection of the seeded clinician + Morgan encounter +
>    required tables before any POST, and an opt-in `--reset` flag
>    that runs `scripts/reset_demo_state.sh` first.
> 2. **Regression test** (`tests/test_phase63c1_smoke_payloads.py`)
>    that pins the five smoke payloads against the live route
>    schemas; any future schema rename will break this test before
>    it breaks the smoke.
> 3. **No backend code change.** The brief explicitly forbade
>    loosening backend validation. I confirmed the validation does
>    not need loosening — the routes accept the smoke's payloads.

## 1. Exact 500s reproduced

| Endpoint | Smoke result on iMac (per brief) | In-process repro result (fresh seed) | In-process repro result (contaminated seed) |
|---|---|---|---|
| `POST /api/v1/encounters/1/vitals-workups` | 500 | **201** | **201** |
| `POST /patients/1/scribe-sessions` | 500 | **201** | **201** |
| `POST /api/v1/encounters/1/fundus-charts/generate` | 500 | **201** | **201** |
| `POST /encounters/1/events` (manual_note string) | 400 ✓ | **400** ✓ | **400** ✓ |
| `POST /encounters/1/events` (manual_note object) | 500 | **201** | **201** |

Contaminated DB used for the second repro column was deliberately
poisoned with the same surface pattern the Phase 63B audit
captured: a `Maria charlie` patient, a `Maria Charlie` encounter on
patient 1, two QA encounters (`QA63B-62081` / `QA63B-68784`), and
50 synthetic rows in `security_audit_events`. All five routes
still returned the expected 201/400.

## 2. Root cause for each endpoint

For all four reported 500s: **route handler not at fault**. The
backend code path, the Pydantic request schema, the SQL inserts,
and the audit-log insert all work as expected against the smoke's
exact payloads. The 500s come from operator-environment state I
cannot model:

- **Most likely**: the operator's `users` row for
  `clin@chartnav.local` has a stale `organization_id`, `role`, or
  `is_active` value left over from a pre-Phase-63C session,
  causing `require_caller` or `_require_write_role` to raise an
  unexpected exception inside `_audit`. Or the user row was
  deleted / soft-deleted and only the seed's `INSERT OR IGNORE`
  would re-add it.
- **Also possible**: `security_audit_events` schema mismatch
  between the operator's DB (created by an older migration chain)
  and what the audit module writes. The 500 would be on the audit
  insert, which happens *after* the workup/session/chart row is
  created — so the data would be inserted but the response would
  500.
- **Less likely**: orphan FK rows from an interrupted earlier
  session that violate a foreign key constraint somewhere in the
  insert.

All three are surfaced and recovered from by the new pre-flight
introspection (§ 4) + the `--reset` flag (§ 5).

## 3. Files changed

| Path | Why |
|---|---|
| `scripts/demo/phase63c_functional_smoke.sh` | Enhanced: pre-flight DB introspection (seeded clinician + Morgan + required tables), full failure-body dumps to stderr, `--reset` flag wiring, expanded recovery hints. |
| `apps/api/tests/test_phase63c1_smoke_payloads.py` | New: 5 tests pin the smoke's exact payloads against the live route schemas against a freshly seeded test DB. |
| `docs/build/phase-63c1-functional-smoke-500-repair-report.md` | This report. |
| `scripts/check_demo_claims.sh` | FILES list extended for this report so the demo claims scanner covers it (no new claims; 0 hits). |

**No backend product code changed.** No route signature, schema,
service module, or migration changed. No claim policy changed. No
public website changed. No deploy. No real PHI. No production LLM.

## 4. Pre-flight DB introspection (new)

The smoke now prints, before any POST:

- `clinician` row: `(id, email, role, organization_id, is_active)`
  for `clin@chartnav.local`.
- `encounter 1` row: `(id, organization_id, patient_identifier,
  patient_name, status)`.
- Total encounter count (to surface accumulated drift).

And asserts:

- Clinician row exists.
- Email matches.
- Role is one of `clinician` / `admin` / `technician`.
- `is_active` is truthy.
- `organization_id == 1` (Morgan is in org 1; cross-org would 404).
- Encounter 1 is `PT-1001` in org 1 (Morgan Lee).

Any of these failing prints a specific recovery hint pointing at
`bash scripts/reset_demo_state.sh` or the bundle's `./start-api.sh`
auto-seed.

## 5. `--reset` flag (new)

```bash
bash scripts/demo/phase63c_functional_smoke.sh --reset
```

Runs `scripts/reset_demo_state.sh` first (which is already safety-
checked: refuses to run if `DATABASE_URL` points anywhere other
than local SQLite). That wipes the dev DB to a clean Morgan-only
seed state. Then continues with the standard smoke.

Default behaviour (no flag) is unchanged — non-destructive,
introspect-and-report.

## 6. Workflows verified

Static / regression coverage:

- `apps/api/tests/test_phase63c1_smoke_payloads.py` — 5/5 PASS.
- `apps/api/tests/test_vitals_workup.py` — 37 cases unchanged, PASS.
- `apps/api/tests/test_fundus_charts.py` — 49 cases unchanged, PASS.
- `apps/api/tests/test_ambient_documentation.py` — 27 cases unchanged, PASS.
- `apps/api/tests/test_runtime_safety.py` — 6 cases unchanged, PASS.
- Backend manual_note rejection (`test_admin.py`,
  `test_invitations.py`) — unchanged, PASS.

End-to-end smoke (live stack):

- **Operator-side only.** The build sandbox has no live API/web
  stack. The operator runs the enhanced smoke; on FAIL it now
  prints the actual response body + a recovery suggestion.

## 7. Tests added / updated

**New**: `apps/api/tests/test_phase63c1_smoke_payloads.py`
(5 tests pinning all five smoke payloads).

**Unchanged**: all other backend + frontend tests. No widening or
narrowing of any existing test.

## 8. Smoke result

| Run | Result |
|---|---|
| Sandbox in-process repro (fresh seed, 5 routes) | 4× `201` + 1× `400` = **PASS** |
| Sandbox in-process repro (contaminated DB) | 4× `201` + 1× `400` = **PASS** |
| Smoke against operator's iMac stack (before 63C-1) | per brief: 4× `500` + 1× `400` = **NO-GO** |
| Smoke against operator's iMac stack (after 63C-1) | TBD by operator — but the smoke now surfaces *why* with introspection + failure-body output, and `--reset` provides a one-line recovery. |

## 9. Buyer-demo GO / NO-GO

- **Repo-side: GO** — every safety gate passes on this branch; new
  regression tests PASS; smoke is `bash -n` clean.
- **Operator-side: undetermined.** The operator runs the enhanced
  smoke. If it still fails, the printed failure body + the seeded-
  state report will name the cause and the operator can either
  paste the body back here for diagnosis or rerun with `--reset`
  for a clean slate.

## 10. Remaining risks

- **I cannot reproduce the operator's 500s.** This is honest. The
  routes work in every reproduction I've run. Until the operator
  pastes back a real failure body, I cannot say definitively which
  table or column is responsible. The `--reset` flag is the
  pragmatic backstop.
- **Identity propagation by localStorage.** Phase 63C's feature
  clients read identity from localStorage; this is fine for the
  demo. If the operator's frontend somehow clears the key, the
  feature clients would omit the header and the backend would 401
  — but the smoke uses curl, not the frontend, so this can't
  affect smoke results.
- **The `--reset` flag is destructive within the local SQLite DB.**
  It only ever touches `apps/api/chartnav.db` (the reset script
  refuses any other `DATABASE_URL`), but it does wipe data. The
  operator opt-in is explicit (`--reset` is not the default).

## 11. Exact next command for Jean-Max

After Phase 63C-1 merges:

```bash
export CHARTNAV_REPO_PATH="$HOME/Desktop/ARCG/chartnav-platform"
cd "$CHARTNAV_REPO_PATH"
git checkout main
git pull origin main
git log --oneline -1
```

Expected HEAD: `<merge sha> fix(demo): repair phase 63c functional smoke 500s (#NN)`.

Refresh the bundle (picks up nothing new for this PR — the bundle
wrappers already auto-migrate per Phase 63C):

```bash
rm -rf "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
cp -R "$CHARTNAV_REPO_PATH/artifacts/phase-62/desktop-bundle/" \
      "$HOME/Desktop/ChartNav-Buyer-Demo-Build"
```

**Run the enhanced smoke with the clean-slate flag** — this is the
fastest path to `BUYER-DEMO FUNCTIONAL GO: YES`:

```bash
cd "$CHARTNAV_REPO_PATH"
bash scripts/demo/phase63c_functional_smoke.sh --reset
```

Expected last line: `BUYER-DEMO FUNCTIONAL GO: YES`.

If anything still FAILs, the smoke now prints the actual failure
body inline. Paste those `↳ <name> body:` lines into the chat and
I'll diagnose the specific operator-environment cause.

## Related documents

- `docs/build/phase-63c-demo-critical-functional-repair-report.md`
- `docs/build/phase-63b-functional-demo-qa-audit.md` (on its own
  branch; the source of truth for the 14 defects)
- `docs/build/phase-63a-automated-demo-media-capture-report.md`
- `docs/build/current-product-truth.md`
