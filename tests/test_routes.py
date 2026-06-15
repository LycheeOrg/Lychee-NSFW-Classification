"""Route tests.

All tests use a mock lifespan that pre-populates ``app.state`` with a stub
queue (no DB, no NudeNet) and overrides ``get_settings`` so no real env vars
are required.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import AppSettings, get_settings
from app.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator
    from pathlib import Path

    from fastapi import FastAPI

    from app.queue.base import Job

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_settings(**overrides: Any) -> AppSettings:
    from app.config import LabelSetConfig

    defaults = dict(
        lychee_api_url="http://lychee",
        api_key="test-key",
        verify_ssl=False,
        skip_lychee_check=True,
        photos_path="/tmp",
        confidence_threshold=0.1,
        area_ratio_threshold=0.0,
        block=LabelSetConfig(labels=["FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"]),
        review=LabelSetConfig(labels=["BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED"]),
        sensitive=LabelSetConfig(labels=["FEMALE_BREAST_COVERED", "FEMALE_GENITALIA_COVERED", "ANUS_COVERED"]),
        queue_backend="database",
        queue_max_size=0,
        storage_path="/tmp/nsfw-queue-test",
        thread_pool_size=1,
        workers=1,
        log_level="warning",
        pg_host="localhost",
        pg_port=5432,
        pg_database="ai_vision",
        pg_user="ai_vision",
        pg_password="",
        redis_host="localhost",
        redis_port=6379,
        redis_password="",
        redis_db=0,
    )
    defaults.update(overrides)
    return AppSettings.model_construct(**defaults)  # ty: ignore[invalid-argument-type]


class _StubQueue:
    """In-memory queue stub for tests."""

    def __init__(self) -> None:
        self._jobs: list[Job] = []
        self._counter = 0
        self.enqueue = AsyncMock(return_value=True)
        self.dequeue = AsyncMock(return_value=None)
        self.complete = AsyncMock()
        self.size = AsyncMock(return_value=0)
        self.purge = AsyncMock()
        self.position = AsyncMock(return_value=None)
        self.close = AsyncMock()


@pytest.fixture
def stub_queue() -> _StubQueue:
    return _StubQueue()


@pytest.fixture
def test_settings() -> AppSettings:
    return _make_settings()


@pytest.fixture
def client(stub_queue: _StubQueue, test_settings: AppSettings) -> Generator[TestClient]:
    @asynccontextmanager
    async def _mock_lifespan(app: FastAPI) -> AsyncGenerator[None]:
        from concurrent.futures import ThreadPoolExecutor

        app.state.queue = stub_queue
        app.state.executor = ThreadPoolExecutor(max_workers=1)
        yield
        app.state.executor.shutdown(wait=False)

    application = create_app(lifespan=_mock_lifespan)
    application.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(application) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    response = client.get("/api/nsfw/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /config
# ---------------------------------------------------------------------------


def test_config_requires_api_key(client: TestClient) -> None:
    response = client.get("/api/nsfw/config")
    assert response.status_code == 401


def test_config_returns_diagnostics(client: TestClient) -> None:
    response = client.get("/api/nsfw/config", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert "confidence_threshold" in data["config"]
    assert "api_key" not in data["config"]


# ---------------------------------------------------------------------------
# POST /detect
# ---------------------------------------------------------------------------


def test_detect_returns_202_and_enqueues(
    stub_queue: _StubQueue,
    tmp_path: Path,
) -> None:
    # photos_path must match the directory where the file lives
    settings = _make_settings(photos_path=str(tmp_path))
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
        from concurrent.futures import ThreadPoolExecutor

        app.state.queue = stub_queue
        app.state.executor = ThreadPoolExecutor(max_workers=1)
        yield
        app.state.executor.shutdown(wait=False)

    application = create_app(lifespan=_lifespan)
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as c:
        response = c.post(
            "/api/nsfw/detect",
            json={"photo_id": "42", "photo_path": "photo.jpg"},
            headers={"X-API-Key": "test-key"},
        )
    assert response.status_code == 202
    stub_queue.enqueue.assert_awaited_once()
    call_kwargs = stub_queue.enqueue.call_args
    assert call_kwargs.kwargs["job_type"] == "detect"
    assert call_kwargs.kwargs["photo_id"] == "42"


def test_detect_missing_api_key(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/nsfw/detect", json={"photo_id": "1", "photo_path": "photo.jpg"})
    assert response.status_code == 401


def test_detect_file_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/nsfw/detect",
        json={"photo_id": "1", "photo_path": "missing.jpg"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_detect_path_traversal_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/nsfw/detect",
        json={"photo_id": "1", "photo_path": "/../etc/passwd"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 400
    assert "outside the allowed directory" in response.json()["detail"]


def test_detect_queue_full_returns_429(
    stub_queue: _StubQueue,
    tmp_path: Path,
) -> None:
    settings = _make_settings(photos_path=str(tmp_path))
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")
    stub_queue.enqueue.return_value = False

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
        from concurrent.futures import ThreadPoolExecutor

        app.state.queue = stub_queue
        app.state.executor = ThreadPoolExecutor(max_workers=1)
        yield
        app.state.executor.shutdown(wait=False)

    application = create_app(lifespan=_lifespan)
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as c:
        response = c.post(
            "/api/nsfw/detect",
            json={"photo_id": "1", "photo_path": "photo.jpg"},
            headers={"X-API-Key": "test-key"},
        )
    assert response.status_code == 429


# ---------------------------------------------------------------------------
# /queue endpoints
# ---------------------------------------------------------------------------


def test_queue_size(client: TestClient, stub_queue: _StubQueue) -> None:
    stub_queue.size.return_value = 3
    response = client.get("/api/nsfw/queue", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    assert response.json()["pending"] == 3


def test_queue_purge(client: TestClient, stub_queue: _StubQueue) -> None:
    response = client.delete("/api/nsfw/queue", headers={"X-API-Key": "test-key"})
    assert response.status_code == 204
    stub_queue.purge.assert_awaited_once()


def test_queue_position_found(client: TestClient, stub_queue: _StubQueue) -> None:
    stub_queue.position.return_value = 2
    response = client.get("/api/nsfw/queue/42", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    assert response.json() == {"photo_id": "42", "position": 2}


def test_queue_position_not_found(client: TestClient, stub_queue: _StubQueue) -> None:
    stub_queue.position.return_value = None
    response = client.get("/api/nsfw/queue/99", headers={"X-API-Key": "test-key"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Background job (_run_detection_job)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_run_detection_job_calls_callback(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from app.api.routes import _run_detection_job

    settings = _make_settings()
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")

    raw = [{"class": "FEMALE_BREAST_EXPOSED", "score": 0.9, "box": [10, 20, 100, 150]}]

    callback_route = respx.post("http://lychee/api/v2/NsfwDetection/results").mock(return_value=httpx.Response(200))

    classify_result = {
        "should_block": False,
        "should_review": False,
        "is_sensitive": False,
        "all_detected": [],
        "block_detected": [],
        "review_detected": [],
        "sensitive_detected": [],
    }
    with (
        patch("app.detection.detector.detect_from_path", return_value=(raw, 800, 600)),
        patch("app.detection.detector.classify", return_value=classify_result),
    ):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            await _run_detection_job(
                photo_id="1",
                image_path=img,
                executor=executor,
                settings=settings,
            )
        finally:
            executor.shutdown(wait=False)

    assert callback_route.called
    payload = callback_route.calls.last.request
    import json

    body = json.loads(payload.content)
    assert body["photo_id"] == "1"
    assert body["status"] == "success"
    assert "should_block" in body
    assert "should_review" in body
    assert "is_sensitive" in body


@pytest.mark.asyncio
@respx.mock
async def test_run_detection_job_sends_error_callback_on_failure(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from app.api.routes import _run_detection_job

    settings = _make_settings()
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")

    error_route = respx.post("http://lychee/api/v2/NsfwDetection/results").mock(return_value=httpx.Response(200))

    with patch("app.detection.detector.detect_from_path", side_effect=RuntimeError("boom")):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            await _run_detection_job(
                photo_id="2",
                image_path=img,
                executor=executor,
                settings=settings,
            )
        finally:
            executor.shutdown(wait=False)

    assert error_route.called
    import json

    body = json.loads(error_route.calls.last.request.content)
    assert body["status"] == "error"
    assert body["photo_id"] == "2"
