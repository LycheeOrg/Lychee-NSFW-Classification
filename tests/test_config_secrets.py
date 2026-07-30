"""Tests for Docker secrets file support on AppSettings."""

from pathlib import Path
from typing import ClassVar

import pytest
from pydantic_settings import SettingsConfigDict

from app.config import AppSettings


def _settings_with_secrets_dir(tmp_path: Path) -> type[AppSettings]:
    """Build an AppSettings subclass reading only from `tmp_path` as secrets_dir.

    Disables the `.env` file lookup so the test is isolated from any local
    developer `.env`.
    """

    class _TestSettings(AppSettings):
        model_config: ClassVar[SettingsConfigDict] = {
            **AppSettings.model_config,
            "secrets_dir": tmp_path,
            "env_file": None,
        }

    return _TestSettings


def test_reads_required_fields_from_secrets_dir(tmp_path: Path) -> None:
    (tmp_path / "VISION_NSFW_API_KEY").write_text("secret-from-file")
    (tmp_path / "VISION_NSFW_LYCHEE_API_URL").write_text("http://lychee-from-file")

    settings = _settings_with_secrets_dir(tmp_path)()

    assert settings.api_key == "secret-from-file"
    assert settings.lychee_api_url == "http://lychee-from-file"


def test_env_var_overrides_secrets_dir_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "VISION_NSFW_API_KEY").write_text("secret-from-file")
    (tmp_path / "VISION_NSFW_LYCHEE_API_URL").write_text("http://lychee-from-file")
    monkeypatch.setenv("VISION_NSFW_API_KEY", "secret-from-env")

    settings = _settings_with_secrets_dir(tmp_path)()

    assert settings.api_key == "secret-from-env"
    assert settings.lychee_api_url == "http://lychee-from-file"


def test_missing_secrets_dir_does_not_raise(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    class _TestSettings(AppSettings):
        model_config: ClassVar[SettingsConfigDict] = {
            **AppSettings.model_config,
            "secrets_dir": missing,
            "env_file": None,
        }

    settings = _TestSettings(lychee_api_url="http://lychee", api_key="key")

    assert settings.api_key == "key"
