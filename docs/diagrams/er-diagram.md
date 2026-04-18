# ER Diagram

```mermaid
erDiagram
  organizations ||--o{ locations        : "has"
  organizations ||--o{ users            : "employs (identity + role)"
  organizations ||--o{ encounters       : "owns"
  organizations ||--o{ patients         : "owns (phase 18, native)"
  organizations ||--o{ providers        : "owns (phase 18, native)"
  locations     ||--o{ encounters       : "hosts"
  patients      ||--o{ encounters       : "subject of (nullable FK)"
  providers     ||--o{ encounters       : "primary provider (nullable FK)"
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
    boolean is_active
    datetime created_at
  }
  users {
    int id PK
    int organization_id FK
    string email UK
    string full_name
    string role "admin | clinician | reviewer (CHECK)"
    boolean is_active
    datetime invited_at
    string invitation_token_hash "sha256 hex, indexed"
    datetime invitation_expires_at
    datetime invitation_accepted_at
    datetime created_at
  }
  encounters {
    int id PK
    int organization_id FK
    int location_id FK
    int patient_id FK "nullable — native linkage (phase 18)"
    int provider_id FK "nullable — native linkage (phase 18)"
    string patient_identifier "display; kept for back-compat"
    string patient_name "display; kept for back-compat"
    string provider_name "display; kept for back-compat"
    string status
    datetime scheduled_at
    datetime started_at
    datetime completed_at
    datetime created_at
  }
  patients {
    int id PK
    int organization_id FK
    string external_ref "nullable — vendor id"
    string patient_identifier "local MRN; unique per org"
    string first_name
    string last_name
    date date_of_birth
    string sex_at_birth
    boolean is_active
    datetime created_at
  }
  providers {
    int id PK
    int organization_id FK
    string external_ref "nullable — vendor id"
    string display_name
    string npi "nullable, 10-digit; unique per org when set"
    string specialty
    boolean is_active
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
