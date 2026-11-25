from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["ops"])


@router.get("/healthz")
async def healthz():
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request):
    """Readiness: Redis reachable and storage directory writable."""
    problems = []
    try:
        await request.app.state.redis.ping()
    except Exception:
        problems.append("redis")
    root = request.app.state.settings.storage_dir
    probe = root / ".tmp" / ".ready"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok")
        probe.unlink()
    except OSError:
        problems.append("storage")
    if problems:
        return JSONResponse({"status": "unavailable", "failing": problems}, 503)
    return {"status": "ready"}
