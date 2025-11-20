"""Pydantic models shared by the RAG module."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Client payload carrying the natural-language question."""

    question: str = Field(..., min_length=1, description="用户提出的问题")


class SourceDocument(BaseModel):
    """Metadata returned for every supporting document chunk."""

    text: str = Field(..., description="检索到的文本内容")
    url: Optional[str] = Field(default=None, description="原文链接或来源")
    title: Optional[str] = Field(default=None, description="来源标题或标识")
    score: Optional[float] = Field(default=None, description="相似度得分（0-1）")


class AnswerResponse(BaseModel):
    """Standard RAG response envelope."""

    code: str = Field(default="200")
    answer: str = Field(..., description="生成式模型返回的答案")
    sources: List[SourceDocument] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error payload surfaced by the API layer."""

    error: str
    code: str = Field(default="500")
    details: Optional[str] = None
