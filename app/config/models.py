"""Pydantic models for label-set configuration."""

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
    def _validate_threshold_keys_subset_of_labels(self) -> "LabelSetConfig":
        orphans = sorted(set(self.label_thresholds.keys()) - set(self.labels))
        if orphans:
            raise ValueError(f"label_thresholds contains labels not present in labels: {orphans}")
        return self
