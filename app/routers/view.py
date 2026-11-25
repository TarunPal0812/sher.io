"""Read shares: JSON, file download, and the HTML page for /<id>."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..deps import RateLimiter, get_files, get_store
from ..errors import not_found
from ..schemas import ShareRecord, ShareView
from ..services.files import FileStorage
from ..services.ids import is_valid_id
from ..services.store import ShareStore

STATIC = Path(__file__).resolve().parent.parent / "static"

api = APIRouter(prefix="/api/v1", tags=["shares"], dependencies=[Depends(RateLimiter("view"))])
pages = APIRouter(include_in_schema=False)


async def _load(share_id: str, store: ShareStore) -> ShareRecord:
    record = await store.get(share_id)
    if record is None:
        raise not_found()
    return record


@api.get("/{share_id}", response_model=ShareView)
async def get_share(share_id: str, store: ShareStore = Depends(get_store)):
    record = await _load(share_id, store)
    remaining = max(0, int((record.expires_at - datetime.now(UTC)).total_seconds()))
    return ShareView(
        id=share_id,
        type=record.type,
        content=record.content,
        filename=record.filename,
        size=record.size,
        download_url=f"/api/v1/{share_id}/download" if record.type == "file" else None,
        expires_at=record.expires_at,
        seconds_remaining=remaining,
    )


@api.get("/{share_id}/download")
async def download(
    share_id: str,
    store: ShareStore = Depends(get_store),
    files: FileStorage = Depends(get_files),
):
    record = await _load(share_id, store)
    if record.type != "file":
        raise not_found()
    path = files.path_for(share_id)
    if not path.is_file():
        raise not_found()
    return FileResponse(path, filename=record.filename, media_type="application/octet-stream")


@pages.get("/")
async def home():
    return FileResponse(STATIC / "index.html")


@pages.get("/{share_id}")
async def share_page(share_id: str):
    if not is_valid_id(share_id):
        raise not_found()
    return FileResponse(STATIC / "view.html")
