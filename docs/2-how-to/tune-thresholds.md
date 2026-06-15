# Configure Classification Tiers

_Status: Active | Last updated: June 15, 2026_

This guide explains how to tune the confidence and area thresholds that control which detections trigger each classification tier.

For label selection and preset configuration, see [Choose a preset](choose-a-preset.md) first.

---

## Threshold hierarchy

Every detection must pass two tests before it is added to a tier's detected list:

```
detection.score  ≥  effective_confidence_threshold
detection.area_ratio  ≥  effective_area_ratio_threshold
```

Both thresholds are resolved per-detection per-tier using a three-level priority chain:

```
label_thresholds[label].value    (highest priority)
        │ if None
        ▼
  set.value                      (tier-level default)
        │ if None
        ▼
global threshold                 (lowest priority / global fallback)
```

This means you can set a strict default for the whole block tier, then relax it for a single label within that tier — without touching anything else.

---

## Global thresholds

Set in `.env` or via environment variables. Used as the fallback when no tier or label threshold is configured.

| Variable | Default | Effect |
|---|---|---|
| `VISION_NSFW_CONFIDENCE_THRESHOLD` | `0.1` | Minimum NudeNet score for any detection to trigger any tier. |
| `VISION_NSFW_AREA_RATIO_THRESHOLD` | `0.0` | Minimum image fraction a detection must cover. `0.0` = no area filter. |
| `VISION_NSFW_DEBUG_DETECT_THRESHOLD` | `0.0` | Absolute confidence floor **before** tier evaluation. Detections below this value are discarded entirely — they will not appear in `all_detected` or any tier list. Useful for suppressing near-zero-confidence noise from the callback payload without affecting tier thresholds. |

```dotenv
VISION_NSFW_CONFIDENCE_THRESHOLD=0.15
VISION_NSFW_AREA_RATIO_THRESHOLD=0.01

# Strip out any NudeNet detection below 1% confidence before processing
VISION_NSFW_DEBUG_DETECT_THRESHOLD=0.01
```

---

## Tier-level thresholds

Each tier accepts a `confidence` and/or `area_ratio` value that overrides the global defaults for all labels in that tier.

**Example:** Require higher confidence for the block tier than for sensitive:

```dotenv
VISION_NSFW_BLOCK__CONFIDENCE=0.7
VISION_NSFW_SENSITIVE__CONFIDENCE=0.3
```

Or as a JSON object (equivalent):

```dotenv
VISION_NSFW_BLOCK='{"labels": ["FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"], "confidence": 0.7}'
```

---

## Per-label thresholds

Use `label_thresholds` inside a tier config to override thresholds for specific labels. Keys must be labels already listed in the tier's `labels` array.

**Example:** The block tier uses a high confidence by default, but `ANUS_EXPOSED` is considered high-risk enough to trigger even at low confidence:

```dotenv
VISION_NSFW_BLOCK='{
  "labels": ["FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"],
  "confidence": 0.7,
  "label_thresholds": {
    "ANUS_EXPOSED": {"confidence": 0.1}
  }
}'
```

Both `confidence` and `area_ratio` can be set independently per label:

```dotenv
VISION_NSFW_REVIEW='{
  "labels": ["BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED"],
  "label_thresholds": {
    "FEMALE_BREAST_EXPOSED": {"confidence": 0.6, "area_ratio": 0.05}
  }
}'
```

---

## Same label in multiple tiers (graduated response)

Tiers are fully independent. The same label can appear in multiple tiers at once, each with its own threshold. This lets you define a **graduated response** based on how prominent the content is in the image.

**Example:** `FEMALE_GENITALIA_EXPOSED` should block only when it dominates the image (large, explicit photo), but trigger a moderation review even when it is a smaller detail:

```dotenv
VISION_NSFW_BLOCK='{
  "labels": ["FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"],
  "area_ratio": 0.5
}'
VISION_NSFW_REVIEW='{
  "labels": ["FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED", "FEMALE_BREAST_EXPOSED", "BUTTOCKS_EXPOSED"],
  "area_ratio": 0.05
}'
```

With this configuration:

| Detection area | Result |
|---|---|
| < 5 % of image | No tier triggered |
| 5 % – 50 % | `should_review: true`, `should_block: false` |
| > 50 % of image | `should_review: true`, `should_block: true` |

A detection that passes both area thresholds will appear in both `review_detected` and `block_detected` in the callback payload. Lychee can then apply its own policy: block immediately if `should_block`, else hold for review if `should_review`.

---

## Common tuning scenarios

### Too many false positives (safe images flagged)

The service is triggering on images you consider acceptable.

1. **Raise `VISION_NSFW_CONFIDENCE_THRESHOLD`** (e.g. `0.3`) — discard uncertain detections outright.
2. **Raise `VISION_NSFW_AREA_RATIO_THRESHOLD`** (e.g. `0.02`) — require a detection to cover more of the image before it counts. Prevents flags on tiny incidental regions.
3. **Raise the tier-level `confidence`** for the noisy tier only, instead of globally.

```dotenv
VISION_NSFW_REVIEW__CONFIDENCE=0.5
VISION_NSFW_REVIEW__AREA_RATIO=0.02
```

### Too many false negatives (unsafe images missed)

The service is passing images you consider unacceptable.

1. **Lower `VISION_NSFW_CONFIDENCE_THRESHOLD`** (e.g. `0.05`) — capture lower-confidence detections. Watch for increased false positives.
2. **Lower or remove the area threshold** — `VISION_NSFW_AREA_RATIO_THRESHOLD=0.0` means area is not considered at all.
3. **Set a per-label low-confidence override** for the highest-risk labels in the block tier.

```dotenv
VISION_NSFW_BLOCK='{
  "labels": ["FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED", "MALE_GENITALIA_EXPOSED"],
  "confidence": 0.5,
  "label_thresholds": {
    "ANUS_EXPOSED": {"confidence": 0.05},
    "MALE_GENITALIA_EXPOSED": {"confidence": 0.05}
  }
}'
```

### Flag any explicit content regardless of size

Set the area threshold to `0.0` (the default) and remove any per-tier area threshold:

```dotenv
VISION_NSFW_AREA_RATIO_THRESHOLD=0.0
```

Any detection that passes the confidence filter will trigger its tier, even if it covers a single pixel.

### Ignore small detections (e.g. incidental exposure in the background)

Require detections to cover at least 1% of the image at the tier level:

```dotenv
VISION_NSFW_BLOCK__AREA_RATIO=0.01
VISION_NSFW_REVIEW__AREA_RATIO=0.01
```

---

## Recommended workflow

1. Start with a [preset](choose-a-preset.md) close to your target.
2. Collect photos the service classifies incorrectly.
3. For each **false positive**: check which label triggered and whether raising the tier-level `confidence` or `area_ratio` would prevent it.
4. For each **false negative**: check whether the missed detection was below the confidence threshold or covered too small an area.
5. Adjust one variable at a time, restart the container, and re-evaluate.
6. Use per-label overrides for labels that behave differently from the rest of their tier.

---

## How to apply changes

All thresholds are read from environment variables at startup. No code changes or image rebuilds are needed — just update `.env` and restart:

```bash
docker restart <container-name>
```

---

*Last updated: June 15, 2026*
