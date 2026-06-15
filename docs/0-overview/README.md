# Lychee NSFW Classification — Overview

_Status: Active | Last updated: June 15, 2026_

Lychee NSFW Classification is a Python microservice that analyses photos for explicit content and reports results to the [Lychee](https://github.com/LycheeOrg/Lychee) photo gallery. It runs as a Docker sidecar and communicates with Lychee exclusively over HTTP.

---

## Purpose

Lychee itself has no built-in content moderation. This service fills that gap: when a photo is uploaded, Lychee can call this service to determine whether the image is safe before making it visible to viewers or applying additional access controls.

---

## How it works

```
Lychee                       NSFW Service
  │                               │
  │  POST /api/nsfw/detect        │
  │  { photo_id, image_url }      │
  │ ──────────────────────────► │
  │                               │  1. Fetch image
  │                               │  2. Run NudeNet inference
  │                               │  3. Apply classification logic
  │                               │  4. Build response
  │  200 OK                       │
  │  { is_safe, detections }      │
  │ ◄────────────────────────── │
```

Detection is **synchronous**: Lychee sends a request and waits for the result. The classification logic runs entirely inside the single HTTP round-trip — there is no callback or polling model.

---

## Key design decisions

### Synchronous detection

Unlike some AI sidecars that use a job queue and callback flow, this service responds inline. This keeps the integration surface minimal (one endpoint, one request, one response) and is appropriate because NudeNet inference is fast: typically 100–300 ms per image on CPU.

### Stateless

The service holds no persistent state. Every request is independent. There is no embedding store, job queue, or database. This simplifies deployment and makes horizontal scaling trivial — run as many replicas as needed behind a load balancer.

### Two-stage classification

Raw NudeNet detections do not map directly to an `is_safe` verdict. The service applies two independent safety tests:

1. **Always-block categories** — certain body parts are never acceptable regardless of image area covered (e.g. exposed male or anal genitalia). A single detection above the banned threshold marks the image unsafe.
2. **Area-based threshold** — other sensitive categories (e.g. exposed female genitalia) are flagged only when their total detected area exceeds a configurable fraction of the image. This reduces false positives from incidental framing.

See [concepts](../1-concepts/README.md) for the full classification logic.

### Authentication

All endpoints except `GET /health` require a shared-secret `X-API-Key` header. When `VISION_NSFW_API_KEY` is empty the check is disabled (useful for local development only).

---

## Technology

| Component | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | FastAPI + Uvicorn |
| Inference | [NudeNet](https://github.com/notAI-tech/NudeNet) v3 (ONNX) |
| Containerisation | Docker (multi-stage build) |
| Configuration | pydantic-settings, `.env` file |

---

## Further reading

- [Core Concepts](../1-concepts/README.md) — classification pipeline and NudeNet categories
- [Deploy with Docker](../2-how-to/deploy-with-docker.md) — run alongside Lychee
- [Tune thresholds](../2-how-to/tune-thresholds.md) — adjust sensitivity
- [API Reference](../3-reference/api.md) — endpoint contracts
- [Configuration](../3-reference/configuration.md) — all environment variables

---

*Last updated: June 15, 2026*
