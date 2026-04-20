# Phase 37 — Deployment Telemetry, LCC Control Plane, and SourceDeck Productization

> One ChartNav capability, surfaced through three lenses:
> the doctor app, LCC (multi-deployment fleet view), and
> SourceDeck (catalog + implementation flow). No fork, no fake
> second product — just an explicit set of HTTP contracts the other
> two surfaces consume.

## What landed in `chartnav-platform` this phase

- `apps/api/app/services/deployment_telemetry.py` — pure aggregator
  reading from `organizations`, `locations`, `users`, `encounters`,
  `encounter_inputs`, `note_versions`, `security_audit_events`. PHI
  minimising — no transcript bodies, no patient identifiers.
- `apps/api/app/services/capability_manifest.py` — typed
  `CapabilityCard` describing ChartNav + a shared `setup_inputs`
  schema both implementation modes (self-serve + done-for-you)
  consume.
- Eight new HTTP endpoints (six admin, two public).
- 13 deterministic backend tests covering shape, scoping, and PHI
  invariants.

## Why this lives in chartnav-platform, not in LCC or SourceDeck

This working environment contains LCC and SourceDeck only as static
HTML manuals — not as executable codebases. The brief's hard rules
are explicit: "Do not invent a fake second product. Do not fork
ChartNav into separate codebases for LCC and SourceDeck. Keep one
real ChartNav capability, surfaced differently by..."

So this phase ships:
- the **single source of truth** (in ChartNav),
- the **HTTP contracts** LCC and SourceDeck call into,
- and the **integration spec** (this document) that defines those
  contracts so the two consumer products can be built honestly when
  their codebases mature.

When LCC or SourceDeck ship as real codebases, they implement what
this spec defines and read from these endpoints. Nothing on the
ChartNav side changes.

## Surface map

| Lens | Endpoint | Auth | Purpose |
|---|---|---|---|
| ChartNav admin | `GET /admin/deployment/overview?hours=N` | admin | Top-level rollup. Default lens for the in-app admin section. |
| ChartNav admin | `GET /admin/deployment/locations?hours=N` | admin | Per-location drill-down. |
| ChartNav admin | `GET /admin/deployment/alerts?hours=N` | admin | Failure-class events grouped by event_type + error_code. |
| ChartNav admin | `GET /admin/deployment/jobs?limit=N` | admin | Recent ingestion outcomes (status + last_error_code only — PHI safe). |
| ChartNav admin | `GET /admin/deployment/qa` | admin | Review-queue counts. |
| ChartNav admin | `GET /admin/deployment/config-actual` | admin | This deployment's actual runtime config, secrets masked. |
| LCC + SourceDeck | `GET /deployment/manifest` | public | Build/runtime fingerprint. SourceDeck uses it to confirm the deployed instance matches the catalog version it expects. |
| SourceDeck catalog | `GET /capability/manifest` | public | Capability descriptor + setup inputs + prerequisites + implementation modes. |

## ChartNav admin section (lens #1)

The doctor app's admin dropdown surfaces the same data, scoped to
the admin's own org. No new frontend in this phase — the contract
is what's load-bearing; an in-app screen drops onto the same data
in the next frontend lane.

## LCC control plane (lens #2)

LCC is the multi-deployment fleet view. Treat each ChartNav
deployment as a row in LCC's fleet table. Each row keys off
`/deployment/manifest` (identity) and `/admin/deployment/overview`
(health + counts).

### Recommended LCC navigation

```
ChartNav
├─ Overview        ← fleet rollup; default landing
│                    (sums across all deployments LCC is connected to)
├─ Locations       ← drill into one deployment, then one location
├─ Alerts          ← failure events grouped, deployment dropdown
├─ Jobs            ← recent ingestion outcomes, deployment dropdown
├─ QA              ← review queues, deployment dropdown
└─ Deployments     ← list of every connected deployment + manifest +
                     last-seen timestamp + health dot
```

### LCC ↔ ChartNav protocol

- LCC stores one **deployment registration** per ChartNav instance:
  - base URL
  - admin service-account JWT (or X-User-Email in dev/header mode)
  - polling cadence (default: every 60 s for `/admin/deployment/overview`,
    every 5 min for `/admin/deployment/locations`)
