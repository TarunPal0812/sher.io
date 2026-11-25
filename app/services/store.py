"""Redis-backed share store. Redis TTL is the single source of truth for expiry."""

from datetime import UTC, datetime

from redis.asyncio import Redis

from ..schemas import ShareRecord
from .ids import generate_id, is_valid_id


class IdSpaceExhausted(Exception):
    pass


def _key(share_id: str) -> str:
    return f"share:{share_id}"


class ShareStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def reserve(
        self, record: ShareRecord, ttl_seconds: int, id_length: int, attempts: int = 5
    ) -> str:
        """Atomically claim an unused ID (SET NX EX) and store the record."""
        payload = record.model_dump_json()
        for _ in range(attempts):
            share_id = generate_id(id_length)
            if await self.redis.set(_key(share_id), payload, nx=True, ex=ttl_seconds):
                return share_id
        raise IdSpaceExhausted

    async def get(self, share_id: str) -> ShareRecord | None:
        if not is_valid_id(share_id):
            return None
        raw = await self.redis.get(_key(share_id))
        if raw is None:
            return None
        record = ShareRecord.model_validate_json(raw)
        if record.expires_at <= datetime.now(UTC):
            return None
        return record

    async def exists(self, share_id: str) -> bool:
        return bool(await self.redis.exists(_key(share_id)))

    async def delete(self, share_id: str) -> None:
        await self.redis.delete(_key(share_id))
