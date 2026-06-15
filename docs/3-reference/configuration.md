# Configuration Reference

_Status: Active | Last updated: June 15, 2026_

All environment variables are read at startup from the environment or from a `.env` file in the working directory. Copy `.env.example` to `.env` and fill in the required values.

---

## Authentication

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_API_KEY` | _(empty)_ | Shared secret validated on inbound requests via the `X-API-Key` header. When empty, authentication is disabled — **do not leave empty in production**. |

---

## Lychee connectivity

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_LYCHEE_URL` | _(empty)_ | Base URL of the Lychee instance, no trailing slash. Used when the service needs to call back to Lychee (e.g. to report errors). Example: `https://lychee.example.com`. |
| `VISION_NSFW_LYCHEE_API_KEY` | _(empty)_ | API key sent on outbound requests to Lychee. Must match the key configured in Lychee. |

---

## Detection thresholds

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_CONFIDENCE_THRESHOLD` | `0.1` | Minimum NudeNet confidence score (`0.0–1.0`) for a detection to be included in the response and to participate in safety tests. Detections below this value are silently discarded. |
| `VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD` | `0.05` | Minimum confidence for an always-block detection to trigger an unsafe verdict. Intentionally lower than `VISION_NSFW_CONFIDENCE_THRESHOLD` so that always-block categories are not missed. |
| `VISION_NSFW_UNSAFE_CONFIDENCE_THRESHOLD` | `0.3` | Minimum confidence for a detection to contribute its area to the unsafe-area accumulator. |
| `VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD` | `0.02` | Fraction of image area (`0.0–1.0`) that unsafe detections must collectively cover to trigger an unsafe verdict. `0.02` = 2% of the image. Set to `0.0` to flag any unsafe detection regardless of area. |

See [Tune Detection Thresholds](../2-how-to/tune-thresholds.md) for guidance on adjusting these values.

---

## Always-block categories

The following NudeNet labels always produce `is_safe: false` when their confidence exceeds `VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD`, regardless of image area covered:

- `ANUS_EXPOSED`
- `MALE_GENITALIA_EXPOSED`

These are hardcoded and cannot be changed via configuration. All other sensitive categories are governed by the area-based test.

---

## Example `.env`

```dotenv
VISION_NSFW_API_KEY=change-me

VISION_NSFW_LYCHEE_URL=https://lychee.example.com
VISION_NSFW_LYCHEE_API_KEY=

# Detection thresholds
VISION_NSFW_CONFIDENCE_THRESHOLD=0.1
VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD=0.05
VISION_NSFW_UNSAFE_CONFIDENCE_THRESHOLD=0.3
VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD=0.02
```

---

*Last updated: June 15, 2026*
