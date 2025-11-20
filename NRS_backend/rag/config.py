"""Configuration helpers for the RAG module."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    """Environment-driven configuration for the RAG workflow."""

    vector_service_url: str | None = Field(
        default=None,
        alias="VECTOR_SERVICE_URL",
        description="Optional external vector service base URL; falls back to in-process bridge when unset.",
    )
    vector_search_endpoint: str = Field(
        default="/vectors/search",
        alias="VECTOR_SEARCH_ENDPOINT",
        description="Relative path to the search endpoint when using an external vector service.",
    )
    vector_request_timeout: float = Field(
        default=30.0,
        alias="VECTOR_REQUEST_TIMEOUT",
        description="HTTP timeout (seconds) for external vector service calls.",
    )

    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen3:8b", alias="OLLAMA_MODEL")
    ollama_timeout: float = Field(default=60.0, alias="OLLAMA_TIMEOUT")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        alias="OPENAI_BASE_URL",
        description="Base URL for OpenAI-compatible APIs (set this to Qwen cloud endpoint when needed).",
    )

    top_k: int = Field(default=3, alias="TOP_K")
    similarity_threshold: float = Field(default=0.7, alias="SIMILARITY_THRESHOLD")
    prompt_template: str = Field(
        default=(
            "请根据以下上下文信息回答问题。如果上下文中包含答案，请结合引用内容进行回答；"
            "如果无法在上下文中找到足够信息，请明确说明信息不足。\n\n"
            "问题：{question}\n\n"
            "相关上下文：\n{context}\n\n"
            "请基于以上上下文提供准确、有用的回答："
        ),
        alias="PROMPT_TEMPLATE",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> RagSettings:
    return RagSettings()
