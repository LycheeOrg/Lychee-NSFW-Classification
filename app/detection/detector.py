from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

import httpx
from nudenet import NudeDetector
from PIL import Image

if TYPE_CHECKING:
    from app.config import AppSettings, LabelSetConfig

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


def _resolve(label_val: float | None, set_val: float | None, global_val: float) -> float:
    """Resolve effective threshold using the priority: label → set → global."""
    if label_val is not None:
        return label_val
    if set_val is not None:
        return set_val
    return global_val


def _check_set(
    label: str,
    confidence: float,
    area_ratio: float,
    set_cfg: LabelSetConfig,
    global_conf: float,
    global_area: float,
) -> bool:
    lt = set_cfg.label_thresholds.get(label)
    eff_conf = _resolve(lt.confidence if lt else None, set_cfg.confidence, global_conf)
    eff_area = _resolve(lt.area_ratio if lt else None, set_cfg.area_ratio, global_area)
    return confidence >= eff_conf and area_ratio >= eff_area


def classify(
    raw_detections: list[dict],
    image_width: int,
    image_height: int,
    settings: AppSettings,
) -> dict:
    """Filter detections by per-tier thresholds and classify into block/review/sensitive.

    Threshold resolution per detection per tier (highest priority first):
      label_thresholds[label].confidence → set.confidence → settings.confidence_threshold
      label_thresholds[label].area_ratio → set.area_ratio → settings.area_ratio_threshold

    Returns a dict with should_block, should_review, is_sensitive flags and the
    corresponding detected-part lists, ready for the DetectCallbackPayload schema.
    """
    total_area = image_width * image_height
    global_conf = settings.confidence_threshold
    global_area = settings.area_ratio_threshold

    block_set = set(settings.block.labels)
    review_set = set(settings.review.labels)
    sensitive_set = set(settings.sensitive.labels)

    block_detected: list[dict] = []
    review_detected: list[dict] = []
    sensitive_detected: list[dict] = []

    for d in raw_detections:
        label: str = d["class"]
        confidence: float = d["score"]
        box: list = d["box"]  # [x, y, width, height]

        det_width, det_height = int(box[2]), int(box[3])
        area_pixels = det_width * det_height
        area_ratio = area_pixels / total_area

        det = {
            "label": label,
            "confidence": confidence,
            "bbox": {
                "x": int(box[0]),
                "y": int(box[1]),
                "width": det_width,
                "height": det_height,
            },
            "area_pixels": area_pixels,
            "area_ratio": area_ratio,
        }

        if label in block_set and _check_set(label, confidence, area_ratio, settings.block, global_conf, global_area):
            block_detected.append(det)
        if label in review_set and _check_set(label, confidence, area_ratio, settings.review, global_conf, global_area):
            review_detected.append(det)
        if label in sensitive_set and _check_set(
            label, confidence, area_ratio, settings.sensitive, global_conf, global_area
        ):
            sensitive_detected.append(det)

    return {
        "should_block": bool(block_detected),
        "should_review": bool(review_detected),
        "is_sensitive": bool(sensitive_detected),
        "block_detected": block_detected,
        "review_detected": review_detected,
        "sensitive_detected": sensitive_detected,
    }
