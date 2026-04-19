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
  encounters    ||--o{ encounter_inputs : "captures (phase 19)"
  encounters    ||--o{ extracted_findings: "extracted for (phase 19)"
  encounters    ||--o{ note_versions    : "drafts + signs (phase 19)"
  encounter_inputs  ||--o{ extracted_findings : "source of"
  encounter_inputs  ||--o{ note_versions      : "source of"
  extracted_findings||--o{ note_versions      : "feeds"

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
    string external_ref "nullable — vendor id for bridged encounters (phase 21)"
    string external_source "nullable — adapter key (phase 21)"
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
  encounter_inputs {
    int id PK
    int encounter_id FK
    string input_type "audio_upload | text_paste | manual_entry | imported_transcript"
    string processing_status "queued | processing | completed | failed | needs_review"
    text transcript_text "nullable"
    string confidence_summary "nullable"
    text source_metadata "JSON blob"
    int created_by_user_id FK
    int retry_count "phase 22 — monotonic on explicit retry"
    text last_error "phase 22 — nullable; cleared on success"
    string last_error_code "phase 22 — stable error code"
    datetime started_at "phase 22 — nullable"
    datetime finished_at "phase 22 — nullable"
    string worker_id "phase 22 — inline/worker tag"
    string claimed_by "phase 23 — background-worker claim"
    datetime claimed_at "phase 23 — claim timestamp for stale recovery"
    datetime created_at
    datetime updated_at
  }
  extracted_findings {
    int id PK
    int encounter_id FK
    int input_id FK
    text chief_complaint
    text hpi_summary
    string visual_acuity_od
    string visual_acuity_os
    string iop_od
    string iop_os
    text structured_json "JSON: diagnoses[], medications[], plan, follow_up_interval"
    string extraction_confidence "high | medium | low"
    datetime created_at
  }
  note_versions {
    int id PK
    int encounter_id FK
    int version_number "unique per encounter"
    string draft_status "draft | provider_review | revised | signed | exported"
    string note_format "soap | assessment_plan | consult_note | freeform"
    text note_text
    int source_input_id FK
    int extracted_findings_id FK
    string generated_by "system | manual"
    boolean provider_review_required
    text missing_data_flags "JSON array"
    datetime signed_at
    int signed_by_user_id FK
    datetime exported_at
    datetime created_at
    datetime updated_at
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
