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
  │  { photo_id, photo_path }     │
  │ ──────────────────────────► │
  │  202 Accepted                 │
  │ ◄────────────────────────── │
  │                               │  1. Read image from shared volume
  │                               │  2. Run NudeNet inference
  │                               │  3. Apply classification logic
  │                               │  4. POST callback to Lychee
  │                               │
  │  POST /api/v2/NsfwDetection/results
  │  { photo_id, should_block, … }│
  │ ◄────────────────────────── │
```

Detection is **asynchronous**: Lychee sends a request and receives `202 Accepted` immediately. The service enqueues the job and a background worker runs NudeNet inference. Results are POSTed back to Lychee's callback endpoint (`/api/v2/NsfwDetection/results`) once detection completes.

---

## Key design decisions

### Asynchronous detection with callback

The service uses a job queue and callback flow. Lychee submits a job and returns immediately; the result arrives asynchronously. This decouples upload latency from inference latency and allows the queue to absorb bursts.

### Queue-backed processing

The service maintains a job queue (in-memory or database-backed) that bounds concurrency and provides back-pressure via `429 Too Many Requests` when full. Queue depth and position are queryable via `/api/nsfw/queue`.

### Three-tier classification

Raw NudeNet detections are classified into three independent tiers, each with its own label set and thresholds:

- **block** — hide the photo entirely (`should_block: true`).
- **review** — queue for human moderation (`should_review: true`).
- **sensitive** — mark the photo but keep it visible (`is_sensitive: true`).

A photo can match multiple tiers simultaneously. All raw detections (regardless of tier) are included in `all_detected` in the callback payload, which is useful for Lychee-side filtering and threshold tuning.

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

*Last updated: June 16, 2026*
