# API Contract

All endpoints are registered in `apps/api/app/api/routes.py` under
the Phase 64 block. Authentication is ChartNav's normal
`X-User-Email` (dev header mode) / JWT bearer (prod). Every route
enforces `ensure_same_org` implicitly through the caller's identity.

## Read surface

### `GET /clinical-coding/version/active`

Returns the currently-preferred `icd10cm_versions` row, or `503
no_icd10cm_version_loaded` if nothing has been ingested yet.

### `GET /clinical-coding/version/by-date?dateOfService=YYYY-MM-DD`

Resolves the correct release for the given date of service. Falls
back to the active version if no release's window contains the date.

### `GET /clinical-coding/search?q=TERM`

Query params:

| Param | Notes |
|---|---|
| `q` (required) | Code prefix (`H40`) or free text (`glaucoma`). |
| `dateOfService` | ISO date; resolves version. |
| `limit` | Default 25, max 100. |
| `specialtyTag` | Optional filter. |
| `billableOnly` | `true` restricts to `is_billable = 1`. |

Response shape:

```json
{
  "version": { "id": 1, "version_label": "...", "source_authority": "CMS", ... },
  "query": "glaucoma",
  "limit": 25,
  "result_count": 12,
  "results": [
    {
      "code": "H40.1110",
      "normalized_code": "H401110",
      "is_billable": 1,
      "short_description": "Primary open-angle glaucoma...",
      "long_description": "Primary open-angle glaucoma, right eye...",
      "chapter_code": "VII",
      "category_code": "H40",
      "parent_code": "H40.111",
      "specificity_flags": "stage_required"
    }
  ]
}
```

### `GET /clinical-coding/code/{code}?dateOfService=...`

Returns one row plus children + matching advisory support hints:

```json
{
  "version": { "version_label": "ICD-10-CM FY2026", ... },
  "code": {
    "code": "H40.1110",
    "long_description": "...",
    "chapter_code": "VII",
    "children": [ { "code": "H40.11101", "short_description": "...", "is_billable": 1 } ],
    "support_hints": [
      {
        "specialty_tag": "glaucoma",
        "workflow_area": "specificity_prompt",
        "advisory_hint": "Primary open-angle glaucoma: document laterality and severity stage...",
        "specificity_prompt": "Laterality: OD / OS / bilateral\nStage: mild / moderate / severe / indeterminate",
        "source_reference": "CDC Official ICD-10-CM Guidelines, Section I.C.7.a"
      }
    ]
  }
}
```

Returns `404 code_not_found` when the code does not exist in the
resolved version.

### `GET /clinical-coding/specialties`

```json
{
  "specialties": ["retina","glaucoma","cataract","cornea","oculoplastics","general"],
  "bundles": [ { "specialty_tag": "glaucoma", "label": "Primary open-angle glaucoma", "pattern": "H40.11%" }, ... ]
}
```

### `GET /clinical-coding/specialty/{tag}/codes?dateOfService=...`

Like `/specialties` but each bundle is pre-expanded into concrete
billable codes that exist in the resolved version. Returns `400
unknown_specialty_tag` for unknown tags.

## Favorites

### `GET /clinical-coding/favorites`

Caller's favorites only. Returns an array of `provider_favorite_codes`
rows.

### `POST /clinical-coding/favorites` — `201`

Body:

```json
{ "code": "H40.1110", "specialty_tag": "glaucoma", "is_pinned": true, "bump_usage": true }
```

Idempotent upsert. `bump_usage=true` increments `usage_count` and
sets `last_used_at`. Returns the persisted row. Reviewer role gets
`403 role_forbidden`.

### `DELETE /clinical-coding/favorites/{id}`

`200 { "deleted": true, "id": N }` when deleted; `deleted: false`
when the caller does not own the row.

## Admin

### `POST /admin/clinical-coding/sync` — `202`

Admin only. Body:

```json
{ "version_label": "ICD-10-CM FY2026", "allow_network": true }
```

Runs the sync pipeline end-to-end. Returns the ingestion result.
`500 sync_failed` with the exception message on parser / fetch
errors.

### `GET /admin/clinical-coding/sync/status`

Admin only. Returns the active version row + the most recent N
(default 10) `coding_sync_jobs` rows.

### `GET /admin/clinical-coding/audit`

Admin only. Returns every `icd10cm_versions` row (including
superseded) plus sync-job history. Checksum is visible.

## Error envelope

All error responses follow ChartNav's standard shape:

```json
{ "detail": { "error_code": "role_forbidden", "reason": "admin only" } }
```
