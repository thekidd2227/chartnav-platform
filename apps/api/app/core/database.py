"""Compatibility shim: async session provider backed by app.config settings."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

_url = getattr(settings, "database_url", "sqlite+aiosqlite:///./chartnav.db")
_async_url = _url.replace("sqlite:///", "sqlite+aiosqlite:///") \
    if _url.startswith("sqlite:///") else _url

_engine = create_async_engine(_async_url, echo=False)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        yield session

__all__ = ["get_async_session"]
