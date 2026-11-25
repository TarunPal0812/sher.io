import os
import time

from app.services.cleanup import sweep
from app.services.files import FileStorage
from app.services.ids import generate_id, is_valid_id
from app.services.store import ShareStore


async def test_sweeper_removes_orphans_keeps_live(client, redis, settings):
    live = (await client.post("/api/v1/file", files={"file": ("a", b"1")})).json()["id"]
    dead = (await client.post("/api/v1/file", files={"file": ("b", b"2")})).json()["id"]
    await redis.delete(f"share:{dead}")

    files = FileStorage(settings.storage_dir)
    stale = files.tmp / "stale"
    stale.write_bytes(b"x")
    old = time.time() - 3600
    os.utime(stale, (old, old))

    removed = await sweep(ShareStore(redis), files)
    assert removed == 2
    assert (settings.storage_dir / live).exists()
    assert not (settings.storage_dir / dead).exists()
    assert not stale.exists()


async def test_rate_limit(settings, redis):
    import httpx

    from app.main import create_app

    settings.rate_limit_upload_per_min = 2
    app = create_app(settings, redis)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        codes = []
        for _ in range(3):
            resp = await c.post("/api/v1/text", json={"content": "x"})
            codes.append(resp.status_code)
        last = await c.post("/api/v1/text", json={"content": "x"})
    assert codes == [201, 201, 429]
    assert last.json()["error"]["code"] == "rate_limited" and "retry-after" in last.headers


async def test_security_headers_and_pages(client):
    r = await client.get("/")
    assert r.status_code == 200
    h = r.headers
    assert "default-src 'self'" in h["content-security-policy"]
    assert h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer"
    assert (await client.get("/abcde")).status_code == 200     # valid-format ID: SPA page
    assert (await client.get("/not-an-id")).status_code == 404
    assert (await client.get("/api/v1/abcde")).headers["cache-control"] == "no-store"


async def test_health_and_ready(client):
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    assert (await client.get("/readyz")).json() == {"status": "ready"}


async def test_redis_error_returns_503(client, monkeypatch):
    import redis.exceptions

    from app.services.store import ShareStore

    async def broken_get(*args, **kwargs):
        raise redis.exceptions.ConnectionError("Redis connection lost")

    monkeypatch.setattr(ShareStore, "get", broken_get)
    r = await client.get("/api/v1/abcde")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


async def test_render_memory_fallback(monkeypatch, tmp_path):
    from app.config import Settings
    from app.main import create_app

    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("SHER_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    s = Settings(_env_file=None, storage_dir=tmp_path / "storage")
    app = create_app(s)
    async with app.router.lifespan_context(app):
        assert app.state.redis is not None
        assert await app.state.redis.ping() is True


def test_id_helpers():
    for n in range(4, 9):
        sid = generate_id(n)
        assert len(sid) == n and is_valid_id(sid)
    for bad in ["abc", "abcdefghi", "ABCDE", "../abc", "abcd/", "ab cd"]:
        assert not is_valid_id(bad)
