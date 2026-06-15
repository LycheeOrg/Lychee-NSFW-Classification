import os
import tempfile

import httpx
from nudenet import NudeDetector
from PIL import Image

from app.config import settings

# Parts that are always considered unsafe regardless of area ratio
_ALWAYS_BLOCK = frozenset({"ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"})

# Parts that are unsafe only when they cover enough of the image
_UNSAFE_PARTS = frozenset(
    {"FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"}
)

_detector: NudeDetector | None = None


def _get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector


def _run(image_path: str) -> tuple[list[dict], int, int]:
    with Image.open(image_path) as img:
        width, height = img.size
    raw = _get_detector().detect(image_path)
    return raw, width, height


def detect_from_path(image_path: str) -> tuple[list[dict], int, int]:
    return _run(image_path)


def detect_from_url(image_url: str) -> tuple[list[dict], int, int]:
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(image_url)
        response.raise_for_status()

    suffix = ".jpg"
    content_type = response.headers.get("content-type", "")
    if "png" in content_type:
        suffix = ".png"
    elif "webp" in content_type:
        suffix = ".webp"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        return _run(tmp_path)
    finally:
        os.unlink(tmp_path)


def classify(
    raw_detections: list[dict], image_width: int, image_height: int
) -> tuple[bool, list[dict]]:
    """
    Filter detections by confidence, compute area_ratio per detection, and
    determine whether the image is unsafe.

    Returns (is_safe, detections) where detections is a list of dicts ready
    for the DetectResponse schema.
    """
    total_area = image_width * image_height
    detections = []
    unsafe_area = 0.0
    always_blocked = False

    for d in raw_detections:
        label: str = d["class"]
        confidence: float = d["score"]
        box: list = d["box"]  # [x, y, width, height]

        if confidence < settings.confidence_threshold:
            continue

        det_width, det_height = box[2], box[3]
        area = det_width * det_height
        area_ratio = area / total_area

        detections.append(
            {
                "label": label,
                "confidence": confidence,
                "bbox": {
                    "x": box[0],
                    "y": box[1],
                    "width": det_width,
                    "height": det_height,
                },
                "area_ratio": area_ratio,
            }
        )

        if label in _ALWAYS_BLOCK and confidence > settings.confidence_banned_threshold:
            always_blocked = True

        if label in _UNSAFE_PARTS and confidence > settings.unsafe_confidence_threshold:
            unsafe_area += area

    area_unsafe = (unsafe_area / total_area) > settings.unsafe_area_ratio_threshold
    is_safe = not always_blocked and not area_unsafe
    return is_safe, detections
