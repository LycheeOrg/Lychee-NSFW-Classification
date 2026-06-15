from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import verify_api_key
from app.api.schemas import BoundingBox, Detection, DetectRequest, DetectResponse
from app.detection import detector

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/detect", response_model=DetectResponse, dependencies=[Depends(verify_api_key)])
def detect(request: DetectRequest) -> DetectResponse:
    try:
        if request.image_url:
            raw, w, h = detector.detect_from_url(request.image_url)
        elif request.image_path is not None:
            raw, w, h = detector.detect_from_path(request.image_path)
        else:
            raise HTTPException(status_code=422, detail="Either image_url or image_path must be provided")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Image could not be processed: {exc}") from exc

    is_safe, dets = detector.classify(raw, w, h)

    return DetectResponse(
        photo_id=request.photo_id,
        is_safe=is_safe,
        detections=[
            Detection(
                label=d["label"],
                confidence=d["confidence"],
                bbox=BoundingBox(**d["bbox"]),
                area_ratio=d["area_ratio"],
            )
            for d in dets
        ],
    )
