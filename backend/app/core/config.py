"""
Central application configuration using Pydantic Settings.
All environment variables are managed here — never hardcoded throughout the app.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _BACKEND_DIR / ".env"
_ROOT_ENV_PATH = _BACKEND_DIR.parent / ".env"


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=(_ENV_PATH, _ROOT_ENV_PATH, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "Enterprise GTM Intelligence Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    )

    # -------------------------------------------------------------------------
    # Database (SQLite default for zero-setup, or PostgreSQL if configured)
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./gtm_intelligence.db"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # -------------------------------------------------------------------------
    # Gemini API — keep model configurable, never hardcode
    # -------------------------------------------------------------------------
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.1-flash-lite")
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_REQUEST_TIMEOUT: int = 60       # seconds
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_RETRY_DELAY: float = 2.0        # seconds between retries

    # -------------------------------------------------------------------------
    # ChromaDB — local persistent vector storage
    # -------------------------------------------------------------------------
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_data")
    CHROMA_COLLECTION_NAME: str = "gtm_documents"

    # -------------------------------------------------------------------------
    # Embeddings — local sentence-transformers, no paid API
    # -------------------------------------------------------------------------
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32

    # -------------------------------------------------------------------------
    # RAG
    # -------------------------------------------------------------------------
    RAG_TOP_K: int = 8
    RAG_SIMILARITY_THRESHOLD: float = 0.35   # cosine distance; tuned per model
    RAG_MAX_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 64

    # -------------------------------------------------------------------------
    # Website ingestion
    # -------------------------------------------------------------------------
    INGESTION_MAX_PAGES: int = 10
    INGESTION_PAGE_SIZE_LIMIT: int = 1_000_000   # bytes
    INGESTION_REQUEST_TIMEOUT: int = 15
    INGESTION_USER_AGENT: str = (
        "GTMIntelligenceBot/1.0 (+https://github.com/gtm-intelligence-agent)"
    )

    # -------------------------------------------------------------------------
    # CSV upload
    # -------------------------------------------------------------------------
    CSV_MAX_FILE_SIZE: int = 10 * 1024 * 1024   # 10 MB
    CSV_MAX_ROWS: int = 10_000

    # -------------------------------------------------------------------------
    # Scoring weights — deterministic, configurable
    # -------------------------------------------------------------------------
    SCORE_WEIGHT_PRODUCT_FIT: float = 0.35
    SCORE_WEIGHT_ENGAGEMENT: float = 0.25
    SCORE_WEIGHT_GROWTH_SIGNALS: float = 0.20
    SCORE_WEIGHT_CRM_QUALITY: float = 0.20

    SCORE_HIGH_THRESHOLD: int = 80
    SCORE_MEDIUM_THRESHOLD: int = 60

    # -------------------------------------------------------------------------
    # Background jobs
    # -------------------------------------------------------------------------
    JOB_MAX_DURATION: int = 300    # seconds before marking a job as timed out

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    ALLOWED_URL_SCHEMES: List[str] = Field(default=["http", "https"])
    BLOCKED_HOSTS: List[str] = Field(
        default=[
            "localhost", "127.0.0.1", "0.0.0.0", "::1",
            "169.254.169.254",  # AWS metadata
            "metadata.google.internal",
        ]
    )

    @field_validator("GEMINI_API_KEY", mode="before")
    @classmethod
    def warn_missing_key(cls, v: str) -> str:
        if not v:
            # Allow startup without key — agents will return a clear error
            import warnings
            warnings.warn(
                "GEMINI_API_KEY is not set. AI features will not work until it is configured.",
                stacklevel=2,
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()


# Convenience shortcut
settings = get_settings()
