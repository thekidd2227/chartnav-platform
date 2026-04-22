# Phase 56 — External Evidence Integrity and Immutable Audit Sink

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150c` (up from `e1f2a304150b`)

## Scope

Phase 55 introduced the in-app tamper-evident evidence chain plus a
forensic evidence bundle. Phase 56 hardens the boundary between
ChartNav and everything downstream:

1. **External evidence sink** — per-org jsonl/webhook forward channel,
   independent of the general audit sink.
2. **Cryptographically signed bundles** — optional HMAC-SHA256
   signatures over bundle body hashes.
3. **Export snapshots** — byte-exact, hash-stamped capture of what
   was actually handed off at export time.
4. **Chain seals** — manual checkpoints that capture tip event_hash
   + count so silent rewinds are detectable.
5. **Admin visibility** — two new ops-overview counters plus a sink
   probe endpoint.

The in-app chain remains authoritative. Every external seam is
best-effort on write and re-verifiable offline.

## External evidence sink contract

Per-org configuration under `organizations.settings.security`:

```
{
  "evidence_sink_mode":   "disabled" | "jsonl" | "webhook",
  "evidence_sink_target": "<file path>" | "<https URL>" | null
}
```

`evidence_sink_mode` is independent of `audit_sink_mode`. An org
may point observability events at one SIEM and evidence events at
a separate WORM store, or vice versa.

- `jsonl` — each evidence event appended as one line to
  `evidence_sink_target`. Canonical payload shape `{ "kind":
  "chartnav.evidence_event.v1", id, organization_id,
  note_version_id, encounter_id, event_type, actor_*, occurred_at,
  draft_status, final_approval_status, content_fingerprint,
  detail_json, prev_event_hash, event_hash }`. Every line is
  self-contained; downstream consumers re-verify integrity by
  recomputing event_hash.
- `webhook` — HTTPS POST to `evidence_sink_target` with the same
  payload + hard 2s timeout. Transport failures never block the
  governance transaction.

Per-event delivery status is persisted on
`note_evidence_events.sink_status`:

- `sent` — transport accepted the event.
- `failed` — transport rejected or raised. `sink_error` carries a
  short reason (`<ExceptionClass>:<first 200 chars>`).
- `skipped` — sink is disabled for this org.
- `NULL` — row predates Phase 56.

Admins probe the transport via
`POST /admin/operations/evidence-sink/test` (security-admin gated).

Ops overview reports `evidence_sink_delivery_failed` count over the
configured window (default 7 days).

## Signing mode contract

Per-org configuration under `organizations.settings.security`:

```
{
  "evidence_signing_mode":  "disabled" | "hmac_sha256",
  "evidence_signing_key_id": "<short id>" | null
}
```

The HMAC secret itself lives in process env
(`CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY`), NOT in per-org JSON —
that JSON is readable to org admins, and the signing material must
not be.

Semantics:

- `disabled` (default) — bundles carry `signature = { mode:
  "disabled", signature_hex: null, ... }`.
- `hmac_sha256` with env key set — bundles carry
  `signature.mode = "hmac_sha256"`, `signature.key_id`, and
  `signature.signature_hex` (SHA-256 HMAC of
  `envelope.body_hash_sha256`).
- `hmac_sha256` with env key NOT set → `GET
  /note-versions/{id}/evidence-bundle` returns 503
  `evidence_signing_unconfigured`. No silent degrade to unsigned.

Verification: `POST /note-versions/{id}/evidence-bundle/verify`
(body = the bundle JSON as issued) returns:

```json
{
  "note_id": 42, "note_id_match": true,
  "body_hash_ok": true, "recomputed_body_hash": "...",
  "claimed_body_hash": "...",
  "signature": { "mode": "hmac_sha256", "ok": true, ... }
}
```

Tamper classes and how they're caught:

| tamper | body_hash_ok | signature.ok |
|---|---|---|
| mutate body, leave envelope hash | **false** | true |
| mutate body + update envelope hash | true | **false** |
| mutate signature hex | true | **false** |
| full re-sign (attacker owns HMAC key) | true | true — out of scope |

Body-hash recomputation and signature verification together
defeat the first three. Full re-sign requires the attacker to hold
the host's HMAC secret, which is the threat boundary the secret
is designed for.

Key rotation is intentionally out of scope for this pass. A future
pass can introduce a keyed lookup indexed by `signature.key_id` so
old bundles remain verifiable after a rotation.

## Export snapshot behaviour

On every successful `POST /note-versions/{id}/export`, the platform
now:

1. emits the `note_exported` evidence event (Phase 55);
2. computes the canonical JSON artifact via the Phase 25 builder;
3. persists the byte-exact artifact bytes + SHA-256 into
   `note_export_snapshots`, linked to the evidence event id.

Schema columns on `note_export_snapshots`:
`organization_id, note_version_id, encounter_id,
evidence_chain_event_id, artifact_json (TEXT, canonical), 
artifact_hash_sha256, content_fingerprint, issued_at,
issued_by_user_id, issued_by_email`.

Consumers:

- `GET /note-versions/{id}/export-snapshots` — list (newest first).
- `GET /note-versions/{id}/export-snapshots/{snap_id}` — full
  snapshot including the captured artifact JSON.

Both are org-scoped; cross-org reads return 404.

Amendment does **not** delete or modify past snapshots. After an
amendment, the original row becomes superseded and its snapshot
is preserved as-is — that was the record of care at export time.

Ops overview surfaces `export_snapshot_missing` when a
`note_exported` event exists in the window without a corresponding
snapshot row (e.g. snapshot persist failed). This is an advisory
signal so operators can tell when a handoff occurred without an
immutable byte capture.

## Chain seal / checkpoint strategy

A seal is a manual snapshot of the org's evidence-chain tip:

```
POST /admin/operations/evidence-chain/seal   { note: "..." }
  → { id, tip_event_id, tip_event_hash, event_count, sealed_at }

