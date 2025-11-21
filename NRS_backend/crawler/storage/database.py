"""MongoDB storage helpers for crawler records."""

from __future__ import annotations

import os
from typing import Any, Iterable, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://svc_mongo:27017")

_client: AsyncIOMotorClient | None = None
_collection = None


def initialize() -> None:
    """Initialize the Motor client and articles collection if not already set."""
    global _client, _collection
    if _collection is not None:
        return
    _client = AsyncIOMotorClient(MONGO_URL)
    _collection = _client["crawler_db"]["articles"]


def _get_collection() -> Any:
    if _collection is None:
        initialize()
    return _collection


async def record_exists(content_hash: str) -> bool:
    """Check whether a record with the given hash already exists."""
    collection = _get_collection()
    document = await collection.find_one({"content_hash": content_hash}, {"_id": 1})
    return document is not None


async def insert_record(
    record_id: str,
    title: str,
    url: str,
    publish_time: str,
    source_id: str,
    source_name: str,
    content: str,
    status: str = "pending",
    attachments: Optional[List[dict[str, Any]]] = None,
    extra_meta: Optional[dict[str, Any]] = None,
) -> None:
    """Insert or upsert a crawl record into MongoDB."""
    collection = _get_collection()
    doc = {
        "content_hash": record_id,
        "source": source_id,
        "source_name": source_name,
        "title": title,
        "url": url,
        "publish_time": publish_time,
        "raw_content": content,
        "status": status,
        "attachments": attachments or [],
        "extra_meta": extra_meta or {},
    }
    await collection.update_one(
        {"content_hash": record_id},
        {"$setOnInsert": doc},
        upsert=True,
    )


async def mark_synced(record_ids: Iterable[str]) -> None:
    """Mark records as synced by updating their status."""
    record_list = list(record_ids)
    if not record_list:
        return
    collection = _get_collection()
    await collection.update_many(
        {"content_hash": {"$in": record_list}},
        {"$set": {"status": "synced"}},
    )
