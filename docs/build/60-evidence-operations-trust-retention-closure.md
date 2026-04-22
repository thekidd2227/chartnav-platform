# Phase 59 — Evidence Operations, Trust, and Retention Closure

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150f` (up from `e1f2a304150e`)

## Scope

Closes the remaining operator-grade gaps in the evidence lane so
trust and retention are **operable**, not only **generated**.
Waves 55–57 produced the evidence chain, bundles, signatures,
seals, and snapshots. This pass finishes the operational seams
around them:

- a unified trust verdict for bundle verification
- retry lifecycle (pending → permanent_failure → abandoned) with
  an explicit attempt cap
- operator-initiated abandon action with audit
- retention policy + sweep for operational retry noise
- two new ops overview counters

No canonical evidence semantics change. The chain remains
hash-linked and immutable; every new seam touches operational
metadata only.

## Bundle trust contract

`POST /note-versions/{id}/evidence-bundle/verify` now returns a
new `trust` block in addition to `body_hash_ok` and `signature`.
Operators read the category; the underlying fields are preserved
for forensic detail.

| category | meaning | operator action |
|---|---|---|
| `verified` | body hash OK + HMAC verifies | none |
| `unsigned_ok` | body hash OK, bundle issued unsigned | confirm policy — trust limited to body hash |
| `failed_tamper` | recomputed body hash ≠ envelope hash | reject; investigate how the bundle was mutated |
| `failed_signature` | body hash OK, HMAC mismatch | reject; likely envelope-only tamper or signature corruption |
| `stale_key` | HMAC key_id not in this host's keyring | restore the key OR re-verify on another host |
| `stale_config` | signing enabled, no keys configured | fix signing config; cannot verify today |
| `unverifiable` | malformed signature / unknown mode | treat as untrusted; bundle may be legacy |

Service API: `classify_bundle_trust(body_hash_ok, signature_verdict)`
returns `{category, ok, reason, signature_mode, key_id}`. Category
is stable; client UI can switch on it.

## Retry lifecycle

Three dispositions now govern an evidence event's delivery state.
Column: `note_evidence_events.sink_retry_disposition`.

- **NULL** — legacy pre-Phase-59 row. Treated as `pending` by the
  retry sweep.
- **`pending`** — transport failure, eligible for automatic retry.
- **`permanent_failure`** — attempts crossed
  `MAX_SINK_ATTEMPTS` (constant, currently `10`). No more
  automatic retries; requires operator review.
- **`abandoned`** — operator explicitly gave up via the abandon
  endpoint. Never retried.

Lifecycle rules (enforced in `evidence_sink.update_sink_status`):

- Success (`sent`): disposition clears to NULL (no longer a retry
  candidate).
- Failure (`failed`): disposition becomes `pending` unless the
  post-attempt count reaches `MAX_SINK_ATTEMPTS`, in which case
  it auto-promotes to `permanent_failure`.
- Skip (sink disabled): disposition unchanged.
- Explicit override (`disposition_override`): used by abandon
  path; bypasses the policy.

The retry endpoint (`POST /admin/operations/evidence-sink/retry-
failed`) now selects ONLY rows with `sink_status='failed' AND
(sink_retry_disposition IS NULL OR 'pending')`. Rows that are
`permanent_failure` or `abandoned` are left alone until an
operator acts.

### Abandon endpoint

`POST /admin/operations/evidence-events/{event_id}/abandon`
(security-admin gated; body: `{reason?: string}`).

Semantics:

- only `sink_status='failed'` rows are abandonable;
  anything else returns 409 `abandon_not_applicable`
- cross-org / missing id → 404 `evidence_event_not_found`
- idempotent: abandoning an already-abandoned row returns OK
- `sink_retry_disposition` flips to `abandoned`
- `sink_error` is overwritten with the operator's reason string
  (preserves why the decision was made)
- `sink_attempt_count` is NOT incremented — abandoning is not
  an attempt
- emits `evidence_event_abandoned` audit event

## Retention policy

New per-org setting `evidence_sink_retention_days`. Null = retain
forever; integer ≥ 7 = sweep after N days. Hard floor of 7 days
enforced at policy-write time so the most recent failure reason
always survives a weekend of triage.

### `POST /admin/operations/evidence-sink/retention-sweep`

- `{dry_run: true}` → returns candidates, no writes
- `{dry_run: false}` → clears `sink_error` on rows where:
  - `organization_id` matches
  - `sink_retry_disposition IN ('abandoned', 'permanent_failure')`
  - `sink_attempted_at < now - retention_days`
  - `sink_error IS NOT NULL` (idempotent)

SAFETY — the sweep **never**:

- deletes a row (chain references stay resolvable)
- touches `event_hash`, `prev_event_hash`, `content_fingerprint`,
  or any canonical column
- clears the disposition itself (operators still see what the
  final state was)

Retention is therefore honest: the chain remains immutable; only
the operational noise (failure reason text) is pruned. Audited as
`evidence_sink_retention_sweep`.

## Admin visibility

New operations category `evidence_sink_permanent_failure`
(severity `error`). Surfaced on the Infrastructure bucket of the
ops overview. The pre-existing `evidence_sink_retry_pending`
counter now counts **only** rows in the pending pool, so the two
categories are disjoint:

- `evidence_sink_retry_pending` — auto-retries will keep trying
- `evidence_sink_permanent_failure` — auto-retries will NOT
  (operator action required)

The overview `security_policy` block now also exposes:

- `evidence_sink_retention_days`
- `evidence_sink_retention_configured`
- `evidence_sink_max_attempts` (the cap constant itself, so an
  operator reading the UI can understand when a row will promote)

## Client / API type additions

`apps/web/src/api.ts`:

- `BundleTrustCategory`, `BundleTrustVerdict`
- `EvidenceBundleVerifyResponse.trust` optional field
- `EvidenceEventAbandonResponse` + `abandonEvidenceEvent` helper
- `EvidenceSinkRetentionSweepResponse` +
  `runEvidenceSinkRetentionSweep` helper
- `SecurityPolicyPayload` / `SecurityPolicyPatch` gained
  `evidence_sink_retention_days`
- `OperationsSecurityPolicyStatus` gained the three new evidence-
  sink posture fields

`OperationsPane` Infrastructure bucket includes the new card via
data-driven keys; no layout redesign.

## Tests

New file: `apps/api/tests/test_evidence_operations_closure.py`
(20 tests):

- **Unified trust verdict (3):** verified + unsigned_ok; all five
  failure categories; `/evidence-bundle/verify` returns the field.
- **Retry disposition (3):** first failure → pending; cap auto-
  promotes; successful retry clears disposition back to NULL.
- **Abandon endpoint (5):** flips disposition; 409 on non-failed
  rows; security-admin guard; cross-org → 404; audit event fires.
- **Retention policy + sweep (5):** policy rejects < 7 days;
  accepts valid + null; no-op when unconfigured; dry-run then
  real clear; leaves young rows alone; role guard + audit.
- **Ops overview (2):** disjoint pending vs permanent counters;
  security_policy surfaces `evidence_sink_max_attempts`.
- **Regression (2):** pilot flow end-to-end; phase-56/57 evidence
  tests unaffected.

## Validation

- `alembic upgrade head` from empty: clean; head `e1f2a304150f`.
- Backend `pytest -q`: **583 passed / 0 failed** (up from 563;
  +20 new tests).
- `npm run typecheck`: clean.
- `npm test -- --run` (vitest): 194/194 / 9 files.
- `npm run build`: clean.
- No regression against Phases 54–58.

## Remaining items (documented honestly)

- **Exponential backoff** between retries. Current retries are
  operator-triggered bulk sweeps with no spacing logic. A worker-
  driven scheduled retry loop is a natural follow-up.
- **Per-event notification** when a row auto-promotes to
  permanent_failure. Today operators see the counter on the ops
  overview; a proactive notification path (email/webhook) is
  out of scope.
- **Re-enable abandoned rows.** An abandoned row is terminal in
  this pass; bringing one back into the retry pool requires a
  small future endpoint (`un-abandon`) that must itself be
  audited.
- **Cross-host trust posture aggregation.** `stale_key` and
  `stale_config` are returned per verify call. A fleet-wide
  "which keys are known on which hosts" view would help a
  multi-tenant operator but needs a directory component that
  does not exist.
- **Automatic retention cadence.** The retention sweep is manual.
  A small scheduled worker that runs the sweep on a cadence
  aligned with `evidence_sink_retention_days` is a reasonable
  follow-up.
