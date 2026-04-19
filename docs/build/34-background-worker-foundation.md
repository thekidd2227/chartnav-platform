# Background Worker Foundation + Bridged Encounter Refresh (phase 23)

Ingestion now has a real worker seam: claim-based queue pickup
prevents double-processing, stale claims get recovered, and the
phase-22 `run_ingestion_now()` is wrapped by a `run_one()`
`run_until_empty()` pair that a cron, systemd timer, or background
process can call without touching the HTTP layer. Bridged external
encounters gained a small, honest refresh foundation — the first
real step toward periodic mirror sync — with strict source-of-truth
enforcement.

No new infra (no Redis, no Celery, no broker), no fake STT, no
write-back to the external EHR.

## 1. Schema change (migration `d0e1f2a30415`)

Two columns added to `encounter_inputs` via batch rewrite:

| column       | type          | notes |
|--------------|---------------|-------|
| `claimed_by` | VARCHAR(64) nullable | worker id currently owning the row |
| `claimed_at` | DATETIME nullable    | when the claim was taken; used for stale-claim recovery |

Plus an index on `(processing_status, claimed_by)` so the
"give me one queued + unclaimed row" query is cheap.

Pure additive. Existing rows unchanged.

## 2. Worker primitives (`app/services/worker.py`)

```python
claim_one(worker_id=None)          # -> ClaimResult(input_id, claimed)
release_claim(input_id, reason=…)  # explicit release
requeue_stale_claims(worker_id=None)
run_one(worker_id=None)            # claim + process + return WorkerTick
run_until_empty(worker_id=None, max_ticks=100)
```

**Claim atomicity.** Two concurrent callers never win the same row —
`claim_one()` issues an UPDATE conditioned on `claimed_by IS NULL`
and re-reads the row to confirm the winner. Mutual exclusion at the
row level; no advisory locks required, works identically on SQLite
and Postgres.

**Stale-claim TTL.** A row whose claim is older than
`CHARTNAV_WORKER_CLAIM_TTL_SECONDS` (default `900` = 15 minutes)
gets re-queued on the next `claim_one()` or `requeue_stale_claims()`
call. TTL is env-tunable with a 30-second floor.

**Worker identity.** `<hostname>/<pid>` by default. Operators override
via `CHARTNAV_WORKER_ID` for semantic names.

**Failure path.** A pipeline failure is already persisted on the row
by `run_ingestion_now()` (phase 22); the worker additionally clears
the claim so a follow-up `retry` doesn't hit stale-claim logic.

## 3. HTTP + CLI

| Surface | Notes |
|---|---|
| `POST /workers/tick` (admin) | Claim-and-process one row; `200 {processed:false}` if queue empty. |
| `POST /workers/drain` (admin) | Run until empty (capped at 100 ticks); returns `{processed, completed, failed, error_codes}`. |
| `POST /workers/requeue-stale` (admin) | Recover stale `processing` rows; returns `{recovered: N}`. |
| `scripts/run_worker.py --once` | One tick; JSON-per-line output. |
| `scripts/run_worker.py --drain` | Drain the queue. |
| `scripts/run_worker.py --loop [--interval 5]` | Long-running worker loop; SIGINT-safe. |
| `scripts/run_worker.py --requeue-stale` | Recovery one-shot. |

All three primitives are admin-only HTTP for the ops console / smoke
script use case. A deployment with a real worker process calls the
`app.services.worker` primitives directly; the HTTP hook is the same
function behind HTTP so operators aren't locked out.

## 4. Bridged encounter refresh (`app/services/bridge_sync.py`)

```python
refresh_bridged_encounter(*, native_id, organization_id)
```

- Only works on bridged encounters (`external_ref` + `external_source`
  set). 409 `not_bridged` on standalone-native rows.
