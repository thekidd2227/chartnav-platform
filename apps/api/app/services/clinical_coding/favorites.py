"""Provider favorite codes — CRUD against provider_favorite_codes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.db import fetch_all, fetch_one, transaction, insert_returning_id


def list_favorites(user_id: int, organization_id: int) -> list[dict]:
    return fetch_all(
        "SELECT id, organization_id, user_id, code, specialty_tag, "
        "usage_count, is_pinned, last_used_at, created_at, updated_at "
        "FROM provider_favorite_codes "
        "WHERE user_id = :u AND organization_id = :org "
        "ORDER BY is_pinned DESC, usage_count DESC, code ASC",
        {"u": user_id, "org": organization_id},
    )


def upsert_favorite(
    user_id: int, organization_id: int, code: str,
    *, specialty_tag: str | None = None, is_pinned: bool | None = None,
    bump_usage: bool = False,
) -> dict:
    code = code.strip().upper()
    existing = fetch_one(
        "SELECT id, usage_count, is_pinned, specialty_tag "
        "FROM provider_favorite_codes WHERE user_id = :u AND code = :c",
        {"u": user_id, "c": code},
    )
    with transaction() as conn:
        if existing:
            updates: dict = {"id": existing["id"], "now": datetime.utcnow()}
            set_parts = ["updated_at = :now"]
            if specialty_tag is not None:
                set_parts.append("specialty_tag = :t"); updates["t"] = specialty_tag
            if is_pinned is not None:
                set_parts.append("is_pinned = :p"); updates["p"] = 1 if is_pinned else 0
            if bump_usage:
                set_parts.append("usage_count = usage_count + 1")
                set_parts.append("last_used_at = :now")
            conn.execute(
                text(f"UPDATE provider_favorite_codes SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )
            fav_id = existing["id"]
        else:
            fav_id = insert_returning_id(
                conn, "provider_favorite_codes",
                {
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "code": code,
                    "specialty_tag": specialty_tag,
                    "usage_count": 1 if bump_usage else 0,
                    "is_pinned": 1 if is_pinned else 0,
                    "last_used_at": datetime.utcnow() if bump_usage else None,
                },
            )
    return fetch_one(
        "SELECT id, organization_id, user_id, code, specialty_tag, "
        "usage_count, is_pinned, last_used_at, created_at, updated_at "
        "FROM provider_favorite_codes WHERE id = :id",
        {"id": fav_id},
    )


def remove_favorite(fav_id: int, user_id: int) -> bool:
    existing = fetch_one(
        "SELECT id FROM provider_favorite_codes WHERE id = :id AND user_id = :u",
        {"id": fav_id, "u": user_id},
    )
    if not existing:
        return False
    with transaction() as conn:
        conn.execute(
            text("DELETE FROM provider_favorite_codes WHERE id = :id"),
            {"id": fav_id},
        )
    return True
