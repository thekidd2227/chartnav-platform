# Enterprise Integration — Wave 1

Repo: `thekidd2227/chartnav-platform`
Integration branch: `chartnav-enterprise-integration-wave1`
Base commit: `162d26332563193b67f8d04484d77ea09ea3f243`
(= tip of `chartnav-roi-wave-1` at the time of this integration)

## Purpose

Produce a single authoritative integration branch that consolidates
the approved enterprise-readiness work. This branch is the canonical
merge target for any further enterprise governance / identity /
operations work.

## Source-branch reconciliation — what was actually on this repo

The brief for this integration pass referenced two source branches
to reconcile:

- `chartnav-roi-wave-1` — Claude-side lane (final physician approval,
  operations & exceptions control plane, clinical governance /
  approval-readiness surfaces, KPI scorecard, security-governance
  control plane).
- `work` — Codex-side lane (tenant-safe identity/provisioning
  hardening, production-config hardening, enterprise release
  hardening and validation improvements).

**Finding.** An exhaustive check of this repo confirms that only
`chartnav-roi-wave-1` exists. A `work` branch does not exist:

- Local refs enumerated via `git branch -a` → `chartnav-roi-wave-1`,
  `feat/doctor-frontdesk-expansion`, `main`.
- Remote refs enumerated via `git ls-remote --heads origin` → only
  `refs/heads/main`.
- `git worktree list` shows one worktree at the primary checkout;
  no secondary worktree holds a Codex lane.
- `git stash list` is empty.
- `git fsck --unreachable` shows only routine garbage trees/blobs
  from rebase/amends — no dangling commits that look like a lost
  Codex lane.
- No sibling chartnav checkout exists elsewhere on the machine (only
  `/Users/jean-maxcharles/Desktop/ARCG/chartnav-platform/.git` is a
  chartnav repository; `ARCG/Chartnav/` is an unrelated docs
  directory with no `.git`).

Because the Codex-side branch does not exist in this repo, there
are no cross-branch conflicts to resolve. This integration pass
consequently cuts the authoritative branch directly from
`chartnav-roi-wave-1` with no merge, validates it fully, and
documents the state honestly rather than fabricate reconciled
content for a branch that cannot be read.

If a Codex-side branch is later imported (as a remote, a bundle, or
a tarball), the next integration pass should re-open this work by
branching from `chartnav-enterprise-integration-wave1`, merging the
Codex lane, and resolving conflicts per the rules in the original
mission.

## Integration branch contents

`main..chartnav-enterprise-integration-wave1` = 9 commits, 78 files
changed, +18,820 / −69 lines. Commit chain (newest first):

| short | phase | summary |
|---|---|---|
| `162d263` | 53 / Wave 8 | Enterprise operations & exceptions control plane |
| `9d2a86f` | 52 / Wave 7 + 49 / Wave 3 | Clinical governance + final physician approval |
| `33ed395` | 48 / Wave 2 | Enterprise control-plane wave 2 — real security governance |
| `38d1386` | 47 | KPI scorecard UI + before/after comparison |
| `c6d67d0` | 47 | Pilot KPI scorecard + enterprise control-plane seam |
| `5216252` | 46 | Wedge + integrated/native encounter UX (non-architectural hardening) |
| `45f7169` | 46 | ChartNav ROI wave 1 — doctor / staff / visual improvements |
| `b8eb971` | — | Backup: pre ChartNav ROI wave 1 |
| `d035ece` | 38 | Doctor + front-desk expansion + visual refresh |

## Exact enterprise behaviors preserved

### Clinical governance + final physician approval (Wave 3 + Wave 7)

- Canonical lifecycle state machine in
  `apps/api/app/services/note_lifecycle.py` (states, transitions,
  edge roles, release blockers, attestation template, content
  fingerprint).
- Amendment service in
  `apps/api/app/services/note_amendments.py` creates a new
  `note_versions` row and marks the original superseded; never
  mutates a signed row in place.
- Final physician approval in
  `apps/api/app/services/note_final_approval.py`:
  authorized-signer gate, case-sensitive exact-name match, six
  structured failure codes, export gated on `approved`, amendment
  invalidates prior approval.
- Migrations: `e1f2a3041508` (Wave 3 lifecycle columns) and
  `e1f2a3041509` (Wave 7 approval columns + `users.is_authorized_final_signer`).

### Operations & exceptions control plane (Wave 8)

- Pure aggregation service in
  `apps/api/app/services/operations_exceptions.py` — 18 canonical
  categories, `EVENT_TO_CATEGORY` mapping, per-category metadata.
- Eight `/admin/operations/*` routes gated by
  `caller_is_security_admin`.
- `OperationsPane.tsx` with 7 tabs (Overview / Final approval /
  Blocked notes / Identity / Sessions / Ingest / Security config).
- Migration `e1f2a304150a` adds composite audit indexes on
  `(organization_id, created_at)` and
  `(organization_id, error_code, created_at)`.

