"""Database access layer — SQLAlchemy Core, cross-dialect.

Exposes:
    engine            SA Engine built from settings.database_url.
    transaction()     Context manager yielding a transactional connection
                      (auto-commit on success, rollback on exception).
    fetch_all(sql,params)
    fetch_one(sql,params)

All SQL uses **named** bind parameters (`:name`) so the same statement
runs on SQLite *and* PostgreSQL. Keep database-specific functions out of
query strings — use portable SQL (`COALESCE` not `IFNULL`, etc.).

Rows are returned as plain `dict`s — never leak `Row` objects past this
module so callers don't acquire a hidden dependency on SA internals.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from app.config import settings

engine: Engine = create_engine(
    settings.database_url,
    future=True,
    # SQLite with threads needs this; Postgres ignores it.
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
)

# Enable foreign key enforcement on SQLite (Postgres does this by default).
if settings.database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys = ON")


def is_sqlite() -> bool:
    return engine.url.get_backend_name() == "sqlite"


def is_postgres() -> bool:
    return engine.url.get_backend_name().startswith("postgres")


@contextmanager
def transaction() -> Iterator[Connection]:
    """Yield a transactional connection. Commits on normal exit,
    rolls back on exception."""
    with engine.begin() as conn:
        yield conn


def fetch_all(sql: str, params: Optional[dict[str, Any]] = None) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(r) for r in rows]


def fetch_one(sql: str, params: Optional[dict[str, Any]] = None) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row else None


def insert_returning_id(
    conn: Connection, table: str, values: dict[str, Any]
) -> int:
    """Insert a row and return its new primary key `id`.

    Uses `RETURNING id` where supported; falls back to
    `cursor.lastrowid` on SQLite.
    """
    cols = ", ".join(values.keys())
    placeholders = ", ".join(f":{k}" for k in values.keys())
    if is_postgres():
        result = conn.execute(
            text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) RETURNING id"),
            values,
        )
        return int(result.scalar_one())
    else:
        cur = conn.execute(
            text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"),
            values,
        )
        return int(cur.lastrowid)