GET  /admin/operations/evidence-chain/seals
  → newest-first list
```

What a seal proves: at time T, the org had N events and the tip
hash was H. If someone later drops a middle event and re-hashes the
chain (an attacker with DB access can do this), the new tip hash
differs from H and a seal comparison catches it. If the attacker
also rewrites every seal row, the admin can still cross-reference
with an externally-kept copy of H (printed, emailed, or mirrored
to a WORM store).

Seals do not replace `verify_chain()`. They cap its trust in time:
verify alone proves "the chain is internally consistent as
currently stored"; a seal proves "as currently stored matches what
we saw at a prior point". Both are needed for defensible forensics.

This pass does not auto-seal. Automatic periodic sealing is a
reasonable follow-up; this pass ships the storage, the write
endpoint, and the read endpoint so an operator can seal on a
cadence of their choice.

## Admin / API surface added

| Method | Path | Guard | Purpose |
|---|---|---|---|
| POST | `/note-versions/{id}/evidence-bundle/verify` | authed org member | body + signature verification |
| GET  | `/note-versions/{id}/export-snapshots` | authed org member | list snapshots for a note |
| GET  | `/note-versions/{id}/export-snapshots/{sid}` | authed org member | snapshot detail incl. artifact bytes |
| POST | `/admin/operations/evidence-sink/test` | security-admin | transport probe |
| POST | `/admin/operations/evidence-chain/seal` | security-admin | record a tip seal |
| GET  | `/admin/operations/evidence-chain/seals` | security-admin | list seals |

`security_policy` write path accepts the four new keys
(`evidence_sink_mode`, `evidence_sink_target`,
`evidence_signing_mode`, `evidence_signing_key_id`); read path
returns them alongside the existing audit sink config.

`/admin/operations/overview` `security_policy` block now carries
`evidence_sink_mode`, `evidence_sink_configured`,
`evidence_signing_mode`, `evidence_signing_configured` so admins
can see evidence posture at a glance.

Two new operations exception categories surfaced on the overview
counters: `evidence_sink_delivery_failed` (warning) and
`export_snapshot_missing` (warning). The Infrastructure bucket in
`OperationsPane` renders both.

## Client / API type additions

`apps/web/src/api.ts`:

- `EvidenceSinkMode`, `EvidenceSigningMode` unions.
- `EvidenceBundleSignatureVerdict`, `EvidenceBundleVerifyResponse`.
- `ExportSnapshotSummary`, `ExportSnapshotListResponse`,
  `ExportSnapshotDetail`.
- `EvidenceSinkProbeResponse`, `EvidenceChainSeal`,
  `EvidenceChainSealsResponse`.
- Helpers: `verifyNoteEvidenceBundle`,
  `listNoteExportSnapshots`, `getNoteExportSnapshot`,
  `probeEvidenceSink`, `sealEvidenceChain`,
  `listEvidenceChainSeals`.
- `SecurityPolicyPayload` + `SecurityPolicyPatch` gained the four
  new keys.
- `OperationsSecurityPolicyStatus` extended with the four new
  evidence-posture fields.

UI: `OperationsPane` Infrastructure bucket now includes the two
new cards; no new tabs, no redesign.

## Tests

New file: `apps/api/tests/test_external_evidence_hardening.py` —
21 tests:

- **Sink delivery (7):** jsonl writes one line per event marks
  `sent`; unreachable webhook marks `failed` with reason; chain
  still verifies after sink failure; disabled sink marks `skipped`;
  sink failure is org-scoped; ops overview counts failed
  deliveries in window; probe endpoint reports disabled cleanly
  and success cleanly; probe requires security-admin.
- **Signed bundles (4):** hmac_sha256 produces a 64-char hex
  signature and verifies; body-tamper detected via body-hash
  recomputation (signature still valid — correct semantics);
  signature-tamper detected; signing enabled without env key → 503
  `evidence_signing_unconfigured`; unsigned bundle verify returns
  honest "unsigned_bundle" verdict alongside body-hash recheck.
- **Export snapshots (4):** export creates snapshot linked to
  chain event; cross-org list + get return 404; amendment
  preserves snapshot; ops overview flags exports without
  snapshots.
- **Chain seals (3):** seal records tip + count + hash; sealing
  empty chain → 409 `evidence_chain_empty`; seal requires
  security-admin.
- **Regression (3):** pilot flow still green with full stack
  (sink + signing + snapshot + chain) enabled; pre-existing Phase
  55 tests remain green; previous waves' tests untouched.

## Validation

- `alembic upgrade head` from empty: clean; head `e1f2a304150c`.
- Backend `pytest -q`: **519 passed / 0 failed** (up from 498; +21
  new tests).
- `npm run typecheck`: clean.
- `npm test -- --run`: **194 passed / 9 files**.
- `npm run build`: clean.
- End-to-end chain (sign → final-approve → export → amend →
  invalidation → evidence bundle → signature verify → snapshot →
  sink delivery → chain seal) verified via the 21 new tests plus
  the pre-existing 498-test suite.
- No duplicate lifecycle truth regressed (Phase 54 source-level
  guard still passes).
- Forensic context preserved through amendment: original row
  retains its approval signature + invalidation reason + export
  snapshot even after amendment supersedes it.

## Remaining evidence/audit gaps

Explicit, to keep claims honest.

- **HMAC key rotation.** This pass supports a single active HMAC
  key via `CHARTNAV_EVIDENCE_SIGNING_HMAC_KEY`. Rotating the key
  invalidates verification of older bundles. A keyring indexed by
  `signature.key_id` is a natural next pass.
- **Automatic sealing.** Seals are manual. A scheduled sealing
  cadence + external mirror of the most recent seal would harden
  against sophisticated DB-level attacks.
- **Signed seal records.** Seals are stored in-DB. Mirroring seals
  to the evidence sink (or a separate append-only store) means an
  attacker with DB access cannot also rewrite the seal history.
- **Signing beyond HMAC.** Ed25519 (public-key) signing would let
  an external consumer verify without holding the secret. This is
  a process change (key management, key discovery) not just a code
  one; staged as a later pass.
- **Sink delivery retry.** Failed deliveries are recorded but not
  retried. A small async retry loop keyed off `sink_status='failed'`
  would close the soft-delivery gap without changing the
  authoritative chain semantics.
- **Snapshot garbage collection.** Snapshots accumulate without
  bound. A retention policy (env-driven, same pattern as
  `audit_retention_days`) is a reasonable hardening follow-up.

## Canonical lifecycle unchanged

Phase 56 adds surface area on top of the canonical lifecycle model
established in Phase 54 but does not change the lifecycle itself.
The Phase 54 source-level guard (`test_no_stale_transitions_dict_in_routes_source`)
remains green.
