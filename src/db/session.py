"""Async PostgreSQL connection management."""
from contextlib import asynccontextmanager
import os

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Initialize the shared asyncpg pool when DATABASE_URL is configured."""
    global _pool
    if _pool is not None:
        return
    if not DATABASE_URL:
        return
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


async def close_pool() -> None:
    """Close the shared asyncpg pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db():
    """Yield a database connection for direct ``async with`` usage."""
    if _pool is None:
        await init_pool()
    if _pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with _pool.acquire() as conn:
        yield conn


async def get_db_dep():
    """FastAPI dependency that yields a database connection."""
    if _pool is None:
        await init_pool()
    if _pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    async with _pool.acquire() as conn:
        yield conn


async def get_optional_db_dep():
    """FastAPI dependency that yields None when DATABASE_URL is not configured."""
    if _pool is None:
        await init_pool()
    if _pool is None:
        yield None
        return
    async with _pool.acquire() as conn:
        yield conn
