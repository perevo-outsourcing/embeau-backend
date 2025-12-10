"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "EMBEAU API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://embeau:embeau@localhost:5432/embeau"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # External APIs
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    # ML Models (local PyTorch models)
    use_local_models: bool = True
    models_dir: str = "models"
    bisenet_weights: str = "models/79999_iter.pth"
    emotion_model_weights: str = "models/best_densenet121_rafdb.pth"

    # Color Tone API (external fallback)
    color_tone_api_url: str = "http://localhost:8001"

    # RAG System
    rag_pdf_path: str = "data/color.pdf"
    rag_similarity_threshold: float = 0.64

    # Logging (for research paper)
    log_user_actions: bool = True
    log_retention_days: int = 365  # Keep logs for 1 year for research


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
