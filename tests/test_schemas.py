import pytest
from pydantic import ValidationError

from app.api.schemas import DetectRequest


def test_detect_request_requires_image_source() -> None:
    with pytest.raises(ValidationError):
        DetectRequest(photo_id="1")


def test_detect_request_url_only() -> None:
    req = DetectRequest(photo_id="1", image_url="http://example.com/img.jpg")
    assert req.image_url == "http://example.com/img.jpg"
    assert req.image_path is None


def test_detect_request_path_only() -> None:
    req = DetectRequest(photo_id="1", image_path="/tmp/img.jpg")
    assert req.image_path == "/tmp/img.jpg"
    assert req.image_url is None


def test_detect_request_both_allowed() -> None:
    req = DetectRequest(photo_id="1", image_url="http://example.com/img.jpg", image_path="/tmp/img.jpg")
    assert req.image_url is not None
    assert req.image_path is not None
