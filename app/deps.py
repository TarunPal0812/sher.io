"""FastAPI dependencies: settings, stores, client IP, rate limiting."""

from fastapi import Request
from redis.asyncio import Redis

from .config import Settings
from .errors import ApiError
from .services.files import FileStorage
from .services.store import ShareStore


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_store(request: Request) -> ShareStore:
    return ShareStore(request.app.state.redis)


def get_files(request: Request) -> FileStorage:
    return FileStorage(request.app.state.settings.storage_dir)


def client_ip(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.trust_proxy:
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Fixed-window limiter backed by Redis (INCR + EXPIRE)."""

    def __init__(self, scope: str):
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        import time

        settings: Settings = request.app.state.settings
        limit = (
            settings.rate_limit_upload_per_min
            if self.scope == "upload"
            else settings.rate_limit_view_per_min
        )
        window = 60
        bucket = int(time.time() // window)
        key = f"rl:{self.scope}:{client_ip(request)}:{bucket}"
        redis: Redis = request.app.state.redis
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window + 5)
        if count > limit:
            retry = window - int(time.time() % window)
            raise ApiError(
                429, "rate_limited", "Too many requests. Try again shortly.",
                headers={"Retry-After": str(retry)},
            )
