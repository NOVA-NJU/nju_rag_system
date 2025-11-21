"""Lightweight helpers for intra-process vector service calls."""  # 进程内向量服务调用的轻量级助手
from __future__ import annotations  # 兼容未来类型注解语法

from typing import Any, Dict  # 类型注解：Any用于任意类型，Dict用于字典

from .models import DocumentPayload, VectorSearchRequest, VectorSearchResponse  # 导入向量存储数据模型
from .services import vector_service  # 导入向量存储服务实例


async def store_document(document_id: str, text: str, metadata: Dict[str, Any]) -> bool:
    safe_metadata = dict(metadata or {})  # 创建元数据的安全副本，避免修改原字典
    safe_metadata.setdefault("original_id", document_id)  # 设置默认的原始ID
    url = safe_metadata.get("url")  # 从元数据中获取URL
    payload = DocumentPayload(text=text, metadata=safe_metadata, url=url)  # 创建文档载荷对象
    response = await vector_service.upsert_document(payload)  # 调用向量服务的文档插入/更新方法
    return response.status.lower() in {"stored", "queued", "updated"}  # 返回操作是否成功的布尔值


async def search_documents(query: str, top_k: int = 5) -> VectorSearchResponse:
    request = VectorSearchRequest(query=query, top_k=top_k)  # 创建搜索请求对象
    return await vector_service.search(request)  # 调用向量服务的搜索方法并返回响应
