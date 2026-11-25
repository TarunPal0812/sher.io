"""Application settings, loaded from environment variables (prefix ``SHER_``)."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SHER_", extra="ignore")

    base_url: str = Field(
        default="https://sher-5x0c.onrender.com",
        validation_alias=AliasChoices("SHER_BASE_URL", "RENDER_EXTERNAL_URL", "BASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("SHER_REDIS_URL", "REDIS_URL"),
    )
    storage_dir: Path = Path("storage")

    id_length: int = Field(default=5, ge=4, le=8)

    allowed_ttls: tuple[int, ...] = (5, 10)
    default_ttl_minutes: int = 5

    max_text_bytes: int = 100 * 1024
    max_file_bytes: int = 10 * 1024 * 1024

    rate_limit_upload_per_min: int = 20
    rate_limit_view_per_min: int = 60

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