- Re-calls the adapter's `fetch_encounter` and reconciles **only**
  the mirror fields (`patient_identifier`, `patient_name`,
  `provider_name`, `status`). Everything else — especially
  ChartNav-native tables (workflow_events, encounter_inputs,
  extracted_findings, note_versions) — is untouched.
- **Source-of-truth guard.** If the deployment's current adapter
  key doesn't match the historical `external_source` on the row,
  refresh refuses with 409 `external_source_mismatch`. No silent
  cross-vendor re-mapping.
- Never writes back to the external EHR.

HTTP: `POST /encounters/{id}/refresh` (admin + clinician; reviewer
403; cross-org 404). Emits `encounter_refreshed` audit event
regardless of whether any mirror field actually changed.

## 5. Frontend UX

- **NoteWorkspace Tier 1** gains:
  - A "↻ Refresh" button next to the tier heading — re-fetches the
    input list so operators can pick up worker-completed rows
    without reloading the page.
  - A `banner--info` "Processing continues in the background" block
    that appears whenever any input is `queued` OR `processing`.
    The banner text differentiates "waiting for a worker" from
    "currently processing".
- **Encounter detail** gains a **BridgedEncounterRefreshBanner** when
  the native row carries an `external_ref`. Admin + clinician see a
  **Refresh from external** button that dispatches
  `refreshBridgedEncounter` and surfaces which fields changed.
  Reviewer sees a subtle-note explaining the RBAC.
- `refreshDetail` in App.tsx now preserves the mounted detail pane
  on re-fetch (only shows the "Loading…" fallback on initial load
  for a given id), so banner state persists across refresh cycles.

## 6. Tests

Backend **+21**:
- `tests/test_worker.py` (12): claim atomicity, claim stamps,
  run_one happy path, failure path clears the claim, drain,
  stale-claim recovery, fresh claims not recovered, HTTP
  endpoints (tick / drain / requeue-stale) admin-only, HTTP tick
  processes one row and empties the queue, no regression on the
  phase-19/22 inline text wedge.
- `tests/test_bridge_sync.py` (9): standalone refusal, bridged row
  updates mirror fields only, idempotent on unchanged shell,
  doesn't touch ChartNav-native workflow, source-of-truth mismatch
  refusal, reviewer 403, cross-org 404, audit event emitted on
  refresh.

Frontend **+6** (total 55/55 Vitest):
- NoteWorkspace queue banner renders for queued rows with
  "waiting for a worker" copy.
- Banner differentiates "currently processing" when a row is
  claimed.
- Banner hidden when all inputs are `completed`.
- Manual refresh button re-fetches the input list.
- Bridged-native encounter renders the refresh banner + button,
  dispatches `refreshBridgedEncounter`, shows the success message.
- Reviewer role sees the refresh banner but no button and a
  disabled-note.

Playwright: 17/17 workflow + a11y. Visual baselines refreshed.

## 7. Configuration

| Env var | Default | Notes |
|---|---|---|
| `CHARTNAV_WORKER_CLAIM_TTL_SECONDS` | `900` | Stale-claim TTL, min 30s |
| `CHARTNAV_WORKER_ID`                | `<hostname>/<pid>` | Semantic override |

## 8. What this phase does NOT do

- No real STT. Phase-22 seam + phase-23 worker wire together cleanly,
  but `ingestion.transcribe_audio` still raises
  `audio_transcription_not_implemented` by default. A deployment
  installs a real transcriber via `ingestion.set_transcriber(fn)` at
  boot; the worker picks it up automatically.
- No WebSocket / SSE push. The UI polls via explicit refresh. A
  future phase can wire a push channel without changing the
  contract.
- No bridged-encounter background sync loop — the refresh is
  operator-triggered (or callable from a future cron). Full
  continuous sync belongs to a dedicated phase.
- No `DocumentReference` write-back to external EHRs. Export stays
  download + clipboard.
- No broker / queue infrastructure. The in-repo worker is enough
  for single-node deployments; a future Celery/RQ/SQS adapter can
  keep the same primitives.
