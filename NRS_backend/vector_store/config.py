"""Configuration for the vector store service inside the unified backend."""
from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class VectorSettings(BaseSettings):
    """Vector service configuration class."""

    db_path: str = "./chroma_db"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    HF_TOKEN: Optional[str] = None
    default_top_k: int = 5
    enable_chunking: bool = False
    chunk_size: int = 500
    chunk_overlap: int = 50
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_prefix="VECTOR_",
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


def get_settings() -> VectorSettings:
    return VectorSettings()


default_settings = get_settings()
settings = default_settings
