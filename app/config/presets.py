"""Named presets for label-set configuration.

A preset is a curated combination of block / review / sensitive label sets.
Use the ``VISION_NSFW_PRESET`` environment variable to load one by name; any
explicit ``VISION_NSFW_BLOCK``, ``VISION_NSFW_REVIEW``, or
``VISION_NSFW_SENSITIVE`` values still override the preset defaults.

Available presets
-----------------
strict          Block all exposed nudity; review covered intimate parts.
                Suitable for family-friendly or children's services.

moderation      Nothing is blocked outright; all nudity is sent for human
                review.  Suitable for platforms that want a manual approval
                workflow before images become public.

nude_female     Tailored for nude female photography (boudoir, fine-art).
                Male genitalia and anus are always blocked; female genitalia
                goes to moderation; remaining nudity is marked sensitive.

permissive      Only hard-core explicit content (genitalia / anus) is blocked.
                Suitable for adult-art or medical contexts where partial nudity
                is expected.

social_media    Mirrors typical social-media content policies (female breasts
                and all genitalia blocked, buttocks flagged for review).
"""

from dataclasses import dataclass

from app.config.models import LabelSetConfig


@dataclass(frozen=True)
class LabelPreset:
    """A named, immutable combination of block / review / sensitive label sets."""

    name: str
    description: str
    block: LabelSetConfig
    review: LabelSetConfig
    sensitive: LabelSetConfig


# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

STRICT = LabelPreset(
    name="strict",
    description=(
        "Block all exposed nudity. Covered intimate parts are flagged as "
        "sensitive. Suitable for family-friendly or children's services."
    ),
    block=LabelSetConfig(
        labels=[
            "BUTTOCKS_EXPOSED",
            "FEMALE_BREAST_EXPOSED",
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "MALE_BREAST_EXPOSED",
            "ANUS_EXPOSED",
        ]
    ),
    review=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_COVERED",
            "FEMALE_GENITALIA_COVERED",
            "BUTTOCKS_COVERED",
            "ANUS_COVERED",
        ]
    ),
    sensitive=LabelSetConfig(
        labels=[
            "BELLY_EXPOSED",
            "ARMPITS_EXPOSED",
            "FEET_EXPOSED",
        ]
    ),
)

MODERATION = LabelPreset(
    name="moderation",
    description=(
        "Nothing blocked outright; all nudity is sent for human review before "
        "becoming public. Suitable for platforms with a manual approval workflow."
    ),
    block=LabelSetConfig(labels=[]),
    review=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_EXPOSED",
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "MALE_BREAST_EXPOSED",
            "BUTTOCKS_EXPOSED",
            "ANUS_EXPOSED",
        ]
    ),
    sensitive=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_COVERED",
            "FEMALE_GENITALIA_COVERED",
            "BUTTOCKS_COVERED",
            "ANUS_COVERED",
            "BELLY_EXPOSED",
        ]
    ),
)

NUDE_FEMALE = LabelPreset(
    name="nude_female",
    description=(
        "Tailored for nude female photography (boudoir, fine-art nude). "
        "Male genitalia and anus are always blocked. Female genitalia is sent "
        "for moderation. All other nudity is marked sensitive."
    ),
    block=LabelSetConfig(
        labels=[
            "MALE_GENITALIA_EXPOSED",
            "ANUS_EXPOSED",
        ]
    ),
    review=LabelSetConfig(
        labels=[
            "FEMALE_GENITALIA_EXPOSED",
        ]
    ),
    sensitive=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_EXPOSED",
            "BUTTOCKS_EXPOSED",
            "FEMALE_BREAST_COVERED",
            "FEMALE_GENITALIA_COVERED",
            "BUTTOCKS_COVERED",
            "ANUS_COVERED",
        ]
    ),
)

PERMISSIVE = LabelPreset(
    name="permissive",
    description=(
        "Only hard-core explicit content (genitalia and anus) is blocked. "
        "Partial nudity is marked sensitive. Suitable for adult-art or "
        "medical contexts where nudity is expected and acceptable."
    ),
    block=LabelSetConfig(
        labels=[
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "ANUS_EXPOSED",
        ]
    ),
    review=LabelSetConfig(labels=[]),
    sensitive=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_EXPOSED",
            "MALE_BREAST_EXPOSED",
            "BUTTOCKS_EXPOSED",
        ]
    ),
)

SOCIAL_MEDIA = LabelPreset(
    name="social_media",
    description=(
        "Mirrors typical social-media content policies (e.g. Instagram). "
        "Female breasts and all genitalia are blocked; buttocks are flagged "
        "for review; covered intimate parts are marked sensitive."
    ),
    block=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_EXPOSED",
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "ANUS_EXPOSED",
        ]
    ),
    review=LabelSetConfig(
        labels=[
            "BUTTOCKS_EXPOSED",
            "MALE_BREAST_EXPOSED",
        ]
    ),
    sensitive=LabelSetConfig(
        labels=[
            "FEMALE_BREAST_COVERED",
            "FEMALE_GENITALIA_COVERED",
            "BUTTOCKS_COVERED",
            "ANUS_COVERED",
            "BELLY_EXPOSED",
        ]
    ),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PRESETS: dict[str, LabelPreset] = {p.name: p for p in [STRICT, MODERATION, NUDE_FEMALE, PERMISSIVE, SOCIAL_MEDIA]}
