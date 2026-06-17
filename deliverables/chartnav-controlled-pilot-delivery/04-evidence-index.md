# Evidence Index

**Audience:** Practice security owner / CISO + ARCG ops lead
**Posture:** Fake data only. Every artifact below is generated
against the synthetic seed data.

## How this evidence is produced

ARCG runs four commands, in order, on a clean clone of `main`.
Each writes a **dated artifact bundle** under `artifacts/` in the
repo. The dated paths are then handed to the practice's CISO via
the `artifacts/manifest.txt` file in this delivery folder (the
operator fills it in after running the gates — see
`artifacts/README.md`).

```bash
# 1. Seed the local fake-data DB
bash scripts/demo/phase101_local_seed_sqlite.sh

# 2. Start the stack (API on 8765, web on 5173) — see 07-…

# 3. Run the release-side launch gate
bash scripts/release/phase100_controlled_pilot_launch_gate.sh

# 4. Capture the buyer-demo evidence bundle
PHASE101_SMOKE_RESET=0 \
PHASE63C_API_URL="http://127.0.0.1:8765" \
PHASE63C_WEB_URL="http://127.0.0.1:5173" \
bash scripts/demo/phase101_mcp_independent_demo_capture.sh
```

## Evidence catalogue

### 1. Release evidence gate (Phase 88)

| Artifact | Path | Contents |
|---|---|---|
| Summary | `artifacts/release-evidence/<ts>/summary.txt` | Per-check PASS/FAIL table; `OVERALL: PASS` on success. |
| Metadata | `artifacts/release-evidence/<ts>/metadata.txt` | Build SHA, branch, operator host, captured-at timestamp. |
| Backend (tiered pytest) | `01-backend.log` | Tier 1 security/RBAC/scoping, Tier 2 clinical surfaces, Tier 3 spine regression. |
| Frontend typecheck | `02-tsc.log` | `tsc --noEmit` clean. |
| Frontend test suite | `03-vitest.log` | Full vitest run. |
| Commercial claims scanner | `04-commercial-claims.log` | 0 fail / 0 warn required. |
| Website claims scanner | `05-website-claims.log` | 0 fail / 0 warn required. |
| Demo claims scanner | `06-demo-claims.log` | 0 positive-claim hits required. |
| Pilot readiness scanner | `07-pilot-readiness.log` | 0 fail required; warns logged. |
| Runtime safety scanner | `08-runtime-safety.log` | No unsafe runtime combinations. |
| `git diff --check` | `09-git-diff-check.log` | Whitespace clean. |
| Claim policy fixtures | `10-claim-policy-fixtures.log` | Fixture suite green. |

### 2. Phase 100 controlled-pilot launch gate

| Artifact | Path | Contents |
|---|---|---|
| Summary | `artifacts/phase-100-controlled-pilot-launch/<ts>/summary.txt` | Per-stage table; `OVERALL: PASS` on success. |
| Go / No-Go | `…/go-no-go.txt` | One-line release-side recommendation. |
| Delegated release evidence | `…/01-phase93-pilot-launch-gate.log` | Full Phase 93 (→ Phase 88) gate output. |
| Doc inventory (Phase 100 + Phase 93) | `…/02-doc-inventory-phase100.log`, `…/03-doc-inventory-phase93.log` | Required-doc presence checks. |
| Linked bundle | `…/phase-93-pilot-launch/` (symlink/copy) | The Phase 93 bundle this Phase 100 delegated to. |

### 3. Phase 101 buyer-demo evidence capture

| Artifact | Path | Contents |
|---|---|---|
| Summary | `artifacts/buyer-demo/<ts>/summary.txt` | Per-stage table; `OVERALL: PASS` + `BUYER-DEMO RECOMMENDATION` line. |
| No-real-PHI attestation | `…/no-real-phi-attestation.txt` | Carries the boundary statement into the buyer-facing bundle. |
| Missing-evidence ledger | `…/missing-evidence.txt` | SKIP / optional-FAIL rows the operator may fill manually. |
| Phase 100 delegate | `…/01-phase100-launch-gate.log` | Mirrors the Phase 100 gate run. |
| Phase 100 bundle pointer | `…/phase-100-controlled-pilot-launch/` (symlink/copy) | The Phase 100 bundle this capture delegated to. |
| Manual screenshots | `…/manual-screenshots/` | Empty by default; operator can drop manual captures here before handing the bundle to the practice. |

### 4. Phase 63C functional smoke (optional — embedded in the Phase 101 bundle when local stack is reachable)

| Artifact | Path | Contents |
|---|---|---|
| Smoke log | `artifacts/buyer-demo/<ts>/O1-phase63c-smoke.log` | 20-step happy-path smoke: clinician auth, vitals create/review/sign, visit-draft create/draft/review/finalize, fundus generate/review/sign, `manual_note` payload-shape enforcement. |
| Pass condition | inside the log | `Phase 63C functional smoke: 20 pass / 0 fail` + `BUYER-DEMO FUNCTIONAL GO: YES` |

If `PHASE63C_API_URL` / `PHASE63C_WEB_URL` are not set or do not
answer, this row is SKIPPED (recorded in `missing-evidence.txt`).

### 5. Documentation (in the delivery folder)

| File | Audience |
|---|---|
| `06-no-real-phi-attestation.md` | Practice CISO + ARCG legal |
| `05-go-no-go-form.md` | All signers |
| `08-known-limitations.md` | Practice + ARCG ops |
| `09-next-steps-for-practice.md` | Practice + ARCG commercial |

### 6. Optional screenshot / video evidence

Playwright capture (via the in-repo
`scripts/demo/phase63a_capture_demo_media.mjs`) is **optional**.
It runs only when:

- `apps/web/node_modules/@playwright/test/package.json` exists,
- the local stack is reachable, and
- Chromium is installed under `$HOME/.cache/ms-playwright`
  (`cd apps/web && npx playwright install --with-deps chromium`).

The Phase 101 capture script plumbs `PHASE63C_API_URL` /
`PHASE63C_WEB_URL` to the Playwright capture as `E2E_API_URL` /
`E2E_BASE_URL`, so the capture targets the workstation's actual
ports.

When chromium is absent, the row SKIPs cleanly with a verbatim
install hint — not a FAIL. Manual screenshots may be dropped
into `artifacts/buyer-demo/<ts>/manual-screenshots/` to fill the
gap.

## Missing-evidence handling

The Phase 101 capture script always writes `missing-evidence.txt`
with every optional row that SKIPped or FAILed. ARCG should hand
the practice's CISO **both** the `summary.txt` and the
`missing-evidence.txt` so the practice has an accurate ledger,
not a curated subset.

## What the practice's CISO can expect from this evidence

- A reproducible release SHA + per-check PASS/FAIL table.
- An explicit non-authorization statement for real PHI.
- A 20-step functional smoke trace against synthetic data when
  the local stack is reachable.
- A standardized missing-evidence ledger that lists, by name,
  every optional check that did not run on the operator's
  workstation.
- Zero raw credential leaks (the SAM-style scans + runtime
  safety validator enforce this).
