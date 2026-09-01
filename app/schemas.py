from datetime import datetime

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
    reading_id: str | None = None
    reading_status: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class MeterCreate(BaseModel):
    serial_number: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=255)
    meter_type: str | None = Field(default=None, max_length=128)
    address: str | None = Field(default=None, max_length=500)


class MeterResponse(MeterCreate):
    id: str
    status: str
    created_at: datetime | str
    updated_at: datetime | str


class ReviewUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    corrected_value: float | None = Field(default=None, ge=0)
    reviewer: str | None = Field(default=None, max_length=128)
    note: str | None = Field(default=None, max_length=1000)
