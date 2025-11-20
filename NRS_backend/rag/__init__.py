"""Module wiring helpers for the RAG service."""
from fastapi import FastAPI

from .router import router as rag_router


def setup_rag(app: FastAPI) -> None:
    """Attach RAG routes to the shared FastAPI instance."""
    app.include_router(rag_router)


__all__ = ["setup_rag", "rag_router"]
