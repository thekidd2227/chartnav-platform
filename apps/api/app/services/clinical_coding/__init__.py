"""Clinical Coding Intelligence service package.

Public surface:
    run_sync                     — end-to-end ingestion pipeline
    resolve_version_for_date     — date-of-service → version row
    active_version               — currently-preferred version row
    search_codes                 — code/description search
    get_code_detail              — one-row lookup + relationships
    list_specialty_bundles       — ophthalmology quick-picks
    list_favorites / upsert_favorite / remove_favorite
    list_sync_jobs
    ALL_SPECIALTY_TAGS
"""
from .ingest import run_sync, list_sync_jobs
from .query import (
    resolve_version_for_date,
    active_version,
    search_codes,
    get_code_detail,
)
from .specialty import (
    ALL_SPECIALTY_TAGS,
    list_specialty_bundles,
    specialty_bundle_codes,
)
from .favorites import (
    list_favorites,
    upsert_favorite,
    remove_favorite,
)

__all__ = [
    "run_sync", "list_sync_jobs",
    "resolve_version_for_date", "active_version",
    "search_codes", "get_code_detail",
    "ALL_SPECIALTY_TAGS", "list_specialty_bundles", "specialty_bundle_codes",
    "list_favorites", "upsert_favorite", "remove_favorite",
]
