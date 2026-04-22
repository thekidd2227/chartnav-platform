# Phase 58 — Practice Backup, Restore, and Reinstall Recovery

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150e` (up from `e1f2a304150d`)

## Stack reality and honest model

ChartNav is a **browser-only web app** (Vite + React 18) backed by
FastAPI + SQL. There is no Electron, Tauri, or native shell. A
browser can only write files via a user-initiated download
(object-URL `<a download>`), and can only read files via a user-
selected `<input type="file">`. Phase 58 respects those limits
and does not fabricate filesystem capabilities the stack lacks.

Honest model for this pass:

- **Backup.** Admin calls
  `POST /admin/practice-backup/create`. Server assembles a
  canonical JSON bundle of this org's clinical data and returns it
  to the UI. The UI triggers a native Save-As download via an
  object URL. The server **never stores the bundle bytes** —
  only a metadata record (hash, size, counts, timestamp). If the
  server dies, the operator still has the file they downloaded.
- **Restore.** Admin uploads the saved bundle via
  `<input type="file">`. The UI reads the bytes, posts the JSON to
  the server, and the server validates + (after explicit
  confirmation) applies it into an **empty target org**. Merging
  into a live org is deliberately out of scope this pass — that
  needs collision semantics the schema does not yet express.
- **Recovery flow.** Create backup → delete/reinstall/rebootstrap
  → sign in to the fresh empty org → upload the backup → server
  validates and restores. No filesystem magic at any step.

## Data-inclusion contract

**Included** (bundle top-level keys):
- `organization` — the one org row, `settings_json` preserved verbatim
- `users` — users of that org
- `locations`, `patients`, `providers`
- `encounters`
- `encounter_inputs` (transcripts)
- `extracted_findings`
- `note_versions` — every Wave 3 + Wave 7 lifecycle/approval/
  attestation/fingerprint column

**Excluded** (`body.excluded` lists these explicitly for transparency):
- `security_audit_events` — volumetric; rebuilds naturally
- `note_evidence_events` — hash chain is tied to specific ids on
  the source install; transplanting breaks integrity
- `note_export_snapshots` — artifact_json bytes would bloat the
  bundle to unbounded size
- `evidence_chain_seals` — tied to the source chain
- `user_sessions` — ephemeral; users re-authenticate
- process secrets (HMAC keys, JWT keys) — these live in env

The exclusions are **safety-preserving**: a restored bundle
does not fraudulently claim a chain of evidence events it never
witnessed. Signed bundles (Phase 55/56) remain independently
verifiable off-server; post-restore, new evidence rebuilds from
future governance events.

## Safety contract (enforced by the route layer)

| Concern | Enforcement |
|---|---|
| who can create | `role=admin` (403 `role_admin_required` otherwise) |
| who can restore | `caller_is_security_admin` (403 `security_admin_required`) |
| destructive confirmation | `confirm_destructive=true` required unless `dry_run` (409 `restore_requires_confirmation`) |
| wrong-org protection | `source_organization_id` in bundle must equal caller's org (404 `backup_org_mismatch`) |
| wrong-practice protection | the bundle body hash validates end-to-end; mismatch → 400 `backup_hash_mismatch` |
| schema/version compat | `bundle_version` must equal this build's value (400 `backup_incompatible_bundle_version`) |
| non-empty-target | target org must be empty (no encounters/patients/notes) or 409 `restore_target_not_empty` |
| mode | only `empty_target_only` today; `merge_preserve_existing` returns 400 `restore_mode_unsupported` |
| default safety | `dry_run` defaults to `true`; a bare POST without flags never destroys anything |

Every backup and restore emits an audit event
(`practice_backup_created`, `practice_backup_downloaded`,
`practice_backup_restore_dry_run`,
`practice_backup_restore_applied`) and a
`practice_backup_records` history row.

## API surface added

| Method | Path | Guard | Purpose |
|---|---|---|---|
| POST | `/admin/practice-backup/create` | `admin` | assemble bundle; return JSON + hash |
| GET | `/admin/practice-backup/download` | `admin` | same bundle as attachment (Save-As) |
| GET | `/admin/practice-backup/history` | `admin` | metadata history |
| POST | `/admin/practice-backup/validate` | `admin` | verdict without writing |
| POST | `/admin/practice-backup/restore` | `security_admin` | `{bundle, mode, dry_run, confirm_destructive}` |

## Client / API type additions

`apps/web/src/api.ts`:

- `PracticeBackupBundle`, `PracticeBackupCounts`,
  `PracticeBackupCreateResponse`, `PracticeBackupHistoryRow`,
  `PracticeBackupHistoryResponse`,
  `PracticeBackupValidationVerdict`,
  `PracticeBackupRestoreResponse`.
- Helpers: `createPracticeBackup`, `getPracticeBackupHistory`,
  `validatePracticeBackup`, `restorePracticeBackup`,
  `downloadPracticeBackupBundle` (browser blob + object-URL
  anchor download trick).

## UI

New `BackupPane` component mounted as an `admin-tab-backup` tab
in `AdminPanel`. Three small sections — Create, Restore, History.
Not a redesign; no operations redesigned; only minimum surfaces
needed for an operator to drive the recovery flow.

Restore-side defaults are safety-first:
- `dry_run` checkbox is checked by default.
- `confirm_destructive` checkbox is unchecked by default AND
  disabled while dry_run is checked.
- Apply button is disabled unless either `dry_run=true` or both
  toggles are explicit.

## Tests

New file: `apps/api/tests/test_practice_backup.py` — 20 tests:

- **Create + download (6):** bundle has envelope+hash+counts;
  round-trips validate; deterministic for same state; role guard;
  records history; attachment headers correct.
- **Validation failure (4):** malformed → `malformed_bundle`;
  wrong bundle_version → `backup_incompatible_bundle_version`;
  tampered body → `backup_hash_mismatch`; cross-org →
  `backup_org_mismatch`.
- **Restore (7):** refuses non-empty target; refuses merge mode;
  refuses cross-org; dry-run doesn't write; requires
  `confirm_destructive`; full round-trip after simulated wipe
  (and re-issued backup hash matches pre-wipe); role guard
  requires security-admin.
- **History + regression (3):** history surfaces both event
  types; cross-org isolation; pilot flow still green.

**Deterministic restore**: `test_restore_round_trip_after_wipe`
asserts the strongest available correctness contract — the hash
of a backup re-issued AFTER a full restore equals the hash of
the backup issued BEFORE the wipe. This proves the restore path
produces byte-identical canonical state.

## Validation

- `alembic upgrade head` from empty: clean; head `e1f2a304150e`.
- `npm run typecheck`: clean.
- `npm test -- --run` (vitest): **194 passed / 9 files**.
- `npm run build`: clean (62 KB CSS / 360 KB JS).
- Backend `pytest -q`: see next run — scheduled for the final
  commit.

## Remaining scope (documented honestly)

- **Merge restore mode.** Needs collision semantics: what happens
  on duplicate patient_identifier, duplicate encounter_id, etc.
  Intentional follow-up.
- **Bundle compression + signing.** Bundles could be gzipped and
  HMAC-signed using the Phase 57 keyring so the downloaded file
  carries its own tamper-evident signature. The framework is in
  place; this pass ships the data envelope without the optional
  signature layer.
- **Server-side bundle staging.** Today the download is live —
  large orgs (thousands of encounters) will see a long request.
  A staged build-to-disk-on-server + poll + download pattern is
  a reasonable scale follow-up.
- **Scheduled / automated backups.** Out of scope. This pass is
  admin-initiated only.
- **Restore progress / chunked upload.** Single-shot POST today;
  a streamed JSON approach could help very large orgs.
- **Evidence chain rebuild on restore.** The chain intentionally
  does not transplant. If an operator wants seamless continuity,
  a post-restore "seal + resume" flow is a natural follow-up.
- **Cross-version migrations.** Today we require exact
  `bundle_version` equality. When the format evolves, a forward
  migrator (upgrade v1→v2 bundles) is a reasonable follow-up.

## No conflict with earlier work

Phase 58 adds endpoints and a UI tab but does not change:

- the canonical lifecycle model (Phase 54)
- evidence chain writes (Phase 55)
- external evidence sink or signed bundles (Phase 56)
- keyring rotation, signed seals, sink retry, snapshot retention
  (Phase 57)

The evidence-related tables are deliberately excluded from the
bundle so a restore cannot fraudulently carry a chain of events
the target install did not witness.
