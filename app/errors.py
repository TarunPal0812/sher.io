"""Uniform error type and response shape: {"error": {"code", "message"}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("sher.errors")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


def not_found() -> ApiError:
    # One message for "never existed" and "expired" so IDs can't be probed.
    return ApiError(404, "not_found", "This link doesn't exist or has expired.")


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message), exc.status, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Routing-level errors (unknown path, wrong method) use the same shape.
        if exc.status_code == 404:
            e = not_found()
            return JSONResponse(_body(e.code, e.message), 404)
        return JSONResponse(
            _body("http_error", str(exc.detail)), exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = f"Invalid {loc}: {first.get('msg', 'bad value')}" if loc else "Invalid request."
        return JSONResponse(_body("validation_error", msg), 422)

    @app.exception_handler(RedisError)
    async def _redis_error(_: Request, exc: RedisError) -> JSONResponse:
        log.error("Redis operation failed: %s", exc)
        return JSONResponse(
            _body("service_unavailable", "Temporary database error. Try again shortly."), 503
        )
