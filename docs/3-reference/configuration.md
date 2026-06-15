# Configuration Reference

_Status: Active | Last updated: June 15, 2026_

All environment variables are read at startup from the process environment or from a `.env` file in the working directory. Copy `.env.example` to `.env` and fill in the required values.

All variables use the `VISION_NSFW_` prefix. Nested tier configs support `__`-delimited sub-keys (see [Tier configuration](#tier-configuration) below).

---

## Required

| Variable | Description |
|---|---|
| `VISION_NSFW_API_KEY` | Shared secret validated on inbound requests via the `X-API-Key` header and sent on outbound callbacks to Lychee. Must match `AI_VISION_NSFW_API_KEY` in Lychee's `.env`. **Do not leave empty in production.** |
| `VISION_NSFW_LYCHEE_API_URL` | Lychee base URL for callbacks, no trailing slash. Example: `https://lychee.example.com`. |

---

## Connectivity

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_VERIFY_SSL` | `true` | Verify SSL certificates on outbound callbacks. Set to `false` for development with self-signed certificates. **Do not disable in production.** |
| `VISION_NSFW_SKIP_LYCHEE_CHECK` | `false` | Skip the Lychee connectivity check at startup. Useful when Lychee is not yet reachable. |

---

## Photo volume

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_PHOTOS_PATH` | `/data/photos` | Mount point for the shared Docker volume containing Lychee photos. `photo_path` values in requests are validated to reside within this root (path-traversal protection). |

---

## Classification — preset

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_PRESET` | _(none)_ | Load a named preset as the default for block / review / sensitive. Valid values: `strict`, `moderation`, `nude_female`, `permissive`, `social_media`. Explicit tier settings override the preset. |

See [Choose a preset](../2-how-to/choose-a-preset.md) for a description of each preset.

---

## Classification — per-preset overrides

Each named preset can be independently tuned at startup so that all presets are fully configured before any request arrives. This lets Lychee (or any other caller) select a preset per request without the service needing to be reconfigured between calls.

The env var pattern is:

```
VISION_NSFW_<PRESET>__<TIER>__<FIELD>=<value>
```

Where:
- `<PRESET>` is the preset name in upper case: `STRICT`, `MODERATION`, `NUDE_FEMALE`, `PERMISSIVE`, `SOCIAL_MEDIA`
- `<TIER>` is `BLOCK`, `REVIEW`, or `SENSITIVE`
- `<FIELD>` is `CONFIDENCE`, `AREA_RATIO`, or `LABEL_THRESHOLDS`

**Examples:**

```dotenv
# Raise the confidence bar for the strict preset's block tier
VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9

# Require detections to cover at least 5% of the image before triggering
# nude_female's review tier (reduces noise on small or background detections)
VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05

# Require a minimum area before social_media blocks anything
VISION_NSFW_SOCIAL_MEDIA__BLOCK__AREA_RATIO=0.02

# Per-label threshold within a preset tier
VISION_NSFW_STRICT__BLOCK__LABEL_THRESHOLDS='{"ANUS_EXPOSED": {"confidence": 0.1}}'
```

**Label replacement** — to replace a preset's label list entirely for one tier, set the `LABELS` subkey:

```dotenv
VISION_NSFW_PERMISSIVE__BLOCK__LABELS='["ANUS_EXPOSED", "FEMALE_GENITALIA_EXPOSED"]'
```

If `LABELS` is not set, the preset's original label list is kept and only the specified threshold fields are changed.

**Scope** — per-preset overrides apply whenever that preset is used, regardless of how it is selected (via `VISION_NSFW_PRESET`, or via the `preset` field in a `POST /detect` request). They are completely independent of each other: configuring the strict preset does not affect moderation, and vice versa.

**Priority order** (highest wins):

```
VISION_NSFW_BLOCK / REVIEW / SENSITIVE (global tier override)
        │
VISION_NSFW_<PRESET>__<TIER>__… (per-preset override)
        │
Preset base definition (label list and tier defaults)
```

The global tier variables (`VISION_NSFW_BLOCK`, etc.) only apply when no per-request preset is specified. When a `preset` field is sent in the request body, the global tier variables are ignored entirely for that job and only the preset base + per-preset overrides are used.

---

## Classification — global thresholds

These values are used as fallbacks when no tier-level or label-level threshold is configured.

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_CONFIDENCE_THRESHOLD` | `0.1` | Minimum NudeNet confidence score (`0.0–1.0`) for a detection to trigger any tier. |
| `VISION_NSFW_AREA_RATIO_THRESHOLD` | `0.0` | Minimum fraction of the image area (`0.0–1.0`) a detection must cover to trigger any tier. `0.0` = no area filter. |
| `VISION_NSFW_DEBUG_DETECT_THRESHOLD` | `0.0` | Absolute confidence floor applied **before** tier evaluation. Detections below this value are discarded entirely and will not appear in `all_detected` or any tier list. `0.0` keeps all NudeNet output. Raise (e.g. `0.01`) to suppress near-zero-confidence noise from the callback payload. |

---

## Classification — tier configuration

Each of the three tiers (block, review, sensitive) is configured as a JSON object with the following fields:

Tiers are **independent** — the same label can appear in multiple tiers simultaneously, each with its own threshold. A common pattern is to block when a detection covers a large fraction of the image and only review when it is smaller. See [Configure classification tiers](../2-how-to/tune-thresholds.md#same-label-in-multiple-tiers-graduated-response) for an example.

| Field | Type | Default | Description |
|---|---|---|---|
| `labels` | `list[str]` | _(see defaults below)_ | NudeNet labels that belong to this tier. The same label may also appear in other tiers; each tier evaluates it independently. |
| `confidence` | `float \| null` | `null` | Confidence threshold for this tier. `null` falls back to the global `confidence_threshold`. |
| `area_ratio` | `float \| null` | `null` | Area-ratio threshold for this tier. `null` falls back to the global `area_ratio_threshold`. |
| `label_thresholds` | `object` | `{}` | Per-label overrides. Keys must be labels listed in `labels`. Each value is `{"confidence": float \| null, "area_ratio": float \| null}`. |

### Setting a tier

**As a JSON object** (sets the entire tier at once):

```dotenv
VISION_NSFW_BLOCK='{"labels": ["FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"], "confidence": 0.7}'
```

**Using `__` sub-keys** (set individual fields without replacing the whole tier):

```dotenv
VISION_NSFW_BLOCK__CONFIDENCE=0.7
VISION_NSFW_BLOCK__AREA_RATIO=0.01
VISION_NSFW_BLOCK__LABELS='["FEMALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"]'
VISION_NSFW_BLOCK__LABEL_THRESHOLDS='{"ANUS_EXPOSED": {"confidence": 0.1}}'
```

### `VISION_NSFW_BLOCK`

Controls which detections set `should_block: true` in the callback.

**Default labels:** `FEMALE_GENITALIA_EXPOSED`, `MALE_GENITALIA_EXPOSED`, `ANUS_EXPOSED`

### `VISION_NSFW_REVIEW`

Controls which detections set `should_review: true` in the callback.

**Default labels:** `BUTTOCKS_EXPOSED`, `FEMALE_BREAST_EXPOSED`

### `VISION_NSFW_SENSITIVE`

Controls which detections set `is_sensitive: true` in the callback.

**Default labels:** `FEMALE_BREAST_COVERED`, `FEMALE_GENITALIA_COVERED`, `ANUS_COVERED`, `BUTTOCKS_COVERED`, `BELLY_EXPOSED`

### Valid NudeNet labels

Only these labels are accepted. Using an unknown label raises a startup error.

```
ANUS_COVERED          ANUS_EXPOSED
ARMPITS_COVERED       ARMPITS_EXPOSED
BELLY_COVERED         BELLY_EXPOSED
BUTTOCKS_COVERED      BUTTOCKS_EXPOSED
FACE_FEMALE           FACE_MALE
FEET_COVERED          FEET_EXPOSED
FEMALE_BREAST_COVERED FEMALE_BREAST_EXPOSED
FEMALE_GENITALIA_COVERED FEMALE_GENITALIA_EXPOSED
MALE_BREAST_EXPOSED   MALE_GENITALIA_EXPOSED
```

---

## Job queue

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_QUEUE_BACKEND` | `database` | Queue backend: `database` (SQLite) or `redis`. |
| `VISION_NSFW_QUEUE_MAX_SIZE` | `0` | Maximum pending jobs. `0` = unlimited. Requests beyond this limit receive `429 Too Many Requests`. |
| `VISION_NSFW_STORAGE_PATH` | `/data/queue` | Directory for the SQLite queue database (used when `queue_backend=database`). |

### Redis (when `queue_backend=redis`)

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_REDIS_HOST` | `localhost` | Redis host. |
| `VISION_NSFW_REDIS_PORT` | `6379` | Redis port. |
| `VISION_NSFW_REDIS_PASSWORD` | _(empty)_ | Redis password. Leave empty for no authentication. |
| `VISION_NSFW_REDIS_DB` | `0` | Redis logical database index. |

---

## Concurrency

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_THREAD_POOL_SIZE` | `1` | Number of threads for CPU-bound NudeNet inference. Increase only if NudeNet is confirmed thread-safe in your version. |
| `VISION_NSFW_WORKERS` | `1` | Number of Uvicorn worker processes. For higher throughput, prefer multiple container replicas instead. |

---

## Logging

| Variable | Default | Description |
|---|---|---|
| `VISION_NSFW_LOG_LEVEL` | `info` | Log level: `debug`, `info`, `warning`, `error`, `critical`. |

---

## Example `.env`

### Single-preset deployment

Use one preset as the service default, with a global confidence override:

```dotenv
# Required
VISION_NSFW_API_KEY=change-me
VISION_NSFW_LYCHEE_API_URL=https://lychee.example.com

# Use the social_media preset as a baseline
VISION_NSFW_PRESET=social_media

# Override: also flag bare male chest for review
VISION_NSFW_REVIEW__LABELS='["BUTTOCKS_EXPOSED", "MALE_BREAST_EXPOSED", "FEMALE_BREAST_EXPOSED"]'

# Require higher confidence before anything gets blocked
VISION_NSFW_BLOCK__CONFIDENCE=0.7

# But always block anus even at low confidence
VISION_NSFW_BLOCK__LABEL_THRESHOLDS='{"ANUS_EXPOSED": {"confidence": 0.1}}'
```

### Multi-preset deployment (per-request preset selection)

Configure every preset at startup so callers can choose which one to apply per request via the `preset` field in `POST /detect`:

```dotenv
# Required
VISION_NSFW_API_KEY=change-me
VISION_NSFW_LYCHEE_API_URL=https://lychee.example.com

# No service-level default — callers always specify the preset per request
# VISION_NSFW_PRESET=  (leave unset)

# Tune the strict preset: require higher confidence before blocking
VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.85

# Tune the nude_female preset: require detections to cover at least 5 % of the
# image before triggering review (reduces noise on background detections)
VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05

# Tune the moderation preset: only flag detections with at least 10 % confidence
VISION_NSFW_MODERATION__REVIEW__CONFIDENCE=0.1
```

Lychee then selects the preset per photo:

```json
{ "photo_id": "42", "photo_path": "2024/01/photo.jpg", "preset": "strict" }
```

---

*Last updated: June 15, 2026*

