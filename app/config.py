"""Application settings, loaded from environment variables (prefix ``SHER_``)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SHER_", extra="ignore")

    # Public base URL used when building share links.
    base_url: str = "http://localhost:8000"
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: Path = Path("storage")

    # Share IDs: lowercase hex, 4-8 chars. Longer is safer (see docs/adr/002).
    id_length: int = Field(default=5, ge=4, le=8)

    # Lifetimes the user may pick, in minutes. The default must be one of them.
    allowed_ttls: tuple[int, ...] = (5, 10)
    default_ttl_minutes: int = 5

    max_text_bytes: int = 100 * 1024
    max_file_bytes: int = 10 * 1024 * 1024

    # Fixed-window rate limits, per client IP, per minute.
    rate_limit_upload_per_min: int = 20
    rate_limit_view_per_min: int = 60

    # Only enable behind a proxy that overwrites X-Real-IP (see docs/DEPLOYMENT.md).
    trust_proxy: bool = False

    cleanup_interval_seconds: int = 30
    enable_docs: bool = False
    log_level: str = "INFO"

    @field_validator("default_ttl_minutes")
    @classmethod
    def _default_in_allowed(cls, v: int, info) -> int:  # noqa: ANN001
        allowed = info.data.get("allowed_ttls", ())
        if allowed and v not in allowed:
            raise ValueError("default_ttl_minutes must be one of allowed_ttls")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
