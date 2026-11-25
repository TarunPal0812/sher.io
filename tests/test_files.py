import os

import pytest

from app.services.files import sanitize_filename

DATA = os.urandom(10_000)


async def upload(client, name="report.bin", data=DATA, ttl="5"):
    return await client.post(
        "/api/v1/file", files={"file": (name, data)}, data={"ttl_minutes": ttl}
    )


async def test_file_roundtrip_is_byte_identical(client, settings):
    r = await upload(client)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert (settings.storage_dir / sid).is_file()

    meta = (await client.get(f"/api/v1/{sid}")).json()
    assert meta["type"] == "file" and meta["filename"] == "report.bin"
    assert meta["size"] == len(DATA) and meta["download_url"] == f"/api/v1/{sid}/download"

    dl = await client.get(meta["download_url"])
    assert dl.status_code == 200 and dl.content == DATA
    assert dl.headers["content-disposition"].startswith("attachment")
    assert dl.headers["content-type"] == "application/octet-stream"
    assert dl.headers["x-content-type-options"] == "nosniff"


async def test_html_upload_is_never_served_inline(client):
    r = await upload(client, "evil.html", b"<script>alert(1)</script>")
    dl = await client.get(r.json()["id"].join(["/api/v1/", "/download"]))
    assert dl.headers["content-type"] == "application/octet-stream"
    assert dl.headers["content-disposition"].startswith("attachment")


async def test_oversize_file_rejected_and_leaves_nothing(client, settings):
    r = await upload(client, data=b"x" * (settings.max_file_bytes + 1))
    assert r.status_code == 413
    assert list(settings.storage_dir.glob("[0-9a-f]*")) == []
    assert list((settings.storage_dir / ".tmp").iterdir()) == []


async def test_empty_file_rejected(client, settings):
    r = await upload(client, data=b"")
    assert r.status_code == 422
    assert list((settings.storage_dir / ".tmp").iterdir()) == []


async def test_bad_ttl_on_file(client):
    assert (await upload(client, ttl="99")).status_code == 422


async def test_traversal_filename_is_neutralised(client, settings):
    r = await upload(client, name="../../etc/passwd")
    sid = r.json()["id"]
    assert (await client.get(f"/api/v1/{sid}")).json()["filename"] == "passwd"
    assert (settings.storage_dir / sid).is_file()
    assert not (settings.storage_dir.parent / "etc").exists()


async def test_download_of_text_share_is_404(client):
    sid = (await client.post("/api/v1/text", json={"content": "t"})).json()["id"]
    assert (await client.get(f"/api/v1/{sid}/download")).status_code == 404


async def test_download_after_expiry_even_if_file_lingers(client, redis, settings):
    sid = (await upload(client)).json()["id"]
    await redis.delete(f"share:{sid}")
    assert (settings.storage_dir / sid).exists()
    assert (await client.get(f"/api/v1/{sid}/download")).status_code == 404


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\a.txt", "a.txt"),
        ('we"ird<>.txt', "weird.txt"),
        ("   ...  ", "file"),
        ("", "file"),
        (None, "file"),
        ("a" * 500 + ".txt", "a" * 120),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected
