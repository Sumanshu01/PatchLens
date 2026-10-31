"""Configuration and runtime settings for the PatchLens API."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    """Application settings and environment configuration."""

    project_name: str = "PatchLens"
    version: str = "0.1.0"
    api_prefix: str = "/api"

    # Database
    database_url: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./patchlens.db"),
        description="SQLAlchemy database connection URL",
    )

    # File uploads & storage
    upload_dir: Path = Field(
        default=Path(os.getenv("PATCHLENS_UPLOAD_DIR", str(BASE_DIR / "uploads"))),
        description="Directory for temporary uploaded binary files",
    )
    max_upload_size_mb: int = Field(
        default=int(os.getenv("PATCHLENS_MAX_UPLOAD_MB", "50")),
        description="Maximum allowed binary file size in megabytes",
    )

    # Queue & Worker
    redis_url: str = Field(
        default=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        description="Redis broker URL for RQ workers",
    )
    use_redis: bool = Field(
        default=os.getenv("USE_REDIS", "false").lower() in ("1", "true", "yes"),
        description="Whether to use Redis RQ worker instead of in-process pool",
    )
    analysis_timeout_seconds: int = Field(
        default=int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "180")),
        description="Maximum execution timeout for binary analysis job",
    )

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ]


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
