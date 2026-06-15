# Core Concepts

_Status: Active | Last updated: June 15, 2026_

This document explains the domain model and classification logic used by the Lychee NSFW Classification service.

---

## NudeNet and detection labels

The service uses [NudeNet v3](https://github.com/notAI-tech/NudeNet), an ONNX-based model that returns a list of detections for each image. Each detection has:

- **`class`** — a label string identifying the body part or content category (see table below)
- **`score`** — a confidence value between `0.0` and `1.0`
- **`box`** — bounding box as `[x, y, width, height]` in absolute pixels

NudeNet's full label set:

| Label | Description |
|---|---|
| `FACE_FEMALE` | Female face |
| `FACE_MALE` | Male face |
| `FEMALE_BREAST_COVERED` | Clothed female breast |
| `FEMALE_BREAST_EXPOSED` | Bare female breast |
| `FEMALE_GENITALIA_COVERED` | Clothed female genitalia |
| `FEMALE_GENITALIA_EXPOSED` | Bare female genitalia |
| `MALE_GENITALIA_EXPOSED` | Bare male genitalia |
| `MALE_BREAST_EXPOSED` | Bare male chest |
| `ANUS_COVERED` | Clothed anus |
| `ANUS_EXPOSED` | Bare anus |
| `BUTTOCKS_COVERED` | Clothed buttocks |
| `BUTTOCKS_EXPOSED` | Bare buttocks |
| `BELLY_COVERED` | Clothed abdomen |
| `BELLY_EXPOSED` | Bare abdomen |
| `ARMPITS_COVERED` | Clothed armpits |
| `ARMPITS_EXPOSED` | Bare armpits |
| `FEET_COVERED` | Clothed feet |
| `FEET_EXPOSED` | Bare feet |

---

## Three-tier classification

Raw NudeNet detections are classified into three independent tiers. Each tier has its own configurable set of labels and thresholds.

```
NudeNet detections
       │
       ▼
┌─────────────┐    should_block ──► block_detected[ ]
│   block     │
└─────────────┘
       │
       ▼
┌─────────────┐    should_review ──► review_detected[ ]
│   review    │
└─────────────┘
       │
       ▼
┌─────────────┐    is_sensitive ──► sensitive_detected[ ]
│  sensitive  │
└─────────────┘
```

All three tiers evaluate every detection independently — a single detection can appear in more than one tier if its label is listed in multiple sets.

### Tier meanings

| Tier | Callback field | Intended action |
|---|---|---|
| **block** | `should_block: true` | Hide the photo from all viewers. |
| **review** | `should_review: true` | Hold for human moderation before publishing. |
| **sensitive** | `is_sensitive: true` | Mark and restrict, but do not hide outright. |

---

## Threshold resolution

Each detection must pass **two** thresholds to appear in a tier's detected list:

1. **Confidence** — the NudeNet `score` must be ≥ the effective confidence threshold.
2. **Area ratio** — `(bbox_width × bbox_height) / (image_width × image_height)` must be ≥ the effective area-ratio threshold. The default global value is `0.0`, which disables the area filter.

Thresholds are resolved per-detection, per-tier, using a three-level priority chain:

```
label_thresholds[label].confidence
        │ if None
        ▼
  set.confidence
        │ if None
        ▼
settings.confidence_threshold          ← global fallback (default 0.1)
```

The same chain applies to `area_ratio`. This means you can set a strict default for the whole block tier, then loosen it for specific low-risk labels within that tier.

---

## Bounding box and area fields

Every detection in the callback payload includes:

```json
{
  "label": "FEMALE_GENITALIA_EXPOSED",
  "confidence": 0.87,
  "bbox": {"x": 120, "y": 45, "width": 300, "height": 280},
  "area_pixels": 84000,
  "area_ratio": 0.175
}
```

- `bbox.x` / `bbox.y` — top-left corner of the bounding box in absolute pixels.
- `bbox.width` / `bbox.height` — box dimensions in pixels.
- `area_pixels` — `width × height` in raw pixels.
- `area_ratio` — `area_pixels / (image_width × image_height)`: the fraction of the image covered.

---

## Request and callback model

### Request (`POST /api/nsfw/detect`)

```json
{
  "photo_id": "42",
  "photo_path": "2024/01/photo.jpg"
}
```

`photo_path` is relative to the shared volume root (`VISION_NSFW_PHOTOS_PATH`, default `/data/photos`). The service validates that the resolved path stays within that root before reading the file.

The endpoint returns **`202 Accepted`** immediately. Detection runs in the background.

### Callback — success

The result is POSTed to `{VISION_NSFW_LYCHEE_API_URL}/api/v2/NsfwDetection/results`:

```json
{
  "photo_id": "42",
  "status": "success",
  "should_block": false,
  "should_review": true,
  "is_sensitive": true,
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

### Callback — error

```json
{
  "photo_id": "42",
  "status": "error",
  "error_code": "corrupt_file",
  "message": "Image could not be decoded"
}
```

---

## Presets

Named presets provide curated default label sets for common use cases without requiring manual label configuration. Available presets:

| Name | Description |
|---|---|
| `strict` | Block all exposed nudity; review covered intimate parts. |
| `moderation` | Nothing blocked; all nudity sent for human review. |
| `nude_female` | Block male genitalia/anus; moderate female genitalia; rest sensitive. |
| `permissive` | Only block genitalia and anus; partial nudity is sensitive. |
| `social_media` | Block female breasts and all genitalia; review buttocks. |

Set `VISION_NSFW_PRESET=<name>` to activate a preset. See [Choose a preset](../2-how-to/choose-a-preset.md).

---

## Thread safety

NudeNet inference is CPU-bound. The `NudeDetector` is loaded lazily on the first request and reused for all subsequent requests. Because NudeNet is not thread-safe, the `ThreadPoolExecutor` is intentionally sized to one thread by default (`VISION_NSFW_THREAD_POOL_SIZE=1`). For higher throughput, run multiple container replicas behind a load balancer.

---

*Last updated: June 15, 2026*
