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

**Threshold-only overrides** — to change a threshold without touching the preset's label list, omit `labels` entirely:

```dotenv
VISION_NSFW_PRESET=strict
VISION_NSFW_BLOCK__CONFIDENCE=0.85
VISION_NSFW_REVIEW__AREA_RATIO=0.02
```

The preset's block and review label lists are kept exactly as defined; only the thresholds change.

---

## Fine-tuning individual presets

You can tune each preset's thresholds independently using env vars of the form:

```
VISION_NSFW_<PRESET>__<TIER>__<FIELD>=<value>
```

This is different from the global tier overrides above: it customises a specific preset in isolation, leaving all other presets unchanged. All presets are configured at startup, so any of them can be used at any time without restarting the service.

**Examples:**

```dotenv
# Raise the confidence bar for the strict preset's block tier
VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9

# Require detections to cover at least 5 % of the image before
# nude_female's review tier triggers
VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05

# Make the moderation preset require at least 10 % confidence before review
VISION_NSFW_MODERATION__REVIEW__CONFIDENCE=0.1

# Require a minimum area before social_media blocks anything
VISION_NSFW_SOCIAL_MEDIA__BLOCK__AREA_RATIO=0.02
```

Per-preset overrides follow the same merge rules as global tier overrides: when `LABELS` is not included in the override, the preset's original label list is preserved and only the specified threshold fields are changed.

---

## Selecting a preset per request

Instead of (or in addition to) a service-level default, callers can include a `preset` field in the `POST /detect` request body. This lets Lychee apply a different policy to each photo without any service restart or reconfiguration.

```json
{
  "photo_id": "42",
  "photo_path": "2024/01/photo.jpg",
  "preset": "nude_female"
}
```

When `preset` is set in the request:
- The service-level `VISION_NSFW_PRESET` and the global tier variables (`VISION_NSFW_BLOCK`, `VISION_NSFW_REVIEW`, `VISION_NSFW_SENSITIVE`) are **ignored for this job**.
- The named preset's label sets are used, including any per-preset env overrides you configured (e.g. `VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO`).
- An unknown preset name returns `400 Bad Request` immediately.

Omitting `preset` (or setting it to `null`) falls back to the service default.

### Typical multi-preset setup

Configure all presets at startup and let callers pick:

```dotenv
# .env — no service-level default; callers always specify preset
VISION_NSFW_API_KEY=change-me
VISION_NSFW_LYCHEE_API_URL=https://lychee.example.com

# Per-preset tuning
VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9
VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05
VISION_NSFW_MODERATION__REVIEW__CONFIDENCE=0.1
```

Lychee then sends the appropriate preset with each job based on the album's policy, the user's role, or any other application logic.

---

## Next steps

- [Configure classification tiers](tune-thresholds.md) — fine-tune confidence and area thresholds per tier or per label.
- [Configuration Reference](../3-reference/configuration.md) — full variable reference including per-preset override syntax.

---

*Last updated: June 15, 2026*
