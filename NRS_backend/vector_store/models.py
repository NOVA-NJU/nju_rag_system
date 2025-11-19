"""Vector-store specific Pydantic models."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .config import VectorSettings


class DocumentPayload(BaseModel):
    text: str = Field(..., description="需要做嵌入的原始文本内容")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    url: Optional[str] = Field(default=None, description="文档来源链接")


class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="需要嵌入并匹配的自然语言查询")
    top_k: int = Field(VectorSettings().default_top_k, ge=1, le=50, description="需要返回的结果数量")


class VectorMatch(BaseModel):
    document_id: str
    score: float
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorSearchResponse(BaseModel):
    results: List[VectorMatch]
    query: str
    top_k: int


class DocumentUpsertResponse(BaseModel):
    document_id: str
    status: str = "queued"
    detail: Optional[str] = None


class DocumentChunk(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentGetResponse(BaseModel):
    document_id: str
    text: Optional[str] = None
    chunks: Optional[List[DocumentChunk]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClearDbResponse(BaseModel):
    status: str
