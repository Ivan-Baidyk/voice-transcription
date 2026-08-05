"""PostgreSQL database layer using asyncpg connection pool."""

import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn=url, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def save_transcription(text: str, user_id: int | None = None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO transcriptions (text, created_at, user_id) VALUES ($1, NOW(), $2)',
            text, user_id,
        )


async def get_transcriptions(user_id: int | None = None, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id is not None:
            rows = await conn.fetch(
                'SELECT text, created_at FROM transcriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2',
                user_id, limit,
            )
        else:
            rows = await conn.fetch(
                'SELECT text, created_at FROM transcriptions ORDER BY created_at DESC LIMIT $1',
                limit,
            )
        return [dict(r) for r in rows]


async def count_user_transcriptions(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT COUNT(*) as cnt FROM transcriptions WHERE user_id = $1',
            user_id,
        )
        return row['cnt'] if row else 0


async def deactivate_user(user_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE users SET is_approved = false WHERE id = $1',
            user_id,
        )


async def get_user_by_id(user_id: int) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT id, email, is_approved FROM users WHERE id = $1',
            user_id,
        )
        return dict(row) if row else None
