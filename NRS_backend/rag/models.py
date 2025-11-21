"""Pydantic models shared by the RAG module."""  # RAG模块共享的Pydantic数据模型
from __future__ import annotations  # 兼容未来类型注解语法

from typing import List, Optional  # 类型注解：List用于列表，Optional用于可选类型

from pydantic import BaseModel, Field  # Pydantic基础模型和字段定义


class QuestionRequest(BaseModel):
    """Client payload carrying the natural-language question."""  # 客户端载荷，包含自然语言问题

    question: str = Field(..., min_length=1, description="用户提出的问题")  # 问题字段：必填，最小长度1，描述用户问题


class SourceDocument(BaseModel):
    """Metadata returned for every supporting document chunk."""  # 为每个支持文档块返回的元数据

    text: str = Field(..., description="检索到的文本内容")  # 文本字段：必填，描述检索到的文本内容
    url: Optional[str] = Field(default=None, description="原文链接或来源")  # URL字段：可选，默认None，描述原文链接
    title: Optional[str] = Field(default=None, description="来源标题或标识")  # 标题字段：可选，默认None，描述来源标题
    score: Optional[float] = Field(default=None, description="相似度得分（0-1）")  # 分数字段：可选，默认None，描述相似度得分


class AnswerResponse(BaseModel):
    """Standard RAG response envelope."""  # 标准RAG响应信封

    code: str = Field(default="200")  # 状态码字段：默认"200"
    answer: str = Field(..., description="生成式模型返回的答案")  # 答案字段：必填，描述LLM生成的答案
    sources: List[SourceDocument] = Field(default_factory=list)  # 源文档列表字段：默认空列表，包含支持文档


class ErrorResponse(BaseModel):
    """Error payload surfaced by the API layer."""  # API层表面的错误载荷

    error: str  # 错误字段：错误消息字符串
    code: str = Field(default="500")  # 状态码字段：默认"500"
    details: Optional[str] = None  # 详情字段：可选，默认None，包含额外错误详情
