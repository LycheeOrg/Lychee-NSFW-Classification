"""AppSettings and cached factory."""

import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.models import LabelSetConfig, PresetOverride

_RED = "\033[31m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _pretty_config_error(exc: ValidationError) -> None:
    missing: list[str] = []
    invalid: list[tuple[str, str]] = []

    for error in exc.errors():
        field = str(error["loc"][0])
        env_var = f"VISION_NSFW_{field.upper()}"
        if error["type"] == "missing":
            missing.append(env_var)
        else:
            invalid.append((env_var, error["msg"]))

    lines = [
        "",
        f"{_BOLD}{_RED}✗  AI Vision Service failed to start — invalid configuration{_RESET}",
        "",
    ]

    if missing:
        lines.append(f"{_YELLOW}Required environment variables are not set:{_RESET}")
        for var in missing:
            lines.append(f"  {_BOLD}{var}{_RESET}")
        lines.append("")

    if invalid:
        lines.append(f"{_YELLOW}Environment variables have invalid values:{_RESET}")
        for var, msg in invalid:
            lines.append(f"  {_BOLD}{var}{_RESET}  {_DIM}— {msg}{_RESET}")
        lines.append("")

    lines += [
        f"{_DIM}All settings use the VISION_NSFW_ prefix.",
        f"Example:  VISION_NSFW_LYCHEE_API_URL=http://lychee  VISION_NSFW_API_KEY=secret{_RESET}",
        "",
    ]

    print("\n".join(lines), file=sys.stderr)


