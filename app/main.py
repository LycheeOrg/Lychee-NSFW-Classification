"""FastAPI application factory.

Entry point for the NSFW Classification Service.  The ``create_app`` factory
accepts an optional ``lifespan`` parameter so that tests can inject a custom
lifespan context that pre-populates ``app.state`` with mock objects instead of
loading the real NudeNet model.
"""

from __future__ import annotations

import asyncio
import logging
import typing
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import router
from app.config import AppSettings, get_settings
from app.queue.factory import create_queue
from app.queue.worker import run_worker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[35m",  # magenta
}
_DIM = "\033[2m"
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    @typing.override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return f"{_DIM}{super().formatTime(record, datefmt)}{_RESET}"

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{_RESET}"
        return super().format(record)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def _default_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Production lifespan: initialise the queue and thread pool."""
    settings: AppSettings = get_settings()

    # Configure logging
    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter("%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[handler],
    )

    # Verify Lychee connectivity
    if settings.skip_lychee_check:
        logger.warning("Skipping Lychee connectivity check (VISION_NSFW_SKIP_LYCHEE_CHECK=true)")
    else:
        lychee_up_url = f"{settings.lychee_api_url}/up"
        logger.info("Checking Lychee connectivity at %s", lychee_up_url)
        try:
            async with httpx.AsyncClient(verify=settings.verify_ssl, timeout=10.0) as client:
                response = await client.get(lychee_up_url)
                response.raise_for_status()
                logger.info("✓ Lychee is reachable (status=%d)", response.status_code)
        except httpx.HTTPStatusError as e:
            logger.error("✗ Lychee /up endpoint returned status %d", e.response.status_code)
            raise RuntimeError(
                f"Lychee health check failed: /up returned {e.response.status_code}. "
                "Ensure VISION_NSFW_LYCHEE_API_URL is correct and Lychee is running."
            ) from e
        except httpx.RequestError as e:
            logger.error("✗ Cannot connect to Lychee at %s: %s", lychee_up_url, e)
            raise RuntimeError(
                f"Cannot connect to Lychee at {lychee_up_url}. "
                "Ensure VISION_NSFW_LYCHEE_API_URL is correct and Lychee is reachable."
            ) from e

    # Thread pool for CPU-bound NudeNet inference
    executor = ThreadPoolExecutor(max_workers=settings.thread_pool_size)

    # Job queue
    queue = create_queue(settings)
    logger.info("Job queue initialised (backend=%s, max_size=%d)", settings.queue_backend, settings.queue_max_size)

    app.state.executor = executor
    app.state.queue = queue

    # Start one worker task per thread-pool slot so all CPU threads stay busy.
    worker_tasks = [
        asyncio.create_task(run_worker(queue, app.state, settings)) for _ in range(settings.thread_pool_size)
    ]
    logger.info("Started %d queue worker(s)", len(worker_tasks))

    try:
        yield
    finally:
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        await queue.close()
        executor.shutdown(wait=False)
        logger.info("NSFW Classification Service shut down")


def create_app(lifespan: Any = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        lifespan: Optional async context manager to use as the application
            lifespan.  When ``None``, :func:`_default_lifespan` is used.
            Override in tests to inject mock state without loading the model.

    Returns:
        A configured :class:`fastapi.FastAPI` instance.
    """
    used_lifespan = lifespan if lifespan is not None else _default_lifespan

    application = FastAPI(
        title="Lychee NSFW Classification Service",
        description="NSFW content moderation microservice for Lychee photo gallery.",
        version="0.1.0",
        lifespan=used_lifespan,
    )
    application.include_router(router, prefix="/api/nsfw")

    @application.get("/", include_in_schema=False)
    async def _root() -> RedirectResponse:
        return RedirectResponse(url="/api/nsfw/health")

    return application


# Module-level app instance used by uvicorn when started via the Dockerfile CMD.
app: FastAPI = create_app()
