# Phase 47 — Pilot KPI Scorecard + Enterprise Control-Plane Seam

> Two concerns in one pass. The KPI scorecard is the **shipped
> production lane**. The enterprise control-plane blueprint below
> is the **next build lane**, scaffolded here as a docs-first seam
> so wave-2 can be executed against a concrete contract rather
> than a fresh design discussion.

## Part 1 — KPI scorecard (shipped this phase)

### What landed

- `apps/api/app/services/kpi_scorecard.py` — pure aggregation
  module. No new schema. Reads:
    - `encounter_inputs.{created_at, started_at, finished_at,
       processing_status}`
    - `note_versions.{created_at, signed_at, exported_at,
       draft_status, version_number, generated_by,
       missing_data_flags}`
    - `encounters.{provider_id, provider_name, organization_id,
       created_at}`
    - `providers.{id, display_name, organization_id, is_active}`
- Three admin, org-scoped HTTP endpoints:
    - `GET /admin/kpi/overview?hours=N` — org rollup.
    - `GET /admin/kpi/providers?hours=N` — per-provider breakdown.
    - `GET /admin/kpi/export.csv?hours=N` — flat CSV for pilot
       reporting (before/after comparisons).
- `apps/api/tests/test_kpi_scorecard.py` — 11 tests covering
  unit helpers, admin-only access, org scoping, shape of JSON
  payloads, CSV contract, export audit, and query validation.

### Metrics surfaced (all derived from existing timestamps)

| Metric | Formula | Source |
|---|---|---|
| Transcript → draft (min) | first completed input.finished_at → first note_version.created_at | `encounter_inputs` + `note_versions` |
| Draft → sign (min) | first note_version.created_at → first note_version.signed_at | `note_versions` |
| Total time-to-signed-note (min) | first completed input.finished_at → first note_version.signed_at | `encounter_inputs` + `note_versions` |
| Missing-data rate | count(note_versions where missing_data_flags non-empty) / count(all note_versions) | `note_versions` |
| Avg revisions per signed note | per-encounter: max(version_number − 1) for encounters with a signed note | `note_versions` |
| Export-ready rate | count(exported) / count(signed + exported) | `note_versions` |
| Encounter / signed-note / exported-note counts | direct | `encounters` + `note_versions` |

All latency metrics are surfaced with `n / median / mean / p90 /
min / max` (null-safe — empty windows return `n=0` + all-nulls).

### PHI posture

Aggregations return counts, milliseconds, and rates. **Never**
transcript text, note body, or patient identifiers. Every export
is audit-logged as `admin_kpi_export`.

### Pilot usage pattern

Two identical calls with different `hours` windows produce a
before/after comparison for a pilot review. CSV export is the
format the contracted pilot reporting deliverable expects.

---

## Part 2 — Enterprise control-plane seam (next build lane)

This section is the seam definition for wave-2. The product code
surface to change is pinpointed here so wave-2 can be executed
against a concrete plan.

### Identity

**Today.** `apps/api/app/auth.py` supports two modes:

- `header` — dev-only, `X-User-Email` → `users.email` → `Caller`.
- `bearer` — production, JWT signed by a customer-managed IdP,
  verified via JWKS (`CHARTNAV_JWT_JWKS_URL`). Token `sub` /
  `email` claims map to `users.email`. Hard dependency on the
  customer's IdP.

**Seam for SSO / MFA / SCIM.** In bearer mode, the token's
claim set is the only input we honor. The enterprise lane adds:

1. A typed `IdPClaims` dataclass (subject, email, mfa_authenticated,
   acr, amr, groups) built from the token payload in
   `auth.resolve_caller_from_bearer`.
2. A `require_mfa` dependency that checks
   `IdPClaims.mfa_authenticated` or `acr ∈ { "AAL2", "AAL3" }`
   and 401s otherwise.
3. A claim → role + role-template mapping surface (see RBAC
   below). Today, `users.role` is resolved from the DB after the
   email match; tomorrow, the IdP `groups` claim can override
   if an org opts into "IdP-managed roles."
4. SCIM 2.0 provisioning lands on a new `/scim/v2/*` route
   family that creates / updates / deactivates `users` rows.

**Intentionally not done here.** SCIM endpoints themselves —
they require an agreed IdP pilot partner before implementation.

### RBAC

**Today.** `apps/api/app/authz.py` ships 4 hardcoded roles
(`admin`, `clinician`, `reviewer`, `front_desk`) with per-edge
transition maps.

**Seam for permission templates.** A new `role_templates` table
lives ahead of multi-customer role drift. Shape:

```
role_templates
  id            PK
  organization_id  nullable  (NULL = catalog template)
  name          VARCHAR(64)
  permissions   JSON  — list of predicate keys
  is_active     BOOLEAN
  created_at    DATETIME
```

