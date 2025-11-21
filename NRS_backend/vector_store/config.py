"""Configuration for the vector store service inside the unified backend."""  # 统一后端中向量存储服务的配置
from __future__ import annotations  # 兼容未来类型注解语法

from typing import Optional  # 类型注解：Optional用于可选类型

from pydantic_settings import BaseSettings, SettingsConfigDict  # Pydantic设置基类和配置字典


class VectorSettings(BaseSettings):
    """Vector service configuration class."""  # 向量服务配置类

    db_path: str = "./chroma_db"  # 向量数据库路径，默认当前目录下的chroma_db
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # 嵌入模型名称，默认中文小模型
    embedding_dim: int = 512  # 嵌入维度，默认512
    HF_TOKEN: Optional[str] = None  # HuggingFace令牌，可选，用于访问私有模型
    default_top_k: int = 5  # 默认检索结果数量，默认5
    enable_chunking: bool = False  # 是否启用分块，默认False
    chunk_size: int = 500  # 分块大小，默认500字符
    chunk_overlap: int = 50  # 分块重叠大小，默认50字符
    HOST: str = "0.0.0.0"  # 服务主机地址，默认所有接口
    PORT: int = 8000  # 服务端口，默认8000
    DEBUG: bool = True  # 调试模式，默认True

    model_config = SettingsConfigDict(  # Pydantic模型配置
        env_prefix="VECTOR_",  # 环境变量前缀
        env_file=".env",  # 环境文件路径
        case_sensitive=True,  # 区分大小写
        extra="ignore",  # 忽略额外字段
    )


def get_settings() -> VectorSettings:
    return VectorSettings()  # 返回VectorSettings实例


default_settings = get_settings()  # 获取默认设置
settings = default_settings  # 设置全局settings变量
