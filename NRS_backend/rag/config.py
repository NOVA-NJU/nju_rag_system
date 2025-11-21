"""Configuration helpers for the RAG module."""  # RAG模块的配置助手
from __future__ import annotations  # 兼容未来类型注解语法

from functools import lru_cache  # LRU缓存装饰器，用于缓存设置实例

from pydantic import Field  # Pydantic字段定义
from pydantic_settings import BaseSettings, SettingsConfigDict  # Pydantic设置基类和配置字典


class RagSettings(BaseSettings):
    """Environment-driven configuration for the RAG workflow."""  # 环境驱动的RAG工作流配置

    # 向量服务配置
    vector_service_url: str | None = Field(  # 外部向量服务基础URL
        default=None,  # 默认值为None
        alias="VECTOR_SERVICE_URL",  # 环境变量别名
        description="Optional external vector service base URL; falls back to in-process bridge when unset.",  # 描述：可选的外部向量服务基础URL；未设置时回退到进程内桥接
    )
    vector_search_endpoint: str = Field(  # 向量搜索端点路径
        default="/vectors/search",  # 默认搜索端点
        alias="VECTOR_SEARCH_ENDPOINT",  # 环境变量别名
        description="Relative path to the search endpoint when using an external vector service.",  # 描述：使用外部向量服务时的搜索端点相对路径
    )
    vector_request_timeout: float = Field(  # 向量服务请求超时
        default=30.0,  # 默认30秒
        alias="VECTOR_REQUEST_TIMEOUT",  # 环境变量别名
        description="HTTP timeout (seconds) for external vector service calls.",  # 描述：外部向量服务调用的HTTP超时（秒）
    )

    # LLM提供商配置
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")  # LLM提供商，默认ollama
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")  # Ollama基础URL，默认本地
    ollama_model: str = Field(default="qwen3:8b", alias="OLLAMA_MODEL")  # Ollama模型名称
    ollama_timeout: float = Field(default=60.0, alias="OLLAMA_TIMEOUT")  # Ollama请求超时，默认60秒

    # OpenAI配置
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")  # OpenAI API密钥，可选
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")  # OpenAI模型名称
    openai_base_url: str = Field(  # OpenAI基础URL
        default="https://api.openai.com/v1",  # 默认OpenAI API
        alias="OPENAI_BASE_URL",  # 环境变量别名
        description="Base URL for OpenAI-compatible APIs (set this to Qwen cloud endpoint when needed).",  # 描述：OpenAI兼容API的基础URL（需要时设置为Qwen云端点）
    )

    # 检索配置
    top_k: int = Field(default=3, alias="TOP_K")  # 检索结果数量，默认3
    similarity_threshold: float = Field(default=0.7, alias="SIMILARITY_THRESHOLD")  # 相似度阈值，默认0.7
    prompt_template: str = Field(  # 提示模板
        default=(  # 默认提示模板
            "请根据以下上下文信息回答问题。如果上下文中包含答案，请结合引用内容进行回答；"
            "如果无法在上下文中找到足够信息，请明确说明信息不足。\n\n"
            "问题：{question}\n\n"
            "相关上下文：\n{context}\n\n"
            "请基于以上上下文提供准确、有用的回答："
        ),
        alias="PROMPT_TEMPLATE",  # 环境变量别名
    )

    # Pydantic配置
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # 模型配置：从.env文件读取，忽略额外字段


@lru_cache(maxsize=1)  # LRU缓存，最大缓存1个实例，避免重复创建
def get_settings() -> RagSettings:
    return RagSettings()  # 返回RagSettings实例
