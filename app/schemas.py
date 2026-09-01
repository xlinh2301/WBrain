from pydantic import BaseModel, Field


class CropResult(BaseModel):
    box: list[int] = Field(description="x1, y1, x2, y2")
    confidence: float
    text: str = ""
    text_confidence: float = 0.0


class RecognitionResponse(BaseModel):
    request_id: str
    processing_ms: float
    crops: list[CropResult]
    warning: str | None = None
