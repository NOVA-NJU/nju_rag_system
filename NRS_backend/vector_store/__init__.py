"""Vector store module wiring helpers."""  # 向量存储模块布线助手
from fastapi import FastAPI  # 导入FastAPI主类，用于类型标注

from .router import router as vector_router  # 导入向量存储路由对象，定义了/vectors相关接口


def setup_vector_store(app: FastAPI) -> None:
    """Attach vector store routes to the shared FastAPI app."""  # 将向量存储路由附加到共享的FastAPI应用
    app.include_router(vector_router, prefix="/vectors", tags=["vectors"])  # 注册向量存储路由到主应用，添加前缀/vectors和标签vectors


__all__ = ["setup_vector_store", "vector_router"]  # 模块导出，供主应用或其他模块引用
