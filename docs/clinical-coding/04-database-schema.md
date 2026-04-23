# Database Schema

Alembic revision: `c1c2c3c4cc01_clinical_coding_intelligence.py`
(down revision: `f1r2e3m4i5n6` — reminders).

All six tables are scoped to the existing ChartNav DB (SQLite in
dev, Postgres in prod). No cross-database or sharded stores.

## `icd10cm_versions`

One row per official release. Multiple releases may live side by
side; exactly zero or one may be `is_active = 1`.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `version_label` | VARCHAR(64) | Unique per release, e.g. `"ICD-10-CM FY2026"`. |
| `source_authority` | VARCHAR(32) | `"CDC/NCHS"`, `"CMS"`, or `"CMS (local fixture)"` when a fixture supplied the file. |
| `source_url` | VARCHAR(512) | Documented upstream URL even if the current copy came from a fixture. |
| `release_date` | DATE | From the CDC/CMS release notes. |
| `effective_start_date` | DATE | First date of service this release applies to. |
| `effective_end_date` | DATE | Nullable = open-ended. |
| `is_active` | INT | `1` on the currently-preferred default version. |
| `manifest_json` | TEXT | JSON array of `{name, sha256, size}` per retained file. |
| `checksum_sha256` | VARCHAR(64) | SHA-256 of the manifest; any change means the release was re-downloaded. |
| `downloaded_at` | DATETIME | |
| `parsed_at` | DATETIME | |
| `activated_at` | DATETIME | |
| `parse_status` | VARCHAR(32) | `downloaded` / `parsing` / `ready` / `failed` / `superseded`. |

Indexes: `(effective_start_date, effective_end_date)`, `is_active`.

## `icd10cm_codes`

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `version_id` | FK icd10cm_versions | Scoped to one release. |
| `code` | VARCHAR(16) | Decimal-pointed (`H40.1211`). |
| `normalized_code` | VARCHAR(16) | Dot stripped (`H401211`). |
| `is_billable` | INT | `0` for header / category rows, `1` for billable terminals. |
| `short_description` | VARCHAR(256) | |
| `long_description` | TEXT | |
| `chapter_code` / `chapter_title` | VARCHAR | e.g. `VII` / "Diseases of the eye and adnexa". |
| `category_code` | VARCHAR(8) | 3-char category (`H40`). |
| `parent_code` | VARCHAR(16) | Immediate parent in the tabular hierarchy. |
| `specificity_flags` | VARCHAR(128) | Comma-separated UI prompts. |
| `source_file` / `source_line_no` | str / int | Where this record came from for audit. |

Unique: `(version_id, code)`.
Indexes: `(version_id, normalized_code)`, `(version_id, category_code)`.

## `icd10cm_code_relationships`

Parent/child + (future) chapter/category membership graph. Kept in
its own table so the flat code table stays fast to scan.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `version_id` | FK | |
| `parent_code` / `child_code` | VARCHAR(16) | |
| `relationship_type` | VARCHAR(32) | `parent_child` (v1). Reserved: `chapter`, `category`. |

Indexes: `(version_id, parent_code)`, `(version_id, child_code)`.

## `provider_favorite_codes`

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `organization_id` / `user_id` | FK (loose) | org-scoped; unique per `(user_id, code)`. |
| `code` | VARCHAR(16) | |
| `specialty_tag` | VARCHAR(32) | One of the six specialty tags. Nullable. |
| `usage_count` | INT | Bumped by `bump_usage=true` on upsert. |
| `is_pinned` | INT | |
| `last_used_at` / `created_at` / `updated_at` | DATETIME | |

## `coding_sync_jobs`

Audit trail for every sync attempt. Never cleaned automatically.

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `job_type` | VARCHAR(32) | `scheduled` / `manual`. |
| `status` | VARCHAR(32) | `queued` / `running` / `succeeded` / `failed`. |
| `version_id` | FK nullable | Filled once parsing binds to a version row. |
| `started_at` / `completed_at` | DATETIME | |
| `files_downloaded` / `records_parsed` / `bytes_downloaded` | INT | |
| `error_log` | TEXT | Populated on failure. |
| `triggered_by_user_id` | INT nullable | |

Indexes: `(status, created_at)`.

## `ophthalmology_support_rules`

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `specialty_tag` | VARCHAR(32) | One of the six tags. |
| `workflow_area` | VARCHAR(64) | `specificity_prompt` / `claim_support_hint` / `search` / `favorites`. |
| `diagnosis_code_pattern` | VARCHAR(32) | SQL-LIKE pattern, e.g. `H40.11%`. |
| `advisory_hint` | TEXT | Short message shown to the clinician. |
| `specificity_prompt` | TEXT nullable | Bullet prompts (laterality / stage / manifestation). |
| `source_reference` | VARCHAR(256) nullable | "CDC Official ICD-10-CM Guidelines, Section I.C.7" etc. |
| `is_active` | INT | |

Indexes: `specialty_tag`.

## Retention

- `icd10cm_versions` rows are never deleted by the service. An
  operator may set `parse_status='superseded'` to hide a release
  from the UI.
- Raw files in `apps/api/data/icd10cm/raw/` are retained verbatim.
- `coding_sync_jobs` rows are never deleted automatically;
  operators may prune with the existing audit-retention script on
  their own cadence.
