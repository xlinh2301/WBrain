from __future__ import annotations

import time
import uuid

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
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
from .schemas import CropResult, RecognitionResponse

settings = get_settings()
configure_logging(settings.log_path, settings.log_max_bytes, settings.log_backup_count)
logger = get_logger(__name__)
app = FastAPI(title="WBrain Water Meter OCR", version="0.1.0")
app.mount("/web", StaticFiles(directory="web"), name="web")
detector, recognizer, startup_warning = load_components(settings)


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


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            getattr(locals().get("response"), "status_code", 500),
            (time.perf_counter() - started) * 1000,
        )
        request_id_context.reset(token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    mapping = {
        400: IMAGE_DECODE_ERROR,
        413: IMAGE_TOO_LARGE,
        415: FILE_TYPE_ERROR,
    }
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
    return {"status": "ok", "device": "cpu", "warning": startup_warning}


@app.post("/api/v1/recognize", response_model=RecognitionResponse)
async def recognize(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(FILE_TYPE_ERROR.status_code, FILE_TYPE_ERROR.message)
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
    )
