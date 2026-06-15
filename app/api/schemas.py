from pydantic import BaseModel, model_validator


class DetectRequest(BaseModel):
    photo_id: str
    image_url: str | None = None
    image_path: str | None = None

    @model_validator(mode="after")
    def require_image_source(self) -> "DetectRequest":
        if not self.image_url and not self.image_path:
            raise ValueError("Either image_url or image_path must be provided")
        return self


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Detection(BaseModel):
    label: str
    confidence: float
    bbox: BoundingBox
    area_ratio: float


class DetectResponse(BaseModel):
    photo_id: str
    is_safe: bool
    detections: list[Detection]
