# Operator Control Plane

Phase 13 ships the pieces an operator actually needs to run the product:
organization settings, security-audit visibility, and a minimal user
lifecycle signal (`invited_at`). The admin panel becomes a four-tab
console: Users, Locations, Organization, Audit log.

## 1. Organization settings

### API

| Method | Path            | Auth            | Body                                          |
|--------|-----------------|-----------------|-----------------------------------------------|
| GET    | `/organization` | any authed role | —                                             |
| PATCH  | `/organization` | admin only      | `{ name?, settings? }`                        |

### Contract

- **Read** is open to any authenticated caller in the org — so the UI
  can show org context in places the admin may not have visited.
- **Write** is `admin`-only (`role_admin_required` 403 otherwise).
- `slug` is **immutable** — renaming a slug ripples into URLs, audit
  search, and any downstream integration keying on it. Documented on
  the read response; the UI shows it readonly.
- `name` is a free text field (1..255 chars).
- `settings` is a JSON object. Server rejects non-object (pydantic
  422) and blobs > 16 KB of serialized JSON (400 `settings_too_large`).
- PATCH only touches the caller's org; there is no path to mutate
  another org (`organization_id` isn't even a parameter).

Persistence: new migration `d4e5f6a7b8c9` adds `organizations.settings TEXT NULL`.

## 2. Security audit read API

### Endpoint

| Method | Path                          | Auth    |
|--------|-------------------------------|---------|
| GET    | `/security-audit-events`      | admin only |

Query parameters:

| Param         | Type   | Notes                                             |
|---------------|--------|---------------------------------------------------|
| `event_type`  | string | Exact match (e.g. `cross_org_access_forbidden`).  |
| `error_code`  | string | Exact match on the response `error_code`.         |
| `actor_email` | string | Exact match.                                      |
| `q`           | string | Substring match against `path` or `detail`.       |
| `limit`       | int    | 1..500, default 50.                               |
| `offset`      | int    | ≥0.                                               |

Response is a JSON array ordered newest-first (by `id DESC`). The
pagination triplet (`X-Total-Count`, `X-Limit`, `X-Offset`) is returned
as response headers, matching the encounter pagination contract.

### Scoping rule (documented here so future readers don't have to guess)

```sql
WHERE organization_id = :caller.org OR organization_id IS NULL
```

Rows without an `organization_id` are pre-auth failures (no caller has
been resolved yet — `missing_auth_header`, `unknown_user`,
`invalid_token`, etc.). Those have **no** org attribution by
construction, so showing them to every admin is correct: they're
system-wide signals about unauth traffic hitting the service.

Rows **with** a cross-org attribution are never shown — if an admin in
org1 issues a cross-org denial (actor=1, `organization_id=1`), it
appears in org1's audit. If an attacker uses an org2 identity to probe
org1, the audit row will be `organization_id=2` and admin1 will
**not** see it. That's the right property: an org can't learn about
sibling orgs by reading its own audit.

Backed by a pytest assertion (`test_audit_org_scoping`).

### What gets written

No change from phase 10 — the HTTP exception handler still drives
inserts via `app.audit.record(...)`. The read API simply surfaces what
was already being persisted.

## 3. User lifecycle — `invited_at`

Migration `d4e5f6a7b8c9` adds `users.invited_at DATETIME NULL`. Admin
create sets it to "now"; existing seeded users stay `null`. The admin
panel renders an "Invited" badge on any active user with `invited_at`
set.

Email delivery is **intentionally out of scope** — ChartNav doesn't
send mail. The badge + timestamp are a real, testable signal that a
user hasn't been "turned on" by any other channel yet; what the
operator does with that (Slack, in-person, external mailer) is their
business.

Out of scope:
- Token-based invitation links.
- Expiring invitations.
- Email delivery and templating.
- Self-serve signup.

## 4. Admin UI — four-tab console

`apps/web/src/AdminPanel.tsx` now has:

- **Users** — create form, table with inline role change, deactivate/reactivate, self-row disabled, "Invited" badge where `invited_at` is set.
- **Locations** — create form, inline rename, deactivate.
- **Organization** — loads `/organization`, form for `name` + `settings` JSON (16 KB cap enforced server-side); slug shown readonly; local JSON parse error surfaces inline before any PATCH is fired.
- **Audit log** — filter row (`event_type`, `actor_email`, free-text `q`), paginated table (25/page), timestamp / event / actor / method+path / error code / request id columns. Backend 403 surfaces as banner.

UX invariants preserved from earlier phases:
- Non-admin callers never see the Admin button, and the panel never renders for them.
- All mutations disable submit while in flight.
- Every 4xx surfaces the backend `{error_code, reason}` envelope.

## 5. Tests

### Backend (`apps/api/tests/test_control_plane.py`, 17 new)
- Read `/organization` for all three roles + 401 without auth.
- Admin patches name, settings (valid JSON object).
- Non-object settings → 422.
- Settings > 16 KB → 400 `settings_too_large`.
- Non-admin PATCH → 403 `role_admin_required`.
- Cross-org isolation: admin1 PATCHing org1 does not change org2's row.
- Admin reads `/security-audit-events`.
- Non-admin 403.
- Filters by `event_type`, `actor_email`, and `q` substring match.
- Pagination (limit/offset, disjoint pages, X-Limit/Offset headers).
- Org scoping: admin1 never sees rows with `organization_id` outside `{1, null}`.
- New users carry `invited_at`; seeded ones do not.

### Frontend (`apps/web/src/test/AdminPanel.test.tsx`, 4 new on top of phase 12)
- Organization tab loads current org, readonly slug, edits dispatch PATCH.
- Organization settings local JSON parse error surfaces before calling backend.
- Audit tab loads, row rendered with `event_type`, filter dispatch hits the mocked API.
- Audit 403 surfaces as error banner.

### E2E (`apps/web/tests/e2e/workflow.spec.ts`, 1 new)
- Admin opens panel → Organization tab → edits name → Audit tab loads. End-to-end against the live backend.

Totals: **pytest 88/88, Vitest 22/22, Playwright 11/11**.

## 6. What this phase does NOT do

- No row-level user actions on the audit log (expand a row, pin, comment). The table is read-only.
- No export of audit events.
- No CSV download for users/locations/audit.
- No rich settings schema — the app doesn't consume any specific key in `settings` yet. The field exists so operators can stash tenant preferences before we build the consumer.
