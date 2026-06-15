from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = ""

    lychee_url: str = ""
    lychee_api_key: str = ""

    # Detection thresholds (mirroring example.py defaults)
    confidence_threshold: float = 0.1
    confidence_banned_threshold: float = 0.05
    unsafe_confidence_threshold: float = 0.3
    unsafe_area_ratio_threshold: float = 0.02

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "env_prefix": "VISION_NSFW_"}


settings = Settings()
