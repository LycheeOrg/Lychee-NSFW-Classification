# API Reference

_Status: Active | Last updated: June 15, 2026_

Base path: `/api/nsfw`

Interactive docs are available at `http://localhost:8000/docs` when the service is running.

---

## Authentication

All endpoints except `GET /health` require the `X-API-Key` header:

```
X-API-Key: your-shared-secret
```

The value must match the `API_KEY` environment variable. When `API_KEY` is empty, the check is disabled (development only). Requests with a missing or incorrect key receive `403 Forbidden`.

---

## Endpoints

### `GET /api/nsfw/health`

Returns the service operational status. No authentication required.

**Response `200 OK`**

```json
{"status": "ok"}
```

---

### `POST /api/nsfw/detect`

Classify an image for explicit content.

**Request body** (`application/json`)

```json
{
  "photo_id": "string",
  "image_url": "string | null",
  "image_path": "string | null"
}
```

| Field | Required | Description |
|---|---|---|
| `photo_id` | Yes | Opaque identifier echoed back in the response. Used by Lychee to correlate the result with the original photo. |
| `image_url` | Conditional | HTTP(S) URL of the image to classify. Must be provided if `image_path` is absent. |
| `image_path` | Conditional | Absolute filesystem path to the image. Must be provided if `image_url` is absent. |

Exactly one of `image_url` or `image_path` must be provided. Providing neither returns `422 Unprocessable Entity`.

**Response `200 OK`**

```json
{
  "photo_id": "string",
  "is_safe": true,
  "detections": [
    {
      "label": "string",
      "confidence": 0.0,
      "bbox": {
        "x": 0,
        "y": 0,
        "width": 0,
        "height": 0
      },
      "area_ratio": 0.0
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `photo_id` | string | Echoed from the request. |
| `is_safe` | bool | `true` if no safety test was triggered. `false` if always-block or area threshold was exceeded. |
| `detections` | array | Detections that passed the confidence filter, regardless of whether they contributed to an unsafe verdict. May be empty. |
| `detections[].label` | string | NudeNet category label (see [Concepts](../1-concepts/README.md)). |
| `detections[].confidence` | float | Detection confidence `0.0–1.0`. |
| `detections[].bbox` | object | Bounding box in absolute pixels: top-left `(x, y)`, `width`, `height`. |
| `detections[].area_ratio` | float | `(bbox_width × bbox_height) / (image_width × image_height)` — fraction of the image covered by this detection. |

**Response `403 Forbidden`**

Missing or invalid `X-API-Key`.

```json
{"detail": "Invalid API key"}
```

**Response `422 Unprocessable Entity`**

Validation error (e.g. neither `image_url` nor `image_path` provided, or the image could not be decoded).

```json
{"detail": "Image could not be processed: <reason>"}
```

---

## Error handling

| Status | Cause |
|---|---|
| `403` | Missing or incorrect `X-API-Key` header |
| `422` | Request body validation failure or image processing error |
| `500` | Unexpected server error (check service logs) |

---

## Example

```bash
curl -X POST http://localhost:8000/api/nsfw/detect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d '{
    "photo_id": "photo-abc-123",
    "image_url": "https://example.com/uploads/photo.jpg"
  }'
```

Response (safe image):

```json
{
  "photo_id": "photo-abc-123",
  "is_safe": true,
  "detections": [
    {
      "label": "FEMALE_FACE",
      "confidence": 0.92,
      "bbox": {"x": 230, "y": 45, "width": 180, "height": 200},
      "area_ratio": 0.015
    }
  ]
}
```

Response (unsafe image):

```json
{
  "photo_id": "photo-xyz-456",
  "is_safe": false,
  "detections": [
    {
      "label": "FEMALE_GENITALIA_EXPOSED",
      "confidence": 0.87,
      "bbox": {"x": 120, "y": 200, "width": 300, "height": 280},
      "area_ratio": 0.036
    }
  ]
}
```

---

*Last updated: June 15, 2026*
