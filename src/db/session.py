"""
DB セッション管理 (asyncpg + コネクションプール)
"""
import os
from contextlib import asynccontextmanager

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/postlift")

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


async def close_pool() -> None:
    if _pool:
        await _pool.close()


@asynccontextmanager
async def get_db():
    if _pool is None:
        await init_pool()
    async with _pool.acquire() as conn:
        yield conn
