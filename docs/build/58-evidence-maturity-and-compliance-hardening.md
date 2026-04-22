# Phase 57 — Evidence Maturity and Compliance Hardening

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150d` (up from `e1f2a304150c`)

## Scope

Closes the four remaining gaps documented at the end of Phase 56:
HMAC key rotation, signed seal records, sink retry loop, snapshot
retention. Keeps the in-app evidence chain authoritative; every new
operator surface is read-only or narrowly scoped.

## Key rotation contract

Process env supports a keyring:

```
CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS={"k1":"secret-one","k2":"secret-two"}
```

The legacy single-key env `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY`
remains honoured and is auto-aliased under key_id `"default"` in
the keyring, so pre-rotation deploys keep working unchanged.

Per-org `evidence_signing_key_id` names the ACTIVE signing key
for new bundles. Every key in the ring is a VALID verification
key; old bundles remain verifiable as long as the key they were
signed with stays in the ring.

**Rotation flow** (operator contract, now enforced):

1. Add the new key to `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEYS`
   alongside the old key. Reload the service.
2. Update the org's `evidence_signing_key_id` to the new id.
3. Old bundles continue to verify because the old key is still
   in the ring.
4. When no more bundles require the old key, drop it from the
   keyring env on next deploy.

**Inconsistent configuration** — if an org enables signing but the
named active key is not in the process ring, bundle issuance now
returns `503 evidence_signing_key_unknown` with the list of
available ids. If the ring is entirely empty, returns
`503 evidence_signing_unconfigured`. No silent degrade to unsigned.

**Verification flow** — `verify_signature()` reads `signature.key_id`
from the bundle (not the org's current active key) and looks that
id up in the process ring. Bundles signed by a key no longer in
the ring surface `signing_key_not_in_keyring` with the list of
available ids so an operator can diagnose whether the key was
dropped prematurely.

## Seal verification contract

`POST /admin/operations/evidence-chain/seal` now stamps three
additional columns on every new seal row:

- `seal_hash_sha256` — SHA-256 over the seal's canonical payload
  (org, tip_event_id, tip_event_hash, event_count, sealed_at,
  sealed_by_*, note). Always populated.
- `seal_signature_hex` — optional HMAC over `seal_hash_sha256`,
  emitted when the org has signing enabled and the keyring is
  consistent.
- `seal_signing_key_id` — which keyring entry signed the seal.

Two verification surfaces:

- `GET /admin/operations/evidence-chain/seals?verify=true` — list
  with per-row verdict.
- `GET /admin/operations/evidence-chain/seals/{id}/verify` —
  single-seal full verdict including `stored_hash` and
  `recomputed_hash` so an operator can eyeball the diff.

Verdict shape: `{mode, ok, hash_ok, signature_ok, error_code,
reason, recomputed_hash, stored_hash, key_id}`. Pre-Phase-57 seals
(no `seal_hash_sha256`) report `mode="legacy"` with
`error_code="legacy_seal_without_hash"` — operator-visible, not
silently "ok".

**Trust semantics**: a clean hash verdict proves the row has not
been mutated since it was written. A clean signature verdict adds
"the host that wrote it held the HMAC key". Both together give
operator-defensible proof of seal integrity. A sophisticated
attacker with both DB write access AND the HMAC secret can forge
— but that attacker can forge anything, and that threat model
requires out-of-band key custody (documented as a later pass).

## Sink retry contract

`POST /admin/operations/evidence-sink/retry-failed`
(security-admin gated) retries every evidence event in the org
where `sink_status = 'failed'`, oldest first, up to
`max_events` (default 100, cap 500).

**Guarantees**:

- never modifies any canonical evidence column (`event_hash`,
  `prev_event_hash`, `content_fingerprint`, etc.) — ONLY the
  sink_* tracking columns
- `sink_attempt_count` increments on each attempt so stuck rows
  become visible
- emits `evidence_sink_retry_attempted` audit event
- returns `{attempted, sent, failed, skipped, events[]}` so the
  operator sees both per-call summary and per-row outcome

Operator flow is: observe `evidence_sink_retry_pending` counter on
the ops overview, probe the sink via `/evidence-sink/test`, fix
transport config if needed, then retry-failed.

## Retention / GC policy

New per-org setting under `organizations.settings.security`:

```
{ "export_snapshot_retention_days": 365 | null }
```

- `null` (default) → retain forever.
- integer ≥ 90 → soft-purge snapshot bodies older than this window
  on operator-initiated sweep.
- integer < 90 → rejected at policy-write time (hard floor so an
  accidental config change cannot destroy current-quarter
  evidence).

**Soft-purge semantics**: when a snapshot enters the sweep, the
heavy `artifact_json` body is cleared (set to empty string). The
row, `artifact_hash_sha256`, `content_fingerprint`, the link to
`evidence_chain_event_id`, and the issuer metadata are preserved.
Evidence chain references to the snapshot id remain resolvable;
the hash remains comparable if a matching byte stream is produced
elsewhere. Two new columns make this visible:

- `artifact_purged_at` — when the sweep cleared the body.
- `artifact_purged_reason` — canonical reason string
  (`retention_sweep:days=N;retained_hash_only`).

**Operator flow**:

1. `POST /admin/operations/export-snapshots/retention-sweep`
   `{"dry_run": true}` — see `candidate_ids` + `candidates_found`.
2. `POST …/retention-sweep` `{"dry_run": false}` —
   actually clear the bodies.

Every sweep (dry-run or real) emits
`export_snapshot_retention_sweep` audit. Real sweeps also report
`purged` count. Security-admin gated.

**Hard-delete is intentionally NOT implemented.** The row id is
referenced by evidence chain events; dropping the row would break
the referential integrity of forensic forward pointers. If a
regulator mandates hard delete, that is a separate conversation
requiring chain event cleanup in the same transaction; this pass
stays safe by default.

## Admin visibility

Two new operations categories surfaced on the overview counters:

- `evidence_signing_inconsistent` (severity `error`) — org has
  signing enabled but active key is missing from the process ring.
- `evidence_sink_retry_pending` (severity `warning`) — current
  count of rows with `sink_status='failed'` (not windowed — the
  backlog is a backlog).

`security_policy` block on the overview now also carries:

- `evidence_signing_active_key_id` (string)
- `evidence_signing_active_key_present` (bool)
- `evidence_signing_keyring_key_ids` (string[])
- `evidence_signing_inconsistent` (bool)
- `export_snapshot_retention_days` (int or null)
- `export_snapshot_retention_configured` (bool)

A dedicated `GET /admin/operations/signing-posture` endpoint
returns the same keyring view for UI code that only needs signing
posture. **Never exposes secret material** — only key ids + a
consistency verdict.

The `OperationsPane` Infrastructure bucket renders the two new
cards alongside the existing evidence signals. No new tabs, no
redesign.

## Client / API type additions

`apps/web/src/api.ts` gained:

- `SigningPostureResponse`, `SealVerificationVerdict`,
  `SealVerifyResponse`, `EvidenceSinkRetryEvent`,
  `EvidenceSinkRetryResponse`,
  `ExportSnapshotRetentionSweepResponse`.
- Helpers: `getSigningPosture`, `verifyEvidenceChainSeal`,
  `retryFailedEvidenceSinkDeliveries`,
  `runExportSnapshotRetentionSweep`.
- `SecurityPolicyPayload` + `SecurityPolicyPatch` gained
  `export_snapshot_retention_days`.
- `OperationsSecurityPolicyStatus` gained the six new evidence
  posture / retention fields.
- `ExportSnapshotSummary` gained `artifact_purged_at` and
  `artifact_purged_reason`.
- `listEvidenceChainSeals(email, {verify})` now supports the
  `?verify=true` query flag.

## Tests

New file: `apps/api/tests/test_evidence_maturity.py` — 24 tests:

- **Keyring / rotation (6):** old bundle verifies after rotation
  when old key in ring; fails with `signing_key_not_in_keyring`
  when dropped; 503 on missing active key; legacy env alias as
  "default"; signing-posture endpoint never exposes secrets;
  signing-posture flags inconsistent config.
- **Signed seals (5):** write stamps hash + signature; verify ok
  on clean row; tamper detection on canonical fields; bulk list
  with `?verify=true`; role guard.
- **Sink retry (4):** retries only failed rows + increments
  attempt count + preserves `event_hash`; successful retry after
  transport repair; role guard; audited.
- **Snapshot retention (5):** policy rejects below 90 days; accepts
  null + valid value; no-op sweep when unconfigured; dry-run then
  real soft-purge; rows younger than retention left alone; audited
  + role-gated.
- **Admin visibility (2):** new counters surfaced; signing
  inconsistent flagged.
- **Regression (2):** pilot flow still green; phase-56 signed
  bundle tests updated to provision the keyring (previous tests
  used the legacy env alone + named a non-default key_id — now
  explicitly either stays default or adds a matching key to the
  ring).

Phase-56 suite (21 tests) updated: `_enable_signing` helper now
provisions the keyring env for non-`default` key_ids, with a
`populate_keyring=False` override for the
`test_signing_enabled_without_key_returns_503` test.

## Validation

- `alembic upgrade head` from empty: clean; head `e1f2a304150d`.
- Backend `pytest -q`: **543 passed / 0 failed** in 611 s (up from
  519; +24 new evidence-maturity tests).
- `npm run typecheck`: clean.
- `npm test -- --run` (vitest): **194 passed / 9 files**.
- `npm run build`: clean.

## Remaining gaps (documented honestly)

- **Signed + external-mirrored seals.** Seals live in-DB. Mirroring
  the seal row (hash + signature only — never the HMAC secret)
  to the existing evidence sink on write would give off-host
  assurance that seal rows cannot be silently rewritten.
- **Automatic periodic sealing.** Seals are still manual. A
  scheduled sealing cadence (cron / worker tick) is a natural
  next pass.
- **Key custody.** HMAC secrets live in process env. A proper
  secrets-manager integration (AWS KMS, HashiCorp Vault, etc.) is
  a deployment concern — this pass ships the keyring contract so
  a later deploy-side integration has something to wire to.
- **Retention on evidence events themselves.** Retention today
  applies only to `note_export_snapshots.artifact_json`. The
  evidence chain events are kept indefinitely; if an org
  eventually requires event-level retention, it needs a separate,
  chain-aware design because deleting an event breaks the hash
  chain from that row forward.
- **Ed25519 / public-key signing.** HMAC requires the verifier to
  hold the secret. An external consumer who needs to verify
  without holding the signing key will need Ed25519 or equivalent;
  the keyring shape is already key-id addressable so the extension
  is a key-type column + signing-mode enum, not a redesign.
- **Restore / re-sign flow.** There is no path today to re-sign a
  legacy unsigned bundle or to re-seal a pre-Phase-57 seal. Both
  are intentional — re-signing changes provenance and should be an
  explicit, audited operation.
