"""API router exposing RAG endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from .models import AnswerResponse, ErrorResponse, QuestionRequest
from .service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("", response_model=AnswerResponse, responses={400: {"model": ErrorResponse}})
async def rag_endpoint(payload: QuestionRequest) -> AnswerResponse:
    """Run the end-to-end RAG pipeline for the provided question."""
    try:
        return await rag_service.generate_answer(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG pipeline failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/health")
async def rag_health() -> dict[str, str]:
    """Lightweight health probe for the RAG subsystem."""
    return {"code": "200", "status": "healthy", "service": "RAG"}
