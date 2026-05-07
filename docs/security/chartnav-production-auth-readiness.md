# ChartNav Production Auth Readiness (Phase 18)

> Auth contract for a controlled-pilot deployment that may handle
> real PHI. Read with `chartnav-pilot-deployment-guide.md` and the
> Phase 18 controlled-pilot go-live checklist.
>
> This doc is **not** a HIPAA / SOC 2 / certified-EHR claim. ChartNav
> is **not** HIPAA-certified. The auth contract below is a
> precondition for a real-PHI conversation, not a substitute for a
> Business Associate Agreement, practice security review, or
> written practice approval.

---

## Two auth modes

ChartNav's API supports two authentication modes via
`CHARTNAV_AUTH_MODE`:

| Mode | Header / token | When |
|---|---|---|
| `header` | `X-User-Email: alice@chartnav.local` | **Local fake-data demo only.** Trivially spoofable. **Never** safe for PHI. |
| `bearer` | `Authorization: Bearer <jwt>` | **Required for any PHI environment.** Validates signature + issuer + audience + expiry. |

The validator at `scripts/validate_controlled_pilot_env.sh`
**fails** if `CHARTNAV_AUTH_MODE != bearer` or any of the three
JWT env vars are missing.

---

## Required environment in controlled-pilot

| Variable | Required | Notes |
|---|---|---|
| `CHARTNAV_AUTH_MODE` | yes — must be `bearer` | `header` is dev-only. |
| `CHARTNAV_JWT_ISSUER` | yes | OIDC issuer URL. App refuses to import without it when in bearer mode. |
| `CHARTNAV_JWT_AUDIENCE` | yes | Expected `aud` claim. |
| `CHARTNAV_JWT_JWKS_URL` | yes | JWKS endpoint for signing keys. **Must be HTTPS.** |
| `CHARTNAV_JWT_USER_CLAIM` | optional | Claim mapping the token to `users.email`. Default `email`. |
| `CHARTNAV_CORS_ALLOW_ORIGINS` | yes | Explicit list. **Wildcard rejected.** No localhost in pilot. |
| `DATABASE_URL` | yes | Postgres only in controlled-pilot. SQLite refused. |

---

## OIDC / IdP setup the practice needs to provide

ChartNav does **not** ship with a built-in identity provider. The
practice (or the operator on behalf of the practice) provides:

1. **An OIDC-compliant IdP** (e.g. Okta, Auth0, Microsoft Entra
   ID, Google Workspace, AWS Cognito, Azure AD B2C, or an
   on-premises issuer).
2. **A registered application / API** representing ChartNav.
3. **A users-and-roles map** that ChartNav can consume.
4. **Token claims** that resolve a user to a row in the
   ChartNav `users` table.

### Required claims

| Claim | Required | Used for |
|---|---|---|
| `iss` | yes | Must equal `CHARTNAV_JWT_ISSUER` |
| `aud` | yes | Must equal `CHARTNAV_JWT_AUDIENCE` |
| `exp` | yes | Token expiry (verified) |
| User identity claim | yes | Default `email`. Override via `CHARTNAV_JWT_USER_CLAIM`. The value must match `users.email` exactly. |

ChartNav does **not** consume custom roles claims from the JWT.
The user's role lives in the ChartNav `users.role` column
(`admin`, `clinician`, `reviewer`) and is set during user
provisioning. This is intentional — the practice manages
identity at the IdP, ChartNav manages role / org binding inside
the application.

### User provisioning flow

