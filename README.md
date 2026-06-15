# Lychee NSFW Classification

NSFW content moderation microservice for [Lychee](https://github.com/LycheeOrg/Lychee).

Analyses photos for explicit content using NudeNet and reports results to the Lychee PHP backend via a REST callback.

[![Build Status][build-status-shield]](https://github.com/LycheeOrg/Lychee-NSFW-Classification/actions)
[![Code Coverage][codecov-shield]](https://codecov.io/gh/LycheeOrg/Lychee-NSFW-Classification)
[![CII Best Practices Summary][cii-shield]](https://bestpractices.coreinfrastructure.org/projects/2855)
[![OpenSSF Scorecard][ossf-shield]](https://securityscorecards.dev/viewer/?uri=github.com/LycheeOrg/Lychee-NSFW-Classification)
<br>
[![Website][website-shield]](https://lycheeorg.dev)
[![Documentation][docs-shield]](https://lycheeorg.dev/docs/)
[![Changelog][changelog-shield]](https://lycheeorg.dev/docs/releases.html)
[![Discord][discord-shield]][discord]

---

> [!CAUTION]
> ## License — GNU Affero General Public License v3 (AGPL-3.0)
>
> **This repository is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).**
>
> This is **different from all other LycheeOrg repositories**, which are released under the MIT License.
>
> ### Why AGPL-3.0?
>
> This service uses [NudeNet](https://github.com/notAI-tech/NudeNet), which is itself licensed under the AGPL-3.0. Because AGPL-3.0 is a strong copyleft license, any software that links to or distributes NudeNet must adopt the same license. This entire repository is therefore AGPL-3.0.
>
> See the [LICENSE](LICENSE) file for the full license text.

---

## How it works

1. Lychee sends a `POST /api/nsfw/detect` request with a photo ID and its path on the shared volume.
2. The service returns `202 Accepted` immediately and enqueues the job.
3. A background worker runs NudeNet inference on the image.
4. Results are POSTed back to Lychee's callback endpoint (`/api/v2/NsfwDetection/results`).

The callback payload classifies detections into three tiers:

| Field | Meaning |
|---|---|
| `should_block` | One or more detections matched the **block** label set — hide the photo. |
| `should_review` | One or more detections matched the **review** label set — send for human moderation. |
| `is_sensitive` | One or more detections matched the **sensitive** label set — mark the photo but keep it visible. |

All three tiers are independent: a photo can be both `should_block` and `is_sensitive` if labels from both sets are detected.

## Tech stack

| Concern | Library |
|---------|---------|
| Web framework | FastAPI + Uvicorn |
| Inference | NudeNet v3 (ONNX) |
| Image loading | Pillow |
| HTTP client | httpx |
| Config | Pydantic BaseSettings |

## Directory layout

```
Lychee-NSFW-Classification/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app factory + lifespan
│   ├── config/
│   │   ├── __init__.py    # Re-exports all public names
│   │   ├── labels.py      # VALID_LABELS frozenset
│   │   ├── models.py      # LabelThreshold, LabelSetConfig
│   │   ├── presets.py     # Named presets (strict, moderation, …)
│   │   └── settings.py    # AppSettings (Pydantic BaseSettings)
│   ├── api/
│   │   ├── dependencies.py  # API key authentication
│   │   ├── routes.py        # /detect, /health, /config, /queue
│   │   └── schemas.py       # Pydantic request/response/callback models
│   ├── detection/
│   │   └── detector.py      # NudeNet wrapper + classify()
│   └── queue/
│       ├── base.py          # JobQueue ABC
│       ├── factory.py       # Queue backend selection
│       └── worker.py        # Background job runner
├── tests/
├── docs/                  # Developer documentation (Diátaxis)
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Quick start — choose a preset

The fastest way to configure the service is to pick a **preset** that matches your use case:

| Preset | `VISION_NSFW_PRESET=` | Block | Review | Sensitive |
|--------|----------------------|-------|--------|-----------|
| Strict | `strict` | All exposed nudity incl. male chest | Covered intimate parts | Belly, armpits, feet |
| Moderation | `moderation` | _(nothing)_ | All exposed nudity | Covered intimate parts |
| Nude female | `nude_female` | Male genitalia, anus | Female genitalia | Female breast/buttocks + covered parts |
| Permissive | `permissive` | Genitalia + anus only | _(nothing)_ | Female/male breast, buttocks |
| Social media | `social_media` | Female breast, all genitalia, anus | Buttocks, male chest | Covered intimate parts |

Set it in `.env`:

```dotenv
VISION_NSFW_PRESET=strict
```

Individual tier settings (`VISION_NSFW_BLOCK`, `VISION_NSFW_REVIEW`, `VISION_NSFW_SENSITIVE`) always override the preset, so you can start from a preset and refine from there.

You can also **fine-tune each preset independently** at startup and let callers **select a preset per request**:

```dotenv
# Raise the confidence bar for the strict preset's block tier
VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9

# Require detections to cover ≥ 5 % of the image for nude_female's review tier
VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05
```

```json
{ "photo_id": "42", "photo_path": "2024/01/photo.jpg", "preset": "strict" }
```

See [Choose a preset](docs/2-how-to/choose-a-preset.md) and [Configure classification tiers](docs/2-how-to/tune-thresholds.md) for details.

## Environment variables

All variables are prefixed `VISION_NSFW_`. Copy `.env.example` to `.env` and fill in the required values.

### Required

| Variable | Description |
|----------|-------------|
| `VISION_NSFW_API_KEY` | Shared secret — validated on inbound requests via `X-API-Key` and sent on outbound callbacks. Must match `AI_VISION_NSFW_API_KEY` in Lychee's `.env`. |
| `VISION_NSFW_LYCHEE_API_URL` | Lychee base URL for callbacks, no trailing slash. Example: `https://lychee.example.com`. |

### Classification

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_NSFW_PRESET` | _(none)_ | Named preset: `strict`, `moderation`, `nude_female`, `permissive`, `social_media`. Populates block/review/sensitive defaults; explicit tier settings override it. |
| `VISION_NSFW_CONFIDENCE_THRESHOLD` | `0.1` | Global fallback minimum confidence `(0.0–1.0)` for a detection to trigger any tier. |
| `VISION_NSFW_AREA_RATIO_THRESHOLD` | `0.0` | Global fallback minimum area fraction `(0.0–1.0)` a detection must cover. `0.0` = no area filter. |
| `VISION_NSFW_BLOCK` | _(see defaults)_ | JSON object configuring the block tier. See [Configuration Reference](docs/3-reference/configuration.md). |
| `VISION_NSFW_REVIEW` | _(see defaults)_ | JSON object configuring the review tier. |
| `VISION_NSFW_SENSITIVE` | _(see defaults)_ | JSON object configuring the sensitive tier. |
| `VISION_NSFW_<PRESET>__<TIER>__<FIELD>` | _(none)_ | Per-preset threshold override. Tunes a specific preset in isolation so all presets are ready for per-request selection. Example: `VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9`. |

Full reference: [docs/3-reference/configuration.md](docs/3-reference/configuration.md)

## API endpoints

Base path: `/api/nsfw`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/nsfw/health` | No | Service health check |
| `POST` | `/api/nsfw/detect` | Yes | Enqueue an NSFW detection job |
| `GET` | `/api/nsfw/config` | Yes | Show active configuration (secrets redacted) |
| `GET` | `/api/nsfw/queue` | Yes | Number of pending jobs |
| `DELETE` | `/api/nsfw/queue` | Yes | Purge all pending jobs |
| `GET` | `/api/nsfw/queue/{photo_id}` | Yes | Queue position of a specific job |

Interactive docs: `http://localhost:8000/docs`

### `POST /api/nsfw/detect` — request

```json
{
  "photo_id": "42",
  "photo_path": "2024/01/photo.jpg",
  "preset": "strict"
}
```

| Field | Required | Description |
|---|---|---|
| `photo_id` | Yes | Lychee photo identifier, echoed back in the callback. |
| `photo_path` | Yes | Path relative to `VISION_NSFW_PHOTOS_PATH`. Validated to stay within that root. |
| `preset` | No | Override the service-level preset for this job. See [Choose a preset](docs/2-how-to/choose-a-preset.md). |

The endpoint returns **`202 Accepted`** immediately. Results arrive via callback.

### Callback payload (POSTed to Lychee)

```json
{
  "photo_id": "42",
  "status": "success",
  "should_block": true,
  "should_review": false,
  "is_sensitive": true,
  "block_detected": [
    {
      "label": "FEMALE_GENITALIA_EXPOSED",
      "confidence": 0.91,
      "bbox": {"x": 120, "y": 200, "width": 300, "height": 280},
      "area_pixels": 84000,
      "area_ratio": 0.175
    }
  ],
  "review_detected": [],
  "sensitive_detected": [
    {
      "label": "FEMALE_BREAST_COVERED",
      "confidence": 0.74,
      "bbox": {"x": 50, "y": 80, "width": 150, "height": 140},
      "area_pixels": 21000,
      "area_ratio": 0.044
    }
  ]
}
```

On failure, the callback contains `"status": "error"` with `error_code` and `message` fields.

Full API reference: [docs/3-reference/api.md](docs/3-reference/api.md)

## Development

### Setup

```bash
# Install uv (https://docs.astral.sh/uv/getting-started/installation/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev)
uv sync

# Copy and edit the env file
cp .env.example .env
```

### Makefile

```bash
make lint          # ruff check + ruff format --check + ty check
make format        # ruff format + ruff check --fix
make test          # pytest
make run           # uvicorn with --reload (local dev)
make docker-build  # docker build
make docker-run    # docker run --env-file .env
```

The service will be available at `http://localhost:8000`.

### Running tests with coverage

```bash
uv run pytest --cov=app --cov-report=html
```

## Docker

```bash
# Build
make docker-build

# Run using .env for configuration
make docker-run

# Or manually, mounting the Lychee uploads volume
docker run --rm \
  --env-file .env \
  -v /path/to/lychee/public/uploads:/data/photos:ro \
  -p 8000:8000 \
  lychee-nsfw-classification
```

See [Deploy with Docker](docs/2-how-to/deploy-with-docker.md) for a full deployment guide.

[build-status-shield]: https://img.shields.io/github/actions/workflow/status/LycheeOrg/Lychee-NSFW-Classification/CICD.yaml?branch=master
[codecov-shield]: https://codecov.io/gh/LycheeOrg/Lychee-NSFW-Classification/branch/master/graph/badge.svg
[cii-shield]: https://img.shields.io/cii/summary/2855.svg
[ossf-shield]: https://api.securityscorecards.dev/projects/github.com/LycheeOrg/Lychee-NSFW-Classification/badge
[website-shield]: https://img.shields.io/badge/-Website-informational.svg?logo=data:image/png;base64,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
[docs-shield]: https://img.shields.io/badge/-Documentation-informational.svg?logo=data:image/png;base64,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
[changelog-shield]: https://img.shields.io/badge/-Changelog-informational.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAASCAYAAACuLnWgAAABfWlDQ1BpY2MAACiRfZE9SMNAHMVfU6VaKg52EHEIWJ0siIqIk1ahCBVCrdCqg8mlX9CkIWlxcRRcCw5+LFYdXJx1dXAVBMEPECdHJ0UXKfF/SaFFjAfH/Xh373H3DhDqJaZZHWOAplfMZDwmpjOrYuAVQQTQjSHMyMwy5iQpAc/xdQ8fX++iPMv73J+jR81aDPCJxLPMMCvEG8RTmxWD8z5xmBVklficeNSkCxI/cl1x+Y1z3mGBZ4bNVHKeOEws5ttYaWNWMDXiSeKIqumUL6RdVjlvcdZKVda8J39hKKuvLHOd5iDiWMQSJIhQUEURJVQQpVUnxUKS9mMe/gHHL5FLIVcRjBwLKEOD7PjB/+B3t1ZuYtxNCsWAzhfb/hgGArtAo2bb38e23TgB/M/Ald7yl+vA9CfptZYWOQJ6t4GL65am7AGXO0D/kyGbsiP5aQq5HPB+Rt+UAfpugeCa21tzH6cPQIq6StwAB4fASJ6y1z3e3dXe279nmv39AJMecrRgM3JmAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAC4jAAAuIwF4pT92AAAEPUlEQVQ4y6XU34tUZRgH8O/748yZOWfn7OyuOzuzaquuu/4kUTS1i0S8CFLQCCGEuki680+IroS6CQKjC70JRIXooiDCQEkKRUyxxFCydV1Xx5md2fl1fr/ved+3CyEQLDf83j98eHh4vgRLjDSGy7mZirxxjTNKQCenMza5vm67bvaiWb4UwBhDur/8/LZuLBynnb6joMHo/Uj2uh8ZY74hhJiXRlpXL7+V3rn7hZlrlpkmoAUC6oeg1eBEcPumD+D8SyPNG9d30FqzbPkaJAOsxAJJBYwSY9LO73sRQpeCtFttBO0+0n4A6ccQ3RiyFSJt9SDi6KBfr1WXjEShGAyCZFym5pkNS1u3wI8CxH6EzBeQrQiiFyFthkh7kRZa/+dNCADouqGnb378ZkfeOVYo2NOAfWZicPeZNRfFel7vbFMr83vv/np1D5lPUC4MI6c4mMeReAbOG9uulycrP4gwImxw5Jq3acePzrIR+QxiMlP6+sInxy7fO32sKWbHuK0wlK+qve2DC9O/ea4D4+VKFvomwszMAwQLbZQsF8o26OZSrNo1hfFqGUYIaLu4KFeXvw03Jt9Bl37aPnkkAACaJWagHy68V28/GKPKRp67qPaHWfmKqNJHvmcCAdMRGDQFbN48DWuFh/OP7uCPsIGRMRdOEiJrL0AuLiKceTjSuXn96J/3vjo30zp76uLvn40BALUG6CNOimdLhSq4JVEd8rD2yUrYTQMVC4huAtFLIdspaM9g8+QUXtw13JkAtm3YaqoxByfvXe7LYbUe4D4BRvf2QoDtYrAMIAAAAASUVORK5CYII=
[discord]: https://discord.gg/JMPvuRQcTf
[discord-shield]: https://img.shields.io/discord/1046911561366765598?logo=discord
