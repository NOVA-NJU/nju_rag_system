"""
RAG（检索增强生成）模块初始化与挂载

本文件负责：
1. 定义 setup_rag(app) 方法，将 RAG 相关路由挂载到主 FastAPI 应用。
2. 通过 include_router 注册 /api/rag 路由（见 router.py），供前端或其他服务调用。

API整合流程：
- 主应用调用 setup_rag(app)，本方法会自动注册 RAG 路由。
- 所有 RAG 相关 API 都通过 /api/rag 暴露。
"""
from fastapi import FastAPI  # 导入 FastAPI 主类，用于类型标注和应用实例传递

from .router import router as rag_router  # 导入 RAG 路由对象，定义了 /api/rag 相关接口


def setup_rag(app: FastAPI) -> None:
    """
    挂载 RAG 路由到主 FastAPI 应用。
    参数：app —— 主 FastAPI 应用实例。
    作用：注册 /api/rag 路由（由 router.py 提供），实现 RAG API。
    """
    app.include_router(rag_router)  # 注册 RAG 路由到主应用，所有 /api/rag 请求由 router.py 处理


__all__ = ["setup_rag", "rag_router"]  # 模块导出，供主应用或其他模块引用
