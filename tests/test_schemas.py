import pytest
from pydantic import ValidationError

from app.api.schemas import DetectRequest
from app.config import VALID_LABELS, AppSettings, LabelSetConfig, LabelThreshold


def test_detect_request_requires_photo_path() -> None:
    with pytest.raises(ValidationError):
        DetectRequest(photo_id="1")  # ty: ignore[missing-argument]


def test_detect_request_valid() -> None:
    req = DetectRequest(photo_id="1", photo_path="/data/photos/img.jpg")
    assert req.photo_id == "1"
    assert req.photo_path == "/data/photos/img.jpg"


# ---------------------------------------------------------------------------
# LabelSetConfig validation
# ---------------------------------------------------------------------------


def test_label_set_rejects_unknown_label() -> None:
    with pytest.raises(ValidationError, match="Unknown label"):
        LabelSetConfig(labels=["NOT_A_LABEL"])


def test_label_set_rejects_unknown_threshold_key() -> None:
    with pytest.raises(ValidationError, match="Unknown label"):
        LabelSetConfig(labels=["ANUS_EXPOSED"], label_thresholds={"FAKE": LabelThreshold(confidence=0.9)})


def test_label_set_rejects_threshold_key_not_in_labels() -> None:
    with pytest.raises(ValidationError, match="not present in labels"):
        LabelSetConfig(labels=["ANUS_EXPOSED"], label_thresholds={"BUTTOCKS_EXPOSED": LabelThreshold(confidence=0.9)})


def test_label_set_accepts_valid_labels() -> None:
    cfg = LabelSetConfig(labels=["ANUS_EXPOSED", "BUTTOCKS_EXPOSED"])
    assert cfg.labels == ["ANUS_EXPOSED", "BUTTOCKS_EXPOSED"]


def test_label_set_accepts_all_valid_labels() -> None:
    cfg = LabelSetConfig(labels=list(VALID_LABELS))
    assert set(cfg.labels) == VALID_LABELS


def test_label_set_accepts_empty_labels() -> None:
    cfg = LabelSetConfig(labels=[])
    assert cfg.labels == []


def test_label_set_accepts_label_threshold_matching_labels() -> None:
    cfg = LabelSetConfig(
        labels=["ANUS_EXPOSED"],
        label_thresholds={"ANUS_EXPOSED": LabelThreshold(confidence=0.9, area_ratio=0.05)},
    )
    assert cfg.label_thresholds["ANUS_EXPOSED"].confidence == 0.9
    assert cfg.label_thresholds["ANUS_EXPOSED"].area_ratio == 0.05


def test_label_set_partial_threshold_override() -> None:
    cfg = LabelSetConfig(
        labels=["ANUS_EXPOSED"],
        label_thresholds={"ANUS_EXPOSED": LabelThreshold(confidence=0.8)},
    )
    assert cfg.label_thresholds["ANUS_EXPOSED"].confidence == 0.8
    assert cfg.label_thresholds["ANUS_EXPOSED"].area_ratio is None


# ---------------------------------------------------------------------------
# AppSettings validation
# ---------------------------------------------------------------------------


def _base_settings(**overrides: object) -> dict:
    return {
        "lychee_api_url": "http://lychee",
        "api_key": "key",
        **overrides,
    }


def test_settings_defaults_are_valid() -> None:
    settings = AppSettings.model_validate(_base_settings())
    assert settings.confidence_threshold == 0.1
    assert settings.area_ratio_threshold == 0.0
    assert "ANUS_EXPOSED" in settings.block.labels
    assert settings.block.confidence is None
    assert settings.block.area_ratio is None


def test_settings_accepts_set_level_thresholds() -> None:
    settings = AppSettings.model_validate(
        _base_settings(
            block={"labels": ["ANUS_EXPOSED"], "confidence": 0.8, "area_ratio": 0.05},
        )
    )
    assert settings.block.confidence == 0.8
    assert settings.block.area_ratio == 0.05


def test_settings_accepts_label_level_thresholds() -> None:
    settings = AppSettings.model_validate(
        _base_settings(
            block={
                "labels": ["ANUS_EXPOSED"],
                "label_thresholds": {"ANUS_EXPOSED": {"confidence": 0.95}},
            },
        )
    )
    assert settings.block.label_thresholds["ANUS_EXPOSED"].confidence == 0.95


def test_settings_rejects_unknown_label_in_block() -> None:
    with pytest.raises(ValidationError, match="Unknown label"):
        AppSettings.model_validate(_base_settings(block={"labels": ["INVALID"]}))


def test_settings_rejects_unknown_label_in_review() -> None:
    with pytest.raises(ValidationError, match="Unknown label"):
        AppSettings.model_validate(_base_settings(review={"labels": ["INVALID"]}))


def test_settings_rejects_unknown_label_in_sensitive() -> None:
    with pytest.raises(ValidationError, match="Unknown label"):
        AppSettings.model_validate(_base_settings(sensitive={"labels": ["INVALID"]}))


def test_settings_rejects_threshold_key_not_in_labels() -> None:
    with pytest.raises(ValidationError, match="not present in labels"):
        AppSettings.model_validate(
            _base_settings(
                block={
                    "labels": ["ANUS_EXPOSED"],
                    "label_thresholds": {"BUTTOCKS_EXPOSED": {"confidence": 0.9}},
                }
            )
        )


def test_settings_accepts_empty_sets() -> None:
    settings = AppSettings.model_validate(
        _base_settings(
            block={"labels": []},
            review={"labels": []},
            sensitive={"labels": []},
        )
    )
    assert settings.block.labels == []
    assert settings.review.labels == []
    assert settings.sensitive.labels == []
