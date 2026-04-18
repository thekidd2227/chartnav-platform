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
