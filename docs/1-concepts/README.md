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
| `FEMALE_FACE` | Female face |
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

Not all labels trigger an unsafe verdict. The classification logic below determines which ones matter and how.

---

## Classification logic

Raw NudeNet detections pass through two independent safety tests. The image is `is_safe = false` if **either** test triggers.

### Step 1 — confidence filter

Any detection with `score < VISION_NSFW_CONFIDENCE_THRESHOLD` (default `0.1`) is discarded before further processing. This removes low-confidence noise.

### Step 2 — always-block test

Some categories are considered unsafe regardless of how much of the image they cover. If any detection in this set has `score > VISION_NSFW_CONFIDENCE_BANNED_THRESHOLD` (default `0.05`), the image is immediately marked unsafe:

```
ALWAYS_BLOCK = { ANUS_EXPOSED, MALE_GENITALIA_EXPOSED }
```

The threshold here is intentionally low (`0.05`) so these categories are not missed even when the model is uncertain.

### Step 3 — area-based test

Other sensitive categories are only flagged when they occupy a meaningful portion of the image. For each detection in the area-sensitive set:

```
UNSAFE_PARTS = { FEMALE_GENITALIA_EXPOSED, ANUS_EXPOSED, MALE_GENITALIA_EXPOSED }
```

If its `score > VISION_NSFW_UNSAFE_CONFIDENCE_THRESHOLD` (default `0.3`), its pixel area (`width × height`) is added to a running `unsafe_area` total. If:

```
unsafe_area / (image_width × image_height) > VISION_NSFW_UNSAFE_AREA_RATIO_THRESHOLD
```

(default `0.02`, i.e. 2% of the image) then the image is marked unsafe. This prevents false positives where a sensitive label appears on a tiny incidental region.

### Final verdict

```python
is_safe = not always_blocked and not area_unsafe
```

Both conditions must be absent for the image to be considered safe.

---

## Bounding box coordinates

Bounding boxes in the API response are reported in **absolute pixels** as they come from NudeNet:

```json
"bbox": {
  "x": 120,
  "y": 45,
  "width": 200,
  "height": 180
}
```

`x` and `y` are the top-left corner. `width` and `height` are the box dimensions. All values are in the pixel space of the original image.

The `area_ratio` field in the response is computed as `(width × height) / (image_width × image_height)` — a normalised fraction showing how much of the image the detection covers.

---

## Request and response model

### Request (`POST /api/nsfw/detect`)

```json
{
  "photo_id": "abc-123",
  "image_url": "https://lychee.example.com/storage/img.jpg"
}
```

or

```json
{
  "photo_id": "abc-123",
  "image_path": "/path/to/image.jpg"
}
```

Exactly one of `image_url` or `image_path` must be provided.

### Response

```json
{
  "photo_id": "abc-123",
  "is_safe": false,
  "detections": [
    {
      "label": "FEMALE_GENITALIA_EXPOSED",
      "confidence": 0.87,
      "bbox": { "x": 120, "y": 45, "width": 200, "height": 180 },
      "area_ratio": 0.031
    }
  ]
}
```

`detections` contains only the labels that passed the confidence filter. It may be empty even when `is_safe` is `false` (if the always-block test triggers on a detection that was itself above the banned threshold but below the general confidence threshold — though in practice this is unlikely given the threshold ordering).

---

## Image fetching

When `image_url` is provided, the service downloads the image using `httpx` with a 30-second timeout, writes it to a temporary file, and passes the path to NudeNet. The temporary file is deleted after inference regardless of success or failure.

Supported content types: JPEG, PNG, WebP. The file extension is inferred from the `Content-Type` response header.

When `image_path` is provided, the file is read directly from disk. The path is not validated against any prefix — ensure Lychee only sends paths it controls.

---

## Thread safety

NudeNet inference is CPU-bound. The service loads the `NudeDetector` lazily on the first request and reuses it for subsequent requests. Because NudeNet is not thread-safe, the service should be run with a single Uvicorn worker in production. If you need parallelism, run multiple container replicas behind a load balancer rather than increasing the worker count.

---

*Last updated: June 15, 2026*
