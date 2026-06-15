# Deploy with Docker

_Status: Active | Last updated: June 15, 2026_

This guide explains how to run the Lychee NSFW Classification service as a Docker container alongside your Lychee instance.

---

## Prerequisites

- Docker (or Docker Compose)
- A running Lychee instance reachable from the container

---

## Build the image

```bash
make docker-build
```

Or directly:

```bash
docker build -t lychee-nsfw-classification .
```

The image bundles the NudeNet ONNX model weights. Expect a ~300 MB download on the first build; subsequent builds use the Docker layer cache.

---

## Minimal run

```bash
docker run --rm \
  -e VISION_NSFW_API_KEY=your-shared-secret \
  -e VISION_NSFW_LYCHEE_URL=https://lychee.example.com \
  -e VISION_NSFW_LYCHEE_API_KEY=your-lychee-api-key \
  -p 8000:8000 \
  lychee-nsfw-classification
```

---

## Using an env file

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Then run:

```bash
make docker-run
```

Or directly:

```bash
docker run --rm --env-file .env -p 8000:8000 lychee-nsfw-classification
```

---

## Docker Compose example

```yaml
services:
  nsfw-classifier:
    image: lychee-nsfw-classification
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    restart: unless-stopped
```

If you are running Lychee via Docker Compose, add the service to the same `docker-compose.yml` so both containers share the same network and can reach each other by service name.

---

## Verify the service is running

```bash
curl http://localhost:8000/api/nsfw/health
```

Expected response:

```json
{"status": "ok"}
```

---

## Test a classification

```bash
curl -X POST http://localhost:8000/api/nsfw/detect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-shared-secret" \
  -d '{"photo_id": "test-1", "image_url": "https://example.com/photo.jpg"}'
```

---

## Running without Docker (development)

```bash
uv sync --dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or using the Makefile:

```bash
make run
```

---

## Notes

**API key:** When `VISION_NSFW_API_KEY` is empty the authentication check is disabled. Always set a strong key in production.

**Single worker:** NudeNet inference is not thread-safe. Keep `UVICORN_WORKERS=1` (the default). For higher throughput, run multiple container replicas behind a reverse proxy (e.g. nginx or Traefik).

See [Configuration](../3-reference/configuration.md) for the full list of environment variables.

---

*Last updated: June 15, 2026*
