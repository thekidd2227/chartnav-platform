# Demo identities

The review environment uses **dev identity selection** — pick a user in the app,
no password. Auth is `X-User-Email` header mode (development only; production
uses real OIDC/JWT with MFA). All users are seeded deterministically.

## Clinic A — `demo-eye-clinic` (primary)

| Email | Role | Can do |
|---|---|---|
| `admin@chartnav.local` | admin | everything in the org: manage users/locations, edit patients, create/sign eye diagrams |
| `clin@chartnav.local` | clinician | open charts, edit patients, create/sign eye diagrams, notes |
| `tech@chartnav.local` | technician | operational tasks (capture/intake) per role dashboard |
| `front@chartnav.local` | front desk | scheduling / front-office surfaces |
| `rev@chartnav.local` | reviewer | **read-only** — can view, cannot create/sign (writes → 403) |

Seeded patients: **PT-1001 Morgan Lee**, **PT-1002 Jordan Rivera**.

## Clinic B — `northside-retina` (for cross-tenant tests)

| Email | Role |
|---|---|
| `admin@northside.local` | admin |
| `clin@northside.local` | clinician |
| `tech@northside.local` / `front@northside.local` | technician / front desk |

Seeded patient: **PT-2001 Priya Shah**.

## Why two clinics

Tenant isolation is enforced by `organization_id`. Logged in as
`admin@northside.local`, requesting Clinic A's patient returns a **non-disclosing
404** (looks like the patient doesn't exist) — confirming a tenant can't reach
another tenant's data. Try it in `FEATURE_TEST_SCRIPT.md`.

> Synthetic data only. These are not real people and not real credentials.
