"""Pydantic schemas shared by crawler endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class CrawlRequest(BaseModel):
    """Client payload that specifies which source id to crawl."""

    source: str


class Attachments(BaseModel):
    """Normalized representation of each attachment extracted from a detail page."""

    url: HttpUrl
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    text: Optional[str] = None


class CrawlItem(BaseModel):
    """Single crawled article with aggregated text and metadata."""

    id: str
    title: str
    content: str
    url: HttpUrl
    publish_time: datetime
    source: str
    attachments: Optional[List[Attachments]] = None
    extra_meta: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standardized error payload returned by the API layer."""

    error: str
    code: str = "404"


class CrawlResponse(BaseModel):
    """Success envelope returned by /api/crawl."""

    code: str = "200"
    data: List[CrawlItem]
