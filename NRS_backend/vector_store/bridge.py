"""Lightweight helpers for intra-process vector service calls."""
from __future__ import annotations

from typing import Any, Dict

from .models import DocumentPayload, VectorSearchRequest, VectorSearchResponse
from .services import vector_service


async def store_document(document_id: str, text: str, metadata: Dict[str, Any]) -> bool:
    safe_metadata = dict(metadata or {})
    safe_metadata.setdefault("original_id", document_id)
    url = safe_metadata.get("url")
    payload = DocumentPayload(text=text, metadata=safe_metadata, url=url)
    response = await vector_service.upsert_document(payload)
    return response.status.lower() in {"stored", "queued", "updated"}


async def search_documents(query: str, top_k: int = 5) -> VectorSearchResponse:
    request = VectorSearchRequest(query=query, top_k=top_k)
    return await vector_service.search(request)
