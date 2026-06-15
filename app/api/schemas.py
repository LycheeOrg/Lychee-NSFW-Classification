"""Pydantic request/response schemas for the NSFW Classification Service API.

These models define the contract between the Python service and Lychee (PHP).
"""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# /detect - Lychee -> Python (request)  &  Python -> Lychee (callback)
# ---------------------------------------------------------------------------


class DetectRequest(BaseModel):
    """Body sent by Lychee when dispatching an NSFW detection job.

    ``callback_url`` is intentionally absent: the service reads
    ``VISION_NSFW_LYCHEE_API_URL`` from env and posts results there directly.
    """

    photo_id: str
    """Lychee-internal photo identifier (string PK)."""

    photo_path: str
    """Absolute filesystem path on the shared Docker volume.

    The service validates that this path starts with ``VISION_NSFW_PHOTOS_PATH``
    before opening the file (path-traversal protection).
    """


class BoundingBox(BaseModel):
    """Pixel-space bounding box for a single detection."""

    x: int
    y: int
    width: int
    height: int


class Detection(BaseModel):
    """One NSFW detection result."""

    label: str
    """NudeNet class label (e.g. ``FEMALE_BREAST_EXPOSED``)."""

    confidence: float = Field(ge=0.0, le=1.0)
    """Detection confidence score."""

    bbox: BoundingBox
    """Pixel-space bounding box."""

    area_pixels: int
    """Area of this detection in pixels."""

    area_ratio: float = Field(ge=0.0, le=1.0)
    """Fraction of the total image area covered by this detection."""


class DetectCallbackPayload(BaseModel):
    """Payload POSTed by the service to Lychee's results endpoint on success."""

    photo_id: str
    status: str = "success"
    should_block: bool
    should_review: bool
    is_sensitive: bool
    all_detected: list[Detection]
    block_detected: list[Detection]
    review_detected: list[Detection]
    sensitive_detected: list[Detection]


class ErrorCallbackPayload(BaseModel):
    """Payload POSTed by the service to Lychee's results endpoint on failure."""

    photo_id: str
    status: str = "error"
    error_code: str
    """Machine-readable error code (e.g. ``"corrupt_file"``, ``"internal_error"``)."""
    message: str
    """Human-readable description of the failure."""


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response body for ``GET /health``."""

    status: str
    """``"ok"`` when fully operational."""


# ---------------------------------------------------------------------------
# /config
# ---------------------------------------------------------------------------


class ServiceConfigResponse(BaseModel):
    """Response body for ``GET /config``."""

    config: dict[str, str]
    """Current runtime configuration values as strings (with secrets redacted)."""


# ---------------------------------------------------------------------------
# /queue
# ---------------------------------------------------------------------------


class QueueSizeResponse(BaseModel):
    """Response body for ``GET /queue``."""

    pending: int
    """Number of jobs waiting to be processed."""


class QueuePositionResponse(BaseModel):
    """Response body for ``GET /queue/{photo_id}``."""

    photo_id: str
    position: int
    """1-based rank in the pending queue.  0 means the job is currently being processed."""
