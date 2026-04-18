# Known Gaps & Verification Matrix

## Automated verification (this phase)

```
$ cd apps/api && pytest tests/ -v
... 25 passed in 12.39s
```

Every matrix below is now machine-asserted in `apps/api/tests/`.

### Auth (5/5)

| Case                                 | Expected | Result |
|--------------------------------------|----------|--------|
| `/health` open                       | 200      | ✅     |
| `/me` no header                      | 401 `missing_auth_header` | ✅ |
| `/me` empty header                   | 401      | ✅     |
| `/me` unknown email                  | 401 `unknown_user` | ✅ |
| `/me` admin org1                     | 200 role=admin, org=1 | ✅ |

### Scoping (8/8)

| Case                                                 | Expected | Result |
|------------------------------------------------------|----------|--------|
| `/organizations` scoped per tenant                   | 1 row each | ✅ |
| `/organizations` no auth                             | 401      | ✅     |
| `/locations` scoped                                  | caller org only | ✅ |
| `/users` scoped                                      | caller org only | ✅ |
| `/encounters` disjoint per tenant                    | no overlap | ✅ |
| Cross-org `GET /encounters/{id}`                     | 404      | ✅     |
| `?organization_id=<other>` lens                      | 403      | ✅     |
| Filter within org (`?status=`)                        | no leakage | ✅ |

### RBAC (12/12)

| Case                                                     | Expected | Result |
|----------------------------------------------------------|----------|--------|
| Admin creates encounter                                  | 201      | ✅     |
| Clinician creates encounter                              | 201      | ✅     |
| Reviewer creates encounter                               | 403 `role_cannot_create_encounter` | ✅ |
| Reviewer adds event                                      | 403 `role_cannot_create_event` | ✅ |
| Clinician: in_progress→draft_ready                       | 200      | ✅     |
| Clinician: review_needed→completed                       | 403 `role_cannot_transition` | ✅ |
| Reviewer: review_needed→completed                        | 200      | ✅     |
| Reviewer: review_needed→draft_ready (kick back)          | 200      | ✅     |
| Cross-org mutate                                         | 404      | ✅     |
| Invalid transition (admin: in_progress→completed)        | 400 `invalid_transition` | ✅ |
| `status_changed` event written with `changed_by`         | event count +1 | ✅ |
| Cross-org create body mismatch                           | 403 `cross_org_access_forbidden` | ✅ |

## Real gaps (prioritized for next phase)

1. **Transport still dev-only.** `X-User-Email` is spoofable. Swap to a signed token path via `CHARTNAV_AUTH_MODE`. The seam is in place; the dependency only needs a new branch.
2. **No user/org metadata writes.** `/organizations`, `/locations`, `/users` are read-only. Admins can't invite users, create locations, or edit their own org metadata through the API. Needs RBAC-gated write endpoints.
3. **Role constraint is app-layer only.** `users.role` is a free VARCHAR. Next migration could add a CHECK constraint or a lookup table.
4. **No pagination / cursor** on `GET /encounters`.
5. **No encounter update / delete / cancel** path; no `cancelled` status.
6. **Free-form `event_data`**. No per-`event_type` schema validation.
7. **Raw `sqlite3`** per-request connections. Postgres parity (docker compose) untested.
8. **CORS `allow_origins=["*"]`** — tighten before any hosted deploy.
9. **No distinct audit log.** Auth failures and scoping violations are not persisted; only successful workflow events are.
10. **No rate limiting, no lockout, no observability.**
11. **No CI.** Tests exist but aren't yet run on every PR.
