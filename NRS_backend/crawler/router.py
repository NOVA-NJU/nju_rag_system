"""API router exposing crawler endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .models import CrawlRequest, CrawlResponse, ErrorResponse
from .services import crawl_source

router = APIRouter()


@router.post(
    "/api/crawl",
    response_model=CrawlResponse,
    responses={404: {"model": ErrorResponse}},
)
async def crawl_endpoint(payload: CrawlRequest) -> CrawlResponse:
    """Trigger a crawl for the requested source id and normalize failures."""
    try:
        data = await crawl_source(payload.source)
        return CrawlResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