- LCC's "All Locations" rollup is computed by summing the per-
  deployment counts client-side. ChartNav doesn't ship a cross-org
  aggregator on purpose — cross-tenant aggregation is LCC's job.
- LCC's deployment-detail page links straight back into the
  ChartNav admin section for the encounter / job detail view.
  ChartNav owns the PHI-bearing reads; LCC stays at the count level.

### Health dot semantics

`overview.health` is one of `green` / `amber` / `red` (computed in
`_summary_health`):

- `red` — `alerts.total >= 5` OR `inputs.failed_window >= 3`
- `amber` — oldest queued >= 10 min OR any failure / alert in window
- `green` — clean window

Tuneable on the ChartNav side; LCC just renders the dot.

## SourceDeck productization (lens #3)

SourceDeck is the implementation catalog. ChartNav is one capability
card in that catalog. SourceDeck reads `/capability/manifest` to
render the card; it offers two purchase modes that resolve to the
same shipped product.

### Capability card shape (returned by `/capability/manifest`)

```jsonc
{
  "key": "chartnav",
  "version": "1.0.0",
  "name": "ChartNav",
  "one_liner": "Doctor-first dictation + structured note workflow…",
  "longer_pitch": "…",
  "target_buyers": [...],
  "capability_summary": [...],          // bullet feature list
  "setup_inputs": [
    {"key": "organization_name", "label": "...", "kind": "string", "required": true, ...},
    {"key": "stt_provider", "kind": "select", "options": ["stub","openai_whisper","none"], ...},
    {"key": "openai_api_key", "kind": "secret", "secret_masked": true, ...},
    {"key": "audio_ingest_mode", "kind": "select", "options": ["inline","async"], ...},
    {"key": "auth_mode", "kind": "select", "options": ["header","bearer"], ...},
    {"key": "capture_modes_enabled", "kind": "select",
     "options": ["both","browser-mic","file-upload"], ...},
    ...
  ],
  "prerequisites": [
    {"key": "https_endpoint", "label": "HTTPS endpoint", "detail": "..."},
    {"key": "stt_provider_credentials", ...},
    {"key": "worker_runtime", ...},
    ...
  ],
  "implementation_modes": [
    {
      "key": "self_implementation",
      "name": "Self-implementation",
      "pricing_model": "subscription",
      "setup_owner": "buyer",
      "typical_timeline": "1–3 days from kickoff to first signed note",
      "includes": [...],
      "excludes": [...],
      "request_path": "/sourcedeck/chartnav/self"
    },
    {
      "key": "done_for_you",
      "name": "Done-for-you implementation",
      "pricing_model": "one_time_setup",
      "setup_owner": "arcg_implementation_team",
      "typical_timeline": "5–10 business days from contract to first signed note",
      "includes": [...],
      "excludes": [...],
      "request_path": "/sourcedeck/chartnav/managed"
    }
  ]
}
```

### How SourceDeck renders each mode

- **Self-Implementation** — render the `setup_inputs` schema as a
  setup form. Buyer fills required fields. SourceDeck POSTs the
  filled form to `request_path` (a SourceDeck-side endpoint, NOT
  ChartNav). On success SourceDeck provisions a ChartNav instance
  with those inputs as env vars and shows the deployment URL.
- **Done-For-You** — render the `setup_inputs` schema as a
  read-only handoff worksheet. Buyer agrees to the `pricing_model`,
  SourceDeck POSTs the request to `request_path`. ARCG's
  implementation team is paged; they own the `setup_owner=
  arcg_implementation_team` work and hand the deployment back when
  the prerequisites checklist is green and `/admin/deployment/overview`
  reports `health=green`.

The same `setup_inputs` schema drives both flows. Adding a new
required input is a one-line change in
`apps/api/app/services/capability_manifest.py` — both modes pick
it up automatically.

### Deployment readiness

SourceDeck's "is this deployment ready for the doctor to use it?"
check is a function of three reads:

1. `GET /deployment/manifest` — confirms the running build matches
   the catalog version SourceDeck deployed.
2. `GET /admin/deployment/config-actual` (with the deployment's
   own admin token) — confirms every required `setup_input` has a
   non-null actual value.
3. `GET /admin/deployment/overview` — confirms `health=green` and
   the prerequisites the LCC dot reflects (queue not stuck, no
   failed-window > 0).

Done-for-you implementation is signed off when all three are green
on the same day.

