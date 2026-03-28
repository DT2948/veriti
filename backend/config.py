import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    app_name: str = "Veriti API"
    app_description: str = "Privacy-first crisis signal verification"
    version: str = "0.1.0"
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///veriti.db")
    )
    upload_dir: str = Field(default_factory=lambda: os.getenv("UPLOAD_DIR", "uploads"))
    max_upload_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    )
    grid_size_meters: int = Field(
        default_factory=lambda: int(os.getenv("GRID_SIZE_METERS", "500"))
    )
    clustering_time_window_minutes: int = Field(
        default_factory=lambda: int(os.getenv("CLUSTERING_TIME_WINDOW_MINUTES", "30"))
    )
    embedding_similarity_threshold: float = Field(
        default_factory=lambda: float(os.getenv("EMBEDDING_SIMILARITY_THRESHOLD", "0.7"))
    )
    duplicate_hash_threshold: int = Field(
        default_factory=lambda: int(os.getenv("DUPLICATE_HASH_THRESHOLD", "5"))
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
