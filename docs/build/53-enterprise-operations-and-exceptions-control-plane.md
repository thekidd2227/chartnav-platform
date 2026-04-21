# Phase 53 — Enterprise Operations & Exceptions Control Plane (Wave 8)

Repo: `thekidd2227/chartnav-platform`
Branch: `chartnav-roi-wave-1`
Alembic head: `e1f2a304150a` (up from `e1f2a3041509`)

## What Wave 8 implemented

Wave 8 turns the pile of denial audit events and blocked-state note
rows into one usable admin surface. Before Wave 8, answering "what
is broken in my org right now?" required running ad-hoc SQL against
`security_audit_events` or scrolling the raw audit log. After Wave 8
there is a single admin tab that surfaces:

- **Overview** counters grouped by domain (governance, identity &
  sessions, infrastructure), with remediation hints pulled from a
  central taxonomy.
- **Final approval queue** — every note in the org currently
  `pending` or `invalidated`, including attribution and timestamps.
- **Blocked notes** — merged timeline of sign-blocked, export-blocked,
  signature-mismatch, and unauthorized-approval events.
- **Identity** — real auth-denial events (unknown user, invalid
  issuer, expired token, cross-org attempts). Intentionally does NOT
  claim a SCIM queue because SCIM is not in the repo; the tab carries
  an explicit advisory saying so.
- **Sessions** — revocations and timeouts from `user_sessions` /
  `security_audit_events`.
- **Ingest** — stuck `encounter_inputs` rows (status=failed or
  `last_error_code` set).
- **Security config** — synthesized card that tells the admin whether
  session tracking, the audit sink, the admin allowlist, and MFA are
  configured. Flags a fully-unconfigured org.

No module is decorative. Every counter ties to an indexed query;
every row in every queue is a real audit row or a real
`note_versions` row. There are no trend charts, no vanity metrics,
no "score" numbers.

## Exact operational exception model

Single source of truth: `apps/api/app/services/operations_exceptions.py`.

- `ExceptionCategory` enum — 18 canonical categories covering
  governance, identity/auth, session, ingest, and config-state.
- `EVENT_TO_CATEGORY` dict — maps every known audit `event_type` to
  a category. Adding a new category requires extending this dict AND
  the UI taxonomy; the dict is the server-side contract.
- `CATEGORY_METADATA` dict — per-category `label`, `severity`
  (`info` | `warning` | `error`), and `next_step` remediation hint.
  Published to the client via
  `GET /admin/operations/categories` so the UI doesn't inline copy.
- `ExceptionItem` dataclass — uniform shape for every queue row.
- `ExceptionCounters` dataclass — the overview payload.

### Categories surfaced

- Clinical governance:
  `governance_sign_blocked`, `export_blocked`,
  `final_approval_pending`, `final_approval_invalidated`,
  `final_approval_signature_mismatch`,
  `final_approval_unauthorized`.
- Identity / access:
  `identity_unknown_user`, `identity_token_expired`,
  `identity_invalid_token`, `identity_invalid_issuer`,
  `identity_invalid_audience`, `identity_missing_user_claim`,
  `identity_cross_org_attempt`.
- Session governance:
  `session_revoked_active`, `session_idle_timeout`,
  `session_absolute_timeout`.
- Infrastructure / config:
  `ingest_stuck`, `security_policy_unconfigured`.

### Categories intentionally NOT added

- `scim_identity_conflict` — SCIM is not implemented in this repo.
  The identity endpoint publishes `scim_configured: false` and the
  UI prints an honest advisory rather than an empty queue that would
  suggest SCIM exists.
- `oidc_identity_ambiguous` — OIDC mapping is a pure email-claim
  lookup. There is no ambiguity concept; the closest real signal is
  `identity_unknown_user`, which IS surfaced.

## Exact admin/operations surfaces added

All HTTP routes in `apps/api/app/api/routes.py`, gated by
`caller_is_security_admin` (403 `security_admin_required` for
non-admins; same style as the existing `/admin/security/*` surface).
Every endpoint is org-scoped to the caller.

| Method + Path | Returns |
|---|---|
| GET `/admin/operations/overview?hours=` | `ExceptionCounters` + `security_policy` status + `total_open` summary |
| GET `/admin/operations/blocked-notes?hours=&limit=` | merged sign-blocked / export-blocked / denial events |
| GET `/admin/operations/final-approval-queue?limit=` | live `{pending, invalidated}` from `note_versions` |
| GET `/admin/operations/identity-exceptions?hours=&limit=` | identity-denial rows plus honest `scim_configured:false` + `oidc_identity_mapping:"email_claim_lookup"` advisory flags |
| GET `/admin/operations/session-exceptions?hours=&limit=` | revocation + timeout audit rows |
| GET `/admin/operations/stuck-ingest?limit=` | failed `encounter_inputs` rows |
| GET `/admin/operations/security-config-status` | synthesized config card |
| GET `/admin/operations/categories` | taxonomy for the UI |

### Frontend surface

- `apps/web/src/api.ts` gained 9 types and 8 client helpers scoped
  to the operations namespace (`OperationsItem`,
  `OperationsCategoryMeta`,
  `OperationsSecurityPolicyStatus`,
  `OperationsOverview`,
  `OperationsFinalApprovalQueue`,
  `OperationsListResponse`,
  `OperationsIdentityResponse`,
  `OperationsSeverity`,
  `OperationsCategoryValue`; helpers: `getOperationsOverview`,
  `getOperationsCategories`, `getOperationsBlockedNotes`,
  `getOperationsFinalApprovalQueue`,
  `getOperationsIdentityExceptions`,
  `getOperationsSessionExceptions`, `getOperationsStuckIngest`,
  `getOperationsSecurityConfigStatus`).
