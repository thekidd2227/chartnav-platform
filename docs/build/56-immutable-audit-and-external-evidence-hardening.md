# Phase 55 — Immutable Audit and External Evidence Hardening

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-enterprise-integration-wave1`
Alembic head: `e1f2a304150b` (up from `e1f2a304150a`)

## Context

Phase 54 unified the canonical lifecycle model across routes,
artifact, and supersession. This pass adds the second half of the
mission: a **tamper-evident audit chain** and a **forensic evidence
bundle** on top of that canonical model.

The existing `security_audit_events` table is append-only-by-
convention and records everything the platform does. It is the
correct place for general observability. It is NOT a tamper-evident
store — any row with write access to the DB can edit or delete
individual rows without detection.

Phase 55 adds a narrower, hash-chained log that covers only the
governance transitions that must be forensically reconstructible,
and a bundle endpoint that assembles the full evidence for any
single note in one structured document.

## What was added

### Immutable evidence chain

New migration `e1f2a304150b` creates the `note_evidence_events`
table. Each row records:

- `organization_id`, `note_version_id`, `encounter_id` — scope
- `event_type` — one of 6 canonical values (see below)
- `actor_user_id`, `actor_email`, `occurred_at`
- `draft_status`, `final_approval_status`, `content_fingerprint`
  captured at event time
- `detail_json` — event-specific structured context
- `prev_event_hash` — SHA-256 of the org's previous event (NULL
  only for the org's first event)
- `event_hash` — SHA-256 over a canonical JSON serialization of
  the row + `prev_event_hash`

Canonical event types (`EvidenceEventType` enum):

| value | emitted when |
|---|---|
| `note_signed` | `POST /note-versions/{id}/sign` succeeds |
| `note_final_approved` | `POST /note-versions/{id}/final-approve` succeeds |
| `note_exported` | `POST /note-versions/{id}/export` succeeds |
| `note_amended_source` | `POST /note-versions/{id}/amend` — original is now superseded |
| `note_amended_new` | `POST /note-versions/{id}/amend` — new amendment row is born |
| `note_final_approval_invalidated` | `POST /note-versions/{id}/amend` when the original's approval was `approved` (separately emitted; not implied by `note_amended_source`) |

### Service — `apps/api/app/services/note_evidence.py`

Pure service that owns append + verify + bundle:

- `record_evidence_event(...)` — transactional append; looks up the
  org's last `event_hash`, canonicalizes the payload with sorted
  keys, computes the new hash, inserts the row. Never raises up to
  the caller; route-layer wrappers log and proceed so a chain
  failure cannot break the governance transaction.
- `verify_chain(organization_id)` — walks the org's chain in id
  order. Recomputes `event_hash` for each row and compares against
  stored; checks `prev_event_hash` links. Returns a
  `ChainVerification` dataclass with `ok`, `broken_at_event_id`,
  and `broken_reason` (one of `prev_event_hash_mismatch`,
  `event_hash_mismatch`). Non-destructive; safe to call from the
  admin UI.
- `note_evidence_health(note_row)` — returns per-note evidence
  health (has-signed / has-final-approval / has-export /
  has-invalidated-approval / fingerprint-matches-current /
  event count / last event hash).
- `build_evidence_bundle(...)` — assembles a single structured JSON
  document covering note metadata, canonical lifecycle state, final
  approval metadata, content fingerprint (frozen + live), full
  supersession chain, the org's evidence events that touch this
  note, chain-integrity verdict, and an envelope with a
  deterministic body hash.

### Route wiring

Sign / final-approve / export / amend now call
`record_evidence_event` after their audit record. Failures are
logged (`chartnav.evidence` logger) but never propagate — the
governance transaction is authoritative; the chain is best-effort
on write and re-verifiable offline. This matches the audit-sink
pattern shipped in Wave 2.

The `amend` path emits two events for every amendment (source side
+ new row), and a third `note_final_approval_invalidated` event
only when the superseded row's approval was `approved`. An
amendment of a `pending` approval produces two events, not three.

### New HTTP endpoints

| Method | Path | Guard | Purpose |
|---|---|---|---|
| GET | `/note-versions/{id}/evidence-bundle` | any authed org member | forensic evidence bundle for one note |
| GET | `/admin/operations/evidence-chain-verify` | `caller_is_security_admin` | re-verify the org's chain |
| GET | `/admin/operations/notes/{id}/evidence-health` | `caller_is_security_admin` | per-note evidence-health card |

The bundle endpoint emits a `note_evidence_bundle_issued` audit
event so bundle issuance itself is logged.

### Operations-plane integration

`apps/api/app/services/operations_exceptions.py`:

- New category `evidence_chain_broken` (severity `error`).
- `compute_counters()` now calls `verify_chain(caller_org)` and
  surfaces the result as `counts["evidence_chain_broken"]`
  (0 when the chain verifies, 1 when it does not).
- `/admin/operations/overview` therefore reports chain integrity
  alongside governance and identity counters. The new category is
  included in the Infrastructure bucket of the admin UI.

### Evidence bundle shape

```json
{
  "bundle_version": "chartnav.evidence.v1",
  "note": { "id", "version_number", "draft_status", "content_fingerprint",
            "fingerprint_matches_current", "attestation_text",
            "signed_at", "signed_by_user_id", "signed_by_email",
            "exported_at", "reviewed_at", "reviewed_by_user_id" },
  "encounter": { "id", "organization_id", "patient_display",
                 "provider_display", "external_ref", "external_source" },
  "final_approval": { "status", "approved_at", "approved_by_user_id",
                      "approved_by_email", "signature_text",
                      "invalidated_at", "invalidated_reason" },
  "supersession": { "chain_length", "current_record_of_care_note_id",
                    "has_invalidated_approval", "chain": [ … ] },
  "evidence_events": [ { id, event_type, occurred_at, event_hash, prev_event_hash, ... } ],
  "evidence_health": { … },
  "chain_integrity": { "ok", "total_events", "verified_events",
                       "broken_at_event_id", "broken_reason" },
  "envelope": { "issued_at", "issued_by_email", "issued_by_user_id",
                "body_hash_sha256", "hash_inputs" }
}
```

`body_hash_sha256` is computed over the canonical body (sorted
keys, compact JSON) **excluding** envelope fields, so re-issuing
the bundle for the same row state produces the same hash — a
consumer can re-verify the bundle independently of when it was
issued.

## UI / API alignment

- `apps/web/src/api.ts` gained `EvidenceBundle`, `EvidenceHealth`,
  `EvidenceChainVerdict` types and three helpers
  (`getNoteEvidenceBundle`, `verifyEvidenceChain`,
  `getNoteEvidenceHealth`).
- `apps/web/src/OperationsPane.tsx` Infrastructure bucket now
  includes the `evidence_chain_broken` card. Unknown-category
  degradation remains: if the server ever returns an unknown
  category, the UI renders the raw key rather than crashing.
- No NoteWorkspace / lifecycle panel changes in this pass — the
  bundle endpoint is the programmatic forensic export; surfacing a
  "download evidence bundle" button is a trivial follow-up and is
  intentionally left out of this pass to keep the scope narrow.

## Tests

New file: `apps/api/tests/test_note_evidence_chain.py` — 19 tests:

- Hash-chain mechanics (first event has null prev; every subsequent
  event links correctly; verify_chain returns ok on clean chain;
  detects `prev_event_hash_mismatch`; detects
  `event_hash_mismatch`; chains are org-scoped).
- Route wiring (sign emits one event; sign+approve+export emits
  three; amend emits two on pending, three on approved).
- Evidence bundle (all sections present; body hash deterministic;
  supersession chain populated; cross-org → 404).
- Admin endpoints (chain-verify clean; chain-verify detects tamper;
  chain-verify requires security-admin; note-evidence-health
  happy path + role guard).
- Ops overview surfaces the new `evidence_chain_broken` counter
  when the chain is tampered with.
- Pilot flow end-to-end verifies sign/final-approve/export produce
  the expected three-event chain + a valid bundle.

## Validation performed

- `alembic upgrade head` from empty: clean; head `e1f2a304150b`.
- Backend `pytest -q`: **498 passed / 0 failed** (up from 479 — 19
  new tests).
- `npm run typecheck`: clean.
- `npm test -- --run` (vitest): **194 passed / 9 files** (no new
  UI tests required — the Operations pane's unknown-category
  degradation already covers the new `evidence_chain_broken` card).
- `npm run build`: clean (60 KB CSS / 351 KB JS).
- End-to-end enterprise chain (review / sign / final-approve /
  export / amend / invalidation / operations visibility /
  evidence bundle issuance + re-verification) verified.

## What remains for later evidence/audit waves

- **External sink for evidence events.** The chain is stored in
  the app DB. Mirroring events to the existing audit sink (jsonl /
  webhook) would give an off-host copy that survives a compromised
  app DB. A reasonable next pass.
- **Signed-artifact snapshot on first export.** The artifact is
  still computed on-demand. Storing the issued artifact bytes +
  hash on first export (with an evidence event recording that
  storage) would give true point-in-time immutability of what was
  actually handed off. Separate pass.
- **Cryptographic signing of bundles.** `body_hash_sha256` proves
  content integrity but not issuer identity. An HMAC or
  Ed25519-signed envelope is the natural next step when an
  organization deploys a signing key.
- **Chain checkpointing.** For very large orgs, storing a
  periodic `chain_tip_hash` in `organization_settings` (or
  publishing it to a write-once store) would let integrity be
  verified in O(last-checkpoint) time. Not needed at pilot scale.
- **UI affordance on NoteLifecyclePanel.** A "Download evidence
  bundle" link on the lifecycle panel would be a minor but
  worthwhile UX win — deferred to keep this pass focused on the
  model.

## No duplicate governance truth remains

All route-layer governance transitions (sign / final-approve /
export / amend) now emit evidence events from the same service
module. The chain is org-scoped, read-only verifiable at any time,
and surfaces its health through the existing operations overview
without a new admin tab. The canonical lifecycle model from Phase
54 remains the single source of lifecycle truth; Phase 55 layers
tamper-evident auditability on top.
