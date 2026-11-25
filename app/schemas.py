from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TextCreate(BaseModel):
    content: str = Field(min_length=1)
    ttl_minutes: int = 5


class ShareRecord(BaseModel):
    """What is persisted in Redis under ``share:<id>`` (the ID is the key)."""

    type: Literal["text", "file"]
    content: str | None = None
    filename: str | None = None
    size: int
    expires_at: datetime


class ShareCreated(BaseModel):
    id: str
    url: str
    expires_at: datetime
    ttl_seconds: int


class ShareView(BaseModel):
    id: str
    type: Literal["text", "file"]
    content: str | None = None
    filename: str | None = None
    size: int
    download_url: str | None = None
    expires_at: datetime
    seconds_remaining: int