- `apps/web/src/OperationsPane.tsx` — new component, 7 tabs
  (Overview / Final approval / Blocked notes / Identity / Sessions /
  Ingest / Security config), tab-badge counters, window selector
  (24h / 7d / 14d / 30d), refresh button, unknown-category
  degradation so adding a new server category does not crash the UI.
- `apps/web/src/AdminPanel.tsx` — new `operations` tab wired with
  `data-testid="admin-tab-operations"`.
- `apps/web/src/styles.css` — `.ops-pane*`, `.ops-tab*`, `.ops-card*`,
  `.ops-table*`, `.ops-chip*`, `.ops-config*` styles. Severity data
  attributes drive the color cues; no inline styles.

## Governance / final-approval ops visibility

- Pending-approval queue reads `note_versions` directly using the
  Wave 7 `ix_note_versions_final_approval_status` index.
  `superseded_at IS NULL` is part of the filter so amended rows do
  not pollute the queue.
- Invalidated queue surfaces the reason string stamped during
  amendment plus the original signer attribution.
- Blocked-notes queue reads audit rows for
  `note_sign_blocked`, `note_export_blocked`,
  `note_final_approval_signature_mismatch`, and
  `note_final_approval_unauthorized`.
- Each row carries `error_code` + `detail` so a support operator can
  see the exact gate that fired (`sign_blocked_by_gate`,
  `export_blocked_by_gate`, `signature_mismatch`, etc.).
- Each row carries a `next_step` remediation hint pulled from the
  central `CATEGORY_METADATA` map; the UI renders it both as a
  tooltip and in the overview card copy.

## Identity / provisioning ops visibility

- Aggregates the real auth denial events emitted by
  `app/auth.py` and `app/session_governance.py`.
- Publishes `scim_configured: false` + `oidc_identity_mapping:
  "email_claim_lookup"` so the UI does not overclaim.
- Session tab separates `session_revoked_active` (expected after an
  admin revoke) from idle/absolute timeout; the latter two are
  excluded from the `total_open` summary counter to avoid inflating
  the admin badge with routine traffic.

## Audit / support usability

- New composite indexes on `security_audit_events`:
  `(organization_id, created_at)` and
  `(organization_id, error_code, created_at)` — Alembic revision
  `e1f2a304150a`. Primary index pattern is
  `(org, window) → rows` for every operational query.
- Existing audit CSV export and the raw audit-events endpoint are
  unchanged. Ops endpoints complement the raw log — they do not
  replace it.
- Every queue row carries the full set of context fields
  (`actor_email`, `note_id`, `encounter_id`, `error_code`,
  `detail`, `occurred_at`) so operators can pivot to the raw audit
  row when they need more.

## Counters / telemetry

One aggregate call — `GET /admin/operations/overview` — returns a
dict keyed by every `ExceptionCategory.value`, plus a
synthesized `security_policy` block and a coarse `total_open`
summary for the nav badge.

- `final_approval_pending` — live `COUNT(*)` over `note_versions`
  with `final_approval_status='pending' AND superseded_at IS NULL`.
- `final_approval_invalidated` — live `COUNT(*)` over
  `note_versions` with `final_approval_status='invalidated'`.
- All audit-derived counters — `GROUP BY event_type` over
  `security_audit_events` in the time window, translated to
  categories via `EVENT_TO_CATEGORY`.
- `ingest_stuck` — `COUNT(*)` over `encounter_inputs` with
  `processing_status='failed' OR last_error_code IS NOT NULL` in
  the window.
- `security_policy_unconfigured` — synthesized `1 | 0` from the
  absence of timeouts, audit sink, allowlist, and MFA.

No vanity metrics. No trend charts. No rolling averages — Wave 8
is point-in-time observation.

## Validation performed

- Alembic upgrade from empty: clean (head now `e1f2a304150a`).
- Backend pytest: **464 passed** (20 new Wave 8 tests in
  `tests/test_operations_exceptions_wave8.py`).
- Frontend typecheck: clean.
- Frontend vitest: **194 passed** (9 new `OperationsPane.test.tsx`
  tests).
- Frontend production build: clean (60 KB CSS / 351 KB JS).
- Pilot flow regression (sign → final-approve → export) verified
  green via `test_pilot_flow_still_green_after_wave8`.

## What remains for later enterprise ops waves

- **SCIM-based provisioning.** If/when the product gains a real SCIM
  source, add `scim_identity_conflict` to
  `ExceptionCategory`, map the relevant audit event_types in
  `EVENT_TO_CATEGORY`, and flip `scim_configured` to `true` in the
  identity endpoint.
- **Ops actions.** Today the ops surface is read-only. A "resolve"
  or "acknowledge" workflow on invalidated approvals and stuck
  ingest inputs would be a natural Wave 9 seam; it must remain
  audited.
- **Saved views / pinned filters.** The window selector is per-tab
  and in-memory. Persisted saved views (per-admin) would add
  operational value without reshaping the model.
- **Time-series deltas.** The current payload is a snapshot; a
  sibling endpoint that returns the previous-window delta (like
  `/admin/kpi/compare`) would let support teams spot week-over-week
  regressions.
- **Provisioning audit sink.** The identity endpoint surfaces
  denials, not the underlying IdP; a `provisioning_events` table
  would add operator visibility into the upstream flow if/when
  provisioning lands.
