"""Background task wiring for the crawler module."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Optional

from fastapi import FastAPI

from .config import AUTO_CRAWL_ENABLED, CRAWL_INTERVAL, TARGET_SOURCES
from .services import crawl_source

logger = logging.getLogger(__name__)

_periodic_task: Optional[asyncio.Task] = None


async def _crawl_all_sources_once() -> None:
    """Iterate through configured sources and run the crawler sequentially."""
    for source in TARGET_SOURCES:
        source_id = source["id"]
        try:
            await crawl_source(source_id)
            logger.info("Periodic crawl finished for source %s", source_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Periodic crawl failed for source %s: %s", source_id, exc)


async def _periodic_crawl_loop() -> None:
    """Background loop that keeps crawling based on the configured interval."""
    while True:
        await _crawl_all_sources_once()
        await asyncio.sleep(max(1, CRAWL_INTERVAL))


def register_crawler_lifecycle(app: FastAPI) -> None:
    """Register startup/shutdown hooks on the shared FastAPI app."""

    @app.on_event("startup")
    async def _start_periodic_task() -> None:
        global _periodic_task  # noqa: PLW0603 - module level state is intentional
        if AUTO_CRAWL_ENABLED and _periodic_task is None:
            _periodic_task = asyncio.create_task(_periodic_crawl_loop())
            logger.info("Started periodic crawler task with interval %s seconds", CRAWL_INTERVAL)

    @app.on_event("shutdown")
    async def _stop_periodic_task() -> None:
        global _periodic_task  # noqa: PLW0603 - module level state is intentional
        if _periodic_task:
            _periodic_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await _periodic_task
            logger.info("Stopped periodic crawler task")
            _periodic_task = None
