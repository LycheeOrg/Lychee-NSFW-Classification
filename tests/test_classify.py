from unittest.mock import patch

from app.detection.detector import classify


def _make_raw(label: str, score: float, box: list[int]) -> dict:
    return {"class": label, "score": score, "box": box}


def test_classify_safe_returns_true() -> None:
    with patch("app.detection.detector.settings") as s:
        s.confidence_threshold = 0.1
        s.confidence_banned_threshold = 0.05
        s.unsafe_confidence_threshold = 0.3
        s.unsafe_area_ratio_threshold = 0.02
        is_safe, dets = classify([], 800, 600)

    assert is_safe is True
    assert dets == []


def test_classify_always_blocked_label() -> None:
    raw = [_make_raw("ANUS_EXPOSED", 0.9, [0, 0, 50, 50])]
    with patch("app.detection.detector.settings") as s:
        s.confidence_threshold = 0.1
        s.confidence_banned_threshold = 0.05
        s.unsafe_confidence_threshold = 0.3
        s.unsafe_area_ratio_threshold = 0.02
        is_safe, dets = classify(raw, 800, 600)

    assert is_safe is False
    assert len(dets) == 1
    assert dets[0]["label"] == "ANUS_EXPOSED"


def test_classify_below_confidence_threshold_filtered() -> None:
    raw = [_make_raw("FEMALE_GENITALIA_EXPOSED", 0.05, [0, 0, 800, 600])]
    with patch("app.detection.detector.settings") as s:
        s.confidence_threshold = 0.1
        s.confidence_banned_threshold = 0.05
        s.unsafe_confidence_threshold = 0.3
        s.unsafe_area_ratio_threshold = 0.02
        is_safe, dets = classify(raw, 800, 600)

    assert is_safe is True
    assert dets == []


def test_classify_large_unsafe_area() -> None:
    # covers >2% of 800x600=480000; box 400x300=120000 → 25%
    raw = [_make_raw("FEMALE_GENITALIA_EXPOSED", 0.9, [0, 0, 400, 300])]
    with patch("app.detection.detector.settings") as s:
        s.confidence_threshold = 0.1
        s.confidence_banned_threshold = 0.05
        s.unsafe_confidence_threshold = 0.3
        s.unsafe_area_ratio_threshold = 0.02
        is_safe, dets = classify(raw, 800, 600)

    assert is_safe is False


def test_classify_area_ratio_computed() -> None:
    raw = [_make_raw("FEMALE_BREAST_EXPOSED", 0.8, [0, 0, 80, 60])]
    with patch("app.detection.detector.settings") as s:
        s.confidence_threshold = 0.1
        s.confidence_banned_threshold = 0.05
        s.unsafe_confidence_threshold = 0.3
        s.unsafe_area_ratio_threshold = 0.02
        _, dets = classify(raw, 800, 600)

    assert len(dets) == 1
    assert abs(dets[0]["area_ratio"] - (80 * 60 / (800 * 600))) < 1e-9
