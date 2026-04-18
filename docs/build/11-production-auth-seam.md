# Production-Auth Seam

## State (after phase 10)

Bearer mode is no longer a placeholder — it performs real JWT validation
against a JWKS endpoint. Header mode is preserved for local/dev.

## Transports

| Mode      | State       | Behavior                                                       |
|-----------|-------------|----------------------------------------------------------------|
| `header`  | implemented | Reads `X-User-Email`, resolves from `users`. Dev only.         |
| `bearer`  | implemented | Reads `Authorization: Bearer <jwt>`, validates signature/iss/aud/exp against `CHARTNAV_JWT_JWKS_URL`, maps to a `users` row by `CHARTNAV_JWT_USER_CLAIM` (default `email`). |

Both produce the same `Caller(user_id, email, full_name, role, organization_id)`.

## JWT validation specifics

Implemented in `apps/api/app/auth.py::resolve_caller_from_bearer`:

1. Parse `Authorization: Bearer <token>`. Missing → 401 `missing_auth_header`. Malformed → 401 `invalid_authorization_header`.
2. Look up the signing key via `PyJWKClient(settings.jwt_jwks_url)` (cached). Failure → 401 `invalid_token`.
3. `jwt.decode(...)` with:
   - Algorithms: `RS256 / RS384 / RS512 / ES256 / ES384 / ES512`
   - `issuer=settings.jwt_issuer`
   - `audience=settings.jwt_audience`
   - `options={"require": ["exp", "iss", "aud"]}`
4. Specific error codes per failure:
   - `token_expired` — `exp` in the past
   - `invalid_issuer` — `iss` mismatch
   - `invalid_audience` — `aud` mismatch
   - `invalid_token` — any other JWT error
5. Pull `settings.jwt_user_claim` (default `email`) out of the claims. Missing / non-string → 401 `missing_user_claim`.
6. `fetch_one` against `users`. Missing → 401 `unknown_user`.

No fallbacks. No "if token looks roughly ok, let it through". Fail closed.

## Claim mapping

`CHARTNAV_JWT_USER_CLAIM` (default `email`) names the claim whose value
is used to look up the `users.email` row. In most OIDC setups that's
exactly `email`; for deployments that use a different claim shape, this
is the single knob to turn.

The internal `users` table remains the authoritative source of
`organization_id` and `role`. Tokens carry identity, not authorization.

## Test hook

`apps/api/app/auth.py::set_jwk_client(client)` lets tests inject a fake
JWKS client. The real `PyJWKClient` is used in production. This is the
only crack in the wall that tests are allowed to poke.

## Bearer-mode test coverage (`tests/test_auth_modes.py`)

| Scenario                                                   | Result |
|------------------------------------------------------------|--------|
| Bearer mode without JWT env → `RuntimeError` at import     | ✅ |
| Header mode default contract unchanged                     | ✅ |
| Valid RS256 token + known user → 200 with role/org         | ✅ |
| Missing Authorization → 401 `missing_auth_header`          | ✅ |
| Non-Bearer scheme → 401 `invalid_authorization_header`     | ✅ |
| Garbage token → 401 `invalid_token`                        | ✅ |
| Wrong issuer → 401 `invalid_issuer`                        | ✅ |
| Wrong audience → 401 `invalid_audience`                    | ✅ |
| Expired token → 401 `token_expired`                        | ✅ |
| Valid token, claim points at unknown user → 401 `unknown_user` | ✅ |
| Valid token missing the configured claim → 401 `missing_user_claim` | ✅ |

Tests generate a local RSA keypair and sign tokens with it, then inject
a lightweight JWKS stub via `set_jwk_client(...)` so no network calls
happen.

## What still isn't covered in this phase

- No JWKS rotation test (we cache aggressively via PyJWKClient).
- No HS256 / shared-secret flow — intentionally; production should be asymmetric.
- No refresh-token dance. ChartNav only validates access tokens.
- No revocation list. If a token needs to be killed before `exp`, the identity provider has to roll the signing key (or the user's `users` row can be deleted, which takes the caller down one hop later).
