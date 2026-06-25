# Production authentication

ChartNav has two auth transports, gated by `CHARTNAV_AUTH_MODE` (see
`apps/api/app/auth.py`, `apps/api/app/config.py`):

| Mode | Use | Trust |
|---|---|---|
| `header` | **dev/test only** | reads `X-User-Email`, trivially spoofable |
| `bearer` | **staging/production** | validates `Authorization: Bearer <JWT>` against an OIDC IdP |

## Bearer / OIDC validation

In `bearer` mode every request's JWT is validated (PyJWT + `PyJWKClient`):
- **signature** against the IdP JWKS (`CHARTNAV_JWT_JWKS_URL`);
- **issuer** == `CHARTNAV_JWT_ISSUER`;
- **audience** == `CHARTNAV_JWT_AUDIENCE`;
- **expiry** (`exp`) and not-before;
- the caller is mapped to a `users` row by `CHARTNAV_JWT_USER_CLAIM`
  (default `email`; an immutable `sub` claim mapping is also supported);
- the user must exist, be **active**, and belong to an **organization** with a
  **role** — otherwise the request is rejected.

**MFA is an IdP policy.** ChartNav delegates MFA, password reset, and lockout to
the identity provider; enforce MFA there (e.g. require it on the ChartNav app
registration).

## Startup refusals (fail fast)

`config.py` refuses to construct invalid production settings (`CHARTNAV_ENV=prod`):
- header auth → refused (`bearer` required);
- SQLite `DATABASE_URL` → refused;
- wildcard CORS → refused.

`bearer` mode (any env) requires issuer + audience + JWKS or import fails. A
forged `X-User-Email` header **does not authenticate** in bearer mode — the
header transport code path is not consulted.

## Tests

- `apps/api/tests/test_production_config.py` — prod refuses header/SQLite/wildcard CORS; dev still permits header+SQLite.
- `apps/api/tests/test_auth*.py` / auth-mode tests — forged headers, expired tokens, wrong issuer/audience, unknown/disabled user, cross-org (existing suite).
- `scripts/production/verify_no_dev_auth.py` — gate that header auth / header-trust is off in prod.

## Provisioning / invitations

Organization + first-admin provisioning and staff invitations are
administrative flows (see `docs/deployment/clinic-onboarding.md`); credentials
and MFA live in the IdP, not ChartNav.

## Not yet verified

This documents the implemented controls. It is **not** a security attestation:
penetration testing, IdP hardening review, and a formal auth threat model
remain to be completed and independently verified before any compliance claim.
