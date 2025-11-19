"""Crawler module wiring helpers."""
from fastapi import FastAPI

from .router import router as crawler_router
from .lifecycle import register_crawler_lifecycle


def setup_crawler(app: FastAPI) -> None:
    """Attach crawler routes and lifecycle hooks to the shared FastAPI app."""
    app.include_router(crawler_router)
    register_crawler_lifecycle(app)


__all__ = ["setup_crawler", "crawler_router"]
