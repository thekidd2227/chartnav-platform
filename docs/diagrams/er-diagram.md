# ER Diagram

```mermaid
erDiagram
  organizations ||--o{ locations        : "has"
  organizations ||--o{ users            : "employs (identity + role)"
  organizations ||--o{ encounters       : "owns"
  locations     ||--o{ encounters       : "hosts"
  encounters    ||--o{ workflow_events  : "emits"

  security_audit_events {
    int id PK
    string event_type
    string request_id
    string actor_email
    int actor_user_id
    int organization_id
    string path
    string method
    string error_code
    text detail
    string remote_addr
    datetime created_at
  }

  organizations {
    int id PK
    string name
    string slug UK
    datetime created_at
  }
  locations {
    int id PK
    int organization_id FK
    string name
    datetime created_at
  }
  users {
    int id PK
    int organization_id FK
    string email UK
    string full_name
    string role "admin | clinician | reviewer"
    datetime created_at
  }
  encounters {
    int id PK
    int organization_id FK
    int location_id FK
    string patient_identifier
    string patient_name
    string provider_name
    string status
    datetime scheduled_at
    datetime started_at
    datetime completed_at
    datetime created_at
  }
  workflow_events {
    int id PK
    int encounter_id FK
    string event_type
    text event_data
    datetime created_at
  }
```

## Seeded tenants & users

| org_id | slug               | email                    | role      |
|--------|--------------------|--------------------------|-----------|
| 1      | `demo-eye-clinic`  | admin@chartnav.local     | admin     |
| 1      | `demo-eye-clinic`  | clin@chartnav.local      | clinician |
| 1      | `demo-eye-clinic`  | rev@chartnav.local       | reviewer  |
| 2      | `northside-retina` | admin@northside.local    | admin     |
| 2      | `northside-retina` | clin@northside.local     | clinician |

`users.email` is the authentication key consumed from `X-User-Email`.
`users.role` is the RBAC key consumed by `app.authz`.
`users.organization_id` is the authoritative source of scope; never
derived from client input.
