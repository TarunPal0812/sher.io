"""Disk storage for uploaded files. Files are named by share ID only."""

import asyncio
import os
import re
import time
import unicodedata
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from .ids import is_valid_id

CHUNK = 1024 * 1024


class FileTooLarge(Exception):
    pass


class EmptyFile(Exception):
    pass


def sanitize_filename(name: str | None) -> str:
    """Display-only name: no paths, no control or header-hostile characters."""
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r'[\x00-\x1f\x7f"<>|:*?]', "", name).strip(". ")
    return name[:120] or "file"


class FileStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.tmp = self.root / ".tmp"

    def ensure_dirs(self) -> None:
        self.tmp.mkdir(parents=True, exist_ok=True)

    def path_for(self, share_id: str) -> Path:
        if not is_valid_id(share_id):
            raise ValueError("invalid share id")
        return self.root / share_id

    async def save_upload(self, upload: UploadFile, max_bytes: int) -> tuple[Path, int]:
        """Stream the upload to a temp file, enforcing the size cap as we go."""
        self.ensure_dirs()
        tmp_path = self.tmp / uuid.uuid4().hex
        size = 0
        try:
            async with aiofiles.open(tmp_path, "wb") as out:
                while chunk := await upload.read(CHUNK):
                    size += len(chunk)
                    if size > max_bytes:
                        raise FileTooLarge
                    await out.write(chunk)
            if size == 0:
                raise EmptyFile
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return tmp_path, size

    async def commit(self, tmp_path: Path, share_id: str) -> None:
        await asyncio.to_thread(os.replace, tmp_path, self.path_for(share_id))

    def discard_tmp(self, tmp_path: Path) -> None:
        tmp_path.unlink(missing_ok=True)

    def delete(self, share_id: str) -> None:
        self.path_for(share_id).unlink(missing_ok=True)

    def stored_ids(self) -> list[str]:
        if not self.root.exists():
            return []
        return [p.name for p in self.root.iterdir() if p.is_file() and is_valid_id(p.name)]

    def purge_stale_tmp(self, max_age_seconds: int = 600) -> int:
        removed = 0
        if not self.tmp.exists():
            return 0
        cutoff = time.time() - max_age_seconds
        for p in self.tmp.iterdir():
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)
                removed += 1
        return removed
