from unittest.mock import MagicMock

from app.config import LabelSetConfig, LabelThreshold
from app.detection.detector import classify


def _make_set(
    labels: list[str],
    confidence: float | None = None,
    area_ratio: float | None = None,
    label_thresholds: dict | None = None,
) -> LabelSetConfig:
    return LabelSetConfig(
        labels=labels,
        confidence=confidence,
        area_ratio=area_ratio,
        label_thresholds={k: LabelThreshold(**v) for k, v in (label_thresholds or {}).items()},
    )


def _make_settings(
    confidence_threshold: float = 0.1,
    area_ratio_threshold: float = 0.0,
    debug_detect_threshold: float = 0.0,
    block: LabelSetConfig | None = None,
    review: LabelSetConfig | None = None,
    sensitive: LabelSetConfig | None = None,
) -> MagicMock:
    s = MagicMock()
    s.confidence_threshold = confidence_threshold
    s.area_ratio_threshold = area_ratio_threshold
    s.debug_detect_threshold = debug_detect_threshold
    s.block = block if block is not None else _make_set(["ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"])
    s.review = review if review is not None else _make_set(["FEMALE_BREAST_EXPOSED", "BUTTOCKS_EXPOSED"])
    s.sensitive = sensitive if sensitive is not None else _make_set(["FEMALE_BREAST_COVERED", "BELLY_EXPOSED"])
    return s


def _make_raw(label: str, score: float, box: list[int]) -> dict:
    return {"class": label, "score": score, "box": box}


def test_classify_safe_returns_no_flags() -> None:
    result = classify([], 800, 600, _make_settings())
    assert result["should_block"] is False
    assert result["should_review"] is False
    assert result["is_sensitive"] is False
    assert result["block_detected"] == []
    assert result["review_detected"] == []
    assert result["sensitive_detected"] == []


def test_classify_block_label_sets_should_block() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 50, 50])]
    result = classify(raw, 800, 600, _make_settings())
    assert result["should_block"] is True
    assert len(result["block_detected"]) == 1
    assert result["block_detected"][0]["label"] == "ANUS_EXPOSED"
    assert result["should_review"] is False
    assert result["is_sensitive"] is False


def test_classify_review_label_sets_should_review() -> None:
    raw = [_make_raw("FEMALE_BREAST_EXPOSED", 0.8, [0, 0, 100, 100])]
    result = classify(raw, 800, 600, _make_settings())
    assert result["should_review"] is True
    assert len(result["review_detected"]) == 1
    assert result["should_block"] is False
    assert result["is_sensitive"] is False


def test_classify_sensitive_label_sets_is_sensitive() -> None:
    raw = [_make_raw("FEMALE_BREAST_COVERED", 0.7, [0, 0, 80, 80])]
    result = classify(raw, 800, 600, _make_settings())
    assert result["is_sensitive"] is True
    assert len(result["sensitive_detected"]) == 1
    assert result["should_block"] is False
    assert result["should_review"] is False


# ---------------------------------------------------------------------------
# Confidence threshold resolution
# ---------------------------------------------------------------------------


def test_classify_global_confidence_filters_detection() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.05, [0, 0, 800, 600])]
    result = classify(raw, 800, 600, _make_settings(confidence_threshold=0.1))
    assert result["should_block"] is False
    assert result["block_detected"] == []


def test_classify_set_confidence_overrides_global() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.15, [0, 0, 800, 600])]
    # global threshold 0.1 would pass, but set threshold 0.5 should filter it
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            confidence_threshold=0.1,
            block=_make_set(["ANUS_EXPOSED"], confidence=0.5),
        ),
    )
    assert result["should_block"] is False


def test_classify_label_confidence_overrides_set() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.4, [0, 0, 800, 600])]
    # set threshold 0.5 would filter it, but per-label 0.3 should pass it
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            block=_make_set(
                ["ANUS_EXPOSED"],
                confidence=0.5,
                label_thresholds={"ANUS_EXPOSED": {"confidence": 0.3}},
            ),
        ),
    )
    assert result["should_block"] is True


# ---------------------------------------------------------------------------
# Area-ratio threshold resolution
# ---------------------------------------------------------------------------