## Shared implementation model (the source of truth for both modes)

Defined in `apps/api/app/services/capability_manifest.py`. Single
source of truth — every input below is a real ChartNav config
knob; nothing aspirational.

| Key | Kind | Required | Notes |
|---|---|---|---|
| `organization_name` | string | yes | Display name in admin + LCC. |
| `primary_location_name` | string | yes | First clinic site. |
| `implementation_mode` | select(`self_implementation`/`done_for_you`) | yes | Drives SourceDeck's flow + ARCG paging rules. |
| `stt_provider` | select(`stub`/`openai_whisper`/`none`) | yes | Picks the STT adapter at boot. |
| `openai_api_key` | secret | optional | Required iff `stt_provider=openai_whisper`. **Fail-loud** — never silently downgrade. |
| `audio_upload_dir` | string | optional | Local-disk audio path. |
| `audio_upload_max_bytes` | int | optional | Default 25 MiB. |
| `audio_ingest_mode` | select(`inline`/`async`) | yes | Production should be `async`. |
| `rate_limit_per_minute` | int | optional | 0 disables. |
| `auth_mode` | select(`header`/`bearer`) | yes | `bearer` for production. |
| `jwt_jwks_url` | string | optional | Required iff `auth_mode=bearer`. |
| `capture_modes_enabled` | select(`both`/`browser-mic`/`file-upload`) | yes | Lets locked clinics disable browser-mic. |

## What stays out of LCC + SourceDeck

- **PHI.** Neither LCC nor SourceDeck ever sees transcript text,
  patient identifiers, or note content. The deepest a control-plane
  reader gets is `(input_id, status, last_error_code)`. The
  `/admin/deployment/jobs` test asserts the row keys are exactly
  this set.
- **Cross-tenant aggregation.** ChartNav's endpoints are org-scoped.
  LCC computes fleet rollups client-side from per-deployment
  responses. This keeps multi-tenant boundaries enforced at the
  source.
- **Vendor secrets.** `/admin/deployment/config-actual` masks every
  field whose key contains `key`, `token`, or `secret` so an admin
  view never echoes a live API key.

## Test coverage

`apps/api/tests/test_deployment_telemetry_phase37.py` — **13
deterministic scenarios**:

- Public manifests: capability + deployment manifests are
  fetchable without auth and carry the expected shape.
- Admin gate: clinician + reviewer both 403 across all six
  `/admin/deployment/*` reads.
- Overview shape: every load-bearing key + `health` ∈ {green,
  amber, red}.
- Live signal: a stub audio upload bumps `inputs.completed_window`.
- Org scoping: org1 admin only ever sees org1 traffic in the
  rollup.
- Locations rollup: returns the admin's org's locations only.
- Alerts: failed audio uploads land in the alerts grouping.
- Jobs PHI invariant: response rows are exactly `{input_id,
  encounter_id, input_type, processing_status,
  last_error_code, retry_count, finished_at, updated_at}` —
  no transcript, no metadata, no PHI.
- QA counts: review queue + signoff queue.
- Config-actual masking: secret-named keys come back masked.
- Phase 33–36 regression: telemetry reads do NOT mutate the
  encounter pipeline; reviewer role stays blocked.

Full backend suite remains green: 348 → **361 passed** (+13
phase-37). No frontend changes in this phase.

## Files touched

- `apps/api/app/services/deployment_telemetry.py` (new)
- `apps/api/app/services/capability_manifest.py` (new)
- `apps/api/app/api/routes.py` (8 new endpoints appended)
- `apps/api/tests/test_deployment_telemetry_phase37.py` (new)
- `docs/build/45-control-plane-and-productization.md` (this file)

## Deliberately not done

- **No LCC frontend code.** LCC isn't a live codebase here. The
  spec above is enough for a real LCC build to consume the
  contracts honestly.
- **No SourceDeck frontend code.** Same reason. The
  `/capability/manifest` endpoint is the surface; SourceDeck's
  catalog renderer drops onto it.
- **No new frontend in the doctor app.** The deployment endpoints
  exist; an in-app admin screen for them is its own phase.
- **No multi-tenant aggregator on the ChartNav side.** Cross-tenant
  rollups belong in LCC client-side. Pushing them server-side
  would force ChartNav to authenticate cross-org reads, which is a
  deliberate non-feature.
