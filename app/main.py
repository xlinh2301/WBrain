from __future__ import annotations

import hashlib
import re
import secrets
import time
import uuid
from pathlib import Path
from sqlite3 import IntegrityError

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Database
from .errors import (
    FILE_TYPE_ERROR,
    IMAGE_DECODE_ERROR,
    IMAGE_TOO_LARGE,
    INFERENCE_ERROR,
    INTERNAL_ERROR,
    ApiError,
)
from .logging import configure_logging, get_logger, request_id_context
from .pipeline import load_components, run_pipeline
from .schemas import CropResult, MeterCreate, RecognitionResponse, ReviewUpdate

settings = get_settings()
configure_logging(settings.log_path, settings.log_max_bytes, settings.log_backup_count)
logger = get_logger(__name__)
app = FastAPI(title="WBrain Water Meter OCR", version="0.1.0")
app.mount("/web", StaticFiles(directory="web"), name="web")
# Vite emits root-relative asset URLs; expose them when a frontend build exists.
if Path("web/assets").is_dir():
    app.mount("/assets", StaticFiles(directory="web/assets"), name="assets")
detector, recognizer, startup_warning = load_components(settings)
database = Database(settings.database_path) if settings.persistence_enabled else None


def _error_response(error: ApiError, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def _require_api_key(request: Request) -> None:
    supplied = request.headers.get("X-API-Key", "")
    if settings.api_key and not secrets.compare_digest(supplied, settings.api_key):
        raise HTTPException(401, "authentication required")


def _reading_value(text: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _validate_reading(
    meter_id: str | None, value: float | None, confidence: float
) -> tuple[str, str | None]:
    if value is None:
        return "review_required", "OCR result is not numeric"
    if confidence < settings.review_confidence_threshold:
        return "review_required", "OCR confidence is below threshold"
    if meter_id and database:
        previous = database.previous_value(meter_id)
        if previous is not None and value < previous:
            return "review_required", "reading is lower than previous reading"
    return "accepted", None


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    request.state.request_id = request_id
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            getattr(response, "status_code", 500),
            (time.perf_counter() - started) * 1000,
        )
        request_id_context.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    mapping = {400: IMAGE_DECODE_ERROR, 413: IMAGE_TOO_LARGE, 415: FILE_TYPE_ERROR}
    error = mapping.get(
        exc.status_code,
        ApiError(f"WBRAIN-HTTP-{exc.status_code}", str(exc.detail), exc.status_code),
    )
    logger.warning(
        "handled API error code=%s", error.code, extra={"error_code": error.code}
    )
    return _error_response(error, request.state.request_id)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = ApiError("WBRAIN-API-400", "invalid request", 400)
    logger.warning(
        "request validation failed code=%s",
        error.code,
        extra={"error_code": error.code},
    )
    return _error_response(error, request.state.request_id)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "unhandled exception code=%s",
        INTERNAL_ERROR.code,
        extra={"error_code": INTERNAL_ERROR.code},
    )
    return _error_response(INTERNAL_ERROR, request.state.request_id)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("web/index.html")


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "device": "cpu",
        "warning": startup_warning,
        "persistence": database is not None,
    }


