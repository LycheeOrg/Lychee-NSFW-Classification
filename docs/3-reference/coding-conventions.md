# Python Coding Conventions

This document describes the coding standards enforced in this project. All rules are verified by `ruff` and `ty` — pull requests must pass both before merging.

## Python version

**Python 3.13** is the only supported version (`requires-python = ">=3.13,<3.14"`). Use modern syntax freely: `match`, `Self`, `TypeAlias`, `ExceptionGroup`, built-in generics, etc.

## Tooling

| Tool | Purpose | Command |
|---|---|---|
| `ruff check` | Lint (pycodestyle, pyflakes, isort, naming, annotations, bugbear, …) | `make lint` |
| `ruff format` | Auto-format | `make format` |
| `ty check` | Static type checking | `make lint` |
| `pytest` | Tests | `make test` |

Run all three before opening a PR. `ruff format --check` and `ruff check` run in CI and will fail the build.

## Formatting

- **Line length:** 120 characters.
- **Indentation:** 4 spaces (ruff normalises Python files to spaces regardless of `.editorconfig` tab settings).
- **String quotes:** double (`"`).
- **Line endings:** LF.
- **Trailing whitespace:** trimmed.

## Imports

Every module must begin with:

```python
from __future__ import annotations
```

This enables PEP 563 postponed annotation evaluation, which allows forward references and eliminates runtime annotation cost.

Import order (enforced by `ruff I` / isort):

1. Standard library
2. Third-party packages
3. First-party (`app.*`)

Imports used only in type annotations go inside a `TYPE_CHECKING` guard:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from app.detection.detector import NsfwClassifier
```

This keeps heavy packages (`nudenet`, `pillow`, …) out of the runtime import graph when only their types are needed.

## Type annotations

All function parameters and return types must be fully annotated (`ruff ANN`). Unannotated signatures fail CI.

```python
# correct
def classify(self, image_path: Path) -> ClassificationResult:

# wrong — missing return type
def classify(self, image_path: Path):
```

`typing.Any` is permitted only where no more precise type exists — specifically raw NudeNet return values (`ANN401` is suppressed). Do not use `Any` as an escape hatch elsewhere.

Use built-in generic types directly (`list[str]`, `dict[str, int]`, `tuple[str, ...]`) — not `typing.List`, `typing.Dict` (enforced by `ruff UP`).

Apply `@typing.override` when overriding a base class or protocol method:

```python
class _ColorFormatter(logging.Formatter):
    @typing.override
    def format(self, record: logging.LogRecord) -> str:
        ...
```

## Naming

PEP 8 naming enforced by `ruff N`:

| Kind | Convention | Example |
|---|---|---|
| Module | `snake_case` | `detector.py` |
| Class | `PascalCase` | `NsfwClassifier`, `DetectionResult` |
| Function / method | `snake_case` | `detect_from_url`, `classify` |
| Variable | `snake_case` | `raw_detections`, `photo_id` |
| Module-level private | leading `_` | `_ALWAYS_BLOCK`, `_default_lifespan` |
| Instance private | leading `_` | `_detector`, `_loaded` |

Do not shadow Python built-ins (`id`, `list`, `type`, …) — enforced by `ruff A`.

## Docstrings

Use a single-line docstring when the purpose is obvious from the name and signature. Add `Args:` and `Raises:` sections when behaviour or failure modes are non-obvious.

```python
def count(self) -> int:
    """Return the total number of classifications processed."""

def classify(self, image_path: Path) -> ClassificationResult:
    """Classify an image file for NSFW content.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        Classification result with is_safe flag and per-detection breakdown.

    Raises:
        RuntimeError: If the detector has not been initialised.
        ValueError: If the file cannot be decoded as an image.
    """
```

Do not write a docstring that only restates the function name. A docstring must add information beyond what the name and types already express.

## Inline comments

Write a comment only when the **why** is non-obvious from the code. Do not explain what the code does. Do not reference issue numbers or task IDs — those belong in commit messages.

```python
# Avoid division by zero for zero-area images
total_area = max(image_width * image_height, 1)

# NudeNet reads model weights lazily on first call, not at import time,
# so initialising the detector here — before the first request — amortises
# the startup cost across all workers rather than hitting the first caller.
_detector = NudeDetector()
```

## Application structure

### Configuration

All settings live in `app/config.py` as a `pydantic-settings` `Settings` model. **Never read environment variables directly.** Inject settings in route handlers via `Depends(get_settings)`.

```python
# correct
async def detect(settings: Settings = Depends(get_settings)) -> None:
    threshold = settings.confidence_threshold

# wrong
threshold = float(os.environ["VISION_NSFW_CONFIDENCE_THRESHOLD"])
```

`get_settings()` is cached with `@lru_cache`. Override it in tests with `app.dependency_overrides[get_settings]`.

### FastAPI routes

Routes must be thin: validate the request, delegate to domain modules, return. Business logic belongs in `app/detection/`.

`Depends()` calls in function default arguments are allowed — `B008` is suppressed because FastAPI requires this pattern.

### Interfaces

Use `typing.Protocol` for backend-agnostic interfaces. Concrete implementations satisfy the protocol structurally — no inheritance needed.

```python
@runtime_checkable
class Classifier(Protocol):
    def detect(self, image_path: str) -> list[dict[str, Any]]: ...
    def classify(self, raw: list[dict[str, Any]], width: int, height: int) -> tuple[bool, list[dict[str, Any]]]: ...
```

### CPU-bound work

NudeNet inference is blocking and slow. Always offload it to the `ThreadPoolExecutor` in `app.state.executor`:

```python
loop = asyncio.get_running_loop()
results = await loop.run_in_executor(executor, detector.detect_from_path, image_path)
```

Never call blocking functions directly inside `async def` handlers.

## Tests

- Test files live in `tests/`, named after the module they cover (`test_api.py`, `test_detection.py`, …).
- `asyncio_mode = "auto"` is set globally — no `@pytest.mark.asyncio` decorator needed.
- Use `respx` to mock `httpx` HTTP calls. Do not patch `httpx` internals.
- Inject fakes via `app.dependency_overrides` instead of monkeypatching globals.
- `--strict-markers` is enabled: any custom marker must be declared under `[tool.pytest.ini_options]` in `pyproject.toml`.