class AppSettings(BaseSettings):
    """Runtime configuration for the AI Vision NSFW Service.

    All values are read from environment variables prefixed ``VISION_NSFW_``.
    Nested set configs can be set as JSON or via ``__``-delimited sub-keys, e.g.:
      ``VISION_NSFW_BLOCK__CONFIDENCE=0.8``
      ``VISION_NSFW_BLOCK__LABELS='["ANUS_EXPOSED"]'``
      ``VISION_NSFW_BLOCK__LABEL_THRESHOLDS='{"ANUS_EXPOSED": {"confidence": 0.9}}'``
    """

    # --- Required ---
    lychee_api_url: str
    """Lychee instance base URL for callbacks (e.g. ``http://lychee``). No trailing slash."""

    api_key: str
    """Shared API key used in both directions: validated on *inbound* requests from Lychee
    (``X-API-Key`` header) and sent as ``X-API-Key`` on *outbound* callbacks to Lychee.
    Must match ``AI_VISION_NSFW_API_KEY`` in the Lychee ``.env``."""

    # --- Connectivity ---
    verify_ssl: bool = True
    """Whether to verify SSL certificates when making callbacks to Lychee.
    Set to ``False`` for development environments with self-signed certificates.
    **WARNING:** Disabling SSL verification in production is a security risk."""

    skip_lychee_check: bool = False
    """Skip the Lychee connectivity check at startup.
    Useful for local development or when Lychee is not yet reachable."""

    # --- Photo volume ---
    photos_path: str = "/data/photos"
    """Shared Docker-volume mount point for photo files.

    ``photo_path`` values from Lychee are validated to reside within this prefix
    (path-traversal protection).
    """

    # --- Global detection thresholds (fallbacks when not overridden by a set or label) ---
    confidence_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    """Global minimum confidence for a detection to trigger any tier."""

    area_ratio_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    """Global minimum fraction of the image area a detection must cover to trigger any tier.
    ``0.0`` (default) means area is not considered."""

    debug_detect_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    """Absolute confidence floor applied before any tier evaluation.

    Detections below this value are discarded entirely and will not appear
    in ``all_detected``, ``block_detected``, ``review_detected``, or
    ``sensitive_detected``.  Default ``0.0`` keeps all NudeNet output.
    Raise it (e.g. ``0.01``) to suppress near-zero-confidence noise."""

    # --- Preset ---
    preset: str | None = None
    """Load a named preset as the baseline for block / review / sensitive.

    Explicit ``VISION_NSFW_BLOCK``, ``VISION_NSFW_REVIEW``, or
    ``VISION_NSFW_SENSITIVE`` values still override the preset.  Two override
    modes are supported:

    * **Full override** — supply ``labels`` (and optionally thresholds).  The
      preset's label list is ignored entirely for that tier.
      Example: ``VISION_NSFW_BLOCK='{"labels":["ANUS_EXPOSED"]}'``

    * **Threshold-only override** — supply only threshold keys
      (``confidence``, ``area_ratio``, ``label_thresholds``) *without*
      ``labels``.  The preset's labels are kept and the explicit thresholds
      are merged on top.
      Example: ``VISION_NSFW_BLOCK__CONFIDENCE=0.9``
      Example: ``VISION_NSFW_REVIEW__AREA_RATIO=0.05``

    Valid names: ``strict``, ``moderation``, ``nude_female``, ``permissive``,
    ``social_media``."""

    @model_validator(mode="before")
    @classmethod
    def _apply_preset(cls, data: dict) -> dict:
        preset_name = data.get("preset")
        if preset_name is None:
            return data
        from app.config.presets import PRESETS

        preset = PRESETS.get(preset_name)
        if preset is None:
            raise ValueError(f"Unknown preset {preset_name!r}. Valid presets: {sorted(PRESETS)}")

        # Per-preset env overrides, e.g. VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9
        preset_override_raw = data.get(preset_name) or {}

        for field in ("block", "review", "sensitive"):
            preset_config = getattr(preset, field).model_dump()

            # Merge preset-specific tier override (labels replaced only when explicitly set)
            tier_raw = {}
            if isinstance(preset_override_raw, dict):
                raw = preset_override_raw.get(field) or {}
                if isinstance(raw, dict):
                    if "labels" in raw and raw["labels"] is not None:
                        tier_raw["labels"] = raw["labels"]
                    for key in ("confidence", "area_ratio", "label_thresholds"):
                        if raw.get(key) is not None:
                            tier_raw[key] = raw[key]

            merged_preset = {**preset_config, **tier_raw}

            if field not in data:
                data[field] = merged_preset
            elif isinstance(data[field], dict) and "labels" not in data[field]:
                # Global threshold-only override on top of the (already merged) preset config.
                # e.g. VISION_NSFW_BLOCK__CONFIDENCE=0.8 with VISION_NSFW_PRESET=strict
                # keeps strict's labels but uses confidence=0.8.
                data[field] = {**merged_preset, **data[field]}
            # else: global override includes explicit labels → use as-is (full override).

        return data

    # --- Label set configurations ---
    block: LabelSetConfig = Field(
        default_factory=lambda: LabelSetConfig(
            labels=[
                "FEMALE_GENITALIA_EXPOSED",
                "MALE_GENITALIA_EXPOSED",
                "ANUS_EXPOSED",
            ]
        )
    )
    """Labels and thresholds for the *block* tier (``should_block`` in the callback)."""

    review: LabelSetConfig = Field(
        default_factory=lambda: LabelSetConfig(
            labels=[
                "BUTTOCKS_EXPOSED",
                "FEMALE_BREAST_EXPOSED",
            ]
        )
    )
    """Labels and thresholds for the *review* tier (``should_review`` in the callback)."""

    sensitive: LabelSetConfig = Field(
        default_factory=lambda: LabelSetConfig(
            labels=[
                "FEMALE_BREAST_COVERED",
                "FEMALE_GENITALIA_COVERED",
                "ANUS_COVERED",
                "BUTTOCKS_COVERED",
                "BELLY_EXPOSED",
            ]
        )
    )
    """Labels and thresholds for the *sensitive* tier (``is_sensitive`` in the callback)."""

    # --- Per-preset overrides ---
    # Each field holds threshold/label overrides for the corresponding named preset.
    # These are loaded from env vars using the preset name as the nested key, e.g.:
    #   VISION_NSFW_STRICT__BLOCK__CONFIDENCE=0.9
    #   VISION_NSFW_NUDE_FEMALE__REVIEW__AREA_RATIO=0.05
    # All fields default to no-op (inherit from the preset definition).
    strict: PresetOverride = Field(default_factory=PresetOverride)
    moderation: PresetOverride = Field(default_factory=PresetOverride)
    nude_female: PresetOverride = Field(default_factory=PresetOverride)
    permissive: PresetOverride = Field(default_factory=PresetOverride)
    social_media: PresetOverride = Field(default_factory=PresetOverride)

    def resolve_preset(self, name: str) -> tuple[LabelSetConfig, LabelSetConfig, LabelSetConfig]:
        """Return ``(block, review, sensitive)`` for a preset with its env overrides applied.

        Used for per-request preset selection: the caller swaps in these label sets
        instead of the global ``block`` / ``review`` / ``sensitive`` fields.

        Raises ``ValueError`` for unknown preset names.
        """
        from app.config.presets import PRESETS

        if name not in PRESETS:
            raise ValueError(f"Unknown preset {name!r}. Valid presets: {sorted(PRESETS)}")
        preset = PRESETS[name]
        override: PresetOverride = getattr(self, name)
        return (
            override.block.apply_to(preset.block),
            override.review.apply_to(preset.review),
            override.sensitive.apply_to(preset.sensitive),
        )

    # --- Concurrency ---
    thread_pool_size: int = 1
    """Number of threads in the ``ThreadPoolExecutor`` used for CPU-bound inference."""

    workers: int = 1
    """Number of Uvicorn worker processes."""

    # --- Job queue ---
    queue_backend: str = "database"
    """Queue backend: ``database`` (SQLite) or ``redis``."""

    queue_max_size: int = 0
    """Maximum number of pending jobs in the queue.  Requests that would exceed
    this limit are rejected with **429 Too Many Requests**."""

    storage_path: str = "/data/queue"
    """Directory for the SQLite queue database (used when ``queue_backend = "database"``)."""

    # --- PostgreSQL (for queue when queue_backend = "database" with pg) ---
    pg_host: str = "localhost"
    """PostgreSQL host."""

    pg_port: int = 5432
    """PostgreSQL port."""

    pg_database: str = "ai_vision"
    """PostgreSQL database name."""

    pg_user: str = "ai_vision"
    """PostgreSQL username."""

    pg_password: str = ""
    """PostgreSQL password."""

    # --- Redis (only when queue_backend = "redis") ---
    redis_host: str = "localhost"
    """Redis host."""

    redis_port: int = 6379
    """Redis port."""

    redis_password: str = ""
    """Redis password (leave empty for no authentication)."""

    redis_db: int = 0
    """Redis logical database index."""

    # --- Logging ---
    log_level: str = "info"
    """Uvicorn/application log level."""

    model_config = SettingsConfigDict(
        env_prefix="VISION_NSFW_",
        env_nested_delimiter="__",
        env_file=(
            Path(__file__).parent.parent.parent / ".env",  # Project root (fallback)
            ".env",  # Current working directory (takes precedence)
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def to_diagnostics_payload(self) -> dict[str, str]:
        """Return settings as a diagnostics-safe mapping (secrets redacted)."""
        import json

        return {
            "confidence_threshold": str(self.confidence_threshold),
            "area_ratio_threshold": str(self.area_ratio_threshold),
            "debug_detect_threshold": str(self.debug_detect_threshold),
            "block": json.dumps(self.block.model_dump()),
            "review": json.dumps(self.review.model_dump()),
            "sensitive": json.dumps(self.sensitive.model_dump()),
            "queue_backend": str(self.queue_backend),
            "queue_max_size": str(self.queue_max_size),
            "thread_pool_size": str(self.thread_pool_size),
            "verify_ssl": str(self.verify_ssl),
            "workers": str(self.workers),
        }


@lru_cache
def get_settings() -> AppSettings:
    """Return a cached ``AppSettings`` instance.

    Call this function via ``Depends(get_settings)`` in FastAPI route handlers.
    Override ``app.dependency_overrides[get_settings]`` in tests to inject
    mock settings without touching environment variables.
    """
    try:
        return AppSettings()  # ty: ignore
    except ValidationError as exc:
        _pretty_config_error(exc)
        raise SystemExit(1) from None
