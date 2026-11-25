"""Application factory. Run with: uvicorn app.main:create_app --factory"""

import asyncio
import contextlib
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from . import __version__
from .config import Settings, get_settings
from .errors import install_error_handlers
from .routers import health, share, view
from .services.cleanup import cleanup_loop
from .services.files import FileStorage

STATIC = Path(__file__).resolve().parent / "static"
log = logging.getLogger("sher")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


def create_app(settings: Settings | None = None, redis: Redis | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    FileStorage(settings.storage_dir).ensure_dirs()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        owns_redis = app.state.redis is None
        if owns_redis:
            app.state.redis = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )
        task = asyncio.create_task(cleanup_loop(app))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            if owns_redis:
                await app.state.redis.aclose()

    docs = "/api/docs" if settings.enable_docs else None
    app = FastAPI(
        title="sher.io",
        version=__version__,
        lifespan=lifespan,
        docs_url=docs,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    app.state.redis = redis
    install_error_handlers(app)

    @app.middleware("http")
    async def harden_and_log(request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response = await call_next(request)
        h = response.headers
        h["X-Request-ID"] = rid
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not (settings.enable_docs and request.url.path.startswith("/api/docs")):
            h["Content-Security-Policy"] = CSP
        if request.url.path.startswith("/api/") or request.url.path in ("/healthz", "/readyz"):
            h["Cache-Control"] = "no-store"
        log.info(
            "rid=%s %s %s -> %d %.1fms",
            rid, request.method, request.url.path, response.status_code,
            (time.perf_counter() - start) * 1000,
        )
        return response

    app.include_router(health.router)
    app.include_router(share.router)
    app.include_router(view.api)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    app.include_router(view.pages)  # last: "/{share_id}" is a catch-all
    return app
