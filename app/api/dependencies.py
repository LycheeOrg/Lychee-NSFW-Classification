"""FastAPI dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Header, HTTPException, Request

from app.config import AppSettings, get_settings

if TYPE_CHECKING:
    from app.queue.base import JobQueue


async def require_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    settings: AppSettings = Depends(get_settings),
) -> None:
    """FastAPI dependency that validates the ``X-API-Key`` request header.

    Raises:
        HTTPException(401): If the header is missing or does not match
            ``VISION_NSFW_API_KEY``.
    """
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_queue(request: Request) -> JobQueue:
    """Return the :class:`JobQueue` stored in ``app.state``."""
    return request.app.state.queue