1. Practice IdP issues a user account (e.g. for `dr.lee@practice.example.com`).
2. ChartNav admin (or an automated provisioning step) creates a
   row in `users`:
   - `email = dr.lee@practice.example.com`
   - `role = clinician` (or `admin` / `reviewer`)
   - `organization_id = N` (the practice's org)
   - `is_active = true`
3. The user logs in through the practice's IdP, the IdP returns
   a JWT, the frontend includes `Authorization: Bearer <jwt>`
   on every API call, ChartNav resolves the caller via
   `resolve_caller_from_bearer()` in `apps/api/app/auth.py`.

If a JWT arrives whose `email` does not match an active row in
`users`, ChartNav rejects the request with `401
unknown_user_for_token`. There is **no auto-provisioning**.

### De-provisioning

When a user leaves the practice:

1. The IdP de-provisions the account (revokes refresh tokens,
   disables MFA, etc.).
2. The ChartNav admin marks the row in `users` as
   `is_active = false` (or via the admin API).
3. Existing tokens still validate against JWKS until they
   expire — short token lifetimes (≤ 1 hour) mitigate this.
   ChartNav additionally rejects inactive users.

---

## Roles inside ChartNav

ChartNav's authorization model is `(role × organization)`:

| Role | Permissions |
|---|---|
| `admin` | Generate / accept / dismiss / complete every artifact in the org. Manage users in the org. |
| `clinician` | Generate / accept / dismiss / complete every artifact in the org. **Cannot** manage users. |
| `reviewer` | **Read-only** across every clinical surface. Write attempts return `403 role_forbidden`. |

The role mapping is enforced in:

- `apps/api/app/authz.py` — role gate decorators.
- Per-resource handlers (e.g. `apps/api/app/api/scribe_sessions.py`)
  call `require_caller(role={"admin", "clinician"})` for write
  surfaces.
- `apps/api/tests/test_rbac.py` — eight tests covering admin /
  clinician / reviewer write attempts on encounters, events,
  workflow transitions, and review completion.

### Cross-organization isolation

Patient resolution always filters by the caller's
`organization_id` first. A request from an admin in org 1 for a
patient in org 2 returns `404 patient_not_found` (no existence
leak, no role-error leak).

This is enforced by:

- Per-resource SELECTs that always include `organization_id =
  :org` in the WHERE clause.
- `apps/api/tests/test_auth.py`,
  `apps/api/tests/test_patients.py`, and per-resource test
  files exercise the cross-org path.

---

## Failure modes that ChartNav rejects

The `bearer` path rejects (with `401`) any of the following:

| Failure | Test |
|---|---|
| Missing `Authorization` header | `test_bearer_missing_token` |
| Malformed `Authorization` header | `test_bearer_malformed_header` |
| Garbage / unsigned token | `test_bearer_garbage_token` |
| Wrong issuer | `test_bearer_wrong_issuer` |
| Wrong audience | `test_bearer_wrong_audience` |
| Expired token | `test_bearer_expired` |
| Token resolves to no `users` row | `test_bearer_unknown_user` |
| Token has no user-identity claim | `test_bearer_missing_user_claim` |

All eight tests live in `apps/api/tests/test_auth_modes.py` and
run on every CI commit.

The app **refuses to import** in `bearer` mode if any of the
three JWT env vars (`CHARTNAV_JWT_ISSUER`,
`CHARTNAV_JWT_AUDIENCE`, `CHARTNAV_JWT_JWKS_URL`) are missing.
This is intentional — there is no silent fallback to `header`.

---

## Why `header` mode is local-only

`header` mode reads `X-User-Email` and trusts whatever value
arrives. Anyone on the network can pretend to be any user. This
is appropriate for:

- Local fake-data developer workflows.
- CI smoke tests against a seeded SQLite DB.
- The `staging` environment when no PHI is present.

It is **never** appropriate for any environment that may handle
real PHI. The validator
(`scripts/validate_controlled_pilot_env.sh`) **fails** if
`CHARTNAV_AUTH_MODE` is anything other than `bearer` in a
controlled-pilot env.

---

## Operator pre-flight before booking a real-PHI session

Run, in order:

1. `bash scripts/validate_controlled_pilot_env.sh` — must report
   `PASSED`.
2. Confirm the practice's IdP issues tokens with the expected
   `iss`, `aud`, and user claim.
3. Issue a test JWT for one staff account and run
   `bash scripts/smoke_controlled_pilot.sh` (Phase 18.8) — admin
   / clinician / reviewer surfaces should respond appropriately.
4. Verify cross-org isolation against a designated pilot test org
   (the smoke script supports a `CHARTNAV_SMOKE_TEST_ORG_ID`).
5. Walk the controlled-pilot go-live checklist
   (`docs/pilot/chartnav-controlled-pilot-go-live-checklist.md`).
6. Get **written practice approval** before booking a real-PHI
   start date.

---

## What is forbidden

- Running `header` auth in any PHI environment.
- Auto-provisioning users from a JWT without an explicit row in
  `users`.
- Passing a JWT without `iss`, `aud`, and `exp` claims.
- Using JWKS over plain HTTP.
- Wildcard `CHARTNAV_CORS_ALLOW_ORIGINS=*`.
- Reusing dev placeholder credentials (`chartnav:chartnav` in
  `DATABASE_URL`).
- Echoing tokens or passwords in logs / scripts.

---

## What this doc is NOT

- **Not** a HIPAA compliance attestation.
- **Not** a SOC 2 attestation.
- **Not** a certified-EHR claim.
- **Not** practice approval. The practice's security / compliance
  reviewer must accept the security review packet
  (`docs/pilot/chartnav-security-review-packet.md`) and sign off
  in writing.
- **Not** a substitute for the BAA. The BAA must be executed
  before any real PHI moves through ChartNav.