@app.post("/api/v1/recognize", response_model=RecognitionResponse)
async def recognize(
    request: Request,
    file: UploadFile = File(...),
    meter_id: str | None = Form(default=None),
):
    _require_api_key(request)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(FILE_TYPE_ERROR.status_code, FILE_TYPE_ERROR.message)
    if meter_id and database and not database.get_meter(meter_id):
        raise HTTPException(404, "meter not found")
    payload = await file.read()
    if len(payload) > settings.max_image_bytes:
        raise HTTPException(IMAGE_TOO_LARGE.status_code, IMAGE_TOO_LARGE.message)
    image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(IMAGE_DECODE_ERROR.status_code, IMAGE_DECODE_ERROR.message)
    try:
        rows, elapsed = run_pipeline(image, detector, recognizer)
    except Exception:
        logger.exception(
            "pipeline failed code=%s",
            INFERENCE_ERROR.code,
            extra={"error_code": INFERENCE_ERROR.code},
        )
        return _error_response(INFERENCE_ERROR, request.state.request_id)

    reading_id = None
    reading_status = None
    if database:
        digest = hashlib.sha256(payload).hexdigest()
        storage_path = None
        if settings.store_images:
            suffix = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }.get(file.content_type, ".bin")
            target = settings.image_storage_dir / f"{digest}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            storage_path = str(target)
        image_id = database.add_image(
            meter_id, digest, file.content_type, len(payload), storage_path
        )
        text = "".join(row[2] for row in rows)
        confidence = float(np.mean([row[3] for row in rows])) if rows else 0.0
        value = _reading_value(text)
        reading_status, reason = _validate_reading(meter_id, value, confidence)
        record = database.add_reading(
            {
                "meter_id": meter_id,
                "image_id": image_id,
                "raw_text": text,
                "value": value,
                "confidence": confidence,
                "status": reading_status,
                "anomaly_reason": reason,
                "model_version": settings.model_version,
                "processing_ms": elapsed,
            },
            request.state.request_id,
        )
        reading_id = record["id"]
    return RecognitionResponse(
        request_id=request.state.request_id,
        processing_ms=round(elapsed, 2),
        crops=[
            CropResult(
                box=b, confidence=round(c, 4), text=t, text_confidence=round(tc, 4)
            )
            for b, c, t, tc in rows
        ],
        warning=startup_warning,
        reading_id=reading_id,
        reading_status=reading_status,
    )


@app.post("/api/v1/meters", status_code=201)
def create_meter(request: Request, payload: MeterCreate):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    try:
        return database.create_meter(payload.model_dump(), request.state.request_id)
    except IntegrityError:
        raise HTTPException(409, "meter serial number already exists") from None


@app.get("/api/v1/meters")
def list_meters(request: Request, limit: int = 50, offset: int = 0):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    return database.list_meters(max(1, min(limit, 100)), max(0, offset))


@app.get("/api/v1/meters/{meter_id}")
def get_meter(request: Request, meter_id: str):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    meter = database.get_meter(meter_id)
    if not meter:
        raise HTTPException(404, "meter not found")
    return meter


@app.get("/api/v1/meters/{meter_id}/readings")
def meter_readings(request: Request, meter_id: str, limit: int = 50, offset: int = 0):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    if not database.get_meter(meter_id):
        raise HTTPException(404, "meter not found")
    return database.list_readings(meter_id, max(1, min(limit, 100)), max(0, offset))


@app.get("/api/v1/readings")
def readings(
    request: Request, meter_id: str | None = None, limit: int = 50, offset: int = 0
):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    return database.list_readings(meter_id, max(1, min(limit, 100)), max(0, offset))


@app.get("/api/v1/reviews")
def reviews(
    request: Request, status: str = "pending", limit: int = 50, offset: int = 0
):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    if status not in {"pending", "approved", "rejected"}:
        raise HTTPException(400, "invalid review status")
    return database.list_reviews(status, max(1, min(limit, 100)), max(0, offset))


@app.patch("/api/v1/reviews/{task_id}")
def update_review(request: Request, task_id: str, payload: ReviewUpdate):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    result = database.review(
        task_id,
        payload.status,
        payload.corrected_value,
        payload.reviewer,
        payload.note,
        request.state.request_id,
    )
    if not result:
        raise HTTPException(404, "review task not found")
    return result


@app.get("/api/v1/models")
def list_models(request: Request):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    return database.list_models()


@app.post("/api/v1/models", status_code=201)
def add_model(request: Request, name: str, version: str, checksum: str | None = None):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    try:
        return database.add_model(name, version, checksum, request.state.request_id)
    except IntegrityError:
        raise HTTPException(409, "model version already exists") from None


@app.get("/api/v1/audit")
def audit(request: Request, request_id: str | None = None, limit: int = 100):
    _require_api_key(request)
    if not database:
        raise HTTPException(503, "persistence is disabled")
    return database.list_audit(request_id, max(1, min(limit, 200)))
