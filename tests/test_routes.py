from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/nsfw/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture
def mock_detector() -> tuple:
    raw = [
        {
            "class": "FEMALE_BREAST_EXPOSED",
            "score": 0.9,
            "box": [10, 20, 100, 150],
        }
    ]
    return raw, 800, 600


def test_detect_from_path(mock_detector: tuple) -> None:
    raw, w, h = mock_detector
    with (
        patch("app.detection.detector.detect_from_path", return_value=(raw, w, h)),
        patch("app.detection.detector.classify", return_value=(False, [])),
    ):
        response = client.post(
            "/api/nsfw/detect",
            json={"photo_id": "1", "image_path": "/tmp/test.jpg"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["photo_id"] == "1"
    assert data["is_safe"] is False


def test_detect_from_url(mock_detector: tuple) -> None:
    raw, w, h = mock_detector
    with (
        patch("app.detection.detector.detect_from_url", return_value=(raw, w, h)),
        patch("app.detection.detector.classify", return_value=(True, [])),
    ):
        response = client.post(
            "/api/nsfw/detect",
            json={"photo_id": "2", "image_url": "http://example.com/img.jpg"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["photo_id"] == "2"
    assert data["is_safe"] is True


def test_detect_missing_image_source() -> None:
    response = client.post(
        "/api/nsfw/detect",
        json={"photo_id": "3"},
    )
    assert response.status_code == 422


def test_detect_invalid_image_raises_422() -> None:
    with patch("app.detection.detector.detect_from_path", side_effect=FileNotFoundError("not found")):
        response = client.post(
            "/api/nsfw/detect",
            json={"photo_id": "4", "image_path": "/nonexistent.jpg"},
        )
    assert response.status_code == 422
    assert "Image could not be processed" in response.json()["detail"]
