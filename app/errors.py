from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    status_code: int


FILE_TYPE_ERROR = ApiError("WBRAIN-API-001", "file must be an image", 415)
IMAGE_TOO_LARGE = ApiError("WBRAIN-API-002", "image is too large", 413)
IMAGE_DECODE_ERROR = ApiError("WBRAIN-API-003", "cannot decode image", 400)
INFERENCE_ERROR = ApiError(
    "WBRAIN-PIPELINE-001",
    "recognition could not be completed; check the service logs",
    503,
)
INTERNAL_ERROR = ApiError(
    "WBRAIN-INTERNAL-001",
    "internal service error; check the service logs",
    500,
)
