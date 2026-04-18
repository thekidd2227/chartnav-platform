# ER Diagram

```mermaid
erDiagram
  organizations ||--o{ locations        : "has"
  organizations ||--o{ users            : "employs (identity + org lens)"
  organizations ||--o{ encounters       : "owns"
  locations     ||--o{ encounters       : "hosts"
  encounters    ||--o{ workflow_events  : "emits"

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
    string role
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

## Dev auth note

`users.email` is the authentication key consumed from the `X-User-Email`
header. `users.organization_id` is the authoritative source of the
caller's organization scope — never derived from body or query params.

## Seeded tenants

| org_id | slug               | admin email             | location_id | encounter_ids |
|--------|--------------------|-------------------------|-------------|---------------|
| 1      | `demo-eye-clinic`  | admin@chartnav.local    | 1           | 1, 2          |
| 2      | `northside-retina` | admin@northside.local   | 2           | 3             |
