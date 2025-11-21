
"""
RAG 问答 API 路由

本文件负责暴露 /api/rag 相关接口，包括：
  - POST /api/rag      问答主接口（前端 Thinking 模式用）
  - GET /api/rag/health  RAG 子系统健康检查
"""
from __future__ import annotations  # 兼容未来类型注解语法

import logging  # 日志记录，用于异常追踪

from fastapi import APIRouter, HTTPException, status  # FastAPI路由器、异常处理、状态码

# 数据模型：问答请求体、响应体、错误体
from .models import AnswerResponse, ErrorResponse, QuestionRequest  # 导入Pydantic数据模型
# 业务逻辑：RAG 问答服务
from .service import rag_service  # 导入RAG服务实例

logger = logging.getLogger(__name__)  # 获取当前模块日志对象

# 创建路由器实例，统一前缀 /api/rag
router = APIRouter(prefix="/api/rag", tags=["rag"])  # 定义路由器，添加标签便于文档分组

#
# POST /api/rag
# 说明：
#   - 请求体：{"question": "你的问题"}
#   - 返回：AI 生成的答案和引用信息
#   - 内部流程：先向量检索，再拼接 Prompt，最后调用 LLM
#
@router.post("", response_model=AnswerResponse, responses={400: {"model": ErrorResponse}})
async def rag_endpoint(payload: QuestionRequest) -> AnswerResponse:
    """
    RAG 问答主接口。
    参数：payload.question（用户问题字符串）
    返回：AnswerResponse（答案、引用来源等）
    异常：
      - ValueError：问题无效，返回 400
      - 其他异常：返回 502
    内部流程：
      1. 先用向量检索找相关片段
      2. 拼接 Prompt
      3. 调用 LLM（Ollama/OpenAI）生成答案
      4. 返回答案和引用
    """
    try:
        return await rag_service.generate_answer(payload.question)
    except ValueError as exc:
        # 问题无效，返回 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG pipeline failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


# GET /api/rag/health
# 说明：
#   - 返回 RAG 子系统健康状态
#   - 供前端/监控探测
@router.get("/health")
async def rag_health() -> dict[str, str]:
    """
    RAG 子系统健康检查接口。
    返回：服务状态、版本等
    """
    return {"code": "200", "status": "healthy", "service": "RAG"}
