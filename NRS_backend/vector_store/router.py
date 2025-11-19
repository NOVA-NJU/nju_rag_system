"""Vector store API routes."""
from __future__ import annotations

from fastapi import APIRouter

from .models import (
    ClearDbResponse,
    DocumentGetResponse,
    DocumentPayload,
    DocumentUpsertResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)
from .services import vector_service

router = APIRouter()


@router.post("/search", response_model=VectorSearchResponse)
async def search_vectors(request: VectorSearchRequest) -> VectorSearchResponse:
    return await vector_service.search(request)


@router.post("/search/", response_model=VectorSearchResponse, include_in_schema=False)
async def search_vectors_trailing(request: VectorSearchRequest) -> VectorSearchResponse:
    return await vector_service.search(request)


@router.get("/search/{document_id}", response_model=DocumentGetResponse)
async def get_document(document_id: str) -> DocumentGetResponse:
    return await vector_service.get_document_by_id(document_id)


@router.post("/documents", response_model=DocumentUpsertResponse)
async def add_document(payload: DocumentPayload) -> DocumentUpsertResponse:
    return await vector_service.upsert_document(payload)


@router.post("/cleardb", response_model=ClearDbResponse)
async def clear_db() -> ClearDbResponse:
    return await vector_service.clear_db()
