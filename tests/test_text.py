import asyncio

import pytest


async def test_text_roundtrip(client):
    r = await client.post("/api/v1/text", json={"content": "hello", "ttl_minutes": 5})
    assert r.status_code == 201
    body = r.json()
    assert len(body["id"]) == 5 and body["ttl_seconds"] == 300
    assert body["url"] == f"https://sher.test/{body['id']}"

    got = await client.get(f"/api/v1/{body['id']}")
    assert got.status_code == 200
    data = got.json()
    assert data["type"] == "text" and data["content"] == "hello"
    assert 0 < data["seconds_remaining"] <= 300


async def test_unicode_text(client):
    r = await client.post("/api/v1/text", json={"content": "नमस्ते 🌏", "ttl_minutes": 10})
    got = await client.get(f"/api/v1/{r.json()['id']}")
    assert got.json()["content"] == "नमस्ते 🌏"


@pytest.mark.parametrize("payload", [{"content": ""}, {"content": "   \n"}, {}])
async def test_empty_or_missing_text_rejected(client, payload):
    r = await client.post("/api/v1/text", json=payload)
    assert r.status_code == 422
    assert "error" in r.json()


async def test_invalid_ttl_rejected(client):
    r = await client.post("/api/v1/text", json={"content": "x", "ttl_minutes": 60})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_ttl"


async def test_text_too_large(client):
    r = await client.post("/api/v1/text", json={"content": "a" * 2000})
    assert r.status_code == 413


async def test_unknown_and_malformed_ids_look_identical(client):
    a = await client.get("/api/v1/abcde")
    b = await client.get("/api/v1/..%2Fetc")
    c = await client.get("/api/v1/ZZZZZ")
    assert a.status_code == b.status_code == c.status_code == 404
    assert a.json() == b.json() == c.json()


async def test_expiry(client, redis):
    r = await client.post("/api/v1/text", json={"content": "bye"})
    sid = r.json()["id"]
    await redis.pexpire(f"share:{sid}", 100)
    await asyncio.sleep(0.25)
    assert (await client.get(f"/api/v1/{sid}")).status_code == 404


async def test_id_collision_retries(client, monkeypatch):
    ids = iter(["aaaaa", "aaaaa", "bbbbb"])
    monkeypatch.setattr("app.services.store.generate_id", lambda n: next(ids))
    first = await client.post("/api/v1/text", json={"content": "one"})
    second = await client.post("/api/v1/text", json={"content": "two"})
    assert first.json()["id"] == "aaaaa" and second.json()["id"] == "bbbbb"
    assert (await client.get("/api/v1/aaaaa")).json()["content"] == "one"


async def test_id_space_exhausted(client, monkeypatch):
    monkeypatch.setattr("app.services.store.generate_id", lambda n: "ccccc")
    await client.post("/api/v1/text", json={"content": "one"})
    r = await client.post("/api/v1/text", json={"content": "two"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "id_space_busy"