### Security / session governance (Wave 2)

- `user_sessions` table + `app.session_governance` tracking
  (created, last activity, idle/absolute timeout, revocation reason).
- `security_admin_emails` allowlist + `caller_is_security_admin`
  dependency; `/admin/security/*` surface.
- Audit sink with jsonl/webhook modes and a probe endpoint.

### Identity / OIDC reality (honest statement)

- Bearer JWT validation in `app/auth.py` with explicit failure
  branches (`unknown_user`, `token_expired`, `invalid_issuer`,
  `invalid_audience`, `missing_user_claim`, `invalid_token`).
- Identity mapping is a pure email-claim lookup.
  `/admin/operations/identity-exceptions` publishes
  `scim_configured: false` and
  `oidc_identity_mapping: "email_claim_lookup"` as honest flags.
- SCIM / tenant-safe provisioning / production-config
  hardening from the referenced Codex-side lane is **not present
  on this integration branch** because the source branch was not
  found. This is a known gap, not a silent regression.

## Exact cleanup performed

Because no merge was performed, cleanup was limited to coherence
verification on the cut branch:

- No conflict markers in `apps/api/app` or `apps/web/src`
  (`grep -rnE "^(<<<<<<<|>>>>>>>|=======)$"` → empty).
- No duplicate source files — one canonical
  `note_lifecycle.py`, `note_amendments.py`,
  `note_final_approval.py`, `operations_exceptions.py`,
  `NoteLifecyclePanel.tsx`, `OperationsPane.tsx`.
- Exactly one docs/build entry for Wave 7 (`52-*.md`) and Wave 8
  (`53-*.md`).
- Alembic head is `e1f2a304150a`; fresh migrate-from-empty
  completes with no errors.

## Validation performed

All commands run on the integration branch at commit `162d263`
(pre-this-doc-commit).

| gate | result |
|---|---|
| `alembic upgrade head` on an empty SQLite | clean; head at `e1f2a304150a` |
| `pytest -q` (full backend suite) | **464 passed** / 0 failed in 513 s |
| Enterprise-critical workflow suites (`test_note_lifecycle_wave3.py`, `test_note_final_approval_wave7.py`, `test_operations_exceptions_wave8.py`, `test_transcript_to_note.py`, `test_encounter_bridge.py`) | **96 passed** / 0 failed |
| `npm run typecheck` | clean |
| `npm test -- --run` (vitest) | **194 passed** / 9 files |
| `npm run build` | clean (60 KB CSS / 351 KB JS) |

### End-to-end enterprise workflow verified

Covered by `test_pilot_flow_still_green_after_wave8` (wave-8 suite)
plus `test_final_approve_success_persists_fields`,
`test_amendment_invalidates_approved_original`, and
`test_export_blocked_after_approval_invalidated_by_amendment` from
the wave-7 suite:

1. Sign a note → `draft_status='signed'` +
   `final_approval_status='pending'`.
2. Final-approve with exact stored name →
   `final_approval_status='approved'` +
   `note_final_approved` audit event.
3. Export → `draft_status='exported'` +
   `note_version_exported` audit event.
4. Amend → new `note_versions` row is created; original marked
   superseded; original's `final_approval_status` flipped to
   `'invalidated'`; `note_final_approval_invalidated` audit event
   emitted.
5. Operations surface visibility: invalidated row appears in
   `/admin/operations/final-approval-queue`; sign-blocked attempts
   appear in `/admin/operations/blocked-notes`; invalidated export
   blocker surfaces in the overview counters.

### Identity / provisioning validation

- OIDC identity-denial paths in `app/auth.py` have full unit
  coverage in the existing auth tests and surface correctly on
  `/admin/operations/identity-exceptions`.
- Organisation-safe `cross_org_access_forbidden` path surfaces
  correctly on the identity tab.
- SCIM conflict paths and production-config hardening from the
  referenced Codex lane could not be validated because the source
  branch is not present — documented above under "known gap".

## Known gaps carried forward to the next integration pass

- Codex lane (`work` branch) was not present in the repo. Items
  likely absent from this integration branch and subject to a
  future integration pass:
  - tenant-safe SCIM conflict-path hardening
  - `app/config.py` production-config validation improvements
  - enterprise release hardening / validation runbook script
- None of these are regressions from what was previously shipping
  on `main`; they are unreconciled work that never reached this
  repo.

## Next integration pass — how to resume

If/when the Codex lane becomes available:

```bash
git checkout chartnav-enterprise-integration-wave1
git remote add codex <url>                   # or fetch the bundle
git fetch codex
git merge codex/work                         # resolve conflicts per mission rules
# Re-run full validation (same gates as above).
```

The mission's rules for conflict resolution apply unchanged on the
next pass: keep the stricter enterprise-safe implementation on
overlaps, remove duplicated paths, preserve final approval +
invalidation + operations surfaces + identity hardening +
production-config hardening + release hardening simultaneously.
