import fakeredis.aioredis
import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        storage_dir=tmp_path / "storage",
        base_url="https://sher.test",
        id_length=5,
        max_file_bytes=64 * 1024,
        max_text_bytes=1024,
        rate_limit_upload_per_min=1000,
        rate_limit_view_per_min=1000,
    )


@pytest.fixture
def redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def app(settings, redis):
    return create_app(settings, redis)


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
