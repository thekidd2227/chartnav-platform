# Production-Auth Seam

## Goal

Make auth transport swappable without touching routes or RBAC.

## Where the seam lives

`apps/api/app/auth.py` exposes a single FastAPI dependency:

```python
def require_caller(x_user_email: ..., authorization: ...) -> Caller:
    mode = settings.auth_mode
    if mode == "header":  return resolve_caller_from_header(...)
    if mode == "bearer":  return resolve_caller_from_bearer(...)
    raise ...
```

Both resolvers return the **same** `Caller` contract:

```python
Caller(user_id, email, full_name, role, organization_id)
```

Every route, every RBAC helper, every test depends on `Caller`, not on a
specific header. Changing transports is a one-file edit inside `auth.py`.

## Mode selection

`CHARTNAV_AUTH_MODE` in the environment (see `12-runtime-config.md`):

| Value    | State       | Behavior                                               |
|----------|-------------|--------------------------------------------------------|
| `header` | implemented | Reads `X-User-Email`, looks up `users`. Dev only.      |
| `bearer` | placeholder | Requires `Authorization: Bearer …`; returns 501 because JWT validation is not yet wired. |

Unknown values cause `app.config` to refuse to import — fail fast.

## Bearer mode — honest placeholder

When `CHARTNAV_AUTH_MODE=bearer` is selected, `app.config._load()`
verifies these three values are all present before letting the app come
up at all:

- `CHARTNAV_JWT_ISSUER`
- `CHARTNAV_JWT_AUDIENCE`
- `CHARTNAV_JWT_JWKS_URL`

Missing any one → `RuntimeError` at import time with the list of
missing vars. The app will not start with a half-configured bearer
setup.

When bearer mode is active and fully configured, `resolve_caller_from_bearer`
currently returns:

```
HTTP 501
{"detail": {"error_code": "auth_bearer_not_implemented",
            "reason": "bearer-token validation is not implemented in this phase; set CHARTNAV_AUTH_MODE=header for local dev"}}
```

This is intentional. A future phase will wire real JWT signature
verification (PyJWT + JWKS fetch against `CHARTNAV_JWT_JWKS_URL`,
issuer/audience checks, claim → `users` lookup). When it ships, only
the body of `resolve_caller_from_bearer` changes.

## What production-ready vs not yet implemented

| Component                  | State                                      |
|----------------------------|--------------------------------------------|
| Mode selection + config    | ✅ production-shaped; fails fast on gaps   |
| Standardized error envelope| ✅ `{error_code, reason}` everywhere       |
| Header transport           | ✅ works; dev only, do not expose          |
| Bearer transport           | ⚠ placeholder — returns 501 honestly       |
| JWT signature validation   | ❌ not implemented                         |
| JWKS rotation / cache      | ❌ not implemented                         |
| Token → `users` mapping    | ❌ not implemented (design TBD)            |
| RBAC integration           | ✅ works for any transport via `Caller`    |
| Org scoping integration    | ✅ works for any transport via `Caller`    |

## Tests

`apps/api/tests/test_auth_modes.py`:

- `test_bearer_mode_requires_jwt_env` — setting `CHARTNAV_AUTH_MODE=bearer`
  without issuer/audience/JWKS raises at `import app.config`.
- `test_bearer_mode_refuses_to_serve_traffic` — with JWT config set, bearer
  requests still get a clear 501 `auth_bearer_not_implemented`; missing
  header returns 401 `missing_auth_header`.
- `test_header_mode_unchanged_contract` — header mode (the default) still
  resolves seeded users to the expected role/org.
