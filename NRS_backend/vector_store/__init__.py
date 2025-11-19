"""Vector store module wiring helpers."""
from fastapi import FastAPI

from .router import router as vector_router


def setup_vector_store(app: FastAPI) -> None:
    """Attach vector store routes to the shared FastAPI app."""
    app.include_router(vector_router, prefix="/vectors", tags=["vectors"])


__all__ = ["setup_vector_store", "vector_router"]
