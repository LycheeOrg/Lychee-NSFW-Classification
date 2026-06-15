"""Pydantic models for label-set configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config.labels import VALID_LABELS


class LabelThreshold(BaseModel):
    """Per-label confidence and area-ratio overrides within a set."""

    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    """Override confidence threshold for this specific label. ``None`` falls back to the set threshold."""

    area_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    """Override area-ratio threshold for this specific label. ``None`` falls back to the set threshold."""


class LabelSetConfig(BaseModel):
    """Configuration for one classification tier (block / review / sensitive).

    Threshold resolution order (highest priority first):
      label_thresholds[label].confidence → confidence → (global fallback)
      label_thresholds[label].area_ratio → area_ratio → (global fallback)
    """

    labels: list[str] = []
    """Labels that belong to this tier."""

    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    """Default confidence threshold for all labels in this set.
    ``None`` means fall back to the global ``confidence_threshold``."""

    area_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    """Default area-ratio threshold for all labels in this set.
    ``None`` means fall back to the global ``area_ratio_threshold``."""

    label_thresholds: dict[str, LabelThreshold] = {}
    """Per-label threshold overrides, keyed by label name."""

    @field_validator("labels", mode="after")
    @classmethod
    def _validate_labels(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - VALID_LABELS)
        if unknown:
            raise ValueError(f"Unknown label(s): {unknown}. Valid labels are: {sorted(VALID_LABELS)}")
        return value

    @field_validator("label_thresholds", mode="after")
    @classmethod
    def _validate_threshold_keys(cls, value: dict[str, LabelThreshold]) -> dict[str, LabelThreshold]:
        unknown = sorted(set(value.keys()) - VALID_LABELS)
        if unknown:
            raise ValueError(
                f"Unknown label(s) in label_thresholds: {unknown}. Valid labels are: {sorted(VALID_LABELS)}"
            )
        return value

    @model_validator(mode="after")
    def _validate_threshold_keys_subset_of_labels(self) -> LabelSetConfig:
        orphans = sorted(set(self.label_thresholds.keys()) - set(self.labels))
        if orphans:
            raise ValueError(f"label_thresholds contains labels not present in labels: {orphans}")
        return self


class PresetTierOverride(BaseModel):
    """Optional per-preset threshold/label overrides for one classification tier.

    All fields default to ``None`` / empty, meaning "inherit from the preset definition".
    Only the fields you set are applied on top of the base preset tier.

    Env var examples (with ``VISION_NSFW_STRICT__`` prefix for the *strict* preset):
      ``VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9``
      ``VISION_NSFW_STRICT__REVIEW__AREA_RATIO=0.05``
      ``VISION_NSFW_STRICT__BLOCK__LABELS='["ANUS_EXPOSED"]'``  (replaces preset labels)
    """

    labels: list[str] | None = None
    """Replace the preset's label list for this tier.  ``None`` keeps the preset labels."""

    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    """Override the per-set confidence threshold.  ``None`` keeps the preset default."""

    area_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    """Override the per-set area-ratio threshold.  ``None`` keeps the preset default."""

    label_thresholds: dict[str, LabelThreshold] = {}
    """Per-label threshold overrides.  Empty dict keeps the preset label_thresholds."""

    @field_validator("labels", mode="after")
    @classmethod
    def _validate_labels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        unknown = sorted(set(value) - VALID_LABELS)
        if unknown:
            raise ValueError(f"Unknown label(s): {unknown}. Valid labels are: {sorted(VALID_LABELS)}")
        return value

    @field_validator("label_thresholds", mode="after")
    @classmethod
    def _validate_threshold_keys(cls, value: dict[str, LabelThreshold]) -> dict[str, LabelThreshold]:
        unknown = sorted(set(value.keys()) - VALID_LABELS)
        if unknown:
            raise ValueError(f"Unknown label(s) in label_thresholds: {unknown}")
        return value

    def apply_to(self, base: LabelSetConfig) -> LabelSetConfig:
        """Return a new ``LabelSetConfig`` with this override merged onto *base*."""
        return LabelSetConfig(
            labels=self.labels if self.labels is not None else base.labels,
            confidence=self.confidence if self.confidence is not None else base.confidence,
            area_ratio=self.area_ratio if self.area_ratio is not None else base.area_ratio,
            label_thresholds=self.label_thresholds if self.label_thresholds else base.label_thresholds,
        )


class PresetOverride(BaseModel):
    """Per-preset configuration overrides for all three classification tiers.

    Loaded from env vars such as:
      ``VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9``
      ``VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05``

    Unset tiers are inherited unchanged from the preset definition.
    """

    block: PresetTierOverride = Field(default_factory=PresetTierOverride)
    review: PresetTierOverride = Field(default_factory=PresetTierOverride)
    sensitive: PresetTierOverride = Field(default_factory=PresetTierOverride)