The 4 hardcoded roles become catalog templates with
`organization_id = NULL`. Customers can clone into their org and
override. The `authz.py` predicates stay in-code (the list of
permission *keys* is stable); only the *template → predicate
bundle* mapping becomes data.

**Intentionally not done here.** Migration + the new table.
Adding them before the first customer asks for custom roles
creates schema churn with no pilot value.

### Tenant model

**Today.** Every route pins `organization_id = caller.organization_id`
(grep finds 84+ sites). Providers, patients, encounters,
inputs, notes, audit events, quick comments, custom shortcuts —
all carry `organization_id`. The scoping is strong, consistent,
and enforced at the query layer, not at a framework ORM policy.

**Seam for multi-region + multi-site.** `organizations` can
grow `region` and `parent_organization_id` columns without
breaking any query. Site-level scoping is already modeled via
`locations.organization_id`.

**Intentionally not done here.** Region + parent-org columns —
again, not until a real customer asks.

### Immutable audit logging

**Today.** `security_audit_events` is append-oriented by
convention. No backend DELETE path (retention job prunes by age
only — no per-row edit), no UPDATE path, and every admin write
lands in it.

**Seam for hard append-only + SIEM forwarding.**

1. A Postgres-only `BEFORE UPDATE/DELETE` trigger that raises
   `immutability_violation` when `organization_id` is not null.
   Land in the migration that ships alongside the first enterprise
   pilot.
2. A background forwarder module `apps/api/app/services/audit_sink.py`
   — pluggable transport to syslog + HTTPS webhook + S3 JSONL.
   Default transport is in-process no-op; enterprise orgs opt in
   via `CHARTNAV_AUDIT_SINK_URL`.
3. Every audit write already goes through `app.audit.record()` —
   the sink call attaches there.

**Intentionally not done here.** The trigger + the sink. Both
require a real customer SIEM endpoint to validate.

### Session governance

**Today.** Session lifetime is entirely the IdP's. No
server-side idle timeout, no logout-everywhere, no refresh
token rotation.

**Seam for session governance.**

1. Per-org settings already live in
   `organizations.settings.feature_flags`. Add keys:
   - `session_idle_timeout_minutes` (int)
   - `session_absolute_timeout_minutes` (int)
   - `require_mfa` (bool)
2. A new middleware `apps/api/app/session_policy.py` reads these
   on every request and compares to JWT `iat` / a
   `last_activity_at` stored in `user_sessions` (a new small
   table — one row per active caller).
3. Admin action `POST /admin/sessions/terminate?user_id=N` deletes
   matching rows to force a re-auth.

**Intentionally not done here.** The `user_sessions` table —
creating it without a customer MFA / session policy is
scope creep.

### Admin / security controls

**Today.** Users, locations, invitations, audit log, deployment
telemetry, feature flags, custom shortcuts, quick comments —
all admin-gated. SBOM + image digest per release. Non-root
container, health/ready endpoints.

**Seam for enterprise-grade admin.**

1. Break-glass / emergency access with audit — a dedicated
   `/admin/break-glass` action that escalates the caller for
   one request and logs `break_glass_used` with mandatory
   reason text.
2. Impersonation — admin opens an audited session as another
   user; every action in that session carries
   `actor_email=admin@, as_user_email=target@` in the audit row.
3. Customer-health dashboard (internal, cross-org) — lives
   outside the main app; calls
   `/deployment/manifest` per deployment.
4. Per-org data-export on customer request — structured JSON
   dump of every table row with `organization_id = N`, PHI
   redacted per a template. Required for data-portability
   clauses in BAAs.

**Intentionally not done here.** All four require either a
customer pilot or a signed DPA before implementation.

---

## Wave-2 exec order (when a named pilot lands)

1. **Session idle timeout + MFA required-claim check** — org
   feature-flag-driven. Zero schema cost. Ships in a week.
2. **Audit sink** — syslog + HTTPS webhook. Config-driven,
   opt-in per-org.
3. **Break-glass + impersonation + audit-trail hygiene.**
4. **Role templates table + migration** — unblocks custom roles
   for multi-customer expansion.
5. **SCIM 2.0 provisioning** — drops in against the existing
   `users` + `organizations` tables.
6. **Session governance table + terminate action.**
7. **Per-org data export.**
8. **Region / parent-org columns** — only when a multi-region
   customer needs it.

## What is **not** in this phase

- SSO (SAML / OIDC) — bearer/JWKS already exists; enterprise
  SSO is the IdP's job + the SCIM bits above.
- Field-level PHI encryption — separate wave, touches Alembic +
  all text writers.
- Pen test + SOC 2 readiness — procurement track, not a code
  track.
- FHIR write-through — still a roadmap module on the site,
  still `AdapterNotSupported` on every write path in
  `apps/api/app/integrations/fhir.py`. Intentional — site and
  code now match.
