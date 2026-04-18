# API / Data Flow & CI

## UI → Backend request path

```mermaid
sequenceDiagram
  autonumber
  participant U as Operator (browser)
  participant W as apps/web (App.tsx + api.ts)
  participant Cfg as app.config
  participant Authn as require_caller
  participant Authz as authz gate
  participant R as Route handler
  participant SM as State Machine
  participant DB as SA Core → SQLite / Postgres

  U->>W: pick identity · change filter · click transition
  W->>Authn: fetch with X-User-Email: admin@chartnav.local
  Cfg-->>Authn: auth_mode=header
  Authn->>DB: SELECT user WHERE email=:email
  DB-->>Authn: {role, org}
  Authn-->>Authz: Caller
  Authz->>R: Caller
  R->>DB: scoped SQL (:name binds)
  DB-->>R: rows
  R-->>W: 200 + JSON (or 4xx {error_code, reason})
  W-->>U: render list · detail · timeline · banner

  Note over W,R: On 4xx, api.ts wraps into ApiError(status, error_code, reason). App.tsx surfaces it verbatim as a banner.
```

## Role-aware transition flow

```mermaid
sequenceDiagram
  autonumber
  participant W as App.tsx
  participant A as api.allowedNextStatuses()
  participant B as POST /encounters/{id}/status
  participant Authz as authz.assert_can_transition

  W->>A: compute buttons for (role, current)
  A-->>W: [next1, next2, ...]  (UI hint only)
  W->>B: POST status=next
  B->>Authz: validate state-machine edge + role edge
  alt allowed
    Authz-->>B: ok
    B-->>W: 200 updated encounter
    W->>W: refresh detail + events + list; green banner
  else role forbidden
    Authz-->>W: 403 role_cannot_transition
    W->>W: red banner; UI affordances unchanged until next refresh
  end
```

## CI gate flow

```mermaid
flowchart TD
  PR[["push / PR"]] --> SQL[backend-sqlite]
  SQL --> PG[backend-postgres]
  SQL --> DK[docker-build]
  SQL --> DOC[docs]

  subgraph "backend-sqlite"
    A1[pip install -e .dev,postgres] --> A2[alembic upgrade]
    A2 --> A3[seed x2]
    A3 --> A4[pytest 28]
    A4 --> A5[scripts/verify.sh]
  end

  subgraph "backend-postgres (service: postgres:16-alpine)"
    B1[install] --> B2[alembic upgrade]
    B2 --> B3[seed x2]
    B3 --> B4[boot + smoke]
    B4 --> B5[live status transition]
  end

  subgraph "docker-build"
    D1[buildx build] --> D2[run container]
    D2 --> D3[smoke]
  end

  subgraph "docs"
    X1[apt chromium] --> X2[build_docs.py]
    X2 --> X3[upload artifact]
  end
```

## Bearer mode + audit trail (phase 10)

```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant RID as RequestIdMiddleware
  participant Rate as RateLimitMiddleware
  participant Authn as require_caller (bearer)
  participant JWKS as JWKS URL (PyJWKClient)
  participant R as Route
  participant EH as HTTPException handler
  participant Audit as security_audit_events

  C->>RID: GET /me<br/>Authorization: Bearer <jwt>
  RID->>Rate: request + request.state.request_id
  Rate->>Authn: request (within window)
  Authn->>JWKS: get_signing_key_from_jwt(token)
  JWKS-->>Authn: public key
  Authn->>Authn: jwt.decode — sig + iss + aud + exp
  alt invalid token / iss / aud / expired / missing claim / unknown user
    Authn-->>EH: HTTPException(status=401, error_code=...)
    EH->>Audit: record(event_type, request_id, path, method, remote_addr, ...)
    EH-->>C: 401 + X-Request-ID
  else valid
    Authn->>Authn: SELECT users WHERE email = claim
    Authn-->>R: Caller(user_id, role, organization_id)
    R-->>C: 200 + X-Request-ID
  end
```

## Staging deploy flow (phase 11)

```mermaid
flowchart LR
  Op[Operator] --> Up[scripts/staging_up.sh]
  Up --> V[docker compose config]
  V --> UP[docker compose up -d]
  UP --> API[api container<br/>pinned ghcr.io/.../chartnav-api:$TAG]
  UP --> DB[(postgres:16-alpine)]
  API --> E[entrypoint.sh<br/>alembic upgrade + uvicorn]
  E --> Ready["HEALTHCHECK<br/>GET /ready"]
  Ready -->|ok| Proxy[reverse proxy]
  Op --> Verify[scripts/staging_verify.sh]
  Verify -->|health · ready · metrics · 401 · x-request-id · mutation · audit signal| API

  Op -. bad tag .-> Rollback[scripts/staging_rollback.sh PREV_TAG]
  Rollback --> RP[rewrite CHARTNAV_IMAGE_TAG]
  RP --> UPapi[docker compose up -d api]
  UPapi --> Ready
```

## Release pipeline

```mermaid
flowchart LR
  TAG[["git push tag v*.*.*"]] --> RB[release.yml]
  RB --> V[resolve version]
  V --> DK[docker buildx push<br/>ghcr.io/.../chartnav-api:version + :latest]
  V --> RBS[scripts/release_build.sh]
  RBS --> API[chartnav-api-&lt;v&gt;.tar]
  RBS --> WEB[chartnav-web-&lt;v&gt;.tar.gz]
  RBS --> M[MANIFEST.txt]
  API --> GR[GitHub Release]
  WEB --> GR
  M --> GR
  DK --> OPS[operator: docker pull + compose up]
  GR --> OPS
```
