# Choose a Preset

_Status: Active | Last updated: June 15, 2026_

Presets provide curated label sets for common use cases. Setting `VISION_NSFW_PRESET` is the fastest way to configure the service without specifying individual labels.

---

## Available presets

### `strict` — no nudity at all

Suitable for family-friendly libraries, children's platforms, or any service where all nudity should be invisible to end users.

| Tier | Labels |
|---|---|
| block | `BUTTOCKS_EXPOSED`, `FEMALE_BREAST_EXPOSED`, `FEMALE_GENITALIA_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `MALE_BREAST_EXPOSED`, `ANUS_EXPOSED` |
| review | `FEMALE_BREAST_COVERED`, `FEMALE_GENITALIA_COVERED`, `BUTTOCKS_COVERED`, `ANUS_COVERED` |
| sensitive | `BELLY_EXPOSED`, `ARMPITS_EXPOSED`, `FEET_EXPOSED` |

```dotenv
VISION_NSFW_PRESET=strict
```

---

### `moderation` — human review for all nudity

Nothing is hidden automatically. All detected nudity is held for a human moderator to approve or reject before the photo becomes public. Use this when you want full manual control over what your users see.

| Tier | Labels |
|---|---|
| block | _(empty)_ |
| review | `FEMALE_BREAST_EXPOSED`, `FEMALE_GENITALIA_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `MALE_BREAST_EXPOSED`, `BUTTOCKS_EXPOSED`, `ANUS_EXPOSED` |
| sensitive | `FEMALE_BREAST_COVERED`, `FEMALE_GENITALIA_COVERED`, `BUTTOCKS_COVERED`, `ANUS_COVERED`, `BELLY_EXPOSED` |

```dotenv
VISION_NSFW_PRESET=moderation
```

---

### `nude_female` — nude female photography

Tailored for boudoir, fine-art nude, or figure photography collections where female nudity is expected and acceptable but male genitalia and anus should always be blocked.

| Tier | Labels |
|---|---|
| block | `MALE_GENITALIA_EXPOSED`, `ANUS_EXPOSED` |
| review | `FEMALE_GENITALIA_EXPOSED` |
| sensitive | `FEMALE_BREAST_EXPOSED`, `BUTTOCKS_EXPOSED`, `FEMALE_BREAST_COVERED`, `FEMALE_GENITALIA_COVERED`, `BUTTOCKS_COVERED`, `ANUS_COVERED` |

```dotenv
VISION_NSFW_PRESET=nude_female
```

---

### `permissive` — art or medical context

Only the most explicit content (genitalia and anus) is blocked. Partial nudity is flagged as sensitive but not hidden. Suitable for fine-art photography archives, medical image libraries, or adult platforms.

| Tier | Labels |
|---|---|
| block | `FEMALE_GENITALIA_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `ANUS_EXPOSED` |
| review | _(empty)_ |
| sensitive | `FEMALE_BREAST_EXPOSED`, `MALE_BREAST_EXPOSED`, `BUTTOCKS_EXPOSED` |

```dotenv
VISION_NSFW_PRESET=permissive
```

---

### `social_media` — platform content policy

Mirrors the content policies of major social media platforms (e.g. Instagram): female breasts and all genitalia are blocked, buttocks go for review, covered intimate parts are marked sensitive.

| Tier | Labels |
|---|---|
| block | `FEMALE_BREAST_EXPOSED`, `FEMALE_GENITALIA_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `ANUS_EXPOSED` |
| review | `BUTTOCKS_EXPOSED`, `MALE_BREAST_EXPOSED` |
| sensitive | `FEMALE_BREAST_COVERED`, `FEMALE_GENITALIA_COVERED`, `BUTTOCKS_COVERED`, `ANUS_COVERED`, `BELLY_EXPOSED` |

```dotenv
VISION_NSFW_PRESET=social_media
```

---

## Using a preset as a starting point

Presets set the **defaults** for `block`, `review`, and `sensitive`. Any explicit tier setting you add **overrides** only that tier; the rest still come from the preset.

**Example:** Use `strict` but move female breast exposure to `review` instead of `block`:

```dotenv
VISION_NSFW_PRESET=strict
VISION_NSFW_BLOCK='{"labels": ["BUTTOCKS_EXPOSED", "FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "MALE_BREAST_EXPOSED", "ANUS_EXPOSED"]}'
VISION_NSFW_REVIEW='{"labels": ["FEMALE_BREAST_EXPOSED", "FEMALE_BREAST_COVERED", "FEMALE_GENITALIA_COVERED", "BUTTOCKS_COVERED", "ANUS_COVERED"]}'
```

Or use the `__` sub-key form to override only the labels, keeping any tier-level thresholds you added:

```dotenv
VISION_NSFW_PRESET=strict
VISION_NSFW_BLOCK__LABELS='["BUTTOCKS_EXPOSED", "FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"]'
```

---

## Next steps

- [Configure classification tiers](tune-thresholds.md) — fine-tune confidence and area thresholds per tier or per label.
- [Configuration Reference](../3-reference/configuration.md) — full variable reference.

---

*Last updated: June 15, 2026*
