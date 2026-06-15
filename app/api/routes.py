"""FastAPI route handlers.

Endpoints:
  POST /detect   - Accept an NSFW detection job; run async, callback to Lychee.
  GET  /health   - Return service health.
  GET  /config   - Return current runtime configuration values.
  GET  /queue    - Return number of pending jobs.
  DELETE /queue  - Purge all pending jobs.
  GET  /queue/{photo_id} - Return queue position of a photo.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_queue, require_api_key
from app.api.schemas import (
    DetectCallbackPayload,
    Detection,
    DetectRequest,
    ErrorCallbackPayload,
    HealthResponse,
    QueuePositionResponse,
    QueueSizeResponse,
    ServiceConfigResponse,
)
from app.config import AppSettings, get_settings

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from app.queue.base import JobQueue

logger = logging.getLogger(__name__)

router = APIRouter()
queue_router = APIRouter(prefix="/queue", tags=["queue"])


# ---------------------------------------------------------------------------
# POST /detect
# ---------------------------------------------------------------------------


@router.post(
    "/detect",
    status_code=202,
    responses={
        400: {"description": "Invalid or inaccessible photo path"},
        429: {"description": "Queue is full — try again later"},
    },
)
async def detect(
    body: DetectRequest,
    request: Request,
    settings: AppSettings = Depends(get_settings),
    _: None = Depends(require_api_key),
) -> None:
    """Accept an NSFW detection job.

    Validates the photo path (path-traversal protection), then immediately
    returns **202 Accepted** and enqueues detection for a background worker.
    Returns **429 Too Many Requests** when the queue is full.
    Results are POSTed back to Lychee's results endpoint once detection
    completes.
    """
    resolved = Path(settings.photos_path.removesuffix("/") + "/" + body.photo_path.removeprefix("/")).resolve()
    photos_root = Path(settings.photos_path).resolve()

    if not str(resolved).startswith(str(photos_root) + "/") and resolved != photos_root:
        logger.warning(
            "[/detect] 400 path-traversal: photo_id=%s resolved=%s photos_root=%s",
            body.photo_id,
            resolved,
            photos_root,
        )
        raise HTTPException(status_code=400, detail=f"photo_path {resolved} is outside the allowed directory")

    if not resolved.is_file():
        logger.warning(
            "[/detect] 400 file-not-found: photo_id=%s resolved=%s",
            body.photo_id,
            resolved,
        )
        raise HTTPException(status_code=400, detail="photo_path does not exist or is not a file")

    import json

    queue: JobQueue = get_queue(request)
    accepted = await queue.enqueue(
        job_type="detect",
        photo_id=body.photo_id,
        payload=json.dumps({"photo_path": str(resolved)}),
    )
    if not accepted:
        raise HTTPException(status_code=429, detail="Queue is full — try again later")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health() -> HealthResponse:
    """Return service health status.

    Intentionally unauthenticated so that load-balancers and Docker health
    checks can probe it without an API key.
    """
    return HealthResponse(status="ok")


# ---------------------------------------------------------------------------
# GET /config
# ---------------------------------------------------------------------------


@router.get("/config")
async def service_config(
    settings: AppSettings = Depends(get_settings),
    _: None = Depends(require_api_key),
) -> ServiceConfigResponse:
    """Return current runtime configuration values.

    The endpoint is authenticated because it exposes operational details.
    Sensitive values are redacted by ``AppSettings.to_diagnostics_payload``.
    """
    return ServiceConfigResponse(config=settings.to_diagnostics_payload())


# ---------------------------------------------------------------------------
# /queue endpoints
# ---------------------------------------------------------------------------


@queue_router.get("")
async def queue_size(
    request: Request,
    _: None = Depends(require_api_key),
) -> QueueSizeResponse:
    """Return the number of jobs currently waiting to be processed."""
    queue: JobQueue = get_queue(request)
    return QueueSizeResponse(pending=await queue.size())


@queue_router.delete("", status_code=204)
async def queue_purge(
    request: Request,
    _: None = Depends(require_api_key),
) -> None:
    """Delete all pending jobs from the queue. In-flight jobs are not affected."""
    queue: JobQueue = get_queue(request)
    await queue.purge()


@queue_router.get(
    "/{photo_id}",
    responses={
        404: {"description": "Photo not found in queue (already done or never submitted)"},
    },
)
async def queue_position(
    photo_id: str,
    request: Request,
    _: None = Depends(require_api_key),
) -> QueuePositionResponse:
    """Return the position of a photo in the queue.

    - **present** → job is waiting; ``position`` is its 1-based rank among pending jobs.
      ``position=0`` means the job is currently being processed.
    - **absent** → job is done (404).
    """
    queue: JobQueue = get_queue(request)
    pos = await queue.position(photo_id)
    if pos is None:
        raise HTTPException(status_code=404, detail="Photo not found in queue (already done or never submitted)")
    return QueuePositionResponse(photo_id=photo_id, position=pos)


# ---------------------------------------------------------------------------
# Background detection job
# ---------------------------------------------------------------------------


async def _run_detection_job(
    photo_id: str,
    image_path: Path,
    executor: Executor,
    settings: AppSettings,
) -> None:
    """Classify an image for NSFW content and notify Lychee via callback.

    Runs entirely as an async background task after the ``/detect`` route has
    returned 202.  CPU-bound NudeNet inference is offloaded to ``executor`` via
    ``run_in_executor`` so the event loop remains responsive.
    """
    logger.info("Starting NSFW detection job for photo_id=%s, path=%s", photo_id, image_path)
    try:
        from app.detection.detector import classify, detect_from_path

        loop = asyncio.get_running_loop()

        raw, w, h = await loop.run_in_executor(executor, detect_from_path, str(image_path))
        result = classify(raw, w, h, settings)

        logger.info(
            "NSFW detection complete for photo_id=%s: should_block=%s, should_review=%s, is_sensitive=%s | "
            "block=%s review=%s sensitive=%s all=%s",
            photo_id,
            result["should_block"],
            result["should_review"],
            result["is_sensitive"],
            [d["label"] for d in result["block_detected"]],
            [d["label"] for d in result["review_detected"]],
            [d["label"] for d in result["sensitive_detected"]],
            [(d["label"], round(d["confidence"], 3), round(d["area_ratio"], 4)) for d in result["all_detected"]],
        )

        payload = DetectCallbackPayload(
            photo_id=photo_id,
            should_block=result["should_block"],
            should_review=result["should_review"],
            is_sensitive=result["is_sensitive"],
            all_detected=[Detection.model_validate(d) for d in result["all_detected"]],
            block_detected=[Detection.model_validate(d) for d in result["block_detected"]],
            review_detected=[Detection.model_validate(d) for d in result["review_detected"]],
            sensitive_detected=[Detection.model_validate(d) for d in result["sensitive_detected"]],
        )

        callback_url = f"{settings.lychee_api_url}/api/v2/NsfwDetection/results"
        async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
            response = await client.post(
                callback_url,
                json=payload.model_dump(),
                headers={
                    "X-API-Key": settings.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()

        logger.info("Successfully sent NSFW results to Lychee for photo_id=%s", photo_id)

    except Exception:
        logger.exception("NSFW detection job failed for photo_id=%s; sending error callback", photo_id)
        await _send_error_callback(photo_id, "internal_error", "NSFW detection pipeline failed", settings)


async def _send_error_callback(photo_id: str, error_code: str, message: str, settings: AppSettings) -> None:
    """Best-effort POST of an error callback to Lychee."""
    payload = ErrorCallbackPayload(photo_id=photo_id, error_code=error_code, message=message)
    callback_url = f"{settings.lychee_api_url}/api/v2/NsfwDetection/results"
    try:
        async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
            await client.post(
                callback_url,
                json=payload.model_dump(),
                headers={
                    "X-API-Key": settings.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
    except Exception:
        logger.exception("Failed to send error callback for photo_id=%s", photo_id)


# Register queue sub-router after all handlers are defined.
router.include_router(queue_router)
