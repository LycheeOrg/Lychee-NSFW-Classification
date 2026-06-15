"""Tests for preset configurations and the preset field on AppSettings."""

import pytest
from pydantic import ValidationError

from app.config import PRESETS, AppSettings
from app.config.presets import MODERATION, NUDE_FEMALE, PERMISSIVE, SOCIAL_MEDIA, STRICT

# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


def test_all_named_presets_are_in_registry() -> None:
    for preset in [STRICT, MODERATION, NUDE_FEMALE, PERMISSIVE, SOCIAL_MEDIA]:
        assert preset.name in PRESETS
        assert PRESETS[preset.name] is preset


def test_preset_label_sets_are_valid() -> None:
    from app.config.labels import VALID_LABELS

    for preset in PRESETS.values():
        for label in preset.block.labels + preset.review.labels + preset.sensitive.labels:
            assert label in VALID_LABELS, f"{preset.name}: unknown label {label!r}"


# ---------------------------------------------------------------------------
# AppSettings.preset field
# ---------------------------------------------------------------------------


def _base() -> dict:
    return {"lychee_api_url": "http://lychee", "api_key": "key"}


def test_preset_strict_loads_block_labels() -> None:
    settings = AppSettings.model_validate({**_base(), "preset": "strict"})
    assert "BUTTOCKS_EXPOSED" in settings.block.labels
    assert "FEMALE_BREAST_EXPOSED" in settings.block.labels
    assert "MALE_BREAST_EXPOSED" in settings.block.labels


def test_preset_moderation_block_is_empty() -> None:
    settings = AppSettings.model_validate({**_base(), "preset": "moderation"})
    assert settings.block.labels == []
    assert "FEMALE_BREAST_EXPOSED" in settings.review.labels


def test_preset_nude_female_blocks_male_genitalia() -> None:
    settings = AppSettings.model_validate({**_base(), "preset": "nude_female"})
    assert "MALE_GENITALIA_EXPOSED" in settings.block.labels
    assert "ANUS_EXPOSED" in settings.block.labels
    assert "FEMALE_GENITALIA_EXPOSED" in settings.review.labels
    assert "FEMALE_BREAST_EXPOSED" in settings.sensitive.labels


def test_preset_permissive_only_blocks_genitalia_and_anus() -> None:
    settings = AppSettings.model_validate({**_base(), "preset": "permissive"})
    assert set(settings.block.labels) == {
        "FEMALE_GENITALIA_EXPOSED",
        "MALE_GENITALIA_EXPOSED",
        "ANUS_EXPOSED",
    }
    assert settings.review.labels == []


def test_preset_social_media_blocks_female_breast() -> None:
    settings = AppSettings.model_validate({**_base(), "preset": "social_media"})
    assert "FEMALE_BREAST_EXPOSED" in settings.block.labels
    assert "BUTTOCKS_EXPOSED" in settings.review.labels


def test_unknown_preset_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="Unknown preset"):
        AppSettings.model_validate({**_base(), "preset": "nonexistent"})


# ---------------------------------------------------------------------------
# Explicit fields override preset
# ---------------------------------------------------------------------------


def test_explicit_block_overrides_preset() -> None:
    settings = AppSettings.model_validate(
        {
            **_base(),
            "preset": "strict",
            "block": {"labels": ["ANUS_EXPOSED"]},
        }
    )
    # preset strict would include many more labels; explicit value wins
    assert settings.block.labels == ["ANUS_EXPOSED"]
    # review and sensitive still come from the preset
    assert len(settings.review.labels) > 0


def test_explicit_review_overrides_preset() -> None:
    settings = AppSettings.model_validate(
        {
            **_base(),
            "preset": "moderation",
            "review": {"labels": ["ANUS_EXPOSED"]},
        }
    )
    assert settings.review.labels == ["ANUS_EXPOSED"]
    # block still comes from preset (empty for moderation)
    assert settings.block.labels == []


def test_no_preset_uses_default_label_sets() -> None:
    settings = AppSettings.model_validate(_base())
    assert settings.preset is None
    # default block set
    assert "FEMALE_GENITALIA_EXPOSED" in settings.block.labels
    assert "ANUS_EXPOSED" in settings.block.labels


# ---------------------------------------------------------------------------
# Tiers are not mutually exclusive
# ---------------------------------------------------------------------------


def test_same_label_allowed_in_multiple_tiers() -> None:
    # A label can appear in both block and review with different thresholds.
    # Typical use: block when area is large, only review when area is small.
    settings = AppSettings.model_validate(
        {
            **_base(),
            "block": {
                "labels": ["FEMALE_GENITALIA_EXPOSED"],
                "area_ratio": 0.5,
            },
            "review": {
                "labels": ["FEMALE_GENITALIA_EXPOSED"],
                "area_ratio": 0.05,
            },
            "sensitive": {"labels": []},
        }
    )
    assert "FEMALE_GENITALIA_EXPOSED" in settings.block.labels
    assert "FEMALE_GENITALIA_EXPOSED" in settings.review.labels
    assert settings.block.area_ratio == 0.5
    assert settings.review.area_ratio == 0.05


def test_graduated_area_threshold_triggers_correct_tiers() -> None:
    from unittest.mock import MagicMock

    from app.config.models import LabelSetConfig
    from app.detection.detector import classify

    def _mock_settings(block_area: float, review_area: float) -> MagicMock:
        s = MagicMock()
        s.confidence_threshold = 0.1
        s.area_ratio_threshold = 0.0
        s.debug_detect_threshold = 0.0
        s.block = LabelSetConfig(
            labels=["FEMALE_GENITALIA_EXPOSED"],
            area_ratio=block_area,
        )
        s.review = LabelSetConfig(
            labels=["FEMALE_GENITALIA_EXPOSED"],
            area_ratio=review_area,
        )
        s.sensitive = LabelSetConfig(labels=[])
        return s

    # box 400x300 on 800x600 image → area_ratio = 0.25
    raw = [{"class": "FEMALE_GENITALIA_EXPOSED", "score": 0.9, "box": [0, 0, 400, 300]}]

    # 25% area: passes review (>=5%) but not block (>=50%)
    result = classify(raw, 800, 600, _mock_settings(block_area=0.5, review_area=0.05))
    assert result["should_block"] is False
    assert result["should_review"] is True

    # 25% area: passes both block (>=10%) and review (>=5%)
    result = classify(raw, 800, 600, _mock_settings(block_area=0.1, review_area=0.05))
    assert result["should_block"] is True
    assert result["should_review"] is True
