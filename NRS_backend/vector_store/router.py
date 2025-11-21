
"""
向量存储 API 路由

本文件负责暴露 /vectors/* 相关接口，包括：
  - /vectors/search      向量检索（前端 Search 模式用）
  - /vectors/documents  文档写入/更新
  - /vectors/cleardb    清空向量库
  - /vectors/search/{id} 查询单个文档
"""
from __future__ import annotations  # 兼容未来类型注解语法

from fastapi import APIRouter  # 导入FastAPI路由器

# 导入所有数据模型和服务层
from .models import (  # 导入数据模型
    ClearDbResponse,         # 清库响应
    DocumentGetResponse,     # 单文档查询响应
    DocumentPayload,         # 文档写入请求体
    DocumentUpsertResponse,  # 文档写入响应体
    VectorSearchRequest,     # 检索请求体
    VectorSearchResponse,    # 检索响应体
)
from .services import vector_service  # 导入向量存储服务实例

# 创建路由器实例
router = APIRouter()  # 创建路由器实例，用于定义API端点

#
# POST /vectors/search
# 说明：
#   - 请求体：{"query": "文本", "top_k": N}
#   - 返回：最相似的文档片段列表（score、text、metadata...）
#   - 前端 Search 模式用此接口
#
@router.post("/search", response_model=VectorSearchResponse)  # 定义POST /search端点，指定响应模型
async def search_vectors(request: VectorSearchRequest) -> VectorSearchResponse:
    """
    向量检索接口。
    参数：request.query（查询文本），request.top_k（返回条数）
    返回：VectorSearchResponse（匹配结果列表）
    """
    return await vector_service.search(request)  # 调用向量服务的搜索方法

# 兼容结尾带 / 的请求（部分前端/工具会自动加斜杠）
@router.post("/search/", response_model=VectorSearchResponse, include_in_schema=False)  # 定义兼容性端点，不包含在API文档中
async def search_vectors_trailing(request: VectorSearchRequest) -> VectorSearchResponse:
    return await vector_service.search(request)  # 调用相同的搜索方法

#
# GET /vectors/search/{document_id}
# 说明：
#   - 路径参数：document_id
#   - 返回指定文档的详细内容和元数据
#
@router.get("/search/{document_id}", response_model=DocumentGetResponse)  # 定义GET端点，路径参数document_id
async def get_document(document_id: str) -> DocumentGetResponse:
    """
    查询单个文档详细信息。
    参数：document_id（文档唯一标识）
    返回：DocumentGetResponse
    """
    return await vector_service.get_document_by_id(document_id)  # 调用获取文档方法

#
# POST /vectors/documents
# 说明：
#   - 请求体：文档内容、元数据等
#   - 用于新增或更新向量库中的文档
#
@router.post("/documents", response_model=DocumentUpsertResponse)  # 定义POST /documents端点
async def add_document(payload: DocumentPayload) -> DocumentUpsertResponse:
    """
    文档写入/更新接口。
    参数：payload（包含文本、元数据等）
    返回：DocumentUpsertResponse
    """
    return await vector_service.upsert_document(payload)  # 调用文档插入/更新方法

#
# POST /vectors/cleardb
# 说明：
#   - 清空整个向量库（危险操作，需谨慎）
#
@router.post("/cleardb", response_model=ClearDbResponse)  # 定义POST /cleardb端点
async def clear_db() -> ClearDbResponse:
    """
    清空向量库所有内容。
    返回：ClearDbResponse
    """
    return await vector_service.clear_db()  # 调用清空数据库方法