def test_classify_global_area_ratio_filters_small_detection() -> None:
    # box 10x10 = 100 pixels out of 800*600 = 480000 → ratio ≈ 0.000208
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 10, 10])]
    result = classify(raw, 800, 600, _make_settings(area_ratio_threshold=0.01))
    assert result["should_block"] is False


def test_classify_set_area_ratio_overrides_global() -> None:
    # box 80x60 → ratio = 4800/480000 = 0.01
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 80, 60])]
    # global 0.0 would pass, set 0.05 should filter
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            area_ratio_threshold=0.0,
            block=_make_set(["ANUS_EXPOSED"], area_ratio=0.05),
        ),
    )
    assert result["should_block"] is False


def test_classify_label_area_ratio_overrides_set() -> None:
    # box 80x60 → ratio 0.01; set requires 0.05, label override requires 0.005
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 80, 60])]
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            block=_make_set(
                ["ANUS_EXPOSED"],
                area_ratio=0.05,
                label_thresholds={"ANUS_EXPOSED": {"area_ratio": 0.005}},
            ),
        ),
    )
    assert result["should_block"] is True


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------


def test_classify_label_not_in_any_set_ignored() -> None:
    raw = [_make_raw("FACE_FEMALE", 0.9, [0, 0, 100, 100])]
    result = classify(raw, 800, 600, _make_settings())
    assert result["should_block"] is False
    assert result["should_review"] is False
    assert result["is_sensitive"] is False


def test_classify_label_in_block_and_review() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 50, 50])]
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            block=_make_set(["ANUS_EXPOSED"]),
            review=_make_set(["ANUS_EXPOSED"]),
        ),
    )
    assert result["should_block"] is True
    assert result["should_review"] is True
    assert len(result["block_detected"]) == 1
    assert len(result["review_detected"]) == 1


def test_classify_single_detection_in_all_three_tiers() -> None:
    """Tiers are independent: one detection can trigger block, review, and sensitive simultaneously."""
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 50, 50])]
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            block=_make_set(["ANUS_EXPOSED"]),
            review=_make_set(["ANUS_EXPOSED"]),
            sensitive=_make_set(["ANUS_EXPOSED"]),
        ),
    )
    assert result["should_block"] is True
    assert result["should_review"] is True
    assert result["is_sensitive"] is True
    assert len(result["block_detected"]) == 1
    assert len(result["review_detected"]) == 1
    assert len(result["sensitive_detected"]) == 1
    assert result["block_detected"][0] is result["review_detected"][0] is result["sensitive_detected"][0]


def test_classify_block_does_not_prevent_review_or_sensitive() -> None:
    """Triggering block must not suppress review or sensitive checks on the same detection."""
    raw = [_make_raw("FEMALE_GENITALIA_EXPOSED", 0.95, [0, 0, 200, 200])]
    result = classify(
        raw,
        800,
        600,
        _make_settings(
            block=_make_set(["FEMALE_GENITALIA_EXPOSED"]),
            review=_make_set(["FEMALE_GENITALIA_EXPOSED"]),
            sensitive=_make_set(["FEMALE_GENITALIA_EXPOSED"]),
        ),
    )
    assert result["should_block"] is True
    assert result["should_review"] is True
    assert result["is_sensitive"] is True


def test_classify_area_pixels_and_ratio_computed() -> None:
    raw = [_make_raw("FEMALE_BREAST_EXPOSED", 0.8, [0, 0, 80, 60])]
    result = classify(raw, 800, 600, _make_settings())
    det = result["review_detected"][0]
    assert det["area_pixels"] == 80 * 60
    assert abs(det["area_ratio"] - (80 * 60 / (800 * 600))) < 1e-9


def test_classify_bbox_values_are_int() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [10, 20, 100, 150])]
    result = classify(raw, 800, 600, _make_settings())
    bbox = result["block_detected"][0]["bbox"]
    assert isinstance(bbox["x"], int)
    assert isinstance(bbox["y"], int)
    assert isinstance(bbox["width"], int)
    assert isinstance(bbox["height"], int)
