"""Unified FastAPI backend exposing crawler and vector services on port 8000."""
from __future__ import annotations

from fastapi import FastAPI

from .crawler import setup_crawler
from .vector_store import setup_vector_store

app = FastAPI(title="NJU Unified Backend", version="1.0.0")

setup_crawler(app)
setup_vector_store(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def get_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("NRS_backend.main:app", host="0.0.0.0", port=8000, reload=True)
