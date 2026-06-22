# API Reference

_Status: Active | Last updated: June 22, 2026_

Base path: `/api/nsfw`

Interactive docs are available at `http://localhost:8000/docs` when the service is running.

---

## Authentication

All endpoints except `GET /health` require the `X-API-Key` header:

```
X-API-Key: your-shared-secret
```

The value must match `VISION_NSFW_API_KEY`. Requests with a missing or incorrect key receive `401 Unauthorized`.

---

## Endpoints

### `GET /api/nsfw/health`

Returns the service operational status. No authentication required.

**Response `200 OK`**

```json
{"status": "ok"}
```

---

### `GET /api/nsfw/config`

Returns the active runtime configuration (secrets redacted) and all available preset configurations. Useful for verifying that env vars were applied correctly and for discovering which presets are available.

**Response `200 OK`**

```json
{
  "config": {
    "confidence_threshold": "0.1",
    "area_ratio_threshold": "0.0",
    "block": "{\"labels\": [\"FEMALE_GENITALIA_EXPOSED\", ...], \"confidence\": null, ...}",
    "review": "...",
    "sensitive": "...",
    "queue_backend": "database",
    "queue_max_size": "0",
    "thread_pool_size": "1",
    "verify_ssl": "true",
    "workers": "1"
  },
  "presets": {
    "default": {
      "name": "default",
      "description": "Built-in default configuration used when no preset is selected.",
      "block": {"labels": ["FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"], "confidence": null, "area_ratio": null, "label_thresholds": {}},
      "review": {"labels": ["BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED"], "confidence": null, "area_ratio": null, "label_thresholds": {}},
      "sensitive": {"labels": ["FEMALE_BREAST_COVERED", "FEMALE_GENITALIA_COVERED", "ANUS_COVERED", "BUTTOCKS_COVERED", "BELLY_EXPOSED"], "confidence": null, "area_ratio": null, "label_thresholds": {}}
    },
    "strict": {
      "name": "strict",
      "description": "Block all exposed nudity. Covered intimate parts are flagged as sensitive. ...",
      "block": {"labels": ["BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED", "..."], "...": "..."},
      "review": {"labels": ["FEMALE_BREAST_COVERED", "..."], "...": "..."},
      "sensitive": {"labels": ["BELLY_EXPOSED", "..."], "...": "..."}
    },
    "moderation": {"...": "..."},
    "nude_female": {"...": "..."},
    "permissive": {"...": "..."},
    "social_media": {"...": "..."}
  }
}
```

| Field | Type | Description |
|---|---|---|
| `config` | object | Current runtime configuration values as strings (with secrets redacted). |
| `presets` | object | Available preset configurations keyed by name. Always includes `"default"` (the active configuration when no preset is selected) plus all named presets (`strict`, `moderation`, `nude_female`, `permissive`, `social_media`). Each preset includes the full `block`, `review`, and `sensitive` label-set configurations with any per-preset env overrides already applied. |

---

### `POST /api/nsfw/detect`

Enqueue an NSFW detection job. Returns immediately; results are delivered via callback.

**Request body** (`application/json`)

```json
{
  "photo_id": "string",
  "photo_path": "string",
  "preset": "string | null"
}
```

| Field | Required | Description |
|---|---|---|
| `photo_id` | Yes | Lychee-internal photo identifier, echoed back in the callback. |
| `photo_path` | Yes | Photo path relative to `VISION_NSFW_PHOTOS_PATH` (e.g. `2024/01/photo.jpg`). The service validates that the resolved absolute path stays within the photos root. |
| `preset` | No | Named preset to apply for this job. When set, the service-level `VISION_NSFW_PRESET` / `VISION_NSFW_BLOCK` / `VISION_NSFW_REVIEW` / `VISION_NSFW_SENSITIVE` configuration is ignored for this job and the named preset's label sets are used instead. Per-preset env overrides (e.g. `VISION_NSFW_STRICT__BLOCK__CONFIDENCE`) still apply. Valid values: `strict`, `moderation`, `nude_female`, `permissive`, `social_media`. Omit or set to `null` to use the service default. |

**Response `202 Accepted`**

The job has been accepted and enqueued. No body.

**Response `400 Bad Request`**

`photo_path` resolves outside the allowed directory (path-traversal attempt), the file does not exist, or an unknown `preset` name was supplied.

```json
{"detail": "photo_path /etc/passwd is outside the allowed directory"}
{"detail": "Unknown preset 'foo'"}
```

**Response `401 Unauthorized`**

Missing or incorrect `X-API-Key`.

```json
{"detail": "Invalid or missing API key"}
```

**Response `429 Too Many Requests`**

The queue is full (`VISION_NSFW_QUEUE_MAX_SIZE` reached).

