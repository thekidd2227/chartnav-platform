# API / Data Flow & CI

## Request path (happy + denial)

```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant Authn as require_caller
  participant Authz as authz gate
  participant R as Route handler
  participant SM as State Machine
  participant DB as SQLite

  Note over C,DB: Happy path — clinician advances own encounter
  C->>Authn: POST /encounters/1/status {"status":"draft_ready"}<br/>X-User-Email: clin@chartnav.local
  Authn->>DB: SELECT user
  DB-->>Authn: {role=clinician, org=1}
  Authn-->>Authz: Caller
  Authz->>Authz: role in {admin, clinician}? ✓
  Authz-->>R: Caller
  R->>DB: SELECT encounter 1
  DB-->>R: row(org=1, status=in_progress)
  R->>SM: is (in_progress → draft_ready) allowed?
  SM-->>R: yes
  R->>Authz: assert_can_transition(clinician, in_progress, draft_ready)
  Authz-->>R: allowed
  R->>DB: UPDATE + INSERT status_changed{changed_by=clin@...}
  R-->>C: 200

  Note over C,DB: Role denied — clinician tries review-stage edge
  C->>Authn: POST /encounters/2/status {"status":"completed"}
  Authn-->>Authz: Caller(role=clinician)
  Authz->>SM: edge valid?
  SM-->>Authz: yes
  Authz->>Authz: clinician in role-set for (review_needed, completed)?
  Authz-->>C: 403 role_cannot_transition

  Note over C,DB: Cross-org read — 404
  C->>Authn: GET /encounters/3 as clin@chartnav.local
  R->>DB: SELECT encounter 3
  DB-->>R: row(org=2)
  R-->>C: 404 encounter_not_found

  Note over C,DB: Missing / unknown identity
  C->>Authn: GET /encounters (no header) → 401 missing_auth_header
  C->>Authn: GET /encounters (bogus email) → 401 unknown_user
```

## CI gate flow

```mermaid
flowchart TD
  PR[["push / PR"]]
  subgraph backend job
    A[checkout] --> B[setup-python 3.11]
    B --> C["pip install -e \".[dev]\""]
    C --> D["alembic -x url=... upgrade head<br/>(isolated CI DB)"]
    D --> E["seed twice (idempotency)"]
    E --> F["pytest tests/ -v"]
    F --> G["boot uvicorn + poll /health"]
    G --> H["scripts/smoke.sh"]
  end
  subgraph docs job
    I[checkout] --> J[apt chromium]
    J --> K["python scripts/build_docs.py"]
    K --> L["upload HTML + PDF artifact"]
  end
  PR --> A
  H --> I
  classDef fail fill:#fee,stroke:#c33
  class F,G,H,K,L fail
```

Any failure in a red-bordered step fails CI.
