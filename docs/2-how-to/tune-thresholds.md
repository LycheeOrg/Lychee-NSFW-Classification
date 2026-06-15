# Tune Detection Thresholds

_Status: Active | Last updated: June 15, 2026_

This guide explains when and how to adjust the four classification thresholds to suit your library and tolerance for false positives or missed detections.

See [Core Concepts](../1-concepts/README.md) for a full description of how the classification logic works.

---

## The four thresholds

| Variable | Default | Controls |
|---|---|---|
| `VISION_NSFW_CONFIDENCE_THRESHOLD` | `0.1` | Minimum confidence to include a detection at all |
| `VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD` | `0.05` | Minimum confidence to trigger the always-block test |
| `VISION_NSFW_UNSAFE_CONFIDENCE_THRESHOLD` | `0.3` | Minimum confidence for a detection to contribute to the area sum |
| `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD` | `0.02` | Fraction of image area the unsafe detections must cover to fail |

---

## Common tuning scenarios

### Too many false positives (safe images marked unsafe)

The service is flagging images you consider acceptable.

1. **Raise `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD`** (e.g. `0.05`) — require more of the image to be covered by unsafe content before failing. This is the most effective control for borderline images.
2. **Raise `VISION_NSFW_CONFIDENCE_THRESHOLD`** (e.g. `0.2`) — discard lower-confidence detections entirely. Use this if NudeNet is producing many spurious labels on ambiguous regions.
3. **Raise `VISION_NSFW_UNSAFE_CONFIDENCE_THRESHOLD`** (e.g. `0.5`) — require higher confidence before a detection contributes to the area sum. This narrows the unsafe-area calculation to high-certainty detections only.

### Too many false negatives (unsafe images marked safe)

The service is passing images you consider unacceptable.

1. **Lower `VISION_NSFW_CONFIDENCE_THRESHOLD`** (e.g. `0.05`) — capture lower-confidence detections. Be aware this may also increase false positives.
2. **Lower `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD`** (e.g. `0.005`) — flag unsafe content even when it covers a smaller portion of the image.
3. **Lower `VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD`** — trigger the always-block test with even lower-confidence detections for always-block categories.

### Strict mode (block any explicit content regardless of area)

Set `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD=0.0`. Any detection that passes the confidence filter in the `UNSAFE_PARTS` set will fail the area test, since any non-zero area exceeds zero.

### Permissive mode (artistic nudity acceptable)

1. Set `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD=0.15` — only flag images where explicit content is dominant.
2. Set `VISION_NSFW_CONFIDENCE_THRESHOLD=0.5` — ignore uncertain detections.

Keep `VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD` low regardless — always-block categories are non-negotiable.

---

## How to apply changes

Set the variable in your `.env` file and restart the container:

```bash
# .env
VISION_NSFW_CONFIDENCE_THRESHOLD=0.2
VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD=0.05
```

```bash
docker restart <container-name>
```

No code changes or image rebuild are required. All thresholds are read at startup from environment variables.

---

## Recommended workflow

1. Start with the defaults.
2. Collect a sample of images the service classifies incorrectly.
3. For each false positive: identify which detection triggered the failure and whether raising `VISION_NSFW_CONFIDENCE_THRESHOLD` or `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD` would have prevented it.
4. For each false negative: check whether the missed detection was below `VISION_NSFW_CONFIDENCE_THRESHOLD` or whether the area simply did not cross `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD`.
5. Adjust one variable at a time and re-evaluate.

---

*Last updated: June 15, 2026*