```json
{"detail": "Queue is full — try again later"}
```

---

### `GET /api/nsfw/queue`

Returns the number of pending jobs.

**Response `200 OK`**

```json
{"pending": 3}
```

---

### `DELETE /api/nsfw/queue`

Purges all pending jobs. In-flight jobs are not affected.

**Response `204 No Content`**

---

### `GET /api/nsfw/queue/{photo_id}`

Returns the queue position of a specific job.

**Response `200 OK`**

```json
{"photo_id": "42", "position": 2}
```

`position` is 1-based. `position: 0` means the job is currently being processed.

**Response `404 Not Found`**

The job is not in the queue — it has already completed or was never submitted.

---

## Callback

After detection completes, the service POSTs the result to:

```
POST {VISION_NSFW_LYCHEE_API_URL}/api/v2/NsfwDetection/results
```

Headers:

```
X-API-Key: <VISION_NSFW_API_KEY>
Content-Type: application/json
Accept: application/json
```

### Success payload

```json
{
  "photo_id": "string",
  "status": "success",
  "should_block": false,
  "should_review": true,
  "is_sensitive": true,
  "all_detected": [
    {
      "label": "FEMALE_BREAST_EXPOSED",
      "confidence": 0.83,
      "bbox": {"x": 50, "y": 100, "width": 200, "height": 180},
      "area_pixels": 36000,
      "area_ratio": 0.075
    },
    {
      "label": "FEMALE_BREAST_COVERED",
      "confidence": 0.71,
      "bbox": {"x": 260, "y": 110, "width": 180, "height": 160},
      "area_pixels": 28800,
      "area_ratio": 0.060
    }
  ],
  "block_detected": [],
  "review_detected": [
    {
      "label": "FEMALE_BREAST_EXPOSED",
      "confidence": 0.83,
      "bbox": {"x": 50, "y": 100, "width": 200, "height": 180},
      "area_pixels": 36000,
      "area_ratio": 0.075
    }
  ],
  "sensitive_detected": [
    {
      "label": "FEMALE_BREAST_COVERED",
      "confidence": 0.71,
      "bbox": {"x": 260, "y": 110, "width": 180, "height": 160},
      "area_pixels": 28800,
      "area_ratio": 0.060
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `photo_id` | string | Echoed from the request. |
| `status` | string | Always `"success"` for successful detections. |
| `should_block` | bool | `true` if any detection matched the block tier. |
| `should_review` | bool | `true` if any detection matched the review tier. |
| `is_sensitive` | bool | `true` if any detection matched the sensitive tier. |
| `all_detected` | array | Every NudeNet detection that passed `VISION_NSFW_DEBUG_DETECT_THRESHOLD`, regardless of tier membership. Includes detections that did not match any configured label set. Useful for Lychee-side filtering and threshold tuning. |
| `block_detected` | array | Detections that triggered the block tier. Empty if `should_block` is `false`. |
| `review_detected` | array | Detections that triggered the review tier. |
| `sensitive_detected` | array | Detections that triggered the sensitive tier. |

Each detection object:

| Field | Type | Description |
|---|---|---|
| `label` | string | NudeNet label (see [Concepts](../1-concepts/README.md)). |
| `confidence` | float | Detection confidence `0.0–1.0`. |
| `bbox.x` | int | Left edge of the bounding box in pixels. |
| `bbox.y` | int | Top edge of the bounding box in pixels. |
| `bbox.width` | int | Bounding box width in pixels. |
| `bbox.height` | int | Bounding box height in pixels. |
| `area_pixels` | int | `width × height` in raw pixels. |
| `area_ratio` | float | `area_pixels / (image_width × image_height)` — fraction of the image covered. |

### Error payload

Sent when inference fails (corrupt file, unexpected error, etc.).

```json
{
  "photo_id": "string",
  "status": "error",
  "error_code": "internal_error",
  "message": "NSFW detection pipeline failed"
}
```

| `error_code` | Cause |
|---|---|
| `internal_error` | Unhandled exception during detection. Check service logs. |
| `corrupt_file` | The image file could not be decoded by Pillow or NudeNet. |

---

## Examples

### Submit a job using the service default

```bash
curl -X POST http://localhost:8000/api/nsfw/detect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"photo_id": "42", "photo_path": "2024/01/photo.jpg"}'
```

### Submit a job selecting a preset per request

```bash
curl -X POST http://localhost:8000/api/nsfw/detect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{"photo_id": "42", "photo_path": "2024/01/photo.jpg", "preset": "strict"}'
```

Response:

```
HTTP/1.1 202 Accepted
```

The callback will arrive at `{VISION_NSFW_LYCHEE_API_URL}/api/v2/NsfwDetection/results` once detection completes.

---

*Last updated: June 22, 2026*
