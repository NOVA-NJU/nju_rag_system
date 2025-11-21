"""Vector-store specific Pydantic models."""  # 向量存储特定的Pydantic模型
from __future__ import annotations  # 兼容未来类型注解语法

from typing import Any, Dict, List, Optional  # 类型注解：Any任意类型，Dict字典，List列表，Optional可选

from pydantic import BaseModel, Field  # Pydantic基础模型和字段定义

from .config import VectorSettings  # 导入向量存储配置


class DocumentPayload(BaseModel):
    text: str = Field(..., description="需要做嵌入的原始文本内容")  # 文本字段：必填，描述需要嵌入的原始文本
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据字段：默认空字典
    url: Optional[str] = Field(default=None, description="文档来源链接")  # URL字段：可选，默认None，描述文档来源链接


class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="需要嵌入并匹配的自然语言查询")  # 查询字段：必填，描述需要嵌入和匹配的自然语言查询
    top_k: int = Field(VectorSettings().default_top_k, ge=1, le=50, description="需要返回的结果数量")  # top_k字段：默认配置值，范围1-50，描述返回结果数量


class VectorMatch(BaseModel):
    document_id: str  # 文档ID字段：字符串类型
    score: float  # 分数字段：浮点数类型
    text: Optional[str] = None  # 文本字段：可选，默认None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据字段：默认空字典


class VectorSearchResponse(BaseModel):
    results: List[VectorMatch]  # 结果列表字段：VectorMatch对象列表
    query: str  # 查询字段：字符串类型
    top_k: int  # top_k字段：整数类型


class DocumentUpsertResponse(BaseModel):
    document_id: str  # 文档ID字段：字符串类型
    status: str = "queued"  # 状态字段：默认"queued"
    detail: Optional[str] = None  # 详情字段：可选，默认None


class DocumentChunk(BaseModel):
    chunk_id: str  # 分块ID字段：字符串类型
    text: str  # 文本字段：字符串类型
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据字段：默认空字典


class DocumentGetResponse(BaseModel):
    document_id: str  # 文档ID字段：字符串类型
    text: Optional[str] = None  # 文本字段：可选，默认None
    chunks: Optional[List[DocumentChunk]] = None  # 分块列表字段：可选，默认None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据字段：默认空字典


class ClearDbResponse(BaseModel):
    status: str  # 状态字段：字符串类型
