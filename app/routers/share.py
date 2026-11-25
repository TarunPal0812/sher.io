"""Create shares: POST /api/v1/text and POST /api/v1/file."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..config import Settings
from ..deps import RateLimiter, get_files, get_settings_dep, get_store
from ..errors import ApiError
from ..schemas import ShareCreated, ShareRecord, TextCreate
from ..services.files import EmptyFile, FileStorage, FileTooLarge, sanitize_filename
from ..services.store import IdSpaceExhausted, ShareStore

router = APIRouter(prefix="/api/v1", tags=["shares"])

MULTIPART_OVERHEAD = 1024 * 1024


def _validate_ttl(minutes: int, settings: Settings) -> int:
    if minutes not in settings.allowed_ttls:
        allowed = ", ".join(str(t) for t in settings.allowed_ttls)
        raise ApiError(422, "invalid_ttl", f"ttl_minutes must be one of: {allowed}.")
    return minutes * 60


def _created(share_id: str, ttl_seconds: int, expires_at: datetime, settings: Settings):
    return ShareCreated(
        id=share_id,
        url=f"{settings.base_url.rstrip('/')}/{share_id}",
        expires_at=expires_at,
        ttl_seconds=ttl_seconds,
    )


def _busy() -> ApiError:
    return ApiError(503, "id_space_busy", "Couldn't allocate a link. Try again.")


@router.post(
    "/text",
    status_code=201,
    response_model=ShareCreated,
    dependencies=[Depends(RateLimiter("upload"))],
)
async def create_text(
    body: TextCreate,
    store: ShareStore = Depends(get_store),
    settings: Settings = Depends(get_settings_dep),
):
    ttl = _validate_ttl(body.ttl_minutes, settings)
    if not body.content.strip():
        raise ApiError(422, "empty_content", "Text can't be empty.")
    size = len(body.content.encode("utf-8"))
    if size > settings.max_text_bytes:
        raise ApiError(
            413, "too_large", f"Text is over the {settings.max_text_bytes // 1024} KB limit."
        )
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    record = ShareRecord(type="text", content=body.content, size=size, expires_at=expires_at)
    try:
        share_id = await store.reserve(record, ttl, settings.id_length)
    except IdSpaceExhausted:
        raise _busy() from None
    return _created(share_id, ttl, expires_at, settings)


@router.post(
    "/file",
    status_code=201,
    response_model=ShareCreated,
    dependencies=[Depends(RateLimiter("upload"))],
)
async def create_file(
    request: Request,
    file: UploadFile = File(...),
    ttl_minutes: int = Form(5),
    store: ShareStore = Depends(get_store),
    files: FileStorage = Depends(get_files),
    settings: Settings = Depends(get_settings_dep),
):
    ttl = _validate_ttl(ttl_minutes, settings)
    declared = request.headers.get("content-length")
    limit = settings.max_file_bytes + MULTIPART_OVERHEAD
    if declared and declared.isdigit() and int(declared) > limit:
        raise ApiError(413, "too_large", _too_large_msg(settings))

    try:
        tmp_path, size = await files.save_upload(file, settings.max_file_bytes)
    except FileTooLarge:
        raise ApiError(413, "too_large", _too_large_msg(settings)) from None
    except EmptyFile:
        raise ApiError(422, "empty_content", "The file is empty.") from None

    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    record = ShareRecord(
        type="file", filename=sanitize_filename(file.filename), size=size, expires_at=expires_at
    )
    # Reserve the key first, then move the file into place. A live file therefore
    # always has a live key, which is what makes the cleanup sweeper safe.
    try:
        share_id = await store.reserve(record, ttl, settings.id_length)
    except IdSpaceExhausted:
        files.discard_tmp(tmp_path)
        raise _busy() from None
    except Exception:
        files.discard_tmp(tmp_path)
        raise
    try:
        await files.commit(tmp_path, share_id)
    except OSError:
        files.discard_tmp(tmp_path)
        await store.delete(share_id)
        raise ApiError(500, "storage_error", "Couldn't save the file. Try again.") from None
    return _created(share_id, ttl, expires_at, settings)


def _too_large_msg(settings: Settings) -> str:
    return f"File is over the {settings.max_file_bytes // (1024 * 1024)} MB limit."
