from __future__ import annotations

import uuid

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .pipeline import load_components, run_pipeline
from .schemas import CropResult, RecognitionResponse

app = FastAPI(title="WBrain Water Meter OCR", version="0.1.0")
app.mount("/web", StaticFiles(directory="web"), name="web")
settings = get_settings()
detector, recognizer, startup_warning = load_components(settings)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("web/index.html")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "device": "cpu", "warning": startup_warning}


@app.post("/api/v1/recognize", response_model=RecognitionResponse)
async def recognize(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "file must be an image")
    payload = await file.read()
    if len(payload) > settings.max_image_bytes:
        raise HTTPException(413, "image is too large")
    image = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "cannot decode image")
    rows, elapsed = run_pipeline(image, detector, recognizer)
    return RecognitionResponse(
        request_id=str(uuid.uuid4()),
        processing_ms=round(elapsed, 2),
        crops=[
            CropResult(
                box=b, confidence=round(c, 4), text=t, text_confidence=round(tc, 4)
            )
            for b, c, t, tc in rows
        ],
        warning=startup_warning,
    )
